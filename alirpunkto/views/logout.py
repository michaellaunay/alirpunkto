# description: Login view
# author: Michaël Launay
# date: 2023-07-28

import logging
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.security import forget
from alirpunkto.constants_and_globals import CANDIDATURE_OID
from alirpunkto.utils import logout

@view_config(route_name='logout')
def logout_view(request):
    """Logout view.

    Args:
        request (pyramid.request.Request): the request
    """
    logout(request)
    return HTTPFound(location=request.route_url('home'))