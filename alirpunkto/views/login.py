# description: Login view
# author: Michaël Launay
# date: 2023-06-15

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from ldap3 import Server, Connection, ALL, NTLM
from .. import _
from .. import LDAP_SERVER, LDAP_OU, LDAP_BASE_DN, LDAP_LOGIN, LDAP_PASSWORD

@view_config(route_name='login', renderer='alirpunkto:templates/login.pt')
def login_view(request):
    """Login view.

    Args:
        request (pyramid.request.Request): the request
    """
    if 'form.submitted' in request.params:
        username = request.params['username']
        password = request.params['password']
        if check_password(username, password):
            headers = remember(request, username)
            return HTTPFound(location=request.route_url('home'), headers=headers)
        else:
            return {'error': request.translate(_('invalid_username_or_password'))}

    return {}

def check_password(username:str, password:str) -> bool:
    """Check in ldap if the password is correct for the given username.

    Args:
        username (str): the username
        password (str): the password

    Returns:
        bool: True if the password is correct, False otherwise
    """
    server = Server(LDAP_SERVER, get_info=ALL) # define an unsecure LDAP server, requesting info on DSE and schema
    ldap_login=f"uid={username},{LDAP_OU},{LDAP_BASE_DN}" # define the user to authenticate
    conn = Connection(server, ldap_login, password, auto_bind=True) # define an unsecure LDAP connection, using the credentials above
    conn.search(LDAP_BASE_DN, '(uid={})'.format(username), attributes=['cn']) # search for the user in the LDAP directory
    if len(conn.entries) == 0:
        return False
    conn = Connection(server, conn.entries[0].entry_dn, password, auto_bind=True)
    return conn.bind()
