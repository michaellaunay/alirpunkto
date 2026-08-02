"""Sixth audit pass (2026-08-01, §12.5).

The cookie session is signed, not encrypted: the SSO refresh token used
to ride in it in clear. It is now Fernet-encrypted on write
(``store_sso_tokens``) and only decrypted by ``load_sso_refresh_token``,
which treats anything undecryptable — a tampered value, or a clear-text
token from a pre-change session — as an expired SSO session.
"""
from types import SimpleNamespace

from alirpunkto import utils
from alirpunkto.constants_and_globals import SSO_EXPIRES_AT, SSO_REFRESH


def _request():
    return SimpleNamespace(session={})


def test_store_sso_tokens_encrypts_the_refresh_token_at_rest():
    request = _request()
    utils.store_sso_tokens(
        request, {"refresh_token": "RT", "refresh_expires_in": 300})
    stored = request.session[SSO_REFRESH]
    assert stored != "RT"
    assert "RT" not in stored
    assert utils.load_sso_refresh_token(request) == "RT"
    assert SSO_EXPIRES_AT in request.session


def test_load_rejects_a_clear_text_or_tampered_value():
    request = _request()
    # A session written before this change holds the clear token.
    request.session[SSO_REFRESH] = "RT"
    assert utils.load_sso_refresh_token(request) is None
    # A tampered ciphertext must not decrypt either.
    sealed = utils.seal_sso_refresh_token("RT")
    request.session[SSO_REFRESH] = sealed[:-4] + "AAAA"
    assert utils.load_sso_refresh_token(request) is None
    # A well-encrypted value that does not inflate is refused too.
    request.session[SSO_REFRESH] = \
        utils._sso_refresh_fernet().encrypt(b"not-deflated").decode()
    assert utils.load_sso_refresh_token(request) is None


def test_load_returns_none_when_the_session_has_no_token():
    assert utils.load_sso_refresh_token(_request()) is None
