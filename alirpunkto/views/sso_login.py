"""Login through Keycloak (the optional SSO layer — never the only one).

Transversal audit of 2026-10-24 (A04): the authorization-code round
trip is bound to the browser session that started it. The departure
mints a one-time ``state`` and a PKCE verifier (RFC 7636, S256) kept in
the session with their issue time; the callback refuses a ``code`` that
comes back without the matching, unexpired ``state`` (RFC 9700 §2.1,
§4.7), and exchanges it with the verifier. The access token is then
verified against a FIXED algorithm list and the realm's issuer — never
against whatever the token's header announces.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta

from pyramid.view import view_config
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
    is_account_closed,
    update_member_from_ldap,
    store_sso_tokens,
    logout,
)
from alirpunkto.secret_manager import get_secret
import jwt
from alirpunkto.models.users import User
from pyramid.security import remember

#: Session keys of the pending round trip.
SSO_STATE = 'sso_state'
SSO_VERIFIER = 'sso_verifier'
SSO_STARTED_AT = 'sso_started_at'

#: A departure older than this is not resumed (seconds).
SSO_STATE_TTL_SECONDS = int(os.getenv('KEYCLOAK_STATE_TTL_SECONDS', '600'))

#: The signature algorithms the access token may use — a closed list,
#: configured, not read from the token (A04).
JWT_ALGORITHMS = tuple(
    algorithm.strip()
    for algorithm in os.getenv('KEYCLOAK_JWT_ALGORITHMS', 'RS256').split(',')
    if algorithm.strip())


def expected_issuer() -> str | None:
    """The realm's issuer URL, ``KEYCLOAK_ISSUER`` when the deployment
    overrides it, else ``<server>/realms/<realm>``."""
    configured = os.getenv('KEYCLOAK_ISSUER')
    if configured:
        return configured.rstrip('/')
    if KEYCLOAK_SERVER_URL and KEYCLOAK_REALM:
        return f"{KEYCLOAK_SERVER_URL.rstrip('/')}/realms/{KEYCLOAK_REALM}"
    return None


def _openid():
    return KeycloakOpenID(
        server_url=KEYCLOAK_SERVER_URL,
        client_id=get_secret(KEYCLOAK_CLIENT_ID),
        realm_name=KEYCLOAK_REALM,
        client_secret_key=get_secret(KEYCLOAK_CLIENT_SECRET)
    )


def start_round_trip(session) -> tuple[str, str]:
    """Arm the session for one authorization-code round trip and return
    (state, code_challenge)."""
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode('ascii')).digest()).rstrip(b'=').decode('ascii')
    session[SSO_STATE] = state
    session[SSO_VERIFIER] = verifier
    session[SSO_STARTED_AT] = datetime.now().isoformat()
    return state, challenge


def take_round_trip(session, state) -> str | None:
    """Consume the pending round trip: the PKCE verifier when ``state``
    matches the armed, unexpired one, else None. One use only."""
    expected = session.pop(SSO_STATE, None)
    verifier = session.pop(SSO_VERIFIER, None)
    started = session.pop(SSO_STARTED_AT, None)
    if not expected or not state or not secrets.compare_digest(
            str(state), str(expected)):
        return None
    try:
        age = datetime.now() - datetime.fromisoformat(started)
    except (TypeError, ValueError):
        return None
    if age > timedelta(seconds=SSO_STATE_TTL_SECONDS) or age < timedelta(0):
        return None
    return verifier


@view_config(route_name='sso_login')
def sso_login_view(request):
    state, challenge = start_round_trip(request.session)
    auth_url = _openid().auth_url(
        redirect_uri=request.route_url(KEYCLOAK_REDIRECT_PATH),
        scope='openid profile email',
        state=state,
        code_challenge=challenge,
        code_challenge_method='S256',
    )
    return HTTPFound(location=auth_url)


@view_config(route_name=KEYCLOAK_REDIRECT_PATH)
def callback_view(request):
    code = request.params.get('code')
    verifier = take_round_trip(request.session, request.params.get('state'))
    if not code or verifier is None:
        # No armed departure, another browser's state, or a stale one:
        # the code is not ours to exchange (A04).
        log.warning("sso callback refused: missing code or unmatched state")
        logout(request)
        return HTTPFound(location='/')

    keycloak_openid = _openid()
    redirect_uri = request.route_url(KEYCLOAK_REDIRECT_PATH)
    try:
        sso_token = keycloak_openid.token(
            grant_type='authorization_code',
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=verifier,
        )
        access_token = sso_token["access_token"]
        # Get the sso server public key
        public_key = f"""-----BEGIN PUBLIC KEY-----
{keycloak_openid.public_key()}
-----END PUBLIC KEY-----"""
        # Decode and verify the JWT against the configured algorithms and
        # the realm's issuer — the header's "alg" is never trusted.
        decoded_payload = jwt.decode(
            access_token,
            public_key,
            algorithms=list(JWT_ALGORITHMS),
            audience=[get_secret(KEYCLOAK_CLIENT_ID), 'account'],
            issuer=expected_issuer(),
        )
        log.debug("Verified sso token payload for %s",
                  decoded_payload.get('employeeNumber'))

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
        # Quarantine period but isActive is False. Transversal audit of
        # 2026-10-24 (A01): the departure states close the SSO door too.
        if is_account_closed(member):
            return {
                'error': _('account_deactivated_login_error'),
                'site_name': site_name,
                'domain_name': domain_name,
                'organization_details': organization_details,
            }
        if not member.data.is_active:
            return {
                'error': _('account_deactivated_login_error'),
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
    except jwt.ExpiredSignatureError:
        log.debug("The sso token has expired")
        logout(request)
    except jwt.InvalidAudienceError as err:
        log.warning(f"Inavalide audience in sso token: {err}")
        logout(request)
    except jwt.InvalidIssuerError as err:
        log.warning(f"Invalid issuer in sso token: {err}")
        logout(request)
    except jwt.InvalidTokenError as err:
        log.warning(f"Invalid sso token: {err}")
        logout(request)
    except Exception as e:
        log.error(f"Error during sso authentication {e}")
        logout(request)

    return HTTPFound(location='/')
