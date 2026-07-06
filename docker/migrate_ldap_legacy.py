#!/usr/bin/env python3
"""
migrate_ldap_legacy.py — export an old AlirPunkto LDAP tree as LDIF and adapt it
to the schema and field conventions of the *current* version.

WHAT THIS SCRIPT DOES (first migration step)
--------------------------------------------
1. Obtains the source LDIF, either from a running old slapd (via `slapcat`,
   directly or inside a Docker container) or from an already-exported file.
2. Normalises the fields that drifted between ~December 2025 and now:
     * the `coperator -> cooperator` typo, in group names AND in `employeeType`;
     * `employeeType` -> a valid current MemberTypes name
       (ADMINISTRATOR / ORDINARY / COOPERATOR / PROVIDER), tolerating case,
       role-style values and the old enum "*_value" form;
     * obsolete / renamed groups (e.g. `communityGroup -> communityMembersGroup`),
       merging into the target group DN when it already exists;
     * `isActive` -> a canonical LDAP boolean (TRUE / FALSE);
     * `gn` -> `givenName` (same attribute; defensive for hand-written LDIF).
3. Checks consistency: required attributes on person entries, valid
   `employeeType`, referential integrity of `uniqueMemberOf` / `uniqueMember`,
   duplicate DNs.
4. Writes an adapted LDIF ready for `slapadd`/`ldapadd` into the current stack,
   and prints a human-readable report.

OUT OF SCOPE HERE (done in a later step)
----------------------------------------
The LDAP 1.3 migration and the conversion of *cleartext* `userPassword` values
to hashed ones. This script does NOT modify passwords. It only INVENTORIES them
(cleartext vs hashed) so the next step knows exactly what to convert.

The transformation rules live in the TRANSFORM CONFIG section below and are meant
to be extended in the next step.

Usage examples
--------------
    # From an already-exported LDIF:
    ./migrate_ldap_legacy.py --input old.ldif --output adapted.ldif

    # Export from a running old container, then adapt in one go:
    ./migrate_ldap_legacy.py --slapcat-container old-alirpunkto-ldap \
        --output adapted.ldif --report report.txt

    # From a host slapd (needs privileges to read the config/db):
    ./migrate_ldap_legacy.py --slapcat-local --slapcat-args "-n 1" \
        --output adapted.ldif

    # Fail (non-zero exit) on any inconsistency instead of warning:
    ./migrate_ldap_legacy.py --input old.ldif --output adapted.ldif --strict
"""
from __future__ import annotations

import argparse
import base64
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

# ─────────────────────────────────────────────────────────────────────────────
# TRANSFORM CONFIG  (edit here to extend the migration)
# ─────────────────────────────────────────────────────────────────────────────

# Canonical member types = names of MemberTypes in alirpunkto/models/member.py.
# The current app reads employeeType with MemberTypes[value], so the stored
# value MUST be exactly one of these names.
VALID_EMPLOYEE_TYPES = {"ADMINISTRATOR", "ORDINARY", "COOPERATOR", "PROVIDER"}

# How to normalise a legacy employeeType (compared upper-cased and stripped).
# Roles that are not member types (BOARD_MEMBER, MEDIATION_...) are mapped to the
# type a member with that role actually has (a board/council member IS a
# cooperator) and flagged in the report so the choice can be reviewed.
EMPLOYEE_TYPE_MAP = {
    # typo fixed on 2026-05-01 (coperator -> cooperator)
    "COPERATOR": "COOPERATOR",
    "COPERATEUR": "COOPERATOR",
    "COOPERATEUR": "COOPERATOR",
    "COOPERATOR": "COOPERATOR",
    # role-style values that ended up in employeeType
    "ORDINARY_MEMBER": "ORDINARY",
    "ORDINARYMEMBER": "ORDINARY",
    "BOARD_MEMBER": "COOPERATOR",
    "BOARD": "COOPERATOR",
    "MEDIATION_ARBITRATION_COUNCIL": "COOPERATOR",
    "MEDIATIONARBITRATIONCOUNCIL": "COOPERATOR",
    # plain synonyms / case
    "ORDINARY": "ORDINARY",
    "ADMINISTRATOR": "ADMINISTRATOR",
    "ADMIN": "ADMINISTRATOR",
    "PROVIDER": "PROVIDER",
    # old enum "*_value" form (MemberTypes values)
    "MEMBER_TYPES_ADMINISTRATOR_VALUE": "ADMINISTRATOR",
    "MEMBER_TYPES_ORDINARY_VALUE": "ORDINARY",
    "MEMBER_TYPES_COOPERATOR_VALUE": "COOPERATOR",
    "MEMBER_TYPES_COPERATOR_VALUE": "COOPERATOR",
    "MEMBER_TYPES_PROVIDER_VALUE": "PROVIDER",
}

