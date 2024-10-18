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
from pyramid.paster import get_appsettings
from pyramid.scripting import prepare
from pyramid.testing import DummyRequest, testConfig, setUp
from pyramid_mailer.testing import DummyMailer

from unittest.mock import patch
import pytest
import transaction
import webtest
from ldap3 import Server, Connection, MOCK_SYNC, OFFLINE_SLAPD_2_4, ALL
from ldap3.core.exceptions import LDAPException

def pytest_addoption(parser):
    parser.addoption('--ini', action='store', metavar='INI_FILE')

@pytest.fixture(scope='session')
def ini_file(request):
    # potentially grab this path from a pytest option
    return os.path.abspath(request.config.option.ini or 'testing.ini')

@pytest.fixture(scope='session')
def app_settings(ini_file):
    return get_appsettings(ini_file)


@pytest.fixture(scope='session', autouse=True)
def mocked_ldap():
    """Fixture to mock an OpenLDAP server and connection with recorded exchanges."""
    # Create a mock server with OpenLDAP schema
    from alirpunkto.ldap_factory import get_ldap_connection
    conn = get_ldap_connection('A_GREAT_PASSWORD', ldap_client_strategy=MOCK_SYNC)
    # Add entries to the mock server
    # Root entry with OpenLDAP-specific object classes
    conn.strategy.add_entry('dc=example,dc=com', {
        'objectClass': ['top', 'dcObject', 'organization'],
        'dc': 'example',
        'o': 'Example Organization'
    })

    # Admin user entry with appropriate object classes
    conn.strategy.add_entry('cn=admin,dc=example,dc=com', {
        'objectClass': ['top', 'person', 'organizationalPerson', 'inetOrgPerson'],
        'cn': 'admin',
        'sn': 'Administrator',
        'userPassword': 'A_GREAT_PASSWORD'
    })

    # The strategy automatically records all requests and responses
    # Access them via conn.strategy.requests and conn.strategy.responses

    return conn

@pytest.fixture
def tm():
    tm = transaction.manager
    tm.begin()
    tm.doom()

    yield tm

    tm.abort()

@pytest.fixture
def testapp(app, tm):
    testapp = webtest.TestApp(app, extra_environ={
        'HTTP_HOST': 'example.com',
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

