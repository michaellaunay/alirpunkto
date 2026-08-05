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
    # The plaintext witness must be IMPROBABLE inside random base64:
    # the original 2-char witness ("RT") appeared by chance in ~2.7%
    # of ciphertexts (8/300 measured) and finally tripped the CI on
    # 2026-08-04 (Python 3.12 job, matrix twin green — pure dice).
    # 32 distinctive characters cannot occur fortuitously.
    token = "refresh-token-plaintext-sentinel"
    request = _request()
    utils.store_sso_tokens(
        request, {"refresh_token": token, "refresh_expires_in": 300})
    stored = request.session[SSO_REFRESH]
    assert stored != token
    assert token not in stored
    assert utils.load_sso_refresh_token(request) == token
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
