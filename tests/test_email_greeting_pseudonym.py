"""The e-mail greeting names the addressee (issue #226).

reset_password_email.pt (and modification_to_profile.pt, same pattern in the
33 languages) greeted through a convoluted TAL expression testing
`'pseudonym' in globals()` — Chameleon's globals() never contains template
variables — before falling back to `member.pseudonym`; but send_email_to_member
hands `member.data` (a MemberDatas) to the template, whose pseudonym field is
never populated, so the greeting rendered empty. The senders now provide
`pseudonym` explicitly and the 66 templates use plain fallbacks.
"""
from __future__ import annotations

import glob
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from chameleon import PageTemplateFile

import alirpunkto.utils as utils

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_the_globals_pattern_is_gone():
    hits = [pt for pt in glob.glob('alirpunkto/locale/*/LC_MESSAGES/*.pt')
            if 'in globals()' in open(pt, encoding='utf-8').read()]
    assert hits == []


def _member(pseudonym='jdoe'):
    return SimpleNamespace(
        email='m@example.com', pseudonym=pseudonym, oid='oid-1',
        member_state=None,
        data=SimpleNamespace(pseudonym=None, fullname='Jean', lang1='en'),
        email_send_status_history=[SimpleNamespace(seed='s')],
        add_email_send_status=lambda *a, **k: None,
    )


def _request():
    return SimpleNamespace(
        registry=SimpleNamespace(
            queryUtility=lambda *a, **k: None,
            settings={'domain_name': 'D', 'site_name': 'S',
                      'session.secret': 'x' * 32,
                      'organization_details': 'Org'}),
        route_url=lambda *a, **k: 'http://example/view',
        accept_language=SimpleNamespace(best_match=lambda langs: 'en'),
        localizer=SimpleNamespace(translate=lambda ts: 'subject',
                                  locale_name='en'),
    )


@pytest.mark.parametrize("lang", ['en', 'fr'])
def test_reset_password_email_greets_by_pseudonym(lang):
    """End to end: render the template with the exact variables the real
    sender hands over — the greeting must name the member."""
    captured = {}

    def fake_send_email(req, subject, recipients, template_resolver,
                        template_vars, *a, **k):
        captured['vars'] = dict(template_vars)
        return True

    with patch.object(utils, 'send_email', fake_send_email), \
         patch.object(utils, 'encrypt_oid', lambda *a, **k: 'token'), \
         patch.object(utils, '_translate_for_language',
                      lambda r, l, ts: 'subject'):
        utils.send_email_to_member(
            _request(), _member(), 'test', 'reset_password_email',
            'reset_password_email_subject', 'forgot_password')

    path = os.path.join(ROOT, 'alirpunkto', 'locale', lang, 'LC_MESSAGES',
                        'reset_password_email.pt')
    html = PageTemplateFile(path)(**captured['vars'], textual=False)
    assert 'jdoe' in html
    assert 'Hello ,' not in html and 'Bonjour ,' not in html


def test_modification_to_profile_greets_by_pseudonym():
    path = os.path.join(ROOT, 'alirpunkto', 'locale', 'en', 'LC_MESSAGES',
                        'modification_to_profile.pt')
    html = PageTemplateFile(path)(
        pseudonym='jdoe', member=SimpleNamespace(pseudonym=None),
        site_name='S', domain_name='D', organization_details='Org',
        site_url='http://x/', page_with_oid='http://x/p', textual=False,
        MemberStates=SimpleNamespace(), fields=[],
    )
    assert 'jdoe' in html
