import os, pytz, hashlib
from collections import defaultdict
from dotenv import load_dotenv, get_key, find_dotenv
from pyramid.config import Configurator
from pyramid_zodbconn import get_connection
from pyramid.i18n import get_localizer, TranslationStringFactory
from pyramid.i18n import default_locale_negotiator
from pyramid.events import NewRequest, subscriber
from pyramid.config import Configurator
from pyramid_mailer.mailer import Mailer
import logging

from .models import appmaker
from .models.candidature import Candidatures
from pyramid.session import SignedCookieSessionFactory
import deform
from pkg_resources import resource_filename
from pyramid.i18n import get_localizer
from pyramid.threadlocal import get_current_request

load_dotenv() # take environment variables from .env.
# SECRET_KEY is used for cookie signing
# This information is stored in environment variables
# See https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/security.html
# Using get_key() instead of os.getenv() as os.getenv() does not 
# handle values containing `=` properly.
SECRET_KEY = get_key(find_dotenv(), "SECRET_KEY")
# check if secret is not empty an make it accessible from the views
if not SECRET_KEY:
    raise ValueError("You must provide a base64 value for SECRET_KEY")

# LDAP informations are stored in environment variables
LDAP_SERVER = os.getenv("LDAP_SERVER")
LDAP_BASE_DN = get_key(find_dotenv(), "LDAP_BASE_DN")
LDAP_OU = get_key(find_dotenv(), "LDAP_OU")
LDAP_LOGIN = get_key(find_dotenv(), "LDAP_LOGIN")
LDAP_PASSWORD = get_key(find_dotenv(), "LDAP_PASSWORD")
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
log = logging.getLogger('alirpunkto')

# TranslationStringFactory is used to translate strings
_ = TranslationStringFactory('alirpunkto')

# Default session timeout is getting from environment variable or set to 7 hours
DEFAULT_SESSION_TIMEOUT = int(os.getenv("DEFAULT_SESSION_TIMEOUT", 7*60*60))

