"""The preferred language defaults to the browser language (issue #171).

The lang1 selection list preselected its first entry — whatever locale the
directory scan yielded first ("Esperanto" on the reporting deployment). The
field now carries a deferred default bound to the request: the locale
negotiator resolves the session, an explicit parameter, the cookie, then
Accept-Language — at the registration stage, the browser language.
"""
from __future__ import annotations

from types import SimpleNamespace

import colander
import deform
import pytest
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto.schemas.register_form import RegisterForm


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"


@pytest.fixture
def bound_schema():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_translation_dirs('alirpunkto:locale/')

    def _for(locale):
        request = DummyRequest()
        request.session = _Session()
        request._LOCALE_ = locale
        alirpunkto.add_localizer(NewRequest(request))
        return RegisterForm().bind(request=request)

    yield _for
    tearDown()


def test_the_default_is_the_negotiated_locale(bound_schema):
    assert bound_schema('fr').get('lang1').default == 'fr'
    assert bound_schema('de').get('lang1').default == 'de'


def test_an_unavailable_locale_leaves_no_preselection(bound_schema):
    request = SimpleNamespace(locale_name='xx', session=_Session())
    schema = RegisterForm().bind(request=request)
    assert schema.get('lang1').default is colander.null


def test_the_rendered_form_preselects_the_browser_language(bound_schema):
    """End to end: the deform widget marks the negotiated locale selected."""
    schema = bound_schema('fr')
    # Render with deform's stock renderer, hermetic to the application-wide
    # renderer another test may have installed globally.
    html = deform.Form(
        schema, renderer=deform.template.default_renderer).render()
    import re
    m = re.search(r'<select[^>]*name="lang1".*?</select>', html, re.S)
    assert m, "lang1 select not rendered"
    assert re.search(
        r'<option(?=[^>]*value="fr")(?=[^>]*selected)[^>]*>', m.group(0))
    # And the first entry of the unordered scan is NOT preselected any more.
    assert not re.search(
        r'<option(?=[^>]*value="eo")(?=[^>]*selected)[^>]*>', m.group(0))
