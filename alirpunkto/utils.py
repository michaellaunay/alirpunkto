# Definition of the functions used in the project
# author: Michaël Launay
# date: 2023-09-30

from typing import Union, Tuple, Dict, List, Optional, Any
import os
from datetime import date, datetime, timedelta
from pyramid.request import Request
from alirpunkto.models.member import (
    Members,
    MemberDatas,
    EmailSendStatus,
    Member,
    MemberStates,
    MemberTypes
)
from .models.candidature import (
    Candidature,
    CandidatureStates,
)
from pyramid_mailer.message import Message
from pyramid_zodbconn import get_connection
from pyramid.path import AssetResolver
from .constants_and_globals import (
    URL_SCHEME,
    AVAILABLE_LANGUAGES,
    _,
    PYTEST_CURRENT_TEST,
    ADMIN_LOGIN,
    ADMIN_PASSWORD,
    ADMIN_EMAIL,
    LDAP_SERVER,
    LDAP_OU,
    LDAP_BASE_DN,
    LDAP_LOGIN,
    LDAP_USER,
    LDAP_PASSWORD,
    LDAP_ADMIN_OID,
    EUROPEAN_LOCALES,
    DEFAULT_NUMBER_OF_VOTERS,
    MIN_PSEUDONYM_LENGTH,
    MAX_PSEUDONYM_LENGTH,
    MIN_PASSWORD_LENGTH,
    MAX_PASSWORD_LENGTH,
    pseudonym_pattern,
    log,
    SPECIAL_CHARACTERS,
    LOCALE_LANG_MESSAGES,
    ZPT_EXTENSION,
    CANDIDATURE_OID,
    MEMBER_OID,
    SEED_LENGTH,
    DEFAULT_COOPERATIVE_BEHAVIOUR_MARK,
    ACCESSED_MEMBER_OID,
    KEYCLOAK_SERVER_URL,
    KEYCLOAK_REALM,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_CLIENT_SECRET,
    SSO_TOKEN,
    SSO_REFRESH,
    SECRET_KEY,
    SSO_EXPIRES_AT,
    SITE_NAME,
    DOMAIN_NAME,
    ORGANIZATION_DETAILS,
    LDAP_TIME_FORMAT,
    LDAP_TIME_LENGTH,
    DISABLE_EMAIL_MX_CHECKS,
    OID_LINK_TTL_SECONDS,
)
from pyramid.i18n import get_localizer, make_localizer
from pyramid.interfaces import ITranslationDirectories
from translationstring import TranslationString
from ldap3 import (
    Connection,
    MODIFY_ADD,
    MODIFY_REPLACE,
    SUBTREE,
)
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars
from .ldap_factory import get_ldap_connection, schema_safe_attributes
from validate_email import validate_email
from pyramid.renderers import render_to_response
import random
import hmac
import hashlib
import zlib
from urllib.parse import urlparse
from cryptography.fernet import Fernet, InvalidToken
import base64
from .models.users import User
import html
import json
from collections.abc import Mapping
from .secret_manager import get_secret, encrypt_secret_for_logs, make_ldap_password
import requests
import re

def get_preferred_language(request: Request, member=None)->str:
    """Get the preferred language for an interaction.

    The language the member declared in their profile (data.lang1) wins when
    it is one of the supported locales, so e-mails reach the member in the
    language they chose rather than in the browser language of whoever
    triggered the sending (issue #204). Without a member (or without a
    declared language) fall back to the request's Accept-Language.

    Args:
        request (pyramid.request.Request): the request
        member: optional Member/Candidature whose declared language wins
    Returns:
        str: the preferred language
    """
    declared = getattr(getattr(member, "data", None), "lang1", None)         if member is not None else None
    if declared and declared in EUROPEAN_LOCALES:
        return declared
    # Fall back to the browser preference of the current request
    preferred_language = request.accept_language.best_match(EUROPEAN_LOCALES)
    if preferred_language is None:
        preferred_language = "en"
    return preferred_language

def switch_request_language(request: Request, language) -> bool:
    """Apply a freshly chosen language to the current request (issue #247).

    Storing the preference in the session only affects the *next* request:
    the response of the very request that carried the choice — the identity
    document page and the verifier e-mail templates it embeds — was still
    rendered with the language negotiated at NewRequest time. Persist the
    preference, make the explicit _LOCALE_ win for any renegotiation, and
    rebuild request.localizer so auto_translate and the Chameleon renderer,
    which resolve it at call time, follow immediately.
    """
    if not language or language not in AVAILABLE_LANGUAGES:
        return False
    request.session['preferred_language'] = language
    request._LOCALE_ = language
    tdirs = request.registry.queryUtility(ITranslationDirectories) or []
    if tdirs:
        request.localizer = make_localizer(language, tdirs)
        # Legacy mirror kept by add_localizer.
        request.registry.localizer = request.localizer
    request.__dict__.pop('locale_name', None)
    return True


def filter_applications_for_member(request: Request, applications) -> dict:
    """Applications listed on the home page for the logged-in member.

    Each application may declare an ``audience`` — ``all`` (default),
    ``ordinary`` or ``cooperator`` — so the presentation portal can carry a
    different description per membership type and the democratic platforms
    only show to Cooperators (issue #35). An application without a
    configured URL is hidden — e.g. a platform whose SSO connection is not
    implemented yet (issue #142). Administrators get the Cooperator view;
    unknown or provider members get the Ordinary one.
    """
    if not isinstance(applications, Mapping):
        # Test harnesses (and defensive callers) may hand a bare list.
        return applications
    member_type = None
    user = request.session.get('user')
    if isinstance(user, str):
        try:
            user = json.loads(user)
        except (TypeError, ValueError):
            user = None
    oid = user.get('oid') if isinstance(user, dict) else None
    if oid:
        try:
            member = get_member_by_oid(oid, request)
            member_type = getattr(member, 'type', None)
        except Exception as e:
            log.warning(f"filter_applications: cannot resolve member {oid}: {e}")
    is_cooperator = member_type in (
        MemberTypes.COOPERATOR, MemberTypes.ADMINISTRATOR)
    wanted = {'all', 'cooperator' if is_cooperator else 'ordinary'}
    return {
        app_id: app for app_id, app in applications.items()
        if str(app.get('url') or '').strip()
        and app.get('audience', 'all') in wanted
    }


def get_site_url(request: Request) -> str:
    """Return the public base URL of the platform, without a trailing slash.

    The site_url setting is the source of truth (issue #242):
    https://access.cosmopolitical.coop in production. Fall back to the
    URL_SCHEME/DOMAIN_NAME environment constants — never to the domain_name
    setting, whose semantics is the display name of the platform in the
    texts, nor to request.route_url, which yields the proxied localhost when
    e-mails are sent from a subscriber (the verifier reminders).
    """
    settings = getattr(request.registry, 'settings', None) or {}
    configured = str(settings.get('site_url') or '').strip().rstrip('/')
    if configured:
        return configured
    scheme = str(settings.get('url_scheme') or URL_SCHEME).strip().rstrip(':/')
    return f"{scheme}://{DOMAIN_NAME}"


def _translate_for_language(
        request: Request,
        language,
        translation_string
    ) -> str:
    """Translate a TranslationString into an explicit language.

    request.localizer is bound to the language negotiated for the current
    request; e-mail subjects must instead be translated in the language of
    their recipient (issues #238, #239). Build a localizer for that language
    from the registry's translation directories; fall back to the request
    localizer when the language is unknown or unavailable.
    """
    fallback = getattr(request, 'localizer', None) or get_localizer(request)
    if not language or (AVAILABLE_LANGUAGES and language not in AVAILABLE_LANGUAGES):
        return fallback.translate(translation_string)
    tdirs = request.registry.queryUtility(ITranslationDirectories) or []
    if not tdirs:
        return fallback.translate(translation_string)
    localizer = make_localizer(language, tdirs)
    return localizer.translate(translation_string)


def get_candidatures(request)->Members:
    """Get the candidatures from the request.
    Args:
        request (pyramid.request.Request): the request
    Returns:
        Candidatures: the candidatures
    """
    conn = get_connection(request)
    # TODO: Return a generator that filters candidatures from the member list.
    # TODO: Use a cache to avoid fetching candidatures from the database every time.
    return Members.get_instance(connection=conn)

def get_members(request)->Members:
    """Get the members from the request.
    Args:
        request (pyramid.request.Request): the request
    Returns:
        Members: the members
    """
    conn = get_connection(request)
    return Members.get_instance(connection=conn)

