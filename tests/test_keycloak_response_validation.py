"""Sixth audit pass (2026-08-01, §12.6).

A token endpoint answer is untrusted input: ``response.json()`` could
raise on a non-JSON body, required fields could be missing, types were
never checked and expiry values were unbounded. Both Keycloak call
sites now run every payload through ``_validated_token_payload`` and
return ``None`` on anything unusable, without ever logging the body.
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from alirpunkto import utils
from alirpunkto.constants_and_globals import SSO_EXPIRES_AT


class _Response:
    def __init__(self, payload=None, raise_json=False,
                 status_code=200, text=""):
        self._payload = payload
        self._raise = raise_json
        self.status_code = status_code
        self.text = text

    def json(self):
        if self._raise:
            raise ValueError("not json")
        return self._payload


VALID = {
    "access_token": "AT",
    "refresh_token": "RT",
    "expires_in": 300,
    "refresh_expires_in": 1800,
}


def _get(response):
    user = SimpleNamespace(oid="oid-1")
    with patch.object(utils, "PYTEST_CURRENT_TEST", None), \
         patch.object(utils, "KEYCLOAK_SERVER_URL", "https://kc.example"), \
         patch.object(utils, "KEYCLOAK_REALM", "realm"), \
         patch.object(utils.requests, "post", return_value=response):
        return utils.get_keycloak_token(user, "pw")


def _refresh(response):
    with patch.object(utils, "KEYCLOAK_SERVER_URL", "https://kc.example"), \
         patch.object(utils, "KEYCLOAK_REALM", "realm"), \
         patch.object(utils.requests, "post", return_value=response):
        return utils.refresh_keycloak_token("RT")


def test_a_valid_payload_passes_and_gets_its_expiry():
    token = _get(_Response(dict(VALID)))
    assert token is not None
    assert token["access_token"] == "AT"
    assert SSO_EXPIRES_AT in token


@pytest.mark.parametrize("response", [
    _Response(raise_json=True),                        # body is not JSON
    _Response(["not", "an", "object"]),                # JSON, not a dict
    _Response({**VALID, "access_token": None}),        # unusable field
    _Response({key: value for key, value in VALID.items()
               if key != "refresh_token"}),            # missing field
    _Response({**VALID, "expires_in": "300"}),         # wrong type
    _Response({**VALID, "refresh_expires_in": True}),  # bool is not a lifetime
    _Response({**VALID, "expires_in": 10**9}),         # absurd lifetime
    _Response({**VALID, "expires_in": 0}),             # empty lifetime
])
def test_invalid_payloads_are_refused(response):
    assert _get(response) is None


def test_the_refresh_path_is_validated_too():
    assert _refresh(_Response(raise_json=True)) is None
    token = _refresh(_Response(dict(VALID)))
    assert token is not None
    assert token["refresh_token"] == "RT"
