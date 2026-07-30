"""Mandatory fields are marked with an asterisk (issue #107).

The registration form gave no clue about which fields were mandatory. The
deform template already tags required labels with the "required" class; the
CSS now draws the asterisk, a legend explains it, and the password fields —
optional in the shared schema because an empty password means "unchanged" on
profile modification — are required by default through a deferred missing,
so the Ordinary Member list of the ticket (pseudonym, password, confirm,
first language) is fully asterisked and server-enforced.
"""
from __future__ import annotations

import os
import re

import deform
from alirpunkto.constants_and_globals import _
import pytest
from pkg_resources import resource_filename
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto.schemas.register_form import RegisterForm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"


@pytest.fixture
def bind():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_translation_dirs('alirpunkto:locale/')

    def _bind(**kw):
        request = DummyRequest()
        request.session = _Session()
        alirpunkto.add_localizer(NewRequest(request))
        return RegisterForm().bind(request=request, **kw)

    yield _bind
    tearDown()


def test_the_password_fields_are_required_on_registration(bind):
    schema = bind()
    for field in ('pseudonym', 'password', 'password_confirm', 'lang1'):
        assert schema.get(field).required, field


def test_the_password_fields_stay_optional_on_profile_modification(bind):
    schema = bind(password_optional=True)
    assert not schema.get('password').required
    assert not schema.get('password_confirm').required


def test_the_required_labels_carry_the_class_in_the_project_renderer(bind):
    """Rendered with the project's own deform templates — the ones that put
    the 'required' class on the label the CSS turns into an asterisk."""
    renderer = deform.ZPTRendererFactory([
        resource_filename('alirpunkto', 'templates/deform/'),
        resource_filename('deform', 'templates/'),
    ])
    html = deform.Form(bind(), renderer=renderer).render()
    item = re.search(r'<div[^>]*class="[^"]*item-password[^"]*".*?</label>',
                     html, re.S)
    assert item and 'required' in item.group(0)
    opt = re.search(r'<div[^>]*class="[^"]*item-description[^"]*".*?</label>',
                    html, re.S)
    assert opt and 'required' not in opt.group(0)


def test_the_css_draws_the_asterisk():
    css = open(os.path.join(ROOT, 'alirpunkto', 'static', 'theme.css'),
               encoding='utf-8').read()
    assert 'label.required::after' in css
    assert '" *"' in css


def test_the_legend_is_present_and_translated(bind):
    tpl = open(os.path.join(ROOT, 'alirpunkto', 'templates', 'register.pt'),
               encoding='utf-8').read()
    assert 'mandatory-legend' in tpl
    request = DummyRequest()
    request._LOCALE_ = 'fr'
    alirpunkto.add_localizer(NewRequest(request))
    rendered = request.registry.translate(_('mandatory_fields_legend'))
    assert rendered == "Un astérisque (*) signale un champ obligatoire."
