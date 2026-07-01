# Factory to get a LDAP connection
# Allow testing of LDAP connection with both mock and real container
# author: Michaël Launay
# date: 2024-10-17

from .constants_and_globals import (
    LDAP_SERVER,
    LDAP_USE_SSL,
    LDAP_USER,
    LDAP_PORT,
    PYTEST_CURRENT_TEST,
    TEST_WITH_DOCKER_LDAP,
    TEST_WITH_DOCKER_LDAP_SERVER,
    TEST_WITH_DOCKER_LDAP_PORT,
    get_ldap_server_name,
    get_ldap_server_port,
    log
)
import os

from ldap3 import (
    Server,
    Connection,
    ALL,
    SYNC,
    MOCK_SYNC,
    OFFLINE_SLAPD_2_4
)

_server = None

def get_ldap_server(
        server_name=None,
        get_info=ALL,
        use_ssl=LDAP_USE_SSL,
        port=None
    ) -> Server:
    """Get an LDAP server
    Returns:
        Server: An LDAP server
    """
    global _server
    if _server is not None:
        return _server
    # Resolve host/port at call time, not at import time.
    if server_name is None:
        server_name = get_ldap_server_name()
    if port is None:
        port = get_ldap_server_port()
    if PYTEST_CURRENT_TEST and not TEST_WITH_DOCKER_LDAP:
        # Use a mock server for testing /!\ Mock server has some issues with user define schema
        _server = Server(
            server_name,
            get_info=OFFLINE_SLAPD_2_4,
            port=port
        )
    else:           
        # define LDAP server, requesting info on DSE and schema
        _server = Server(
            server_name,
            use_ssl=use_ssl,
            get_info=get_info,
            port=port
        )
    
    return _server

def reset_ldap_connection():
    """Reset the cached LDAP server, forcing a new one on the next call.

    Connections are no longer cached module-side (each call returns a fresh
    connection), so only the cached ``Server`` needs to be dropped.
    """
    global _server
    _server = None

def get_ldap_connection(
        ldap_user=LDAP_USER,  # LDAP_USER
        ldap_password=None,   # get_secret(LDAP_PASSWORD)
        ldap_auto_bind=True,
        ldap_use_ssl=LDAP_USE_SSL,
        ldap_get_info=ALL,
        ldap_client_strategy=SYNC,
        ldap_server=None,  # resolved at call time (LDAP_SERVER)
        ldap_port=None  # resolved at call time (LDAP_PORT)
    ) -> Connection:
    """Get an LDAP connection secure or not depending of LDAP_USE_SSL global.
    Args:
        ldap_user: The LDAP user DN
        ldap_password: The LDAP password
        ldap_auto_bind: Whether to auto bind
        ldap_use_ssl: Whether to use SSL
        ldap_get_info: What info to get from server
        ldap_client_strategy: The client strategy (SYNC, MOCK_SYNC, etc.)
        ldap_server: The LDAP server
        ldap_port: The LDAP port
    Returns:
        Connection: the LDAP connection
    """
    # Resolve host/port at call time, not at import time.
    if ldap_server is None:
        ldap_server = get_ldap_server_name()
    if ldap_port is None:
        ldap_port = get_ldap_server_port()
    server = get_ldap_server(
        server_name=ldap_server,
        use_ssl=ldap_use_ssl if not PYTEST_CURRENT_TEST else False,
        get_info=ldap_get_info,
        port=ldap_port)
    if PYTEST_CURRENT_TEST and not TEST_WITH_DOCKER_LDAP:
        # Use a mock server for testing /!\ Mock server has some issues with user define schema
        conn = Connection(
            server,
            user=ldap_user,
            password=ldap_password,
            auto_bind=ldap_auto_bind,
            client_strategy=MOCK_SYNC
        )
        if ldap_auto_bind:
            conn.bind() # Force the binding of the connection because auto_bind seems not to be working
        return conn

    # Create a fresh connection per call. A single module-level connection is
    # not thread-safe (ldap3 SYNC connections interleave requests/responses
    # across threads) and would be unbound by a caller's `with` block, so it
    # must not be shared.
    try:
        conn = Connection(
            server,
            user=ldap_user,
            password=ldap_password,
            auto_bind=ldap_auto_bind,
            client_strategy=ldap_client_strategy
        )
        if ldap_auto_bind and ldap_client_strategy == MOCK_SYNC:
            conn.bind()  # Force bind for MOCK_SYNC as auto_bind might not work
    except Exception as e:
        log.error(f"Error creating LDAP connection: {e}")
        raise
    return conn


