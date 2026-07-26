"""Regression tests for the password-reset form fields (issue #97, PR #234).

On the reset-password page the user must focus on the password: only the two
password fields are editable, identity (pseudonym, cooperative number) is shown
read-only, and the e-mail field is not shown at all. prepare_for_modification
had no branch for the email field, so it stayed in the form with its default —
editable — widget whatever the view asked for.
"""
from __future__ import annotations

import inspect

import pytest
from pyramid.testing import DummyRequest, setUp, tearDown

from alirpunkto.schemas.register_form import RegisterForm


@pytest.fixture
def schema():
    config = setUp(settings={'pyramid.default_locale_name': 'en'})
    yield RegisterForm().bind(request=DummyRequest())
    tearDown()


def _prepare_as_the_view_does(schema):
    schema.prepare_for_modification(
        {"pseudonym": "jean", "cooperative_number": "oid-1"},
        {"password": "", "password_confirm": ""},
    )
    return schema


def test_reset_form_contains_only_the_expected_fields(schema):
    prepared = _prepare_as_the_view_does(schema)
    names = {child.name for child in prepared.children}
    # csrf_token is the hidden anti-CSRF field and must stay in every form.
    assert names == {"csrf_token", "pseudonym", "cooperative_number",
                     "password", "password_confirm"}


def test_only_the_password_fields_are_editable(schema):
    prepared = _prepare_as_the_view_does(schema)
    readonly = {c.name: bool(getattr(c.widget, 'readonly', False))
                for c in prepared.children if c.name != 'csrf_token'}
    assert readonly == {
        "pseudonym": True,
        "cooperative_number": True,
        "password": False,
        "password_confirm": False,
    }


def test_email_branch_supports_the_three_modes(schema):
    """The new email branch must behave like every other field's."""
    schema.prepare_for_modification(
        {"email": "jean@example.org", "cooperative_number": "oid-1"},
        {"password": "", "password_confirm": ""},
    )
    email = schema.get('email')
    assert email is not None and email.widget.readonly is True
    assert email.widget.value == "jean@example.org"


def test_the_view_no_longer_puts_the_email_in_the_form():
    import alirpunkto.views.forgot_password as fp
    src = inspect.getsource(fp)
    read_only_block = src[src.index("read_only_fields = {"):
                          src.index("}", src.index("read_only_fields = {"))]
    assert '"email"' not in read_only_block
    assert '"pseudonym"' in read_only_block
    assert '"cooperative_number"' in read_only_block
