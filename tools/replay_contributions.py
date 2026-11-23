#!/usr/bin/env python3
"""Replay yearly contributions into the directory and restore the groups.

Issue #272: Cooperators whose yearly contribution lapsed ended up in no
Dynamic Group at all, and renewals invoiced by the online shop never
reached the directory. This tool repairs both from a list of renewals:

1. it reads a CSV of ``pseudonym`` + end of validity of the yearly
   contribution (the shop's invoices are the reference);
2. it writes each date into ``dateEndValidityYearlyContribution`` of
   the matching Cooperator;
3. it re-synchronises the Dynamic Groups (#148) of EVERY active
   Ordinary Member and Cooperator of the directory — the members of
   the list become Cooperators again, the others get back
   ``communityMembersGroup`` and the candidates group their facts
   call for;
4. it asks Keycloak to re-import the changed entries (#269).

It talks to the directory only, through the application's own code
(``dynamic_groups.sync_member_groups``): the application may keep
running, and each member's cached profile is refreshed from the
directory at their next login. Run it on the server, from the
application directory, so the ``.env`` holding the LDAP settings is
found.

The CSV has a header line and one renewal per line; blank lines and
lines starting with ``#`` are ignored:

    pseudonym,date_end_validity_yearly_contribution
    SomePseudonym,2027-09-08

Without ``--apply`` nothing is written: the tool prints what it WOULD
do — every date to write and every member whose groups would move —
so the plan can be read before it is run. A pseudonym that matches no
Cooperator, or several, aborts the run before any write. A date
EARLIER than the one the directory already holds is not written
unless ``--allow-earlier`` is given: a payment recorded since the list
was drawn up must not be undone.

Usage:
    .venv/bin/python tools/replay_contributions.py renewals.csv
    .venv/bin/python tools/replay_contributions.py renewals.csv --apply

Exit code 0: the plan is consistent (dry run), or every write landed
and every member converged (``--apply``). 1: at least one write or
synchronisation failed — the run is idempotent, fix and run it again.
2: the list itself is unusable; nothing was written.
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from ldap3 import MODIFY_REPLACE

from alirpunkto import dynamic_groups
from alirpunkto.constants_and_globals import (
    LDAP_BASE_DN,
    LDAP_DEFAULT_HOUR,
    LDAP_PASSWORD,
    LDAP_TIME_FORMAT,
    LDAP_USER,
)
from alirpunkto.dynamic_groups import (
    COOPERATORS,
    MANAGED_GROUPS,
    MEMBER_FACT_ATTRIBUTES,
    compute_target_groups,
    member_facts,
)
from alirpunkto.ldap_factory import get_ldap_connection
from alirpunkto.models.member import MemberTypes
from alirpunkto.secret_manager import get_secret

PSEUDONYM_COLUMN = 'pseudonym'
DATE_COLUMN = 'date_end_validity_yearly_contribution'
DATE_FORMAT = '%Y-%m-%d'

#: A validity date outside this window is a typo, not a contribution —
#: the same window as ``tools/update_cooperator.py``.
MIN_YEAR = 1900
MAX_YEAR = 2199

IN_SCOPE = (MemberTypes.ORDINARY, MemberTypes.COOPERATOR)


class UnusableList(ValueError):
    """The CSV cannot be replayed as it stands; nothing must be written."""


def read_renewals(path: Path) -> list[tuple[str, date]]:
    """The ``(pseudonym, end of validity)`` pairs of the CSV, in file
    order. Every defect of the file is collected and reported at once."""
    problems = []
    renewals = []
    seen = {}
    with open(path, newline='', encoding='utf-8-sig') as handle:
        lines = [(number, line) for number, line in enumerate(handle, 1)
                 if line.strip() and not line.lstrip().startswith('#')]
    if not lines:
        raise UnusableList(f"{path}: no line to replay")
    reader = csv.reader(line for _, line in lines)
    header = [cell.strip() for cell in next(reader)]
    if header != [PSEUDONYM_COLUMN, DATE_COLUMN]:
        raise UnusableList(
            f"{path}: line {lines[0][0]}: the header must be "
            f"'{PSEUDONYM_COLUMN},{DATE_COLUMN}', got {','.join(header)!r}")
    for (number, _), cells in zip(lines[1:], reader):
        cells = [cell.strip() for cell in cells]
        if len(cells) != 2 or not cells[0]:
            problems.append(f"line {number}: expected 'pseudonym,date'")
            continue
        pseudonym, raw = cells
        try:
            end = datetime.strptime(raw, DATE_FORMAT).date()
            if not MIN_YEAR <= end.year <= MAX_YEAR:
                raise ValueError(raw)
        except ValueError:
            problems.append(
                f"line {number}: {raw!r} is not a YYYY-MM-DD date between "
                f"{MIN_YEAR} and {MAX_YEAR}")
            continue
        key = pseudonym.casefold()
        if key in seen:
            problems.append(f"line {number}: {pseudonym!r} already listed "
                            f"on line {seen[key]}")
            continue
        seen[key] = number
        renewals.append((pseudonym, end))
    if problems:
        raise UnusableList(f"{path}: " + '; '.join(problems))
    if not renewals:
        raise UnusableList(f"{path}: no renewal after the header")
    return renewals


def read_members(conn) -> list[dict]:
    """Every entry of the directory carrying a ``uid``, with its
    pseudonym and the facts of the truth table."""
    conn.search(LDAP_BASE_DN, '(uid=*)',
                attributes=['uid', 'cn', *MEMBER_FACT_ATTRIBUTES])
    members = []
    for entry in conn.entries:
        uid = dynamic_groups.entry_values(entry, 'uid')
        if not uid or not uid[0]:
            continue
        pseudonym = dynamic_groups.entry_values(entry, 'cn')
        members.append({
            'oid': str(uid[0]),
            'pseudonym': str(pseudonym[0]) if pseudonym else '',
            **member_facts(entry),
        })
    return members


def _as_date(value):
    return value.date() if isinstance(value, datetime) else value


def build_plan(members, renewals, *, today=None, allow_earlier=False):
    """What a run would do, without touching anything.

    Returns ``(dates, moves, notes)``: ``dates`` maps the oid of each
    listed Cooperator to the date to write (only when it differs from
    the directory), ``moves`` lists ``(member, current, target)`` for
    every in-scope member whose managed groups would change, ``notes``
    are remarks worth a human eye. Raises :class:`UnusableList` when a
    pseudonym cannot be resolved to exactly one Cooperator."""
    today = today or date.today()
    by_pseudonym = {}
    for member in members:
        by_pseudonym.setdefault(
            member['pseudonym'].casefold(), []).append(member)
    problems, notes = [], []
    dates = {}
    planned_end = {}
    listed = set()
    for pseudonym, end in renewals:
        matches = by_pseudonym.get(pseudonym.casefold(), [])
        if not matches:
            problems.append(f"{pseudonym!r}: no such pseudonym in the "
                            "directory")
            continue
        if len(matches) > 1:
            problems.append(
                f"{pseudonym!r}: {len(matches)} entries carry this "
                f"pseudonym ({', '.join(m['oid'] for m in matches)})")
            continue
        member = matches[0]
        if member['employee_type'] != MemberTypes.COOPERATOR:
            problems.append(
                f"{pseudonym!r} ({member['oid']}) is not a Cooperator "
                f"(employeeType "
                f"{getattr(member['employee_type'], 'name', 'unknown')})")
            continue
        listed.add(member['oid'])
        current = _as_date(member['end'])
        if current == end:
            notes.append(f"{pseudonym}: already valid until {end}")
        elif current is not None and current > end and not allow_earlier:
            notes.append(
                f"{pseudonym}: the directory already holds a LATER date "
                f"({current} > {end}); kept (--allow-earlier to overwrite)")
        else:
            dates[member['oid']] = end
            planned_end[member['oid']] = end
    if problems:
        raise UnusableList('; '.join(problems))

    managed = set(MANAGED_GROUPS)
    moves = []
    for member in members:
        if member['employee_type'] not in IN_SCOPE:
            continue
        current = member['member_side'] & managed
        target = compute_target_groups(
            member['employee_type'], member['is_active'], member['shares'],
            planned_end.get(member['oid'], member['end']), current, today)
        if target != current:
            moves.append((member, current, target))
        if member['oid'] in listed and COOPERATORS not in (target or ()):
            notes.append(
                f"{member['pseudonym']}: will NOT be in {COOPERATORS} "
                f"despite the renewal — {_why_not_cooperator(member)}")
    return dates, moves, notes


def _why_not_cooperator(member) -> str:
    if not member['is_active']:
        return "isActive is false (resigned or never activated)"
    shares = member['shares']
    if not shares or float(shares) <= 0:
        return "numberSharesOwned is 0 or absent"
    return "sanctioned, or the date is already in the past"


def apply_plan(conn, members, dates, *, sync=None) -> list[str]:
    """Write the dates, then converge the groups of every in-scope
    member. Returns the failures, empty when everything landed."""
    sync = sync or dynamic_groups.sync_member_groups
    failures = []
    for oid, end in sorted(dates.items()):
        value = datetime.strptime(
            end.strftime(DATE_FORMAT) + LDAP_DEFAULT_HOUR, LDAP_TIME_FORMAT)
        try:
            written = conn.modify(dynamic_groups.member_dn(oid), {
                'dateEndValidityYearlyContribution': [
                    (MODIFY_REPLACE, [value.strftime(LDAP_TIME_FORMAT)])]})
        except Exception as exc:
            written = False
            print(f"[replay] ERROR writing the date of {oid}: {exc}")
        if not written:
            failures.append(f"date of {oid} not written: "
                            f"{getattr(conn, 'result', None)}")
    managed = set(MANAGED_GROUPS)
    for member in members:
        if member['employee_type'] not in IN_SCOPE:
            continue
        if not member['is_active'] and not member['member_side'] & managed:
            continue  # resigned and already out of every group
        if sync(None, member['oid']) is None:
            failures.append(f"groups of {member['oid']} "
                            f"({member['pseudonym']}) did not converge")
    return failures


def _names(groups) -> str:
    return ', '.join(sorted(groups)) if groups else '(no group)'


def print_plan(members, dates, moves, notes) -> None:
    by_oid = {member['oid']: member for member in members}
    print(f"[replay] {len(dates)} date(s) to write:")
    for oid, end in sorted(dates.items(),
                           key=lambda item: by_oid[item[0]]['pseudonym']):
        member = by_oid[oid]
        print(f"  {member['pseudonym']} ({oid}): "
              f"{_as_date(member['end']) or 'no date'} -> {end}")
    print(f"[replay] {len(moves)} member(s) whose groups move:")
    for member, current, target in sorted(
            moves, key=lambda move: move[0]['pseudonym']):
        print(f"  {member['pseudonym']} ({member['oid']}): "
              f"{_names(current)} -> {_names(target)}")
    for note in notes:
        print(f"[replay] NOTE {note}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay yearly contributions and restore the Dynamic "
                    "Groups (issue #272). Dry run unless --apply.")
    parser.add_argument('csv', type=Path,
                        help=f"CSV file: {PSEUDONYM_COLUMN},{DATE_COLUMN}")
    parser.add_argument('--apply', action='store_true',
                        help="write to the directory (default: dry run)")
    parser.add_argument('--allow-earlier', action='store_true',
                        help="overwrite a later date held by the directory")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)

    try:
        renewals = read_renewals(args.csv)
    except (OSError, UnusableList) as exc:
        print(f"[replay] unusable list: {exc}")
        return 2
    with get_ldap_connection(
            ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        members = read_members(conn)
        try:
            dates, moves, notes = build_plan(
                members, renewals, allow_earlier=args.allow_earlier)
        except UnusableList as exc:
            print(f"[replay] unusable list: {exc}")
            return 2
        print_plan(members, dates, moves, notes)
        if not args.apply:
            print("[replay] dry run: nothing written (--apply to run it)")
            return 0
        failures = apply_plan(conn, members, dates)

    from alirpunkto import keycloak_sync
    from alirpunkto.utils import notify_keycloak_of_directory_change
    if keycloak_sync.is_configured():
        if not notify_keycloak_of_directory_change(
                f"replay of {len(renewals)} yearly contribution(s)"):
            failures.append("Keycloak did not re-import the changes (the "
                            "daily maintenance retries)")
    else:
        print("[replay] Keycloak is not configured here: no propagation")
    for failure in failures:
        print(f"[replay] FAILED {failure}")
    print(f"[replay] done: {len(dates)} date(s) written, "
          f"{len(moves)} member(s) moved, {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
