from __future__ import annotations

from datetime import datetime

import pytest

from alirpunkto.models.member import (
    EmailEvent,
    EmailSendStatus,
    Member,
    MemberDataEvent,
    MemberDataFunctions,
    MemberDatas,
    MemberRoles,
    MemberStates,
    MemberTypes,
    Members,
    random_string,
)
from alirpunkto.models.permissions import Permissions


@pytest.mark.parametrize(
    "state, name_id, value_id",
    [
        (MemberStates.CREATED, "member_state_created_name", "member_state_created_value"),
        (MemberStates.DRAFT, "member_state_draft_name", "member_state_draft_value"),
        (MemberStates.REGISTRED, "member_state_registred_name", "member_state_registred_value"),
        (
            MemberStates.DATA_MODIFICATION_REQUESTED,
            "member_data_modification_request_name",
            "member_data_modification_request_value",
        ),
        (MemberStates.DATA_MODIFIED, "member_datas_modified_name", "member_datas_modified_value"),
        (MemberStates.EXCLUDED, "member_datas_excluded_name", "member_datas_excluded_value"),
        (MemberStates.DELETED, "member_datas_deleted_name", "member_datas_deleted_value"),
    ],
)
def test_member_state_i18n_ids(state, name_id, value_id):
    assert MemberStates.get_i18n_id(state.name) == name_id
    assert MemberStates.get_i18n_id(state.value) == value_id


def test_member_state_names_are_complete():
    assert set(MemberStates.get_names()) == {
        "CREATED",
        "DRAFT",
        "REGISTRED",
        "DATA_MODIFICATION_REQUESTED",
        "DATA_MODIFIED",
        "EXCLUDED",
        "DELETED",
    }


@pytest.mark.parametrize(
    "member_type, name_id, value_id",
    [
        (MemberTypes.ADMINISTRATOR, "member_types_administrator", "member_types_administrator_value"),
        (MemberTypes.ORDINARY, "member_types_ordinary", "member_types_ordinary_value"),
        (MemberTypes.COOPERATOR, "member_types_cooperator", "member_types_cooperator_value"),
        (MemberTypes.PROVIDER, "member_types_provider", "member_types_provider_value"),
    ],
)
def test_member_type_i18n_ids(member_type, name_id, value_id):
    assert MemberTypes.get_i18n_id(member_type.name) == name_id
    assert MemberTypes.get_i18n_id(member_type.value) == value_id


@pytest.mark.parametrize(
    "role, name_id, value_id",
    [
        (MemberRoles.NONE, "member_roles_none", "member_roles_none_value"),
        (MemberRoles.ORDINARY, "member_roles_ordinary", "member_roles_ordinary_value"),
        (MemberRoles.COOPERATOR, "member_roles_cooperator", "member_roles_cooperator_value"),
        (MemberRoles.BOARD, "member_roles_board", "member_roles_board_value"),
        (
            MemberRoles.MEDIATION_ARBITRATION_COUNCIL,
            "member_roles_mediation_arbitration_council",
            "member_roles_mediation_arbitration_council_value",
        ),
    ],
)
def test_member_role_i18n_ids(role, name_id, value_id):
    assert MemberRoles.get_i18n_id(role.name) == name_id
    assert MemberRoles.get_i18n_id(role.value) == value_id


@pytest.mark.parametrize(
    "permission, name_id, value_id",
    [
        (Permissions.NONE, "access_permissions_none", "access_permissions_none_value"),
        (Permissions.ACCESS, "access_permissions_access", "access_permissions_access_value"),
        (Permissions.READ, "access_permissions_read", "access_permissions_read_value"),
        (Permissions.WRITE, "access_permissions_write", "access_permissions_write_value"),
        (Permissions.EXECUTE, "access_permissions_execute", "access_permissions_execute_value"),
        (Permissions.CREATE, "access_permissions_create", "access_permissions_create_value"),
        (Permissions.DELETE, "access_permissions_delete", "access_permissions_delete_value"),
        (Permissions.TRAVERSE, "access_permissions_traverse", "access_permissions_traverse_value"),
        (Permissions.RENAME, "access_permissions_rename", "access_permissions_rename_value"),
        (
            Permissions.DELETE_CHILD,
            "access_permissions_delete_child",
            "access_permissions_delete_child_value",
        ),
        (Permissions.ADMIN, "access_permissions_admin", "access_permissions_admin_value"),
    ],
)
def test_permission_i18n_ids(permission, name_id, value_id):
    assert Permissions.get_i18n_id(permission.name) == name_id
    assert Permissions.get_i18n_id(permission.value) == value_id


