# description: forgot password view
# author: Michaël Launay
# date: 2023-06-15

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
    send_member_state_change_email
)
from pyramid.request import Request
from typing import Dict, Union
from BTrees import OOBTree

from alirpunkto.models.member import (
    MemberStates,
    EmailSendStatus,
    MemberDatas,
    MemberTypes
)
from alirpunkto.constants_and_globals import (
    _,
    LDAP_ADMIN_OID,
    MEMBERS_BEING_MODIFIED,
    log,
    MEMBER_OID,
    SEED_LENGTH
)
from alirpunkto.schemas.register_form import RegisterForm
from pyramid.i18n import Translator
import deform
import colander

@view_config(
    route_name='forgot_password',
    renderer='alirpunkto:templates/forgot_password.pt'
)
def forgot_password(request):
    """Forgot password view.
    Send an email to the user with a link to reset his password
    
    Args:
        request (pyramid.request.Request): the request
    """
    log.debug(f"forgot_password: {request.method} {request.url}")
    transaction = request.tm

    member, error = _retrieve_member(request)
    form = None
    if error:
        return error
    if member:
        schema = RegisterForm().bind(request=request)
        read_only_fields = {
            "email": member.email,
            "pseudonym": member.pseudonym,
            "cooperative_number": member.oid
        }

        writable_field_values = {"password": "", "password_confirm": ""}
        schema.prepare_for_modification(read_only_fields,
            writable_field_values)
        appstruct = {
            'cooperative_number': member.oid,
            'email': member.email,
            'pseudonym': member.pseudonym,
        }
        form = deform.Form(schema,
            buttons=('modify',),
            translator=Translator
        )

    if member and not "modify" in request.POST:
        # If we get here it's because the user used the link received in his 
        # email and it's valid @TODO check the validity period
        # 11) The user receives the email and clicks on the link
        # 12) AlirPunkto displays the forgot_password.pt zpt to enter the new
        # password
        if member.member_state == MemberStates.DATA_MODIFICATION_REQUESTED: 
            request.session[MEMBER_OID] = member.oid
            transaction.commit()
            return {"form": form.render(appstruct=appstruct),
                "member": member
            }
    oid = request.session.get(MEMBER_OID, None)
    if oid:
        member = get_member_by_oid(oid, request, True)
    # 1) AlirPunkto displays the forgot_password.pt zpt to enter the mail
    if 'submit' in request.POST:
        # 2) The user has entered his mail and validated
        mail = request.POST['email'] if 'email' in request.POST else None
        if not mail:
            log.warning('No mail provided')
            return {"error":_('forget_no_mail'), "member": None, "form": None}
        # 2.1) AlirPunkto checks that the mail is valid
        if err:= is_not_a_valid_email_address(mail, check_mx=False):
            log.warning(
                f'Invalid email address: {mail[:512]}')
            # 2.1.1) If not, AlirPunkto displays an error message
            # 2.1.2) Return to 1
            err["member"] = None
            err["form"] = None
            return err

        # 3) AlirPunkto checks that the email exists in ldap
        members = get_member_by_email(mail)
        if not members:
            # 3.1) If the mail does not exist, AlirPunkto displays a message
            # indicating that if the user exists, he will receive an email
            # 3.2) End of the procedure
            return {"error":_('forget_email_in_member_list'), "member": None, "form": None}
        # 4) AlirPunkto retrieves information about the user from the ldap
        if len(members) > 1:
            log.warning(f'Multiple members found for mail: {mail[:512]}')
        ldap_member = members[0]
        uid = str(ldap_member['uid']) # cast ldap3's type to str
        if uid == LDAP_ADMIN_OID:
            log.warning(f'Admin user cannot reset password: {mail[:512]}')
            return {"error":_('forget_admin_user'), "member": None, "form": None}
        # 5) If an instance of Member (an application, or any other
        # derived object) exists for this OID it's updated from LDAP, if not, a MemberDatas
        # instance is created with LDAP informations, and stored in the MemberDatas list.
        # The details of the email sent to the member, such as the link, will
        # be generated by the instance's methods.
        member = update_member_from_ldap(uid, request)
        transaction.commit()
        if not member:
            return {"error":_('forget_email_in_member_list'), "member": None, "form": None}       
        # 5.1) AlirPunkto checks if there is a user being modified
        # get the list of users being modified
        root = get_connection(request).root()
        if MEMBERS_BEING_MODIFIED not in root:
            root[MEMBERS_BEING_MODIFIED] = OOBTree.BTree()
            transaction.commit()
        reset_members = root[MEMBERS_BEING_MODIFIED]
        # Add the user to the list of users being modified
        reset_members[uid] = member
        transaction.commit()
        # Change state to reset password
        # 6) AlirPunkto generates a hashed password reset token
        # 7) AlirPunkto creates a password reset event and adds the token to it
        # 8) AlirPunkto creates a link to the persistent user with the token
        # 9) AlirPunkto sends an email to the user with the link
        member.member_state = MemberStates.DATA_MODIFICATION_REQUESTED
        email_template = "reset_password_email"
        member.add_email_send_status(
            EmailSendStatus.IN_PREPARATION, 
            "forgot_password"
        )
        send_email_to_member(
            request,
            member, 
            'forgot_password',
            email_template,
            'reset_password_email_subject',
            'forgot_password',
        )       
        try:
            transaction.commit()
            member.add_email_send_status(
                EmailSendStatus.SENT,
                email_template
            )
            return {"message":_('forget_email_sent'), "member": member, "form": None}
        except Exception as e:
            log.error(
                f"Error while reset password {member.oid} : {e}"
            )
            member.add_email_send_status(
                EmailSendStatus.ERROR,
                email_template
            )
            # 11) The user receives the email and musts clicks on the link to continue
            # 11.1) If the link is invalid or expired, AlirPunkto displays an error message
            # 11.2) Return to 1
            return {"member":None, "error":_('forget_email_send_error'), "form": None}
    elif 'modify' in request.POST and oid and member:
            # 11.1) If the link is invalid or expired, AlirPunkto displays an error message
        # 12) AlirPunkto displays the forgot_password.pt zpt to enter the new password
        # 13) The user enters his new password and validates
        # 14) AlirPunkto checks that the password is valid and meets security constraints
        # 14.1) If the password is not valid, AlirPunkto displays an error message
        # 14.2) Return to 12
        password = request.params['password']
        password_confirm = request.params['password_confirm']
        if password != password_confirm:
            return {"error":_('password_not_match'),
                "member": member,
                "form": form.render(appstruct=appstruct)}
        if password == "":
            return {"error":_('password_required'),
                "member": member,
                "form": form.render(appstruct=appstruct)}
        err = is_valid_password(password)
        if err:
            return {"error":_(err["error"]),
                "member": member,
                "form": form.render(appstruct=appstruct)}
        # 15) AlirPunkto updates the password in the ldap
        result = update_member_password(request, member.oid, password)
        if result['status'] == "success":
            # 16) AlirPunkto updates the events of the member
            # 17) AlirPunkto displays the forgot_password.pt zpt to confirm the password change
            # 18) AlirPunkto sends an email to the user to notify him of the password change
            member.member_state = MemberStates.DATA_MODIFIED
            transaction.commit()
            result = send_member_state_change_email(
                request,
                member,
                "forgot_password",
            )
            transaction.commit()
            log.debug(f"Password changed for {member.oid} to {password}")
            log.info(f"Password changed for {member.oid}")
            if 'success' in result and result['success']:
                return {"message":_('password_changed'), "member": member, "form": None}
            else:
                log.error(
                    f"Error while reset password {member.oid} : {result['message']}"
                )
                return {"error":_('forget_confirmation_email_send_error'), "member": member, "form": None}
        else:
            log.error(
                f"Error while reset password {member.oid} : {result['message']}"
            )
            return {"error":_('password_not_changed'), "member": member, "form": None}
    else :
        return {"member": None, "form": None}

def _retrieve_member(
        request: Request
    ) -> Union[MemberDatas, Dict]:
    """Retrieve an existing member from the URL.

    Parameters:
    - request (Request): The pyramid request object.

    Returns:
    - tuple: A tuple containing the member object and an error dict if applicable.
    """

    # If the member is not in the request, try to retrieve it from the URL
    encrypted_oid = request.params.get("oid", None)
    if encrypted_oid:
        decrypted_oid, seed = decrypt_oid(
            encrypted_oid,
            SEED_LENGTH,
            request.registry.settings['session.secret'])
        member = get_member_by_oid(decrypted_oid, request, True)
        if member is None:
            error = _('member_not_found')
            return None, {'member': None,
                'error': error}
        if seed != member.email_send_status_history[-1].seed:
            error = _('url_is_obsolete')
            return None, {'member': member,
                'error': error,
                'url_obsolete': True}
        return member, None
    else:
        return None, None
