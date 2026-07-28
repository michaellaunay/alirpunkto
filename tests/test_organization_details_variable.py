"""The organisation details come from the variable, not hard-coded text
(issue #241).

The GDPR data-controller mention — name, address, registration date and SIREN
number — was hard-coded in three catalog messages of every language (and
translated, transliterated or reordered by the assisted translations, which is
why a naive replacement missed a third of them). All of them now interpolate
${organization_details}, resolved from the deployment settings by the live
mapping, as proposed on the UI_SiteName branch for the .pot.
"""
from __future__ import annotations

import glob
import re
from types import SimpleNamespace

import pytest
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto.constants_and_globals import _

MSGIDS = ('email_description', 'ordinary_member_data_explanation',
          'cooperator_data_explanation')
LANGS = sorted(p.split('/')[2] for p in glob.glob(
    'alirpunkto/locale/*/LC_MESSAGES/alirpunkto.po'))
DETAILS = "The Organisation, 1 Some Street, 59000 Lille, France"


@pytest.mark.parametrize("lang", LANGS)
def test_no_hardcoded_details_left_in_the_catalog(lang):
    s = open(f'alirpunkto/locale/{lang}/LC_MESSAGES/alirpunkto.po',
             encoding='utf-8').read()
    for mid in MSGIDS:
        m = re.search(rf'^msgid "{mid}"\n(.*?)(?=\n\n)', s, re.S | re.M)
        if m:
            assert '951' not in m.group(1), f"{lang}/{mid}"
            assert 'Solférino' not in m.group(1), f"{lang}/{mid}"
            assert '${organization_details}' in m.group(1), f"{lang}/{mid}"


def test_the_pot_template_matches():
    s = open('alirpunkto/locale/alirpunkto.pot', encoding='utf-8').read()
    assert '951 007 897' not in s


@pytest.fixture
def translate_for():
    config = setUp(settings={'pyramid.default_locale_name': 'en'})
    config.add_translation_dirs('alirpunkto:locale/')

    def _for(lang):
        request = DummyRequest()
        request._LOCALE_ = lang
        alirpunkto.add_localizer(NewRequest(request))
        return request.localizer

    yield _for
    tearDown()


@pytest.mark.parametrize("lang", ['en', 'fr', 'de', 'tr', 'be', 'ga'])
@pytest.mark.parametrize("mid", MSGIDS)
def test_compiled_catalogs_interpolate_the_details(translate_for, lang, mid):
    """Locks the .po/.mo parity for the trickiest languages of the sweep."""
    rendered = translate_for(lang).translate(
        _(mid, {'organization_details': DETAILS, 'domain_name': 'D',
                'site_name': 'S'}))
    assert DETAILS in rendered
    assert '951' not in rendered
    assert '${organization_details}' not in rendered
