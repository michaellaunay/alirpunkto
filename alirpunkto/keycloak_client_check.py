"""Boot-time check of the SSO client library.

Production incident of 2026-10-30: the home page's Login answered 500 on
every click because the server's virtualenv still carried an old
python-keycloak whose ``auth_url`` had no ``code_challenge`` parameter —
the PKCE round trip of train 0124 (transversal audit A04) needs
python-keycloak 7.1.1, the version ``pyproject.toml`` requires and
``requirements.lock`` pins. The application booted fine and only broke
at the first navigation.

``assert_pkce_capable_client`` runs at the start of ``main()``: when the
installed library cannot do PKCE, the application refuses to start with
one explicit message in the journal (installed version, required
version, the command that fixes it) instead of serving 500s.
"""
from __future__ import annotations

import inspect
from importlib.metadata import PackageNotFoundError, requires, version

from keycloak import KeycloakOpenID

from alirpunkto.constants_and_globals import log

#: The keyword parameters the authorization-code round trip passes.
REQUIRED_PARAMETERS = {
    'auth_url': ('code_challenge', 'code_challenge_method'),
    'token': ('code_verifier',),
}

#: Fallback when the distribution metadata is unavailable (bare source
#: tree without an installed distribution).
DEFAULT_REQUIREMENT = 'python-keycloak>=7.1.1,<8'

#: The command that brings the environment back to the lock.
FIX_COMMAND = 'pip install --require-hashes -r requirements.lock'


def installed_version() -> str:
    try:
        return version('python-keycloak')
    except PackageNotFoundError:
        return 'unknown'


def required_version() -> str:
    """The python-keycloak requirement of the installed distribution,
    as ``pyproject.toml`` states it."""
    try:
        for requirement in requires('alirpunkto') or ():
            if requirement.startswith('python-keycloak'):
                return requirement.split(';', 1)[0].strip()
    except PackageNotFoundError:
        pass
    return DEFAULT_REQUIREMENT


def missing_parameters() -> list[str]:
    """``method(parameter)`` for every PKCE parameter the installed
    ``KeycloakOpenID`` does not declare explicitly."""
    missing = []
    for method, parameters in REQUIRED_PARAMETERS.items():
        callable_ = getattr(KeycloakOpenID, method, None)
        try:
            accepted = inspect.signature(callable_).parameters
        except (TypeError, ValueError):
            accepted = {}
        missing.extend(f"{method}({parameter})" for parameter in parameters
                       if parameter not in accepted)
    return missing


def assert_pkce_capable_client() -> None:
    """Raise ``RuntimeError`` (after a CRITICAL log line) when the
    installed python-keycloak cannot run the PKCE round trip."""
    missing = missing_parameters()
    if not missing:
        return
    message = (
        f"python-keycloak {installed_version()} cannot run the PKCE "
        f"authorization-code round trip: missing {', '.join(missing)}. "
        f"The application requires {required_version()}; reinstall the "
        f"environment from the lock ({FIX_COMMAND}) and restart.")
    log.critical(message)
    raise RuntimeError(message)
