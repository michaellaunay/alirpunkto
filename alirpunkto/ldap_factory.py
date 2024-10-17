# Factory to get a LDAP connection
# Allow testing of LDAP connection
# author: Michaël Launay
# date: 2024-10-17

from .constants_and_globals import (
    LDAP_SERVER,
    LDAP_USE_SSL,
    LDAP_LOGIN,
    LDAP_PASSWORD,
    LDAP_BASE_DN,
    LDAP_OU,
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
        ldap_password, #get_secret(LDAP_PASSWORD)
        ldap_login=LDAP_LOGIN,
        ldap_ou=LDAP_OU,
        ldap_base_dn=LDAP_BASE_DN,
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
            user='cn=admin,dc=example,dc=com',
            password='A_GREAT_PASSWORD',
            client_strategy=MOCK_SYNC,
            auto_bind=True
        )
        return conn       
    # define an unsecure LDAP connection, using the credentials above
    conn = Connection(
        server,
        ldap_login,
        ldap_password,
        auto_bind=ldap_auto_bind,
        client_strategy=ldap_client_strategy
        # client_strategy=SAFE_SYNC # Normaly prevent injection attacks but in this case clear conn.entries and conn.response!
    )
    return conn