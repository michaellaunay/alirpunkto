#!/usr/bin/env python3
"""
ldap_provision.py — extract a live AlirPunkto directory, adapt it, and
re-provision a target installation (docker container or bare-metal host).

One tool for the whole journey:

1. **Extract & adapt** (always). Binds to the source directory with the admin
   credentials from the project ``.env`` (same variables and CLI overrides as
   ``tools/migrate_ldap_legacy_remote.py``, whose functions it reuses), pulls
   the whole subtree, and runs the standard migration pipeline of
   ``docker/migrate_ldap_legacy.py``: ``employeeType``/group/``isActive``
   normalisation, reference repairs (``providerMembersGroup``, members
   misparented under ``cn=admin``, literal ``None`` descriptions) and the
   default ``{SSHA}`` hashing of cleartext passwords (finding 1.3).

2. **Write the seed file** (always). The output is *interchangeable* with the
   file ``docker/init.sh`` generates: copy it to
   ``docker/initials_users.generated.ldif`` (or pass
   ``--install-into-docker`` to do it for you) and the compose stack will
   seed the container with your real users at the next initialisation —
   ``start_ldap.sh`` loads it with ``ldapadd -c``, so the groups it shares
   with the template are simply reported as already existing.

3. **Force the schema update** (``--update-schema``). Reads the reference
   schema ``alirpunkto/alirpunkto_schema.ldif``, discovers the
   ``cn={N}alirpunktoperson,cn=schema,cn=config`` entry on the target and
   *replaces* its ``olcAttributeTypes``/``olcObjectClasses`` with the current
   definitions (idempotent — safe to run twice); if the entry is absent the
   whole schema is added. Runs through ``ldapi:///`` with SASL EXTERNAL:
   inside the container for ``--install-type docker``, locally for
   ``--install-type host`` (root privileges are usually required there — see
   ``--sudo``). This is the definitive fix for the
   ``invalid attribute type cooperativeBehaviourMarkUpdate`` login error.

4. **Recreate the initial users** (``--load``). Feeds the seed file to
   ``ldapadd -c -Y EXTERNAL -H ldapi:///`` on the chosen target — the
   container for ``--install-type docker`` (``--container`` to name it), the
   local slapd for ``--install-type host``. ``-c`` makes existing entries
   (base, groups) harmless.

5. **Hash passwords in place** (``--update-passwords-in-place``). For an
   existing directory you do *not* want to reload: every account whose stored
   ``userPassword`` is still cleartext gets a ``MODIFY_REPLACE`` with the
   ``{SSHA}`` value computed in step 1, over the same authenticated
   connection. Already-hashed values are left untouched, so this too is
   idempotent. Logins keep working: slapd verifies ``{SSHA}`` at bind.

Repopulating the ZODB
---------------------
Nothing to run here — the application does it by itself. Once the directory
is provisioned (schema current, users present, passwords hashed):

1. stop AlirPunkto;
2. move the old object store away: ``mv var var.bak`` (or delete it) and
   recreate the tree the app expects (``mkdir -p var/filestorage var/blobs
   var/log`` on a bare-metal host, or just restart the stack);
3. start AlirPunkto again.

At each user's first login, ``update_member_from_ldap`` finds no member in
the fresh ZODB, rebuilds it from the LDAP entry (``password``/
``password_confirm`` stay ``None`` — finding 1.3) and stores it. This lazy
repopulation is locked by ``tests/test_zodb_repopulation_from_ldap.py``.

Usage examples
--------------
    # Bare-metal host, end to end: seed file + schema + users
    python tools/ldap_provision.py --install-type host --sudo \\
        --update-schema --load --report provision.txt

    # Docker: refresh the seed file for the next container init only
    python tools/ldap_provision.py --install-into-docker

    # Docker: also (re)create the users in the RUNNING container
    python tools/ldap_provision.py --install-type docker \\
        --container alirpunkto-ldap --load

    # Legacy server kept in place: just hash its cleartext passwords
    python tools/ldap_provision.py --update-passwords-in-place

    # Only force the schema of the host's slapd (fixes the login 500)
    python tools/ldap_provision.py --install-type host --sudo --update-schema
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
REMOTE_TOOL_PATH = REPO_ROOT / "tools" / "migrate_ldap_legacy_remote.py"
SCHEMA_FILE = REPO_ROOT / "alirpunkto" / "alirpunkto_schema.ldif"
SEED_FILE_NAME = "initials_users.generated.ldif"
DOCKER_SEED_PATH = REPO_ROOT / "docker" / SEED_FILE_NAME
DEFAULT_CONTAINER = "alirpunkto-ldap"
# presence of these proves the schema is current (post-2024 additions)
MODERN_SCHEMA_PROBES = ("cooperativeBehaviourMarkUpdate", "IBAN",
                        "dateErasureAllData",
    "cipheredPersonalData",
    "identityRecoveryCode",
)
_HASH_PREFIXES = (
    "{SSHA}", "{SHA}", "{SSHA256}", "{SHA256}", "{SSHA512}", "{SHA512}",
    "{SMD5}", "{MD5}", "{CRYPT}", "{ARGON2}", "{PBKDF2}", "{PBKDF2-SHA1}",
    "{PBKDF2-SHA256}", "{PBKDF2-SHA512}",
)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module          # dataclasses need the registration
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def load_remote():
    """Import tools/migrate_ldap_legacy_remote.py (extraction + pipeline)."""
    return _load_module(REMOTE_TOOL_PATH, "migrate_ldap_legacy_remote")


def is_hashed(value: str | None) -> bool:
    return bool(value) and value.upper().startswith(
        tuple(p.upper() for p in _HASH_PREFIXES))


# ─────────────────────────────────────────────────────────────────────────────
# schema sync (pure parts are unit-tested)
# ─────────────────────────────────────────────────────────────────────────────
def parse_schema_file(path: Path = SCHEMA_FILE) -> tuple[list[str], str]:
    """Return (olcAttributeTypes values, olcObjectClasses value) from the repo
    schema, each unfolded to a single normalised line."""
    attribute_types: list[str] = []
    objectclass = ""
    current_key, current_value = None, ""

    def flush():
        nonlocal objectclass, current_key, current_value
        if current_key is None:
            return
        value = re.sub(r"\s+", " ", current_value).strip()
        if current_key == "olcattributetypes":
            attribute_types.append(value)
        elif current_key == "olcobjectclasses":
            objectclass = value
        current_key, current_value = None, ""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith((" ", "\t")):            # LDIF continuation
            current_value += " " + raw_line.strip()
            continue
        flush()
        line = raw_line.strip()
        if line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        if key.lower() in ("olcattributetypes", "olcobjectclasses"):
            current_key, current_value = key.lower(), value.strip()
    flush()
    if not attribute_types or not objectclass:
        raise SystemExit(f"error: could not parse {path}")
    return attribute_types, objectclass


def build_schema_replace_ldif(schema_dn: str, attribute_types: list[str],
                              objectclass: str) -> str:
    """An idempotent cn=config modify: replace both value sets wholesale."""
    lines = [f"dn: {schema_dn}", "changetype: modify",
             "replace: olcAttributeTypes"]
    lines += [f"olcAttributeTypes: {value}" for value in attribute_types]
    lines += ["-", "replace: olcObjectClasses",
              f"olcObjectClasses: {objectclass}", ""]
    return "\n".join(lines)


def build_ldapi_command(install_type: str, container: str,
                        tool_args: list[str], use_sudo: bool) -> list[str]:
    """The ldapi:///+EXTERNAL command for the chosen installation type."""
    if install_type == "docker":
        return ["docker", "exec", "-i", container, *tool_args]
    command = list(tool_args)
    if use_sudo:
        command = ["sudo", *command]
    return command