def get_member_by_email(email: str) -> list:
    """Get the members from LDAP by their email.
    Args:
        email (str): the email of the member
    Returns:
        list: the matching LDAP entries (empty list if none)
    """
    with get_ldap_connection(ldap_user = LDAP_USER,
        ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        conn.search(
            LDAP_BASE_DN,
            f'(mail={escape_filter_chars(email.strip())})',
            search_scope=SUBTREE,
            attributes=['cn', 'uid', 'isActive', 'employeeType']
        )
        if conn.entries:
            return conn.entries
        else:
            return []

def get_ldap_member_list(
        types_of_members: List[str] = [member.name for member in MemberTypes]
    )->List[Tuple[str, str, bool, str]]:
    """Get the list of members from the LDAP.
    Returns:
        list: list of tuples ('cn', 'uid', 'isActive', 'employeeType')
        representing the ldap members.
    """
    with get_ldap_connection(ldap_user=LDAP_USER,
        ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        conn.search(
            LDAP_BASE_DN,
            '(objectClass=alirpunktoPerson)',
            search_scope=SUBTREE,
            attributes=['cn', 'uid', 'mail', 'isActive', 'employeeType']
        )
        return [
            User(
                name = entry['cn'].value,
                email = entry['mail'].value,
                oid= entry['uid'].value,
                isActive = entry['isActive'].value in ["True", "true", "TRUE", "Y", "y", "YES", "yes", "1"],
                type = getattr(MemberTypes, entry['employeeType'].value, MemberTypes.ORDINARY)
            )
            for entry in conn.entries
            if entry and entry['uid'] and entry['employeeType'] in types_of_members
        ]

def retrieve_candidature(
        request: Request
    ) -> Tuple[Optional[Candidature], Dict]:
    """Retrieve an existing candidature from the session or URL and check if
    the OID in the URL is coherent with the OID in the session if it exists.

    Parameters:
    - request (Request): The Pyramid request object.

    Returns:
    - tuple: A tuple containing the candidature object and an error dict if applicable.
    """
    session_oid = None
    decrypted_oid = None
    user_oid = None
    candidature = None

    # Check if the candidature OID is in the session
    if CANDIDATURE_OID in request.session:
        session_oid = request.session[CANDIDATURE_OID]
        candidature = get_candidature_by_oid(session_oid, request)

    # Check if the candidature OID is in the URL
    if "oid" in request.params:
        encrypted_oid = request.params.get("oid", None)
        decrypted_oid, seed = decrypt_oid(
            encrypted_oid,
            SEED_LENGTH,
            request.registry.settings['session.secret']
            )
        candidature = get_candidature_by_oid(decrypted_oid, request)
        if candidature is None:
            error = _('candidature_not_found')
            return None, {'candidature': None,
                'MemberTypes': MemberTypes,
                'error': error}
        if seed != candidature.email_send_status_history[-1].seed:
            error = _('url_is_obsolete')
            return None, {'candidature': candidature,
                'MemberTypes': MemberTypes,
                'error': error,
                'url_obsolete': True}

    # Check if the user is in the session
    if "user" in request.session:
        json_user = request.session["user"]
        user = json.loads(json_user)
        if "oid" in user:
            user_oid = user["oid"]
            candidature = get_candidature_by_oid(user_oid, request)
        else:
            log.error(f"User oid not in user json session parameter: {user_oid}")
            raise ValueError("User oid not in user json session parameter")

    # Legitimate upgrade case (issue #256): a logged-in member opening
    # an upgrade candidature carries session_oid != user_oid by design
    # — the candidature itself proves the link via existing_member_oid.
    if session_oid and user_oid and session_oid != user_oid:
        session_candidature = get_candidature_by_oid(session_oid, request)
        if (session_candidature is not None
                and getattr(session_candidature, 'existing_member_oid',
                            None) == user_oid):
            candidature = session_candidature
            user_oid = session_oid

    # Check if the candidature OID in the session and user and URL match
    if ((session_oid and decrypted_oid
        and session_oid != decrypted_oid)
        or (session_oid and user_oid
            and session_oid != user_oid)
        or (decrypted_oid and user_oid and decrypted_oid != user_oid)):
        # The candidature OID in the session and URL do not match.
        # This is likely due to a URL call with a different OID.
        # We reset the session and send a message inviting the user to log in again.
        logout(request)
        return None, {
            'candidature': None,
            'MemberTypes': None,
            'error': _('candidature_mixed',
                default='The candidature ID in the session and URL do not match.',
                mapping={"site_name":SITE_NAME, "domain_name":DOMAIN_NAME, "organization_details":ORGANIZATION_DETAILS}),
        }

    if not (decrypted_oid or session_oid or user_oid):
        # New candidature
        candidature = Candidature()
        # Add the candidature to the candidature list
        get_candidatures(request)[candidature.oid] = candidature

    if candidature:
        request.session[CANDIDATURE_OID] = candidature.oid
    else:
        log.error(f"No candidature found for oid {decrypted_oid or session_oid or user_oid}")
        return None, {
            'candidature': None,
            'MemberTypes': None,
            'error': _('candidature_not_found'),
        }
    return candidature, None

def safe_local_redirect(url, request):
    """Validate a stored redirect target against open-redirect abuse.

    ``login_view`` honours ``session['redirect_url']`` after a successful
    authentication (external audit, 2026-08-01: the value used to be
    followed blindly). Legitimate writers (``vote``, ``get_email``) store
    ``request.current_route_url()`` — an *absolute* URL of this very site —
    so the rule is: an absolute ``http(s)`` URL is followed only when its
    authority is exactly this request's host (user-info tricks like
    ``https://host@evil`` fail that equality); a relative target must be a
    local absolute path (``/…`` but not the protocol-relative ``//…``);
    backslashes and every other scheme are refused. Anything unsafe
    returns ``None`` and the caller falls back to home.
    """
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if '\\' in url:
        return None
    parts = urlparse(url)
    if parts.scheme and parts.scheme not in ('http', 'https'):
        return None
    if parts.netloc:
        if parts.netloc != request.host:
            return None
    elif not parts.path.startswith('/') or parts.path.startswith('//'):
        return None
    return url


def is_not_a_valid_email_address(
        email:str,
        check_mx:bool=True
    )->Union[Dict[str, str], None]:
    """Check if the email is not a valid email address.
    Args:
        email (str): the email to check
        check_mx (bool): check the mx record
    Returns:
        error: the error if the email is not valid
        None: if the email is valid
    """
    try:
        if not validate_email(email, check_mx=check_mx and not DISABLE_EMAIL_MX_CHECKS):
            return {'error': _('invalid_email')}
    except Exception as e:
        log.error(f"Error while validating email {email}: {e}")
        return {'error': _('connection_error')}
    return None

def is_valid_email(email, request, check_mx=True):
    """Check if the email is valid and not used in LDAP.

    Args:
        email (str): the email to check
        request (pyramid.request.Request): the request
        check_mx (bool): check the mx record

    Returns:
        error: the error if the email is not valid
        None: if the email is valid
    """
    if err := is_not_a_valid_email_address(email, check_mx):
        return err
    try:
        # Verify that the email is not already registered in candidatures
        candidatures = get_candidatures(request)
        for candidature in candidatures.values():
            if candidature.email == email and candidature.candidature_state != CandidatureStates.REFUSED:
                return {'error': _('email_allready_exist')}
        # Verify that the email is not already registered in LDAP
        entries = get_member_by_email(email)
        if len(entries) != 0:
            # If already registered, display an error message
            return {'error': _('email_allready_exist')}
    # The email is valid and not already used
    except:
        log.error(f"Error while checking email {email} in LDAP with {LDAP_SERVER=}, {LDAP_LOGIN=}, {LDAP_OU=}, {LDAP_BASE_DN=}")
        return {'error': _('ldap_error')}
    return None

def is_valid_unique_pseudonym(pseudonym):
    """Check if pseudonym is valid and is not already used.

    Args:
        pseudonym (str): the pseudonym to check

    Returns:
        error: the error if the email is not valid or already used
        None: if the email is valid and not already used
    """
    if not pseudonym_pattern.match(pseudonym):
        return {'error': _('invalid_pseudonym', {
                "MIN_PSEUDONYM_LENGTH":MIN_PSEUDONYM_LENGTH,
                "MAX_PSEUDONYM_LENGTH":MAX_PSEUDONYM_LENGTH
            })}

    if len(pseudonym) < MIN_PSEUDONYM_LENGTH:
        return {
            'error': _('pseudonym_too_short'),
            'error_details':_("pseudonym_minimum_length",
                {"MIN_PSEUDONYM_LENGTH":MIN_PSEUDONYM_LENGTH})
        }
    if len(pseudonym) > MAX_PSEUDONYM_LENGTH:
        return {
            'error': _('pseudonym_too_long'),
            'error_details':_("pseudonym_maximum_length",
                {"MAX_PSEUDONYM_LENGTH":MAX_PSEUDONYM_LENGTH})
        }

    # define an unsecure LDAP server, requesting info on DSE and schema
    with get_ldap_connection(ldap_user=LDAP_USER,
        ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        # Verify that the pseudonym is not already registered
        conn.search(
            LDAP_BASE_DN,
            f"(cn={escape_filter_chars(pseudonym)})",
            attributes=['cn']
        ) # search for the user in the LDAP directory
        # Verify that the candidate is not already registered
        if len(conn.entries) != 0:
            # If already registered, display an error message
            return {'error': _('pseudonym_allready_exists')}
    # The pseudonym is valid and not already used
    return None

def is_valid_password(password):
    """Check if the password is valid.

    Args:
        password (str): the password to check

    Returns:
        error: the error if the password is not valid
        None: if the password is valid
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return {
            'error': _('password_too_short'),
            'error_details':_("password_minimum_length",
            mapping={'password_minimum_length':MIN_PASSWORD_LENGTH})
        }
    if len(password) > MAX_PASSWORD_LENGTH:
        return {
            'error': _('password_too_long'),
            'error_details':_("password_maximum_length",
            mapping={'password_maximum_length':MAX_PASSWORD_LENGTH})
        }
    if not any(char.isdigit() for char in password):
        return {'error': _('password_must_contain_digit')}
    if not any(char.isupper() for char in password):
        return {'error': _('password_must_contain_uppercase')}
    if not any(char.islower() for char in password):
        return {'error': _('password_must_contain_lowercase')}
    if not any(
        char in SPECIAL_CHARACTERS
        for char in password
    ):
        return {'error': _('password_must_contain_special_char')}
    # The password is valid
    return None

def send_email(
        request:Request,
        subject:str,
        recipients:list,
        template_path:str,
        template_vars: Optional[Dict] = None,
        format_vars: Optional[Dict[str, Any]] = None,
        derive_subject_from_title: bool = False
    ) -> bool:
    """
    Generic function to send emails.

    Args:
        request: The incoming Pyramid request object.
        subject: Subject of the email.
        recipients: List of email addresses to send the email to.
        template_path: Path to the email body template.
        template_vars: Variables to be used in the template.

    Returns:
        bool: True if email is sent successfully, otherwise False.
    """
    template_vars = template_vars or {}

    def clean_text(text):
        # Remove redundant newlines and HTML DOCTYPE
        text = re.sub(r'\n{2,}', '\n', text)
        text = re.sub(r'<!DOCTYPE html>\n?', '', text)
        return text.strip()

    def extract_subject_from_html(body: str) -> Optional[str]:
        match = re.search(r'<title>(.*?)</title>', body, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        raw_title = re.sub(r'\s+', ' ', match.group(1).strip())
        return html.unescape(raw_title)

    base_values = {**template_vars, "textual": True}
    text_body = render_to_response(
        template_path,
        request=request,
        value=base_values
    ).text
    text_body = clean_text(text_body)

    html_values = {**template_vars, "textual": False}
    html_body = render_to_response(
        template_path,
        request=request,
        value=html_values
    ).body.decode('utf-8')

    if format_vars:
        try:
            text_body = text_body.format(**format_vars)
            html_body = html_body.format(**format_vars)
        except KeyError as exc:
            log.error(f"Missing email format variable {exc} for template {template_path}")
            raise

    resolved_subject = subject
    if derive_subject_from_title and not resolved_subject:
        resolved_subject = extract_subject_from_html(html_body)

    if not resolved_subject:
        raise ValueError("Subject must be provided or derivable from the template title.")

    sender = request.registry.settings['mail.default_sender']

    message = Message(
        subject=resolved_subject,
        sender=sender,
        recipients=recipients,
        body=text_body,
        html=html_body,
        extra_headers={'Content-Transfer-Encoding': 'quoted-printable',
            'Content-Type': "text/plain; charset='utf-8'"},
    )
    log.debug(f"Email {subject} is prepared and will be sent to {recipients} from {sender} and contains {text_body}")

    mailer = request.registry['mailer']
    status = mailer.send(message) # Remember the message is not sent until the transaction is committed

    if status is None:
        log.error(f"Error while preparing sending email {subject} to {recipients}")
        return False
    else:
        log.info(f"Email {subject} will be sent to {recipients}")
        return True


def generate_math_challenges(request: Request)->Dict[str, str]:
    """Generate four simple math challenges.
    Args:
        request (pyramid.request.Request): the request
    return:
        dict: A dictionary containing the math challenges and their solutions.
    """
    challenges = {}
    numbers = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    number_dict = {word: index for index, word in enumerate(numbers)}
    localizer = get_localizer(request)
    for label in ["A", "B", "C", "D"]:
        num1 = random.randint(1, 9)
        str_num1 = localizer.translate(_(numbers[num1]))
        num2 = random.randint(1, 9)
        str_num2 = localizer.translate(_(numbers[num2]))
        num3 = random.randint(1, 9)
        str_num3 = localizer.translate(_(numbers[num3]))
        str_times = localizer.translate(_("times"))
        str_plus = localizer.translate(_("plus"))
        str_plus_prefix = localizer.translate(_("plus_prefix"))
        challenge_str = f"{str_num1} {str_times} {str_num2}{str_plus_prefix}{str_plus} {str_num3}"
        challenge_solution = num1 * num2 + num3
        challenges[label] = (challenge_str, challenge_solution)
    return challenges

def get_candidature_by_oid(
        oid:str,
        request:Request
    ) -> Candidature:
    """Get the candidature by its oid.
    Args:
        oid (str): the oid of the candidature
        request (pyramid.request.Request): the request
    Returns:
        Candidature: the candidature or None if not found or not a Candidature
    """
    candidatures = get_candidatures(request)
    candidature = candidatures[oid] if oid in candidatures else None
    if not isinstance(candidature, Candidature):
        candidature = None
    return candidature

def get_member_by_oid(
        oid:str,
        request:Request,
        update:bool=False
    ) -> Member:
    """Get the member by its oid.
    Args:
        oid (str): the oid of the member
        request (pyramid.request.Request): the request
        update (bool): update the member from ldap if not found
    Returns:
        Member: the member or None if not found or not a Member
    """
    if oid == LDAP_ADMIN_OID:
        # The admin is not an ldap member
        user = get_admin_user(request) # Force the creation of the admin Member if it does not exist
        return get_members(request)[LDAP_ADMIN_OID]
    members = get_members(request)
    member = members[oid] if oid in members else None
    if update and not isinstance(member, Member):
        update_member_from_ldap(oid, request)
        member = None
    return member

def append_member(
        member: Member,
        request: Request):
    """Append the member to the list of members.
    Args:
        member (Member): the member
        request (pyramid.request.Request): the request
    """
    members = get_members(request)
    members[member.oid] = member

def update_member_from_ldap(
        oid: str,
        request: Request
    ) -> Union[Member, None]:
    """Update the members from LDAP.
    Args:
        oid (str): the oid of the user
        request (pyramid.request.Request): the request
    Returns:
        Member: the member
        None: if not found in ldap
    """
    try:
        with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
            # Extend the list of attributes retrieved to include all those
            # added during registration
            conn.search(
                LDAP_BASE_DN,
                f'(uid={escape_filter_chars(oid)})',
                attributes=schema_safe_attributes(conn, [
                    'cn', 'mail', 'employeeType', 'sn', 'uid',
                    'employeeNumber', 'isActive', 'givenName', 'nationality',
                    'birthdate', 'preferredLanguage', 'secondLanguage',
                    'thirdLanguage','cooperativeBehaviourMark',
                    'cooperativeBehaviourMarkUpdate', 'numberSharesOwned',
                    'dateEndValidityYearlyContribution', 'uniqueMemberOf',
                    'iban', 'dateErasureAllData'
                ])
            )
            if len(conn.entries) == 0:
                if oid == LDAP_ADMIN_OID:
                    # If the admin is not found in LDAP, we fake it
                    return get_members(request)[LDAP_ADMIN_OID]
                log.warning(f"User {oid} not found in LDAP")
                return None
            member_entry = conn.entries[0]
            new_email = member_entry.mail.value if hasattr(member_entry, 'mail') else None
            new_pseudonym = member_entry.cn.value if hasattr(member_entry, 'cn') else None
            if hasattr(member_entry, 'employeeType') and member_entry.employeeType.value:
                try:
                    new_type = MemberTypes[member_entry.employeeType.value]
                except KeyError:
                    log.warning(f"Unknown employeeType '{member_entry.employeeType.value}' for {oid}, defaulting to ORDINARY")
                    new_type = MemberTypes.ORDINARY
            else:
                new_type = None
            new_fullname = member_entry.givenName.value if hasattr(member_entry, 'givenName') else None
            new_nationality = member_entry.nationality.value if hasattr(member_entry, 'nationality') else None
            new_birthdate = member_entry.birthdate.value if hasattr(member_entry, 'birthdate') else None
            def get_date(date_str: str, oid: str) -> Optional[datetime]:
                """Helper function to parse date strings."""
                try :
                    return datetime.strptime(date_str, LDAP_TIME_FORMAT)
                except ValueError:
                    log.error(f"Invalid date format for {oid}: {date_str}")
                    try:
                        # Try to parse as ISO format
                        return datetime.fromisoformat(date_str)
                    except ValueError:
                        log.error(f"Date format is not ISO for {oid}: {date_str}")
                        return None
            if new_birthdate:
                new_birthdate = new_birthdate[:LDAP_TIME_LENGTH] # Ensure correct length
                new_birthdate = get_date(new_birthdate, oid)
            new_preferred_language = member_entry.preferredLanguage.value if hasattr(member_entry, 'preferredLanguage') else None
            new_second_language = member_entry.secondLanguage.value if hasattr(member_entry, 'secondLanguage') else None
            new_third_language = member_entry.thirdLanguage.value if hasattr(member_entry, 'thirdLanguage') else None
            member = get_member_by_oid(oid, request, False)
            cooperative_behaviour_mark = (
                float(member_entry.cooperativeBehaviourMark.value
                    or DEFAULT_COOPERATIVE_BEHAVIOUR_MARK)
                if hasattr(member_entry, 'cooperativeBehaviourMark')
                else DEFAULT_COOPERATIVE_BEHAVIOUR_MARK)
            cooperative_behaviour_mark_update = member_entry.cooperativeBehaviourMarkUpdate.value if hasattr(member_entry, 'cooperativeBehaviourMarkUpdate') else None
            if cooperative_behaviour_mark_update:
                cooperative_behaviour_mark_update = cooperative_behaviour_mark_update[:LDAP_TIME_LENGTH]
                cooperative_behaviour_mark_update = get_date(cooperative_behaviour_mark_update, oid)
            number_shares_owned = member_entry.numberSharesOwned.value if hasattr(member_entry, 'numberSharesOwned') else None
            date_end_validity_yearly_contribution = member_entry.dateEndValidityYearlyContribution.value if hasattr(member_entry, 'dateEndValidityYearlyContribution') else None
            if date_end_validity_yearly_contribution:
                date_end_validity_yearly_contribution = date_end_validity_yearly_contribution[:LDAP_TIME_LENGTH]
                date_end_validity_yearly_contribution = get_date(date_end_validity_yearly_contribution, oid)
            unique_member_of = member_entry.uniqueMemberOf.value if hasattr(member_entry, 'uniqueMemberOf') else None
            iban = member_entry.iban.value if hasattr(member_entry, 'iban') else None
            date_erasure_all_data = member_entry.dateErasureAllData.value if hasattr(member_entry, 'dateErasureAllData') else None

        log.debug(f"Update Member {oid} with ldap informations")
        if not member:
            log.debug(f"Create Member {oid} with informations found in LDAP with {new_email=}, {new_pseudonym=}, {new_type=}, {new_fullname=}, {new_nationality=}, {new_birthdate=}, {new_preferred_language=}, {new_second_language=}")
            datas = MemberDatas(
                fullname=new_fullname,
                fullsurname = new_fullname,
                nationality = new_nationality,
                birthdate = new_birthdate,
                password = None,
                password_confirm = None,
                lang1 = new_preferred_language,
                lang2 = new_second_language,
                lang3 = new_third_language,
                role = new_type,
                cooperative_behaviour_mark = cooperative_behaviour_mark,
                cooperative_behaviour_mark_update = cooperative_behaviour_mark_update,
                number_shares_owned = number_shares_owned,
                date_end_validity_yearly_contribution = date_end_validity_yearly_contribution,
                unique_member_of = unique_member_of,
                iban = iban,
                date_erasure_all_data = date_erasure_all_data
            )
            member = Member(
                email=new_email,
                pseudonym=new_pseudonym,
                oid=oid,
                type=new_type,
                data=datas
            )
            append_member(member, request)
        else :
            # Update the member object with the data retrieved from LDAP
            if new_email and member.email != new_email:
                log.debug(f"Update Member {oid} with new email {new_email}")
                member.email = new_email
            if new_pseudonym and member.pseudonym != new_pseudonym:
                log.debug(f"Update Member {oid} with new pseudonym {new_pseudonym}")
                member.pseudonym = new_pseudonym
            if new_type and member.type != new_type:
                log.debug(f"Update Member {oid} with new type {new_type}")
                member.type = new_type
            # Add additional fields for cooperators
            if new_fullname and member.data.fullname != new_fullname:
                log.debug(f"Update Member {oid} with new fullname {new_fullname}")
                member.data.fullname = new_fullname
            if new_nationality and member.data.nationality != new_nationality:
                log.debug(f"Update Member {oid} with new nationality {new_nationality}")
                member.data.nationality = new_nationality
            if new_birthdate and member.data.birthdate != new_birthdate:
                log.debug(f"Update Member {oid} with new birthdate {new_birthdate}")
                member.data.birthdate = new_birthdate
            if new_preferred_language and member.data.lang1 != new_preferred_language:
                log.debug(f"Update Member {oid} with new preferred language {new_preferred_language}")
                member.data.lang1 = new_preferred_language
            if new_second_language and member.data.lang2 != new_second_language:
                log.debug(f"Update Member {oid} with new second language {new_second_language}")
                member.data.lang2 = new_second_language
        return member
    except LDAPException as e:
        log.error(f"LDAP connection/query error for user {oid}: {e}")
        raise
    except Exception as e:
        log.error(f"Unexpected error while processing LDAP data for {oid}: {e}")
        raise

def get_candidature_from_request(request: Request) -> Optional[Candidature]:
    """Get the candidature from the request.

    The candidature is identified by the encrypted ``oid`` URL parameter.

    Args:
        request (pyramid.request.Request): the request
    Returns:
        Candidature | None: the candidature, or None if the oid is missing,
        invalid, expired, unknown, or its seed does not match.
    """
    encrypted_oid = request.params.get("oid")
    if not encrypted_oid:
        return None

    decrypted_oid, seed = decrypt_oid(
        encrypted_oid,
        Candidature.SEED_SIZE,
        request.registry.settings['session.secret']
    )
    if decrypted_oid is None:
        return None
    candidature = get_candidature_by_oid(decrypted_oid, request)
    if candidature is None or seed != candidature.seed:
        log.warning(
            f"Invalid or obsolete candidature link for oid {decrypted_oid}"
        )
        return None
    return candidature

def generate_key(secret:str)->bytes:
    """Generate a key from the secret.
    Args:
        secret (str): The secret to use to generate the key
    Returns:
        bytes: The key
    """
    sha256 = hashlib.sha256()
    sha256.update(secret.encode())
    return sha256.digest()

def decrypt_oid(
    encrypted_oid: str,
    seed_size: int,
    secret: str,
    ttl: Optional[int] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Decrypt the OID using the SECRET and return the decrypted OID and seed.

    The Fernet token embeds its creation time, so a token older than ``ttl``
    seconds is rejected: reset and verification links expire. Any failure
    (tampered, malformed or expired token) returns ``(None, None)`` instead of
    raising, so callers can handle an invalid link gracefully.

    Args:
        encrypted_oid (str): The encrypted OID.
        seed_size (int): The size of the seed.
        secret (str): The secret to use to decrypt the OID.
        ttl (int | None): Maximum token age in seconds. When None (default),
            OID_LINK_TTL_SECONDS is read at call time.

    Returns:
        tuple: (decrypted OID, seed), or (None, None) if the token is invalid
        or expired.
    """
    if ttl is None:
        ttl = OID_LINK_TTL_SECONDS
    fernet = Fernet(secret)
    try:
        decoded_encrypted_oid = base64.urlsafe_b64decode(encrypted_oid)
        decrypted_message = fernet.decrypt(decoded_encrypted_oid, ttl=ttl).decode()
    except (InvalidToken, ValueError, TypeError) as e:
        log.warning(f"Invalid or expired OID token: {e}")
        return None, None
    index = len(decrypted_message) - seed_size
    return decrypted_message[:index], decrypted_message[index:]

def encrypt_oid(oid: str, seed: str, secret: str) -> str:
    """Encrypt the OID using the SECRET and return the encrypted OID.

    Args:
        oid (str): The OID to encrypt.
        seed (str): The seed.
        secret (str): The secret to use to encrypt the OID.

    Returns:
        str: The encrypted OID.
    """
    concatenated_string = oid + seed
    fernet = Fernet(secret)
    encrypted_message = fernet.encrypt(concatenated_string.encode())
    encoded_encrypted_message = base64.urlsafe_b64encode(
        encrypted_message).decode()

    return encoded_encrypted_message

from typing import List, Dict

def get_potential_voters(conn: Connection) -> List[Dict[str, str]]:
    """Fetch potential voters from LDAP.

    Args:
        conn (Connection): The LDAP connection object.

    Returns:
        list: List of potential voters (uid, cn, mail, sn).
    """
    filter_str = '(&(employeeType=cooperator)(cn=*)(mail=*))'
    conn.search(LDAP_BASE_DN, filter_str, attributes=['uid', 'cn', 'mail', 'sn'])
    return conn.entries

def get_admin_user(request)->  User:
        """return the admin User from the settings.
        Args:
            request (pyramid.request.Request): the request
        Returns:
            User: The admin from the settings
        """
        name = ADMIN_LOGIN
        mail = ADMIN_EMAIL
        oid = LDAP_ADMIN_OID
        admin_user = User(name, mail, oid, True, MemberTypes.ADMINISTRATOR.name)
        if LDAP_ADMIN_OID not in get_members(request) :
            # If the admin user is not in the members, we add it
            admin_data = MemberDatas(
                fullname=name,
                fullsurname=name,
                lang1='en',
                lang2='fr',
                role=MemberTypes.ADMINISTRATOR,
                cooperative_behaviour_mark=DEFAULT_COOPERATIVE_BEHAVIOUR_MARK
            )
            admin_member = Member(admin_data, LDAP_ADMIN_OID, MemberStates.REGISTRED, MemberTypes.ADMINISTRATOR, mail)
            get_members(request)[LDAP_ADMIN_OID] = admin_member
        return admin_user

def random_voters(request: Request) -> List[Dict[str, str]]:
    """
    Randomly select the number of voters defined in settings to validate the
    candidate's personal data.

    Args:
        request (pyramid.request.Request): The request.

    Returns:
        list: A list of voters in the format:
            [{'cn': 'name', 'sn': 'surname', 'mail': 'email'}, ...]
    """
    # Get the number of voters from the settings
    try:
        number_of_voters = int(request.registry.settings['number_of_voters'])
    except:
        number_of_voters = DEFAULT_NUMBER_OF_VOTERS
        log.warning(f"Use {DEFAULT_NUMBER_OF_VOTERS=} "
            "as number of voters due to exception.")
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD),
            ldap_auto_bind=True
        ) as conn:
        potential_voters = get_potential_voters(conn)
        random.shuffle(potential_voters)
        selected_voters = potential_voters[:number_of_voters]

        voters = [
            {
                'uid': voter.uid.value,
                'cn': voter.cn.value,
                'sn': voter.sn.value if hasattr(voter, "sn") else voter.cn.value,
                'mail': voter.mail.value
            }
            for voter in selected_voters
        ]

        # If there are fewer than number_of_voters voters, add the admin
        if len(voters) < number_of_voters:
            voters.append(
                {
                    'uid': LDAP_ADMIN_OID,
                    'cn': ADMIN_LOGIN,
                    'sn': 'Administrator',
                    'mail': ADMIN_EMAIL
                }
            )

        return voters[:number_of_voters]  # Ensure only top number_of_voters are returned

def get_oid_from_pseudonym(
    pseudonym: str,
    request: Request
    ) -> Union[str, None]:
    """Get the oid from the pseudonym and ldap.

    Args:
        pseudonym (str): the pseudonym
        request (pyramid.request.Request): the request

    Returns:
        str: the oid, None if not found
    """
    #verify pseudonym is valid
    pseudonym = pseudonym.strip()
    if not pseudonym_pattern.match(pseudonym):
        return None
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD),
            ldap_auto_bind=True
        ) as conn:
        conn.search(
            LDAP_BASE_DN,
            f'(cn={escape_filter_chars(pseudonym)})',
            attributes=['employeeNumber']
        ) # search for the user in the LDAP directory
        if len(conn.entries) == 0:
            return None
        member_entry = conn.entries[0]
        return member_entry.employeeNumber.value

