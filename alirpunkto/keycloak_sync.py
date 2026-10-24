"""Propagation of directory changes to the SSO infrastructure (issues
#266 and #269).

Keycloak mirrors OpenLDAP through its *user federation*, but it does so
lazily: a new entry is imported the first time Keycloak looks it up, and
an existing one is refreshed only when the member authenticates through
Keycloak again. Until then the mailing lists and the workspace, which
read their users and groups from Keycloak, know nothing of a freshly
registered member (#266) nor of a member whose Dynamic Group just
changed (#269).

Two mechanisms close that gap, both best effort — a Keycloak outage must
never break the operation that triggered them, exactly like the dynamic
group synchroniser:

- :func:`propagate_ldap_changes_to_keycloak` asks Keycloak, through its
  admin REST API, to run a *changed users* synchronisation of every LDAP
  user-storage provider of the realm. Keycloak then re-imports the
  entries whose ``modifyTimestamp`` moved since its last pass — a new
  member, a member moved between Dynamic Groups, a renewed yearly
  contribution — and its group mappers follow. The call authenticates
  with the client credentials AlirPunkto already holds
  (``KEYCLOAK_CLIENT_ID`` / ``KEYCLOAK_CLIENT_SECRET``): the client must
  have *service accounts* enabled and carry the ``view-realm`` and
  ``manage-users`` roles of ``realm-management`` (see
  docs/*/architecture/05_*).
- :func:`import_member_into_keycloak` performs, right after a successful
  registration, the direct-access grant the login view already uses:
  Keycloak looks the new member up in the directory and imports the
  entry. It needs no extra privilege, only the password the member just
  chose, which is why it is reserved to the registration path.

Both honour the ``PYTEST_CURRENT_TEST`` guard of ``get_keycloak_token``:
patch :data:`PYTEST_CURRENT_TEST` to ``None`` to exercise the wire.
"""
from __future__ import annotations

import os
from datetime import datetime

from alirpunkto.constants_and_globals import (
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_CLIENT_SECRET,
    KEYCLOAK_REALM,
    KEYCLOAK_SERVER_URL,
    PYTEST_CURRENT_TEST,
    log,
)
from alirpunkto.secret_manager import get_secret

#: Keycloak component type of the user-storage providers of a realm.
USER_STORAGE_PROVIDER_TYPE = 'org.keycloak.storage.UserStorageProvider'

#: The only provider whose source of truth is our directory.
LDAP_PROVIDER_ID = 'ldap'

#: The admin-API action: re-import the entries changed since the last
#: pass (a full sync would re-read the whole directory on every event).
CHANGED_USERS_SYNC = 'triggerChangedUsersSync'

#: Seconds the admin calls may take; the sync itself runs server-side
#: and answers once done, so the budget covers a small directory delta.
ADMIN_TIMEOUT_SECONDS = 15

#: The LDAP storage component ids, discovered once per process: they
#: are stable for the life of the realm configuration.
_storage_ids_cache: list | None = None

#: Transversal audit of 2026-10-24 (A10): a propagation that failed must
#: be retried even when no new directory delta appears — the daily scan
#: used to call Keycloak only when a group changed during that very
#: pass. This marker file survives the process; it is written when a
#: propagation fails and removed when one succeeds.
PENDING_MARKER_PATH = os.getenv(
    'KEYCLOAK_SYNC_PENDING_MARKER',
    os.path.join('var', 'keycloak_sync_pending'))


def propagation_pending() -> bool:
    """True while a failed propagation awaits a successful retry."""
    return os.path.exists(PENDING_MARKER_PATH)


def _mark_pending(reason: str) -> None:
    try:
        directory = os.path.dirname(PENDING_MARKER_PATH)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(PENDING_MARKER_PATH, 'a', encoding='utf-8') as handle:
            handle.write(f"{datetime.now().isoformat()} {reason}\n")
    except OSError as exc:
        log.warning(f"keycloak_sync: cannot record the pending propagation: "
                    f"{exc}")


def _clear_pending() -> None:
    try:
        os.remove(PENDING_MARKER_PATH)
    except FileNotFoundError:
        pass
    except OSError as exc:
        log.warning(f"keycloak_sync: cannot clear the pending marker: {exc}")


def is_configured() -> bool:
    """True when the SSO infrastructure is declared in the environment."""
    return bool(KEYCLOAK_SERVER_URL and KEYCLOAK_REALM)


def _admin_client():
    """A KeycloakAdmin bound to the realm with the client credentials
    grant, or None when the SSO infrastructure is not configured."""
    if not is_configured():
        return None
    from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
    connection = KeycloakOpenIDConnection(
        server_url=KEYCLOAK_SERVER_URL,
        realm_name=KEYCLOAK_REALM,
        client_id=get_secret(KEYCLOAK_CLIENT_ID),
        client_secret_key=get_secret(KEYCLOAK_CLIENT_SECRET),
        grant_type='client_credentials',
        verify=True,
        timeout=ADMIN_TIMEOUT_SECONDS,
    )
    return KeycloakAdmin(connection=connection)


