"""``tools/replay_contributions.py`` — issue #272.

The tool replays a list of yearly-contribution renewals into the
directory and restores the Dynamic Groups of every member. These tests
run it on the mock directory: the list is validated as a whole before
any write, a dry run writes nothing, and one applied run leaves the
renewed members Cooperators and everyone else back in the Community.
"""
from __future__ import annotations

import importlib.util
import os
from datetime import date
from unittest.mock import patch

import pytest
from ldap3 import MODIFY_REPLACE

import alirpunkto.dynamic_groups as dg
from alirpunkto.dynamic_groups import (
    COMMUNITY, COOPERATORS, MISSING_SHARE, MISSING_YEAR, member_dn)
from tests.test_dynamic_groups import (
    EXPIRED, TODAY, VALID, _add_member, _directory, _groups_of)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER = "pseudonym,date_end_validity_yearly_contribution\n"


def _load_tool():
    path = os.path.join(ROOT, 'tools', 'replay_contributions.py')
    spec = importlib.util.spec_from_file_location(
        'replay_contributions', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _csv(tmp_path, body, header=HEADER):
    path = tmp_path / 'renewals.csv'
    path.write_text(header + body, encoding='utf-8')
    return path


def _stored_end(conn, oid):
    conn.search(member_dn(oid), '(objectclass=*)',
                attributes=['dateEndValidityYearlyContribution'])
    values = dg.entry_values(
        conn.entries[0], 'dateEndValidityYearlyContribution')
    return str(values[0]) if values else None


def _run(conn, path, *args, today=TODAY):
    """The tool's ``main`` on the mock directory, at a fixed date."""
    real_plan, real_sync = tool.build_plan, dg.sync_member_groups

    def plan(members, renewals, **kwargs):
        return real_plan(members, renewals, today=today, **kwargs)

    def sync(request, oid):
        return real_sync(request, oid, today=today)

    with patch.object(tool, 'get_ldap_connection', return_value=conn), \
            patch.object(dg, 'get_ldap_connection', return_value=conn), \
            patch.object(tool, 'build_plan', side_effect=plan), \
            patch.object(dg, 'sync_member_groups', side_effect=sync):
        return tool.main([str(path), *args])


# --------------------------------- the list -------------------------------- #
def test_the_list_is_read_in_order_ignoring_comments(tmp_path):
    path = _csv(tmp_path, "\n# from the invoices\nAda,2027-09-08\n"
                          "Sergio Arbarviro , 2027-07-27\n")
    assert tool.read_renewals(path) == [
        ('Ada', date(2027, 9, 8)), ('Sergio Arbarviro', date(2027, 7, 27))]


@pytest.mark.parametrize("header, body, reason", [
    ("name,date\n", "Ada,2027-09-08\n", "header"),
    (HEADER, "Ada,08/09/2027\n", "not a YYYY-MM-DD"),
    (HEADER, "Ada,0000-01-01\n", "not a YYYY-MM-DD"),
    (HEADER, "Ada\n", "expected 'pseudonym,date'"),
    (HEADER, "Ada,2027-09-08\nada,2027-10-01\n", "already listed"),
    (HEADER, "", "no renewal"),
])
def test_a_defective_list_is_refused_whole(tmp_path, header, body, reason):
    with pytest.raises(tool.UnusableList, match=reason):
        tool.read_renewals(_csv(tmp_path, body, header))


# ------------------------------ the whole run ------------------------------ #
def _population(conn):
    # renewed in the shop, never recorded here, and out of every group
    _add_member(conn, 'ada', shares=2, end=EXPIRED)
    # truly lapsed, out of every group: the ticket's member
    _add_member(conn, 'bob', shares=1, end=EXPIRED)
    # an Ordinary Member who lost the Community too
    _add_member(conn, 'cy', mtype='ORDINARY')
    # resigned: must stay out of everything
    _add_member(conn, 'dee', active='False', shares=1, end=VALID)
    conn.modify(member_dn('dee'), {'dateErasureAllData': [
        (MODIFY_REPLACE, ['2027-01-01T12:00:00'])]})


def test_a_dry_run_writes_nothing(tmp_path, capsys):
    conn = _directory()
    _population(conn)
    before = _stored_end(conn, 'ada')

    assert _run(conn, _csv(tmp_path, "user-ada,2027-09-08\n")) == 0

    assert _stored_end(conn, 'ada') == before
    assert _groups_of(conn, 'ada') == set()
    out = capsys.readouterr().out
    assert "1 date(s) to write" in out
    assert "3 member(s) whose groups move" in out
    assert "dry run: nothing written" in out


def test_an_applied_run_restores_everyone(tmp_path, capsys):
    conn = _directory()
    _population(conn)

    assert _run(conn, _csv(tmp_path, "USER-ADA,2027-09-08\n"),
                '--apply') == 0

    assert _stored_end(conn, 'ada') == '2027-09-08T12:00:00'
    assert _groups_of(conn, 'ada') == {COMMUNITY, COOPERATORS}
    assert _groups_of(conn, 'bob') == {COMMUNITY, MISSING_YEAR}
    assert _groups_of(conn, 'cy') == {COMMUNITY}
    assert _groups_of(conn, 'dee') == set()
    assert "0 failure(s)" in capsys.readouterr().out


def test_a_second_run_has_nothing_left_to_do(tmp_path, capsys):
    conn = _directory()
    _population(conn)
    path = _csv(tmp_path, "user-ada,2027-09-08\n")
    assert _run(conn, path, '--apply') == 0
    capsys.readouterr()

    assert _run(conn, path, '--apply') == 0
    out = capsys.readouterr().out
    assert "0 date(s) to write" in out
    assert "0 member(s) whose groups move" in out


@pytest.mark.parametrize("line, reason", [
    ("nobody,2027-09-08\n", "no such pseudonym"),
    ("user-cy,2027-09-08\n", "not a Cooperator"),
])
def test_an_unresolved_pseudonym_aborts_before_any_write(
        tmp_path, capsys, line, reason):
    conn = _directory()
    _population(conn)
    path = _csv(tmp_path, "user-ada,2027-09-08\n" + line)

    assert _run(conn, path, '--apply') == 2

    assert reason in capsys.readouterr().out
    assert _stored_end(conn, 'ada') != '2027-09-08T12:00:00'
    assert _groups_of(conn, 'ada') == set()


def test_an_ambiguous_pseudonym_aborts(tmp_path, capsys):
    conn = _directory()
    _add_member(conn, 'twin', shares=1, end=EXPIRED)
    _add_member(conn, 'other', shares=1, end=EXPIRED)
    conn.modify(member_dn('other'), {'cn': [(MODIFY_REPLACE, ['User-Twin'])]})

    assert _run(conn, _csv(tmp_path, "user-twin,2027-09-08\n"),
                '--apply') == 2
    assert "2 entries carry this pseudonym" in capsys.readouterr().out


def test_a_later_date_in_the_directory_is_kept(tmp_path, capsys):
    """A payment recorded since the list was drawn up is not undone."""
    conn = _directory()
    _add_member(conn, 'eve', shares=1, end=date(2028, 1, 15),
                groups=(COMMUNITY, COOPERATORS))
    path = _csv(tmp_path, "user-eve,2027-09-08\n")

    assert _run(conn, path, '--apply') == 0
    assert _stored_end(conn, 'eve') == '2028-01-15T00:00:00'
    assert "LATER date" in capsys.readouterr().out

    assert _run(conn, path, '--apply', '--allow-earlier') == 0
    assert _stored_end(conn, 'eve') == '2027-09-08T12:00:00'


def test_a_renewal_that_cannot_make_a_cooperator_is_pointed_out(
        tmp_path, capsys):
    """No share: the date is written, the member is NOT a Cooperator —
    the operator must be told, not left to discover it."""
    conn = _directory()
    _add_member(conn, 'fay', shares=0, end=EXPIRED)

    assert _run(conn, _csv(tmp_path, "user-fay,2027-09-08\n"),
                '--apply') == 0
    assert _groups_of(conn, 'fay') == {COMMUNITY, MISSING_SHARE}
    out = capsys.readouterr().out
    assert "will NOT be in cooperatorsGroup" in out
    assert "numberSharesOwned is 0 or absent" in out


def test_a_failed_convergence_is_a_failed_run(tmp_path, capsys):
    conn = _directory()
    _population(conn)
    members = tool.read_members(conn)
    dates, _reactivations, _moves, _notes = tool.build_plan(
        members, [('user-ada', date(2027, 9, 8))], today=TODAY)

    failures = tool.apply_plan(
        conn, members, dates,
        sync=lambda request, oid: None if oid == 'bob' else {COMMUNITY})

    assert failures == ["groups of bob (user-bob) did not converge"]


# ----------------------------- the reactivation ---------------------------- #
def _founders(conn):
    """The production state behind issue #272: founding members imported
    with ``isActive: FALSE`` and never activated — one renewed in the
    shop, one lapsed — next to a member who really resigned."""
    _add_member(conn, 'gus', active='FALSE', shares=25, end=EXPIRED)
    _add_member(conn, 'hal', active='FALSE', shares=5, end=EXPIRED)
    _add_member(conn, 'dee', active='False', shares=1, end=VALID)
    conn.modify(member_dn('dee'), {'dateErasureAllData': [
        (MODIFY_REPLACE, ['2027-01-01T12:00:00'])]})


def _is_active(conn, oid):
    conn.search(member_dn(oid), '(objectclass=*)', attributes=['isActive'])
    return str(dg.entry_values(conn.entries[0], 'isActive')[0])


def test_without_the_option_the_dormant_members_are_pointed_out(
        tmp_path, capsys):
    conn = _directory()
    _founders(conn)

    assert _run(conn, _csv(tmp_path, "user-gus,2027-09-08\n"),
                '--apply') == 0

    assert _is_active(conn, 'gus') == 'FALSE'
    assert _groups_of(conn, 'gus') == set()
    out = capsys.readouterr().out
    assert "2 member(s) are inactive without having resigned" in out
    assert "user-gus, user-hal" in out
    assert "never activated; see --reactivate" in out


def test_a_dry_run_lists_the_reactivations_and_writes_nothing(
        tmp_path, capsys):
    conn = _directory()
    _founders(conn)

    assert _run(conn, _csv(tmp_path, "user-gus,2027-09-08\n"),
                '--reactivate') == 0

    assert _is_active(conn, 'gus') == 'FALSE'
    out = capsys.readouterr().out
    assert "2 member(s) to reactivate" in out
    assert "2 member(s) whose groups move" in out
    assert "will NOT be in" not in out


def test_the_never_activated_come_back_and_the_resigned_do_not(
        tmp_path, capsys):
    conn = _directory()
    _founders(conn)

    assert _run(conn, _csv(tmp_path, "user-gus,2027-09-08\n"),
                '--reactivate', '--apply') == 0

    assert _is_active(conn, 'gus') == 'TRUE'
    assert _is_active(conn, 'hal') == 'TRUE'
    assert _groups_of(conn, 'gus') == {COMMUNITY, COOPERATORS}
    assert _groups_of(conn, 'hal') == {COMMUNITY, MISSING_YEAR}
    assert _is_active(conn, 'dee') == 'False'
    assert _groups_of(conn, 'dee') == set()
    assert "2 member(s) reactivated" in capsys.readouterr().out


def test_a_refused_reactivation_is_a_failure_and_grants_nothing():
    conn = _directory()
    _founders(conn)
    members = tool.read_members(conn)
    dates, reactivations, _moves, _notes = tool.build_plan(
        members, [('user-gus', date(2027, 9, 8))], today=TODAY,
        reactivate=True)
    synced = []

    with patch.object(conn, 'modify', return_value=False):
        failures = tool.apply_plan(
            conn, members, dates, reactivations,
            sync=lambda request, oid: synced.append(oid) or {COMMUNITY})

    assert len(failures) == 3  # one date, two reactivations
    assert synced == []