def secure_password_fields(parameters: dict) -> dict:
    """Hash the ``password`` field and drop ``password_confirm`` before the dict
    is persisted (finding 1.3): the ZODB must never hold a cleartext password.

    ``make_ldap_password`` is idempotent, so already-hashed values pass through
    unchanged. The returned dict is the same object, mutated in place.
    """
    if parameters.get('password'):
        parameters['password'] = make_ldap_password(parameters['password'])
    if 'password_confirm' in parameters:
        parameters['password_confirm'] = None
    return parameters


def deactivate_member_in_ldap(request, member, erasure_date):
    """Deactivate the LDAP entry of a resigning member (spec "Démissionner").

    The entry is kept — the pseudonym and the identity data must stay
    reserved during the Quarantine period for the uniqueness checks of new
    applications — but isActive turns False so no login is possible, and
    dateErasureAllData records when the purge is due.
    """
    dn = (f"uid={member.oid},{LDAP_OU},{LDAP_BASE_DN}"
          if LDAP_OU else f"uid={member.oid},{LDAP_BASE_DN}")
    changes = {
        'isActive': [(MODIFY_REPLACE, ["False"])],
        'dateErasureAllData': [(MODIFY_REPLACE, [
            erasure_date.strftime(LDAP_TIME_FORMAT)])],
    }
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        try:
            if not conn.modify(dn, changes):
                log.error(f"deactivate_member_in_ldap: modify failed for "
                          f"{dn}: {conn.result}")
                return {'status': 'error',
                        'message': _('unsubscription_failed')}
        except Exception as e:
            log.error(f"deactivate_member_in_ldap: {e}")
            return {'status': 'error', 'message': _('unsubscription_failed')}
    # ``=> None`` in issue #148: a resigned member leaves every dynamic
    # group (the entry itself stays during the Quarantine period).
    from alirpunkto.dynamic_groups import sync_member_groups
    sync_member_groups(request, member.oid)
    log.info(f"Member {member.oid} deactivated in LDAP; erasure due "
             f"{erasure_date.isoformat()}")
    return {'status': 'success'}


