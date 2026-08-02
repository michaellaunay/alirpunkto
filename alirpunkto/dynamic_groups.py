"""Transitions of members between the Dynamic Groups (issue #148).

The ticket formalises every movement as ``group = [event] => group``, but
each guard is a predicate over a handful of facts — shares owned, yearly
contribution validity, sanction, Board/MAC role — and the groups themselves
are the persistent state. The whole algebra therefore reduces to one pure
function, :func:`compute_target_groups`, whose truth table the tests lock
case by case against the ticket, and one idempotent applier,
:func:`sync_member_groups`, called at every event source: successful
registration, upgrade approval, profile update by an administrator, the
resignation flow, and the daily scan that turns calendar time (an expired
yearly contribution) into transitions.

The eleven groups of the ticket are already created at startup by
``alirpunkto.__init__``; ``ordinaryMembersGroup`` is the legacy name that
``communityMembersGroup`` replaces, and the synchroniser removes members
from it so existing deployments converge.
"""
from __future__ import annotations

from datetime import date, datetime

from alirpunkto.constants_and_globals import (
    LDAP_BASE_DN,
    LDAP_OU,
    LDAP_PASSWORD,
    LDAP_USER,
    log,
)
from alirpunkto.ldap_factory import get_ldap_connection
from alirpunkto.models.member import MemberTypes
from alirpunkto.utils import get_secret
from ldap3 import MODIFY_ADD, MODIFY_DELETE
from ldap3.utils.conv import escape_filter_chars

COMMUNITY = 'communityMembersGroup'
MISSING_SHARE_YEAR = 'candidatesMissingShareYearContribGroup'
MISSING_SHARE = 'candidatesMissingShareGroup'
MISSING_YEAR = 'candidatesMissingYearContribGroup'
COOPERATORS = 'cooperatorsGroup'
SANCTIONED = 'sanctionedGroup'
SANCTIONED_MISSING_YEAR = 'sanctionedMissingYearContribGroup'
BOARD = 'boardMembersGroup'
MAC = 'mediationArbitrationCouncilGroup'
SUSPENDED_BOARD = 'suspendedBoardMembersGroup'
SUSPENDED_MAC = 'suspendedMediationArbitrationCouncilGroup'

#: The legacy group communityMembersGroup replaces (kept in LDAP, emptied
#: progressively by the synchroniser).
LEGACY_ORDINARY = 'ordinaryMembersGroup'

#: Every group the synchroniser manages: membership in any other group
#: (administrators, providers) is out of the scope of issue #148.
MANAGED_GROUPS = (
    COMMUNITY, MISSING_SHARE_YEAR, MISSING_SHARE, MISSING_YEAR, COOPERATORS,
    SANCTIONED, SANCTIONED_MISSING_YEAR, BOARD, MAC, SUSPENDED_BOARD,
    SUSPENDED_MAC, LEGACY_ORDINARY,
)


def group_dn(name: str) -> str:
    return (f"cn={name},{LDAP_OU},{LDAP_BASE_DN}"
            if LDAP_OU else f"cn={name},{LDAP_BASE_DN}")


def member_dn(oid: str) -> str:
    return (f"uid={oid},{LDAP_OU},{LDAP_BASE_DN}"
            if LDAP_OU else f"uid={oid},{LDAP_BASE_DN}")


def _parse_ldap_date(value):
    """LDAP hands dates back as strings (ISO or LDAP_TIME_FORMAT); the
    computation wants a date. Tolerant: returns None when unparsable."""
    if value is None or isinstance(value, (date, datetime)):
        return value
    text = str(value).strip()
    for parse in (datetime.fromisoformat,
                  lambda t: datetime.strptime(t, '%Y-%m-%dT%H:%M:%S'),
                  lambda t: datetime.strptime(t, '%Y-%m-%d')):
        try:
            return parse(text)
        except (ValueError, TypeError):
            continue
    log.warning(f"dynamic_groups: unparsable date {value!r}")
    return None


def _names_from_dns(dns) -> set:
    names = set()
    for value in dns or ():
        value = str(value)
        if value.startswith('cn='):
            names.add(value[3:].split(',', 1)[0])
    return names


