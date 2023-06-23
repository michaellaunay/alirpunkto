# description: Login view
# author: Michaël Launay
# date: 2023-06-15

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember

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
    """Check if the password is correct for the given username.

    Args:
        username (str): the username
        password (str): the password

    Returns:
        bool: True if the password is correct, False otherwise
    """
    #@TODO: check the password in OpenLDAP
    return username == 'admin' and password == 'admin'
