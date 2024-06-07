# description: Login view
# author: Michaël Launay
# date: 2023-06-15

import datetime
from typing import Union
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPBindError
from alirpunkto.constants_and_globals import (
    _,
    LDAP_SERVER,
    LDAP_OU,
    LDAP_BASE_DN,
    log
)
from ..models.users import User
from ..utils import (
    is_admin,
    get_admin_user,
    get_oid_from_pseudonym,
    update_member_from_ldap,
    logout,
)

@view_config(route_name='login', renderer='alirpunkto:templates/login.pt')
def login_view(request):
    """Login view.

    Args:
        request (pyramid.request.Request): the request
    """
    logged_in = request.params.get('logged_in', False)
    site_name = request.params.get('site_name', 'AlirPunkto')
    domain_name = request.params.get('domain_name', 'alirpunkto.org')
    username = request.params.get('username', "")
    user = request.session.get('user', None)
    if 'form.submitted' in request.params:
        username = request.params['username']
        password = request.params['password']
        if is_admin(username, password):
            # The user is the ldap admin
            user = get_admin_user()
            oid = user.oid
        else:
            oid = get_oid_from_pseudonym(username, request)
            if not oid:
                # The user is not in the ldap directory
                # return an error message
                return {
                    'error': _('invalid_username_or_password'),
                    'site_name': site_name,
                    'domain_name': domain_name
                }
            user = check_password(username, oid, password)
        if user is not None:
            # The user is in the ldap directory
            update_member_from_ldap(oid, request) # force update of the user
            headers = remember(request, username)
            request.session['logged_in'] = True
            request.session['user'] = user.to_json()
            current_time = datetime.datetime.now().isoformat()
            request.session['created_at'] = current_time
            request.session['site_name'] = site_name
            request.session['domain_name'] = domain_name
            # redirect to the page the user wanted to access before login
            if 'redirect_url' in request.session:
                redirect_url = request.session['redirect_url']
                del request.session['redirect_url']
                return HTTPFound(location=redirect_url, headers=headers)
            return HTTPFound(
                location=request.route_url('home'),
                headers=headers
            )
        else:
            request.session['logged_in'] = False
            return {
                'error': _('invalid_username_or_password'),
                'site_name': site_name,
                'domain_name': domain_name
            }
    else:
        logout(request)
    return {
        'logged_in': True if user else False,
        'site_name': site_name,
        'domain_name': domain_name,
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
    server = Server(LDAP_SERVER, get_info=ALL)
    ldap_login=(
        f"uid={oid},{LDAP_OU},{LDAP_BASE_DN}" if LDAP_OU
        else f"uid={oid},{LDAP_BASE_DN}"
    ) # define the user to authenticate
    log.debug(f"Trying to authenticate {ldap_login=} with {password=}")
    try:
        # define an unsecure LDAP connection, using the credentials above
        conn = Connection(server, ldap_login, password, auto_bind=True)
        conn.search(
            LDAP_BASE_DN,
            '(uid={})'.format(oid),
            attributes=['cn', 'uid','mail', 'employeeNumber']
        ) # search for the user in the LDAP directory
    except LDAPBindError as e:
        log.debug(f"Error while authenticating {username}: {e}")
        return None
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