def compute_target_groups(
        employee_type,
        is_active: bool,
        number_shares_owned,
        date_end_validity_yearly_contribution,
        current_groups,
        today: date | None = None,
        *,
        force_sanctioned: bool | None = None) -> set | None:
    """The pure truth table of issue #148.

    Returns the set of managed groups the member must belong to, or ``None``
    when the member is out of scope (administrators, providers) and the
    groups must not be touched. ``current_groups`` carries the persistent
    facts the ticket stores as memberships: the sanction, and the Board/MAC
    role (suspended or not). ``force_sanctioned`` lets the sanction and
    lift-sanction events of issues #56/#57 override the stored fact.
    """
    if employee_type not in (MemberTypes.ORDINARY, MemberTypes.COOPERATOR):
        return None
    if not is_active:
        # Resignation / exclusion: ``=> None`` in the ticket.
        return set()
    if employee_type == MemberTypes.ORDINARY:
        return {COMMUNITY}

    today = today or date.today()
    current = set(current_groups or ())
    has_shares = bool(number_shares_owned) and float(number_shares_owned) > 0
    end = date_end_validity_yearly_contribution
    if isinstance(end, datetime):
        end = end.date()
    contribution_valid = end is not None and end >= today
    sanctioned = (force_sanctioned if force_sanctioned is not None
                  else bool(current & {SANCTIONED, SANCTIONED_MISSING_YEAR}))

    groups = {COMMUNITY}
    if sanctioned:
        groups.add(SANCTIONED if contribution_valid
                   else SANCTIONED_MISSING_YEAR)
    elif has_shares and contribution_valid:
        groups.add(COOPERATORS)
    elif has_shares:
        groups.add(MISSING_YEAR)
    elif contribution_valid:
        groups.add(MISSING_SHARE)
    else:
        groups.add(MISSING_SHARE_YEAR)

    full_cooperator = has_shares and contribution_valid and not sanctioned
    if current & {BOARD, SUSPENDED_BOARD}:
        groups.add(BOARD if full_cooperator else SUSPENDED_BOARD)
    if current & {MAC, SUSPENDED_MAC}:
        groups.add(MAC if full_cooperator else SUSPENDED_MAC)
    return groups


