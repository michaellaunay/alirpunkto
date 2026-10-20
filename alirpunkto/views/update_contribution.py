"""Administrative update of a Cooperator's financial facts (issue #267).

Issue #75 made the number of shares and the end of validity of the yearly
contribution two directory attributes "updated by the online commercial
site via a Python script" — ``tools/update_cooperator.py``, which logged
an administrator in and drove the profile form of ``modify_member``. Then
issue #149 (confirmed by #249) made another member's profile a read-only
card for everyone, administrators included: the script's POST landed on
the card, nothing was written, and a Cooperator who had just paid kept
losing their rights (#267).

This view is the dedicated write path the script now uses. It is an API,
not a page: ``POST`` only, JSON in and out, the session of a logged-in
administrator and the CSRF token of that session required (Pyramid's
global ``require_csrf``). It accepts exactly the two facts of #75 — any
other profile field stays read-only, as #149 wants — writes them to the
directory, which moves the member between the Dynamic Groups of #148 and
propagates the change to Keycloak (#269), and answers with the member's
new groups so the caller can see the rights restored.
"""
from __future__ import annotations

import datetime
import json

from pyramid.view import view_config

from alirpunkto.constants_and_globals import (
    LDAP_DEFAULT_HOUR,
    LDAP_TIME_FORMAT,
    log,
)
from alirpunkto.models.member import MemberStates, MemberTypes
from alirpunkto.utils import (
    get_member_by_oid,
    update_ldap_member,
    update_member_from_ldap,
)

#: The only two fields this endpoint may write (issue #75).
SHARES_FIELD = 'number_shares_owned'
VALIDITY_FIELD = 'date_end_validity_yearly_contribution'
WRITABLE_FIELDS = (SHARES_FIELD, VALIDITY_FIELD)

#: Accepted date format of the validity field (the script's contract).
DATE_FORMAT = '%Y-%m-%d'


def _session_user(request):
    if not request.session.get('logged_in'):
        return None
    user = request.session.get('user')
    if isinstance(user, str):
        try:
            user = json.loads(user)
        except (TypeError, ValueError):
            return None
    return user if isinstance(user, dict) else None


def _refuse(request, status, error, **extra):
    request.response.status_code = status
    body = {'status': 'error', 'error': error}
    body.update(extra)
    return body


def parse_shares(raw):
    """A non-negative integer, or ValueError."""
    value = int(str(raw).strip())
    if value < 0:
        raise ValueError('negative')
    return value


def parse_validity_date(raw):
    """``YYYY-MM-DD`` as the datetime the directory stores (the LDAP
    default hour, like the profile form), or ValueError."""
    day = datetime.datetime.strptime(str(raw).strip(), DATE_FORMAT)
    return datetime.datetime.strptime(
        day.strftime(DATE_FORMAT) + LDAP_DEFAULT_HOUR, LDAP_TIME_FORMAT)


@view_config(route_name='update_contribution', renderer='json')
def update_contribution(request):
    """POST /update_contribution — body: ``oid`` plus ``number_shares_owned``
    and/or ``date_end_validity_yearly_contribution`` (``YYYY-MM-DD``)."""
    if request.method != 'POST':
        return _refuse(request, 405, 'method_not_allowed')
    user = _session_user(request)
    if user is None or not user.get('oid'):
        return _refuse(request, 401, 'not_logged_in')
    try:
        accessor = get_member_by_oid(user['oid'], request, True)
    except Exception as exc:
        log.error(f"update_contribution: cannot resolve the accessor "
                  f"{user.get('oid')}: {exc}")
        return _refuse(request, 503, 'ldap_error_retry')
    if accessor is None or accessor.type != MemberTypes.ADMINISTRATOR:
        log.warning(f"update_contribution: refused to non-administrator "
                    f"{user.get('oid')}")
        return _refuse(request, 403, 'administrator_required')

    oid = (request.POST.get('oid') or '').strip()
    if not oid:
        return _refuse(request, 400, 'missing_oid')
    updates = {}
    errors = {}
    if request.POST.get(SHARES_FIELD, '') != '':
        try:
            updates[SHARES_FIELD] = parse_shares(request.POST[SHARES_FIELD])
        except ValueError:
            errors[SHARES_FIELD] = 'expected a non-negative integer'
    if request.POST.get(VALIDITY_FIELD, '') != '':
        try:
            updates[VALIDITY_FIELD] = parse_validity_date(
                request.POST[VALIDITY_FIELD])
        except ValueError:
            errors[VALIDITY_FIELD] = f'expected {DATE_FORMAT}'
    if errors:
        return _refuse(request, 400, 'invalid_value', fields=errors)
    if not updates:
        return _refuse(request, 400, 'nothing_to_update',
                       accepted_fields=list(WRITABLE_FIELDS))

    try:
        member = update_member_from_ldap(oid, request)
    except Exception as exc:
        log.error(f"update_contribution: cannot load {oid}: {exc}")
        return _refuse(request, 503, 'ldap_error_retry')
    if member is None:
        return _refuse(request, 404, 'unknown_member')
    if member.type != MemberTypes.COOPERATOR:
        return _refuse(request, 409, 'not_a_cooperator',
                       member_type=getattr(member.type, 'name', None))

    fields_to_update = []
    for field, value in updates.items():
        if getattr(member.data, field, None) != value:
            setattr(member.data, field, value)
            fields_to_update.append(field)
    if fields_to_update:
        result = update_ldap_member(request, member,
                                    fields_to_update=fields_to_update)
        if not isinstance(result, dict) or result.get('status') != 'success':
            log.error(f"update_contribution: LDAP write failed for {oid}: "
                      f"{result}")
            return _refuse(request, 502, 'error_while_updating_member')
        member.member_state = MemberStates.DATA_MODIFIED
        log.info(f"update_contribution: {oid} updated by {accessor.oid}: "
                 f"{', '.join(fields_to_update)}")

    from alirpunkto.dynamic_groups import get_member_groups
    validity = member.data.date_end_validity_yearly_contribution
    return {
        'status': 'success',
        'oid': oid,
        'updated_fields': fields_to_update,
        SHARES_FIELD: member.data.number_shares_owned,
        VALIDITY_FIELD: validity.strftime(DATE_FORMAT) if validity else None,
        'groups': sorted(get_member_groups(oid)),
    }
