# description: check new email view
# author: Michaël Launay
# date: 2024-05-12

from pyramid.view import view_config
from pyramid_zodbconn import get_connection
from alirpunkto.utils import (

    update_member_from_ldap,
    get_member_by_oid,
    send_email_to_member,
    decrypt_oid,
    send_member_state_change_email,
    get_candidature_by_oid,
    update_ldap_member,
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
    decrypted_member = None
    if "oid" in request.params:
        encrypted_oid = request.params.get("oid", None)
        decrypted_oid, seed = decrypt_oid(
            encrypted_oid,
            SEED_LENGTH,
            request.registry.settings['session.secret'])
        if decrypted_oid is None:
            log.error(f"check_new_email: Error decrypting oid {encrypted_oid}")
            return {
                'error': _('invalid_oid'),
                'site_name': request.session.get('site_name', 'AlirPunkto'),
                'domain_name': request.session.get('domain_name', 'alirpunkto.org')
            }
        decrypted_member = get_candidature_by_oid(decrypted_oid, request)
        if decrypted_member is None:
            log.error(f"check_new_email: Candidature not found for oid {decrypted_oid}")
            return {
                'error': _('candidature_not_found'),
                'site_name': request.session.get('site_name', 'AlirPunkto'),
                'domain_name': request.session.get('domain_name', 'alirpunkto.org')
            }
        new_email = decrypted_member.new_email
        if new_email is None:
            log.error(f"check_new_email: Candidature {decrypted_oid} has no new email")
            return {
                'error': _('no_new_email'),
                'site_name': request.session.get('site_name', 'AlirPunkto'),
                'domain_name': request.session.get('domain_name', 'alirpunkto.org')
            }
        decrypted_member.new_email = None
        decrypted_member.email = new_email
        decrypted_member.member_state = MemberStates.DATA_MODIFIED
        result = update_ldap_member(request, decrypted_member, fields_to_update=['email'])
        if result is None:
            log.error(f"check_new_email: Error updating email for oid {decrypted_oid}")
            return {
                'error': _('email_update_error'),
                'site_name': request.session.get('site_name', 'AlirPunkto'),
                'domain_name': request.session.get('domain_name', 'alirpunkto.org')
            }
        transaction.commit()
        return {
            'success': _('email_updated'),
            'site_name': request.session.get('site_name', 'AlirPunkto'),
            'domain_name': request.session.get('domain_name', 'alirpunkto.org')
        }
    return {
        'error': _('invalid_request'),
        'site_name': request.session.get('site_name', 'AlirPunkto'),
        'domain_name': request.session.get('domain_name', 'alirpunkto.org')
    }