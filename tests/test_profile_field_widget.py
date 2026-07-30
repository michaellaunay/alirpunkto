"""The profile field is a proper multi-line textarea (issue #165).

A single-line TextInputWidget carried the 5000-character profile text: no
overview, painful editing. The field is now a 10-row textarea — natively
resizable, nothing in the project CSS disables it — with the 5000-character
limit kept in the browser through the maxlength attribute and, at last,
enforced server-side by a colander Length validator.
"""
from __future__ import annotations

import re

import colander
import deform
import pytest
from deform.widget import TextAreaWidget
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto.schemas.register_form import RegisterForm


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"


@pytest.fixture
def schema():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_translation_dirs('alirpunkto:locale/')
    request = DummyRequest()
    request.session = _Session()
    alirpunkto.add_localizer(NewRequest(request))
    yield RegisterForm().bind(request=request)
    tearDown()


def test_the_profile_field_is_a_ten_row_textarea(schema):
    widget = schema.get('description').widget
    assert isinstance(widget, TextAreaWidget)
    assert widget.rows == 10


def test_the_rendered_field_is_a_resizable_textarea(schema):
    html = deform.Form(
        schema, renderer=deform.template.default_renderer).render()
    m = re.search(r'<textarea[^>]*name="description"[^>]*>', html)
    assert m, "description textarea not rendered"
    assert re.search(r'rows="10"', m.group(0))
    assert re.search(r'maxlength="5000"', m.group(0))


def test_the_limit_is_enforced_server_side(schema):
    node = schema.get('description')
    with pytest.raises(colander.Invalid):
        node.deserialize('x' * 5001)
    assert node.deserialize('x' * 5000) == 'x' * 5000
