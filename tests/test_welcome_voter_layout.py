"""Regression tests for the verifier voting-page welcome text (issue #207).

welcome_voter is a long, multi-paragraph instruction whose \\n line feeds are
ignored by HTML, so the whole text rendered on a single line. Following PR #229,
the seven translated catalogs carry structured HTML (<p>, <ol>/<li>) and the
template renders the message as structure through _() — which also interpolates
${name} and, via SITE_INFORMATION_MAPPING, ${site_name} (previously left as a
literal because the i18n:translate block only provided the name).

The catalogs are compiled: these tests go through the localizer, which reads the
.mo files, so they also lock the .po/.mo parity this repository depends on.
"""
from __future__ import annotations

import os

import pytest
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOTE_PT = os.path.join(ROOT, "alirpunkto", "templates", "vote.pt")
HTML_LANGS = ("de", "en", "es", "fr", "it", "nl", "pl")


@pytest.fixture
def make_translate():
    config = setUp(settings={'pyramid.default_locale_name': 'en'})
    config.add_translation_dirs('alirpunkto:locale/')

    def _for(lang):
        request = DummyRequest()
        request._LOCALE_ = lang
        alirpunkto.add_localizer(NewRequest(request))
        return request.registry.translate

    yield _for
    tearDown()


@pytest.mark.parametrize("lang", HTML_LANGS)
def test_welcome_voter_is_structured_html(make_translate, lang):
    """The compiled catalog (.mo) must carry the HTML layout of PR #229."""
    rendered = make_translate(lang)('welcome_voter',
                                    {'name': 'Jean Candidate'})
    assert "<ol>" in rendered and "<li>" in rendered and "<p>" in rendered


def test_welcome_voter_interpolates_name_and_site_name(make_translate):
    rendered = make_translate('en')('welcome_voter', {'name': 'Jean Candidate'})
    assert "Jean Candidate" in rendered
    assert "${name}" not in rendered
    # site_name comes from SITE_INFORMATION_MAPPING (fix #223), not the caller.
    assert "${site_name}" not in rendered


def test_vote_template_renders_welcome_voter_as_structure():
    content = open(VOTE_PT, encoding="utf-8").read()
    assert "structure _('welcome_voter'" in content
    # The old escaped i18n:translate rendering must be gone.
    assert 'i18n:translate="welcome_voter"' not in content
    # The greeting must still be limited to the not-yet-voted case.
    idx = content.index("structure _('welcome_voter'")
    block = content[max(0, idx - 300):idx]
    assert 'tal:condition="not registered_vote"' in block
