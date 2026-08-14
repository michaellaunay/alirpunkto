# description: modify member view
# author: Michaël Launay
# date: 2024-04-19

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
import datetime
from alirpunkto.utils import (
    switch_request_language,
    get_member_by_oid,
    is_valid_password,
    is_valid_email,
    update_member_from_ldap,
    update_ldap_member,
    update_member_password,
    send_check_new_email,
    get_ldap_member_list,
)

from alirpunkto.models.member import (
    MemberStates,
    MemberTypes,
    EmailSendStatus,
    MemberDatas,
)
from alirpunkto.constants_and_globals import (
    _,
    log,
    ADMIN_EMAIL,
    CANDIDATURE_OID,
    MEMBER_OID,
    ACCESSED_MEMBER_OID,
    LDAP_TIME_FORMAT,
    LDAP_TIME_LENGTH,
    LDAP_DATE_LENGTH,
    LDAP_DEFAULT_HOUR,
)
from alirpunkto.schemas.register_form import RegisterForm
from pyramid.i18n import Translator
import deform
from alirpunkto.models.permissions import Permissions
from alirpunkto.models.model_permissions import (
    get_access_permissions
)
from dataclasses import fields
import json
from typing import get_type_hints


# Resolved declared types of the MemberDatas fields. The modify form submits
# every value as a string, so these are used to coerce values to the model's
# expected types (e.g. number_shares_owned -> int, cooperative_behaviour_mark
# -> float, is_active -> bool) before they are stored.
_MEMBER_DATA_FIELD_TYPES = get_type_hints(MemberDatas)


def _coerce_member_data_value(field, raw):
    """Cast a raw form value to the declared type of ``field``.

    Only the scalar non-string types the form can submit as plain strings are
    converted (bool, int, float). String fields are returned unchanged and date
    fields are handled earlier via ``date_parameters``. Raises ValueError or
    TypeError on an invalid value so the caller can report it to the user.
    """
    if not isinstance(raw, str):
        return raw
    target = _MEMBER_DATA_FIELD_TYPES.get(field)
    if target is bool:
        return raw.strip().lower() in ("true", "1", "yes", "on")
    if target is int:
        return int(raw)
    if target is float:
        return float(raw)
    return raw


#: Translated labels of the dynamic groups (issue #55); unknown group
#: names fall back to their raw cn in the template.
GROUP_LABEL_MSGIDS = {
    'communityMembersGroup': 'group_label_community',
    'candidatesMissingShareYearContribGroup':
        'group_label_missing_share_year',
    'candidatesMissingShareGroup': 'group_label_missing_share',
    'candidatesMissingYearContribGroup': 'group_label_missing_year',
    'cooperatorsGroup': 'group_label_cooperators',
    'sanctionedGroup': 'group_label_sanctioned',
    'sanctionedMissingYearContribGroup':
        'group_label_sanctioned_missing_year',
    'boardMembersGroup': 'group_label_board',
    'mediationArbitrationCouncilGroup': 'group_label_mac',
    'suspendedBoardMembersGroup': 'group_label_suspended_board',
    'suspendedMediationArbitrationCouncilGroup':
        'group_label_suspended_mac',
    'ordinaryMembersGroup': 'group_label_legacy_ordinary',
}


def _own_member_panel(request, member):
    """The read-only facts of one's own profile that live outside the form
    (issue #55): the groups the member belongs to, and — for a Cooperator
    or assimilated — the role in the Cooperative."""
    from alirpunkto.dynamic_groups import get_member_groups
    from alirpunkto.models.member import MemberRoles
    try:
        groups = sorted(get_member_groups(member.oid))
    except Exception:
        groups = []
    panel = {
        'groups': [(name, GROUP_LABEL_MSGIDS.get(name)) for name in groups],
        'role_i18n': None,
    }
    if member.type == MemberTypes.COOPERATOR:
        role = getattr(getattr(member, 'data', None), 'role', None)
        role_name = getattr(role, 'name', role) or MemberRoles.NONE.name
        try:
            panel['role_i18n'] = MemberRoles.get_i18n_id(role_name) or \
                "member_roles_none"
        except Exception:
            panel['role_i18n'] = "member_roles_none"
    return panel


