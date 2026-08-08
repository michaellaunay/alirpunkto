# This file is part of the alirpunkto package.
# author: Michael Launay

# Description: Constants for the alirpunkto app
from typing import Final
from collections.abc import Mapping
from types import MappingProxyType
import os, sys, pytz
# Revised audit: the .env file is loaded exactly once; every global then
# reads os.getenv(), so real environment variables keep their normal
# priority and the file is never re-read through get_key().
from dotenv import load_dotenv, find_dotenv
from pyramid.i18n import (
    TranslationStringFactory,
)
import logging
import re


def env_bool(name: str, default: bool = False) -> bool:
    """Get a boolean value from an environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"true", "1", "yes", "y", "on"}

# PyTest execution
PYTEST_CURRENT_TEST: Final = 'PYTEST_CURRENT_TEST' in os.environ or 'pytest' in sys.modules
# USE SSO DURING TESTS
PYTEST_SSO_TEST: Final = not PYTEST_CURRENT_TEST or env_bool("PYTEST_USE_SSO", False)

# Load environment variables from .env.
# Eleventh-audit follow-up (2026-08-02, smoke run): find_dotenv() walks up
# from the CALLING FILE, so it only ever worked because this module lived
# inside the repository next to .env. The 0075 wheel moved it into the
# venv's site-packages: under pserve (a script, so dotenv's interactive
# cwd fallback does not apply) the walk climbs venv/ and never meets the
# mounted app/.env — SECRET_KEY stays unset and the import dies before
# the socket binds. Look in the current directory first (the container
# WORKDIR carries .env), then fall back to the historical frame walk so
# bare-metal launches from outside the repo keep working.
dotenv_path: Final = find_dotenv(usecwd=True) or find_dotenv()
load_dotenv(dotenv_path)

# Disable MX DNS checks in pytest and local/offline Docker test stacks.
DISABLE_EMAIL_MX_CHECKS: Final = env_bool("DISABLE_EMAIL_MX_CHECKS", PYTEST_CURRENT_TEST)

# LDAP informations are stored in environment variables
# Not Final due to __init__ initialization
SECRET_KEY: Final = "SECRET_KEY"
LDAP_SERVER: Final = os.getenv("LDAP_SERVER")
LDAP_PORT: Final = int(os.getenv("LDAP_PORT", 389))
LDAP_BASE_DN: Final = os.getenv("LDAP_BASE_DN") if not PYTEST_CURRENT_TEST else "dc=example,dc=com"
LDAP_OU: Final = os.getenv("LDAP_OU")
LDAP_USE_SSL: Final = (
    (os.getenv("LDAP_USE_SSL") or "False").lower()
    in ['true', '1', "yes", "y"]
)
# Sixth audit pass (2026-08-01, §12.1): optional CA bundle used to
# validate the LDAP server certificate when LDAP_USE_SSL is true.
# Left unset, ldap3 loads the system CA store (SSLContext
# load_default_certs) — validation itself is enforced by the Tls
# object built in ldap_factory, never skipped.
LDAP_CA_CERT_FILE: Final = os.getenv("LDAP_CA_CERT_FILE") or None
LDAP_PASSWORD: Final = "LDAP_PASSWORD" # use get_secret to get the password
LDAP_LOGIN: Final = os.getenv("LDAP_LOGIN")
LDAP_USER: Final = (f"{LDAP_LOGIN},{LDAP_OU},{LDAP_BASE_DN}"
    if LDAP_OU else f"{LDAP_LOGIN},{LDAP_BASE_DN}"
)
ADMIN_LOGIN: Final = os.getenv("ADMIN_LOGIN")
ADMIN_PASSWORD: Final = "ADMIN_PASSWORD" # use get_secret to get the password
ADMIN_EMAIL: Final = os.getenv("ADMIN_EMAIL")
MAIL_USERNAME: Final = os.getenv("MAIL_USERNAME")
MAIL_SENDER: Final = os.getenv("MAIL_SENDER")
MAIL_SERVER: Final = os.getenv("MAIL_SERVER")
MAIL_PASSWORD: Final = "MAIL_PASSWORD" # use get_secret to get the password
MAIL_PORT: Final = os.getenv("MAIL_PORT")
MAIL_HOST: Final = os.getenv("MAIL_HOST")
MAIL_TLS: Final = os.getenv("MAIL_TLS")
MAIL_SSL: Final = os.getenv("MAIL_SSL")
MAIL_SIGNATURE: Final = os.getenv("MAIL_SIGNATURE", "{fullsurname} {fullname} on {site_name} for {domain_name}")
DOMAIN_NAME: Final = os.getenv("DOMAIN_NAME", "alirpunkto.org")
# Scheme of the public URLs put in outgoing e-mails. E-mail links must not
# be derived from the incoming request (behind the reverse proxy the app is
# reached on http://localhost:6543), so they are built from the configured
# domain and this scheme.
URL_SCHEME: Final = os.getenv("URL_SCHEME", "https")
SITE_NAME: Final = os.getenv("SITE_NAME", "AlirPunkto")
ORGANIZATION_DETAILS: Final = os.getenv("ORGANIZATION_DETAILS", "AlirPunkto is an open source project for managing cooperative memberships.")

# Resignation (specification "Démissionner", issue #54): how long the
# personal data of an unsubscribed member is kept before the purge — the
# Quarantine period, a Quantitative Parameter Affecting Internal Processes
# defined by §3.4 of the Cooperative's statutes, 180 days by default — and
# how long the e-mailed confirmation link stays valid.
#: Maximum size of the member avatar (issue #150) — jpegPhoto in LDAP.
AVATAR_MAX_BYTES: Final = int(os.getenv("AVATAR_MAX_BYTES", str(4096 * 1024)))
QUARANTINE_PERIOD_DAYS: Final = int(os.getenv("QUARANTINE_PERIOD_DAYS", "180"))
UNSUBSCRIBE_LINK_VALIDITY_DAYS: Final = int(
    os.getenv("UNSUBSCRIBE_LINK_VALIDITY_DAYS", "7"))

# --- Site-specific information (issue #236) -------------------------------
# These four values differ from one deployment to another and are interpolated
# into the ${...} placeholders of the i18n messages. Override them through the
# environment (or docker/.env) for a given cooperative.
#: URL of the website hosting the organisation's workspace.
URL_WORKSPACE: Final = os.getenv("URL_WORKSPACE", "")
#: URL where a Cooperator pays the yearly contribution.
URL_PAY_YEARLY_CONTRIB: Final = os.getenv("URL_PAY_YEARLY_CONTRIB", "")
#: URL where a Cooperator purchases shares of the Cooperative.
URL_PURCHASE_SHARES: Final = os.getenv("URL_PURCHASE_SHARES", "")
#: Number of days after which a Cooperative Behaviour Mark is halved.
FORGETTING_TIME_CONSTANT: Final = int(os.getenv("FORGETTING_TIME_CONSTANT", 365))
VERIFIER_VOTE_DEADLINE_DAYS: Final = int(os.getenv("VERIFIER_VOTE_DEADLINE_DAYS", 7))
NOTICE_TIME_VERIFIERS: Final = int(os.getenv("NOTICE_TIME_VERIFIERS", 2))
KEYCLOAK_SERVER_URL:Final = os.getenv("KEYCLOAK_SERVER_URL") # The keycloak server
KEYCLOAK_REALM:Final = os.getenv("KEYCLOAK_REALM") # The realm
# The client id of this application for keycloak
KEYCLOAK_CLIENT_ID:Final = "KEYCLOAK_CLIENT_ID" # use get_secret to get the password
# The client secret of this application
KEYCLOAK_CLIENT_SECRET:Final = "KEYCLOAK_CLIENT_SECRET" # use get_secret to get the password
# The keycloak redirect path
KEYCLOAK_REDIRECT_PATH:Final = "keycloak_redirect"
# SSO Token in session
SSO_TOKEN:Final = "SSO_TOKEN"
# SSO Refresh Token in session
SSO_REFRESH:Final = "SSO_REFRESH"
# SSO Token expiration date
SSO_EXPIRES_AT:Final = 'expires_at'
# logging configuration
log: Final = logging.getLogger('alirpunkto')

# Default session timeout is getting from environment variable or set to 7 hours
DEFAULT_SESSION_TIMEOUT: Final = int(os.getenv("DEFAULT_SESSION_TIMEOUT", 7*60*60))

VERIFIER_REMINDER_MIN_INTERVAL_SECONDS: Final = int(os.getenv("VERIFIER_REMINDER_MIN_INTERVAL_SECONDS", 259200))  # 3 days in seconds

EUROPEAN_ZONES: Final = [tz for tz in pytz.all_timezones if tz.startswith('Europe')]

# LDAP Time Format
LDAP_TIME_FORMAT: Final = "%Y-%m-%dT%H:%M:%S"
LDAP_TIME_LENGTH: Final = 19
LDAP_DATE_LENGTH: Final = 10
LDAP_DEFAULT_HOUR: Final = "T12:00:00"
# LDAPT test
TEST_LDAP_SERVER: Final = os.getenv("TEST_LDAP_SERVER", "my_fake_ldap_server")
HTTP_TEST_HOST: Final = os.getenv("HTTP_TEST_HOST", "example.com")
# LDAP test contener
TEST_WITH_DOCKER_LDAP: Final = os.getenv("TEST_WITH_DOCKER_LDAP", "").lower() in ['true', '1', 'yes', 'y']
TEST_WITH_DOCKER_LDAP_SERVER: Final = os.getenv("TEST_WITH_DOCKER_LDAP_SERVER", "localhost")
TEST_WITH_DOCKER_LDAP_PORT: Final = int(os.getenv("TEST_WITH_DOCKER_LDAP_PORT", "3389"))
def get_ldap_server_name():
    """Get the LDAP server name.
    Returns:
        str: The LDAP server name.
    """
    if PYTEST_CURRENT_TEST:
        if TEST_WITH_DOCKER_LDAP:
            return TEST_WITH_DOCKER_LDAP_SERVER
        else:
            return TEST_LDAP_SERVER
    return LDAP_SERVER

def get_ldap_server_port():
    """Get the LDAP server port.
    Returns:
        int: The LDAP server port.
    """
    if PYTEST_CURRENT_TEST and TEST_WITH_DOCKER_LDAP:
        return TEST_WITH_DOCKER_LDAP_PORT
    return LDAP_PORT

# Single language registry (i18n audit 2026-08-08, P0.1): the one
# source of truth every other list derives from. To add a language:
# add its entry here AND create alirpunkto/locale/<code>/ — the
# test_locale_completeness locks verify the registry and the disk
# stay a bijection, and that every catalog covers the full POT.
# 'selectable' controls whether the registration/profile forms offer
# the language (audit §22, option 2: the eight on-disk locales the
# form never offered are now EXPLICITLY not selectable — flipping
# the boolean is the whole decision). 'tier' records the audit's
# support levels (§20): 1 full, 2 functional, 3 experimental —
# informative for now, ready for CI policies.
SUPPORTED_LOCALES: Final = {
    # Selectable, in the exact order the form has always offered:
    'eo': {'name': 'Esperanto', 'selectable': True, 'tier': 3},
    'bg': {'name': 'български', 'selectable': True, 'tier': 3},
    'cs': {'name': 'čeština', 'selectable': True, 'tier': 3},
    'da': {'name': 'dansk', 'selectable': True, 'tier': 3},
    'de': {'name': 'Deutsch', 'selectable': True, 'tier': 2},
    'et': {'name': 'Eesti', 'selectable': True, 'tier': 3},
    'el': {'name': 'ελληνικά', 'selectable': True, 'tier': 3},
    'en': {'name': 'English', 'selectable': True, 'tier': 1},
    'es': {'name': 'Español', 'selectable': True, 'tier': 2},
    'fr': {'name': 'Français', 'selectable': True, 'tier': 1},
    'ga': {'name': 'Gaeilge', 'selectable': True, 'tier': 3},
    'hr': {'name': 'Hrvatski', 'selectable': True, 'tier': 3},
    'it': {'name': 'Italiano', 'selectable': True, 'tier': 2},
    'lv': {'name': 'Latviešu', 'selectable': True, 'tier': 3},
    'lt': {'name': 'Lietuvių', 'selectable': True, 'tier': 3},
    'hu': {'name': 'Magyar', 'selectable': True, 'tier': 3},
    'mt': {'name': 'Malti', 'selectable': True, 'tier': 3},
    'nl': {'name': 'Nederlands', 'selectable': True, 'tier': 2},
    'pl': {'name': 'Polski', 'selectable': True, 'tier': 2},
    'pt': {'name': 'Português', 'selectable': True, 'tier': 3},
    'ro': {'name': 'Română', 'selectable': True, 'tier': 3},
    'sk': {'name': 'Slovenčina', 'selectable': True, 'tier': 3},
    'sl': {'name': 'Slovenščina', 'selectable': True, 'tier': 3},
    'fi': {'name': 'Suomi', 'selectable': True, 'tier': 3},
    'sv': {'name': 'Svenska', 'selectable': True, 'tier': 3},
    # Offered since 2026-08-08 (maintainer decision, audit §22
    # option 1): full POT coverage is guaranteed by the 0098
    # sync, so the worst case is English fallback — same deal
    # as every tier-3 language. They keep their historical
    # position, so the form lists them after the original 25:
    'be': {'name': 'беларуская', 'selectable': True, 'tier': 3},
    'bs': {'name': 'bosanski', 'selectable': True, 'tier': 3},
    'is': {'name': 'íslenska', 'selectable': True, 'tier': 3},
    'no': {'name': 'norsk', 'selectable': True, 'tier': 3},
    'sq': {'name': 'shqip', 'selectable': True, 'tier': 3},
    'sr': {'name': 'српски', 'selectable': True, 'tier': 3},
    'tr': {'name': 'Türkçe', 'selectable': True, 'tier': 3},
    'uk': {'name': 'українська', 'selectable': True, 'tier': 3},
}

def get_locales():
    """Return the list of available locales.
    Returns:
        list: The list of available locales.
    """
    # The registry is the source of truth (i18n audit 2026-08-08,
    # P0.1); the completeness locks keep it a bijection with the
    # locale/ directories on disk.
    return sorted(SUPPORTED_LOCALES)

AVAILABLE_LANGUAGES: Final = get_locales()

#LANGUAGES_TITLES = EUROPEAN_LOCALES
LANGUAGES_TITLES: Final = {'en': 'English',
                    'fr': 'Français'}

DEFAULT_NUMBER_OF_VOTERS: Final = 3

# TranslationStringFactory is used to translate strings
_: Final = TranslationStringFactory('alirpunkto')

# Derived: the form's choices — same keys, same order, same
# TranslationString values as the historical dict.
EUROPEAN_LOCALES: Final = {
    code: _(spec['name'])
    for code, spec in SUPPORTED_LOCALES.items()
    if spec['selectable']
}

CANDIDATURE_OID: Final = 'candidature_oid'
MEMBER_OID: Final = 'member_oid'
ACCESSED_MEMBER_OID: Final = 'accessed_member_oid'
SEED_LENGTH: Final = 10
# Maximum age, in seconds, of an OID link (password reset, email
# verification...). Past this delay the encrypted token is rejected.
OID_LINK_TTL_SECONDS: Final = int(
    os.getenv("ALIRPUNKTO_OID_LINK_TTL_SECONDS", str(24 * 60 * 60))
)
LDAP_ADMIN_OID: Final = os.getenv("LDAP_ADMIN_OID", "00000000-0000-0000-0000-000000000000")

MIN_PSEUDONYM_LENGTH: Final = 5 # Minimum pseudonym length
MAX_PSEUDONYM_LENGTH: Final = 20 # Maximum pseudonym length

# Constructing the regular expression using f-strings
pseudonym_pattern: Final = re.compile(
# To remove accent use:
    f'^[a-zA-Z0-9_.-]{{1}}(?:[a-zA-Z0-9_.-]| (?=[a-zA-Z0-9_.-])){{0,{MAX_PSEUDONYM_LENGTH - 2}}}[a-zA-Z0-9_.-]{{1}}$'
# To remove space use:
#     f'^[a-zA-Z0-9_.-]{{{MIN_PSEUDONYM_LENGTH},{MAX_PSEUDONYM_LENGTH}}}$'
# To allow accent use:
#     # Starting characters (letters, numbers, dashes, dots, underscores,
#     # accented letters)
#     fr'^[\u00C0-\u017F\w.-]' +
#     # Middle characters (including conditional space)
#     fr'(?:[\u00C0-\u017F\w.-]| (?=[\u00C0-\u017F\w.-]))' +
#     # Repetition with adjusted maximum length
#     fr'{{0,{MAX_PSEUDONYM_LENGTH - 2}}}' +
#     fr'[\u00C0-\u017F\w.-]$'  # Ending character
)

MIN_PASSWORD_LENGTH: Final = 12 # Minimum password length
MAX_PASSWORD_LENGTH: Final = 92 # Maximum password length

SPECIAL_CHARACTERS: Final = ('$', '@', '#', '%', '&', '*', '(', ')', '-', '_', '+', '=')

MEMBERS_BEING_MODIFIED = "members_being_modified"

LOCALE_LANG_MESSAGES: Final = os.path.join('locale', '{lang}', 'LC_MESSAGES', "")
ZPT_EXTENSION: Final = '.pt'

DEFAULT_COOPERATIVE_BEHAVIOUR_MARK: Final = 0


ALIRPUNKTO_LOG_SECRETS_PUBLIC_KEY_B64: Final = os.getenv("ALIRPUNKTO_LOG_SECRETS_PUBLIC_KEY_B64", None)
ALIRPUNKTO_LOG_ENCRYPTED_SECRETS: Final = os.getenv("ALIRPUNKTO_LOG_ENCRYPTED_SECRETS", "true") == "true"


# Values interpolated into the ${...} placeholders of the site-wide i18n
# messages. Shared by every schema description so a new site-specific variable
# only has to be declared once. Read-only: it is handed to many
# TranslationStrings, which must not be able to mutate each other's mapping.
_SITE_INFORMATION_DEFAULTS: Final = MappingProxyType({
    'domain_name': DOMAIN_NAME,
    'site_name': SITE_NAME,
    'site_url': f"{URL_SCHEME}://{DOMAIN_NAME}",
    'organization_details': ORGANIZATION_DETAILS,
    'url_workspace': URL_WORKSPACE,
    'url_pay_yearly_contrib': URL_PAY_YEARLY_CONTRIB,
    'url_purchase_shares': URL_PURCHASE_SHARES,
    'forgetting_time_constant': FORGETTING_TIME_CONSTANT,
})


class _SiteInformationMapping(Mapping):
    """Site variables resolved at rendering time from the deployment settings.

    The .ini settings are the source of truth (site_name, domain_name — the
    display name of the platform in the texts, not a URL —, site_url,
    organization_details, ...); the environment constants above are only
    compatibility fallbacks. Resolution happens on each key access through the
    thread-local registry, so the TranslationStrings that captured this mapping
    at import time (the deform field descriptions of register_form) and the
    template translations (auto_translate) all follow the configuration of the
    running deployment (issues #223 reopened, #242).
    """

    def __init__(self, defaults):
        self._defaults = defaults

    def _settings(self):
        try:
            from pyramid.threadlocal import get_current_registry
            return getattr(get_current_registry(), 'settings', None) or {}
        except Exception:
            return {}

    def __getitem__(self, key):
        default = self._defaults[key]
        value = self._settings().get(key)
        return value if value not in (None, '') else default

    def __iter__(self):
        return iter(self._defaults)

    def __len__(self):
        return len(self._defaults)


SITE_INFORMATION_MAPPING: Final = _SiteInformationMapping(
    _SITE_INFORMATION_DEFAULTS)
