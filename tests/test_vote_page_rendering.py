"""Real rendering of the voting page (issue #243).

The voting page returned a 500: a template comment added with the #207 fix
contained a literal ${name}, and Chameleon evaluates dollar-brace expressions
even inside HTML comments, raising NameError for every verifier opening the
page. Template compilation (cook_check) does not evaluate expressions, so only
a real render through the Pyramid renderer chain — layout macro included —
catches this class of regression. These tests render the page for the three
paths of vote_view: first display, already voted, and error.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pyramid.events import NewRequest
from pyramid.renderers import render
from pyramid.testing import DummyRequest, setUp, tearDown

from alirpunkto import add_localizer, add_renderer_globals
from alirpunkto.models import member as member_module
from alirpunkto.models.member import MemberDatas
from alirpunkto.models.candidature import (
    Candidature,
    CandidatureStates,
    Voter,
    VotingChoice,
)


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"


@pytest.fixture
def request_():
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
    yield request
    tearDown()


def _candidature():
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
    return candidature


def _vars(**extra):
    base = {
        'logged_in': True,
        'site_name': 'Access',
        'domain_name': 'CosmoPolitical Cooperative SCE',
        'organization_details': 'Org details',
        'user': 'verifier1',
        'candidature': _candidature(),
        'VotingChoice': VotingChoice,
        'vote': '',
        'registered_vote': False,
    }
    base.update(extra)
    return base


def test_vote_page_renders_on_first_display(request_):
    """Issue #243: this render raised NameError('name') from a comment."""
    html = render('alirpunkto:templates/vote.pt', _vars(), request=request_)
    assert 'Jean' in html            # the welcome text names the candidate
    assert '<ol>' in html            # the #207 layout survived
    assert 'name="vote"' in html     # the ballot form is there


def test_vote_page_renders_after_voting(request_):
    html = render('alirpunkto:templates/vote.pt',
                  _vars(registered_vote=True, vote='YES'),
                  request=request_)
    # The candidate sheet stays (the verifier sees whom they evaluated), but
    # the welcome text and its ordered list are replaced by the confirmation.
    # The ballot form itself is still displayed by the current template —
    # pre-existing behaviour, out of the scope of #243.
    assert '<ol>' not in html
    assert 'csrf-token' in html


def test_vote_page_renders_the_error_path(request_):
    variables = {
        'error': 'Invalid application identifier',
        'site_name': 'Access',
        'domain_name': 'CosmoPolitical Cooperative SCE',
        'organization_details': 'Org details',
    }
    html = render('alirpunkto:templates/vote.pt', variables, request=request_)
    assert 'Invalid application identifier' in html
