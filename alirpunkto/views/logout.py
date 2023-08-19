# description: Login view
# author: Michaël Launay
# date: 2023-07-28

import datetime
import logging
from typing import Union
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.security import forget
from ldap3 import Server, Connection, ALL, NTLM
from .. import _
from .. import LDAP_SERVER, LDAP_OU, LDAP_BASE_DN, LDAP_LOGIN, LDAP_PASSWORD
from ..models.users import User

@view_config(route_name='logout')
def logout_view(request):
    """Logout view.

    Args:
        request (pyramid.request.Request): the request
    """
    logged_in = request.params.get('logged_in', False)
    site_name = request.params.get('site_name', 'AlirPunkto')
    username = request.params.get('username', "")
    user = request.session.get('user', None)
    if 'form.submitted' in request.params:
        if user is not None:
            del request.session['user']
            request.session['logged_in'] = False
            request.session['created_at'] = None
            request.session['site_name'] = site_name
        else:
            request.session['logged_in'] = False
    forget(request)
    return HTTPFound(location=request.route_url('home'))