def run_ldapi_tool(install_type: str, container: str, tool_args: list[str],
                   ldif: str | None, use_sudo: bool) -> subprocess.CompletedProcess:
    command = build_ldapi_command(install_type, container, tool_args, use_sudo)
    return subprocess.run(command, input=ldif, text=True, capture_output=True)


def parse_schema_dn_output(text: str) -> str | None:
    """First ``dn:`` line of an ldapsearch output (folded lines unfolded)."""
    unfolded = re.sub(r"\n[ \t]", "", text)
    for line in unfolded.splitlines():
        if line.lower().startswith("dn:"):
            return line.partition(":")[2].strip()
    return None


def discover_schema_dn(install_type: str, container: str,
                       use_sudo: bool) -> str | None:
    proc = run_ldapi_tool(
        install_type, container,
        ["ldapsearch", "-Y", "EXTERNAL", "-H", "ldapi:///", "-LLL",
         "-b", "cn=schema,cn=config", "(cn=*alirpunkto*)", "dn"],
        ldif=None, use_sudo=use_sudo)
    if proc.returncode != 0:
        hint = (" (root privileges are usually required on the host: "
                "re-run with --sudo)" if install_type == "host" else "")
        raise SystemExit(
            f"error: could not read cn=schema,cn=config on the "
            f"{install_type} target{hint}:\n{proc.stderr.strip()}")
    return parse_schema_dn_output(proc.stdout)


