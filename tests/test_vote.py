"""Unit tests for ``alirpunkto.views.vote.vote_view`` (audit finding 2.3).

The most important behaviour under test is the persistence of a vote: a vote is
stored by mutating a plain ``Voter`` dataclass nested inside the persistent
``Candidature``. Because that mutation does not mark the candidature as changed,
ZODB must be told explicitly (``candidature._p_changed = True``) or the vote is
silently dropped on commit. The persistence tests therefore use a real
``FileStorage`` reopened from disk between phases -- a pooled connection would
keep the value in its in-memory cache and hide the bug.

The remaining tests cover the deadline gate, the resilience to a session that
lacks the display keys, and the LDAP-result handling on the approval path.
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import transaction
from ZODB import DB
from ZODB.FileStorage import FileStorage

from alirpunkto.constants_and_globals import _, SITE_NAME
from alirpunkto.models.candidature import (
    Candidature,
    CandidatureStates,
    Voter,
    VotingChoice,
)
from alirpunkto.models.member import MemberDatas
from alirpunkto.views import vote
from alirpunkto.views.vote import vote_view


# --------------------------------------------------------------------------- #
# request / wiring helpers
# --------------------------------------------------------------------------- #
class _Request:
    """Minimal stand-in for the pieces of the request vote_view touches."""

    def __init__(self, session, params, post, tm):
        self.session = session
        self.params = params
        self.POST = post
        self.tm = tm

    def route_url(self, name, **kw):
        return f"http://example.com/{name}"

    def current_route_url(self):
        return "http://example.com/vote"


def _request(oid, *, submit=False, vote_value=None, tm=None, session_extra=None):
    session = {"logged_in": True, "user": "{}", "oid": oid}
    if session_extra:
        session.update(session_extra)
    params = {"oid": oid}
    post = {}
    if submit:
        params["submit"] = "1"
        params["vote"] = vote_value
        post["vote"] = vote_value
    return _Request(session, params, post, tm if tm is not None else MagicMock())


_UNSET = object()


@contextmanager
def _wire(candidature, oid, *, voter_oid="voter-1", ldap_result=_UNSET):
    """Patch the collaborators vote_view resolves through the module namespace."""
    with ExitStack() as stack:
        stack.enter_context(
            patch.object(vote, "get_candidatures", return_value={oid: candidature})
        )
        user_cls = stack.enter_context(patch.object(vote, "User"))
        user_cls.from_json.return_value = SimpleNamespace(name="User", oid=voter_oid)
        stack.enter_context(
            patch.object(vote, "send_candidature_state_change_email", return_value=None)
        )
        if ldap_result is not _UNSET:
            stack.enter_context(
                patch.object(vote, "register_user_to_ldap", return_value=ldap_result)
            )
        yield


def _in_memory_candidature(voter_oids, *, state=CandidatureStates.PENDING):
    candidature = Candidature()
    candidature.data = MemberDatas(password="secret")
    candidature.candidature_state = state
    candidature.voters = [
        Voter(oid=o, email=f"{o}@example.com", pseudonym=o) for o in voter_oids
    ]
    return candidature


@contextmanager
def _zodb(path):
    storage = FileStorage(path)
    db = DB(storage)
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# persistence (real ZODB, reopened from disk)
# --------------------------------------------------------------------------- #
def test_vote_view_persists_vote_across_reopen(tmp_path, members_mapping):
    """A vote cast through vote_view must survive closing and reopening the DB."""
    path = str(tmp_path / "Data.fs")

    # Phase 1: persist a candidature with two voters, none of whom have voted.
    with _zodb(path) as db:
        tm = transaction.TransactionManager()
        conn = db.open(transaction_manager=tm)
        candidature = _in_memory_candidature(["voter-1", "voter-2"])
        conn.root()["cand"] = candidature
        oid = candidature.oid
        tm.commit()
        conn.close()

    # Phase 2: voter-1 votes YES through the actual view.
    with _zodb(path) as db:
        tm = transaction.TransactionManager()
        conn = db.open(transaction_manager=tm)
        candidature = conn.root()["cand"]
        request = _request(oid, submit=True, vote_value="YES", tm=tm)
        with _wire(candidature, oid, voter_oid="voter-1"):
            result = vote_view(request)
        assert result["registered_vote"] is True
        conn.close()

    # Phase 3: reopen a fresh DB from disk and check the vote was stored.
    with _zodb(path) as db:
        conn = db.open()
        candidature = conn.root()["cand"]
        stored = {v.oid: v.vote for v in candidature.voters}
        conn.close()

    assert stored["voter-1"] == "YES"
    assert stored["voter-2"] is None


def test_nested_voter_vote_requires_p_changed(tmp_path, members_mapping):
    """Document why the fix is needed: without _p_changed the vote is lost.

    Both arms mutate the same nested Voter and commit; only the arm that marks
    the candidature changed survives a reopen from disk.
    """
    path = str(tmp_path / "Data.fs")

    with _zodb(path) as db:
        tm = transaction.TransactionManager()
        conn = db.open(transaction_manager=tm)
        conn.root()["cand"] = _in_memory_candidature(["voter-1"])
        tm.commit()
        conn.close()

    # Arm A: mutate without _p_changed -> change is not written.
    with _zodb(path) as db:
        tm = transaction.TransactionManager()
        conn = db.open(transaction_manager=tm)
        conn.root()["cand"].voters[0].vote = "YES"  # no _p_changed
        tm.commit()
        conn.close()
    with _zodb(path) as db:
        conn = db.open()
        assert conn.root()["cand"].voters[0].vote is None
        conn.close()

    # Arm B: same mutation but marking the candidature changed -> persisted.
    with _zodb(path) as db:
        tm = transaction.TransactionManager()
        conn = db.open(transaction_manager=tm)
        candidature = conn.root()["cand"]
        candidature.voters[0].vote = "YES"
        candidature._p_changed = True
        tm.commit()
        conn.close()
    with _zodb(path) as db:
        conn = db.open()
        assert conn.root()["cand"].voters[0].vote == "YES"
        conn.close()


# --------------------------------------------------------------------------- #
# deadline gate
# --------------------------------------------------------------------------- #
def test_vote_view_blocks_after_deadline(members_mapping):
    candidature = _in_memory_candidature(["voter-1"])
    candidature.verification_deadline = datetime.now(timezone.utc) - timedelta(days=1)
    tm = MagicMock()
    request = _request(candidature.oid, tm=tm)

    with _wire(candidature, candidature.oid):
        result = vote_view(request)

    assert result["error"] == _("voting_period_ended")
    tm.commit.assert_not_called()


def test_vote_view_allows_before_deadline(members_mapping):
    candidature = _in_memory_candidature(["voter-1"])
    candidature.verification_deadline = datetime.now(timezone.utc) + timedelta(days=1)
    request = _request(candidature.oid)

    with _wire(candidature, candidature.oid):
        result = vote_view(request)

    assert "error" not in result
    assert result["registered_vote"] is False


def test_vote_view_allows_when_no_deadline(members_mapping):
    candidature = _in_memory_candidature(["voter-1"])  # no verification_deadline
    request = _request(candidature.oid)

    with _wire(candidature, candidature.oid):
        result = vote_view(request)

    assert "error" not in result
    assert result["registered_vote"] is False


# --------------------------------------------------------------------------- #
# session resilience
# --------------------------------------------------------------------------- #
def test_vote_view_falls_back_to_global_display_settings(members_mapping):
    """A session lacking site_name/domain_name/organization_details must not raise."""
    candidature = _in_memory_candidature(["voter-1"])
    request = _request(candidature.oid)  # session has no display keys

    with _wire(candidature, candidature.oid):
        result = vote_view(request)

    assert result["site_name"] == SITE_NAME


# --------------------------------------------------------------------------- #
# approval path: LDAP result handling
# --------------------------------------------------------------------------- #
def test_vote_view_approves_when_ldap_registration_succeeds(members_mapping):
    candidature = _in_memory_candidature(["voter-1"])
    request = _request(candidature.oid, submit=True, vote_value="YES")

    with _wire(candidature, candidature.oid, ldap_result={"status": "success"}):
        result = vote_view(request)

    assert candidature.candidature_state is CandidatureStates.APPROVED
    assert result["registered_vote"] is True


def test_vote_view_keeps_state_pending_when_ldap_registration_fails(members_mapping):
    candidature = _in_memory_candidature(["voter-1"])
    tm = MagicMock()
    request = _request(candidature.oid, submit=True, vote_value="YES", tm=tm)

    with _wire(candidature, candidature.oid, ldap_result={"status": "error"}):
        result = vote_view(request)

    assert candidature.candidature_state is CandidatureStates.PENDING
    assert result["error"] == _("registration_failed")
    tm.abort.assert_called()


def test_vote_view_keeps_state_pending_when_ldap_returns_non_dict(members_mapping):
    candidature = _in_memory_candidature(["voter-1"])
    tm = MagicMock()
    request = _request(candidature.oid, submit=True, vote_value="YES", tm=tm)

    with _wire(candidature, candidature.oid, ldap_result=None):
        result = vote_view(request)

    assert candidature.candidature_state is CandidatureStates.PENDING
    tm.abort.assert_called()


def test_vote_view_rejects_invalid_choice(members_mapping):
    candidature = _in_memory_candidature(["voter-1"])
    request = _request(candidature.oid, submit=True, vote_value="MAYBE")

    with _wire(candidature, candidature.oid):
        result = vote_view(request)

    assert result["error"] == _("Invalid voting choice!")
    # the bogus choice must not have been recorded
    assert all(v.vote is None for v in candidature.voters)
