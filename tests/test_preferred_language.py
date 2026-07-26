"""Regression tests for the member's preferred language (issue #204).

The Candidate chooses a preferred language (lang1) upon registration, and a
member can change it in their profile — yet e-mails and the interface kept
using the browser's Accept-Language. E-mails must use the recipient's declared
language, and the interface must follow the language stored in the session at
login / registration / profile modification (an explicit _LOCALE_ still wins).
"""
from __future__ import annotations

import inspect
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import alirpunkto.utils as utils
from alirpunkto import locale_negotiator
from alirpunkto.utils import get_preferred_language, get_local_template

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _request(accept='en', session=None, params=None):
    return SimpleNamespace(
        accept_language=SimpleNamespace(best_match=lambda langs: accept),
        session=session if session is not None else {},
        params=params or {},
        cookies={},
        registry=SimpleNamespace(queryUtility=lambda *a, **k: None, settings={
            'domain_name': 'alirpunkto.org', 'site_name': 'AlirPunkto',
            'session.secret': 'x' * 32,
        }),
        route_url=lambda *a, **k: 'http://example/view',
    )


def _member(lang1='fr'):
    return SimpleNamespace(
        email='m@example.com', pseudonym='m', oid='oid-1',
        data=SimpleNamespace(lang1=lang1, fullname='Jean'),
        email_send_status_history=[SimpleNamespace(seed='s')],
        add_email_send_status=lambda *a, **k: None,
    )


# ---------------- e-mails: the recipient's declared language wins ----------
def test_declared_language_wins_over_the_browser():
    assert get_preferred_language(_request(accept='en'), _member('fr')) == 'fr'


def test_browser_language_without_declared_language():
    assert get_preferred_language(_request(accept='de'), _member(None)) == 'de'


def test_invalid_declared_language_falls_back():
    assert get_preferred_language(_request(accept='en'), _member('zz')) == 'en'


def test_no_member_keeps_the_old_behaviour():
    assert get_preferred_language(_request(accept='it')) == 'it'


def test_template_is_resolved_in_the_member_language():
    path = get_local_template(
        _request(accept='en'),
        'locale/{lang}/LC_MESSAGES/reset_password_email.pt',
        member=_member('fr'),
    ).abspath()
    assert os.sep + 'fr' + os.sep in path


def test_email_to_member_uses_the_member_language():
    """End to end: the resolver handed to send_email is the fr template even
    though the triggering request prefers English."""
    captured = {}

    def fake_send_email(req, subject, recipients, template_resolver, template_vars, *a, **k):
        captured['resolver'] = str(template_resolver)
        return True

    with patch.object(utils, 'send_email', fake_send_email), \
         patch.object(utils, 'get_localizer',
                      lambda r: SimpleNamespace(translate=lambda s: 'subject')), \
         patch.object(utils, 'encrypt_oid', lambda *a, **k: 'token'):
        utils.send_email_to_member(
            _request(accept='en'), _member('fr'), 'test',
            'reset_password_email', 'reset_password_email_subject',
            'forgot_password',
        )
    assert os.sep + 'fr' + os.sep in captured['resolver']


# ---------------- interface: the session language drives the negotiator ----
def test_negotiator_uses_the_session_language():
    request = _request(session={'preferred_language': 'de'})
    assert locale_negotiator(request) == 'de'


def test_negotiator_explicit_locale_wins():
    request = _request(session={'preferred_language': 'de'},
                       params={'_LOCALE_': 'fr'})
    assert locale_negotiator(request) == 'fr'


def test_negotiator_ignores_an_invalid_session_language():
    request = _request(accept='it', session={'preferred_language': 'zz'})
    assert locale_negotiator(request) == 'it'


# ---------------- the session is populated at the three entry points -------
@pytest.mark.parametrize("module_path, needle", [
    ('alirpunkto.views.login', "request.session['preferred_language'] = declared_language"),
    ('alirpunkto.views.register', "request.session['preferred_language'] = request.params['lang1']"),
    ('alirpunkto.views.modify_member', "request.session['preferred_language'] = new_language"),
])
def test_entry_points_store_the_language_in_the_session(module_path, needle):
    import importlib
    src = inspect.getsource(importlib.import_module(module_path))
    assert needle in src


# ---------------- the pending e-mail template now exists -------------------
@pytest.mark.parametrize("lang", ['en', 'fr'])
def test_pending_template_exists_and_renders(lang):
    from chameleon import PageTemplateFile
    from alirpunkto.models.member import MemberTypes
    path = os.path.join(ROOT, 'alirpunkto', 'locale', lang, 'LC_MESSAGES',
                        'send_candidature_pending_email.pt')
    cand = SimpleNamespace(pseudonym='jdoe', type=MemberTypes.COOPERATOR,
                           oid='oid-1')
    html = PageTemplateFile(path)(
        domain_name='alirpunkto.org', organization_details='Org',
        candidature=cand, textual=False,
    )
    assert 'jdoe' in html and '${' not in html
