# Factory to get a LDAP connection
# Allow testing of LDAP connection
# author: Michaël Launay
# date: 2024-10-17

from .constants_and_globals import (
    LDAP_SERVER,
    LDAP_USE_SSL,
    LDAP_USER,
    PYTEST_CURRENT_TEST
)

from ldap3 import (
    Server,
    Connection,
    ALL,
    SYNC,
    MOCK_SYNC,
    OFFLINE_SLAPD_2_4
)

def get_ldap_server(
        server= LDAP_SERVER,
        get_info=ALL,
        use_ssl=LDAP_USE_SSL
    ) -> Server:
    """Get an LDAP server
    Returns:
        Server: An LDAP server
    """
    if not hasattr(get_ldap_server, 'server'):
        get_ldap_server.server = None
    if get_ldap_server.server:
        return get_ldap_server.server
    if PYTEST_CURRENT_TEST:
        # Use a mock server for testing
        get_ldap_server.server = Server(
            'my_fake_ldap_server',
            get_info = OFFLINE_SLAPD_2_4
        )
    else:
        # define LDAP server, requesting info on DSE and schema
        get_ldap_server.server = Server(
            server,
            use_ssl=use_ssl,
            get_info=get_info
        )
    return get_ldap_server.server

def get_ldap_connection(
        ldap_user, #LDAP_USER
        ldap_password, #get_secret(LDAP_PASSWORD)
        ldap_auto_bind=True,
        ldap_use_ssl=LDAP_USE_SSL,
        ldap_get_info=ALL,
        ldap_client_strategy=SYNC
        ) -> Connection:
    """Get an LDAP connection secure or not depending of LDAP_USE_SSL global.
    Returns:
        Connection: the unsecure LDAP connexion
    """
    server = get_ldap_server(LDAP_SERVER, use_ssl=ldap_use_ssl, get_info=ldap_get_info)
    if PYTEST_CURRENT_TEST:
        # Create a mocked LDAP connection with MOCK_SYNC strategy
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
    # define an unsecure LDAP connection, using the credentials above
    conn = Connection(
        server,
        ldap_user,
        ldap_password,
        auto_bind=ldap_auto_bind,
        client_strategy=ldap_client_strategy
        # client_strategy=SAFE_SYNC # Normaly prevent injection attacks but in this case clear conn.entries and conn.response!
    )
    return conn