def ldap_storage_ids(admin, *, refresh: bool = False) -> list:
    """The ids of the LDAP user-storage providers of the realm."""
    global _storage_ids_cache
    if _storage_ids_cache is not None and not refresh:
        return list(_storage_ids_cache)
    components = admin.get_components(
        query={'type': USER_STORAGE_PROVIDER_TYPE})
    ids = [component['id'] for component in components
           if component.get('providerId') == LDAP_PROVIDER_ID
           and component.get('id')]
    _storage_ids_cache = ids
    return list(ids)


def reset_cache():
    """Forget the discovered storage ids (tests, realm reconfiguration)."""
    global _storage_ids_cache
    _storage_ids_cache = None


def propagate_ldap_changes_to_keycloak(reason: str = '') -> bool:
    """Ask Keycloak to re-import the directory entries changed since its
    last pass. Returns True when every LDAP provider of the realm
    synchronised, False otherwise (not configured, unreachable,
    refused). Never raises."""
    if PYTEST_CURRENT_TEST:
        log.debug("keycloak_sync: propagation skipped under pytest")
        return False
    if not is_configured():
        log.debug("keycloak_sync: Keycloak not configured, nothing to "
                  "propagate")
        return False
    try:
        admin = _admin_client()
        storage_ids = ldap_storage_ids(admin)
        if not storage_ids:
            log.warning("keycloak_sync: no LDAP user-storage provider in "
                        f"realm {KEYCLOAK_REALM}; nothing to propagate "
                        f"({reason})")
            return False
        all_clean = True
        for storage_id in storage_ids:
            result = admin.sync_users(storage_id, CHANGED_USERS_SYNC)
            if sync_failed(result):
                # Audit 2026-10-24 (second pass, P6): Keycloak answers
                # 200 with its counters even when some entries failed
                # to import — that is not a propagation. Nor is an
                # "ignored" synchronisation (A10).
                all_clean = False
                log.warning(f"keycloak_sync: provider {storage_id} "
                            f"reported failures while propagating "
                            f"{reason or 'directory change'}: "
                            f"{_summarise(result)}")
            else:
                log.info(f"keycloak_sync: {reason or 'directory change'} "
                         f"propagated to provider {storage_id}: "
                         f"{_summarise(result)}")
        if all_clean:
            _clear_pending()
        else:
            _mark_pending(reason or 'directory change')
        return all_clean
    except Exception as exc:
        # Best effort by design: the daily scan (and the next event)
        # will try again; the member can still log in through
        # AlirPunkto in the meantime. The marker makes that retry
        # happen even on a quiet day (A10).
        reset_cache()
        _mark_pending(reason or 'directory change')
        log.warning(f"keycloak_sync: could not propagate "
                    f"{reason or 'directory change'}: "
                    f"{exc.__class__.__name__}: {exc}")
        return False


def sync_failed(result) -> bool:
    """True when a Keycloak SynchronizationResult reports trouble, or
    when the answer is not one we can read. Only a JSON object carrying
    the ``failed`` counter or a ``status`` string is a recognised
    result (third audit pass): a body of another shape — nothing, a
    bare string, an object without those keys — is NOT taken as clean
    just because the call did not raise."""
    if not isinstance(result, dict):
        return True
    if 'failed' not in result and 'status' not in result:
        return True
    try:
        if int(result.get('failed') or 0) > 0:
            return True
    except (TypeError, ValueError):
        return True
    # SynchronizationResult.ignored: the provider did not run the sync
    # at all (import disabled, period not elapsed). Nothing was
    # propagated — pending, not success (A10).
    if result.get('ignored') in (True, 'true', 'True', 1):
        return True
    status = str(result.get('status') or '').lower()
    return any(word in status for word in ('fail', 'error'))


def _summarise(result) -> str:
    """The counters of a Keycloak SynchronizationResult, body withheld."""
    if not isinstance(result, dict):
        return 'done'
    keys = ('added', 'updated', 'removed', 'failed')
    return ', '.join(f"{key}={result.get(key, 0)}" for key in keys)


def import_member_into_keycloak(oid: str, password: str) -> bool:
    """Make Keycloak import a freshly registered member by authenticating
    them once through the direct-access grant (issue #266). Returns True
    when Keycloak issued a token — the entry now exists on the SSO side.
    Never raises; the token is discarded."""
    if not oid or not password:
        return False
    try:
        from alirpunkto.models.users import User
        from alirpunkto.utils import get_keycloak_token
        user = User(name=oid, email='', oid=oid)
        token = get_keycloak_token(user, password)
    except Exception as exc:
        log.warning(f"keycloak_sync: import of {oid} failed: "
                    f"{exc.__class__.__name__}")
        return False
    if token:
        log.info(f"keycloak_sync: member {oid} imported into Keycloak")
        return True
    log.warning(f"keycloak_sync: Keycloak did not import member {oid}; "
                "the next propagation will retry")
    return False