# employeeType chosen for entries that have none / an unrecognised value
# (mirrors the app's own fallback in update_member_from_ldap). In --strict mode
# an unrecognised value is a hard error instead.
EMPLOYEE_TYPE_FALLBACK = "ORDINARY"

# Group cn renames (old -> new). Applied to the group's own DN/cn and to every
# DN-valued reference (uniqueMemberOf on members, uniqueMember on groups). If the
# new DN already exists, the two entries are merged (union of uniqueMember).
GROUP_RENAMES = {
    "coperatorsGroup": "cooperatorsGroup",   # 2026-05-01 typo fix
    "communityGroup": "communityMembersGroup",  # superseded name
}

# Attributes whose *values* are DNs and must follow group renames.
DN_VALUED_ATTRS = {
    "uniquememberof", "uniquemember", "member", "owner", "roleoccupant",
    "seealso", "manager", "secretary",
}

# When two entries collapse onto the same DN after a group rename, only these
# (genuinely multi-valued) attributes are unioned; single-valued ones such as
# cn/description keep the surviving entry's value.
MERGE_UNION_ATTRS = {"uniquemember", "member", "memberuid"}

# Attribute aliases to canonicalise on output (same underlying LDAP attribute).
ATTR_RENAMES = {"gn": "givenName"}

# Operational / server-generated attributes that slapcat emits and that a fresh
# load should regenerate. Stripped by default (kept with --keep-operational).
OPERATIONAL_ATTRS = {
    "structuralobjectclass", "entryuuid", "entrycsn", "creatorsname",
    "createtimestamp", "modifiersname", "modifytimestamp", "entrydn",
    "subschemasubentry", "hassubordinates", "contextcsn", "pwdchangedtime",
    "pwdfailuretime", "pwdaccountlockedtime",
}

# DN suffixes that are not application data (config / monitor backends). Dropped.
SKIP_DN_SUFFIXES = ("cn=config", "cn=subschema", "cn=monitor")

# Person entries are recognised by this objectClass.
PERSON_OBJECTCLASS = "alirpunktoperson"

# Required attributes on a person entry (current write path in utils.py).
REQUIRED_PERSON_ATTRS = ["uid", "cn", "sn", "mail", "employeeType", "objectClass"]

# Known userPassword hash scheme tags (RFC 2307 style). Anything else is
# considered cleartext and reported for the later password-migration step.
KNOWN_PASSWORD_SCHEMES = (
    "{SSHA}", "{SHA}", "{SSHA256}", "{SHA256}", "{SSHA512}", "{SHA512}",
    "{SMD5}", "{MD5}", "{CRYPT}", "{ARGON2}", "{PBKDF2}", "{PBKDF2-SHA1}",
    "{PBKDF2-SHA256}", "{PBKDF2-SHA512}", "{SCRAM-SHA-1}",
)

# ─────────────────────────────────────────────────────────────────────────────
# LDIF parsing / serialising
# ─────────────────────────────────────────────────────────────────────────────


# Internal markers for values that must survive round-trip untouched.
MARK_B64 = "\x00B64\x00"
MARK_URL = "\x00URL\x00"


@dataclass
class Entry:
    """One LDIF entry: a DN plus ordered (attr, value) pairs (values are str)."""
    dn: str
    attrs: list[tuple[str, str]] = field(default_factory=list)

    def get(self, name: str) -> list[str]:
        low = name.lower()
        return [v for (a, v) in self.attrs if a.lower() == low]

    def first(self, name: str) -> str | None:
        vals = self.get(name)
        return vals[0] if vals else None

    def has_objectclass(self, oc: str) -> bool:
        return any(v.lower() == oc for v in self.get("objectClass"))


def _decode_value(raw: str) -> str:
    """Return the textual value of a raw LDIF value token (handles base64 `::`)."""
    if raw.startswith(":"):  # ":: base64" already stripped of first ':'
        b64 = raw[1:].strip()
        try:
            return base64.b64decode(b64).decode("utf-8")
        except Exception:
            # keep the raw base64 so nothing is lost; it round-trips as-is
            return MARK_B64 + b64
    if raw.startswith("<"):  # ":< file://..." URL reference — keep marker
        return MARK_URL + raw[1:].strip()
    return raw[1:].lstrip(" ") if raw.startswith(" ") else raw.lstrip(" ")


