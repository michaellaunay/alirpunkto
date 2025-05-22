#This module contains fixtures for testing the alirpunkto application.
#
# Fixtures:
#
# - ini_file: Returns the absolute path of the INI file specified in the pytest options or 'testing.ini' if not provided.
# - app_settings: Returns the application settings parsed from the INI file.
# - app: Returns the Pyramid WSGI application instance.
# - tm: Returns a transaction manager for managing database transactions.
# - testapp: Returns a webtest.TestApp instance for making HTTP requests to the application.
# - app_request: Returns a real request object with some drawbacks for testing purposes.
# - dummy_request: Returns a lightweight dummy request object for easier mocking and control of side-effects.
# - mock_generate_math_challenges: Mocks the 'generate_math_challenges' function and returns a dictionary of mocked challenges.
# - mailer_setup: Sets up a DummyMailer object as the mailer in the application registry.
# - dummy_config: Returns a dummy Configurator object for mock configuration and pushing threadlocals.

import os
import time
import socket
import subprocess
from pyramid.paster import get_appsettings
from pyramid.scripting import prepare
from pyramid.testing import DummyRequest, testConfig, setUp
from pyramid_mailer.testing import DummyMailer

from unittest.mock import patch, Mock
import pytest
import transaction
import webtest
from ldap3 import MOCK_SYNC, ALL, SUBTREE
from ldap3.protocol.rfc4512 import AttributeTypeInfo, ObjectClassInfo

def pytest_addoption(parser):
    parser.addoption('--ini', action='store', metavar='INI_FILE')
    parser.addoption('--use-docker-ldap', action='store_true', help='Use Docker LDAP container for testing')

@pytest.fixture(scope='session')
def ini_file(request):
    # potentially grab this path from a pytest option
    return os.path.abspath(request.config.option.ini or 'testing.ini')

@pytest.fixture(scope='session')
def app_settings(ini_file):
    return get_appsettings(ini_file)

def is_port_in_use(port, host='localhost'):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

@pytest.fixture(scope='session', autouse=True)
def ldap_server(request):
    """
    Fixture to either use a Docker LDAP container or mock LDAP based on options.
    """
    from alirpunkto.constants_and_globals import TEST_WITH_DOCKER_LDAP_PORT

    use_docker = request.config.getoption('--use-docker-ldap', False)
    if use_docker:
        # Set environment variable to indicate Docker LDAP usage
        os.environ['USE_DOCKER_LDAP'] = 'true'
        
        # Check if the LDAP container is already running
        ldap_port = TEST_WITH_DOCKER_LDAP_PORT
        if is_port_in_use(ldap_port):
            print(f"LDAP port {ldap_port} already in use, assuming container is running")
            # Wait a bit to ensure the LDAP server is fully initialized
            time.sleep(2)
            return setup_real_ldap_connection()
        
        # Start the LDAP container using docker-compose
        print("Starting LDAP test container...")
        try:
            subprocess.run(
                ["docker-compose", "-f", "docker-compose.test.yml", "up", "-d"],
                check=True
            )
            
            # Wait for LDAP to be ready
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    if is_port_in_use(ldap_port):
                        time.sleep(5)  # Give a bit more time for LDAP to fully initialize
                        conn = setup_real_ldap_connection()
                        print("LDAP container is up and running")
                        
                        # Register the finalizer to stop the container
                        def finalizer():
                            print("Stopping LDAP test container...")
                            subprocess.run(
                                ["docker-compose", "-f", "docker-compose.test.yml", "down"],
                                check=False
                            )
                        request.addfinalizer(finalizer)
                        
                        return conn
                except Exception as e:
                    print(f"Waiting for LDAP to be ready, attempt {attempt+1}/{max_attempts}: {e}")
                    time.sleep(2)
            
            raise Exception("LDAP container failed to start and be ready in time")
        except Exception as e:
            print(f"Error starting LDAP container: {e}")
            # If there was an error starting the container, fall back to the mock
            os.environ['USE_DOCKER_LDAP'] = 'false'
            return setup_mock_ldap()
    else:
        # Ensure the environment variable is set to false
        os.environ['USE_DOCKER_LDAP'] = 'false'
        return setup_mock_ldap()

def setup_real_ldap_connection():
    """Set up a connection to the real LDAP test container"""
    from alirpunkto.constants_and_globals import LDAP_BASE_DN
    from alirpunkto.ldap_factory import get_ldap_connection
    from alirpunkto.secret_manager import get_secret
    
    # Get credentials from environment or use defaults for the test container
    admin_dn = f"cn=admin,{LDAP_BASE_DN}"
    admin_password = os.environ.get('LDAP_ADMIN_PASSWORD', 'test_password')
    
    # Connect to the LDAP server
    conn = get_ldap_connection(
        ldap_user=admin_dn,
        ldap_password=admin_password,
        ldap_auto_bind=True,
        ldap_use_ssl=False,
        ldap_server='localhost',
        ldap_port=3389
    )
    
    # Initialize test data
    initialize_ldap_for_tests(conn, LDAP_BASE_DN)
    
    return conn

