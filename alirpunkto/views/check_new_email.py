# description: check new email view
# author: Michaël Launay
# date: 2024-05-12

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

@view_config(
    route_name='check_new_email',
    renderer='alirpunkto:templates/check_new_email.pt'
)
def check_new_email(request):
    """Check new email view.
    A mail was send to the user for checking his new email.
    If this view is calling with a good token, the user's email is updated.
    
    Args:
        request (pyramid.request.Request): the request
    """
    log.debug(f"check_new_email: {request.method} {request.url}")
    transaction = request.tm

