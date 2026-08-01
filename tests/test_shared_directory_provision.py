"""The Shared Directory LDAP provision (issue #110, statutes §5.3.1).

Six attributes exist in the reference schema — five destination e-mail
slots and one ciphered personal-data block of fewer than 512 characters —
deployable through tools/ldap_provision.py, with low-level helpers to
fill, read and decipher them. No route, no view, no MemberDatas field:
the attributes are invisible to every member by construction; the
ciphered block provably fits the statutory bound even for a maximal
member.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from alirpunkto import shared_directory as sd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET = Fernet.generate_key().decode()

#: A deliberately maximal member: long names, twelve groups, every field.
MAXIMAL = {
    'forenames': 'Marie-Antoinette Joséphine Ghislaine Bernadette',
    'surnames': 'de La Rochefoucauld-Montmorency d\'Aubigné-Kergorlay',
    'birthdate': '1989-12-31',
    'nationality': 'FR',
    'pseudonym': 'marie.antoinette.de.la.rochefoucauld',
    'cooperator_number': '9f8e7d6c-5b4a-3210-fedc-ba9876543210',
    'cooperative_behaviour_mark': 4.87,
    'cooperative_behaviour_mark_update': '2026-07-31T23:59:59',
    'number_shares_owned': 1234,
    'date_end_validity_yearly_contribution': '2027-12-31',
    'role': 'MEDIATION_ARBITRATION_COUNCIL',
    'groups': ['communityMembersGroup', 'cooperatorsGroup',
               'candidatesMissingShareYearContribGroup',
               'candidatesMissingShareGroup',
               'candidatesMissingYearContribGroup', 'sanctionedGroup',
               'sanctionedMissingYearContribGroup', 'boardMembersGroup',
               'mediationArbitrationCouncilGroup',
               'suspendedBoardMembersGroup',
               'suspendedMediationArbitrationCouncilGroup',
               'ordinaryMembersGroup'],
}


# ------------------------------- the schema -------------------------------- #
def test_the_six_attributes_live_in_the_reference_schema():
    ldif = open(os.path.join(ROOT, 'alirpunkto', 'alirpunkto_schema.ldif'),
                encoding='utf-8').read()
    for i in range(1, 6):
        assert f"NAME 'eMailDestinationCooperator{i}'" in ldif
    assert "NAME 'cipheredPersonalData'" in ldif
    assert "1.3.6.1.4.1.1466.115.121.1.15{512}" in ldif
    # And the object class may carry them:
    for i in range(1, 6):
        assert f"eMailDestinationCooperator{i}" in ldif.split(
            "olcObjectClasses")[1]
    assert "cipheredPersonalData" in ldif.split("olcObjectClasses")[1]


# --------------------------- the ciphered block ---------------------------- #
def test_a_maximal_member_fits_the_statutory_bound():
    """The proof the 512-character bound is attainable: the worst
    realistic member — every field set, all twelve groups — stays under
    it, so the future version can rely on the provision."""
    token = sd.build_ciphered_personal_data(MAXIMAL, SECRET)
    assert len(token) < sd.MAX_CIPHERED_PERSONAL_DATA_LENGTH


def test_the_block_round_trips():
    token = sd.build_ciphered_personal_data(MAXIMAL, SECRET)
    assert sd.decipher_personal_data(token, SECRET) == MAXIMAL


def test_an_oversized_block_raises_instead_of_writing_garbage():
    import secrets
    # Random data defeats zlib: the block genuinely exceeds the bound.
    huge = dict(MAXIMAL, forenames=secrets.token_hex(400))
    with pytest.raises(ValueError):
        sd.build_ciphered_personal_data(huge, SECRET)


def test_a_tampered_or_foreign_token_deciphers_to_none():
    token = sd.build_ciphered_personal_data(MAXIMAL, SECRET)
    assert sd.decipher_personal_data(token[:-2] + 'xx', SECRET) is None
    other = Fernet.generate_key().decode()
    assert sd.decipher_personal_data(token, other) is None


# ------------------------- the destination e-mails ------------------------- #
def _connection(search_entries=None):
    conn = MagicMock()
    conn.modify.return_value = True
    conn.search.return_value = search_entries is not None
    conn.entries = search_entries or []
    conn.__enter__ = lambda self: self
    conn.__exit__ = lambda self, *a: False
    return conn


def test_the_sixth_address_is_refused():
    result = sd.set_destination_emails(
        'm-1', [f'c{i}@example.com' for i in range(6)])
    assert result['status'] == 'error'


def test_an_invalid_address_is_refused():
    with patch.object(sd, 'is_not_a_valid_email_address',
                      return_value={'error': 'invalid'}):
        result = sd.set_destination_emails('m-1', ['not-an-address'])
    assert result['status'] == 'error'


def test_the_list_is_the_whole_state():
    """Two addresses fill slots 1-2 and clear 3-5: no stale address ever
    survives in the directory."""
    conn = _connection()
    with patch.object(sd, 'get_ldap_connection', return_value=conn), \
         patch.object(sd, 'get_secret', return_value='x'), \
         patch.object(sd, 'is_not_a_valid_email_address',
                      return_value=None):
        result = sd.set_destination_emails(
            'm-1', ['a@example.com', 'b@example.com'])
    assert result['status'] == 'success'
    changes = conn.modify.call_args[0][1]
    assert changes['eMailDestinationCooperator1'][0][1] == ['a@example.com']
    assert changes['eMailDestinationCooperator2'][0][1] == ['b@example.com']
    for i in (3, 4, 5):
        assert changes[f'eMailDestinationCooperator{i}'][0][1] == []


def test_reading_returns_the_filled_slots_in_order():
    entry = MagicMock()
    entry.eMailDestinationCooperator1 = 'a@example.com'
    entry.eMailDestinationCooperator2 = 'b@example.com'
    entry.eMailDestinationCooperator3 = None
    entry.eMailDestinationCooperator4 = None
    entry.eMailDestinationCooperator5 = None
    conn = _connection([entry])
    with patch.object(sd, 'get_ldap_connection', return_value=conn), \
         patch.object(sd, 'get_secret', return_value='x'), \
         patch.object(sd, 'schema_safe_attributes',
                      side_effect=lambda c, a: a):
        emails = sd.get_destination_emails('m-1')
    assert emails == ['a@example.com', 'b@example.com']


# ------------------------------ invisibility ------------------------------- #
def test_the_attributes_never_reach_the_application_surface():
    """The ticket's visibility rule, by construction: no MemberDatas
    field, no form node, no view context ever names these attributes."""
    from alirpunkto.models.member import MemberDatas
    fields = set(MemberDatas.get_field_names())
    assert 'cipheredPersonalData' not in fields
    assert not any(f.startswith('eMailDestinationCooperator')
                   for f in fields)
    for source_file in ('schemas/register_form.py', 'views/modify_member.py'):
        source = open(os.path.join(ROOT, 'alirpunkto', source_file),
                      encoding='utf-8').read()
        assert 'cipheredPersonalData' not in source
        assert 'eMailDestinationCooperator' not in source
