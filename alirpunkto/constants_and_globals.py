# Description: Constants for the alirpunkto app
from typing import Final
import os, pytz
from dotenv import load_dotenv, get_key, find_dotenv
from pyramid.i18n import (
    TranslationStringFactory,
)
import logging
import re

load_dotenv() # take environment variables from .env.
# SECRET_KEY is used for cookie signing
# This information is stored in environment variables
# See https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/security.html
# Using get_key() instead of os.getenv() as os.getenv() does not 
# handle values containing `=` properly.
SECRET_KEY: Final = get_key(find_dotenv(), "SECRET_KEY")
# check if secret is not empty an make it accessible from the views
if not SECRET_KEY:
    raise ValueError("You must provide a base64 value for SECRET_KEY")

# LDAP informations are stored in environment variables
# Not Final due to __init__ initialization
LDAP_SERVER = os.getenv("LDAP_SERVER")
LDAP_BASE_DN = get_key(find_dotenv(), "LDAP_BASE_DN")
LDAP_OU = get_key(find_dotenv(), "LDAP_OU")
LDAP_LOGIN = get_key(find_dotenv(), "LDAP_LOGIN")
LDAP_PASSWORD = get_key(find_dotenv(), "LDAP_PASSWORD")
ADMIN_LOGIN = get_key(find_dotenv(), "ADMIN_LOGIN")
ADMIN_PASSWORD = get_key(find_dotenv(), "ADMIN_PASSWORD")
ADMIN_EMAIL = get_key(find_dotenv(), "ADMIN_EMAIL")
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_SENDER = os.getenv("MAIL_SENDER")
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PASSWORD = get_key(find_dotenv(), "MAIL_PASSWORD")
MAIL_PORT = os.getenv("MAIL_PORT")
MAIL_HOST = os.getenv("MAIL_HOST")
MAIL_TLS = os.getenv("MAIL_TLS")
MAIL_SSL = os.getenv("MAIL_SSL")
MAIL_SIGNATURE = os.getenv("MAIL_SIGNATURE", "{fullsurname} {fullname} on {site_name}")

# logging configuration
log: Final = logging.getLogger('alirpunkto')

# Default session timeout is getting from environment variable or set to 7 hours
DEFAULT_SESSION_TIMEOUT: Final = int(os.getenv("DEFAULT_SESSION_TIMEOUT", 7*60*60))

EUROPEAN_ZONES: Final = [tz for tz in pytz.all_timezones if tz.startswith('Europe')]

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