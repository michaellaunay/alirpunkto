#!/usr/bin/env python3
"""
migrate_ldap_legacy_remote.py — adapt a legacy AlirPunkto LDAP directory that
runs on a *bare-metal* server (no container, no shell access for ``slapcat``).

``docker/migrate_ldap_legacy.py`` extracts the legacy tree with ``slapcat``,
which requires filesystem access to the slapd database. When the old OpenLDAP
only exposes the network, this tool does the extraction differently and reuses
everything else:

1. It reads the admin credentials from the project ``.env`` at the repository
   root — the same variables the application uses (``LDAP_SERVER``,
   ``LDAP_LOGIN``, ``LDAP_OU``, ``LDAP_BASE_DN``, ``LDAP_PASSWORD``,
   ``LDAP_USE_SSL``/``LDAP_PORT``) — every one of them overridable on the
   command line. The bind DN is built exactly like the application does:
   ``LDAP_LOGIN[,LDAP_OU],LDAP_BASE_DN`` (a ``LDAP_LOGIN`` already containing a
   comma is taken as a full DN).
2. It binds over the network (``ldap3``) and extracts the whole subtree with a
   paged search (RFC 2696), falling back to a plain search on servers too old
   to support the control. Only user attributes are requested, so operational
   attributes never enter the output.
3. Because an LDAP search — unlike ``slapcat`` — returns entries in arbitrary
   order, entries are re-ordered parents-first so the adapted LDIF loads with
   a plain ``ldapadd``.
4. It then runs the **same transformation pipeline** as the docker variant
   (imported from ``docker/migrate_ldap_legacy.py``, single source of truth):
   ``employeeType`` normalisation, group renames and reference rewriting,
   ``gn``→``givenName``, ``isActive`` canonicalisation, consistency checks —
   and, per security finding 1.3, cleartext ``userPassword`` values are hashed
   to ``{SSHA}`` by default (``--keep-cleartext-passwords`` to opt out).

Prerequisites and caveats
-------------------------
* Reading ``userPassword`` over the network requires an account allowed to by
  the server ACLs — normally the rootdn. If person entries come back without
  ``userPassword``, the report says so loudly: fix the bind account before
  loading, or the migrated users will have no password.
* The ``{SSHA}`` hashing lives in the shared pipeline and therefore requires
  the 1.3 patch on ``docker/migrate_ldap_legacy.py``. On an older (pre-1.3)
  pipeline this tool still runs, but it keeps cleartext passwords verbatim
  and the report says so loudly — apply the 1.3 patch before a real
  migration.
* The target stack's ``init.sh`` already creates the base entry, the OU and
  the groups; loading the adapted LDIF with ``ldapadd`` will report
  ``entryAlreadyExists`` for those. Load the remaining entries (``ldapadd``
  continues with ``-c``), or prune them from the LDIF after review — the
  report lists every group it touched.

Usage
-----
    # everything from the project .env, output to files
    python tools/migrate_ldap_legacy_remote.py \
        --output adapted.ldif --report report.txt

    # explicit server and bind DN, password typed interactively
    python tools/migrate_ldap_legacy_remote.py \
        --url ldap://old-server.example.org:389 \
        --bind-dn "cn=admin,dc=example,dc=org" --ask-password \
        --base-dn "dc=example,dc=org" \
        --output adapted.ldif --report report.txt
"""
from __future__ import annotations

import argparse
import base64
import getpass
import importlib.util
import inspect
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SHARED_PATH = REPO_ROOT / "docker" / "migrate_ldap_legacy.py"
DEFAULT_ENV_FILE = REPO_ROOT / ".env"
_PERSON_CLASSES = {"person", "inetorgperson", "alirpunktoperson"}


# ─────────────────────────────────────────────────────────────────────────────
# shared pipeline (docker/migrate_ldap_legacy.py is the single source of truth)
# ─────────────────────────────────────────────────────────────────────────────
def load_shared(path: Path = SHARED_PATH):
    """Import the docker migration script as a module (transform, Entry, ...)."""
    if not path.exists():
        raise SystemExit(f"error: shared pipeline not found at {path}")
    spec = importlib.util.spec_from_file_location("migrate_ldap_legacy", path)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules[__module__]
    sys.modules["migrate_ldap_legacy"] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop("migrate_ldap_legacy", None)
        raise
    return module