def initialize_ldap_for_tests(conn, base_dn):
    """Initialize the LDAP server with necessary test data"""
    try:
        # Check if the base DN exists
        conn.search(base_dn, '(objectClass=*)', search_scope=SUBTREE)
        if not conn.entries:
            conn.add(base_dn, ['top', 'dcObject', 'organization'], 
                    {'dc': base_dn.split(',')[0].split('=')[1], 'o': 'Test Organization'})
            print(f"Created base DN: {base_dn}")
        
        # Create organizational units if they don't exist
        for ou in ['users', 'groups']:
            ou_dn = f'ou={ou},{base_dn}'
            conn.search(ou_dn, '(objectClass=*)', search_scope=SUBTREE)
            if not conn.entries:
                conn.add(ou_dn, ['top', 'organizationalUnit'], {'ou': ou})
                print(f"Created OU: {ou_dn}")
        
        # Create required groups
        create_test_groups(conn, base_dn)
        
        # Ensure admin user exists
        from alirpunkto.constants_and_globals import ADMIN_LOGIN, ADMIN_PASSWORD, LDAP_ADMIN_OID
        from alirpunkto.secret_manager import get_secret
        
        admin_dn = f"cn={ADMIN_LOGIN},ou=users,{base_dn}"
        conn.search(admin_dn, '(objectClass=*)', search_scope=SUBTREE)
        if not conn.entries:
            conn.add(admin_dn, 
                attributes={
                    'objectClass': ['top', 'person', 'organizationalPerson', 'inetOrgPerson'],
                    'cn': ADMIN_LOGIN,
                    'sn': ADMIN_LOGIN,
                    'uid': LDAP_ADMIN_OID,
                    'userPassword': get_secret(ADMIN_PASSWORD)
                }
            )
            print(f"Created admin user: {admin_dn}")
    
    except Exception as e:
        print(f"Error initializing LDAP for tests: {e}")
        raise

def create_test_groups(conn, base_dn):
    """Create the necessary groups for testing"""
    from alirpunkto.constants_and_globals import LDAP_ADMIN_OID, ADMIN_LOGIN
    
    admin_dn = f"cn={ADMIN_LOGIN},ou=users,{base_dn}"
    
    groups = [
        {"name": "ordinaryMembersGroup", "description": "Group for ordinary members"},
        {"name": "cooperatorsGroup", "description": "Group for cooperators"}
    ]
    
    for group in groups:
        group_dn = f"cn={group['name']},ou=groups,{base_dn}"
        conn.search(group_dn, '(objectClass=*)', search_scope=SUBTREE)
        if not conn.entries:
            conn.add(group_dn, 
                attributes={
                    'objectClass': ['top', 'groupOfUniqueNames'],
                    'cn': group['name'],
                    'description': group['description'],
                    'uniqueMember': admin_dn
                }
            )
            print(f"Created group: {group_dn}")

