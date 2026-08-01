"""Identity Recovery Code — LDAP provision (issue #127).

If a member's device is stolen with both the AlirPunkto credentials and
the e-mail account on it, the thief can fully usurp the identity. The
long-term answer is an Identity Recovery Code handed to the member at
registration; this module is the short-term provision: the LDAP
attribute ``identityRecoveryCode`` (declared in
``alirpunkto_schema.ldif``, deployable through
``tools/ldap_provision.py``) and the low-level helpers around it.

Design choice, documented for the future version: the ticket asks the
field to contain "a string of 64 characters" — which is exactly the
length of a SHA-256 hexadecimal digest. A recovery code is a secret on
par with a password, and this module therefore **never stores the code
itself**: the field carries the 64-character SHA-256 of its canonical
form, and verification is a constant-time comparison. The code handed
to the member is short enough to be copied reliably by hand — five
groups of five characters from an alphabet without ambiguous glyphs
(no 0/O, 1/I/L, U/V confusion) — and its canonical form ignores case,
spaces and hyphens, so a hand copy survives formatting.

No route, no view, no ``MemberDatas`` field and no form node: the
attribute is invisible to every member by construction until the
feature ships.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional

from ldap3 import MODIFY_REPLACE

from alirpunkto.constants_and_globals import (
    _,
    LDAP_BASE_DN,
    LDAP_OU,
    LDAP_PASSWORD,
    LDAP_USER,
    log,
)
from alirpunkto.ldap_factory import get_ldap_connection, schema_safe_attributes
from alirpunkto.secret_manager import get_secret

IDENTITY_RECOVERY_CODE_ATTRIBUTE = "identityRecoveryCode"

#: The stored value is a SHA-256 hex digest: exactly this many characters.
STORED_DIGEST_LENGTH = 64

#: Hand-copy friendly alphabet: no 0/O, no 1/I/L, no U (V confusion) —
#: thirty distinct glyphs.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTVWXYZ23456789"

#: Five groups of five characters: ~122 bits of entropy, still short
#: enough to copy by hand.
CODE_GROUPS = 5
CODE_GROUP_LENGTH = 5


def _member_dn(member_oid: str) -> str:
    return (f"uid={member_oid},{LDAP_OU},{LDAP_BASE_DN}"
            if LDAP_OU else f"uid={member_oid},{LDAP_BASE_DN}")


def generate_identity_recovery_code() -> str:
    """A fresh code, displayed as XXXXX-XXXXX-XXXXX-XXXXX-XXXXX."""
    groups = ["".join(secrets.choice(CODE_ALPHABET)
                      for _ in range(CODE_GROUP_LENGTH))
              for _ in range(CODE_GROUPS)]
    return "-".join(groups)


def canonical_code(code: str) -> str:
    """The form that gets hashed: case, spaces and hyphens are noise a
    hand copy may add or drop."""
    return "".join((code or "").upper().split()).replace("-", "")


def code_digest(code: str) -> str:
    """The 64-character value the directory stores."""
    return hashlib.sha256(canonical_code(code).encode("ascii",
                                                      "ignore")).hexdigest()


def store_identity_recovery_code(member_oid: str, code: str) -> dict:
    """Hash the code and store the digest; an empty code clears the field."""
    if code and len(canonical_code(code)) < 16:
        # A hand-typed code this short cannot carry enough entropy.
        return {'status': 'error', 'message': _('recovery_code_too_short')}
    value = [code_digest(code)] if code else []
    dn = _member_dn(member_oid)
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        try:
            if not conn.modify(dn, {IDENTITY_RECOVERY_CODE_ATTRIBUTE: [
                    (MODIFY_REPLACE, value)]}):
                log.error(f"store_identity_recovery_code: modify failed for "
                          f"{dn}: {conn.result}")
                return {'status': 'error', 'message': _('ldap_error_retry')}
        except Exception as e:
            log.error(f"store_identity_recovery_code: {e}")
            return {'status': 'error', 'message': _('ldap_error_retry')}
    log.info(f"Identity recovery digest updated for {member_oid}")
    return {'status': 'success'}


def read_identity_recovery_digest(member_oid: str) -> Optional[str]:
    """The stored 64-character digest of a member, or ``None``."""
    dn = _member_dn(member_oid)
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        attributes = schema_safe_attributes(
            conn, [IDENTITY_RECOVERY_CODE_ATTRIBUTE])
        if not attributes:
            return None
        try:
            if not conn.search(dn, '(objectClass=*)', search_scope='BASE',
                               attributes=attributes):
                return None
        except Exception as e:
            log.error(f"read_identity_recovery_digest: {e}")
            return None
        if not conn.entries:
            return None
        value = getattr(conn.entries[0], IDENTITY_RECOVERY_CODE_ATTRIBUTE,
                        None)
        return str(value) if value and str(value) else None


def verify_identity_recovery_code(member_oid: str, code: str) -> bool:
    """Constant-time check of a hand-typed code against the stored digest."""
    stored = read_identity_recovery_digest(member_oid)
    if not stored or not code:
        return False
    return hmac.compare_digest(code_digest(code), stored)