def test_get_permissions_returns_enabled_bit_flags_only():
    combined = Permissions.ACCESS | Permissions.READ | Permissions.WRITE
    assert list(Permissions.get_permissions(combined)) == [
        Permissions.ACCESS,
        Permissions.READ,
        Permissions.WRITE,
    ]


def test_member_data_event_iteration_serializes_none_values():
    event = MemberDataEvent(
        datetime=datetime(2026, 1, 1, 12, 0, 0),
        function_name="field",
        value_before=None,
        value_after="new",
        seed="seed",
    )
    assert tuple(event) == (
        datetime(2026, 1, 1, 12, 0, 0),
        "field",
        "None",
        "new",
        "seed",
    )
    assert set(MemberDataEvent.get_field_names()) == {
        "datetime",
        "function_name",
        "value_before",
        "value_after",
        "seed",
    }


def test_email_event_helpers():
    event = EmailEvent(
        datetime=datetime(2026, 1, 1, 12, 0, 0),
        state=EmailSendStatus.SENT,
        function_name="register",
        seed="mail-seed",
    )
    assert dict(event.iter_attributes())["state"] is EmailSendStatus.SENT
    assert list(EmailEvent.get_field_names()) == [
        "datetime",
        "state",
        "function_name",
        "seed",
    ]


def test_member_datas_defaults_and_field_names():
    data = MemberDatas()
    assert data.is_active is True
    assert data.role is MemberRoles.NONE
    assert data.number_shares_owned == 0
    assert "cooperative_behaviour_mark" in set(MemberDatas.get_field_names())
    assert "date_erasure_all_data" in set(MemberDatas.get_field_names())


def test_members_singleton_uses_zodb_root(zodb_connection):
    members = Members.get_instance(connection=zodb_connection)
    assert members is Members.get_instance(connection=zodb_connection)
    assert zodb_connection.root.return_value["members"] is members


def test_member_setters_record_audit_events(monkeypatch):
    monkeypatch.setattr(MemberDataFunctions, "func_now", lambda: datetime(2026, 1, 1))
    member = Member(oid="member-1")

    member.email = "user@example.com"
    member.pseudonym = "user-one"
    member.type = MemberTypes.ORDINARY
    member.member_state = MemberStates.REGISTRED
    member.data = MemberDatas(description="Test user")

    assert member.email == "user@example.com"
    assert member.pseudonym == "user-one"
    assert member.type is MemberTypes.ORDINARY
    assert member.member_state is MemberStates.REGISTRED
    assert member.data.description == "Test user"
    assert [event.function_name for event in member.modifications[-5:]] == [
        "email",
        "pseudonym",
        "type",
        "member_state",
        "data",
    ]


@pytest.mark.parametrize(
    "attribute, value, message",
    [
        ("email", None, "email"),
        ("pseudonym", None, "pseudonym"),
        ("type", "ORDINARY", "type"),
        ("member_state", "DRAFT", "state"),
        ("data", {}, "MemberDatas"),
    ],
)
def test_member_setters_validate_types(attribute, value, message):
    member = Member(oid="member-1")
    with pytest.raises(TypeError, match=message):
        setattr(member, attribute, value)


def test_add_email_send_status_generates_then_reuses_email_seed(monkeypatch):
    monkeypatch.setattr(MemberDataFunctions, "func_now", lambda: datetime(2026, 1, 1))
    monkeypatch.setattr("alirpunkto.models.member.random_string", lambda length: "x" * length)
    member = Member(oid="member-1")

    member.add_email_send_status(EmailSendStatus.IN_PREPARATION, "register")
    member.add_email_send_status(EmailSendStatus.SENT, "register")

    history = member.email_send_status_history
    assert [event.state for event in history] == [
        EmailSendStatus.IN_PREPARATION,
        EmailSendStatus.SENT,
    ]
    assert history[0].seed == history[1].seed


def test_random_string_respects_length_and_alphabet():
    value = random_string(20, chars="ab")
    assert len(value) == 20
    assert set(value) <= {"a", "b"}