def update_schema(install_type: str, container: str, rep, use_sudo: bool,
                  dry_run: bool) -> None:
    attribute_types, objectclass = parse_schema_file()
    schema_dn = discover_schema_dn(install_type, container, use_sudo)
    if schema_dn:
        ldif = build_schema_replace_ldif(schema_dn, attribute_types,
                                         objectclass)
        tool = ["ldapmodify", "-Y", "EXTERNAL", "-H", "ldapi:///"]
        rep.info(f"schema entry found at {schema_dn}: replacing "
                 f"{len(attribute_types)} olcAttributeTypes and the "
                 f"olcObjectClasses (idempotent)")
    else:
        ldif = SCHEMA_FILE.read_text(encoding="utf-8")
        tool = ["ldapadd", "-Y", "EXTERNAL", "-H", "ldapi:///"]
        rep.info("no alirpunkto schema entry on the target: adding "
                 f"{SCHEMA_FILE.name} wholesale")
    if dry_run:
        rep.info("dry-run: schema LDIF NOT applied")
        return
    proc = run_ldapi_tool(install_type, container, tool, ldif, use_sudo)
    if proc.returncode != 0:
        raise SystemExit(f"error: schema update failed:\n{proc.stderr.strip()}")
    rep.info("schema update applied")


def verify_schema(remote, url: str, bind_dn: str, password: str, rep) -> None:
    """Re-read the subschema and confirm the modern attributes are known."""
    try:
        from ldap3 import Connection, Server
        server = Server(url, get_info="SCHEMA")
        conn = Connection(server, user=bind_dn, password=password,
                          auto_bind=True)
        conn.unbind()
        types = getattr(server.schema, "attribute_types", {}) or {}
        missing = [p for p in MODERN_SCHEMA_PROBES if p not in types]
        if missing:
            rep.warn(f"schema verification: still missing {', '.join(missing)}")
        else:
            rep.info("schema verification: all modern attributes present "
                     f"({', '.join(MODERN_SCHEMA_PROBES)})")
    except Exception as exc:                      # network target may differ
        rep.warn(f"schema verification skipped ({exc.__class__.__name__}: "
                 f"{exc})")


# ─────────────────────────────────────────────────────────────────────────────
# loading the seed file
# ─────────────────────────────────────────────────────────────────────────────
def parse_ldapadd_output(stdout: str, stderr: str) -> dict:
    added = len(re.findall(r"^adding new entry", stdout, re.M))
    existing = len(re.findall(r"Already exists", stdout + stderr))
    errors = [line for line in (stdout + "\n" + stderr).splitlines()
              if line.startswith("ldap_add:")
              and "Already exists" not in line]
    return {"added": added, "existing": existing, "errors": errors}


def load_seed(install_type: str, container: str, ldif_text: str, rep,
              use_sudo: bool, dry_run: bool) -> None:
    if dry_run:
        rep.info("dry-run: seed LDIF NOT loaded")
        return
    proc = run_ldapi_tool(
        install_type, container,
        ["ldapadd", "-c", "-Y", "EXTERNAL", "-H", "ldapi:///"],
        ldif=ldif_text, use_sudo=use_sudo)
    stats = parse_ldapadd_output(proc.stdout, proc.stderr)
    rep.info(f"load: {stats['added']} entr"
             f"{'y' if stats['added'] == 1 else 'ies'} added, "
             f"{stats['existing']} already existed")
    for line in stats["errors"]:
        rep.error(f"load: {line}")
    if stats["errors"]:
        raise SystemExit(2)


