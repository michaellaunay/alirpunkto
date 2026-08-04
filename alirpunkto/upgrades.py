"""Data-schema versioning and upgrade steps for the ZODB.

The directory (LDAP) is the source of truth for members; the ZODB
carries the application state around it (candidatures, workflows,
per-member application data). When the persisted structure changes,
the code must bring existing databases along — this module gives
that a home, in the spirit of the GenericSetup upgrade steps the
maintainer knows from Plone, reduced to what this application needs.

Contract:

- ``app_root.schema_version`` (int, missing == 0) records the data
  schema a database carries. ``SCHEMA_VERSION`` is what the code
  expects.
- ``UPGRADE_STEPS`` maps each version to the step that reaches it:
  ``(to_version, description, callable(app_root))``. Steps are
  **idempotent** (they may be replayed after a conflict retry) and
  **one per persisted-structure change** — adding an attribute,
  renaming a container, reshaping a mapping. Behavioural code
  changes need no step.
- Two runners share this module: the lazy one in ``root_factory``
  (first request after an upgrade migrates inside that request's
  transaction, pyramid_retry replays it on conflict) and the
  explicit CLI ``tools/run_upgrades.py`` for operators who migrate
  with the application stopped.

The production deployment pinned at e6603d22 needs no data step to
reach version 1: the enum values added since (the resignation flow)
extend the vocabulary without touching stored objects, and the
views read persisted attributes defensively. Version 1 only stamps
the database so every later change has a baseline to build on.

The strong path — wipe the ZODB and rebuild it from LDAP, accepted
by the maintainer on 2026-08-04 (pending candidatures are lost;
they are overwhelmingly unresolved-challenge spam) — lives in
``tools/rebuild_zodb_from_ldap.py``.
"""

import logging

log = logging.getLogger(__name__)


def _stamp_only(app_root) -> None:
    """Version 1 introduces the versioning itself: nothing to move."""


#: (to_version, description, step) — ordered, contiguous from 1.
UPGRADE_STEPS = [
    (1,
     "Begin schema versioning: stamp the database; no data change.",
     _stamp_only),
]

#: The schema the code expects: the highest step target.
SCHEMA_VERSION = UPGRADE_STEPS[-1][0]

# The registry must be dense and ordered — a gap means a database
# could never reach the code's version.
assert [v for v, _, _ in UPGRADE_STEPS] == list(
    range(1, SCHEMA_VERSION + 1)
), "UPGRADE_STEPS must be contiguous from 1"


def get_schema_version(app_root) -> int:
    """The schema a database carries; pre-versioning databases are 0."""
    return getattr(app_root, "schema_version", 0)


def run_pending_upgrades(app_root, commit_each=None) -> list:
    """Bring ``app_root`` from its stored version to SCHEMA_VERSION.

    Applies every step above the stored version, in order, stamping
    the reached version after each one so an interruption resumes
    where it stopped. ``commit_each`` — used by the CLI runner — is
    called after each stamped step to commit it as its own
    transaction; under ``root_factory`` the request's transaction
    commits the whole (steps stay idempotent for conflict replays).

    Returns the list of versions applied.
    """
    applied = []
    current = get_schema_version(app_root)
    for to_version, description, step in UPGRADE_STEPS:
        if to_version <= current:
            continue
        log.info("Upgrade step %s: %s", to_version, description)
        step(app_root)
        app_root.schema_version = to_version
        current = to_version
        applied.append(to_version)
        if commit_each is not None:
            commit_each()
    if applied:
        log.info("Database schema now at version %s", current)
    return applied