def setup_mock_ldap():
    """Set up the mock LDAP for testing when Docker is not available"""
    from alirpunkto.constants_and_globals import LDAP_LOGIN, LDAP_USER, LDAP_PASSWORD, ADMIN_PASSWORD, LDAP_BASE_DN
    from alirpunkto.ldap_factory import get_ldap_connection
    from alirpunkto.secret_manager import get_secret
    
    conn = get_ldap_connection(ldap_user=LDAP_USER,
        ldap_password=get_secret(LDAP_PASSWORD),
        ldap_client_strategy=MOCK_SYNC)

    def extract_syntax(syntax_str):
        """Extract the syntax OID without size limit."""
        if '{' in syntax_str:
            syntax_oid = syntax_str.split('{')[0]
        else:
            syntax_oid = syntax_str
        return syntax_oid.strip("'")

    # Define custom attributes
    nationality_attribute = AttributeTypeInfo(
        oid='1.3.6.1.4.1.61000.1.1',
        name='nationality',
        description='Nationality of the individual',
        equality='caseIgnoreMatch',
        syntax=extract_syntax('1.3.6.1.4.1.1466.115.121.1.15{40}'),
        single_value=True
    )

    birthdate_attribute = AttributeTypeInfo(
        oid='1.3.6.1.4.1.61000.1.2',
        name='birthdate',
        description='Birth date of the individual in ISO 8601 format',
        equality='caseIgnoreMatch',
        syntax=extract_syntax('1.3.6.1.4.1.1466.115.121.1.15{25}'),
        single_value=True
    )

    second_language_attribute = AttributeTypeInfo(
        oid='1.3.6.1.4.1.61000.1.3',
        name='secondLanguage',
        description='Second language of the individual',
        equality='caseIgnoreMatch',
        syntax=extract_syntax('1.3.6.1.4.1.1466.115.121.1.15{40}'),
        single_value=True
    )

    cooperative_behaviour_mark_attribute = AttributeTypeInfo(
        oid='1.3.6.1.4.1.61000.1.4',
        name='cooperativeBehaviourMark',
        description='Cooperative Behaviour Mark, expected to be a floating-point number stored as a string',
        syntax=extract_syntax('1.3.6.1.4.1.1466.115.121.1.15{127}'),
        single_value=True
    )

    cooperative_behavior_mark_update_attribute = AttributeTypeInfo(
        oid='1.3.6.1.4.1.61000.1.5',
        name='cooperativeBehaviorMarkUpdate',
        description='Last Update Time of the Cooperative Behaviour Mark',
        syntax='1.3.6.1.4.1.1466.115.121.1.24',  # Generalized Time Syntax
        single_value=True
    )

    third_language_attribute = AttributeTypeInfo(
        oid='1.3.6.1.4.1.61000.1.6',
        name='thirdLanguage',
        description='Third Interaction Language',
        syntax='1.3.6.1.4.1.1466.115.121.1.15',
        single_value=True
    )

    is_active_attribute = AttributeTypeInfo(
        oid='1.3.6.1.4.1.61000.1.7',
        name='isActive',
        description='Indicates if the user is active',
        equality='booleanMatch',
        syntax='1.3.6.1.4.1.1466.115.121.1.7',
        single_value=True
    )

    number_shares_owned_attribute = AttributeTypeInfo(
        oid='1.3.6.1.4.1.61000.1.8',
        name='numberSharesOwned',
        description='Number of Shares Owned',
        syntax='1.3.6.1.4.1.1466.115.121.1.27'  # Integer Syntax
    )

    date_end_validity_yearly_contribution_attribute = AttributeTypeInfo(
        oid='1.3.6.1.4.1.61000.1.9',
        name='dateEndValidityYearlyContribution',
        description='End Date of Validity for Yearly Contribution in ISO 8601 format',
        equality='caseIgnoreMatch',
        syntax=extract_syntax('1.3.6.1.4.1.1466.115.121.1.15{25}'),
        single_value=True
    )

    iban_attribute = AttributeTypeInfo(
        oid='1.3.6.1.4.1.61000.1.10',
        name='IBAN',
        description='IBAN bank account number of the individual',
        equality='caseIgnoreMatch',
        syntax=extract_syntax('1.3.6.1.4.1.1466.115.121.1.15{34}'),
        single_value=True
    )

    unique_member_of_attribute = AttributeTypeInfo(
        oid='1.3.6.1.4.1.61000.1.11',
        name='uniqueMemberOf',
        description='DN of the group to which the user belongs',
        equality='distinguishedNameMatch',
        syntax='1.3.6.1.4.1.1466.115.121.1.12'  # Distinguished Name Syntax
    )

    date_erasure_all_data_attribute = AttributeTypeInfo(
        oid='1.3.6.1.4.1.61000.1.12',
        name='dateErasureAllData',
        description='Date by which the user data should be erased',
        equality='caseIgnoreMatch',
        substring='caseIgnoreSubstringsMatch',
        syntax=extract_syntax('1.3.6.1.4.1.1466.115.121.1.15{25}'),
        single_value=True
    )

    # Add the attributes to the schema
    attributes = [
        nationality_attribute,
        birthdate_attribute,
        second_language_attribute,
        cooperative_behaviour_mark_attribute,
        cooperative_behavior_mark_update_attribute,
        third_language_attribute,
        is_active_attribute,
        number_shares_owned_attribute,
        date_end_validity_yearly_contribution_attribute,
        iban_attribute,
        unique_member_of_attribute,
        date_erasure_all_data_attribute
    ]
    from alirpunkto.ldap_factory import get_ldap_server
    schema_info = get_ldap_server()._schema_info
    for attr in attributes:
        schema_info.attribute_types[attr.name] = attr
        schema_info.attribute_types[attr.oid] = attr

    # Define the custom object class
    alirpunkto_person_class = ObjectClassInfo(
        oid='1.3.6.1.4.1.61000.2.2.1',
        name='alirpunktoPerson',
        description='AlirPunkto specific person object class',
        superior=['inetOrgPerson'],
        kind='structural',
        must_contain=['uid', 'cn', 'sn', 'mail', 'employeeType', 'isActive'],
        may_contain=[
            'givenName', 'nationality', 'birthdate', 'preferredLanguage', 'description',
            'jpegPhoto', 'secondLanguage', 'thirdLanguage', 'cooperativeBehaviourMark',
            'cooperativeBehaviorMarkUpdate', 'numberSharesOwned',
            'dateEndValidityYearlyContribution', 'IBAN', 'uniqueMemberOf'
        ]
    )

    # Add the object class to the schema
    schema_info.object_classes[alirpunkto_person_class.name] = alirpunkto_person_class
    schema_info.object_classes[alirpunkto_person_class.oid] = alirpunkto_person_class

    # Add the custom schema to the mocked server
    from alirpunkto.ldap_factory import get_ldap_connection
    server = get_ldap_server()
    server._schema_info = schema_info  # Replace the schema with the alirpunkto's schema
   
    # Add entries to the mock server
    # Root entry with OpenLDAP-specific object classes
    conn.strategy.add_entry(LDAP_BASE_DN, {
        'objectClass': ['top', 'dcObject', 'organization'],
        'dc': LDAP_BASE_DN.split(',')[0].split('=')[1],
        'o': 'Example Organization'
    })

    # Admin user entry with appropriate object classes
    conn.strategy.add_entry(LDAP_USER, {
        'objectClass': ['top', 'person', 'organizationalPerson', 'inetOrgPerson'],
        'cn': LDAP_LOGIN.split(',')[0].split('=')[1],
        'sn': LDAP_LOGIN.split(',')[0].split('=')[1],
        'userPassword': get_secret(LDAP_PASSWORD)
    })

    return conn

