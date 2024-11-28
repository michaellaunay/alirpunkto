# This file is part of the alirpunkto package.
# author: Michael Launay

# Description: Constants for the alirpunkto app
from typing import Final
import os, sys, pytz
from dotenv import load_dotenv, get_key, find_dotenv
from pyramid.i18n import (
    TranslationStringFactory,
)
import logging
import re

# PyTest execution
PYTEST_CURRENT_TEST: Final = 'PYTEST_CURRENT_TEST' in os.environ or 'pytest' in sys.modules
# USE SSO DURING TESTS
PYTEST_SSO_TEST: Final = not PYTEST_CURRENT_TEST or os.getenv("PYTEST_USE_SSO", False)
# Load environment variables from .env.
dotenv_path: Final = find_dotenv()
load_dotenv(dotenv_path)

# LDAP informations are stored in environment variables
# Not Final due to __init__ initialization
SECRET_KEY: Final = "SECRET_KEY"
LDAP_SERVER: Final = os.getenv("LDAP_SERVER")
LDAP_BASE_DN: Final = get_key(dotenv_path, "LDAP_BASE_DN") if not PYTEST_CURRENT_TEST else "dc=example,dc=com"
LDAP_OU: Final = get_key(dotenv_path, "LDAP_OU")
LDAP_USE_SSL: Final = (
    (get_key(dotenv_path, "LDAP_USE_SSL") or "False").lower()
    in ['true', '1', "yes", "y"]
)
LDAP_PASSWORD: Final = "LDAP_PASSWORD" # use get_secret to get the password
LDAP_LOGIN: Final = get_key(dotenv_path, "LDAP_LOGIN")
LDAP_USER: Final = (f"{LDAP_LOGIN},{LDAP_OU},{LDAP_BASE_DN}"
    if LDAP_OU else f"{LDAP_LOGIN},{LDAP_BASE_DN}"
)
ADMIN_LOGIN: Final = get_key(dotenv_path, "ADMIN_LOGIN")
ADMIN_PASSWORD: Final = "ADMIN_PASSWORD" # use get_secret to get the password
ADMIN_EMAIL: Final = get_key(dotenv_path, "ADMIN_EMAIL")
MAIL_USERNAME: Final = os.getenv("MAIL_USERNAME")
MAIL_SENDER: Final = os.getenv("MAIL_SENDER")
MAIL_SERVER: Final = os.getenv("MAIL_SERVER")
MAIL_PASSWORD: Final = "MAIL_PASSWORD" # use get_secret to get the password
MAIL_PORT: Final = os.getenv("MAIL_PORT")
MAIL_HOST: Final = os.getenv("MAIL_HOST")
MAIL_TLS: Final = os.getenv("MAIL_TLS")
MAIL_SSL: Final = os.getenv("MAIL_SSL")
MAIL_SIGNATURE: Final = os.getenv("MAIL_SIGNATURE", "{fullsurname} {fullname} on {site_name} for {domain_name}")
DOMAIN_NAME: Final = os.getenv("DOMAIN_NAME")
SITE_NAME: Final = os.getenv("SITE_NAME")
ORGANIZATION_DETAILS: Final = os.getenv("ORGANIZATION_DETAILS")
KEYCLOAK_SERVER_URL:Final = get_key(dotenv_path, "KEYCLOAK_SERVER_URL",None) # The keycloak server
KEYCLOAK_REALM:Final = get_key(dotenv_path, "KEYCLOAK_REALM",None) # The realm
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

EUROPEAN_ZONES: Final = [tz for tz in pytz.all_timezones if tz.startswith('Europe')]

# LDAP Time Format
LDAP_TIME_FORMAT: Final = "%Y-%m-%dT%H:%M:%S"

def get_locales():
    """Return the list of available locales.
    Returns:
        list: The list of available locales.
    """
    dir_ = os.listdir(os.path.join(os.path.dirname(__file__),
                                   '.', 'locale'))
    return list(filter(lambda x: not x.endswith('.pot'), dir_)) + ['en']

AVAILABLE_LANGUAGES: Final = get_locales()

#LANGUAGES_TITLES = EUROPEAN_LOCALES
LANGUAGES_TITLES: Final = {'en': 'English',
                    'fr': 'Français'}

DEFAULT_NUMBER_OF_VOTERS: Final = 3

# TranslationStringFactory is used to translate strings
_: Final = TranslationStringFactory('alirpunkto')
EUROPEAN_LOCALES: Final = {
    'eo': _('Esperanto'),
    'bg': _('български'),
    'cs': _('čeština'),
    'da': _('dansk'),
    'de': _('Deutsch'),
    'et': _('Eesti'),
    'el': _('ελληνικά'),
    'en': _('English'),
    'es': _('Español'),
    'fr': _('Français'),
    'ga': _('Gaeilge'),
    'hr': _('Hrvatski'),
    'it': _('Italiano'),
    'lv': _('Latviešu'),
    'lt': _('Lietuvių'),
    'hu': _('Magyar'),
    'mt': _('Malti'),
    'nl': _('Nederlands'),
    'pl': _('Polski'),
    'pt': _('Português'),
    'ro': _('Română'),
    'sk': _('Slovenčina'),
    'sl': _('Slovenščina'),
    'fi': _('Suomi'),
    'sv': _('Svenska'),
}

CANDIDATURE_OID: Final = 'candidature_oid'
MEMBER_OID: Final = 'member_oid'
ACCESSED_MEMBER_OID: Final = 'accessed_member_oid'
SEED_LENGTH: Final = 10
LDAP_ADMIN_OID: Final = "00000000-0000-0000-0000-000000000000"

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
