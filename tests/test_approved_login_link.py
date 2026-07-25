"""Regression test for the final login link (issue #194).

On the "congratulations" (APPROVED) section of the registration page, the login
button pointed at the deprecated /login form through empty i18n variables
(login_page_url / login_button_label, both untranslated). It must point at the
SSO login route (/sso_login) instead.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER_PT = os.path.join(ROOT, "alirpunkto", "templates", "register.pt")


def _approved_section():
    html = open(REGISTER_PT, encoding="utf-8").read()
    # Isolate the APPROVED status block.
    start = html.index("APPROVED Status Section")
    end = html.index("</div>", html.index("login", start))
    return html[start:end]


def test_login_button_targets_the_sso_route():
    section = _approved_section()
    assert "route_url('sso_login')" in section


def test_login_button_no_longer_uses_the_empty_i18n_url():
    section = _approved_section()
    # The old mechanism overrode href with an untranslated variable.
    assert "login_page_url" not in section
    assert 'href="sso_login"' not in section  # relative, broken href


def test_login_button_has_a_translatable_label():
    section = _approved_section()
    # Uses a message id that actually has a translation.
    assert 'i18n:translate="login_label"' in section