@pytest.fixture(scope='session')
def mocked_ldap(ldap_server):
    """Alias for backward compatibility"""
    return ldap_server

@pytest.fixture
def tm():
    tm = transaction.manager
    tm.begin()
    tm.doom()

    yield tm

    tm.abort()

@pytest.fixture
def testapp(app, tm):
    from alirpunkto.constants_and_globals import HTTP_TEST_HOST
    testapp = webtest.TestApp(app, extra_environ={
        'HTTP_HOST': HTTP_TEST_HOST,
    })

    return testapp

@pytest.fixture
def app_request(app, tm):
    """
    A real request.

    This request is almost identical to a real request but it has some
    drawbacks in tests as it's harder to mock data and is heavier.

    """
    with prepare(registry=app.registry) as env:
        request = env['request']
        request.host = 'example.com'
        request.locale_name = 'en'
        yield request

@pytest.fixture
def dummy_request(tm):
    """
    A lightweight dummy request.

    This request is ultra-lightweight and should be used only when the request
    itself is not a large focus in the call-stack.  It is much easier to mock
    and control side-effects using this object, however:

    - It does not have request extensions applied.
    - Threadlocals are not properly pushed.

    """
    request = DummyRequest()
    request.host = 'example.com'
    request.tm = tm
    request.locale_name = 'en'
    return request

mocked_challenges = {
        "A": ("three times four plus two", 14),
        "B": ("five times seven plus six", 41),
        "C": ("eight times one plus nine", 17),
        "D": ("two times three plus seven", 13),
    }
@pytest.fixture
def mock_generate_math_challenges():    
    with patch('alirpunkto.utils.generate_math_challenges', return_value=mocked_challenges):
        yield

@pytest.fixture
def mailer_setup(testapp):
    class CustomDummyMailer(DummyMailer):
        def send(self, message):
            """Mock sending a transactional message via SMTP.

            The message is appended to the 'outbox' list and returns True
            to indicate success, mimicking the behavior of the real Mailer.
            This is a patch to https://github.com/Pylons/pyramid_mailer/issues/101

            :param message: a 'Message' instance.
            :return: True to indicate the message was 'sent' successfully.
            """
            self.outbox.append(message)
            return True  # Indicate that the send was successful
    mailer = CustomDummyMailer()
    testapp.app.registry['mailer'] = mailer
    return mailer

@pytest.fixture
def dummy_config(dummy_request):
    """
    A dummy :class:`pyramid.config.Configurator` object.  This allows for
    mock configuration, including configuration for ``dummy_request``, as well
    as pushing the appropriate threadlocals.

    """
    with testConfig(request=dummy_request) as config:
         # Add translation directories
        config.add_translation_dirs('alirpunkto:locale/', 'colander:locale/', 'deform:locale/')

        # Set locale name for the request (if not already set)
        dummy_request.locale_name = 'en'
        
        yield config
        from alirpunkto.utils import logout
        logout(dummy_request)

@pytest.fixture(scope='session')
def app(app_settings):
    from alirpunkto import main
    return main({}, **app_settings)