def purge_unsubscribed_members(request, now=None):
    """Purge unsubscribed members whose Quarantine period has expired.

    Per the specification, everything is deleted except the pseudonym, the
    departure date and the reason: the LDAP entry is removed, the ZODB
    member keeps only those three facts and moves to DELETED. Meant to be
    called periodically (cron / console script); returns the purged oids.
    """
    now = now or datetime.now()
    members = get_members(request)
    purged = []
    for oid, member in list(members.items()):
        if getattr(member, 'member_state', None) != MemberStates.UNSUBSCRIBED:
            continue
        due = getattr(getattr(member, 'data', None),
                      'date_erasure_all_data', None)
        if due is None or _as_datetime(due) > now:
            continue
        dn = (f"uid={oid},{LDAP_OU},{LDAP_BASE_DN}"
              if LDAP_OU else f"uid={oid},{LDAP_BASE_DN}")
        try:
            with get_ldap_connection(ldap_user=LDAP_USER,
                    ldap_password=get_secret(LDAP_PASSWORD)) as conn:
                conn.delete(dn)
        except Exception as e:
            log.error(f"purge_unsubscribed_members: LDAP delete failed for "
                      f"{oid}: {e}")
            continue
        pseudonym = member.pseudonym
        # Capture what the farewell message needs before erasing (issue
        # #54): the ticket wants the member informed that the identity
        # data was indeed erased — and after the purge, the address is
        # gone from our stores.
        recipient = getattr(member, 'email', None)
        language = getattr(getattr(member, 'data', None), 'lang1', None)
        member.data = MemberDatas(password='')
        member.member_state = MemberStates.DELETED
        member.departure_reason = getattr(
            member, 'departure_reason', 'resignation')
        member.email = None
        _send_erasure_confirmation(request, recipient, language, pseudonym)
        log.info(f"purge_unsubscribed_members: {oid} ({pseudonym}) purged")
        purged.append(oid)
    return purged