def parse_ldif(text: str) -> list[Entry]:
    """Parse LDIF text into Entry objects, unfolding continuation lines."""
    # 1) unfold: a line starting with a single space continues the previous one
    unfolded: list[str] = []
    for line in text.splitlines():
        if line.startswith(" ") and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)

    entries: list[Entry] = []
    cur: Entry | None = None
    for line in unfolded:
        if not line.strip():          # blank line ends an entry
            if cur is not None:
                entries.append(cur)
                cur = None
            continue
        if line.lstrip().startswith("#"):     # comment
            continue
        if line.startswith("version:"):        # LDIF version header
            continue
        if ":" not in line:
            continue
        name, _, rest = line.partition(":")
        value = _decode_value(rest)
        if name.lower() == "dn":
            cur = Entry(dn=value)
        elif cur is not None:
            cur.attrs.append((name, value))
    if cur is not None:
        entries.append(cur)
    return entries


def _needs_base64(value: str) -> bool:
    if value.startswith((MARK_B64, MARK_URL)):
        return False  # handled specially by the writer
    if value == "" or value[0] in " :<" or value.endswith(" "):
        return True
    return any(ord(c) > 127 or ord(c) < 32 for c in value)


def _fold(line: str, width: int = 76) -> str:
    if len(line) <= width:
        return line
    out = [line[:width]]
    rest = line[width:]
    while rest:
        out.append(" " + rest[: width - 1])
        rest = rest[width - 1:]
    return "\n".join(out)


def format_attr(name: str, value: str) -> str:
    if value.startswith(MARK_B64):
        return _fold(f"{name}:: {value[len(MARK_B64):]}")
    if value.startswith(MARK_URL):
        return f"{name}:< {value[len(MARK_URL):]}"
    if _needs_base64(value):
        enc = base64.b64encode(value.encode("utf-8")).decode("ascii")
        return _fold(f"{name}:: {enc}")
    return _fold(f"{name}: {value}")


def write_ldif(entries: list[Entry], header: str = "") -> str:
    parts: list[str] = []
    if header:
        parts.append(header.rstrip() + "\n")
    for e in entries:
        block = [format_attr("dn", e.dn)]
        block += [format_attr(a, v) for (a, v) in e.attrs]
        parts.append("\n".join(block) + "\n")
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Transformations
# ─────────────────────────────────────────────────────────────────────────────


class Report:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.errors = 0
        self.warnings = 0

    def info(self, msg: str) -> None:
        self.lines.append(f"[info]  {msg}")

    def warn(self, msg: str) -> None:
        self.warnings += 1
        self.lines.append(f"[WARN]  {msg}")

    def error(self, msg: str) -> None:
        self.errors += 1
        self.lines.append(f"[ERROR] {msg}")

    def text(self) -> str:
        return "\n".join(self.lines)


def _split_rdns(dn: str) -> list[str]:
    # naive split on unescaped commas (AlirPunkto DNs use no escaped commas)
    return [p.strip() for p in dn.split(",")]


def _rewrite_group_dn(dn: str, rep: Report, where: str) -> str:
    rdns = _split_rdns(dn)
    changed = False
    for i, rdn in enumerate(rdns):
        if "=" not in rdn:
            continue
        attr, _, val = rdn.partition("=")
        if attr.strip().lower() == "cn" and val.strip() in GROUP_RENAMES:
            new = GROUP_RENAMES[val.strip()]
            rdns[i] = f"{attr.strip()}={new}"
            changed = True
    if changed:
        new_dn = ",".join(rdns)
        rep.info(f"group rename in {where}: {dn}  ->  {new_dn}")
        return new_dn
    return dn


def normalise_employee_type(value: str, dn: str, rep: Report, strict: bool) -> str:
    key = value.strip().upper()
    if key in VALID_EMPLOYEE_TYPES and value == key:
        return value  # already canonical
    if key in VALID_EMPLOYEE_TYPES:
        rep.info(f"employeeType case fix on {dn}: {value!r} -> {key!r}")
        return key
    if key in EMPLOYEE_TYPE_MAP:
        mapped = EMPLOYEE_TYPE_MAP[key]
        rep.info(f"employeeType mapped on {dn}: {value!r} -> {mapped!r}")
        return mapped
    # unrecognised
    if strict:
        rep.error(f"unrecognised employeeType {value!r} on {dn}")
        return value
    rep.warn(
        f"unrecognised employeeType {value!r} on {dn}: "
        f"defaulting to {EMPLOYEE_TYPE_FALLBACK}"
    )
    return EMPLOYEE_TYPE_FALLBACK


