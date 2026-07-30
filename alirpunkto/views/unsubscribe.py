"""Member resignation (specification "Démissionner").

The member asks to deactivate the account from the profile page, reads the
implications, confirms — the member enters PENDING_UNSUBSCRIPTION and
receives an e-mail whose link is the real confirmation. Following the link
moves the member to UNSUBSCRIBED: the LDAP entry is deactivated (kept, the
pseudonym and identity stay reserved during the Quarantine period) with the
erasure due date recorded, a farewell e-mail is sent, and the session ends.
The member may cancel while pending, and a pending request expires lazily
after UNSUBSCRIBE_LINK_VALIDITY_DAYS: the previous state is restored.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from alirpunkto.constants_and_globals import (
    _,
    QUARANTINE_PERIOD_DAYS,
    SEED_LENGTH,
    UNSUBSCRIBE_LINK_VALIDITY_DAYS,
    log,
)
from alirpunkto.models.member import MemberStates
from alirpunkto.utils import (
    deactivate_member_in_ldap,
    decrypt_oid,
    get_member_by_oid,
    send_email_to_member,
)


def _context(request, **extra):
    settings = getattr(request.registry, 'settings', {}) or {}
    context = {
        'logged_in': request.session.get('logged_in', False),
        'site_name': settings.get('site_name'),
        'domain_name': settings.get('domain_name'),
        'organization_details': settings.get('organization_details'),
        'member': None, 'error': None, 'success': None, 'pending': False,
    }
    context.update(extra)
    return context


def _session_member(request):
    user = request.session.get('user')
    if isinstance(user, str):
        try:
            user = json.loads(user)
        except (TypeError, ValueError):
            user = None
    oid = user.get('oid') if isinstance(user, dict) else None
    return get_member_by_oid(oid, request) if oid else None


def expire_stale_unsubscription(member, now=None):
    """Lazy expiry (spec, alternative scenario): a pending request older than
    the link validity silently returns the member to the previous state."""
    if getattr(member, 'member_state', None) != \
            MemberStates.PENDING_UNSUBSCRIPTION:
        return False
    requested = getattr(member, 'unsubscription_requested_at', None)
    now = now or datetime.now()
    if requested and now - requested <= timedelta(
            days=UNSUBSCRIBE_LINK_VALIDITY_DAYS):
        return False
    member.member_state = getattr(
        member, 'previous_member_state', None) or MemberStates.REGISTRED
    member.previous_member_state = None
    member.unsubscription_requested_at = None
    log.info(f"Unsubscription request of {member.oid} expired; state "
             f"restored to {member.member_state}")
    return True


@view_config(route_name='unsubscribe',
             renderer='alirpunkto:templates/unsubscribe.pt')
def unsubscribe(request):
    """The implications page; POST opens the pending request and e-mails
    the confirmation link."""
    if not request.session.get('logged_in'):
        request.session.flash(_('user_not_logged_in'), 'error')
        return HTTPFound(location=request.route_url('home'))
    member = _session_member(request)
    if member is None:
        return _context(request, error=_('unknown_member'))
    expire_stale_unsubscription(member)

    if member.member_state == MemberStates.PENDING_UNSUBSCRIPTION:
        return _context(request, member=member, pending=True)

    if 'confirm' in request.POST:
        member.previous_member_state = member.member_state
        member.member_state = MemberStates.PENDING_UNSUBSCRIPTION
        member.unsubscription_requested_at = datetime.now()
        result = send_email_to_member(
            request, member, 'unsubscribe',
            'unsubscribe_confirmation_email',
            'unsubscribe_email_subject', 'unsubscribe_confirm')
        if not result or result.get('error'):
            # Sending failed: do not strand the member in pending.
            member.member_state = member.previous_member_state
            member.previous_member_state = None
            member.unsubscription_requested_at = None
            log.error(f"unsubscribe: could not send the confirmation e-mail "
                      f"to {member.oid}: {result}")
            return _context(request, member=member,
                            error=_('email_not_sent'))
        log.info(f"Member {member.oid} entered PENDING_UNSUBSCRIPTION")
        return _context(
            request, member=member, pending=True,
            success=_('A confirmation link has been sent to your e-mail '
                      'address. Your account stays active until you follow '
                      'it.'))

    return _context(request, member=member)


@view_config(route_name='unsubscribe_cancel')
def unsubscribe_cancel(request):
    """Cancel a pending request (spec, alternative scenario)."""
    if not request.session.get('logged_in'):
        return HTTPFound(location=request.route_url('home'))
    member = _session_member(request)
    if member is not None and member.member_state == \
            MemberStates.PENDING_UNSUBSCRIPTION:
        member.member_state = getattr(
            member, 'previous_member_state', None) or MemberStates.REGISTRED
        member.previous_member_state = None
        member.unsubscription_requested_at = None
        log.info(f"Member {member.oid} cancelled the unsubscription request")
        request.session.flash(_('Your deactivation request has been '
                                'cancelled.'), 'success')
    return HTTPFound(location=request.route_url('modify_member'))


@view_config(route_name='unsubscribe_confirm',
             renderer='alirpunkto:templates/unsubscribe.pt')
def unsubscribe_confirm(request):
    """The e-mailed link: the actual confirmation of the resignation."""
    encrypted_oid = request.params.get('oid')
    if not encrypted_oid:
        return _context(request, error=_('invalid_oid'))
    decrypted_oid, seed = decrypt_oid(
        encrypted_oid, SEED_LENGTH,
        request.registry.settings['session.secret'])
    if decrypted_oid is None:
        return _context(request, error=_('invalid_oid'))
    member = get_member_by_oid(decrypted_oid, request)
    if member is None:
        return _context(request, error=_('unknown_member'))

    if member.member_state == MemberStates.UNSUBSCRIBED:
        return _context(request, unsubscribed=True,
                        success=_('account_deactivated_message'))
    if expire_stale_unsubscription(member) or \
            member.member_state != MemberStates.PENDING_UNSUBSCRIPTION:
        return _context(request, error=_(
            'This deactivation link has expired. Your account stays '
            'active; you can start again from your profile page.'))

    member.member_state = MemberStates.UNSUBSCRIBED
    member.previous_member_state = None
    member.departure_date = datetime.now()
    member.departure_reason = 'resignation'
    erasure_due = member.departure_date + timedelta(
        days=QUARANTINE_PERIOD_DAYS)
    if getattr(member, 'data', None) is not None:
        member.data.date_erasure_all_data = erasure_due.date()
        member.data.is_active = False
    result = deactivate_member_in_ldap(request, member, erasure_due)
    if result.get('status') != 'success':
        return _context(request, error=result.get('message'))
    send_email_to_member(
        request, member, 'unsubscribe_confirm', 'unsubscribed_email',
        'unsubscribed_email_subject', 'home')
    # End the member's own session if this browser held it.
    request.session.pop('logged_in', None)
    request.session.pop('user', None)
    log.info(f"Member {member.oid} UNSUBSCRIBED; erasure due "
             f"{erasure_due.date().isoformat()}")
    return _context(request, unsubscribed=True,
                    success=_('account_deactivated_message'))