def _send_erasure_confirmation(request, recipient, language, pseudonym):
    '''Tell the former member their identity data was erased (issue #54).

    Best effort: the purge itself must not fail on a mail hiccup. And
    deliberately content-minimal: the pseudonym is the only retained fact,
    so it is the only personal thing the message carries.
    '''
    if not recipient:
        return
    try:
        language = language if language in ('en', 'fr') else 'en'
        template = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'locale', language,
            'LC_MESSAGES', 'erasure_confirmation_email.pt')
        if not os.path.exists(template):
            template = template.replace(f"/{language}/", "/en/")
        subject = _translate_for_language(
            request, language, _('erasure_confirmation_email_subject'))
        send_email(request, subject, [recipient], template, {
            'pseudonym': pseudonym,
            'site_name': SITE_NAME,
            'domain_name': DOMAIN_NAME,
            'organization_details': ORGANIZATION_DETAILS,
            'textual': False,
        })
    except Exception as e:
        log.warning(f"_send_erasure_confirmation: could not inform "
                    f"{recipient}: {e}")


def _as_datetime(value):
    """Accept date or datetime for the erasure due date."""
    if isinstance(value, datetime):
        return value
    return datetime(value.year, value.month, value.day)


def upgrade_member_in_ldap(request, candidature, member_oid):
    """Turn an existing Ordinary Member into a Cooperator in LDAP (issue #7).

    The entry keeps its uid, cn (pseudonym), mail and userPassword; only the
    membership type, the identity attributes gathered by the upgrade
    candidature and the group memberships change. On success the ZODB member
    is refreshed from LDAP so both stores agree.
    """
    dn = (f"uid={member_oid},{LDAP_OU},{LDAP_BASE_DN}"
          if LDAP_OU else f"uid={member_oid},{LDAP_BASE_DN}")
    try:
        changes = {
            'employeeType': [(MODIFY_REPLACE, [MemberTypes.COOPERATOR.name])],
            'sn': [(MODIFY_REPLACE, [candidature.data.fullsurname])],
            'gn': [(MODIFY_REPLACE, [candidature.data.fullname])],
            'nationality': [(MODIFY_REPLACE, [candidature.data.nationality])],
            'birthdate': [(MODIFY_REPLACE, [
                candidature.data.birthdate.strftime(LDAP_TIME_FORMAT)])],
        }
    except Exception as e:
        log.error(f"upgrade_member_in_ldap: cannot prepare changes for "
                  f"{member_oid}: {e}")
        return {'status': 'error', 'message': _('registration_failed')}
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        try:
            success = conn.modify(dn, changes)
            if not success:
                log.error(f"upgrade_member_in_ldap: modify failed for {dn}: "
                          f"{conn.result}")
                return {'status': 'error',
                        'message': _('registration_failed')}
        except Exception as e:
            log.error(f"upgrade_member_in_ldap: {e}")
            return {'status': 'error', 'message': _('registration_failed')}
    # Place the upgraded member in the dynamic groups of issue #148: with
    # no share and no yearly contribution yet, that is
    # candidatesMissingShareYearContribGroup — not cooperatorsGroup.
    from alirpunkto.dynamic_groups import sync_member_groups
    sync_member_groups(request, member_oid)
    try:
        # Refresh the ZODB member from the updated LDAP entry.
        update_member_from_ldap(member_oid, request)
    except Exception as e:
        log.warning(f"upgrade_member_in_ldap: ZODB refresh failed for "
                    f"{member_oid}: {e}")
    log.info(f"Member {member_oid} upgraded to Cooperator in LDAP")
    return {'status': 'success'}


def get_member_avatar(request, member_oid):
    """Return the jpegPhoto bytes of a member, or None (issue #150)."""
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        conn.search(LDAP_BASE_DN,
                    f'(uid={escape_filter_chars(member_oid)})',
                    attributes=['jpegPhoto'])
        if not conn.entries:
            return None
        entry = conn.entries[0]
        if 'jpegPhoto' not in entry or not entry.jpegPhoto.value:
            return None
        value = entry.jpegPhoto.value
        return value[0] if isinstance(value, list) else value


def set_member_avatar(request, member_oid, jpeg_bytes):
    """Store the avatar of a member as jpegPhoto (issue #150)."""
    dn = (f"uid={member_oid},{LDAP_OU},{LDAP_BASE_DN}"
          if LDAP_OU else f"uid={member_oid},{LDAP_BASE_DN}")
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        try:
            if not conn.modify(dn, {'jpegPhoto': [
                    (MODIFY_REPLACE, [jpeg_bytes])]}):
                log.error(f"set_member_avatar: modify failed for {dn}: "
                          f"{conn.result}")
                return {'status': 'error',
                        'message': _('avatar_update_failed_error')}
        except Exception as e:
            log.error(f"set_member_avatar: {e}")
            return {'status': 'error',
                    'message': _('avatar_update_failed_error')}
    log.info(f"Avatar updated for {member_oid} "
             f"({len(jpeg_bytes)} bytes)")
    return {'status': 'success'}


def delete_member_avatar(request, member_oid):
    """Remove the avatar of a member (issue #150)."""
    dn = (f"uid={member_oid},{LDAP_OU},{LDAP_BASE_DN}"
          if LDAP_OU else f"uid={member_oid},{LDAP_BASE_DN}")
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        try:
            conn.modify(dn, {'jpegPhoto': [(MODIFY_REPLACE, [])]})
        except Exception as e:
            log.error(f"delete_member_avatar: {e}")
            return {'status': 'error',
                    'message': _('avatar_update_failed_error')}
    return {'status': 'success'}