def _admin_member_card(request, accessed_member, full=True):
    """The fixed, read-only member card (issues #149/#249).

    full=True (administrators): the eight #149 fields plus the e-mail
    address. full=False (any member, issue #249): the public fields
    only — pseudonym, Cooperative Behaviour Mark and its update date.
    """
    from alirpunkto.models.member import MemberRoles
    from alirpunkto.views.avatar import get_member_avatar
    data = getattr(accessed_member, 'data', None)
    role = getattr(data, 'role', None)
    role_name = getattr(role, 'name', role) or MemberRoles.NONE.name
    try:
        role_i18n = MemberRoles.get_i18n_id(role_name) or \
            "member_roles_none"
    except Exception:
        role_i18n = "member_roles_none"
    try:
        has_avatar = bool(get_member_avatar(request, accessed_member.oid))
    except Exception:
        has_avatar = False
    if not full:
        return {
            'oid': accessed_member.oid,
            'pseudonym': getattr(accessed_member, 'pseudonym', None),
            'cooperative_behaviour_mark':
                getattr(data, 'cooperative_behaviour_mark', None),
            'cooperative_behaviour_mark_update':
                getattr(data, 'cooperative_behaviour_mark_update', None),
            'has_avatar': has_avatar,
        }
    return {
        'email': getattr(accessed_member, 'email', None),
        'oid': accessed_member.oid,
        'pseudonym': getattr(accessed_member, 'pseudonym', None),
        'description': getattr(data, 'description', None),
        'role_i18n': role_i18n,
        'cooperative_behaviour_mark':
            getattr(data, 'cooperative_behaviour_mark', None),
        'cooperative_behaviour_mark_update':
            getattr(data, 'cooperative_behaviour_mark_update', None),
        'departure_date': getattr(accessed_member, 'departure_date', None),
        'departure_reason': getattr(accessed_member, 'departure_reason',
                                    None),
        'has_avatar': has_avatar,
    }