# ─────────────────────────────────────────────────────────────────────────────
# configuration (.env at the repository root, CLI overrides)
# ─────────────────────────────────────────────────────────────────────────────
def read_env_file(path: Path) -> dict[str, str]:
    """Parse a ``.env`` file (python-dotenv when available, else minimal)."""
    if not path.exists():
        return {}
    try:
        from dotenv import dotenv_values
        return {k: v for k, v in dotenv_values(path).items() if v is not None}
    except ImportError:
        pass
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, _, value = line.partition("=")
        value = value.strip()
        if value[:1] in {'"', "'"} and value[-1:] == value[:1]:
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].rstrip()
        values[key.strip()] = value
    return values


def cfg(env: dict[str, str], key: str) -> str | None:
    """Config lookup: process environment first, then the ``.env`` file."""
    return os.environ.get(key) or env.get(key)


def build_server_url(env: dict[str, str], override: str | None = None) -> str:
    url = override or cfg(env, "LDAP_SERVER")
    if not url:
        raise SystemExit("error: no server — set LDAP_SERVER in .env or pass --url")
    if "://" in url:
        return url
    use_ssl = (cfg(env, "LDAP_USE_SSL") or "False").lower() in ("1", "true", "yes", "y")
    port = cfg(env, "LDAP_PORT")
    scheme = "ldaps" if use_ssl else "ldap"
    return f"{scheme}://{url}" + (f":{port}" if port else "")


def build_bind_dn(env: dict[str, str], override: str | None = None) -> str:
    """Reproduce the application's bind DN: LDAP_LOGIN[,LDAP_OU],LDAP_BASE_DN."""
    if override:
        return override
    login = cfg(env, "LDAP_LOGIN")
    if not login:
        raise SystemExit("error: no bind DN — set LDAP_LOGIN in .env or pass --bind-dn")
    if "," in login:                      # already a full DN
        return login
    base = cfg(env, "LDAP_BASE_DN")
    if not base:
        raise SystemExit("error: LDAP_BASE_DN is required to build the bind DN "
                         "from LDAP_LOGIN (or pass --bind-dn)")
    ou = cfg(env, "LDAP_OU")
    return f"{login},{ou},{base}" if ou else f"{login},{base}"


def resolve_password(env: dict[str, str], password_env: str, ask: bool) -> str:
    password = cfg(env, password_env)
    if not password and ask:
        password = getpass.getpass(f"Password for the LDAP bind ({password_env} unset): ")
    if not password:
        raise SystemExit(f"error: no password — set {password_env} (process env or .env), "
                         f"use --password-env NAME, or pass --ask-password")
    return password


# ─────────────────────────────────────────────────────────────────────────────
# extraction
# ─────────────────────────────────────────────────────────────────────────────
def raw_to_value(raw: bytes, mark_b64: str) -> str:
    """ldap3 raw value → shared-pipeline value.

    UTF-8 text is kept as ``str`` — ``format_attr`` already base64-encodes
    anything not LDIF-safe on output. Truly binary values are carried with the
    pipeline's base64 marker so they round-trip byte-for-byte.
    """
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return mark_b64 + base64.b64encode(raw).decode("ascii")


def _dn_depth(dn: str) -> int:
    # naive split on unescaped commas — same assumption as the shared pipeline
    return len([p for p in dn.split(",") if p.strip()])


def connect(url: str, bind_dn: str, password: str,
            starttls: bool = False, timeout: int = 10):
    from ldap3 import Connection, Server
    server = Server(url, get_info=None, connect_timeout=timeout)
    conn = Connection(server, user=bind_dn, password=password,
                      raise_exceptions=True)
    conn.open()
    if starttls:
        conn.start_tls()
    conn.bind()
    return conn


