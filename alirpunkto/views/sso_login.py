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
    SSO_REFRESH,
    SSO_EXPIRES_AT,
)
from alirpunkto.utils import (
    update_member_from_ldap,
    get_keycloak_token,
    logout,
)
from alirpunkto.secret_manager import get_secret
import jwt
from alirpunkto.models.users import User
from alirpunkto.models.member import Member
from datetime import datetime, timedelta
from pyramid.security import remember

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
    try:
        sso_token = keycloak_openid.token(
            grant_type='authorization_code',
            code=code,
            redirect_uri=redirect_uri
        )
        access_token = sso_token["access_token"]
        at_head = jwt.get_unverified_header(access_token)
        algo = at_head['alg']
        # Get the sso server public key
        public_key = f"""-----BEGIN PUBLIC KEY-----
{keycloak_openid.public_key()}
-----END PUBLIC KEY-----"""
        # Decode and verify the JWT
        decoded_payload = jwt.decode(
            access_token,
            public_key,
            algorithms=[algo],
            audience=[get_secret(KEYCLOAK_CLIENT_ID), 'account']
        )
        log.debug("Verified sso token payload: ", decoded_payload)

        logout(request) # Enforce logout before processing login
        site_name = request.params.get('site_name', 'AlirPunkto')
        domain_name = request.params.get('domain_name', 'alirpunkto.org')
        organization_details = request.params.get('organization_details', 'AlirPunkto')
        oid = decoded_payload['employeeNumber']
        # The user is in the ldap directory
        member = update_member_from_ldap(oid, request) # force update of the user
        if not member:
            # The user is not in the ldap directory
            # return an error message
            return {
                'error': _('invalid username or password'),
                'site_name': site_name,
                'domain_name': domain_name,
                'organization_details': organization_details
            }
        user = User(
            member.pseudonym,
            member.email,
            member.oid,
            member.data.is_active,
            member.type.name
        )
        request.session['site_name'] = site_name
        request.session['domain_name'] = domain_name
        request.session['organization_details'] = organization_details
        request.session['logged_in'] = True
        request.session['user'] = user.to_json()
        now = datetime.now()
        current_time = now.isoformat()
        request.session['created_at'] = current_time
        request.session[SSO_REFRESH] = sso_token['refresh_token']
        refresh_at = now + timedelta(seconds=int(sso_token['refresh_expires_in']))
        request.session[SSO_EXPIRES_AT] = refresh_at.isoformat()
        request.headers['Authorization'] = f'Bearer {sso_token}'
        headers = remember(request, member.pseudonym)
        return HTTPFound(
            location=request.route_url('home'),
            headers=headers
        )
    except jwt.ExpiredSignatureError as err:
        log.debug("The sso token has expired")
        logout(request)
    except jwt.InvalidAudienceError as err:
        log.warning(f"Inavalide audience in sso token: {err}")
        logout(request)
    except jwt.InvalidTokenError as err:
        log.warning(f"Invalid sso token: {err}")
        logout(request)
    except Exception as e:
        log.error(f"Error during sso authentication {e}")
        logout(request)
    #@TODO from uid retrieve the ldap user and log him in
    
    return HTTPFound(location='/')
