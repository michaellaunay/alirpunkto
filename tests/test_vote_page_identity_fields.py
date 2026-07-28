"""Only the identity fields show on the voting page (issue #206).

The verifiers compare the declared identity with the ID document: the page
must display fullname, fullsurname, nationality and birthdate — and nothing
else. The candidate sheet used to list the whole record; a first filter
narrowed it to eight fields, still exposing the description and the declared
languages, which are irrelevant to the verification and covered by GDPR data
minimisation.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pyramid.events import NewRequest
from pyramid.renderers import render
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto import add_localizer, add_renderer_globals
from alirpunkto.models import member as member_module
from alirpunkto.models.member import MemberDatas
from alirpunkto.models.candidature import (
    Candidature, CandidatureStates, Voter, VotingChoice)


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"


@pytest.fixture
def page():
    config = setUp(settings={
        'pyramid.default_locale_name': 'en',
        'session.secret': 'x' * 32,
        'site_name': 'Access',
        'domain_name': 'CosmoPolitical Cooperative SCE',
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
    with patch.object(member_module.Members, 'get_instance',
                      return_value={'members': {}, 'candidatures': {}}):
        candidature = Candidature()
    candidature.data = MemberDatas(
        password="secret", fullname='Jean', fullsurname='Doe',
        nationality='FR', birthdate='2000-01-01',
        lang1='eo', lang2='mt', description='UNIQUEDESCRIPTION')
    candidature.candidature_state = CandidatureStates.PENDING
    candidature.voters = [
        Voter(oid='voter-1', email='v1@example.com', pseudonym='v1')]
    html = render('alirpunkto:templates/vote.pt', {
        'logged_in': True, 'site_name': 'Access',
        'domain_name': 'CosmoPolitical Cooperative SCE',
        'organization_details': 'Org', 'user': 'verifier1',
        'candidature': candidature, 'VotingChoice': VotingChoice,
        'vote': '', 'registered_vote': False,
    }, request=request)
    yield html
    tearDown()


def test_the_four_identity_fields_show(page):
    for value in ('Jean', 'Doe', 'FR', '2000-01-01'):
        assert value in page
    for name in ('>fullname<', '>fullsurname<', '>nationality<',
                 '>birthdate<'):
        assert name in page


def test_nothing_else_from_the_record_shows(page):
    assert 'UNIQUEDESCRIPTION' not in page      # description value
    for name in ('>description<', '>lang1<', '>lang2<', '>lang3<'):
        assert name not in page


def test_the_ballot_still_renders(page):
    assert 'name="vote"' in page
