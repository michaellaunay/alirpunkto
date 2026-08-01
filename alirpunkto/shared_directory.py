"""Shared Directory of Cooperators — LDAP provision (issue #110).

Statutes §5.3.1 foresee that each Cooperator keeps the e-mail addresses
of a few other Cooperators so the IT infrastructure can be rebuilt if
its servers are destroyed. The feature belongs to a later version; this
module is the provision: six LDAP attributes
(``eMailDestinationCooperator1``..``5`` and ``cipheredPersonalData``,
declared in ``alirpunkto_schema.ldif`` and deployable through
``tools/ldap_provision.py``) and the low-level helpers to fill, read and
decipher them. Deliberately no route, no view, no ``MemberDatas`` field
and no form node: the attributes are invisible to every member by
construction — only an administrator, through these helpers or direct
LDAP tooling, can reach them, mainly to test the future version.
"""
from __future__ import annotations

import json
import zlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
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
from alirpunkto.utils import is_not_a_valid_email_address

#: The five per-member destination addresses (statutes §5.3.1).
DESTINATION_EMAIL_ATTRIBUTES = tuple(
    f"eMailDestinationCooperator{i}" for i in range(1, 6))

CIPHERED_PERSONAL_DATA_ATTRIBUTE = "cipheredPersonalData"

#: Hard limit of the ticket: the ciphered block is one single value of
#: fewer than 512 characters.
MAX_CIPHERED_PERSONAL_DATA_LENGTH = 512


def _member_dn(member_oid: str) -> str:
    return (f"uid={member_oid},{LDAP_OU},{LDAP_BASE_DN}"
            if LDAP_OU else f"uid={member_oid},{LDAP_BASE_DN}")


# --------------------------- destination e-mails --------------------------- #
def set_destination_emails(member_oid: str, emails) -> dict:
    """Store up to five destination addresses; unused slots are cleared.

    The list is the whole state: passing two addresses fills slots 1-2 and
    empties 3-5, so the directory never keeps a stale address.
    """
    emails = [e.strip() for e in (emails or []) if e and e.strip()]
    if len(emails) > len(DESTINATION_EMAIL_ATTRIBUTES):
        return {'status': 'error', 'message': _('too_many_destination_emails')}
    for email in emails:
        if is_not_a_valid_email_address(email, check_mx=False):
            log.warning(
                f"set_destination_emails: invalid address for {member_oid}")
            return {'status': 'error', 'message': _('invalid_email')}
    changes = {}
    for slot, attribute in enumerate(DESTINATION_EMAIL_ATTRIBUTES):
        value = [emails[slot]] if slot < len(emails) else []
        changes[attribute] = [(MODIFY_REPLACE, value)]
    dn = _member_dn(member_oid)
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        try:
            if not conn.modify(dn, changes):
                log.error(f"set_destination_emails: modify failed for {dn}: "
                          f"{conn.result}")
                return {'status': 'error', 'message': _('ldap_error_retry')}
        except Exception as e:
            log.error(f"set_destination_emails: {e}")
            return {'status': 'error', 'message': _('ldap_error_retry')}
    log.info(f"Destination e-mails updated for {member_oid} "
             f"({len(emails)} slot(s) filled)")
    return {'status': 'success'}


def get_destination_emails(member_oid: str) -> list:
    """The filled destination addresses of a member, in slot order."""
    dn = _member_dn(member_oid)
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        attributes = schema_safe_attributes(
            conn, list(DESTINATION_EMAIL_ATTRIBUTES))
        if not attributes:
            return []
        try:
            if not conn.search(dn, '(objectClass=*)', search_scope='BASE',
                               attributes=attributes):
                return []
        except Exception as e:
            log.error(f"get_destination_emails: {e}")
            return []
        if not conn.entries:
            return []
        entry = conn.entries[0]
        emails = []
        for attribute in DESTINATION_EMAIL_ATTRIBUTES:
            value = getattr(entry, attribute, None)
            value = str(value) if value and str(value) else None
            if value:
                emails.append(value)
        return emails


# --------------------------- ciphered personal data ------------------------ #
_FIELD_ORDER = (
    ('fn', 'forenames'), ('sn', 'surnames'), ('bd', 'birthdate'),
    ('na', 'nationality'), ('ps', 'pseudonym'), ('nu', 'cooperator_number'),
    ('cb', 'cooperative_behaviour_mark'),
    ('cu', 'cooperative_behaviour_mark_update'),
    ('sh', 'number_shares_owned'),
    ('ct', 'date_end_validity_yearly_contribution'),
    ('ro', 'role'), ('gr', 'groups'),
)

