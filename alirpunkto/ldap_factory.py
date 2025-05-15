# Factory to get a LDAP connection
# Allow testing of LDAP connection with both mock and real container
# author: Michaël Launay
# date: 2024-10-17

from .constants_and_globals import (
    LDAP_SERVER,
    LDAP_USE_SSL,
    LDAP_USER,
    PYTEST_CURRENT_TEST,
    USE_DOCKER_LDAP,
    DOCKER_LDAP_PORT
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
        server=LDAP_SERVER,
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
    
    if PYTEST_CURRENT_TEST:
        if USE_DOCKER_LDAP:
            # Use real Docker LDAP container for testing
            _server = Server(
                'localhost',
                port=DOCKER_LDAP_PORT,
                get_info=get_info,
                use_ssl=False  # Docker container typically doesn't use SSL
            )
        else:
            # Use a mock server for testing
            _server = Server(
                'my_fake_ldap_server',
                get_info=OFFLINE_SLAPD_2_4
            )
    else:
        # Use specified port if provided
        server_kwargs = {
            'use_ssl': use_ssl,
            'get_info': get_info
        }
        if port is not None:
            server_kwargs['port'] = port
            
        # define LDAP server, requesting info on DSE and schema
        _server = Server(
            server,
            **server_kwargs
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
        ldap_server=None,
        ldap_port=None
    ) -> Connection:
    """Get an LDAP connection secure or not depending of LDAP_USE_SSL global.
    Args:
        ldap_user: The LDAP user DN
        ldap_password: The LDAP password
        ldap_auto_bind: Whether to auto bind
        ldap_use_ssl: Whether to use SSL
        ldap_get_info: What info to get from server
        ldap_client_strategy: The client strategy (SYNC, MOCK_SYNC, etc.)
        ldap_server: Optional custom LDAP server address
        ldap_port: Optional custom LDAP port
    Returns:
        Connection: the LDAP connection
    """
    global _conn
    
    # Always create a new connection when using client_strategy other than SYNC
    # or when explicitly specifying a server or port
    if ldap_client_strategy != SYNC or ldap_server is not None or ldap_port is not None:
        server = get_ldap_server(
            server=ldap_server or LDAP_SERVER,
            use_ssl=ldap_use_ssl,
            get_info=ldap_get_info,
            port=ldap_port
        )
        
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
        if PYTEST_CURRENT_TEST and USE_DOCKER_LDAP:
            server = get_ldap_server(
                server='localhost',
                use_ssl=False,
                get_info=ldap_get_info,
                port=DOCKER_LDAP_PORT
            )
        else:
            server = get_ldap_server(
                use_ssl=ldap_use_ssl,
                get_info=ldap_get_info
            )
            
        _conn = Connection(
            server,
            user=ldap_user,
            password=ldap_password,
            auto_bind=ldap_auto_bind,
            client_strategy=ldap_client_strategy
        )
    
    return _conn