EUROPEAN_LOCALES = {
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

EUROPEAN_ZONES = [tz for tz in pytz.all_timezones if tz.startswith('Europe')]

def get_locales():
    """Return the list of available locales.
    Returns:
        list: The list of available locales.
    """
    dir_ = os.listdir(os.path.join(os.path.dirname(__file__),
                                   '.', 'locale'))
    return list(filter(lambda x: not x.endswith('.pot'), dir_)) + ['en']

AVAILABLE_LANGUAGES = get_locales()


#LANGUAGES_TITLES = EUROPEAN_LOCALES
LANGUAGES_TITLES = {'en': 'English',
                    'fr': 'Français'}

@subscriber(NewRequest)
def add_localizer(event):
    """add_localizer is used to add the localizer to the request
    """
    request = event.request
    localizer = get_localizer(request)
    
    def auto_translate(string):
        return localizer.translate(_(string))
    
    request.localizer = localizer
    # add the localizer and auto_translate to the registry
    request.registry.localizer = localizer
    request.registry.translate = auto_translate

def add_renderer_globals(event):
    """add_renderer_globals is used to add the localizer to the renderer globals
    """
    request = event['request'] # get the request from the event
    event['_'] = request.registry.translate # add the auto_translate function to the renderer globals
    event['localizer'] = request.localizer # add the localizer to the renderer globals

def get_time_zone(request):
    #TODO get user timezone
    return pytz.timezone('Europe/Paris')

def locale_negotiator(request):
    """locale_negotiator is used to get the locale from the request

    Args:
        request (pyramid.request.Request): the request

    Returns:
        str: the locale
    """
    locale = default_locale_negotiator(request)
    if locale is None and getattr(request, 'accept_language', None):
        locale = request.accept_language.best_match(AVAILABLE_LANGUAGES)

    return locale

def root_factory(request):
    """root_factory is used to create the root object of the ZODB database
    and to create the candidatures singletons.
    """
    conn = get_connection(request)
    root = appmaker(conn.root())
    Candidatures.get_instance(connection=conn)
    return root


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """

    with Configurator(settings=settings) as config:
        # set session factory
        hash_object = hashlib.sha256()
        hash_object.update(SECRET_KEY.encode('utf-8'))
        derived_secret = hash_object.hexdigest()
        session_factory = SignedCookieSessionFactory(derived_secret, timeout=DEFAULT_SESSION_TIMEOUT)        
        config.set_session_factory(session_factory)

        config.include('pyramid_chameleon')
        config.include('pyramid_tm')
        config.include('pyramid_retry')
        config.include('pyramid_zodbconn')
        # Use os.environ.get() for replacing the default values if exist
        settings['mail.username'] = MAIL_USERNAME if MAIL_USERNAME else os.environ.get('MAIL_USERNAME', None)
        if settings['mail.username'] == "None":
            settings['mail.username'] = None
        settings['mail.password'] = MAIL_PASSWORD if MAIL_PASSWORD else os.environ.get('MAIL_PASSWORD', None)
        if settings['mail.password'] == "None":
            settings['mail.password'] = None
        settings['mail.default_sender'] = MAIL_SENDER if MAIL_SENDER else os.environ.get('MAIL_SENDER', 'default_sender')
        settings['mail.host'] = MAIL_HOST if MAIL_HOST else os.environ.get('MAIL_HOST', 'localhost')
        settings['mail.port'] = MAIL_PORT if MAIL_PORT else os.environ.get('MAIL_PORT', '25')
        settings['mail.tls'] = MAIL_TLS if MAIL_TLS else os.environ.get('MAIL_TLS', 'false')
        settings['mail.ssl'] = MAIL_SSL if MAIL_SSL else os.environ.get('MAIL_SSL', 'false')

        # get secret key from environment variable
        config.registry.settings["mail.default_sender"] = settings['mail.default_sender'] # I didn't find a way to pass the default_sender to the views...
        # Create a mailer object
        mailer = Mailer.from_settings(settings)
        config.registry['mailer'] = mailer
        config.add_settings({'session.secret': SECRET_KEY})

        # Prefix for application-related settings
        PARAM = "applications."
        try : # Check if applications parameters are well defined in the configuration file
            # Extract settings items with the PARAM prefix into tuples (name, key) and value.
            l_applications = [(tuple(key[len(PARAM):].split(".")), value)
                                for key, value in settings.items()
                                if key.startswith(PARAM)]

            # Initialize dictionary for applications using defaultdict
            applications = defaultdict(dict)

            # Populate the 'applications' dictionary from 'l_applications'.
            for (name, k), v in l_applications:
                applications[name][k] = v
            # Verify for each application that the required parameters are defined (name, logo, url)
            for app_name, app in applications.items():
                if not 'name' in app:
                    raise Exception(f"Application {app_name} has no name")
                if not 'logo_file' in app:
                    raise Exception(f"Application {app_name} has no logo")
                if not 'url' in app:
                    raise Exception(f"Application {app_name} has no url")
            
            # I didn't find a way to pass the applications dictionary to the views...
            # So I store it in the registry
            config.registry.settings['applications'] = applications

        except Exception as e:
            log.error(f"Error while parsing applications settings: {e}")
            raise

        config.include('pyramid_mailer')
        config.include('.routes')
        config.set_root_factory(root_factory)
        config.add_route('home', '/')
        config.add_route('login', '/login')
        config.add_route('logout', '/logout')
        config.add_route('register', '/register')
        config.add_route('elections', '/elections')
        config.add_route('vote', '/vote')
        config.add_route('forgot_password', '/forgot_password')
        config.scan()
        config.add_translation_dirs('alirpunkto:locale/', 'colander:locale/', 'deform:locale/')
        config.set_locale_negotiator(locale_negotiator)       
        config.add_request_method(get_time_zone, 'tz', reify=True) # add tz to the request
        config.add_subscriber(add_renderer_globals, 'pyramid.events.BeforeRender')
        deform_template_dir = resource_filename('deform', 'templates/')
        def translator(term):
            return get_localizer(get_current_request()).translate(term)
        zpt_renderer = deform.ZPTRendererFactory(
            [deform_template_dir],
            translator=translator,
        )

    deform.Form.set_default_renderer(zpt_renderer)

    return config.make_wsgi_app()