def sync_member_groups(request, member_oid, *, today=None,
                       force_sanctioned=None):
    """Read BOTH sides of the relation, compute the target groups and
    converge each side onto them independently.

    Sixth audit pass (2026-08-01, §12.3): the two sides — the member's
    ``uniqueMemberOf`` and each group's ``uniqueMember`` — used to
    receive one shared diff computed from the member side alone, so a
    half-applied write persisted forever. Each side now gets its own
    diff toward the same target; a detected divergence is logged
    before being repaired.

    Eighth audit pass (2026-08-02, §7/§8): the MEMBER side is the
    authoritative current state — it is what the application reads,
    and feeding the truth table the union of both sides let a stale
    group-side record resurrect a half-revoked Board/MAC/sanction
    latch ("repaired in the wrong direction"). And fail-closed is now
    enforced, not just ordered: the second write of every pair is
    conditional on the first — a grant touches the member side only
    once the group side carries it, a revocation touches the group
    side only once the member side is clean. The asymmetry is
    deliberate: a grant whose member-side write failed is rolled back
    by the next pass (losing a grant is safe and re-runnable), while a
    revocation converges until both sides are clean (resurrecting a
    revoked privilege is not). Idempotent; returns the target set, or
    None if out of scope or on failure."""
    dn = member_dn(member_oid)
    try:
        with get_ldap_connection(ldap_user=LDAP_USER,
                ldap_password=get_secret(LDAP_PASSWORD)) as conn:
            conn.search(
                LDAP_BASE_DN,
                f'(uid={escape_filter_chars(member_oid)})',
                attributes=['employeeType', 'isActive', 'numberSharesOwned',
                            'dateEndValidityYearlyContribution',
                            'uniqueMemberOf'])
            if not conn.entries:
                log.warning(f"sync_member_groups: {member_oid} not in LDAP")
                return None
            entry = conn.entries[0]
            employee_type = MemberTypes[str(entry.employeeType)] \
                if str(entry.employeeType or '') in MemberTypes.__members__ \
                else None
            is_active = str(entry.isActive) in (
                "True", "true", "TRUE", "Y", "y", "YES", "yes", "1")
            shares = entry.numberSharesOwned.value \
                if 'numberSharesOwned' in entry else None
            end = _parse_ldap_date(
                entry.dateEndValidityYearlyContribution.value
                if 'dateEndValidityYearlyContribution' in entry else None)
            member_side = _names_from_dns(
                entry.uniqueMemberOf.values
                if 'uniqueMemberOf' in entry else ())
            group_side = _group_side_groups(conn, dn)
            if (member_side & set(MANAGED_GROUPS)) != group_side:
                log.warning(
                    f"sync_member_groups: {member_oid} sides diverged "
                    f"(member side {sorted(member_side & set(MANAGED_GROUPS))}, "
                    f"group side {sorted(group_side)}); repairing both")

            # Eighth audit pass (§8): the truth table sees the MEMBER
            # side only. The union used to resurrect half-revoked
            # latches: with the member side cleared but a stale group
            # record left behind, `current` still carried the role and
            # the table granted it back.
            current = member_side
            target = compute_target_groups(
                employee_type, is_active, shares, end,
                current & set(MANAGED_GROUPS), today,
                force_sanctioned=force_sanctioned)
            if target is None:
                return None
            target &= set(MANAGED_GROUPS) - {LEGACY_ORDINARY}

            # Per-side convergence (§12.3): each side gets its own diff.
            group_add = target - group_side
            group_del = group_side - target
            member_add = target - member_side
            member_del = (member_side & set(MANAGED_GROUPS)) - target

            def _checked_modify(target_dn, changes, op_id):
                # Revised audit: half-applied membership used to fail
                # silently — one side of the group/memberOf pair could
                # succeed while the other did not. Best-effort remains
                # (the caller's operation never breaks), but every
                # failure is now logged with an operation identifier.
                try:
                    ok = conn.modify(target_dn, changes)
                except Exception as exc:
                    log.error(f"sync_member_groups {op_id}: {exc}")
                    return False
                if not ok:
                    log.error(f"sync_member_groups {op_id}: "
                              f"{getattr(conn, 'result', None)}")
                return bool(ok)

            # Eighth audit pass (§7): the second write of each pair is
            # CONDITIONAL on the first — ordering alone was not fail
            # closed, a failed first write used to be followed by the
            # second anyway.
            for name in sorted(group_add | member_add):
                on_group = (name not in group_add) or _checked_modify(
                    group_dn(name),
                    {'uniqueMember': [(MODIFY_ADD, [dn])]},
                    f"{member_oid} +{name} (group side)")
                if on_group and name in member_add:
                    _checked_modify(dn, {'uniqueMemberOf': [
                        (MODIFY_ADD, [group_dn(name)])]},
                        f"{member_oid} +{name} (member side)")
            for name in sorted(member_del | group_del):
                off_member = (name not in member_del) or _checked_modify(
                    dn, {'uniqueMemberOf': [
                        (MODIFY_DELETE, [group_dn(name)])]},
                    f"{member_oid} -{name} (member side)")
                if off_member and name in group_del:
                    _checked_modify(
                        group_dn(name),
                        {'uniqueMember': [(MODIFY_DELETE, [dn])]},
                        f"{member_oid} -{name} (group side)")
            if group_add or group_del or member_add or member_del:
                log.info(
                    f"sync_member_groups: {member_oid} "
                    f"group side +{sorted(group_add)} -{sorted(group_del)}, "
                    f"member side +{sorted(member_add)} "
                    f"-{sorted(member_del)}")
            return target
    except Exception as e:
        # Best effort by design: the group synchronisation must never break
        # the operation that triggered it — the daily scan will catch up.
        log.error(f"sync_member_groups: {member_oid}: {e}")
        return None


