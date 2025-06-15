""" Pyramid view for managing providers.
Create and update provider members.
"""
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
    MemberTypes,
    EmailSendStatus,
)
from alirpunkto.constants_and_globals import (
    _,
    log,
    CANDIDATURE_OID,
    MEMBER_OID,
    ACCESSED_MEMBER_OID,
    LDAP_ADMIN_OID
)
from alirpunkto.schemas.register_form import RegisterForm
from pyramid.i18n import Translator
import deform
from alirpunkto.models.users import User
from alirpunkto.models.permissions import Permissions
from alirpunkto.models.model_permissions import (
    MemberDataPermissions,
    get_access_permissions
)
from dataclasses import fields
import json

manage_provider_schema = {
    'name': {'type': 'string', 'required': True, 'empty': False},
    'email': {'type': 'string', 'required': True, 'empty': False},
    'phone': {'type': 'string', 'required': False, 'empty': True},
    'address': {'type': 'string', 'required': False, 'empty': True},
    'website': {'type': 'string', 'required': False, 'empty': True},
}

@view_config(route_name='manage_provider', renderer='alirpunkto:templates/manage_provider.pt')
def manage_provider_view(request):
    """Manage provider view.

    Args:
        request (pyramid.request.Request): the request
    """
    log.debug(f"manage_provider: {request.method} {request.url}")
    accessor_member = None
    oid = None
    user = request.session.get('user', None)
    accessed_member_oid = None
    form = None
    if user:
        user = User.from_json(user)
        oid = user.oid
    if not oid:
        return {'member':user,
            'form':None,
            'providers': {},
            'error': _('user_not_logged_in')}
    accessor_member = get_member_by_oid(oid, request, True)
    if not accessor_member:
        return {'member':user,
            'form':None,
            'providers': {},
            'error': _('member_not_found')}
    # For the moment, only administrators can manage providers
    if accessor_member.type != MemberTypes.ADMINISTRATOR:
        return {'member':user,
            'form':None,
            'providers': {},
            'error': _('must_be_administrator')}
    ldap_members = get_ldap_member_list((MemberTypes.PROVIDER,))
    providers = {provider.oid:provider.name for provider in ldap_members}
    if request.method == "POST":
        if "add_provider" in request.POST:
            provider_email = request.params.get('provider_email', None)
            provider_pseudonym = request.params.get('provider_pseudonym', None)
            provider_password = request.params.get('provider_password', None)
            if not provider_email or not provider_pseudonym or not provider_password:
                return {'member':user,
                    'form':None,
                    'providers': providers,
                    'error': _('provider_email_fullname_password_missing')}
            email_error = is_valid_email(provider_email, request)
            if email_error is not None:
                email_error.update(
                    {'member':user,
                    'form':None,
                    'providers': providers})
                return email_error
            password_error = is_valid_password(provider_password)
            if password_error is not None:
                password_error.update({'member':user,
                    'form':None,
                    'providers': providers})
                return password_error
            if provider_email in providers:
                return {'member':user,
                    'form':None,
                    'providers': providers,
                    'error': _('provider_email_already_exists')}
            try:
                provider = get_member_by_oid(provider_email, request, True)
                if provider:
                    return {'member':user, 'form':None, 'providers': providers, 'error': _('provider_already_exists')}
                # Create new provider member
                provider = update_ldap_member(provider_email, {
                    'name': provider_pseudonym,
                    'email': provider_email,
                    'password': provider_password,
                    'type': MemberTypes.PROVIDER,
                }, request)
                if not provider:
                    return {'member':user, 'form':None, 'providers': providers, 'error': _('provider_creation_failed')}
                send_member_state_change_email(provider, MemberStates.ACTIVE, request)
                send_check_new_email(provider, request)
                return {'member':user, 'form':None, 'providers': providers, 'success': _('provider_created')}
            except Exception as e:
                log.error(f"Error creating provider: {e}")
                return {'member':user, 'form':None, 'providers': providers, 'error': str(e)}
        elif "update" in request.POST:
            accessed_provider_oid = request.params.get(ACCESSED_MEMBER_OID, None)
            if not accessed_provider_oid:
                return {'error': _('accessed_member_oid_missing')}
            member = get_member_by_oid(accessed_provider_oid, request, True)
            if not member:
                return {'error': _('member_not_found')}
            form = RegisterForm(request, schema=manage_provider_schema, member=member)
            if 'form.submitted' in request.params:
                try:
                    form.validate(request.params)
                    data = form.get_data()
                    if not is_valid_email(data['email']):
                        return {'member':user, 'form':None, 'providers': providers, 'error': _('invalid_email')}
                    if not is_valid_password(data.get('password', '')):
                        return {'member':user, 'form':None, 'providers': providers, 'error': _('invalid_password')}
                    update_member_from_ldap(member.oid, request)
                    update_ldap_member(member.oid, data, request)
                    send_member_state_change_email(member, MemberStates.ACTIVE, request)
                    return {'member':user, 'form':None, 'providers': providers, 'success': _('provider_updated')}
                except deform.ValidationFailure as e:
                    log.error(f"Validation failed: {e}")
                    return {'member':user, 'form':None, 'providers': providers, 'error': str(e)}
    else:
        return {'member':user, 'form':None, 'providers': providers}
    return {'error': 'Invalid request method'}