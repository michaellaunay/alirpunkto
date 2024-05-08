# description: modify member view
# author: Michaël Launay
# date: 2024-04-19

from pyramid.view import view_config
from alirpunkto.utils import (
    get_member_by_oid,
    is_valid_password,
    update_member_password,
    send_member_state_change_email,
    get_members,
)
from pyramid.request import Request
from typing import Dict, Union

from alirpunkto.models.member import (
    MemberStates,
    EmailSendStatus,
    MemberDatas,
    Members,
)
from alirpunkto.constants_and_globals import (
    _,
    log,
    CANDIDATURE_OID,
    MEMBER_OID,
    ACCESSED_MEMBER_OID,
)
from alirpunkto.schemas.register_form import RegisterForm
from pyramid.i18n import Translator
import deform
from alirpunkto.models.permissions import Permissions
from alirpunkto.models.model_permissions import (
    MemberDataPermissions,
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
    schema = None
    members = {k:m.pseudonym
        for (k,m) in get_members(request).items()
            if m.member_state in (
                MemberStates.DATA_MODIFIED,
                MemberStates.DATA_MODIFICATION_REQUESTED,
                MemberStates.REGISTRED
            )
    }
    transaction = request.tm
    oid = (request.session.get(CANDIDATURE_OID, None)
        or request.session.get(MEMBER_OID, None))
    if not oid:
        user = request.session.get("user", None)
        if user:
            oid = json.loads(user).get("oid", None)
    if oid:
        member = get_member_by_oid(oid, request)
    else:
        return {
            "form": None,
            "message": _('unknown_member'),
            "member": None,
            "accessed_member": None,
            "accessed_members": members,
        }
    accessor_member = member

    if "submit" in request.POST or 'modify' in request.POST:
        if "submit" in request.POST:
            accessed_member_oid = request.POST.get(ACCESSED_MEMBER_OID, None)
            if accessed_member_oid and accessed_member_oid in members:
                accessed_member = Members.get_instance()[accessed_member_oid]
                if not accessed_member:
                    return {
                        "form": None,
                        "member": member,
                        "accessed_member": None,
                        "accessed_members": members,
                        "message": _('unknown_accessed_member'),
                    }
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
                "message": _('unknown_accessed_member'),
            }
        accessed_member = Members.get_instance()[accessed_member_oid]
        permissions = get_access_permissions(accessed_member, accessor_member)
        if not permissions or permissions == Permissions.NONE:
            log.warning(
                f'No permission to access member datas: {accessed_member_oid.oid}'
            )
            request.session.flash(_('no_permission'), 'error')
            return {"error":_('no_permission'),
                "member": None,
                "form": None,
                "accessed_members": members,
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
            'cooperative_behaviour_mark_update': accessed_member.data.cooperative_behaviour_mark_updated,
            'number_shares_owned': accessed_member.data.number_shares_owned,
            'date_end_validity_yearly_contribution': accessed_member.data.date_end_validity_yearly_contribution,
            'iban': accessed_member.data.iban,
            #'date_erasure_all_data': accessed_member.data.date_erasure_all_data #TODO
        }
        form = deform.Form(schema,
            buttons=('modify',),
            translator=Translator
        )
        request.session[ACCESSED_MEMBER_OID] = accessed_member.oid
        accessed_member.member_state = MemberStates.DATA_MODIFICATION_REQUESTED
        transaction.commit()
        return {"form": form.render(appstruct=appstruct),
            "member": member,
            "accessed_members": {},
            "accessed_member": accessed_member.oid,
        }
    elif 'modify' in request.POST and oid and member:
        # check if the member data field is writable before assignement
        writable_fields = [
            permission.name
                for permission in fields(permissions.data)
                if (getattr(permissions.data, permission.name)
                    & (Permissions.WRITE|Permissions.ACCESS))
        ]
        err = None
        for field in writable_fields:
            if field in request.POST and request.POST[field] and request.POST[field] != getattr(accessed_member.data, field):
                if "password" in request.POST and "password" in writable_fields:
                    password = request.params['password'] if 'password' in request.params else None
                    password_confirm = request.params['password_confirm'] if 'password_confirm' in request.params else None
                    if password != password_confirm:
                        request.session.flash(_('password_not_match'), 'error')
                        return {"error":_('password_not_match'),
                            "member": member,
                            "accessed_members": {},
                            "accessed_member": accessed_member.oid,
                            "form": form.render()}
                    if password == "":
                        request.session.flash(_('password_required'), 'error')
                        return {"error":_('password_required'),
                            "member": member,
                            "accessed_members": {},
                            "accessed_member": accessed_member.oid,
                            "form": form.render()}
                    err = is_valid_password(password)
                else:
                    #@TODO cast the value to the right type
                    try:
                        setattr(accessed_member.data, field, request.POST[field])
                    except Exception as e:
                        log.error(f"Error while setting {field} to {request.POST[field]} : {e}")
                        error = _('error_while_setting_field', mapping={'field': field})
                        request.session.flash(_('error_while_setting_field'), error)
                        return {"error":_('password_required'),
                            "member": member,
                            "accessed_members": members,
                            "accessed_member": accessed_member.oid,
                            "form": form.render(),
                            "error": error}
        # @TODO write in ldap
        accessed_member.member_state = MemberStates.DATA_MODIFIED
        transaction.commit()
        #@TODO send a modification confirmation email
        # 15) AlirPunkto updates the member in the ldap
        raise NotImplementedError
        result = update_member_password(request, member.oid, password)
        if result['status'] == "success":
            # 16) AlirPunkto updates the events of the member
            # 17) AlirPunkto displays the modify_member.pt zpt to confirm the password change
            # 18) AlirPunkto sends an email to the user to notify him of the password change
            member.member_state = MemberStates.DATA_MODIFIED
            transaction.commit()
            result = send_member_state_change_email(
                request,
                member,
                "modify_member",
            )
            transaction.commit()
            log.debug(f"Fields changed for {member.oid} to {password}")
            log.info(f"Fields changed for {member.oid}")
            if 'sucess' in result and result['sucess']:
                return {"message":_('fields_changed'),
                    "member": member, "accessed_member": accessed_member,
                    "accessed_members": {}, "form": None}
            else:
                log.error(
                    f"Error while reset password {member.oid} : {result['error']}"
                )
                return {"error":_('forget_confirmation_email_send_error'),
                    "member": {}, "accessed_members": {}, "form": None}
        else:
            log.error(
                f"Error while modify {accessed_member.oid} by {member.oid} : {result['message']}"
            )
            return {"error":_('15dd'),
                "member": member, "accessed_members": {}, "form": None}
    else :
        return {"member": member, "form": None, "accessed_member":None,"accessed_members": members}
