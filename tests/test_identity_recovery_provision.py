"""The Identity Recovery Code LDAP provision (issue #127).

The short-term ask: an ``identityRecoveryCode`` field containing a
string of 64 characters. Sixty-four is exactly a SHA-256 hex digest, and
a recovery code is a secret on par with a password — so the field stores
the digest of the code's canonical form, never the code itself. The code
handed to the member is five hand-copyable groups of five unambiguous
characters; canonicalisation forgives case, spaces and hyphens; and
verification is constant-time. No route, no view, no MemberDatas field:
invisible by construction until the feature ships.
"""
from __future__ import annotations

import os
import re
from unittest.mock import MagicMock, patch


from alirpunkto import identity_recovery as ir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------- the schema -------------------------------- #
def test_the_attribute_lives_in_the_reference_schema():
    ldif = open(os.path.join(ROOT, 'alirpunkto', 'alirpunkto_schema.ldif'),
                encoding='utf-8').read()
    assert "NAME 'identityRecoveryCode'" in ldif
    assert "1.3.6.1.4.1.1466.115.121.1.15{64}" in ldif
    assert "identityRecoveryCode" in ldif.split("olcObjectClasses")[1]


# -------------------------------- the code --------------------------------- #
def test_the_generated_code_is_hand_copyable():
    code = ir.generate_identity_recovery_code()
    assert re.fullmatch(r"([A-Z2-9]{5}-){4}[A-Z2-9]{5}", code)
    for forbidden in "0O1ILU":
        assert forbidden not in code
    assert set(ir.canonical_code(code)) <= set(ir.CODE_ALPHABET)


def test_two_codes_never_collide():
    codes = {ir.generate_identity_recovery_code() for _ in range(64)}
    assert len(codes) == 64


def test_the_stored_value_is_exactly_the_ticket_64_characters():
    """The ticket's letter: the field contains a string of 64
    characters — the SHA-256 hex digest of the canonical code."""
    code = ir.generate_identity_recovery_code()
    digest = ir.code_digest(code)
    assert len(digest) == ir.STORED_DIGEST_LENGTH == 64
    assert re.fullmatch(r"[0-9a-f]{64}", digest)


def test_a_hand_copy_survives_formatting():
    """Case, spaces and hyphens are exactly what a hand copy mangles."""
    code = "ABCDE-FGHJK-MNPQR-STVWX-YZ234"
    sloppy = "  abcde fghjk-MNPQR stvwx-yz234 "
    assert ir.code_digest(sloppy) == ir.code_digest(code)


def test_verification_accepts_the_right_code_and_refuses_others():
    code = ir.generate_identity_recovery_code()
    stored = ir.code_digest(code)
    with patch.object(ir, 'read_identity_recovery_digest',
                      return_value=stored):
        assert ir.verify_identity_recovery_code('m-1', code.lower())
        assert not ir.verify_identity_recovery_code(
            'm-1', ir.generate_identity_recovery_code())
        assert not ir.verify_identity_recovery_code('m-1', '')


def test_the_comparison_is_constant_time():
    source = open(os.path.join(ROOT, 'alirpunkto', 'identity_recovery.py'),
                  encoding='utf-8').read()
    assert "hmac.compare_digest" in source


# ------------------------------- the storage ------------------------------- #
def _connection():
    conn = MagicMock()
    conn.modify.return_value = True
    conn.__enter__ = lambda self: self
    conn.__exit__ = lambda self, *a: False
    return conn


def test_storing_writes_the_digest_never_the_code():
    code = ir.generate_identity_recovery_code()
    conn = _connection()
    with patch.object(ir, 'get_ldap_connection', return_value=conn), \
         patch.object(ir, 'get_secret', return_value='x'):
        result = ir.store_identity_recovery_code('m-1', code)
    assert result['status'] == 'success'
    written = conn.modify.call_args[0][1][
        ir.IDENTITY_RECOVERY_CODE_ATTRIBUTE][0][1]
    assert written == [ir.code_digest(code)]
    assert ir.canonical_code(code) not in written[0]


def test_a_too_short_code_is_refused():
    result = ir.store_identity_recovery_code('m-1', 'ABCDE-FGHJK')
    assert result['status'] == 'error'


# ------------------------------ invisibility ------------------------------- #
def test_the_attribute_never_reaches_the_application_surface():
    from alirpunkto.models.member import MemberDatas
    assert 'identityRecoveryCode' not in set(MemberDatas.get_field_names())
    for source_file in ('schemas/register_form.py', 'views/modify_member.py'):
        source = open(os.path.join(ROOT, 'alirpunkto', source_file),
                      encoding='utf-8').read()
        assert 'identityRecoveryCode' not in source
