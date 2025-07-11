import os, pytz, hashlib
from collections import defaultdict
from pyramid.config import Configurator
from pyramid_zodbconn import get_connection
from pyramid.i18n import (
    get_localizer,
    default_locale_negotiator,
    get_localizer
)
from pyramid.events import NewRequest, subscriber
from pyramid.config import Configurator
from pyramid_mailer.mailer import Mailer

from .models import appmaker
from .models.member import Members
from pyramid.session import SignedCookieSessionFactory
import deform
from pkg_resources import resource_filename
from pyramid.threadlocal import get_current_request

from .constants_and_globals import (
    _,
    log,
    SECRET_KEY,
    LDAP_ADMIN_OID,
    LDAP_BASE_DN,
    LDAP_OU,
    LDAP_USER,
    LDAP_PASSWORD,
    AVAILABLE_LANGUAGES,
    ADMIN_LOGIN,
    MAIL_USERNAME,
    MAIL_PASSWORD,
    MAIL_SENDER,
    MAIL_HOST,
    MAIL_PORT,
    MAIL_TLS,
    MAIL_SSL,
    DEFAULT_SESSION_TIMEOUT,
    DEFAULT_NUMBER_OF_VOTERS,
    KEYCLOAK_REDIRECT_PATH,
)
from .secret_manager import get_secret
from dotenv import get_key

get_secret(None) # force the initialization of the secrets

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
    Members.get_instance(connection=conn)
    return root

def create_ldap_groups_if_not_exists():
    """
    Connects to an LDAP server and creates specified groups if they do not
    already exist.

    This function establishes a connection to an LDAP server using predefined
    LDAP settings. 
    It then iteratively checks for the existence of a set of predefined groups. 
    If a group does not exist, it creates the group with its specific
    attributes in the LDAP directory.

    Predefined groups include OrdinaryMembersGroup, CooperatorsGroup,
    BoardMembersGroup, and MediationArbitrationCouncilGroup. Each group is
    defined with a common name (cn) and a description. Initially, these groups
    have no members.

    Note: The function assumes that the specified LDAP_OU already exists in the LDAP directory.
    """

    # Connecting to the LDAP Server
    from .ldap_factory import get_ldap_connection
    conn = get_ldap_connection(ldap_user=LDAP_USER,
        ldap_password=get_secret(LDAP_PASSWORD),
        ldap_auto_bind=True
    )

    admin_dn = f"uid={LDAP_ADMIN_OID},cn={ADMIN_LOGIN},{LDAP_BASE_DN}"
    # Defining the groups to be created
    groups = [
        {"name": "ordinaryMembersGroup", "description": "Group for ordinary members of the cooperative"},
        {"name": "cooperatorsGroup", "description": "Group for active cooperators of the cooperative"},
        {"name": "administratorsGroup", "description": "Group for active administrators of the cooperative"},
        {"name": "providersGroup", "description": "Group for active providers of the cooperative"},
        {"name": "boardMembersGroup", "description": "Group for board members of the cooperative"},
        {"name": "mediationArbitrationCouncilGroup", "description": "Group for members of the Mediation Arbitration Council"},
        {"name": "candidatesMissingShareYearContribGroup", "description": "Group for members who have not contributed their share for the current year"},
        {"name": "candidatesMissingShareGroup", "description": "Group for members who have not contributed their share"},
        {"name": "candidatesMissingYearContribGroup", "description": "Group for members who have not contributed for the current year"},
        {"name": "sanctionedGroup", "description": "Group for sanctioned members"},
        {"name": "sanctionedMissingYearContribGroup", "description": "Group for sanctioned members who have not contributed for the current year"},
        {"name": "communityMembersGroup", "description": "Group for members of the community who are not yet cooperators"},
        {"name": "suspendedBoardMembersGroup", "description": "Group for suspended board members"},
        {"name": "suspendedMediationArbitrationCouncilGroup", "description": "Group for suspended members of the Mediation Arbitration Council"}
    ]

    # Checking for existence and creating groups
    for group in groups:
        dn = (f"cn={group['name']},{LDAP_OU},{LDAP_BASE_DN}"
                if LDAP_OU else f"cn={group['name']},{LDAP_BASE_DN}")
        # Check if the group already exists
        if conn.search(dn, '(objectClass=*)', search_scope='BASE'):
            log.warning(f"Group {group['name']} already exists.")
            continue  # Skip to the next group if it already exists

        # Creating the group
        attributes = {
            'objectClass': ["top", "groupOfUniqueNames"],
            'description': group['description'],
            'uniqueMember': admin_dn
        }
        if not conn.add(dn, attributes=attributes):
            log.error(f"Error adding group {group['name']}: {conn.result}")
    # Closing the connection
    conn.unbind()

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
        settings['mail.password'] = get_secret(MAIL_PASSWORD)
        if settings['mail.password'] == "None":
            settings['mail.password'] = None
        settings['mail.default_sender'] = MAIL_SENDER if MAIL_SENDER else os.environ.get('MAIL_SENDER', 'default_sender')
        settings['mail.host'] = MAIL_HOST if MAIL_HOST else os.environ.get('MAIL_HOST', 'localhost')
        settings['mail.port'] = MAIL_PORT if MAIL_PORT else os.environ.get('MAIL_PORT', '25')
        settings['mail.tls'] = MAIL_TLS if MAIL_TLS else os.environ.get('MAIL_TLS', 'false')
        settings['mail.ssl'] = MAIL_SSL if MAIL_SSL else os.environ.get('MAIL_SSL', 'false')
        settings['site_logo'] = settings['site_logo'] if 'site_logo' in settings else os.environ.get('SITE_LOGO', 'static/alirpunkto.png')
        settings['site_logo_small'] = settings['site_logo_small'] if 'site_logo_small' in settings else os.environ.get('SITE_LOGO_SMALL', 'static/alirpunkto-16x16.png')
        settings['number_of_voters'] = settings['number_of_voters'] if 'number_of_voters' in settings else os.environ.get('NUMBER_OF_VOTERS', DEFAULT_NUMBER_OF_VOTERS)

        # set site_logo and site_logo_small in the registry
        config.registry.settings['site_logo'] = settings['site_logo']
        config.registry.settings['site_logo_small'] = settings['site_logo_small']
        
        # get secret key from environment variable
        config.registry.settings["mail.default_sender"] = settings['mail.default_sender'] # I didn't find a way to pass the default_sender to the views...
        # Create a mailer object
        mailer = Mailer.from_settings(settings)
        config.registry['mailer'] = mailer
        config.add_settings({'session.secret': get_secret(SECRET_KEY)})

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
                if not 'id' in app:
                    raise Exception(f"Application {app_name} has no id")
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
        config.add_route('manage_provider', '/manage_provider')
        config.add_route('elections', '/elections')
        config.add_route('vote', '/vote')
        config.add_route('forgot_password', '/forgot_password')
        config.add_route('modify_member', '/modify_member')
        config.add_route('get_email', '/get_email')
        config.add_route('check_new_email', '/check_new_email')
        config.add_route('sso_login', '/sso_login')
        config.add_route(KEYCLOAK_REDIRECT_PATH, f'/{KEYCLOAK_REDIRECT_PATH}')
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
    create_ldap_groups_if_not_exists()

    return config.make_wsgi_app()
