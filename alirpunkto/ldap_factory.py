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
_conn = None

def get_ldap_server(
        server_name=get_ldap_server_name(),
        get_info=ALL,
        use_ssl=LDAP_USE_SSL,
        port=get_ldap_server_port()
    ) -> Server:
    """Get an LDAP server
    Returns:
        Server: An LDAP server
    """
    global _server
    if _server is not None:
        return _server
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
    """Reset the LDAP connection, forcing a new connection on next call"""
    global _conn, _server
    try:
        if _conn is not None:
            _conn.unbind()
    except:
        pass
    
    _conn = None
    _server = None

def get_ldap_connection(
        ldap_user=LDAP_USER,  # LDAP_USER
        ldap_password=None,   # get_secret(LDAP_PASSWORD)
        ldap_auto_bind=True,
        ldap_use_ssl=LDAP_USE_SSL,
        ldap_get_info=ALL,
        ldap_client_strategy=SYNC,
        ldap_server=get_ldap_server_name(),  # LDAP_SERVER
        ldap_port=get_ldap_server_port()  # LDAP_PORT
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
    global _conn
    # Always create a new connection when using client_strategy other than SYNC
    # or when explicitly specifying a server or port
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

    if ldap_client_strategy != SYNC:
        conn = Connection(
            server,
            user=ldap_user,
            password=ldap_password,
            auto_bind=ldap_auto_bind,
            client_strategy=ldap_client_strategy
        )
        
        if ldap_auto_bind and ldap_client_strategy == MOCK_SYNC:
            conn.bind()  # Force bind for MOCK_SYNC as auto_bind might not work
            
        return conn
    # Otherwise use/create the singleton connection
    if _conn is None:
        # For Docker LDAP container in tests
        try :
            _conn = Connection(
                server,
                user=ldap_user,
                password=ldap_password,
                auto_bind=ldap_auto_bind,
                client_strategy=ldap_client_strategy
            )
            if ldap_auto_bind and ldap_client_strategy == MOCK_SYNC:
                _conn.bind()  # Force bind for MOCK_SYNC as auto_bind might not work
        except Exception as e:
            log.error(f"Error creating LDAP connection: {e}")
            raise
    
    return _conn
