# description: Login view
# author: Michaël Launay
# date: 2023-07-07

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from ldap3 import Server, Connection, ALL, NTLM
from .. import _

@view_config(route_name='home', renderer='alirpunkto:templates/home.pt')
def home_view(request):
    """Home view.
    show the applications selection page

    Args:
        request (pyramid.request.Request): the request
    """
    if 'form.submitted' in request.params:
        ... # TODO

    return {}
