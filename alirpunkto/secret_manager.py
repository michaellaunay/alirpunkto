from typing import Final
from .constants_and_globals import (
    log,
    SECRET_KEY,
    LDAP_PASSWORD,
    ADMIN_PASSWORD,
    MAIL_PASSWORD,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_CLIENT_SECRET,
)
import os
import base64
import hashlib
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding



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
        os.environ.pop(SECRET_KEY, None)
        # check if secret is not empty an make it accessible from the views
        if not SECRET_KEY_VALUE:
            raise ValueError("You must provide a base64 value for SECRET_KEY")
        get_secret.secrets = {
            SECRET_KEY: SECRET_KEY_VALUE,
            LDAP_PASSWORD: os.getenv(LDAP_PASSWORD),
            ADMIN_PASSWORD: os.getenv(ADMIN_PASSWORD),
            MAIL_PASSWORD: os.getenv(MAIL_PASSWORD),
            KEYCLOAK_CLIENT_ID: os.getenv(KEYCLOAK_CLIENT_ID, None),
            KEYCLOAK_CLIENT_SECRET: os.getenv(KEYCLOAK_CLIENT_SECRET, None),
        }
        os.environ.pop(LDAP_PASSWORD, None)
        os.environ.pop(ADMIN_PASSWORD, None)
        os.environ.pop(MAIL_PASSWORD, None)
        if get_secret.secrets[KEYCLOAK_CLIENT_ID] :
            os.environ.pop(KEYCLOAK_CLIENT_ID, None)
        if get_secret.secrets[KEYCLOAK_CLIENT_SECRET]:
            os.environ.pop(KEYCLOAK_CLIENT_SECRET, None)
    if not secret_name:
        # force the initialization of the secrets
        return None
    if secret_name not in get_secret.secrets:
        log.error(f"Unknown secret: {secret_name}")
        raise ValueError(f"Unknown secret: {secret_name}")
    return get_secret.secrets[secret_name]

def encrypt_secret_for_logs(secret: str | None) -> str:
    """Encrypt a secret for debug logs using a public key from environment.

    The private key must never be deployed on the application server.
    If encryption is disabled or unavailable, no secret is logged.
    """
    if not secret:
        return "<empty>"

    enabled = os.getenv("ALIRPUNKTO_LOG_ENCRYPTED_SECRETS", "false").lower()
    if enabled not in {"1", "true", "yes"}:
        return "<disabled>"

    public_key_b64 = os.getenv("ALIRPUNKTO_LOG_SECRETS_PUBLIC_KEY_B64")
    if not public_key_b64:
        return "<no-public-key>"

    try:
        public_key_pem = base64.b64decode(public_key_b64)
        public_key = serialization.load_pem_public_key(public_key_pem)

        encrypted = public_key.encrypt(
            secret.encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        return "enc:v1:" + base64.b64encode(encrypted).decode("ascii")

    except Exception:
        return "<encryption-error>"

# Recognised LDAP password hash scheme prefixes (RFC 2307 style). A value that
# already starts with one of these is treated as hashed and left untouched.
_HASHED_PREFIXES: Final = (
    "{SSHA}", "{SHA}", "{SSHA256}", "{SHA256}", "{SSHA512}", "{SHA512}",
    "{SMD5}", "{MD5}", "{CRYPT}", "{ARGON2}", "{PBKDF2}", "{PBKDF2-SHA1}",
    "{PBKDF2-SHA256}", "{PBKDF2-SHA512}",
)


def is_hashed_password(value: str | None) -> bool:
    """Return True if ``value`` already carries an LDAP password hash prefix."""
    if not value:
        return False
    return value.upper().startswith(tuple(p.upper() for p in _HASHED_PREFIXES))


def make_ldap_password(cleartext: str, salt_len: int = 8) -> str:
    """Return a salted-SHA1 ``{SSHA}`` userPassword value for ``cleartext``.

    This is exactly what ``slappasswd -h {SSHA}`` produces. OpenLDAP verifies it
    natively during bind, so storing this instead of the cleartext password keeps
    the existing bind-based authentication (see ``check_password``) working with
    no server-side change (finding 1.3).

    Idempotent: an already-hashed value is returned unchanged, so callers may
    apply it defensively on values that might have been hashed upstream.
    """
    if is_hashed_password(cleartext):
        return cleartext
    salt = os.urandom(salt_len)
    digest = hashlib.sha1(cleartext.encode("utf-8") + salt).digest()
    return "{SSHA}" + base64.b64encode(digest + salt).decode("ascii")