@view_config(
    route_name='modify_member',
    renderer='alirpunkto:templates/modify_member.pt'
)
def modify_member(request):
    """Modify member view.
    get the accessed member oid and show form to modify accessed member datas.
    
    Args:
        request (pyramid.request.Request): the request
    """
    log.debug(f"modify_member: {request.method} {request.url}")
    if 'cancel' in request.POST:
        # Issue #123 / #116: abandon the edits — redirect to a fresh GET of
        # one's profile (post/redirect/get), before any LDAP work.
        return HTTPFound(location=request.route_url('modify_member'))
    member = None
    accessed_member_oid = None
    form = None
    appstruct = None
    schema = None
    message = None
    error = None
    logged_in = request.session.get('logged_in', False)
    session_user = request.session.get("user")
    if not logged_in or not session_user:
        log.info("modify_member: session expired or user not logged in")
        request.session['logged_in'] = False
        request.session.pop('user', None)
        request.session.flash(_('user_not_logged_in'), 'error')
        return HTTPFound(location=request.route_url('home'))

    if isinstance(session_user, dict):
        user_data = session_user
    else:
        try:
            user_data = json.loads(session_user)
        except (TypeError, json.JSONDecodeError):
            log.warning("modify_member: unable to decode user session payload, redirecting to home")
            request.session['logged_in'] = False
            request.session.pop('user', None)
            request.session.flash(_('user_not_logged_in'), 'error')
            return HTTPFound(location=request.route_url('home'))

    oid = (request.session.get(CANDIDATURE_OID, None)
        or request.session.get(MEMBER_OID, None))
    if not oid:
        oid = user_data.get("oid")
    if oid:
        # Any LDAP hiccup here used to escape as a bare 500 (issue #202);
        # answer with the same retryable error as the selection path below.
        try:
            member = get_member_by_oid(oid, request, True)
            if not member:
                member = update_member_from_ldap(oid, request)
        except Exception as e:
            log.error(f"modify_member: failed to resolve the accessor {oid}: {e}")
            return {
                "form": None,
                "member": None,
                "accessed_member": None,
                "accessed_members": {},
                "error": _('ldap_error_retry'),
            }
        if not member:
            return {
                "form": None,
                "member": None,
                "accessed_member": None,
                "accessed_members": {},
                "error": _('unknown_member'),
            }
    else:
        return {
            "form": None,
            "member": None,
            "accessed_member": None,
            "accessed_members": [],
            "error": _('unknown_member'),
        }
    # The member is known and will be recognized as the accessor.
    # Issue #249 supersedes the #201 restriction: every logged-in member
    # may browse the directory and open another member's card — the card
    # content, not the list, is what the accessor's role scopes.
    is_admin = member.type == MemberTypes.ADMINISTRATOR
    try:
        ldap_members = get_ldap_member_list()
    except Exception as e:
        log.error(f"modify_member: failed to list the members from LDAP: {e}")
        return {
            "form": None,
            "member": member,
            "accessed_member": None,
            "accessed_members": {},
            "error": _('ldap_error_retry'),
        }
    members = {user.oid:user.name for user in ldap_members}
    accessor_member = member
    # Issue #258: redirects (e.g. after an avatar upload rejection) need
    # a GET route straight to one's own edit form — ?self=1 provides it,
    # so the flash lands on the profile page, not on the directory.
    wants_self = request.method == 'GET' and 'self' in request.params
    if "submit" in request.POST or 'modify' in request.POST or wants_self:
        if wants_self:
            accessed_member_oid = member.oid
        elif "submit" in request.POST:
            accessed_member_oid = request.POST.get(ACCESSED_MEMBER_OID, None)
        elif 'modify' in request.POST:
            # Issue #249: without an armed session, the 'modify' POST is
            # the save of one's OWN form — never someone else's.
            accessed_member_oid = (request.session[ACCESSED_MEMBER_OID]
                if ACCESSED_MEMBER_OID in request.session
                else member.oid)
        if not accessed_member_oid:
            return {
                "form": None,
                "member": member,
                "accessed_member": None,
                "accessed_members": members,
                "error": _('unknown_accessed_member'),
            }
        # Update the accessed member from the ldap
        try:
            accessed_member = update_member_from_ldap(accessed_member_oid, request)
        except Exception as e:
            log.error(f"Failed to fetch accessed_member {accessed_member_oid}: {e}")
            return {
                "form": None,
                "member": member,
                "accessed_member": None,
                "accessed_members": members,
                "error": _('ldap_error_retry'),
            }
        if not accessed_member:
            log.error(f'No consistency ldap entry for {accessed_member_oid}')
            return {
                "form": None,
                "member": member,
                "accessed_member": None,
                "accessed_members": members,
                "error": _('unknown_accessed_member')
            }
        if accessed_member.oid != member.oid:
            # Issues #149/#249: someone else's profile is a fixed read-only
            # card — never the modification form, and the visit neither
            # flips the member's state nor arms the session for a later
            # 'modify' POST. The accessor's role scopes the card: members
            # see the public fields, administrators the full card.
            return {
                "form": None,
                "member": member,
                "accessed_member": accessed_member.oid,
                "accessed_members": members,
                "admin_view": _admin_member_card(
                    request, accessed_member, full=is_admin),
            }
        # Memorize the moddification request — but never clobber a running
        # resignation (issue #201 made plain GETs land here, and the
        # unsubscription flow relies on PENDING_UNSUBSCRIPTION surviving a
        # profile visit).
        if accessed_member.member_state in (
                MemberStates.PENDING_UNSUBSCRIPTION,
                MemberStates.UNSUBSCRIBED):
            if ACCESSED_MEMBER_OID not in request.session:
                request.session[ACCESSED_MEMBER_OID] = accessed_member.oid
        elif accessed_member.member_state != MemberStates.DATA_MODIFICATION_REQUESTED:
            request.session[ACCESSED_MEMBER_OID] = accessed_member.oid
            accessed_member.member_state = MemberStates.DATA_MODIFICATION_REQUESTED
        elif ACCESSED_MEMBER_OID not in request.session:
            request.session[ACCESSED_MEMBER_OID] = accessed_member.oid
        permissions = get_access_permissions(accessed_member, accessor_member)
        if not permissions or permissions == Permissions.NONE:
            log.warning(
                f'No permission to access member datas: {accessed_member_oid}'
            )
            request.session.flash(_('no_permission'), 'error')
            return {
                "member": None,
                "form": None,
                "accessed_members": members,
                "error":_('no_permission'),
            }
        schema = RegisterForm().bind(request=request, password_optional=True)
        # The permissions don't have the same structure as the schema,
        # so we need to apply permissions.data and permissions to the schema.
        schema.apply_permissions(permissions.data)
        schema.apply_permissions(permissions)
    # Issue #249: the pre-filled edit form only makes sense right after a
    # selection landed on oneself ("submit"); a plain GET now falls
    # through to the directory below, and the 'modify' POST keeps its
    # own saving branch.
    if "submit" in request.POST or wants_self:
        appstruct = {
            'accessed_member': accessed_member,
            'cooperative_number': accessed_member.oid,
            'email': accessed_member.email,
            'pseudonym': accessed_member.pseudonym,
            'fullname': accessed_member.data.fullname,
            'fullsurname': accessed_member.data.fullsurname,
            'description': accessed_member.data.description,
            'birthdate': accessed_member.data.birthdate,
            'nationality': accessed_member.data.nationality,
            'lang1': accessed_member.data.lang1,
            'lang2': accessed_member.data.lang2,
            'lang3': accessed_member.data.lang3,
            'cooperative_behaviour_mark': accessed_member.data.cooperative_behaviour_mark,
            'cooperative_behaviour_mark_update': accessed_member.data.cooperative_behaviour_mark_update,
            'number_shares_owned': accessed_member.data.number_shares_owned,
            'date_end_validity_yearly_contribution': accessed_member.data.date_end_validity_yearly_contribution,
            'iban': accessed_member.data.iban,
            #'date_erasure_all_data': accessed_member.data.date_erasure_all_data #TODO
        }
        # Issue #123: a translated Submit and a Cancel button (issue #116)
        # — the submit keeps its historical name 'modify' so the POST
        # branch below is untouched.
        form = deform.Form(schema,
            buttons=(
                deform.Button('modify', title=_('submit_button')),
                deform.Button('cancel', title=_('cancel_button')),
            ),
            translator=Translator
        )
        return {
            "form": form.render(appstruct=appstruct) if form else None,
            "member": member,
            "accessed_members": {},
            "accessed_member": accessed_member.oid,
            "own_view": _own_member_panel(request, member)
                if accessed_member.oid == member.oid else None,
        }
    elif 'modify' in request.POST and oid and member:
        # check if the member data field is writable before assignement
        writable_fields = [
            permission.name
            for permission in fields(permissions.data)
            if (
                    getattr(permissions.data, permission.name)
                    & (Permissions.WRITE | Permissions.ACCESS)
                ) == (Permissions.WRITE | Permissions.ACCESS)
        ]
        writable_fields.extend([
            permission.name
            for permission in fields(permissions)
            if (
                    permission.name != 'data'
                    and (getattr(permissions, permission.name)
                    & (Permissions.WRITE | Permissions.ACCESS))
                ) == (Permissions.WRITE | Permissions.ACCESS)
        ])
        err = None
        fields_to_update = []
    
        #manage dform date fields
        date_parameters = {}
        iterator = iter(request.params.items())
        for key, value in iterator:
            if key == '__start__':
                current_key = value.split(':')[0]  # remove ':mapping' from dform date field
                date_value = None
                # We move forward until we find 'date' then '__end__'
                for k, v in iterator:
                    if k == 'date':
                        try:
                            # For the moment we take only the last date value
                            # Format date as YYYYMMDDHHMMSSZ
                            date_value = datetime.datetime.strptime(
                                v[:LDAP_TIME_LENGTH] if len(v) >= LDAP_TIME_LENGTH else (v[:LDAP_DATE_LENGTH]+LDAP_DEFAULT_HOUR),
                                LDAP_TIME_FORMAT
                                )
                        except ValueError as e:
                            log.error(f"Error while parsing date {v}: {e}")
                            request.session.flash(_('invalid_date_format'), 'error')
                            return {
                                "member": member,
                                "accessed_members": {},
                                "accessed_member": accessed_member.oid,
                                "form": form.render(appstruct=appstruct) if form else None,
                                "error": _('invalid_date'),
                            }
                    elif k == '__end__':
                        break
                date_parameters[current_key] = date_value

        #restrict the writable fields to the granted before update it
        for field in writable_fields:
            if (
                field in request.POST 
                and request.POST[field]
                and (
                    request.POST[field] != getattr(
                        accessed_member.data, field, NotImplemented)
                    or request.POST[field] != getattr(
                        accessed_member, field, NotImplemented)
                )) or field in date_parameters:
                if (
                    field == "email" and accessed_member_oid == member.oid and
                    "email" in request.POST and "email" in writable_fields
                ):
                    email = request.POST['email']
                    if email != accessed_member.email:
                        err = is_valid_email(email, request)
                        if err:
                            request.session.flash(err, 'error')
                            return {
                                "member": member,
                                "accessed_members": {},
                                "accessed_member": accessed_member.oid,
                                "form": form.render(appstruct=appstruct) if form else None,
                                "error":err,
                                }
                        accessed_member.new_email = email
                        email_template = "check_new_email"
                        accessed_member.add_email_send_status(
                            EmailSendStatus.IN_PREPARATION, 
                            email_template
                        )
                        sending_success = send_check_new_email(
                            request,
                            accessed_member,
                            email
                        )
                        if not sending_success:
                            accessed_member.add_email_send_status(
                                EmailSendStatus.ERROR,
                                email_template
                            )                           
                            return {
                                "message":_('check_new_email_send_error'),
                                "member": member,
                                "accessed_member": accessed_member,
                                "accessed_members": {},
                                "form": form.render(appstruct=appstruct) if form else None,
                            }
                        try:
                            accessed_member.add_email_send_status(
                                EmailSendStatus.SENT,
                                email_template
                            )
                            message = _('check_new_email_send')
                        except Exception as e:
                            log.error(
                                f"Error while reset password {member.oid} : {e}"
                            )
                            accessed_member.add_email_send_status(
                                EmailSendStatus.ERROR,
                                email_template
                            )
                            # message is left with error because we can't
                            # use the error message as it could be overridden
                            message = _('forget_email_send_error',
                                         {'administrator': ADMIN_EMAIL})
                elif "password" in request.POST and "password" in writable_fields:
                    password = request.params['password'] if 'password' in request.params else None
                    password_confirm = request.params['password_confirm'] if 'password_confirm' in request.params else None
                    if password != password_confirm:
                        request.session.flash(_('password_not_match'), 'error')
                        return {
                            "member": member,
                            "accessed_members": {},
                            "accessed_member": accessed_member.oid,
                            "form": form.render(appstruct=appstruct) if form else None,
                            "error":_('password_not_match'),
                        }
                    if password == "":
                        request.session.flash(_('password_required'), 'error')
                        return {
                            "member": member,
                            "accessed_members": {},
                            "accessed_member": accessed_member.oid,
                            "form": form.render(appstruct=appstruct) if form else None,
                            "error":_('password_required'),
                        }
                    err = is_valid_password(password)
                    if err:
                        request.session.flash(err['error'], 'error')
                        return {
                            "member": member,
                            "accessed_members": {},
                            "accessed_member": accessed_member.oid,
                            "form": form.render(appstruct=appstruct) if form else None,
                            "error": err['error'],
                        }
                    password_result = update_member_password(
                        request, accessed_member.oid, password
                    )
                    if not password_result or password_result.get('status') != 'success':
                        return {
                            "member": member,
                            "accessed_members": {},
                            "accessed_member": accessed_member.oid,
                            "form": form.render(appstruct=appstruct) if form else None,
                            "error": _('password_update_failed'),
                        }
                else:
                    requested_value = request.POST[field] if field not in date_parameters else date_parameters[field]
                    # Coerce the form string to the field's declared type before
                    # storing it (date fields already arrive typed via
                    # date_parameters and are left untouched).
                    if field not in date_parameters:
                        try:
                            requested_value = _coerce_member_data_value(
                                field, requested_value
                            )
                        except (ValueError, TypeError):
                            log.error(
                                f"Invalid value {request.POST[field]!r} for "
                                f"field {field}"
                            )
                            error = _('invalid_field_value',
                                mapping={'field': field})
                            request.session.flash(error, 'error')
                            return {
                                "member": member,
                                "accessed_members": members,
                                "accessed_member": accessed_member.oid,
                                "form": form.render(appstruct=appstruct) if form else None,
                                "error": error,
                            }
                    if field in accessed_member.data.get_field_names():
                        if getattr(accessed_member.data, field) != requested_value:
                            setattr(accessed_member.data, field, requested_value)
                            fields_to_update.append(field)
                    elif field in dir(accessed_member):
                        if getattr(accessed_member, field) != requested_value:
                            setattr(accessed_member, field, requested_value)
                            fields_to_update.append(field)
                    else:
                        log.error(f"Unknown field {field} to {requested_value}")
                        error = _('error_while_setting_field', mapping={'field': field})
                        request.session.flash(error, 'error')
                        return {
                            "member": member,
                            "accessed_members": members,
                            "accessed_member": accessed_member.oid,
                            "form": form.render(appstruct=appstruct) if form else None,
                            "error": error,
                        }
        # write modifications in ldap

        sending_success = None
        if fields_to_update:
            sending_success = update_ldap_member(request, accessed_member, fields_to_update=fields_to_update)
        if fields_to_update and sending_success.get('status') != 'success':
            return {
                "member": member,
                "accessed_members": members,
                "accessed_member": accessed_member.oid,
                "form": form.render(appstruct=appstruct) if form else None,
                "error":_('error_while_updating_member'),
                }
        accessed_member.member_state = MemberStates.DATA_MODIFIED
        # When the member changed their own preferred language, the interface
        # must follow immediately (issue #204).
        if 'lang1' in fields_to_update and \
                getattr(member, 'oid', None) == accessed_member.oid:
            # Also applies to the response of this request (issue #247).
            switch_request_language(
                request, getattr(accessed_member.data, 'lang1', None))
        #@TODO send a modification confirmation email
        return {
            "member": member,
            "form": None,
            "accessed_member":accessed_member,
            "accessed_members": {},
            "message": message if message else _('member_data_updated'),
        }
        
    else :
        return {"member": member, "form": None, "accessed_member":None,"accessed_members": members}


