"""Unit tests for ``ldap_factory`` (audit finding 2.15).

Two concrete issues are covered: the host/port default arguments were evaluated
once at import time (``server_name=get_ldap_server_name()``), freezing the
configuration; and the SYNC production connection was a module-level singleton
(``_conn``), which is not thread-safe. The defaults are now resolved at call
time and no connection is cached module-side.
"""

from __future__ import annotations

import inspect

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


def test_reset_ldap_connection_clears_the_cached_server():
    ldap_factory._server = object()  # pretend a server was cached
    ldap_factory.reset_ldap_connection()
    assert ldap_factory._server is None
