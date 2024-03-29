# description: Login view
# author: Michaël Launay
# date: 2023-07-07

from pyramid.view import view_config
from alirpunkto.constants_and_globals import _
from json import loads

def is_authenticated(request):
    # Check if the user is authenticated
    return 'user' in request.session


@view_config(route_name='home', renderer='alirpunkto:templates/home.pt')
def home_view(request):
    """Home view.
    show the applications selection page

    Args:
        request (pyramid.request.Request): the request
    """
    applications = []
    if is_authenticated(request):
        logged_in = request.session['logged_in'] = True
        applications = request.registry.settings["applications"]
    else:
        logged_in = request.session['logged_in'] = False
    site_name = request.registry.settings.get('site_name', 'AlirPunkto')
    domain_name = request.registry.settings.get('domain_name', 'alirpunkto.org')
    user = request.session.get('user', None)
    user = loads(user) if user else {'name':'unknown'}
    return {
        'logged_in': logged_in,
        'site_name': site_name,
        'domain_name': domain_name,
        'user': user,
        'applications': applications
    }
