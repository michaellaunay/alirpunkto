"""The application log tells the whole story of a navigation
(production diagnosis of 2026-10-30).

A click on the home page's "Login" answered "Internal Server Error"
and ``var/log/alirpunkto.log`` stayed empty: the ``alirpunkto`` logger
writes to its file with ``propagate = 0`` while the escaping exception
was reported by Waitress on its own logger — stderr, the systemd
journal — and nothing in the application logged the request itself.
The outermost tween of ``alirpunkto.request_log`` now records every
request, every response and every escaping exception with its
traceback, on the application logger, without opening a session and
without copying a query value.
"""
from __future__ import annotations

import json
import logging
from unittest.mock import patch

import pytest
import webtest
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPFound
from pyramid.interfaces import ITweens
from pyramid.response import Response
from pyramid.session import SignedCookieSessionFactory

from alirpunkto import request_log
from alirpunkto.constants_and_globals import log


class _Records(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def messages(self, level=None):
        return [r.getMessage() for r in self.records
                if level is None or r.levelno == level]


@pytest.fixture
def records():
    """Collected straight from the ``alirpunkto`` logger: the ini files
    set ``propagate = 0``, so caplog's root handler would see nothing."""
    handler = _Records()
    previous = log.level
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    try:
        yield handler
    finally:
        log.removeHandler(handler)
        log.setLevel(previous)


def _app(view, *, session=False):
    with Configurator(settings={}) as config:
        if session:
            config.set_session_factory(SignedCookieSessionFactory('s' * 32))
        config.include('pyramid_tm')
        config.include('alirpunkto.request_log')
        config.add_route('probe', '/probe')
        config.add_view(view, route_name='probe')
        app = config.make_wsgi_app()
    return webtest.TestApp(app)


def test_the_tween_is_the_outermost_of_the_chain():
    app = _app(lambda request: Response('ok'))
    names = [name for name, _ in
             app.app.registry.queryUtility(ITweens).implicit()]
    assert names[0] == request_log.TWEEN_NAME
    assert 'pyramid_tm.tm_tween_factory' in names[1:]


def test_an_escaping_exception_is_logged_with_its_traceback(records):
    def boom(request):
        raise RuntimeError('the directory answered nonsense')
    app = _app(boom)
    with pytest.raises(RuntimeError):
        app.get('/probe?code=SECRET-CODE&state=SECRET-STATE')

    errors = [r for r in records.records if r.levelno == logging.ERROR]
    assert len(errors) == 1
    error = errors[0]
    assert error.exc_info and error.exc_info[0] is RuntimeError
    assert 'unhandled RuntimeError on GET /probe?code,state' in \
        error.getMessage()
    assert 'the directory answered nonsense' in error.getMessage()
    assert records.messages(logging.DEBUG)[0].startswith(
        'request GET /probe?code,state from ')


def test_query_values_never_reach_the_log(records):
    """Parameter names only: the SSO ``code``, an encrypted ``oid`` link
    or a ``state`` must not be readable from the log (A12)."""
    app = _app(lambda request: Response('ok'))
    app.get('/probe?oid=ENCRYPTED-LINK&code=THE-CODE')
    text = '\n'.join(records.messages())
    assert 'ENCRYPTED-LINK' not in text
    assert 'THE-CODE' not in text
    assert '/probe?code,oid' in text


def test_a_raised_redirect_is_an_ordinary_response(records):
    def go(request):
        raise HTTPFound(location='/elsewhere')
    app = _app(go)
    answer = app.get('/probe')
    assert answer.status_code == 302
    assert records.messages(logging.ERROR) == []
    (line,) = [m for m in records.messages(logging.DEBUG)
               if m.startswith('response ')]
    assert '-> 302 Found route=probe in ' in line


def test_a_5xx_built_by_the_stack_is_flagged(records):
    app = _app(lambda request: Response('bad', status=502))
    app.get('/probe', expect_errors=True)
    assert records.messages(logging.ERROR) == []
    (line,) = records.messages(logging.WARNING)
    assert '-> 502 Bad Gateway' in line


def test_the_tween_never_opens_the_session(records):
    """A signed-cookie session is re-issued on every access: the trace
    must not add a Set-Cookie to a static asset's answer."""
    app = _app(lambda request: Response('ok'), session=True)
    answer = app.get('/probe')
    assert 'Set-Cookie' not in answer.headers
    assert 'user=' not in '\n'.join(records.messages())


def test_the_user_is_named_when_the_view_opened_the_session(records):
    def login(request):
        request.session['user'] = json.dumps(
            {'name': 'alice', 'email': 'a@example.com', 'oid': 'o-1'})
        return Response('ok')
    app = _app(login, session=True)
    app.get('/probe')
    (line,) = [m for m in records.messages(logging.DEBUG)
               if m.startswith('response ')]
    assert 'user=alice' in line


@pytest.mark.functional
def test_the_real_application_registers_the_tween_first(app):
    names = [name for name, _ in
             app.registry.queryUtility(ITweens).implicit()]
    assert names[0] == request_log.TWEEN_NAME


@pytest.mark.functional
def test_the_production_symptom_leaves_a_traceback_in_the_log(
        testapp, records):
    """The home page's Login goes to /sso_login: whatever breaks there
    must land in the application log, traceback included."""
    from alirpunkto.views import sso_login as sso
    with patch.object(sso, 'start_round_trip',
                      side_effect=RuntimeError('auth_url() refused')):
        with pytest.raises(RuntimeError):
            testapp.get('/sso_login')
    (error,) = [r for r in records.records if r.levelno == logging.ERROR]
    assert error.exc_info[0] is RuntimeError
    assert 'unhandled RuntimeError on GET /sso_login' in error.getMessage()
    assert 'auth_url() refused' in error.getMessage()