def normalise_bool(value: str) -> str | None:
    v = value.strip().lower()
    if v in ("true", "t", "yes", "y", "1"):
        return "TRUE"
    if v in ("false", "f", "no", "n", "0"):
        return "FALSE"
    return None


def password_scheme(value: str) -> str:
    """Return the hash scheme tag, or 'CLEARTEXT'."""
    v = value
    if v.startswith("\x00B64\x00"):
        try:
            v = base64.b64decode(v[len(MARK_B64):]).decode("utf-8", "replace")
        except Exception:
            return "UNKNOWN"
    up = v.upper()
    for scheme in KNOWN_PASSWORD_SCHEMES:
        if up.startswith(scheme):
            return scheme.strip("{}")
    return "CLEARTEXT"


def transform(entries: list[Entry], rep: Report, strict: bool,
              keep_operational: bool) -> list[Entry]:
    kept: list[Entry] = []
    cleartext_dns: list[str] = []
    hashed = 0

    for e in entries:
        low_dn = e.dn.lower()
        if any(low_dn.endswith(sfx) or f",{sfx}" in low_dn for sfx in SKIP_DN_SUFFIXES):
            rep.info(f"skip non-application entry: {e.dn}")
            continue

        # rewrite the entry's own DN if it is a renamed group
        e.dn = _rewrite_group_dn(e.dn, rep, "dn")

        is_person = e.has_objectclass(PERSON_OBJECTCLASS)
        new_attrs: list[tuple[str, str]] = []
        seen_dn_values: set[tuple[str, str]] = set()

        for name, value in e.attrs:
            low = name.lower()

            if not keep_operational and low in OPERATIONAL_ATTRS:
                continue

            # attribute alias canonicalisation (gn -> givenName)
            if low in ATTR_RENAMES:
                name = ATTR_RENAMES[low]
                low = name.lower()

            # employeeType normalisation
            if low == "employeetype":
                value = normalise_employee_type(value, e.dn, rep, strict)

            # a group's own cn must follow the DN rename (RDN attribute rule)
            elif low == "cn" and value in GROUP_RENAMES:
                new = GROUP_RENAMES[value]
                rep.info(f"group cn rename on {e.dn}: {value!r} -> {new!r}")
                value = new

            # isActive -> canonical boolean
            elif low == "isactive":
                canon = normalise_bool(value)
                if canon is None:
                    rep.warn(f"isActive value {value!r} on {e.dn} not boolean; kept as-is")
                elif canon != value:
                    rep.info(f"isActive normalised on {e.dn}: {value!r} -> {canon}")
                    value = canon

            # DN-valued attributes follow group renames (+ dedupe)
            elif low in DN_VALUED_ATTRS:
                value = _rewrite_group_dn(value, rep, name)
                dedup_key = (low, value.lower())
                if dedup_key in seen_dn_values:
                    rep.info(f"drop duplicate {name} on {e.dn}: {value}")
                    continue
                seen_dn_values.add(dedup_key)

            # password inventory (never modified here)
            elif low == "userpassword":
                scheme = password_scheme(value)
                if scheme == "CLEARTEXT":
                    cleartext_dns.append(e.dn)
                else:
                    hashed += 1

            new_attrs.append((name, value))

        e.attrs = new_attrs
        kept.append(e)

    # ── merge entries whose DN collided after a group rename ──────────────────
    merged: dict[str, Entry] = {}
    order: list[str] = []
    for e in kept:
        key = e.dn.lower()
        if key in merged:
            tgt = merged[key]
            rep.warn(f"duplicate DN after rename, merging into one entry: {e.dn}")
            existing = {(a.lower(), v.lower()) for (a, v) in tgt.attrs}
            for a, v in e.attrs:
                if a.lower() not in MERGE_UNION_ATTRS:
                    continue  # keep the surviving entry's cn/description/etc.
                if (a.lower(), v.lower()) not in existing:
                    tgt.attrs.append((a, v))
                    existing.add((a.lower(), v.lower()))
        else:
            merged[key] = e
            order.append(key)
    result = [merged[k] for k in order]

    # password inventory summary
    rep.info("")
    rep.info(f"userPassword inventory: {hashed} hashed, {len(cleartext_dns)} cleartext")
    if cleartext_dns:
        rep.warn(
            f"{len(cleartext_dns)} account(s) store a CLEARTEXT password "
            f"(to be converted in the password-migration step):"
        )
        for dn in cleartext_dns:
            rep.lines.append(f"          - {dn}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Consistency checks
# ─────────────────────────────────────────────────────────────────────────────


def check_consistency(entries: list[Entry], rep: Report) -> None:
    dns = {e.dn.lower() for e in entries}

    # duplicate DNs (should be none after the merge pass)
    seen: set[str] = set()
    for e in entries:
        k = e.dn.lower()
        if k in seen:
            rep.error(f"duplicate DN remains: {e.dn}")
        seen.add(k)

    persons = 0
    groups = 0
    for e in entries:
        if e.has_objectclass(PERSON_OBJECTCLASS):
            persons += 1
            for attr in REQUIRED_PERSON_ATTRS:
                if not e.get(attr):
                    rep.error(f"person {e.dn} misses required attribute '{attr}'")
            et = e.first("employeeType")
            if et and et not in VALID_EMPLOYEE_TYPES:
                rep.error(f"person {e.dn} has invalid employeeType {et!r} after adaptation")
            # every group this member claims must exist
            for g in e.get("uniqueMemberOf"):
                if g.lower() not in dns:
                    rep.warn(f"{e.dn}: uniqueMemberOf points to missing group {g}")
        if e.has_objectclass("groupofuniquenames") or e.has_objectclass("groupofnames"):
            groups += 1
            for m in e.get("uniqueMember") + e.get("member"):
                # allow the bare admin placeholder DNs; only flag app-user DNs
                if m.lower() not in dns and m.lower().startswith("uid="):
                    rep.warn(f"group {e.dn}: member points to missing entry {m}")

    rep.info("")
    rep.info(f"summary: {len(entries)} entries ({persons} persons, {groups} groups)")


# ─────────────────────────────────────────────────────────────────────────────
# Source acquisition (slapcat) + main
# ─────────────────────────────────────────────────────────────────────────────


def run_slapcat(container: str | None, local: bool, args: str) -> str:
    slapcat_args = args.split() if args else ["-n", "1"]
    if container:
        cmd = ["docker", "exec", container, "slapcat", *slapcat_args]
    elif local:
        cmd = ["slapcat", *slapcat_args]
    else:
        raise ValueError("no slapcat source selected")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"slapcat failed (exit {proc.returncode})")
    return proc.stdout


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Export and adapt a legacy AlirPunkto LDAP tree to the current schema.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = p.add_mutually_exclusive_group()
    src.add_argument("--input", metavar="LDIF", help="read the source LDIF from a file")
    src.add_argument("--slapcat-container", metavar="NAME",
                     help="run `docker exec NAME slapcat` to get the source")
    src.add_argument("--slapcat-local", action="store_true",
                     help="run `slapcat` on this host to get the source")
    p.add_argument("--slapcat-args", default="-n 1",
                   help="arguments passed to slapcat (default: '-n 1' = data DB)")
    p.add_argument("--output", metavar="LDIF", help="adapted LDIF (default: stdout)")
    p.add_argument("--report", metavar="FILE", help="report file (default: stderr)")
    p.add_argument("--strict", action="store_true",
                   help="treat unrecognised employeeType / issues as errors (non-zero exit)")
    p.add_argument("--keep-operational", action="store_true",
                   help="keep server-generated operational attributes")
    args = p.parse_args(argv)

    if args.input:
        with open(args.input, encoding="utf-8") as fh:
            source = fh.read()
    elif args.slapcat_container or args.slapcat_local:
        source = run_slapcat(args.slapcat_container, args.slapcat_local, args.slapcat_args)
    else:
        source = sys.stdin.read()

    rep = Report()
    entries = parse_ldif(source)
    rep.info(f"parsed {len(entries)} entries from source")

    entries = transform(entries, rep, strict=args.strict,
                        keep_operational=args.keep_operational)
    check_consistency(entries, rep)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = (
        f"# Adapted from a legacy AlirPunkto LDAP export by migrate_ldap_legacy.py\n"
        f"# Generated: {now}\n"
        f"# NOTE: userPassword values are preserved verbatim (password migration is a\n"
        f"#       separate step). Review the report before loading with slapadd/ldapadd.\n"
    )
    out = write_ldif(entries, header=header)

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
