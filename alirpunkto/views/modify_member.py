# description: modify member view
# author: Michaël Launay
# date: 2024-04-19

from pyramid.view import view_config
from alirpunkto.utils import (
    get_member_by_oid,
    is_valid_password,
    is_valid_email,
    update_member_password,
    update_member_from_ldap,
    update_ldap_member,
    send_member_state_change_email,
    send_check_new_email,
    get_members,
    get_ldap_member_list,
)

from alirpunkto.models.member import (
    MemberStates,
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
    ldap_members= get_ldap_member_list()
    members = {user.oid:user.name for user in ldap_members}
    """
    members = {k:m.pseudonym
        for (k,m) in get_members(request).items()
            if m.member_state in (
                MemberStates.DATA_MODIFIED,
                MemberStates.DATA_MODIFICATION_REQUESTED,
                MemberStates.REGISTRED
            )
    }
    """
    transaction = request.tm
    message = None
    oid = (request.session.get(CANDIDATURE_OID, None)
        or request.session.get(MEMBER_OID, None))
    if not oid:
        user = request.session.get("user", None)
        if user:
            oid = json.loads(user).get("oid", None)
    if oid:
        member = get_member_by_oid(oid, request)
        if not member:
            member = update_member_from_ldap(oid, request)
            if not member:
                return {
                    "form": None,
                    "message": _('unknown_member'),
                    "member": None,
                    "accessed_member": None,
                    "accessed_members": members,
                }
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
                update_member_from_ldap(accessed_member_oid, request)
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
            if accessed_member_oid:
                # Force the update of the member from the ldap
                accessed_member = update_member_from_ldap(
                    accessed_member_oid,
                    request
                )
        if not accessed_member_oid:
            return {
                "form": None,
                "member": member,
                "accessed_member": None,
                "accessed_members": members,
                "message": _('unknown_accessed_member'),
            }
        accessed_member = update_member_from_ldap(accessed_member_oid, request)
        if not accessed_member:
            return {
                "form": None,
                "member": member,
                "accessed_member": None,
                "accessed_members": members,
                "message": _('unknown_accessed_member'),
                "error": sending_success
            }

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
        for field in writable_fields:
            if (
                field in request.POST 
                and request.POST[field]
                and (
                    request.POST[field] != getattr(accessed_member.data, field, NotImplemented)
                    or request.POST[field] != getattr(accessed_member, field, NotImplemented)
                )):
                if accessed_member_oid == member.oid and "email" in request.POST and "email" in writable_fields:
                    email = request.POST['email']
                    if email != accessed_member.email:
                        err = is_valid_email(email, request)
                        if err:
                            request.session.flash(err, 'error')
                            return {"error":err,
                                "member": member,
                                "accessed_members": {},
                                "accessed_member": accessed_member.oid,
                                "form": form.render()}
                        accessed_member.new_email = email
                        transaction.commit()
                        sending_success = send_check_new_email(request, accessed_member, email)
                        if not sending_success:
                            return {"message":_('check_new_email_send_error'),
                                "member": member,
                                "accessed_member": accessed_member,
                                "accessed_members": {},
                                "form": form.render()}
                        message = _('check_new_email_send')
                elif "password" in request.POST and "password" in writable_fields:
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
                    if field in fields(accessed_member.data):
                        if getattr(accessed_member.data, field) != request.POST[field]:
                            setattr(accessed_member.data, field, request.POST[field])
                    elif field in fields(accessed_member):
                        if getattr(accessed_member, field) != request.POST[field]:
                            setattr(accessed_member, field, request.POST[field])
                    else:
                        log.error(f"Unknown field {field} to {request.POST[field]}")
                        error = _('error_while_setting_field', mapping={'field': field})
                        request.session.flash(_('error_while_setting_field'), error)
                        return {"error":_('password_required'),
                            "member": member,
                            "accessed_members": members,
                            "accessed_member": accessed_member.oid,
                            "form": form.render(),
                            "error": error}
        # write modifications in ldap
        fields_to_update = []
        sending_success = None
        for field in writable_fields:
            if (field in request.POST and request.POST[field] 
                and getattr(accessed_member.data, field, getattr(accessed_member, field,None))
            ):
                if field == "email" and accessed_member_oid == member.oid:
                    continue # The email is updated by the check_new_email view
                fields_to_update.append(field)
        if fields_to_update:
            sending_success = update_ldap_member(accessed_member, request, fields_to_update=fields_to_update)
        if not sending_success and fields_to_update:
            return {"error":_('error_while_updating_member'),
                "member": member,
                "accessed_members": members,
                "accessed_member": accessed_member.oid,
                "form": form.render()}
        accessed_member.member_state = MemberStates.DATA_MODIFIED
        transaction.commit()
        #@TODO send a modification confirmation email
        return {"member": member,
            "form": None,
            "accessed_member":accessed_member,
            "accessed_members": [],
            "message": message if message else _('member_data_updated')
        }
        
    else :
        return {"member": member, "form": None, "accessed_member":None,"accessed_members": members}
