"""Regression tests for the verifier e-mail subject language (issue #238).

The body of the verifier e-mails is localised by picking a per-language template
(_get_voter_language). The subject, however, was translated with the request
localizer, i.e. in the Candidate's language, not the Verifier's. _translate_for_
language must translate the subject into the Verifier's own language.
"""
from __future__ import annotations

import pytest
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto.constants_and_globals import _
from alirpunkto.views.register import _translate_for_language


@pytest.fixture
def request_en():
    # The triggering request is negotiated in English (the Candidate's language).
    config = setUp(settings={'pyramid.default_locale_name': 'en'})
    config.add_translation_dirs('alirpunkto:locale/')
    request = DummyRequest()
    alirpunkto.add_localizer(NewRequest(request))
    yield request
    tearDown()


def _subject(request, language):
    ts = _("inform_verifier_subject", {'domain_name': 'alirpunkto.org'})
    return _translate_for_language(request, language, ts)


def test_subject_is_translated_in_the_verifier_language(request_en):
    """A French verifier gets a French subject even on an English request."""
    english = _subject(request_en, 'en')
    french = _subject(request_en, 'fr')
    german = _subject(request_en, 'de')

    assert english.startswith("Please help us")
    assert french.startswith("Aide-nous")
    assert german.startswith("Bitte hilf uns")
    assert french != english
    # The placeholder is still interpolated.
    assert 'alirpunkto.org' in french
    assert '${domain_name}' not in french


def test_subject_falls_back_to_request_language_when_unknown(request_en):
    """An unknown/None language must not crash; fall back to the request."""
    fallback = _subject(request_en, None)
    unknown = _subject(request_en, 'zz')

    assert fallback.startswith("Please help us")  # request is English
    assert unknown == fallback
