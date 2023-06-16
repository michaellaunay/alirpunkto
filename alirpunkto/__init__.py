import os, pytz
from pyramid.config import Configurator
from pyramid_zodbconn import get_connection
from pyramid.i18n import get_localizer, TranslationStringFactory
from pyramid.i18n import Localizer, default_locale_negotiator
from pyramid.events import NewRequest, subscriber
import logging

from .models import appmaker

log = logging.getLogger('alirpunkto')

_ = TranslationStringFactory('alirpunkto')

DEFAULT_SESSION_TIMEOUT = 25200

EUROPEAN_LOCALES = {
    'esp': _('Esperanto'),
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
    dir_ = os.listdir(os.path.join(os.path.dirname(__file__),
                                   '.', 'locale'))
    return list(filter(lambda x: not x.endswith('.pot'), dir_)) + ['en']

AVAILABLE_LANGUAGES = get_locales()


#LANGUAGES_TITLES = EUROPEAN_LOCALES
LANGUAGES_TITLES = {'en': 'English',
                    'fr': 'Français'}

@subscriber(NewRequest)
def add_localizer(event):
    request = event.request
    localizer = get_localizer(request)
    
    def auto_translate(string):
        return localizer.translate(_(string))
    
    request.localizer = localizer
    # add the localizer and auto_translate to the registry
    request.registry.localizer = localizer
    request.registry.translate = auto_translate


def get_time_zone(request):
    #TODO get user timezone
    return pytz.timezone('Europe/Paris')

def locale_negotiator(request):
    locale = default_locale_negotiator(request)
    if locale is None and getattr(request, 'accept_language', None):
        locale = request.accept_language.best_match(AVAILABLE_LANGUAGES)

    return locale

def root_factory(request):
    conn = get_connection(request)
    return appmaker(conn.root())


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    with Configurator(settings=settings) as config:
        config.include('pyramid_chameleon')
        config.include('pyramid_tm')
        config.include('pyramid_retry')
        config.include('pyramid_zodbconn')
        config.include('.routes')
        config.set_root_factory(root_factory)
        config.add_route('login', '/login')
        config.add_route('register', '/register')
        config.add_route('forgot_password', '/forgot_password')
        config.scan()
        config.add_translation_dirs('alirpunkto:locale/')
        config.set_locale_negotiator(locale_negotiator)       
    return config.make_wsgi_app()
