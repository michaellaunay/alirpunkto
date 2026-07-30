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
    DOMAIN_NAME,
    SITE_NAME,
    ORGANIZATION_DETAILS,
)
from alirpunkto.utils import (
    update_member_from_ldap,
    store_sso_tokens,
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
        site_name = SITE_NAME
        domain_name = DOMAIN_NAME
        organization_details = ORGANIZATION_DETAILS
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
        # A resigned (or otherwise deactivated) member cannot log in
        # (spec "Démissionner"): the LDAP entry stays during the
        # Quarantine period but isActive is False.
        if not member.data.is_active:
            return {
                'error': _('This account has been deactivated.'),
                'site_name': site_name,
                'domain_name': domain_name,
                'organization_details': organization_details,
            }

        user = User(
            member.pseudonym,
            member.email,
            member.oid,
            member.data.is_active,
            member.type.name
        )
        request.session['logged_in'] = True
        request.session['user'] = user.to_json()
        request.session['created_at'] = datetime.now().isoformat()
        # refresh token + expiry only: the access token is never read back
        # and would overflow the 4093-byte session cookie (2026-07-08).
        store_sso_tokens(request, sso_token)
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
