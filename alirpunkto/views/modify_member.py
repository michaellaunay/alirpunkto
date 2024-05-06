# description: modify member view
# author: Michaël Launay
# date: 2024-04-19

from pyramid.view import view_config
from pyramid_zodbconn import get_connection
from alirpunkto.utils import (
    is_not_a_valid_email_address,
    get_member_by_email,
    update_member_from_ldap,
    get_member_by_oid,
    send_email_to_member,
    decrypt_oid,
    is_valid_password,
    update_member_password,
    send_member_state_change_email,
    get_members,
)
from pyramid.request import Request
from typing import Dict, Union
from BTrees import OOBTree

from alirpunkto.models.member import (
    MemberStates,
    EmailSendStatus,
    MemberDatas,
    Members,
)
from alirpunkto.constants_and_globals import (
    _,
    LDAP_ADMIN_OID,
    MEMBERS_BEING_MODIFIED,
    log,
    CANDIDATURE_OID,
    MEMBER_OID,
    ACCESSED_MEMBER_OID,
    SEED_LENGTH
)
from alirpunkto.schemas.register_form import RegisterForm
from pyramid.i18n import Translator
import deform
from alirpunkto.models.permissions import Permissions
from alirpunkto.models.model_permissions import (
    MemberDataPermissions,
    MemberPermissions,
    CandidaturePermissions,
    get_access_permissions
)

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
    transaction = request.tm
    oid = (request.session.get(CANDIDATURE_OID, None)
        or request.session.get(MEMBER_OID, None))
    member = None
    members = {k:m.pseudonym
        for (k,m) in get_members(request).items()
        if m.member_state in (
            MemberStates.DATA_MODIFIED,
            MemberStates.DATA_MODIFICATION_REQUESTED,
            MemberStates.REGISTRED
        )
    }
    if oid:
        member = get_member_by_oid(oid, request)
    else:
        return {"member": None,
            "form": None,
            "message": _('unknown_member'),
            "accessed_members": members,
        }
    accessor_member = member
    accessed_member_oid = request.POST.get(ACCESSED_MEMBER_OID, None)
    if not accessed_member_oid:
        if accessed_member_oid in Members.get_instance():
            accessed_member = Members.get_instance()[accessed_member_oid]
        else:
            return {"accessed_member": None,
                "form": None,
                "message": _('unknown_accessed_member'),
                "accessed_members": members,
            }
    form = None
    schema = None
    if "submit" in request.POST or 'modify' in request.POST:
        if not accessed_member_oid:
            return {"accessed_member": None,
                "form": None,
                "message": _('unknown_accessed_member'),
                "accessed_members": members,
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
        request.session[MEMBER_OID] = member.oid
        transaction.commit()
        return {"form": form.render(appstruct=appstruct),
            "member": member
        }
    elif 'modify' in request.POST and oid and member:
        password = request.params['password'] if 'password' in request.params else None
        password_confirm = request.params['password_confirm'] if 'password_confirm' in request.params else None
        if password != password_confirm:
            request.session.flash(_('password_not_match'), 'error')
            return {"error":_('password_not_match'),
                "member": member,
                "accessed_member": accessed_member_oid.oid,
                "form": form.render()}
        if password == "":
            request.session.flash(_('password_required'), 'error')
            return {"error":_('password_required'),
                "member": member,
                "form": form.render()}
        err = is_valid_password(password)
        if err:
            request.session.flash(err, 'error')
            return {"error":_('password_required'),
                "member": member,
                "form": form.render()}
        #@TODO gérer tous les champs du formulaire
        #@TODO mettre accessed_member à jour
        #@TODO Mette à jour son état DATA_MODIFIED et le modifier
        # 15) AlirPunkto updates the password in the ldap
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
            log.debug(f"Password changed for {member.oid} to {password}")
            log.info(f"Password changed for {member.oid}")
            if 'sucess' in result and result['sucess']:
                return {"message":_('password_changed'), "member": member, "form": None}
            else:
                log.error(
                    f"Error while reset password {member.oid} : {result['error']}"
                )
                return {"error":_('forget_confirmation_email_send_error'), "member": member, "form": None}
        else:
            log.error(
                f"Error while reset password {member.oid} : {result['message']}"
            )
            return {"error":_('15dd'), "member": member, "form": None}
    else :
        return {"member": None, "form": None, "accessed_members": members}
