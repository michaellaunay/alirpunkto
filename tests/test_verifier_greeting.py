"""Regression tests for the verifier greeting (issue #217, from PR #228).

The inform/remind verifier e-mails started with "Dear ," — the greeting span
displayed the `verifier` variable but its tal:condition tested `exists:user`, a
variable the sender never provides (template_vars only carries domain_name,
organization_details and verifier). The span was therefore always dropped. The
condition must test the variable the span actually renders.
"""
from __future__ import annotations

import glob
import os

import pytest
from chameleon import PageTemplateFile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALE = os.path.join(ROOT, "alirpunkto", "locale")

GREETING_TEMPLATES = sorted(
    glob.glob(os.path.join(LOCALE, "*", "LC_MESSAGES", "inform_verifiers.pt"))
    + glob.glob(os.path.join(LOCALE, "*", "LC_MESSAGES", "remind_verifiers.pt"))
)


def test_the_greeting_templates_are_found():
    # 33 languages x inform + the languages that ship a remind template.
    assert len(GREETING_TEMPLATES) >= 40


@pytest.mark.parametrize(
    "path", GREETING_TEMPLATES,
    ids=[p[len(LOCALE) + 1:].replace(os.sep, "/") for p in GREETING_TEMPLATES],
)
def test_greeting_condition_tests_the_rendered_variable(path):
    content = open(path, encoding="utf-8", errors="replace").read()
    assert 'tal:replace="verifier" tal:condition="exists:user"' not in content
    assert 'tal:replace="verifier" tal:condition="exists:verifier"' in content


@pytest.mark.parametrize("name", ["inform_verifiers.pt", "remind_verifiers.pt"])
def test_greeting_renders_the_verifier_pseudonym(name):
    """Render the real template as the sender does: the pseudonym must appear."""
    path = os.path.join(LOCALE, "en", "LC_MESSAGES", name)
    # send_email renders e-mail templates with `textual` in scope (True for
    # the text part, False for HTML); provide it as the real sender does.
    html = PageTemplateFile(path)(
        domain_name="alirpunkto.org",
        organization_details="Org details",
        verifier="JeanTest",
        textual=False,
    )
    assert "Dear JeanTest," in html.replace("\r", "")
    assert "Dear ," not in html.replace("\r", "")