def _group_side_groups(conn, dn):
    """The managed groups whose ``uniqueMember`` lists ``dn`` — the group
    side of the relation, read independently of the member side
    (sixth audit pass, §12.3)."""
    names = set()
    for name in MANAGED_GROUPS:
        try:
            conn.search(group_dn(name), '(objectClass=*)',
                        search_scope='BASE',
                        attributes=['uniqueMember'])
        except Exception as exc:
            log.warning(
                f"sync_member_groups: cannot read the group side of "
                f"{name}: {exc}")
            continue
        if not conn.entries:
            continue
        values = (conn.entries[0].uniqueMember.values
                  if 'uniqueMember' in conn.entries[0] else ())
        if dn in {str(value) for value in values}:
            names.add(name)
    return names


def daily_group_scan(request, today=None):
    """The daily scan of the ticket: calendar time (an expired or renewed
    yearly contribution) becomes transitions. Scans every member found on
    EITHER side of the managed relations — a member recorded only in a
    group's ``uniqueMember``, or only in their own ``uniqueMemberOf``
    (a half-applied write), is discovered and repaired too (sixth audit
    pass, §12.3). Re-synchronises each of them; meant for a periodic
    caller (cron / console script), alongside purge_unsubscribed_members.
    Returns the oids whose groups changed."""
    changed = []
    seen = set()
    try:
        with get_ldap_connection(ldap_user=LDAP_USER,
                ldap_password=get_secret(LDAP_PASSWORD)) as conn:
            _collect_group_members(conn, seen)
            _collect_member_side_members(conn, seen)
    except Exception as e:
        log.error(f"daily_group_scan: cannot read the groups: {e}")
        return changed
    for oid in sorted(seen):
        before = _current_groups(oid)
        after = sync_member_groups(request, oid, today=today)
        if after is not None and before != after:
            changed.append(oid)
    return changed


def _collect_group_members(conn, seen):
    for name in MANAGED_GROUPS:
        try:
            conn.search(group_dn(name), '(objectClass=*)',
                        search_scope='BASE',
                        attributes=['uniqueMember'])
        except Exception as e:
            log.warning(f"daily_group_scan: cannot read {name}: {e}")
            continue
        if not conn.entries:
            continue
        for value in (conn.entries[0].uniqueMember.values
                      if 'uniqueMember' in conn.entries[0] else ()):
            value = str(value)
            if value.startswith('uid='):
                seen.add(value[4:].split(',', 1)[0])

def _collect_member_side_members(conn, seen):
    """Members whose own ``uniqueMemberOf`` names a managed group — the
    member side of the relation. Filtering is done client-side so the
    scan works against directories (and the test mock) regardless of
    their support for extensible matching on DN-valued attributes."""
    try:
        conn.search(LDAP_BASE_DN, '(objectClass=*)',
                    attributes=['uid', 'uniqueMemberOf'])
    except Exception as e:
        log.warning(f"daily_group_scan: cannot read the member side: {e}")
        return
    managed_dns = {group_dn(name) for name in MANAGED_GROUPS}
    for entry in conn.entries:
        values = (entry.uniqueMemberOf.values
                  if 'uniqueMemberOf' in entry else ())
        if not managed_dns & {str(value) for value in values}:
            continue
        if 'uid' in entry and entry.uid.value:
            seen.add(str(entry.uid.value))


def get_member_groups(member_oid):
    """The managed dynamic groups a member belongs to (issue #55: shown,
    read-only, on one's own profile). Best effort: empty set on failure."""
    return _current_groups(member_oid)


def _current_groups(member_oid):
    try:
        with get_ldap_connection(ldap_user=LDAP_USER,
                ldap_password=get_secret(LDAP_PASSWORD)) as conn:
            return _read_current_groups(conn, member_oid)
    except Exception:
        return set()


def _read_current_groups(conn, member_oid):
    conn.search(LDAP_BASE_DN,
                f'(uid={escape_filter_chars(member_oid)})',
                attributes=['uniqueMemberOf'])
    if not conn.entries:
        return set()
    entry = conn.entries[0]
    return _names_from_dns(
        entry.uniqueMemberOf.values
        if 'uniqueMemberOf' in entry else ()) & set(MANAGED_GROUPS)
