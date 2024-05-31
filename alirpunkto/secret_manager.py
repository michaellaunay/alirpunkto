from typing import Final
from .constants_and_globals import (
    log,
    dotenv_path,
    SECRET_KEY,
    LDAP_PASSWORD,
    ADMIN_PASSWORD,
    MAIL_PASSWORD,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_CLIENT_SECRET,
)
import os, inspect

def get_secret(secret_name: str) -> str:
    """Get the secret from the secret manager.
    Args:
        secret_name: The name of the secret, None force the initialization.
    Returns:
        The secret.
    """
    if not hasattr(get_secret, 'secrets'):
        # SECRET_KEY is used for cookie signing
        # This information is stored in environment variables
        # See https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/security.html
        # Using get_key() instead of os.getenv() as os.getenv() does not 
        # handle values containing `=` properly.
        SECRET_KEY_VALUE: Final = os.getenv(SECRET_KEY, None)
        del os.environ[SECRET_KEY]
        # check if secret is not empty an make it accessible from the views
        if not SECRET_KEY:
            raise ValueError("You must provide a base64 value for SECRET_KEY")
        get_secret.secrets = {
            SECRET_KEY: SECRET_KEY_VALUE,
            LDAP_PASSWORD: os.getenv(LDAP_PASSWORD),
            ADMIN_PASSWORD: os.getenv(ADMIN_PASSWORD),
            MAIL_PASSWORD: os.getenv(MAIL_PASSWORD),
            KEYCLOAK_CLIENT_ID: os.getenv(KEYCLOAK_CLIENT_ID, None),
            KEYCLOAK_CLIENT_SECRET: os.getenv(KEYCLOAK_CLIENT_SECRET, None),
        }
        del os.environ[LDAP_PASSWORD]
        del os.environ[ADMIN_PASSWORD]
        del os.environ[MAIL_PASSWORD]
        if get_secret.secrets[KEYCLOAK_CLIENT_ID] :
            del os.environ[KEYCLOAK_CLIENT_ID]
        if get_secret.secrets[KEYCLOAK_CLIENT_SECRET]:
            del os.environ[KEYCLOAK_CLIENT_SECRET]
    if not secret_name:
        # force the initialization of the secrets
        return None
    if secret_name not in get_secret.secrets:
        log.error(f"Unknown secret: {secret_name}")
        raise ValueError(f"Unknown secret: {secret_name}")
    return get_secret.secrets[secret_name]