# description: modify member view
# author: Michaël Launay
# date: 2024-04-19

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
import datetime
from alirpunkto.utils import (
    get_member_by_oid,
    is_valid_password,
    is_valid_email,
    update_member_from_ldap,
    update_ldap_member,
    send_check_new_email,
    get_ldap_member_list,
)

from alirpunkto.models.member import (
    MemberStates,
    EmailSendStatus,
)
from alirpunkto.constants_and_globals import (
    _,
    log,
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
    member = None
    accessed_member_oid = None
    form = None
    appstruct = None
    schema = None
    transaction = request.tm
    message = None
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
        member = get_member_by_oid(oid, request, True)
        if not member:
            member = update_member_from_ldap(oid, request)
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
    ldap_members= get_ldap_member_list()
    members = {user.oid:user.name for user in ldap_members}
    accessor_member = member
    if "submit" in request.POST or 'modify' in request.POST:
        if "submit" in request.POST:
            accessed_member_oid = request.POST.get(ACCESSED_MEMBER_OID, None)
        elif 'modify' in request.POST:
            accessed_member_oid = (request.session[ACCESSED_MEMBER_OID]
                if ACCESSED_MEMBER_OID in request.session else None
                )
        if not accessed_member_oid:
            return {
                "form": None,
                "member": member,
                "accessed_member": None,
                "accessed_members": members,
                "error": _('unknown_accessed_member'),
            }
        # Update the accessed member from the ldap
        accessed_member = update_member_from_ldap(accessed_member_oid, request)
        # Memorize the moddification request
        if accessed_member.member_state != MemberStates.DATA_MODIFICATION_REQUESTED:
            request.session[ACCESSED_MEMBER_OID] = accessed_member.oid
            accessed_member.member_state = MemberStates.DATA_MODIFICATION_REQUESTED
            transaction.commit()
        elif ACCESSED_MEMBER_OID not in request.session:
            request.session[ACCESSED_MEMBER_OID] = accessed_member.oid
        if not accessed_member:
            return {
                "form": None,
                "member": member,
                "accessed_member": None,
                "accessed_members": members,
                "error": _('unknown_accessed_member')
            }
        permissions = get_access_permissions(accessed_member, accessor_member)
        if not permissions or permissions == Permissions.NONE:
            log.warning(
                f'No permission to access member datas: {accessed_member_oid.oid}'
            )
            request.session.flash(_('no_permission'), 'error')
            return {
                "member": None,
                "form": None,
                "accessed_members": members,
                "error":_('no_permission'),
            }
        schema = RegisterForm().bind(request=request)
        # The permissions don't have the same structure as the schema,
        # so we need to apply permissions.data and permissions to the schema.
        schema.apply_permissions(permissions.data)
        schema.apply_permissions(permissions)
    if "submit" in request.POST:
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
        form = deform.Form(schema,
            buttons=('modify',),
            translator=Translator
        )
        return {
            "form": form.render(appstruct=appstruct) if form else None,
            "member": member,
            "accessed_members": {},
            "accessed_member": accessed_member.oid,
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
                        transaction.commit()
                        email_template = "reset_password_email"
                        member.add_email_send_status(
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
                            transaction.commit()
                            member.add_email_send_status(
                                EmailSendStatus.SENT,
                                email_template
                            )
                            message = _('check_new_email_send')
                        except Exception as e:
                            log.error(
                                f"Error while reset password {member.oid} : {e}"
                            )
                            member.add_email_send_status(
                                EmailSendStatus.ERROR,
                                email_template
                            )
                            # message is left with error because we can't
                            # use the error message as it could be overridden
                            message = _('forget_email_send_error')
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
                else:
                    #@TODO cast the value to the right type
                    requested_value = request.POST[field] if field not in date_parameters else date_parameters[field]
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
                        request.session.flash(_('error_while_setting_field'), error)
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
        if not sending_success and fields_to_update:
            return {
                "member": member,
                "accessed_members": members,
                "accessed_member": accessed_member.oid,
                "form": form.render(appstruct=appstruct) if form else None,
                "error":_('error_while_updating_member'),
                }
        accessed_member.member_state = MemberStates.DATA_MODIFIED
        transaction.commit()
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
