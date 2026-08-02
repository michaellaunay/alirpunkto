"""Unit tests for ``ldap_factory`` (audit finding 2.15).

Two concrete issues are covered: the host/port default arguments were evaluated
once at import time (``server_name=get_ldap_server_name()``), freezing the
configuration; and the SYNC production connection was a module-level singleton
(``_conn``), which is not thread-safe. The defaults are now resolved at call
time and no connection is cached module-side.
"""

from __future__ import annotations

import inspect
import ssl
from unittest.mock import patch

import alirpunkto.ldap_factory as ldap_factory


def test_get_ldap_connection_host_port_defaults_are_resolved_at_call_time():
    params = inspect.signature(ldap_factory.get_ldap_connection).parameters
    assert params["ldap_server"].default is None
    assert params["ldap_port"].default is None


def test_get_ldap_server_host_port_defaults_are_resolved_at_call_time():
    params = inspect.signature(ldap_factory.get_ldap_server).parameters
    assert params["server_name"].default is None
    assert params["port"].default is None


def test_no_module_level_connection_singleton():
    # The thread-unsafe shared SYNC connection has been removed; only the
    # server may be cached.
    assert not hasattr(ldap_factory, "_conn")


def test_reset_ldap_connection_clears_the_cached_servers():
    ldap_factory._servers["sentinel"] = object()  # pretend a server was cached
    ldap_factory.reset_ldap_connection()
    assert ldap_factory._servers == {}


def test_the_server_cache_is_keyed_by_parameters():
    """Sixth audit pass (2026-08-01, §12.2): the cache was one module
    global returned regardless of the parameters — the first call
    imposed its host, port and SSL mode on every later one."""
    ldap_factory.reset_ldap_connection()
    try:
        one = ldap_factory.get_ldap_server(
            server_name="ldap-a.example", port=389)
        other = ldap_factory.get_ldap_server(
            server_name="ldap-b.example", port=389)
        again = ldap_factory.get_ldap_server(
            server_name="ldap-a.example", port=389)
        assert one is not other
        assert one is again
    finally:
        ldap_factory.reset_ldap_connection()


def test_ldaps_servers_validate_the_certificate():
    """Sixth audit pass (§12.1): ``use_ssl`` without a ``Tls`` object
    performs NO certificate validation — ldap3 defaults to CERT_NONE."""
    ldap_factory.reset_ldap_connection()
    try:
        with patch.object(ldap_factory, "PYTEST_CURRENT_TEST", None):
            plain = ldap_factory.get_ldap_server(
                server_name="ldap.example", port=389, use_ssl=False)
            secure = ldap_factory.get_ldap_server(
                server_name="ldap.example", port=636, use_ssl=True)
        assert plain is not secure   # §12.2: distinct cache entries
        assert plain.tls is None
        assert secure.ssl is True
        assert secure.tls is not None
        assert secure.tls.validate == ssl.CERT_REQUIRED
    finally:
        ldap_factory.reset_ldap_connection()
