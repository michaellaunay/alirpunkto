# description: check new email view
# author: Michaël Launay
# date: 2024-05-12

from pyramid.view import view_config
from alirpunkto.utils import (
    consume_action_link,
    decrypt_oid,
    get_member_by_oid,
    link_matches_pending_action,
    update_ldap_member,
)

from alirpunkto.models.member import (
    MemberStates,
)
from alirpunkto.constants_and_globals import (
    SITE_NAME,
    DOMAIN_NAME,
    ORGANIZATION_DETAILS,
    _,
    log,
    SEED_LENGTH,
    ADMIN_EMAIL,
)

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
                'site_name': SITE_NAME,
                'domain_name': DOMAIN_NAME,
                'organization_details': ORGANIZATION_DETAILS,
                'admin_email': ADMIN_EMAIL,
            }
        decrypted_member = get_member_by_oid(decrypted_oid, request)
        if decrypted_member is None:
            log.error(f"check_new_email: Candidature not found for oid {decrypted_oid}")
            return {
                'error': _('candidature_not_found'),
                'site_name': SITE_NAME,
                'domain_name': DOMAIN_NAME,
                'organization_details': ORGANIZATION_DETAILS,
                'admin_email': ADMIN_EMAIL,
            }
        new_email = getattr(decrypted_member, 'new_email', None)
        if new_email is None:
            log.error(f"check_new_email: Candidature {decrypted_oid} has no new email")
            return {
                'error': _('no_new_email'),
                'site_name': SITE_NAME,
                'domain_name': DOMAIN_NAME,
                'organization_details': ORGANIZATION_DETAILS,
                'admin_email': ADMIN_EMAIL,
            }
        if not link_matches_pending_action(decrypted_member, seed,
                                           ('check_new_email',)):
            # Transversal audit of 2026-10-24 (A05): the link must be the
            # one minted for THIS address change — not an older emission,
            # not a reset or resignation link of the same member.
            log.warning(f"check_new_email: stale or foreign link for "
                        f"{decrypted_oid}")
            return {
                'error': _('invalid_oid'),
                'site_name': SITE_NAME,
                'domain_name': DOMAIN_NAME,
                'organization_details': ORGANIZATION_DETAILS,
                'admin_email': ADMIN_EMAIL,
            }
        # Transversal audit of 2026-10-24 (A08): the directory is written
        # BEFORE the pending address is consumed. On a refusal the old
        # address comes back and the request stays pending, so the same
        # link can be retried instead of being lost.
        previous_email = decrypted_member.email
        decrypted_member.email = new_email
        result = update_ldap_member(request, decrypted_member, fields_to_update=['email'])
        if not result or result.get('status') != 'success':
            log.error(f"check_new_email: Error updating email for oid {decrypted_oid}")
            if isinstance(previous_email, str):
                decrypted_member.email = previous_email
            return {
                'error': _('email_update_error'),
                'site_name': SITE_NAME,
                'domain_name': DOMAIN_NAME,
                'organization_details': ORGANIZATION_DETAILS,
            }
        decrypted_member.new_email = None
        decrypted_member.member_state = MemberStates.DATA_MODIFIED
        consume_action_link(decrypted_member, 'check_new_email')
        return {
            'success': _('email_updated'),
            'site_name': SITE_NAME,
            'domain_name': DOMAIN_NAME,
            'organization_details': ORGANIZATION_DETAILS,
            'admin_email': ADMIN_EMAIL,
        }
    return {
        'error': _('invalid_request'),
        'site_name': SITE_NAME,
        'domain_name': DOMAIN_NAME,
        'organization_details': ORGANIZATION_DETAILS,
        'admin_email': ADMIN_EMAIL,
    }