#: The twelve verbose group names weigh ~520 JSON characters on their own —
#: more than the whole statutory bound. Stable two-letter codes keep the
#: block small; unknown names travel uncoded (robustness over compactness).
_GROUP_CODES = {
    'communityMembersGroup': 'cg',
    'cooperatorsGroup': 'co',
    'candidatesMissingShareYearContribGroup': 'cy',
    'candidatesMissingShareGroup': 'cs',
    'candidatesMissingYearContribGroup': 'cm',
    'sanctionedGroup': 'sa',
    'sanctionedMissingYearContribGroup': 'sm',
    'boardMembersGroup': 'bo',
    'mediationArbitrationCouncilGroup': 'ma',
    'suspendedBoardMembersGroup': 'sb',
    'suspendedMediationArbitrationCouncilGroup': 'su',
    'ordinaryMembersGroup': 'om',
}
_GROUP_NAMES = {code: name for name, code in _GROUP_CODES.items()}

_ROLE_CODES = {
    'NONE': 'no', 'ORDINARY': 'or', 'COOPERATOR': 'co', 'BOARD': 'bo',
    'MEDIATION_ARBITRATION_COUNCIL': 'ma',
}
_ROLE_NAMES = {code: name for name, code in _ROLE_CODES.items()}


def build_ciphered_personal_data(personal_data: dict, secret: str) -> str:
    """Cipher the §5.3.1 block: compact JSON → zlib → Fernet, < 512 chars.

    ``personal_data`` uses the long keys of ``_FIELD_ORDER`` (missing or
    ``None`` entries are omitted); dates must already be ISO strings. The
    ticket bounds the stored value to one block of fewer than 512
    characters — a longer result raises ``ValueError`` instead of writing
    a truncated, undecipherable value.
    """
    compact = {short: personal_data[long]
               for short, long in _FIELD_ORDER
               if personal_data.get(long) is not None}
    if 'gr' in compact:
        compact['gr'] = ','.join(
            _GROUP_CODES.get(name, name) for name in compact['gr'])
    if 'ro' in compact:
        compact['ro'] = _ROLE_CODES.get(compact['ro'], compact['ro'])
    payload = json.dumps(compact, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':')).encode('utf-8')
    token = Fernet(secret).encrypt(zlib.compress(payload, 9)).decode('ascii')
    if len(token) >= MAX_CIPHERED_PERSONAL_DATA_LENGTH:
        raise ValueError(
            f"ciphered personal data is {len(token)} characters; the "
            f"statutes bound it to fewer than "
            f"{MAX_CIPHERED_PERSONAL_DATA_LENGTH}")
    return token


def decipher_personal_data(token: str, secret: str) -> Optional[dict]:
    """Reverse of :func:`build_ciphered_personal_data`; ``None`` if invalid."""
    try:
        payload = zlib.decompress(Fernet(secret).decrypt(token.encode()))
        compact = json.loads(payload.decode('utf-8'))
    except (InvalidToken, zlib.error, ValueError):
        return None
    if 'gr' in compact:
        compact['gr'] = [_GROUP_NAMES.get(code, code)
                         for code in compact['gr'].split(',') if code]
    if 'ro' in compact:
        compact['ro'] = _ROLE_NAMES.get(compact['ro'], compact['ro'])
    return {long: compact[short]
            for short, long in _FIELD_ORDER if short in compact}


def store_ciphered_personal_data(member_oid: str, token: str) -> dict:
    """Write the ciphered block (or clear it with an empty token)."""
    if token and len(token) >= MAX_CIPHERED_PERSONAL_DATA_LENGTH:
        return {'status': 'error', 'message': _('ciphered_block_too_long')}
    dn = _member_dn(member_oid)
    value = [token] if token else []
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        try:
            if not conn.modify(dn, {CIPHERED_PERSONAL_DATA_ATTRIBUTE: [
                    (MODIFY_REPLACE, value)]}):
                log.error(f"store_ciphered_personal_data: modify failed for "
                          f"{dn}: {conn.result}")
                return {'status': 'error', 'message': _('ldap_error_retry')}
        except Exception as e:
            log.error(f"store_ciphered_personal_data: {e}")
            return {'status': 'error', 'message': _('ldap_error_retry')}
    return {'status': 'success'}


def read_ciphered_personal_data(member_oid: str) -> Optional[str]:
    """The stored ciphered block of a member, or ``None``."""
    dn = _member_dn(member_oid)
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        attributes = schema_safe_attributes(
            conn, [CIPHERED_PERSONAL_DATA_ATTRIBUTE])
        if not attributes:
            return None
        try:
            if not conn.search(dn, '(objectClass=*)', search_scope='BASE',
                               attributes=attributes):
                return None
        except Exception as e:
            log.error(f"read_ciphered_personal_data: {e}")
            return None
        if not conn.entries:
            return None
        value = getattr(conn.entries[0], CIPHERED_PERSONAL_DATA_ATTRIBUTE,
                        None)
        return str(value) if value and str(value) else None
