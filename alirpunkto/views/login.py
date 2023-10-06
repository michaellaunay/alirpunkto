# description: Login view
# author: Michaël Launay
# date: 2023-06-15

import datetime
import logging
from typing import Union
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from ldap3 import Server, Connection, ALL, NTLM
from .. import _
from .. import LDAP_SERVER, LDAP_OU, LDAP_BASE_DN, LDAP_LOGIN, LDAP_PASSWORD
from ..models.users import User

@view_config(route_name='login', renderer='alirpunkto:templates/login.pt')
def login_view(request):
    """Login view.

    Args:
        request (pyramid.request.Request): the request
    """
    logged_in = request.params.get('logged_in', False)
    site_name = request.params.get('site_name', 'AlirPunkto')
    username = request.params.get('username', "")
    user = request.session.get('user', None)
    if 'form.submitted' in request.params:
        username = request.params['username']
        password = request.params['password']
        user = check_password(username, password)
        if user is not None:
            headers = remember(request, username)
            request.session['logged_in'] = True
            request.session['user'] = user
            request.session['created_at'] = datetime.datetime.now().isoformat()
            request.session['site_name'] = site_name
            return HTTPFound(location=request.route_url('home'), headers=headers)
        else:
            request.session['logged_in'] = False
            return {'error': request.translate(_('invalid_username_or_password'))}
    return {'logged_in': True if user else False, 'site_name': site_name, 'user': username}

def check_password(username:str, password:str) -> Union[None, User]:
    """Check in ldap if the password is correct for the given username.

    Args:
        username (str): the username
        password (str): the password

    Returns:
        User: a User instance if the password is correct, None otherwise
    """
    server = Server(LDAP_SERVER, get_info=ALL) # define an unsecure LDAP server, requesting info on DSE and schema
    ldap_login=f"uid={username},{LDAP_OU},{LDAP_BASE_DN}" if LDAP_OU else f"uid={username},{LDAP_BASE_DN}" # define the user to authenticate
    log.debug(f"Trying to authenticate {ldap_login=} {ldap_login=}")
    conn = Connection(server, ldap_login, password, auto_bind=True) # define an unsecure LDAP connection, using the credentials above
    conn.search(LDAP_BASE_DN, '(uid={})'.format(username), attributes=['cn']) # search for the user in the LDAP directory
    if len(conn.entries) == 0:
        return None
    user_entry = conn.entries[0]
    name = user_entry.cn.value
    if "mail" in user_entry:
        email = user_entry.mail.value
    else:
        email = "undefined@example.com"
        log = logging.getLogger(__name__)
        log.warning(f"User {username} has no email address")
    user = User.create_user(name, email)
    return user
