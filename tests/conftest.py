"""Shared pytest fixtures for AlirPunkto.

The default test suite is intentionally self-contained: it uses lightweight
mocks for LDAP-facing startup side effects, and it does not start Docker unless
a developer explicitly runs the dedicated helper script.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import transaction
import webtest
from pyramid.paster import get_appsettings
from pyramid.scripting import prepare
from pyramid.testing import DummyRequest, testConfig
from pyramid_mailer.testing import DummyMailer
from ZODB.Connection import Connection


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def pytest_addoption(parser):
    parser.addoption("--ini", action="store", metavar="INI_FILE")
    parser.addoption(
        "--use-docker-ldap",
        action="store_true",
        help=(
            "Run tests with an externally started LDAP service. The default "
            "unit test suite uses mocks and never starts Docker."
        ),
    )


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def ini_file(request) -> str:
    configured = request.config.option.ini or "testing.ini"
    path = Path(configured)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        pytest.skip(f"Pyramid functional tests require {path}")
    return str(path)


@pytest.fixture(scope="session")
def app_settings(ini_file):
    return get_appsettings(ini_file)


@pytest.fixture(autouse=True)
def reset_model_singletons():
    """Keep persistent singleton state from leaking between tests."""
    try:
        from alirpunkto.models.member import Members
        from alirpunkto.ldap_factory import reset_ldap_connection
    except Exception:
        yield
        return

    Members._instance = None
    reset_ldap_connection()
    yield
    Members._instance = None
    reset_ldap_connection()


@pytest.fixture
def zodb_connection():
    """Return a minimal ZODB connection mock accepted by isinstance checks."""
    root = {}
    connection = Mock(spec=Connection)
    connection.root.return_value = root
    return connection


@pytest.fixture
def members_mapping(zodb_connection):
    from alirpunkto.models.member import Members

    return Members.get_instance(connection=zodb_connection)


@pytest.fixture
def tm():
    manager = transaction.manager
    manager.begin()
    manager.doom()
    yield manager
    manager.abort()


@pytest.fixture(scope="session")
def app(app_settings):
    """Build the Pyramid app while suppressing LDAP startup side effects."""
    import alirpunkto

    with patch.object(alirpunkto, "create_ldap_groups_if_not_exists", return_value=None), \
         patch("alirpunkto.utils.get_ldap_member_list", return_value=[]):
        return alirpunkto.main({}, **app_settings)


@pytest.fixture
def testapp(app, tm):
    from alirpunkto.constants_and_globals import HTTP_TEST_HOST

    return webtest.TestApp(app, extra_environ={"HTTP_HOST": HTTP_TEST_HOST})


@pytest.fixture
def app_request(app, tm):
    with prepare(registry=app.registry) as env:
        request = env["request"]
        request.host = "example.com"
        request.locale_name = "en"
        request.tm = tm
        yield request


@pytest.fixture
def dummy_request(tm):
    request = DummyRequest()
    request.host = "example.com"
    request.locale_name = "en"
    request.tm = tm
    request.session = {}
    if request.registry.settings is None:
        # DummyRequest falls back to the global registry, which has no settings
        # unless a Configurator/testConfig is active. Seed an empty dict so the
        # fixture can populate it without depending on fixture ordering.
        request.registry.settings = {}
    request.registry.settings.update(
        {
            "site_name": "AlirPunkto",
            "domain_name": "alirpunkto.org",
            "organization_details": "AlirPunkto test organization",
            "applications": {},
            "notice_time_verifiers": 2,
            "number_of_voters": 3,
        }
    )
    request.route_url = lambda name, **kw: f"http://example.com/{name}"
    return request


mocked_challenges = {
    "A": ("three times four plus two", 14),
    "B": ("five times seven plus six", 41),
    "C": ("eight times one plus nine", 17),
    "D": ("two times three plus seven", 13),
}


@pytest.fixture
def mock_generate_math_challenges():
    with patch("alirpunkto.utils.generate_math_challenges", return_value=mocked_challenges):
        yield mocked_challenges


@pytest.fixture
def mailer_setup(testapp):
    class CustomDummyMailer(DummyMailer):
        def send(self, message):
            self.outbox.append(message)
            return True

    mailer = CustomDummyMailer()
    testapp.app.registry["mailer"] = mailer
    return mailer


@pytest.fixture
def dummy_config(dummy_request):
    with testConfig(request=dummy_request) as config:
        config.add_translation_dirs(
            "alirpunkto:locale/",
            "colander:locale/",
            "deform:locale/",
        )
        dummy_request.locale_name = "en"
        yield config
        try:
            from alirpunkto.utils import logout

            logout(dummy_request)
        except Exception:
            pass


@pytest.fixture
def anonymous_user():
    return SimpleNamespace(name="anonymous", email="anonymous@example.com", oid="anonymous")
