"""The organisation name on the voting page (issues #245, #246).

vote_msg and welcome_voter carried ${site_name} — the short name of the site —
while the page is about the organisation running the platform, and the two
messages even showed different values ("AlirPunkto" from the environment
constant handed by the view, "Access" from the settings through the live
mapping). Both messages now use ${domain_name}, and the view reads the site
variables from the deployment settings, so a single configured value shows
everywhere.
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pyramid.events import NewRequest
from pyramid.renderers import render
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto import add_localizer, add_renderer_globals
from alirpunkto.constants_and_globals import _
from alirpunkto.models import member as member_module
from alirpunkto.models.member import MemberDatas
from alirpunkto.models.candidature import (
    Candidature, CandidatureStates, Voter, VotingChoice)

ORGANISATION = "CosmoPolitical Cooperative SCE"
SITE = "Access"
LANGS_VOTE_MSG = (
    'be bg bs cs da de el en eo es et fi fr ga hr hu is it lt lv mt nl no '
    'pl pt ro sk sl sq sr sv tr uk').split()
LANGS_WELCOME = ('de', 'en', 'es', 'fr', 'it', 'nl', 'pl')


@pytest.fixture
def localizer_for():
    config = setUp(settings={'pyramid.default_locale_name': 'en'})
    config.add_translation_dirs('alirpunkto:locale/')

    def _for(lang):
        request = DummyRequest()
        request._LOCALE_ = lang
        alirpunkto.add_localizer(NewRequest(request))
        return request.localizer

    yield _for
    tearDown()


@pytest.mark.parametrize("lang", LANGS_VOTE_MSG)
def test_vote_msg_uses_the_organisation_name(localizer_for, lang):
    rendered = localizer_for(lang).translate(
        _('vote_msg', {'domain_name': ORGANISATION}))
    assert ORGANISATION in rendered
    assert '${site_name}' not in rendered and '${domain_name}' not in rendered


@pytest.mark.parametrize("lang", LANGS_WELCOME)
def test_welcome_voter_uses_the_organisation_name(localizer_for, lang):
    rendered = localizer_for(lang).translate(
        _('welcome_voter', {'domain_name': ORGANISATION, 'name': 'Jean'}))
    assert ORGANISATION in rendered
    assert '${site_name}' not in rendered


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"


def test_the_page_shows_one_consistent_value():
    """Issue #246: a single configured organisation name, everywhere."""
    config = setUp(settings={
        'pyramid.default_locale_name': 'en',
        'session.secret': 'x' * 32,
        'site_name': SITE,
        'domain_name': ORGANISATION,
        'site_logo': 'static/alirpunkto.png',
        'site_logo_small': 'static/alirpunkto-16x16.png',
    })
    config.include('pyramid_chameleon')
    config.add_translation_dirs('alirpunkto:locale/')
    config.add_subscriber(add_renderer_globals, 'pyramid.events.BeforeRender')
    config.add_route('vote', '/vote')
    config.add_static_view('static', 'alirpunkto:static')
    request = DummyRequest()
    request.session = _Session()
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    add_localizer(NewRequest(request))
    try:
        with patch.object(member_module.Members, 'get_instance',
                          return_value={'members': {}, 'candidatures': {}}):
            candidature = Candidature()
        candidature.data = MemberDatas(
            password="secret", fullname='Jean', fullsurname='Doe',
            nationality='FR', birthdate='2000-01-01',
            lang1='fr', lang2='en', description='desc')
        candidature.candidature_state = CandidatureStates.PENDING
        candidature.voters = [
            Voter(oid='voter-1', email='v1@example.com', pseudonym='v1')]
        html = render('alirpunkto:templates/vote.pt', {
            'logged_in': True,
            'site_name': SITE,
            'domain_name': ORGANISATION,
            'organization_details': 'Org details',
            'user': 'verifier1',
            'candidature': candidature,
            'VotingChoice': VotingChoice,
            'vote': '',
            'registered_vote': False,
        }, request=request)
    finally:
        tearDown()
    assert html.count(ORGANISATION) >= 2   # vote_msg header + welcome text
    assert SITE not in html                # the site short name is gone


def test_vote_view_reads_the_settings(members_mapping):
    """Issue #246: the view must hand the configured values, not the
    environment constants."""
    from tests.test_vote import _in_memory_candidature, _request, _wire
    from alirpunkto.views.vote import vote_view

    candidature = _in_memory_candidature(["voter-1"])
    request = _request(candidature.oid,
                       registry_settings={'site_name': SITE,
                                          'domain_name': ORGANISATION})
    with _wire(candidature, candidature.oid):
        result = vote_view(request)

    assert result['domain_name'] == ORGANISATION
    assert result['site_name'] == SITE
