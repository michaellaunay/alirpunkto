"""Render every registration / candidature email template, in every locale,
for both member types (ordinary and cooperator), in both variants produced by
``send_email`` (``textual=True`` -> plain-text body, ``textual=False`` -> HTML
body).

These templates carry translated text hard-coded per language, so the Chameleon
compile check only proves they *parse*. This module proves they also *render*:
it exercises the same TAL expressions the mailer evaluates and therefore guards
against render-time breakage the compile check cannot see, e.g.

* leftover ``##PLACEHOLDER`` tokens (``##IS_COOPERATOR`` / ``##PSEUDONYM`` / ...),
* translated Python identifiers such as ``candidature.modifiche``,
* attribute-name / expression mangling, and
* the cooperator-only identity-data block, which must be driven by
  ``candidature.type`` (shown for cooperators, hidden for ordinary members).

Rendering is done through Chameleon directly with the exact variables the mailer
passes (see ``send_email`` / ``send_member_state_change_email`` in
``alirpunkto.utils``); no Pyramid renderer stack is required because these
templates reference only the explicit template variables plus ``textual``.
Single-brace ``{placeholder}`` tokens are intentionally left untouched: the
mailer fills those with ``str.format`` *after* Chameleon rendering.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import Mock

# The alirpunkto package reads a few secrets from the environment at import
# time. Seed harmless defaults so this module can be collected standalone.
try:  # a valid Fernet key is required if SECRET_KEY is unset
    from cryptography.fernet import Fernet

    os.environ.setdefault("SECRET_KEY", Fernet.generate_key().decode())
except Exception:  # pragma: no cover - cryptography is a hard dependency
    os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("LDAP_PASSWORD", "test-ldap-password")
os.environ.setdefault("ADMIN_PASSWORD", "Admin.Password.123")
os.environ.setdefault("MAIL_PASSWORD", "test-mail-password")

import pytest
from chameleon import PageTemplateFile
from ZODB.Connection import Connection

from alirpunkto.models.candidature import Candidature, CandidatureStates
from alirpunkto.models.member import MemberDatas, Members, MemberStates, MemberTypes


LOCALE_DIR = Path(__file__).resolve().parents[1] / "alirpunkto" / "locale"

# Every locale that ships a LC_MESSAGES directory.
LANGS = sorted(
    p.name for p in LOCALE_DIR.iterdir() if (p / "LC_MESSAGES").is_dir()
)

# Email templates involved in the registration / candidature flow. Some ship
# only in a subset of locales (e.g. remind_verifiers, provider_created_email);
# missing ones are skipped per locale rather than failing the test.
REGISTRATION_EMAIL_TEMPLATES = [
    "check_email",
    "check_new_email",
    "candidature_state_change",
    "member_state_change",
    "identity_request_notification",
    "inform_verifiers",
    "remind_verifiers",
    "send_candidature_approuved_email",
    "modification_to_profile",
    "reset_password_email",
]


def _init_members_singleton():
    """Initialise the Members singleton with a mock ZODB connection.

    Mirrors the ``members_mapping`` conftest fixture; Candidature construction
    needs it for unique-oid generation.
    """
    connection = Mock(spec=Connection)
    connection.root.return_value = {}
    Members._instance = None
    Members.get_instance(connection=connection)


def _make_candidature(member_type: MemberTypes) -> Candidature:
    candidature = Candidature()
    candidature.email = "applicant@example.org"
    candidature.pseudonym = "TestUser"
    candidature.type = member_type
    if candidature.data is None:
        candidature.data = MemberDatas()
    candidature.data.lang1 = "French"
    candidature.data.lang2 = "English"
    candidature.data.lang3 = "German"
    candidature.data.fullname = "Ada"
    candidature.data.fullsurname = "Lovelace"
    return candidature


def _template_vars(candidature: Candidature) -> dict:
    """Superset of the variables the various mailer entry points provide.

    ``member`` and ``candidature`` point to the same object here: across the
    templates ``member`` is sometimes the Member and sometimes ``member.data``,
    but a single rich object satisfies every guarded access (``hasattr`` /
    ``exists:``) they perform.
    """
    return dict(
        candidature=candidature,
        member=candidature,
        user=candidature.pseudonym,
        CandidatureStates=CandidatureStates,
        MemberTypes=MemberTypes,
        MemberStates=MemberStates,
        domain_name="example.org",
        site_name="AlirPunkto",
        site_url="http://example.org/home",
        organization_details="Example organization details",
        page_with_oid="http://example.org/page?oid=abc",
        page_register_with_oid="http://example.org/register?oid=abc",
        check_new_email_view="http://example.org/check-new-email?oid=abc",
        new_email="new-address@example.org",
        full_name="Ada Lovelace",
        verifier="VerifierPseudo",
        challenge_A="1 + 1",
        challenge_B="2 + 2",
        challenge_C="3 + 3",
        challenge_D="4 + 4",
    )


def _existing_templates(lang: str):
    for name in REGISTRATION_EMAIL_TEMPLATES:
        path = LOCALE_DIR / lang / "LC_MESSAGES" / f"{name}.pt"
        if path.exists():
            yield name, path


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize(
    "member_type",
    [MemberTypes.ORDINARY, MemberTypes.COOPERATOR],
    ids=["ordinary", "cooperator"],
)
@pytest.mark.parametrize("textual", [True, False], ids=["text", "html"])
def test_registration_email_templates_render(members_mapping, lang, member_type, textual):
    """Each registration email template renders without error in every locale,
    for both member types and both body variants, with no leftover placeholders.
    """
    candidature = _make_candidature(member_type)
    tvars = _template_vars(candidature)

    rendered_any = False
    for name, path in _existing_templates(lang):
        rendered_any = True
        try:
            output = PageTemplateFile(str(path))(textual=textual, **tvars)
        except Exception as exc:  # noqa: BLE001 - surface the offending file
            pytest.fail(
                f"{lang}/{name}.pt failed to render "
                f"(textual={textual}, type={member_type.name}): "
                f"{type(exc).__name__}: {exc}"
            )

        assert "##" not in output, (
            f"{lang}/{name}.pt still contains an unreplaced ## placeholder"
        )
        # Chameleon ${...} interpolations must all be resolved (single-brace
        # {...} str.format placeholders are handled later by the mailer).
        assert "${" not in output, (
            f"{lang}/{name}.pt has an unrendered ${{...}} interpolation"
        )

    assert rendered_any, f"no registration email templates found for locale {lang}"


@pytest.mark.parametrize("lang", LANGS)
def test_cooperator_identity_block_is_conditional(members_mapping, lang):
    """send_candidature_approuved_email must include the identity-data block for
    cooperators and omit it for ordinary members (``##IS_COOPERATOR`` is now
    wired to ``candidature.type``).
    """
    path = LOCALE_DIR / lang / "LC_MESSAGES" / "send_candidature_approuved_email.pt"
    assert path.exists(), f"missing send_candidature_approuved_email.pt for {lang}"
    template = PageTemplateFile(str(path))

    ordinary_out = template(
        textual=False, **_template_vars(_make_candidature(MemberTypes.ORDINARY))
    )
    cooperator_out = template(
        textual=False, **_template_vars(_make_candidature(MemberTypes.COOPERATOR))
    )

    assert cooperator_out != ordinary_out, (
        f"{lang}: identity-data block is not conditional on member type"
    )
    assert len(cooperator_out) > len(ordinary_out), (
        f"{lang}: cooperator email should contain the extra identity-data line"
    )


def test_all_locales_are_covered():
    """Guard against an empty parametrization if the locale layout changes."""
    assert len(LANGS) >= 30, f"expected the full set of locales, found {LANGS}"
    assert "en" in LANGS and "fr" in LANGS
