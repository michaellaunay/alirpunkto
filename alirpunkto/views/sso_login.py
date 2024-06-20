from pyramid.view import view_config
from pyramid.response import Response
from keycloak import KeycloakOpenID
from pyramid.httpexceptions import HTTPFound
from alirpunkto.constants_and_globals import (
    _,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_REALM,
    KEYCLOAK_SERVER_URL,
    KEYCLOAK_CLIENT_SECRET,
    KEYCLOAK_REDIRECT_PATH,
)
from alirpunkto.secret_manager import get_secret

@view_config(route_name='sso_login')
def sso_login_view(request):
    keycloak_openid = KeycloakOpenID(server_url=KEYCLOAK_SERVER_URL,
                                     client_id=get_secret(KEYCLOAK_CLIENT_ID),
                                     realm_name=KEYCLOAK_REALM,
                                     client_secret_key=get_secret(KEYCLOAK_CLIENT_SECRET))
    auth_url = keycloak_openid.auth_url(redirect_uri=request.route_url(KEYCLOAK_REDIRECT_PATH))
    return HTTPFound(location=auth_url)

@view_config(route_name=KEYCLOAK_REDIRECT_PATH)
def callback_view(request):
    keycloak_openid = KeycloakOpenID(server_url=KEYCLOAK_SERVER_URL,
                                     client_id=get_secret(KEYCLOAK_CLIENT_ID),
                                     realm_name=KEYCLOAK_REALM,
                                     client_secret_key=get_secret(KEYCLOAK_CLIENT_SECRET))

    code = request.params.get('code')
    token = keycloak_openid.token(grant_type='authorization_code', code=code, redirect_uri=request.registry.settings['keycloak.redirect_uri'])
    userinfo = keycloak_openid.userinfo(token['access_token'])
    
    request.session['sso_token'] = token
    request.session['sso_user'] = userinfo

    #@TODO from uid retrieve the ldap user and log him in
    
    return HTTPFound(location='/')