def is_valid_unique_identity(fullname, fullsurname, birthdate):
    """Check that the identity data is not already used (issue #54).

    The given name(s) + family name(s) + date of birth combination is
    compared against every LDAP entry — deliberately including inactive
    ones: a resigned or excluded Cooperator keeps their entry during the
    Quarantine period precisely so they cannot register again with a
    virgin reputation.

    Returns None when the identity is free, an error mapping otherwise.
    """
    if isinstance(birthdate, str):
        try:
            birthdate = datetime.strptime(birthdate, '%Y-%m-%d')
        except ValueError:
            try:
                birthdate = datetime.strptime(birthdate, LDAP_TIME_FORMAT)
            except ValueError:
                return {'error': _('invalid_date')}
    if isinstance(birthdate, date) and not isinstance(birthdate, datetime):
        birthdate = datetime(birthdate.year, birthdate.month, birthdate.day)
    birthdate_str = birthdate.strftime(LDAP_TIME_FORMAT)
    query = (f"(&(gn={escape_filter_chars(fullname)})"
             f"(sn={escape_filter_chars(fullsurname)})"
             f"(birthdate={escape_filter_chars(birthdate_str)}))")
    with get_ldap_connection(ldap_user=LDAP_USER,
            ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        conn.search(LDAP_BASE_DN, query, attributes=['uid'])
        if conn.entries:
            log.warning(
                f"is_valid_unique_identity: identity already used by "
                f"{[str(e.uid) for e in conn.entries]}")
            return {'error': _(
                'This identity (names and date of birth) is already '
                'registered — possibly by a member who resigned or was '
                'excluded less than the Quarantine period ago.')}
    return None


def register_user_to_ldap(request, candidature, password):
    """
    Register a user to the LDAP directory.

    Args:
        request (pyramid.request.Request): the request.
        candidature (Candidature): the candidature of the user to register.

    Returns:
        dict: a dictionary containing the result of the registration.
    """

    # Upgrade of an existing member (issue #7): the LDAP entry already
    # exists under the member's own uid and the pseudonym is legitimately
    # "taken" by that very member — update the entry in place instead of
    # adding a duplicate.
    existing_member_oid = getattr(candidature, 'existing_member_oid', None)
    if existing_member_oid:
        return upgrade_member_in_ldap(request, candidature,
                                      existing_member_oid)

    # First, check if the pseudonym is unique
    pseudonym = candidature.pseudonym
    error = is_valid_unique_pseudonym(pseudonym)
    if error:
        # Normalise to the {'status': 'error', 'message': ...} contract the
        # callers expect (register.py reads result['message']); keep the
        # original error/error_details for callers that display them.
        return {'status': 'error', 'message': error.get('error'), **error}

    # Continue to register the user to LDAP
    with get_ldap_connection(ldap_user=LDAP_USER,
        ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        # DN for the new entry
        dn = (f"uid={candidature.oid},{LDAP_OU},{LDAP_BASE_DN}"
            if LDAP_OU else f"uid={candidature.oid},{LDAP_BASE_DN}"
        )
        # Attributes for the new user
        try:
            attributes = {
                # Adjust this based on your LDAP schema
                'objectClass': ['top', 'inetOrgPerson', 'alirpunktoPerson'],
                'uid': candidature.oid,
                'mail': candidature.email,
                'userPassword': make_ldap_password(password),  # 1.3: hash, never cleartext
                'sn': (
                    candidature.data.fullsurname
                        if candidature.type == MemberTypes.COOPERATOR
                        else pseudonym
                ), # sn 434,is obligatory
                'cn': pseudonym, # Use the pseudonym as commonName
                'employeeNumber': candidature.oid, # Use the oid as employeeNumber
                'employeeType': candidature.type.name, # Use the type as employeeType,
                # Use the fullsurname as sn
                "isActive": "True",
            }
            # preferredLanguage is optional in the schema and must be
            # guarded like lang2/lang3 below: an ORDINARY candidature
            # never sets lang1, and ldap3 refuses a None attribute
            # ("Unable to convert type NoneType to unicode") — the
            # whole add failed and no ordinary member could ever be
            # created through the registration flow (found by the
            # manual-producing scenarios, run 84826165979).
            if getattr(candidature.data, 'lang1', None) not in (None, ''):
                attributes['preferredLanguage'] = candidature.data.lang1
            if hasattr(candidature.data, 'lang2') and candidature.data.lang2 not in (None, ''):
                attributes['secondLanguage'] = candidature.data.lang2
            if hasattr(candidature.data, 'lang3') and candidature.data.lang3 not in (None, ''):
                attributes['thirdLanguage'] = candidature.data.lang3
            if candidature.data.description:
                attributes['description'] = candidature.data.description
        except Exception as e:
            log.error(f"Error while preparing attributes for user {pseudonym}: {e}")
            return {'status': 'error', 'message': _('registration_failed')}
        # Determine the groups the user belongs to and add them to uniqueMemberOf
        groups=[]
        match candidature.type:
            case MemberTypes.COOPERATOR:
                try:
                    # Add full name to inetOrgPerson attribute
                    attributes['gn'] = candidature.data.fullname
                    #@TODO check country code is less of 3 chars
                    attributes["nationality"] = candidature.data.nationality
                    attributes["birthdate"] = candidature.data.birthdate.strftime(LDAP_TIME_FORMAT)
                    attributes["cooperativeBehaviourMark"] = candidature.data.cooperative_behaviour_mark
                    attributes["numberSharesOwned"] = candidature.data.number_shares_owned
                    attributes["dateEndValidityYearlyContribution"] = candidature.data.date_end_validity_yearly_contribution.strftime(LDAP_TIME_FORMAT) if candidature.data.date_end_validity_yearly_contribution else "2023-04-25T12:00:00"

                    #@TODO check language code
                except Exception as e:
                    log.error(f"Error while preparing attributes for user {pseudonym}: {e}")
                    return {'status': 'error', 'message': _('registration_failed')}
            case MemberTypes.ORDINARY:
                pass  # groups are handled by sync_member_groups (issue #148)
            case MemberTypes.ADMINISTRATOR:
                # Admins are not stored in LDAP, so we skip this
                log.debug(f"Admin {pseudonym} does not have a group in LDAP.")
            case MemberTypes.PROVIDER:
                groups.append(
                    f"cn=providersGroup,{f'{LDAP_OU},' if LDAP_OU else ''}{LDAP_BASE_DN}")
                # Providers stay on the historical group model: out of the
                # scope of the dynamic groups of issue #148.
            case _:
                log.error(f"Unsupported member type {candidature.type}")
        # If there are groups the user belongs to, add them to the uniqueMemberOf attribute
        if groups:
            attributes['uniqueMemberOf'] = groups
        safe_attributes = {k: v for k, v in attributes.items() if k != 'userPassword'}
        log.debug(f"LDAP Add {dn=}, {safe_attributes=}, userPassword={encrypt_secret_for_logs(password)}")
        # Add the new user to LDAP. Belt over the guards above: ldap3
        # dies on any None value, so strip empty attributes whatever
        # future field forgets its guard.
        attributes = {k: v for k, v in attributes.items()
                      if v is not None and v != ""}
        try:
            success = conn.add(dn, attributes=attributes)
            if success:
                group_dn = None
                match candidature.type:
                    case MemberTypes.ADMINISTRATOR:
                        # Admins are not stored in LDAP, so we skip this
                        log.debug(f"Admin {pseudonym} does not have a group in LDAP.")
                    case MemberTypes.PROVIDER:
                        # Providers stay on the historical group model.
                        group_dn = ("cn=providersGroup,"
                                    f"{f'{LDAP_OU},' if LDAP_OU else ''}"
                                    f"{LDAP_BASE_DN}"
                        )
                        conn.modify(group_dn, {'uniqueMember': [(MODIFY_ADD, [dn])]})
                    case _:
                        # ORDINARY and COOPERATOR: the dynamic groups of
                        # issue #148 are applied by sync_member_groups just
                        # before the success return.
                        pass

                # Check if group addition was successful (only when a group
                # modify was attempted; ADMINISTRATOR has no LDAP group).
                if group_dn is not None and conn.result['description'] != 'success':
                    log.error(f"Error while adding user {pseudonym} to group {group_dn}: {conn.result}")

        except Exception as e:
            log.error(f"Error while adding user {pseudonym} to LDAP: {e}")
            success = False
        if success:
            # 1.3: the LDAP account now stores a hash; drop the (hashed)
            # password kept in ZODB so nothing credential-shaped survives in
            # the object store once the account exists.
            try:
                if getattr(candidature, "data", None) is not None:
                    if getattr(candidature.data, "password", None):
                        candidature.data.password = None
                    if getattr(candidature.data, "password_confirm", None):
                        candidature.data.password_confirm = None
                    candidature._p_changed = True
            except Exception as e:
                log.warning(
                    f"Could not purge password fields from ZODB for "
                    f"{getattr(candidature, 'oid', '?')}: {e}"
                )
            # Place the new member in the dynamic groups of issue #148: an
            # Ordinary Member joins communityMembersGroup; a new Cooperator
            # lands in the candidates group matching their shares and
            # yearly-contribution facts.
            from alirpunkto.dynamic_groups import sync_member_groups
            sync_member_groups(request, candidature.oid)
            return {'status': 'success', 'message': _('registration_successful')}
        else:
            log.error(f"Error while adding user {pseudonym} to LDAP : {conn.result}")
            return {'status': 'error', 'message': _('registration_failed')}

def update_member_password(request, member_oid, new_password):
    """
    Update a member's password in the LDAP directory.

    Args:
        request (pyramid.request.Request): the request.
        member_oid (str): the oid of the member to update.
        new_password (str): the new password.

    Returns:
        dict: a dictionary containing the result of the update.
    """

    # Connect to the LDAP server
    with get_ldap_connection(ldap_user=LDAP_USER,
        ldap_password=get_secret(LDAP_PASSWORD)) as conn:
        # DN for the member
        dn = (f"uid={member_oid},{LDAP_OU},{LDAP_BASE_DN}"
            if LDAP_OU else f"uid={member_oid},{LDAP_BASE_DN}"
        )

        # Update the member's password
        try:
            hashed = make_ldap_password(new_password)  # 1.3: hash, never cleartext
            success = conn.modify(dn, {'userPassword': [(MODIFY_REPLACE, [hashed])]})
        except Exception as e:
            log.error(f"Error while updating password for user {member_oid} in LDAP: {e}")
            success = False

        if success:
            return {'status': 'success', 'message': _('password_update_successful')}
        else:
            log.error(f"Error while updating password for user {member_oid} in LDAP : {conn.result}")
            return {'status': 'error', 'message': _('password_update_failed')}

def update_ldap_member(
    request:Request,
    member:Member,
    fields_to_update:List[str]=None
    ):
    """
    Update a member in the LDAP directory.

    Args:
        request (pyramid.request.Request): the request.
        member (Member): the member to update.

    Returns:
        dict: a dictionary containing the result of the update.
    """
    # Default to every updatable field, using the *model* field names that the
    # body below tests (callers such as modify_member push model names too).
    if fields_to_update is None:
        fields_to_update = [
            'email', 'fullsurname', 'description', 'type', 'fullname',
            'nationality', 'birthdate', 'lang1', 'lang2', 'lang3', 'is_active',
            'cooperative_behaviour_mark', 'cooperative_behaviour_mark_update',
            'number_shares_owned', 'date_end_validity_yearly_contribution',
            'iban', 'unique_member_of', 'date_erasure_all_data'
        ]
    # Connect to the LDAP server
    with get_ldap_connection(ldap_user=LDAP_USER,
        ldap_password=get_secret(LDAP_PASSWORD)) as conn:

        # DN for the member
        dn = (f"uid={member.oid},{LDAP_OU},{LDAP_BASE_DN}"
            if LDAP_OU else f"uid={member.oid},{LDAP_BASE_DN}"
        )

        # Attributes for the member
        attributes = {}
        if 'email' in fields_to_update:
            attributes['mail'] = [(MODIFY_REPLACE,[member.email])]
        if 'fullsurname' in fields_to_update:
            attributes['sn'] = [(MODIFY_REPLACE,[member.data.fullsurname])]
        if 'description' in fields_to_update:
            attributes['description'] = [(MODIFY_REPLACE,[member.data.description])]
        if 'type' in fields_to_update:
            attributes['employeeType'] = [(MODIFY_REPLACE,[member.type.name])]
        if 'fullname' in fields_to_update:
            attributes['gn'] = [(MODIFY_REPLACE,[member.data.fullname])]
        if 'nationality' in fields_to_update:
            attributes['nationality'] = [(MODIFY_REPLACE,[member.data.nationality])]
        if 'birthdate' in fields_to_update:
            attributes['birthdate'] = [(MODIFY_REPLACE,[member.data.birthdate.strftime(LDAP_TIME_FORMAT)])]
        if 'lang1' in fields_to_update:
            attributes['preferredLanguage'] = [(MODIFY_REPLACE,[member.data.lang1])]
        if 'lang2' in fields_to_update:
            if member.data.lang2 not in (None, ''):
                attributes['secondLanguage'] = [(MODIFY_REPLACE,[member.data.lang2])]
            else:
                attributes['secondLanguage'] = [(MODIFY_REPLACE,[])]
        if 'lang3' in fields_to_update:
            if member.data.lang3 not in (None, ''):
                attributes['thirdLanguage'] = [(MODIFY_REPLACE,[member.data.lang3])]
            else:
                attributes['thirdLanguage'] = [(MODIFY_REPLACE,[])]
        if 'is_active' in fields_to_update:
            attributes['isActive'] = [(MODIFY_REPLACE, [member.data.is_active])]
        if 'cooperative_behaviour_mark' in fields_to_update:
            attributes['cooperativeBehaviourMark'] = [(MODIFY_REPLACE, [str(member.data.cooperative_behaviour_mark)])]
        if 'cooperative_behaviour_mark_update' in fields_to_update:
            attributes['cooperativeBehaviourMarkUpdate'] = [(MODIFY_REPLACE, [member.data.cooperative_behaviour_mark_update.strftime(LDAP_TIME_FORMAT)])]
        if 'number_shares_owned' in fields_to_update:
            attributes['numberSharesOwned'] = [(MODIFY_REPLACE, [str(member.data.number_shares_owned)])]
        if 'date_end_validity_yearly_contribution' in fields_to_update:
            attributes['dateEndValidityYearlyContribution'] = [(MODIFY_REPLACE, [member.data.date_end_validity_yearly_contribution.strftime(LDAP_TIME_FORMAT)])]
        if 'iban' in fields_to_update:
            attributes['IBAN'] = [(MODIFY_REPLACE, [member.data.iban])]
        if 'unique_member_of' in fields_to_update:
            attributes['uniqueMemberOf'] = [(MODIFY_REPLACE, [member.data.unique_member_of])]
        if 'date_erasure_all_data' in fields_to_update:
            attributes['dateErasureAllData'] = [(MODIFY_REPLACE, [member.data.date_erasure_all_data.strftime(LDAP_TIME_FORMAT)])]
        try:
            success = conn.modify(dn, attributes)
        except Exception as e:
            log.error(f"Error while updating user {member.oid} in LDAP: {e}")
            success = False

        if success:
            # Shares or yearly-contribution changes move the member between
            # the dynamic groups of issue #148.
            from alirpunkto.dynamic_groups import sync_member_groups
            sync_member_groups(request, member.oid)
            return {'status': 'success', 'message': _('member_update_successful')}
        else:
            log.error(f"Error while updating user {member.oid} in LDAP : {conn.result}")
            return {'status': 'error', 'message': _('member_update_failed')}

def is_admin(username:str, password:str)-> bool:
    """
    Determines if the provided username and password match the credentials of the administrator.

    This function checks if the given username and password combination is the same as that of the
    administrator.

    Args:
    username (str): The username to be checked.
    password (str): The password corresponding to the username.

    Returns:
    bool: Returns True if the provided username and password match the administrator's credentials,
    otherwise returns False.
    """
    admin_login = ADMIN_LOGIN.split("=")[-1]
    admin_password = get_secret(ADMIN_PASSWORD)
    username_matches = hmac.compare_digest(
        username.strip().encode("utf-8"), admin_login.encode("utf-8")
    )
    password_matches = hmac.compare_digest(
        password.encode("utf-8"), admin_password.encode("utf-8")
    )
    return username_matches and password_matches

def get_local_template(request, pattern_path, member=None):
    """
    Return the local template for the given pattern path according to the user's language preference.

    This function attempts to resolve the template path based on the user's preferred language.
    If the resolution fails, it falls back to the default English language.

    Args:
        request (Request): The request object, used to determine the user's preferred language.
        pattern_path (str): The pattern path for which the local template is requested.

    Returns:
        resolver (object): The resolved pattern handler.

    Raises:
        (No explicit exceptions are raised, but errors are logged)
    """

    lang = get_preferred_language(request, member)
    ar = AssetResolver("alirpunkto")
    try:
        resolver = ar.resolve(pattern_path.format(lang=lang))
        # AssetResolver.resolve never raises on a missing file — the
        # old bare except therefore caught nothing and the German
        # confirmation e-mail died at render time (issue #254). The
        # existence test is what makes the English fallback real.
        if not resolver.exists():
            raise FileNotFoundError(pattern_path.format(lang=lang))
    except Exception:
        log.error(
            f"Locale template missing for {lang} at {pattern_path}"
            f", falling back to en."
        )
        resolver = ar.resolve(pattern_path.format(lang="en"))
    return resolver

def send_confirm_validation_email(request: Request,
    candidature: Candidature) -> Dict:
    """Send the confirmation email to the candidate.
    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature
    Returns:
        dict: the result of the email sending
    """
    return send_candidature_state_change_email(request,
        candidature,
        "send_confirm_validation_email")

def send_member_state_change_email(request: Request,
    member: Member,
    sending_function_name : str,
    template_name : str = None,
    subject:str = None,
    extra_template_parameter:dict = None) -> Dict:
    """Send the member state change email to the candidate.
    Args:
        request (pyramid.request.Request): the request
        member (Member): the member
        sending_function_name (str): the name of the function that sends the email
        template_name (str): the name of the template to use or None to use the default template
        subject (str): the subject of the email or None to use the default subject
        extra_template_parameter (dict): extra parameters to add to the template
    Returns:
        dict: the result of the email sending
    """
    template_name = (template_name
        if template_name
        else "member_state_change"
    )
    assert(template_name.find("{lang}") == -1)
    # The string for the template path is concatenated because the 'lang' variable
    # will be replaced during formatting by the resource resolution
    template_path = LOCALE_LANG_MESSAGES+template_name+ZPT_EXTENSION
    template_resolver = get_local_template(request, template_path, member=member).abspath()
    if subject is None:
        subject = _('email_member_state_changed')
    if isinstance(subject, TranslationString):
        # Subjects are translated in the recipient's language (issue #239);
        # an already-translated plain string is respected as-is.
        subject = _translate_for_language(
            request, get_preferred_language(request, member), subject)
    email = member.email
    seed = member.email_send_status_history[-1].seed

    # Prepare the necessary information for the email
    parameter = encrypt_oid(
        member.oid,
        seed,
        request.registry.settings['session.secret']
    )

    url = request.route_url('register', _query={'oid': parameter})
    site_url = get_site_url(request)
    site_name = request.registry.settings.get('site_name')
    # Prefer the deployment setting, as site_name/domain_name above; fall
    # back to the environment constant so the address is never None when
    # the .ini does not define it (issue #169, PR #233).
    organization_details = (
        request.registry.settings.get('organization_details')
        or ORGANIZATION_DETAILS
    )
    domain_name = request.registry.settings.get('domain_name')
    #We don't have user yet so we use the email parts befor the @ or pseudonym if it exists
    user = (member.pseudonym if hasattr(member, "pseudonym")
            else email.split('@')[0]
    )

    template_vars = {
        'page_register_with_oid': url,
        'site_url': site_url,
        'site_name': site_name,
        'domain_name': domain_name,
        'organization_details': organization_details,
        'member': member,
        'pseudonym': member.pseudonym,
        'MemberStates': MemberStates,
        'user': user
    }
    if extra_template_parameter:
        template_vars.update(extra_template_parameter)

    # Use the send_email from utils.py
    try:
        # Stack email sending action to be executed at commit
        success = send_email(
            request,
            subject,
            [email],
            template_resolver,
            template_vars
        )
    except Exception as e:
        log.error(f"Error while sending email to {email} : {e}")
        success = False

    if success:
        member.add_email_send_status(
            EmailSendStatus.SENT, sending_function_name)
        return {'success': True}
    else:
        member.add_email_send_status(
            EmailSendStatus.ERROR, sending_function_name)
        return {'error': _('email_not_sent')}

def send_candidature_state_change_email(request: Request,
    candidature: Member,
    sending_function_name : str,
    template_name : str = None,
    subject:str = None) -> Dict:
    """Send the candidature state change email to the candidate.
    Args:
        request (pyramid.request.Request): the request
        candidature (Member): the candidature
        sending_function_name (str): the name of the function that sends the email
        template_name (str): the name of the template to use or None to use the default template
        subject (str): the subject of the email or None to use the default subject
    Returns:
        dict: the result of the email sending
    """
    template_name = (template_name
        if template_name
        else "candidature_state_change"
    )

    log.debug(f"template_name={template_name}")
    # The subject is translated by send_member_state_change_email in the
    # recipient's language (issue #239); pass the TranslationString through.
    if subject is None:
        subject = _('email_candidature_state_changed')

    template_vars = {
        'candidature': candidature,
        'CandidatureStates': CandidatureStates,
        # The approval e-mail template conditions on the member type.
        'MemberTypes': MemberTypes,
    }
    return send_member_state_change_email(
        request,
        candidature,
        sending_function_name,
        template_name,
        subject,
        template_vars)

def send_email_to_member(request: Request,
    member: Member,
    sending_function_name: str,
    template_name: str,
    subject_msgid: str,
    view_name: str,
    extra_template_parameters:dict = None) -> Dict:
    """Send an email to the member.
    Args:
        request (pyramid.request.Request): the request
        member (Member): the member
        sending_function_name (str): the name of the function that sends the email
        template_name (str): the name of the template to use
        subject_msgid (str): the msgid of the email subject
        view_name (str): the name of the view to use in the email
    Returns:
        dict: the result of the email sending
    """
    template_path = LOCALE_LANG_MESSAGES+template_name+ZPT_EXTENSION
    template_resolver = get_local_template(request, template_path, member=member).abspath()
    subject = _translate_for_language(
        request, get_preferred_language(request, member), _(subject_msgid))
    email = member.email
    # Retrieve the seed from the last email event which must be
    # EmailSendStatus.IN_PREPARATION
    seed = member.email_send_status_history[-1].seed

    # Prepare the necessary information for the email
    parameter = encrypt_oid(
        member.oid,
        seed,
        request.registry.settings['session.secret']
    )

    url = request.route_url(view_name, _query={'oid': parameter})
    site_url = get_site_url(request)
    site_name = request.registry.settings.get('site_name')
    domain_name = request.registry.settings.get('domain_name')
    # Prefer the deployment setting, as site_name/domain_name above; fall
    # back to the environment constant so the address is never None when
    # the .ini does not define it (issue #169, PR #233).
    organization_details = (
        request.registry.settings.get('organization_details')
        or ORGANIZATION_DETAILS
    )

    template_vars = {
        'page_with_oid': url,
        'site_url': site_url,
        'site_name': site_name,
        'domain_name': domain_name,
        'organization_details': organization_details,
        'member': member.data,
        # The greeting of the e-mail templates (issue #226): the pseudonym
        # lives on the Member, not in MemberDatas.
        'pseudonym': member.pseudonym,
    }
    if extra_template_parameters:
        template_vars.update(extra_template_parameters)

    # Use the send_email from utils.py
    try:
        # Stack email sending action to be executed at commit
        success = send_email(
            request,
            subject,
            [email],
            template_resolver,
            template_vars
        )
    except Exception as e:
        log.error(f"Error while sending email to {email} : {e}")
        success = False

    if success:
        member.add_email_send_status(
            EmailSendStatus.SENT, sending_function_name)
        return {'success': True}
    else:
        member.add_email_send_status(
            EmailSendStatus.ERROR, sending_function_name)
        return {'error': _('email_not_sent')}

def send_validation_email(
        request: Request,
        candidature: 'Candidature'
    ) -> bool:
    """
    Send the validation email to the candidate.

    Args:
        request: The request object.
        candidature: The candidature object.

    Returns:
        bool: True if the email is successfully sent, False otherwise.
    """
    try:
        template_path = LOCALE_LANG_MESSAGES + "check_email" + ZPT_EXTENSION
        template_path = get_local_template(
            request,
            template_path,
            member=candidature
        ).abspath()
    except Exception as e:
        log.error(f"Error while getting template '{template_path}' for email validation: {e}")
        return False

    email = candidature.email # The email to send to.
    challenge = candidature.challenge # The math challenge for email validation.
    subject = _translate_for_language(
        request, get_preferred_language(request, candidature),
        _('email_validation_subject'))
    seed = candidature.email_send_status_history[-1].seed
    parameter = encrypt_oid(
        candidature.oid,
        seed,
        request.registry.settings['session.secret']
    )

    url = request.route_url('register', _query={'oid': parameter})
    site_url = get_site_url(request)
    site_name = request.registry.settings.get('site_name')
    domain_name = request.registry.settings.get('domain_name')
    # Prefer the deployment setting, as site_name/domain_name above; fall
    # back to the environment constant so the address is never None when
    # the .ini does not define it (issue #169, PR #233).
    organization_details = (
        request.registry.settings.get('organization_details')
        or ORGANIZATION_DETAILS
    )

    template_vars = {
        'challenge_A': challenge["A"][0],
        'challenge_B': challenge["B"][0],
        'challenge_C': challenge["C"][0],
        'challenge_D': challenge["D"][0],
        'page_register_with_oid': url,
        'site_url': site_url,
        'site_name': site_name,
        'domain_name': domain_name,
        'organization_details': organization_details
    }

    # Use the send_email from utils.py
    # Put on the stack the action of sending the email wich is done during the commit
    try:
        success = send_email(
            request,
            subject,
            [email],
            template_path,
            template_vars
        )
    except Exception as e:
        log.error(f"Error while sending email to {email} : {e}")
        success = False
    return success

def send_check_new_email(
        request: Request,
        member: 'Member',
        new_email: str
    ) -> bool:
    """
    Send the validation of new email adress to the member.

    Args:
        request: The request object.
        candidature: The candidature object.

    Returns:
        bool: True if the email is successfully sent, False otherwise.
    """
    template_path = get_local_template(
        request,
        LOCALE_LANG_MESSAGES + "check_new_email" + ZPT_EXTENSION,
        member=member
    ).abspath()

    email = member.email # The email to send to.
    subject = _translate_for_language(
        request, get_preferred_language(request, member),
        _('check_new_email_subject'))
    seed = member.email_send_status_history[-1].seed
    parameter = encrypt_oid(
        member.oid,
        seed,
        request.registry.settings['session.secret']
    )

    url = request.route_url('check_new_email', _query={'oid': parameter})
    site_url = get_site_url(request)
    site_name = request.registry.settings.get('site_name')
    domain_name = request.registry.settings.get('domain_name')
    # Prefer the deployment setting, as site_name/domain_name above; fall
    # back to the environment constant so the address is never None when
    # the .ini does not define it (issue #169, PR #233).
    organization_details = (
        request.registry.settings.get('organization_details')
        or ORGANIZATION_DETAILS
    )

    template_vars = {
        'check_new_email_view':url,
        'speudonym': member.pseudonym,
        'site_url': site_url,
        'site_name': site_name,
        'domain_name': domain_name,
        'organization_details': organization_details,
        'new_email': new_email
    }

    # Use the send_email from utils.py
    # Put on the stack the action of sending the email wich is done during the commit
    try:
        success = send_email(
            request,
            subject,
            [email],
            template_path,
            template_vars
        )
    except Exception as e:
        log.error(f"Error while sending email to {email} : {e}")
        success = False
    return success


def _sso_refresh_fernet() -> Fernet:
    """Fernet keyed on SECRET_KEY, the same convention as encrypt_oid."""
    return Fernet(get_secret(SECRET_KEY))


def seal_sso_refresh_token(refresh_token: str) -> str:
    """Compress then encrypt a refresh token for session storage.

    Sixth audit pass (2026-08-01, §12.5): the cookie session is signed,
    not encrypted — its content is readable by whoever holds the cookie
    bytes. Compression comes FIRST because ciphertext is incompressible
    and the 4093-byte cookie limit is a hard wall (field incident of
    2026-07-08): a worst-case 2000-character refresh JWT encrypts to
    ~2.8 KB raw but ~2.2 KB once deflated, keeping the whole session
    under the limit. Only the token is compressed — no attacker-chosen
    data shares the stream, so this opens no compression oracle.
    """
    return _sso_refresh_fernet().encrypt(
        zlib.compress(refresh_token.encode("utf-8"), 9)).decode("ascii")


def load_sso_refresh_token(request) -> Optional[str]:
    """Return the decrypted SSO refresh token from the session, or None.

    Inverse of ``seal_sso_refresh_token``. Anything that does not
    decrypt and inflate (a tampered value, or a clear-text token from a
    session created before the sixth audit pass) is treated as an
    expired SSO session: the caller logs the user out and a fresh login
    rebuilds the session.
    """
    stored = request.session.get(SSO_REFRESH)
    if stored is None:
        return None
    try:
        return zlib.decompress(_sso_refresh_fernet().decrypt(
            stored.encode("ascii"))).decode("utf-8")
    except (InvalidToken, AttributeError, UnicodeError, zlib.error):
        log.warning("Stored SSO refresh token is not a valid encrypted "
                    "token; treating the SSO session as expired.")
        return None


def store_sso_tokens(request, sso_token: dict) -> None:
    """Store the Keycloak tokens the session actually needs.

    Only the *refresh* token and its expiry go into the (cookie-backed)
    session: they are what ``home_view`` needs to keep the SSO session alive.
    The *access* token is deliberately NOT stored — nothing in the
    application ever reads it back, and Keycloak access tokens carry the
    user's group/role claims, so for a member of several groups the two JWTs
    together overflow Pyramid's 4093-byte cookie limit ("ValueError: Cookie
    value is too long to store", field incident of 2026-07-08).

    Sixth audit pass (§12.5): the refresh token is encrypted before it
    enters the session — the signed cookie protects integrity, not
    confidentiality. Read it back with ``load_sso_refresh_token``.
    """
    request.session[SSO_REFRESH] = seal_sso_refresh_token(
        sso_token['refresh_token'])
    refresh_at = datetime.now() + timedelta(
        seconds=int(sso_token['refresh_expires_in']))
    request.session[SSO_EXPIRES_AT] = refresh_at.isoformat()


def logout(request: Request):
    """
    Log out the user by removing the user's OID from the session.

    Args:
        request (Request): The request object.
    """
    # Defensively drop a legacy 'username' session key if it is ever present.
    # It is never set today, and clearing it must not depend on (nor be driven
    # by) a URL parameter — the previous `del request.session['username']`
    # raised KeyError whenever `?username=` was supplied.
    request.session.pop('username', None)
    user = request.session.get('user', None)
    if user is not None:
        # log the user is logging out
        log.info(f"User {user} is logging out")
        del request.session['user']
        request.session['logged_in'] = False
        request.session['created_at'] = None
    else:
        request.session['logged_in'] = False
    if CANDIDATURE_OID in request.session:
        del request.session[CANDIDATURE_OID] #
    if MEMBER_OID in request.session:
        del request.session[MEMBER_OID]
    if ACCESSED_MEMBER_OID in request.session:
        del request.session[ACCESSED_MEMBER_OID]
    if SSO_TOKEN in request.session:
        del request.session[SSO_TOKEN]
    if SSO_REFRESH in request.session:
        del request.session[SSO_REFRESH]
    if SSO_EXPIRES_AT in request.session:
        del request.session[SSO_EXPIRES_AT]

# Sixth audit pass (2026-08-01, §12.6): a token endpoint answer is
# untrusted input — parse and validate it before use. 90 days bounds
# any realistic Keycloak token lifetime and rejects absurd values.
_MAX_TOKEN_LIFETIME_SECONDS = 90 * 24 * 3600


def _validated_token_payload(response, context: str) -> Optional[dict]:
    """Parse a Keycloak token response and validate the fields used.

    Sixth audit pass (§12.6): ``response.json()`` could raise on a
    non-JSON body, required fields could be missing, types were never
    checked and expiry values were unbounded. Every field this
    application dereferences (``refresh_token``, ``access_token``,
    ``expires_in``, ``refresh_expires_in``) is now required, typed and
    bounded; anything else is a failure, logged WITHOUT the body
    (the response may contain tokens) and returned as ``None``.
    """
    try:
        payload = response.json()
    except ValueError:
        log.error(f"Keycloak token response is not JSON while {context} "
                  f"({len(response.text or '')} bytes of body withheld)")
        return None
    if not isinstance(payload, dict):
        log.error(f"Keycloak token response is not an object while "
                  f"{context}")
        return None
    for field in ("access_token", "refresh_token"):
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            log.error(f"Keycloak token response misses a usable "
                      f"'{field}' while {context}")
            return None
    for field in ("expires_in", "refresh_expires_in"):
        value = payload.get(field)
        if (isinstance(value, bool) or not isinstance(value, int)
                or not 0 < value <= _MAX_TOKEN_LIFETIME_SECONDS):
            log.error(f"Keycloak token response carries an invalid "
                      f"'{field}' while {context}")
            return None
    return payload


def get_keycloak_token(user: User, password: str) -> Optional[dict]:
    """Get the Keycloak token for the given user.

    This function sends a request to the Keycloak server to obtain an access token
    for the specified user using their username and password.

    Args:
        user (User): The user object representing the user for whom the token is requested.
        password (str): The password of the user.

    Returns:
        Optional[str]: The full json if the request is successful, None otherwise.
    """
    if PYTEST_CURRENT_TEST:
        log.warning("SSO token retrieval is not yet implemented for pytest.")
        return None
    if not KEYCLOAK_SERVER_URL or not KEYCLOAK_REALM:
        log.warning("Keycloak server URL or realm not set.")
        return None
    token_url = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    if "https" not in token_url:
        log.warning(f"Token from {token_url} is not secure.")
    payload = {
        'client_id': get_secret(KEYCLOAK_CLIENT_ID),
        'client_secret': get_secret(KEYCLOAK_CLIENT_SECRET),
        'grant_type': 'password',
        'username': user.oid, # assuming the oid is used as the username in Keycloak
        'password': password,
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    now = datetime.now()
    try:
        # Revised audit: a hung Keycloak must never pin a Waitress thread.
        response = requests.post(token_url, data=payload, headers=headers,
                                 timeout=(3.0, 10.0))
    except requests.RequestException as exc:
        log.warning(f"Keycloak unavailable while getting the SSO token: "
                    f"{exc.__class__.__name__}")
        return None

    if response.status_code == 200:
        json_response = _validated_token_payload(
            response, "getting the SSO token")
        if json_response is None:
            return None
        expires_at = (now + timedelta(
            seconds=json_response['expires_in'])).isoformat()
        json_response[SSO_EXPIRES_AT] = expires_at
        return json_response
    else:
        log.error(f"Failed to get SSO token: {response.status_code} "
                  f"({len(response.text or '')} bytes of body withheld)")
        return None

def refresh_keycloak_token(refresh_token: str) -> Optional[dict]:
    """Refresh the Keycloak access token using the refresh token.

    Args:
        refresh_token (str): The refresh token obtained from a previous authentication.

    Returns:
        Optional[dict]: The JSON response containing the new access token if the request is successful,
        None otherwise.
    """
    token_url = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    if "https" not in token_url:
        log.warning(f"Token from {token_url} is not secure.")
    payload = {
        'client_id': get_secret(KEYCLOAK_CLIENT_ID),
        'client_secret': get_secret(KEYCLOAK_CLIENT_SECRET),
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = requests.post(token_url, data=payload, headers=headers,
                                 timeout=(3.0, 10.0))
    except requests.RequestException as exc:
        log.warning(f"Keycloak unavailable while refreshing the SSO token: "
                    f"{exc.__class__.__name__}")
        return None

    if response.status_code == 200:
        return _validated_token_payload(
            response, "refreshing the SSO token")
    else:
        log.error(f"Failed to refresh SSO token: {response.status_code} "
                  f"({len(response.text or '')} bytes of body withheld)")
        return None
