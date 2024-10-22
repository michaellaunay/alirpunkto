# Factory to get a LDAP connection
# Allow testing of LDAP connection
# author: Michaël Launay
# date: 2024-10-17

from alirpunkto.constants_and_globals import (
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

import json
import base64

ALIRPUNKTO_LDIF_FILE = "alirpunkto/alirpunkto_schema.ldif"

def parse_ldif(ldif_source:str = ALIRPUNKTO_LDIF_FILE) -> dict:
    """Parse a LDIF file and return a JSON schema object
    Args:
        ldif_source (str): The path to the LDIF file
    Returns:
        dict: A JSON schema object
    """
    entries = []
    with open(ldif_source, 'r') as ldif_file:
        entry = {}
        current_attr = None
        current_value = ''
        for line in ldif_file:
            line = line.rstrip('\n')
            if line == '':
                # End of current entry
                if current_attr is not None:
                    # Save the last attribute
                    if current_attr in entry:
                        if isinstance(entry[current_attr], list):
                            entry[current_attr].append(current_value)
                        else:
                            entry[current_attr] = [entry[current_attr], current_value]
                    else:
                        entry[current_attr] = current_value
                    current_attr = None
                    current_value = ''
                if entry:
                    entries.append(entry)
                    entry = {}
                continue
            if line.startswith(' '): # Continuation of the previous line
                current_value += line[1:]
            else:
                # Save the previous attribute
                if current_attr is not None:
                    if current_attr in entry:
                        if isinstance(entry[current_attr], list):
                            entry[current_attr].append(current_value)
                        else:
                            entry[current_attr] = [entry[current_attr], current_value]
                    else:
                        entry[current_attr] = current_value
                # Analyze the new attribute
                if ': ' in line:
                    current_attr, current_value = line.split(': ', 1)
                elif ':: ' in line:
                    # Value encoded in Base64
                    current_attr, current_value = line.split(':: ', 1)
                    current_value = base64.b64decode(current_value).decode('utf-8')
                else:
                    continue

    # Save the last attribute after the end of the file
    if current_attr is not None:
        if current_attr in entry:
            if isinstance(entry[current_attr], list):
                entry[current_attr].append(current_value)
            else:
                entry[current_attr] = [entry[current_attr], current_value]
        else:
            entry[current_attr] = current_value

    # Save the last entry
    if entry:
        entries.append(entry)

    # Build the JSON object

    if entries:
        entry = entries[0]
        json_obj = {}
        json_obj['dn'] = entry.get('dn', '')
        json_obj['raw'] = {}
        for key in entry:
            if key == 'dn':
                continue
            value = entry[key]
            if not isinstance(value, list):
                value = [value]
            json_obj['raw'][key] = value
        # Define the type based on the content
        json_obj['type'] = 'SchemaInfo'
        return json_obj
    else:
        return {}

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
        from ldap3.protocol.rfc4512 import SchemaInfo
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
        ldap_user,
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

if __name__ == '__main__':
    print("alirpunkto_shema.ldif:", parse_ldif())
    print(get_ldap_server())
    from alirpunkto.secret_manager import get_secret
    from alirpunkto.constants_and_globals import LDAP_PASSWORD
    print(get_ldap_connection(LDAP_USER, get_secret(LDAP_PASSWORD)))