"""Regression tests for the vote URL used in e-mails (issues #237, #242).

The verifier reminders are sent from a NewRequest subscriber, so a URL derived
from the incoming request inherits the host of whatever request triggered the
scan — behind the reverse proxy that is localhost:6543. And the domain_name
setting is the display name of the platform in the texts (e.g. "CosmoPolitical
Cooperative SCE"), not a host: concatenating it produced an invalid link. The
URL is therefore built on get_site_url: the site_url setting, falling back to
the URL_SCHEME/DOMAIN_NAME environment constants.
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

    def route_url(self, name, _query=None):  # must NOT be used
        oid = (_query or {}).get('oid')
        return f"http://localhost:6543/{name}?oid={oid}"


@pytest.fixture
def candidature():
    return SimpleNamespace(oid="cand-oid-1")


def test_voting_url_uses_the_configured_site_url(candidature):
    request = _Request({'site_url': 'https://access.cosmopolitical.coop',
                        'domain_name': 'CosmoPolitical Cooperative SCE'})

    url = _get_voting_url(request, candidature)

    assert url == "https://access.cosmopolitical.coop/vote?oid=cand-oid-1"
    assert "localhost:6543" not in url


def test_voting_url_never_uses_the_display_domain_name(candidature):
    """Issue #242: domain_name is a display name, not a host."""
    request = _Request({'site_url': 'https://access.cosmopolitical.coop',
                        'domain_name': 'CosmoPolitical Cooperative SCE'})

    url = _get_voting_url(request, candidature)

    assert "CosmoPolitical" not in url
    assert " " not in url


def test_voting_url_falls_back_to_the_environment_constants(candidature):
    """Without site_url the environment FQDN applies — still never the
    display domain_name setting."""
    request = _Request({'domain_name': 'CosmoPolitical Cooperative SCE'})

    url = _get_voting_url(request, candidature)

    assert url == f"{URL_SCHEME}://{DOMAIN_NAME}/vote?oid=cand-oid-1"


def test_voting_url_tolerates_a_trailing_slash(candidature):
    request = _Request({'site_url': 'https://access.cosmopolitical.coop/'})

    url = _get_voting_url(request, candidature)

    assert url == "https://access.cosmopolitical.coop/vote?oid=cand-oid-1"
