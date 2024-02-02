# description: Login view
# author: Michaël Launay
# date: 2023-07-28

import logging
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.security import forget
from alirpunkto.constants_and_globals import CANDIDATURE_OID

@view_config(route_name='logout')
def logout_view(request):
    """Logout view.

    Args:
        request (pyramid.request.Request): the request
    """
    username = request.params.get('username', "")
    if username:
        del request.session['username']
    user = request.session.get('user', None)
    if user is not None:
        # log the user is logging out
        log = logging.getLogger('alirpunkto')
        log.info(f"User {user} is logging out")
        del request.session['user']
        request.session['logged_in'] = False
        request.session['created_at'] = None
    else:
        request.session['logged_in'] = False
    if CANDIDATURE_OID in request.session:
        del request.session[CANDIDATURE_OID] #
    #forget(request)
    return HTTPFound(location=request.route_url('home'))