def fetch_entries(conn, base_dn: str, shared, rep, page_size: int = 200) -> list:
    """Search the whole subtree and return parents-first shared ``Entry`` objects."""
    from ldap3 import SUBTREE

    results: list[dict]
    try:
        results = list(conn.extend.standard.paged_search(
            search_base=base_dn,
            search_filter="(objectClass=*)",
            search_scope=SUBTREE,
            attributes=["*"],
            paged_size=page_size,
            generator=True,
        ))
        rep.info(f"paged search over {base_dn} (page size {page_size})")
    except Exception as exc:                       # very old servers: no RFC 2696
        rep.warn(f"paged search unavailable ({exc.__class__.__name__}: {exc}); "
                 f"falling back to a plain subtree search")
        if not conn.search(base_dn, "(objectClass=*)",
                           search_scope=SUBTREE, attributes=["*"]):
            raise SystemExit(f"error: search failed: {conn.result}")
        results = list(conn.response or [])

    entries = []
    persons_without_password = 0
    for item in results:
        if item.get("type") != "searchResEntry":
            continue                               # referrals, controls, ...
        raw_attributes = item.get("raw_attributes") or {}
        pairs: list[tuple[str, str]] = []
        # objectClass first (readability), then the server's order
        for name in sorted(raw_attributes, key=lambda a: a.lower() != "objectclass"):
            for raw in raw_attributes[name]:
                pairs.append((name, raw_to_value(raw, shared.MARK_B64)))
        entry = shared.Entry(dn=item["dn"], attrs=pairs)
        object_classes = {v.lower() for v in entry.get("objectClass")}
        if object_classes & _PERSON_CLASSES and not entry.get("userPassword"):
            persons_without_password += 1
        entries.append(entry)

    # an LDAP search, unlike slapcat, guarantees no order: parents first
    entries.sort(key=lambda e: (_dn_depth(e.dn), e.dn.lower()))

    rep.info(f"fetched {len(entries)} entries from the server")
    if persons_without_password:
        rep.warn(f"{persons_without_password} person entr"
                 f"{'y' if persons_without_password == 1 else 'ies'} came back "
                 f"WITHOUT userPassword — the bind account probably lacks read "
                 f"ACL on userPassword (bind as the rootdn or fix the ACL), "
                 f"otherwise the migrated accounts will have no password")
    return entries


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def transform_with_pipeline(shared, entries, rep, args):
    """Run the shared transform, degrading loudly on a pre-1.3 pipeline.

    Returns ``(entries, supports_hashing)``. When the shared pipeline predates
    the 1.3 patch (no ``hash_cleartext`` parameter), passwords are left
    untouched and the report carries an explicit warning instead of the tool
    crashing with a TypeError.
    """
    kwargs = dict(strict=args.strict, keep_operational=args.keep_operational)
    supports_hashing = (
        "hash_cleartext" in inspect.signature(shared.transform).parameters)
    if supports_hashing:
        kwargs["hash_cleartext"] = not args.keep_cleartext_passwords
    elif not args.keep_cleartext_passwords:
        rep.warn("the shared pipeline predates the 1.3 patch: cleartext "
                 "userPassword values are KEPT VERBATIM — apply the 1.3 patch "
                 "on docker/migrate_ldap_legacy.py to get {SSHA} hashing")
    return shared.transform(entries, rep, **kwargs), supports_hashing


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Adapt a legacy AlirPunkto LDAP served by a bare-metal "
                    "OpenLDAP: bind over the network with the .env admin "
                    "credentials, then run the standard migration pipeline "
                    "(employeeType/groups/isActive normalisation, {SSHA} "
                    "hashing of cleartext passwords).",
    )
    p.add_argument("--env-file", metavar="FILE", default=str(DEFAULT_ENV_FILE),
                   help=f"project .env to read (default: {DEFAULT_ENV_FILE})")
    p.add_argument("--url", metavar="URL",
                   help="ldap[s]://host[:port] (default: LDAP_SERVER from .env)")
    p.add_argument("--bind-dn", metavar="DN",
                   help="bind DN (default: LDAP_LOGIN[,LDAP_OU],LDAP_BASE_DN "
                        "like the application)")
    p.add_argument("--base-dn", metavar="DN",
                   help="search base (default: LDAP_BASE_DN from .env)")
    p.add_argument("--password-env", metavar="NAME", default="LDAP_PASSWORD",
                   help="variable holding the bind password "
                        "(default: LDAP_PASSWORD; process env wins over .env)")
    p.add_argument("--ask-password", action="store_true",
                   help="prompt for the password if the variable is unset")
    p.add_argument("--starttls", action="store_true",
                   help="issue StartTLS before binding")
    p.add_argument("--page-size", type=int, default=200,
                   help="paged-search page size (default: 200)")
    p.add_argument("--timeout", type=int, default=10,
                   help="connect timeout in seconds (default: 10)")
    p.add_argument("--output", metavar="LDIF", help="adapted LDIF (default: stdout)")
    p.add_argument("--report", metavar="FILE", help="report file (default: stderr)")
    p.add_argument("--strict", action="store_true",
                   help="treat unrecognised employeeType / issues as errors "
                        "(non-zero exit)")
    p.add_argument("--keep-operational", action="store_true",
                   help="kept for symmetry with the docker variant (a network "
                        "search never returns operational attributes)")
    p.add_argument("--keep-cleartext-passwords", action="store_true",
                   help="do NOT hash cleartext userPassword values (keep them "
                        "verbatim); by default they are hashed to {SSHA}")
    args = p.parse_args(argv)

    env = read_env_file(Path(args.env_file))
    if not env and not (args.url and args.bind_dn and args.base_dn):
        print(f"note: {args.env_file} not found or empty; relying on process "
              f"environment and CLI options", file=sys.stderr)

    url = build_server_url(env, args.url)
    bind_dn = build_bind_dn(env, args.bind_dn)
    base_dn = args.base_dn or cfg(env, "LDAP_BASE_DN")
    if not base_dn:
        raise SystemExit("error: no search base — set LDAP_BASE_DN in .env "
                         "or pass --base-dn")
    password = resolve_password(env, args.password_env, args.ask_password)

    shared = load_shared()
    rep = shared.Report()
    rep.info(f"source: {url} (bind as {bind_dn})")
    rep.info(f"search base: {base_dn}")

    try:
        from ldap3.core.exceptions import LDAPException
    except ImportError:
        raise SystemExit("error: the ldap3 package is required "
                         "(run inside the application virtualenv)")
    try:
        conn = connect(url, bind_dn, password,
                       starttls=args.starttls, timeout=args.timeout)
    except LDAPException as exc:
        raise SystemExit(f"error: could not bind to {url} as {bind_dn}: {exc}")

    try:
        entries = fetch_entries(conn, base_dn, shared, rep,
                                page_size=args.page_size)
    finally:
        conn.unbind()

    entries, supports_hashing = transform_with_pipeline(
        shared, entries, rep, args)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if args.keep_cleartext_passwords:
        pw_note = "kept verbatim (--keep-cleartext-passwords)"
    elif not supports_hashing:
        pw_note = ("kept verbatim (shared pipeline predates the 1.3 patch — "
                   "apply it to hash)")
    else:
        pw_note = "cleartext values hashed to {SSHA}; existing hashes kept as-is"
    header = (
        f"# Adapted from the legacy AlirPunkto LDAP at {url}\n"
        f"# by migrate_ldap_legacy_remote.py (network extraction, bind {bind_dn})\n"
        f"# Generated: {now}\n"
        f"# userPassword: {pw_note}.\n"
        f"# Review the report before loading with slapadd/ldapadd.\n"
    )
    out = shared.write_ldif(entries, header=header)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(out)
    else:
        sys.stdout.write(out)

    report_text = rep.text() + (
        f"\n\nRESULT: {rep.errors} error(s), {rep.warnings} warning(s)\n"
    )
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(report_text)
    else:
        sys.stderr.write("\n" + report_text)

    if args.strict and rep.errors:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
