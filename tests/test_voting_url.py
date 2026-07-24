"""Regression tests for the vote URL used in e-mails (issue #237).

The verifier reminders are sent from a NewRequest subscriber, so a URL derived
from the incoming request inherits the host of whatever request triggered the
scan — behind the reverse proxy that is localhost:6543. The URL must instead be
built from the configured domain.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from alirpunkto.constants_and_globals import DOMAIN_NAME, URL_SCHEME
from alirpunkto.views.register import _get_voting_url


class _Request:
    """Minimal request whose route_url would return the proxied host."""

    def __init__(self, settings):
        self.registry = SimpleNamespace(settings=settings)

    def route_path(self, name, _query=None):
        oid = (_query or {}).get('oid')
        return f"/{name}?oid={oid}"

    def route_url(self, name, _query=None):  # must NOT be used any more
        oid = (_query or {}).get('oid')
        return f"http://localhost:6543/{name}?oid={oid}"


@pytest.fixture
def candidature():
    return SimpleNamespace(oid="cand-oid-1")


def test_voting_url_uses_the_configured_domain(candidature):
    request = _Request({'domain_name': 'alirpunkto.org', 'url_scheme': 'https'})

    url = _get_voting_url(request, candidature)

    assert url == "https://alirpunkto.org/vote?oid=cand-oid-1"
    assert "localhost:6543" not in url


def test_voting_url_ignores_the_request_host(candidature):
    """The bug: the link pointed at the host Pyramid was reached on."""
    request = _Request({'domain_name': 'alirpunkto.org'})

    url = _get_voting_url(request, candidature)

    assert url.startswith(f"{URL_SCHEME}://alirpunkto.org/")
    assert "localhost" not in url


def test_voting_url_falls_back_to_the_domain_constant(candidature):
    request = _Request({})

    url = _get_voting_url(request, candidature)

    assert url == f"{URL_SCHEME}://{DOMAIN_NAME}/vote?oid=cand-oid-1"


def test_voting_url_tolerates_a_trailing_slash_in_the_domain(candidature):
    request = _Request({'domain_name': 'alirpunkto.org/', 'url_scheme': 'https://'})

    url = _get_voting_url(request, candidature)

    assert url == "https://alirpunkto.org/vote?oid=cand-oid-1"