# ─────────────────────────────────────────────────────────────────────────────
# in-place password hashing (finding 1.3 on a live legacy directory)
# ─────────────────────────────────────────────────────────────────────────────
def update_passwords_in_place(conn, entries, rep, dry_run: bool) -> dict:
    """Replace cleartext userPassword values on the server with the {SSHA}
    hashes computed by the pipeline. Idempotent: hashed values are skipped."""
    from ldap3 import BASE, MODIFY_REPLACE

    stats = {"hashed": 0, "already_hashed": 0, "no_password": 0, "failed": 0}
    for entry in entries:
        if not (entry.has_objectclass("alirpunktoperson")
                or entry.has_objectclass("inetorgperson")):
            continue
        new_value = entry.first("userPassword")
        if not new_value or not is_hashed(new_value):
            continue                       # pipeline left nothing to push
        conn.search(entry.dn, "(objectClass=*)", search_scope=BASE,
                    attributes=["userPassword"])
        server_entry = conn.entries[0] if conn.entries else None
        current = (server_entry.userPassword.value
                   if server_entry is not None
                   and hasattr(server_entry, "userPassword") else None)
        if isinstance(current, bytes):
            current = current.decode("utf-8", "replace")
        if not current:
            stats["no_password"] += 1
            continue
        if is_hashed(current):
            stats["already_hashed"] += 1
            continue
        if dry_run:
            stats["hashed"] += 1
            rep.info(f"dry-run: would hash userPassword on {entry.dn}")
            continue
        if conn.modify(entry.dn,
                       {"userPassword": [(MODIFY_REPLACE, [new_value])]}):
            stats["hashed"] += 1
            rep.info(f"hashed userPassword on {entry.dn}")
        else:
            stats["failed"] += 1
            rep.error(f"could not hash userPassword on {entry.dn}: "
                      f"{conn.result}")
    rep.info(f"in-place passwords: {stats['hashed']} hashed, "
             f"{stats['already_hashed']} already hashed, "
             f"{stats['no_password']} without password, "
             f"{stats['failed']} failed")
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Extract a live AlirPunkto LDAP with the .env admin "
                    "credentials, adapt it (pipeline of "
                    "docker/migrate_ldap_legacy.py, {SSHA} hashing included) "
                    "and re-provision a docker or bare-metal installation.")
    # source (same knobs as migrate_ldap_legacy_remote)
    p.add_argument("--env-file", metavar="FILE",
                   default=str(REPO_ROOT / ".env"))
    p.add_argument("--url", metavar="URL")
    p.add_argument("--bind-dn", metavar="DN")
    p.add_argument("--base-dn", metavar="DN")
    p.add_argument("--password-env", metavar="NAME", default="LDAP_PASSWORD")
    p.add_argument("--ask-password", action="store_true")
    p.add_argument("--starttls", action="store_true")
    p.add_argument("--page-size", type=int, default=200)
    p.add_argument("--timeout", type=int, default=10)
    # outputs
    p.add_argument("--output", metavar="LDIF", default=SEED_FILE_NAME,
                   help=f"seed file to write (default: ./{SEED_FILE_NAME}, "
                        f"interchangeable with docker/{SEED_FILE_NAME})")
    p.add_argument("--install-into-docker", action="store_true",
                   help=f"also copy the seed file to docker/{SEED_FILE_NAME} "
                        f"for the next container initialisation")
    p.add_argument("--report", metavar="FILE")
    # target actions
    p.add_argument("--install-type", choices=("docker", "host"),
                   help="where --update-schema/--load act: the LDAP container "
                        "or the host's OpenLDAP")
    p.add_argument("--container", default=DEFAULT_CONTAINER,
                   help=f"LDAP container name for --install-type docker "
                        f"(default: {DEFAULT_CONTAINER})")
    p.add_argument("--sudo", action="store_true",
                   help="prefix host ldapi commands with sudo "
                        "(cn=config usually requires root)")
    p.add_argument("--update-schema", action="store_true",
                   help="force the target's alirpunkto schema to the repo's "
                        "current definitions (idempotent)")
    p.add_argument("--load", action="store_true",
                   help="recreate the extracted users on the target "
                        "(ldapadd -c: existing entries are harmless)")
    p.add_argument("--update-passwords-in-place", action="store_true",
                   help="hash cleartext userPassword values on the SOURCE "
                        "directory itself (finding 1.3), without reloading")
    p.add_argument("--dry-run", action="store_true",
                   help="compute and report everything, change nothing")
    # pipeline pass-throughs
    p.add_argument("--strict", action="store_true")
    p.add_argument("--keep-operational", action="store_true")
    p.add_argument("--keep-cleartext-passwords", action="store_true")
    args = p.parse_args(argv)

    if (args.update_schema or args.load) and not args.install_type:
        p.error("--update-schema/--load need --install-type {docker,host} "
                "so the admin chooses where to act")

    remote = load_remote()
    shared = remote.load_shared()
    rep = shared.Report()

    env = remote.read_env_file(Path(args.env_file))
    url = remote.build_server_url(env, args.url)
    bind_dn = remote.build_bind_dn(env, args.bind_dn)
    base_dn = args.base_dn or remote.cfg(env, "LDAP_BASE_DN")
    if not base_dn:
        raise SystemExit("error: no search base — set LDAP_BASE_DN in .env "
                         "or pass --base-dn")
    password = remote.resolve_password(env, args.password_env,
                                       args.ask_password)
    rep.info(f"source: {url} (bind as {bind_dn}); search base: {base_dn}")

    try:
        from ldap3.core.exceptions import LDAPException
    except ImportError:
        raise SystemExit("error: the ldap3 package is required "
                         "(run inside the application virtualenv)")
    try:
        conn = remote.connect(url, bind_dn, password,
                              starttls=args.starttls, timeout=args.timeout)
    except LDAPException as exc:
        raise SystemExit(f"error: could not bind to {url} as {bind_dn}: {exc}")

    try:
        entries = remote.fetch_entries(conn, base_dn, shared, rep,
                                       page_size=args.page_size)
        pipeline_args = SimpleNamespace(
            strict=args.strict, keep_operational=args.keep_operational,
            keep_cleartext_passwords=args.keep_cleartext_passwords)
        entries, supports_hashing = remote.transform_with_pipeline(
            shared, entries, rep, pipeline_args)

        if args.update_passwords_in_place:
            if not supports_hashing or args.keep_cleartext_passwords:
                rep.warn("--update-passwords-in-place skipped: no hashed "
                         "values available (pipeline predates 1.3 or "
                         "--keep-cleartext-passwords given)")
            else:
                update_passwords_in_place(conn, entries, rep, args.dry_run)
    finally:
        conn.unbind()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if args.keep_cleartext_passwords:
        pw_note = "kept verbatim (--keep-cleartext-passwords)"
    elif not supports_hashing:
        pw_note = "kept verbatim (shared pipeline predates the 1.3 patch)"
    else:
        pw_note = "cleartext values hashed to {SSHA}; existing hashes kept"
    header = (
        f"# AlirPunkto seed file generated by tools/ldap_provision.py\n"
        f"# Source: {url} (bind {bind_dn}) — Generated: {now}\n"
        f"# userPassword: {pw_note}.\n"
        f"# Interchangeable with docker/{SEED_FILE_NAME}: copy it there and\n"
        f"# the compose stack seeds the container with these users at init\n"
        f"# (start_ldap.sh loads it with `ldapadd -c`).\n"
    )
    ldif_text = shared.write_ldif(entries, header=header)
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(ldif_text)
    rep.info(f"seed file written: {args.output}")
    if args.install_into_docker:
        shutil.copyfile(args.output, DOCKER_SEED_PATH)
        rep.info(f"seed file installed: {DOCKER_SEED_PATH}")

    if args.update_schema:
        update_schema(args.install_type, args.container, rep, args.sudo,
                      args.dry_run)
        if not args.dry_run and args.install_type == "host":
            verify_schema(remote, url, bind_dn, password, rep)

    if args.load:
        load_seed(args.install_type, args.container, ldif_text, rep,
                  args.sudo, args.dry_run)

    report_text = rep.text() + (
        f"\n\nRESULT: {rep.errors} error(s), {rep.warnings} warning(s)\n")
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
