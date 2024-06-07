# description: Login view
# author: Michaël Launay
# date: 2023-07-07

from pyramid.view import view_config
from alirpunkto.constants_and_globals import (
    _,
    SSO_REFRESH,
    SSO_EXPIRES_AT,
)
from json import loads
from alirpunkto.utils import refresh_keycloak_token
from datetime import datetime, timedelta
import copy

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
    if SSO_REFRESH in request.session:
        sso_refresh_token = request.session[SSO_REFRESH]
        sso_expires_at = request.session.get(SSO_EXPIRES_AT, "2020-01-01T00:00:00")
        expire = datetime.fromisoformat(sso_expires_at)
        if expire > datetime.now():
            # Refresh the token
            sso_token = refresh_keycloak_token(sso_refresh_token)
            refresh_at = datetime.now() + timedelta(seconds=int(sso_token['refresh_expires_in']))
            request.session[SSO_REFRESH] = sso_token['refresh_token']
            request.session[SSO_EXPIRES_AT] = refresh_at.isoformat()
            request.headers['Authorization'] = f'Bearer {sso_token}'
            access_token = sso_token['access_token']
            # Add the token to the applications url without changing the original settings
            applications = {
                app_name: {**app_info, 'url': app_info['url'] + f"?token={access_token}"}
                for app_name, app_info in applications.items()
            }

    return {
        'logged_in': logged_in,
        'site_name': site_name,
        'domain_name': domain_name,
        'user': user,
        'applications': applications
    }
