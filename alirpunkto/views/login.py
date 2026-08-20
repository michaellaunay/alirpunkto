# description: Login view
# author: Michaël Launay
# date: 2023-06-15

from datetime import datetime
from typing import Union
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from ldap3.core.exceptions import LDAPBindError
from ldap3.utils.conv import escape_filter_chars
from alirpunkto.ldap_factory import get_ldap_connection
from alirpunkto.constants_and_globals import (
    _,
    LDAP_OU,
    LDAP_BASE_DN,
    log,
    DOMAIN_NAME,
    SITE_NAME,
    ORGANIZATION_DETAILS,
)
from alirpunkto.models.users import User
from alirpunkto.login_throttle import (
    is_throttled,
    record_failure,
    record_success,
)
from alirpunkto.utils import (
    safe_local_redirect,
    switch_request_language,
    is_admin,
    get_admin_user,
    get_oid_from_pseudonym,
    update_member_from_ldap,
    store_sso_tokens,
    logout,
    get_keycloak_token,
)
from alirpunkto.secret_manager import encrypt_secret_for_logs

@view_config(route_name='login', renderer='alirpunkto:templates/login.pt')
def login_view(request):
    """Login view.

    Args:
        request (pyramid.request.Request): the request
    """
    site_name = SITE_NAME
    domain_name = DOMAIN_NAME
    organization_details = ORGANIZATION_DETAILS
    username = request.POST.get('username', "")
    user = request.session.get('user', None)
    # Revised audit: credentials are only ever read from the POST body —
    # a crafted GET (/login?form.submitted=1&username=…&password=…) used
    # to be processed, leaking the password into browser history and
    # HTTP logs and sidestepping the unsafe-method CSRF check.
    if request.method == 'POST' and 'form.submitted' in request.POST:
        username = request.POST.get('username', "")
        password = request.POST.get('password', "")
        client_ip = getattr(request, 'client_addr', None) or 'unknown'
        if is_throttled(client_ip, username):
            # Refused before any LDAP work; never log the password.
            log.warning(f"login throttled for ip={client_ip} "
                        f"username={username!r}")
            return {
                'error': _('too_many_login_attempts'),
                'site_name': site_name,
                'domain_name': domain_name,
                'organization_details': organization_details
            }
        if is_admin(username, password):
            # The user is the ldap admin
            user = get_admin_user(request)
            oid = user.oid
        else:
            oid = get_oid_from_pseudonym(username, request)
            if not oid:
                # The user is not in the ldap directory
                # return an error message
                record_failure(client_ip, username)
                return {
                    'error': _('invalid_username_or_password'),
                    'site_name': site_name,
                    'domain_name': domain_name,
                    'organization_details': organization_details
                }
            user = check_password(username, oid, password)
        if user is not None:
            record_success(client_ip, username)
            # The user is in the ldap directory
            member = update_member_from_ldap(oid, request) # force update of the user
            # Issue #265: a confirmed departure closes the door — an
            # unsubscribed, excluded or deleted account must never log
            # in again, whatever the directory still authenticates.
            from alirpunkto.models.member import MemberStates
            if member is not None and member.member_state in (
                    MemberStates.UNSUBSCRIBED,
                    MemberStates.EXCLUDED,
                    MemberStates.DELETED):
                record_failure(client_ip, username)
                return {
                    'error': _('login_account_disabled'),
                    'site_name': site_name,
                    'domain_name': domain_name,
                    'organization_details': organization_details
                }
            headers = remember(request, username)
            request.session['logged_in'] = True
            # Drive the interface with the member's declared language (issue #204)
            switch_request_language(
                request,
                getattr(getattr(member, 'data', None), 'lang1', None))
            request.session['user'] = user.to_json()
            request.session['created_at'] = datetime.now().isoformat()
                        # Request Keycloak token
            sso_token = get_keycloak_token(user, password)
            if sso_token:
                log.debug(f"Successfully obtained Keycloak token for {username}")
                # refresh token + expiry only (see utils.store_sso_tokens)
                store_sso_tokens(request, sso_token)
            else:
                log.warning(f"Failed to obtain Keycloak token for {username}")
            # redirect to the page the user wanted to access before login
            if 'redirect_url' in request.session:
                # Only same-site targets are followed (open-redirect fix).
                redirect_url = safe_local_redirect(
                    request.session['redirect_url'], request)
                del request.session['redirect_url']
                if redirect_url:
                    return HTTPFound(location=redirect_url, headers=headers)
            return HTTPFound(
                location=request.route_url('home'),
                headers=headers
            )
        else:
            record_failure(client_ip, username)
            request.session['logged_in'] = False
            return {
                'error': _('invalid_username_or_password'),
                'site_name': site_name,
                'domain_name': domain_name,
                'organization_details': organization_details
            }
    else:
        logout(request) # Enforce logout before processing login
    return {
        'logged_in': True if user else False,
        'site_name': site_name,
        'domain_name': domain_name,
        'organization_details': organization_details,
        'user': username
    }

def check_password(username:str, oid:str, password:str) -> Union[None, User]:
    """Check in ldap if the password is correct for the given username.

    Args:
        username (str): the username
        oid (str): the oid
        password (str): the password

    Returns:
        User: a User instance if the password is correct, None otherwise
    """
    # define an unsecure LDAP server, requesting info on DSE and schema
    ldap_user=(
        f"uid={oid},{LDAP_OU},{LDAP_BASE_DN}" if LDAP_OU
        else f"uid={oid},{LDAP_BASE_DN}"
    ) # define the user to authenticate
    log.debug(f"Trying to authenticate {ldap_user=} with {encrypt_secret_for_logs(password)=}")
    try:
        # define an unsecure LDAP connection, using the credentials above
        with get_ldap_connection(ldap_user=ldap_user,
            ldap_password=password, ldap_auto_bind=True) as conn:
            conn.search(
                LDAP_BASE_DN,
                f'(uid={escape_filter_chars(oid)})',
                attributes=['cn', 'uid','mail', 'employeeNumber']
            ) # search for the user in the LDAP directory
            if len(conn.entries) == 0:
                return None
            user_entry = conn.entries[0]
            name = user_entry.cn.value
            employeeNumber = (user_entry.employeeNumber.value
                if "employeeNumber" in user_entry else user_entry.uid.value
            )
            email = (user_entry.mail.value
                if "mail" in user_entry else "undefined@example.com"
            )
            if "mail" not in user_entry:
                log.warning(f"User {username} has no email address")
            if "employeeNumber" not in user_entry:
                log.warning(f"User {username} has no employeeNumber")

            user = User(name=name, email=email, oid=employeeNumber)
            return user
    except LDAPBindError as e:
        log.debug(f"Error while authenticating {username}: {e}")
        return None
