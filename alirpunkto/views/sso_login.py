from pyramid.view import view_config
from pyramid.response import Response
from keycloak import KeycloakOpenID
from pyramid.httpexceptions import HTTPFound
from alirpunkto.constants_and_globals import (
    _,
    log,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_REALM,
    KEYCLOAK_SERVER_URL,
    KEYCLOAK_CLIENT_SECRET,
    KEYCLOAK_REDIRECT_PATH,
)
from alirpunkto.secret_manager import get_secret
import jwt

@view_config(route_name='sso_login')
def sso_login_view(request):
    keycloak_openid = KeycloakOpenID(
        server_url=KEYCLOAK_SERVER_URL,
        client_id=get_secret(KEYCLOAK_CLIENT_ID),
        realm_name=KEYCLOAK_REALM,
        client_secret_key=get_secret(KEYCLOAK_CLIENT_SECRET)
    )
    auth_url = keycloak_openid.auth_url(
        redirect_uri=request.route_url(KEYCLOAK_REDIRECT_PATH),
        scope='openid profile email'
    )
    return HTTPFound(location=auth_url)

@view_config(route_name=KEYCLOAK_REDIRECT_PATH)
def callback_view(request):
    keycloak_openid = KeycloakOpenID(
        server_url=KEYCLOAK_SERVER_URL,
        client_id=get_secret(KEYCLOAK_CLIENT_ID),
        realm_name=KEYCLOAK_REALM,
        client_secret_key=get_secret(KEYCLOAK_CLIENT_SECRET)
    )

    code = request.params.get('code')
    redirect_uri = request.route_url(KEYCLOAK_REDIRECT_PATH)
    token = keycloak_openid.token(
        grant_type='authorization_code',
        code=code,
        redirect_uri=redirect_uri
    )
    access_token = token["access_token"]
    at_head = jwt.get_unverified_header(access_token)
    algo = at_head['alg']
    # Get the sso server public key
    public_key = f"""-----BEGIN PUBLIC KEY-----
{keycloak_openid.public_key()}
-----END PUBLIC KEY-----"""
    try:
    # Decode and verify the JWT
        decoded_payload = jwt.decode(
            access_token,
            public_key,
            algorithms=[algo],
            audience=[get_secret(KEYCLOAK_CLIENT_ID), 'account']
        )
        log.debug("Verified sso token payload: ", decoded_payload)
    except jwt.ExpiredSignatureErrori as err:
        log.debug("The sso token has expired")
    except jwt.InvalidAudienceError as err:
        log.warning(f"Inavalide audience in sso token: {err}")
    except jwt.InvalidTokenError as err:
        log.warning(f"Invalid sso token: {err}")
    #@TODO from uid retrieve the ldap user and log him in
    
    return HTTPFound(location='/')
