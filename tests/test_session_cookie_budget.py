"""The session cookie stays small enough to be stored (field 2026-07-08).

``SignedCookieSessionFactory`` refuses cookies above 4093 bytes ("ValueError:
Cookie value is too long to store"). The SSO login used to put BOTH Keycloak
JWTs plus three static strings in the session; for a member of several groups
the access token's claims pushed the cookie to ~4.8 KB and every login became
a 500. These tests lock the diet: ``store_sso_tokens`` keeps only the refresh
token and its expiry (the access token is never read back by the application),
and a fully populated post-login session serialises well under the limit even
with realistically large tokens.

Sixth audit pass (2026-08-01, §12.5): the refresh token is now sealed
(deflated then Fernet-encrypted) before entering the session, so the
worst-case model below must be INCOMPRESSIBLE like a real JWT — a run
of identical characters would deflate to nothing and fake-pass.
"""
from __future__ import annotations

import base64
import hashlib
import pickle
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import alirpunkto.utils as utils
from alirpunkto import secret_manager as sm
from alirpunkto.constants_and_globals import (
    ADMIN_PASSWORD,
    LDAP_PASSWORD,
    MAIL_PASSWORD,
    SECRET_KEY,
    SSO_EXPIRES_AT,
    SSO_REFRESH,
    SSO_TOKEN,
)
from alirpunkto.models.users import User

# realistic worst-case JWT sizes for a member of several groups
FAKE_ACCESS_TOKEN = "a" * 2600


def _incompressible_token(length: int) -> str:
    """Deterministic base64 text with real-JWT entropy (~6 bits/char)."""
    chunks, seed = [], b"alirpunkto-cookie-budget"
    while sum(len(c) for c in chunks) * 4 // 3 < length + 4:
        seed = hashlib.sha256(seed + bytes([len(chunks) % 256])).digest()
        chunks.append(seed)
    return base64.urlsafe_b64encode(b"".join(chunks)).decode()[:length]


FAKE_REFRESH_TOKEN = _incompressible_token(2000)
COOKIE_LIMIT = 4093
SIGNATURE_MARGIN = 100          # HMAC + serializer framing overhead


@pytest.fixture(autouse=True)
def _secrets_env(monkeypatch):
    # get_secret pops SECRET_KEY from the environment on first use, so the
    # suite-wide value survives only inside its cache. Preserve that cache
    # and put it back, or any test running after this module would find
    # neither cache nor environment (order-dependent ValueError surfaced
    # by the sixth-audit train, whose new tests initialise it earlier).
    saved = getattr(sm.get_secret, "secrets", None)
    for name, value in (
        # A valid Fernet key (32 url-safe base64 bytes): the refresh
        # token is now encrypted with Fernet(SECRET_KEY) on storage.
        (SECRET_KEY, "dGVzdF9zZXNzaW9uX2J1ZGdldF9fX19fX19fX19fX18="),
        (LDAP_PASSWORD, "test-ldap-pw"),
        (ADMIN_PASSWORD, "test-admin-pw"),
        (MAIL_PASSWORD, "test-mail-pw"),
    ):
        monkeypatch.setenv(name, value)
    if saved is not None:
        delattr(sm.get_secret, "secrets")
    yield
    if hasattr(sm.get_secret, "secrets"):
        delattr(sm.get_secret, "secrets")
    if saved is not None:
        sm.get_secret.secrets = saved


def _sso_token():
    return {
        "access_token": FAKE_ACCESS_TOKEN,
        "refresh_token": FAKE_REFRESH_TOKEN,
        "expires_in": 300,
        "refresh_expires_in": 1800,
    }


def test_store_sso_tokens_keeps_the_access_token_out():
    request = SimpleNamespace(session={})
    before = datetime.now()
    utils.store_sso_tokens(request, _sso_token())
    # §12.5: sealed at rest — never the clear token — and readable back.
    assert request.session[SSO_REFRESH] != FAKE_REFRESH_TOKEN
    assert utils.load_sso_refresh_token(request) == FAKE_REFRESH_TOKEN
    assert SSO_TOKEN not in request.session
    expires_at = datetime.fromisoformat(request.session[SSO_EXPIRES_AT])
    assert timedelta(minutes=29) < (expires_at - before) < timedelta(minutes=31)


def test_full_login_session_fits_the_cookie_limit():
    """Everything the login/SSO views store, with worst-case token sizes."""
    request = SimpleNamespace(session={})
    request.session["logged_in"] = True
    request.session["user"] = User(
        "Scilovema", "member@example.org",
        "2dc94f27-a8b8-4aec-8560-c8006e2b72a3", True, "COOPERATOR").to_json()
    request.session["created_at"] = datetime.now().isoformat()
    utils.store_sso_tokens(request, _sso_token())

    serialised = base64.b64encode(pickle.dumps(dict(request.session)))
    assert len(serialised) + SIGNATURE_MARGIN < COOKIE_LIMIT
    # comfortable headroom, not a photo finish
    assert len(serialised) + SIGNATURE_MARGIN < 3600


def test_views_never_store_the_access_token_again():
    for view in ("alirpunkto/views/login.py",
                 "alirpunkto/views/sso_login.py",
                 "alirpunkto/views/home.py"):
        source = open(view, encoding="utf-8").read()
        assert "request.session[SSO_TOKEN]" not in source, view
        assert "store_sso_tokens(request, sso_token)" in source, view
