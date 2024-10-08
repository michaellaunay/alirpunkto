# description: Login view
# author: Michaël Launay
# date: 2023-07-07

from pyramid.view import view_config
from alirpunkto.constants_and_globals import (
    _,
    SSO_REFRESH,
    SSO_EXPIRES_AT,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_REALM,
    KEYCLOAK_SERVER_URL,
    KEYCLOAK_CLIENT_SECRET,
)
from json import loads
from alirpunkto.utils import refresh_keycloak_token, logout
from datetime import datetime, timedelta
import urllib.parse
from alirpunkto.secret_manager import get_secret

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
    organization_details = request.registry.settings.get('organization_details', 'AlirPunkto')
    user = request.session.get('user', None)
    user = loads(user) if user else {'name':'unknown'}
    if SSO_REFRESH in request.session:
        sso_refresh_token = request.session[SSO_REFRESH]
        sso_expires_at = request.session.get(SSO_EXPIRES_AT, "2020-01-01T00:00:00")
        expire = datetime.fromisoformat(sso_expires_at)
        if expire > datetime.now():
            # Refresh the token
            sso_token = refresh_keycloak_token(sso_refresh_token)
            access_token = sso_token['access_token']
            refresh_at = datetime.now() + timedelta(seconds=int(sso_token['refresh_expires_in']))
            request.session[SSO_REFRESH] = sso_token['refresh_token']
            request.session[SSO_EXPIRES_AT] = refresh_at.isoformat()
            request.headers['Authorization'] = f'Bearer {sso_token}'
        else:
            # Session expired, causing the user to be logged out
            logout(request)
            logged_in = False
            user = None
            applications = []

    return {
        'logged_in': logged_in,
        'site_name': site_name,
        'domain_name': domain_name,
        'organization_details': organization_details,
        'user': user,
        'applications': applications
    }
