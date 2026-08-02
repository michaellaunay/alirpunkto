#!/usr/bin/env python3
"""
docker/generate_ldif.py — Generate initials_users.generated.ldif

Interface (eighth audit pass, 2026-08-02, §4/§5): the command line
carries ONLY the two file paths —

    generate_ldif.py TEMPLATE OUT

Every user-provided value — credentials, identities, roles, languages,
nationalities, everything — arrives on standard input as NUL-delimited
``NAME=VALUE`` records, because a command line is world-readable in
/proc/<pid>/cmdline for the whole life of the process, and pseudonyms,
logins, roles and nationalities are personal data just as much as
names and e-mail addresses. A pipe is visible to no one, touches no
disk, and handles any byte a shell variable can hold.

Required record names (missing OR EMPTY aborts with the list of what
is missing — a forgotten password must never silently become the
{SSHA} hash of the empty string):

  LDAP_BASE_DN
  ADMIN_UUID ADMIN_LOGIN ADMIN_PSEUDONYM ADMIN_EMAIL ADMIN_PW
  U1_UUID U1_ROLE U1_PSEUDONYM U1_FIRST U1_LAST U1_LANG U1_NAT
  U1_EMAIL U1_PW
  U2_UUID U2_ROLE U2_PSEUDONYM U2_FIRST U2_LAST U2_LANG U2_NAT
  U2_EMAIL U2_PW
  TODAY

Optional record names (absent means "not provided"):

  U1_SECOND_LANG U1_THIRD_LANG U1_BIRTHDATE U1_DESCRIPTION
  U2_SECOND_LANG U2_THIRD_LANG U2_BIRTHDATE U2_DESCRIPTION

Unknown record names abort too: a typo must fail loudly, not silently
drop a value. Passwords arrive in clear and are hashed to {SSHA} here;
no cleartext ever lands in the generated LDIF.

Fixes produced by this rewrite vs the previous sed/perl approach:
- Demo users (hardcoded UUIDs) are stripped from the template entirely.
- uniqueMember references to demo users are removed from all groups.
- The admin placeholder (00000000-...) is replaced by the real LDAP_ADMIN_OID.
- Group blocks are rebuilt cleanly with no duplicate or missing blank lines.
- Bootstrap users are added to the correct groups based on their role.
- No double "# Users" section in the output.
"""

import base64
import hashlib
import os
import re
import sys

# ── Input ────────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = (
    "LDAP_BASE_DN",
    "ADMIN_UUID", "ADMIN_LOGIN", "ADMIN_PSEUDONYM", "ADMIN_EMAIL",
    "ADMIN_PW",
    "U1_UUID", "U1_ROLE", "U1_PSEUDONYM", "U1_FIRST", "U1_LAST",
    "U1_LANG", "U1_NAT", "U1_EMAIL", "U1_PW",
    "U2_UUID", "U2_ROLE", "U2_PSEUDONYM", "U2_FIRST", "U2_LAST",
    "U2_LANG", "U2_NAT", "U2_EMAIL", "U2_PW",
    "TODAY",
)

OPTIONAL_FIELDS = (
    "U1_SECOND_LANG", "U1_THIRD_LANG", "U1_BIRTHDATE", "U1_DESCRIPTION",
    "U2_SECOND_LANG", "U2_THIRD_LANG", "U2_BIRTHDATE", "U2_DESCRIPTION",
)


def _fail(*lines):
    for line in lines:
        print(line, file=sys.stderr)
    sys.exit(1)


if len(sys.argv) != 3:
    _fail(f"Usage: {sys.argv[0]} TEMPLATE OUT",
          "Every user value is read from stdin as NUL-delimited",
          "NAME=VALUE records — see the module docstring. Nothing",
          "personal belongs on this command line.")

TEMPLATE, OUT = sys.argv[1], sys.argv[2]

_fields = {}
for _record in sys.stdin.buffer.read().split(b"\0"):
    if not _record:
        continue
    _name, _sep, _value = _record.partition(b"=")
    if not _sep:
        _fail("Malformed stdin record (no '='): field name "
              f"{_name.decode('utf-8', 'replace')!r}")
    _fields[_name.decode("utf-8")] = _value.decode("utf-8")

_unknown = sorted(set(_fields) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS))
if _unknown:
    _fail("Unknown stdin record name(s): " + ", ".join(_unknown),
          "A typo must fail loudly, not silently drop a value.")

# Eighth audit pass §5: empty counts as missing — a forgotten password
# variable used to become the valid {SSHA} hash of the empty string.
_missing = sorted(name for name in REQUIRED_FIELDS if not _fields.get(name))
if _missing:
    _fail("Missing or empty required field(s) on stdin: "
          + ", ".join(_missing))

(LDAP_BASE_DN,
 ADMIN_UUID, ADMIN_LOGIN, ADMIN_PSEUDONYM, ADMIN_EMAIL, ADMIN_PW,
 U1_UUID, U1_ROLE, U1_PSEUDONYM, U1_FIRST, U1_LAST, U1_LANG, U1_NAT,
 U1_EMAIL, U1_PW,
 U2_UUID, U2_ROLE, U2_PSEUDONYM, U2_FIRST, U2_LAST, U2_LANG, U2_NAT,
 U2_EMAIL, U2_PW,
 TODAY,
 ) = (_fields[name] for name in REQUIRED_FIELDS)

(U1_SECOND_LANG, U1_THIRD_LANG, U1_BIRTHDATE, U1_DESCRIPTION,
 U2_SECOND_LANG, U2_THIRD_LANG, U2_BIRTHDATE, U2_DESCRIPTION,
 ) = (_fields.get(name, "") for name in OPTIONAL_FIELDS)

# UUIDs of demo / placeholder users present in the template — strip them
DEMO_UUIDS = {
    "123a456a-bb78-9012-3456-7f890abc1d2e",
    "9eb02a19-b2b2-1bfb-9521-d7115b3a99d8",
}

# The old hardcoded admin placeholder — replaced by the real ADMIN_UUID
ADMIN_PLACEHOLDER = "00000000-0000-0000-0000-000000000000"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _ensure_ssha(pw: str) -> str:
    """Passwords reach this script in clear, through the single-use
    environment slots (sixth audit pass: init.sh no longer pre-hashes —
    its slappasswd fallback used to push the cleartext onto argv). They
    are always hashed here, so no cleartext ever lands in the generated
    LDIF (finding 1.3); an already-hashed {SCHEME} value is kept as-is."""
    if pw.startswith("{"):  # already an RFC-2307 scheme ({SSHA}, {CRYPT}, ...)
        return pw
    salt = os.urandom(8)
    # {SSHA} is SHA-1 by definition (OpenLDAP scheme) — same rationale
    # as the annotated make_ldap_password in secret_manager.py.
    digest = hashlib.sha1(
        pw.encode("utf-8") + salt).digest()  # nosec B324
    return "{SSHA}" + base64.b64encode(digest + salt).decode("ascii")


def role_to_groups(role: str) -> list[str]:
    groups = ["communityMembersGroup"]
    mapping = {
        "COOPERATOR":      ["cooperatorsGroup"],
        "ORDINARY_MEMBER": ["ordinaryMembersGroup"],
        "BOARD_MEMBER":    ["boardMembersGroup", "cooperatorsGroup"],
        "ADMINISTRATOR":   ["administratorsGroup", "cooperatorsGroup",
                            "communityMembersGroup"],
    }
    groups += mapping.get(role, [])
    return list(set(groups))  # deduplicate


def user_entry(uuid, pseudonym, first, last, lang, nat, email, pw, role, base_dn, today,
               second_lang=None, third_lang=None, birthdate=None, description=None):
    """cn is set to the pseudonym — this is the login identifier used by Pyramid
    (get_oid_from_pseudonym searches by cn, pseudonym_pattern enforces ASCII only)."""
    lines = [
        f"dn: uid={uuid},{base_dn}",
        "objectClass: top",
        "objectClass: inetOrgPerson",
        "objectClass: alirpunktoPerson",
        f"uid: {uuid}",
        f"sn: {last}",
        f"cn: {pseudonym}",
        f"employeeNumber: {uuid}",
        f"employeeType: {role}",
        "isActive: TRUE",
        f"preferredLanguage: {lang}",
    ]
    if second_lang:
        lines.append(f"secondLanguage: {second_lang}")
    if third_lang:
        lines.append(f"thirdLanguage: {third_lang}")
    lines += [
        f"givenName: {first}",
        f"nationality: {nat}",
        "cooperativeBehaviourMark: 0",
    ]
    if description:
        lines.append(f"description: {description}")
    if birthdate:
        lines.append(f"birthdate: {birthdate}")
    lines += [
        f"mail: {email}",
        f"userPassword: {_ensure_ssha(pw)}",
        "numberSharesOwned: 1",
        f"dateEndValidityYearlyContribution: {today}",
    ]
    lines += [f"uniqueMemberOf: cn={g},{base_dn}" for g in sorted(role_to_groups(role))]
    return "\n".join(lines)


def admin_entry(uuid, login, pseudonym, email, pw, base_dn, today):
    """Generate the LDAP admin entry using LDAP_ADMIN_OID as uid.
    cn is set to the pseudonym — the login identifier used by Pyramid."""
    lines = [
        f"dn: uid={uuid},{base_dn}",
        "objectClass: top",
        "objectClass: inetOrgPerson",
        "objectClass: alirpunktoPerson",
        f"uid: {uuid}",
        f"sn: {login}",
        f"cn: {pseudonym}",
        f"employeeNumber: {uuid}",
        "employeeType: ADMINISTRATOR",
        "isActive: TRUE",
        "preferredLanguage: fr",
        f"givenName: {login}",
        f"mail: {email}",
        f"userPassword: {_ensure_ssha(pw)}",
        "numberSharesOwned: 0",
        f"dateEndValidityYearlyContribution: {today}",
    ]
    lines += [f"uniqueMemberOf: cn={g},{base_dn}"
              for g in sorted(role_to_groups("ADMINISTRATOR"))]
    return "\n".join(lines)

# ── Read and normalise template ───────────────────────────────────────────────

with open(TEMPLATE) as f:
    raw = f.read()

# Replace placeholder base DN
raw = raw.replace("dc=alirpunkto,dc=org", LDAP_BASE_DN)

# Replace admin placeholder UUID with the real LDAP_ADMIN_OID everywhere
raw = raw.replace(ADMIN_PLACEHOLDER, ADMIN_UUID)

# Normalise the admin uniqueMember reference: the template uses
# "uid=ADMIN_UUID,cn=admin,dc=..." but entries use "uid=ADMIN_UUID,dc=..."
raw = re.sub(
    rf"uid={re.escape(ADMIN_UUID)},cn=[^,]+,({re.escape(LDAP_BASE_DN)})",
    rf"uid={ADMIN_UUID},\1",
    raw
)

# Normalise the admin uniqueMember reference: the template uses
# "uid=ADMIN_UUID,cn=admin,dc=..." but entries use "uid=ADMIN_UUID,dc=..."
# Replace any "uid={ADMIN_UUID},cn=admin,{base}" with "uid={ADMIN_UUID},{base}"
import re as _re
raw = _re.sub(
    rf"uid={re.escape(ADMIN_UUID)},cn=[^,]+,({re.escape(LDAP_BASE_DN)})",
    rf"uid={ADMIN_UUID},\1",
    raw
)

# Split into LDIF blocks separated by one or more blank lines
blocks = re.split(r"\n{2,}", raw.strip())

# ── Process blocks ────────────────────────────────────────────────────────────

group_blocks = []   # list of dicts: {cn, lines (without uniqueMember), members (set)}

for block in blocks:
    lines = block.strip().splitlines()
    if not lines:
        continue

    dn_line = lines[0]

    # Skip pure comment blocks (section headers like "# === Users ===")
    if all(l.startswith("#") or l.strip() == "" for l in lines):
        continue

    # Skip demo user entries
    if any(f"uid={u}" in dn_line for u in DEMO_UUIDS):
        continue

    # Group block: cn=...,dc=... without uid=
    if dn_line.startswith("dn:") and "cn=" in dn_line and "uid=" not in dn_line:
        non_member_lines = []
        members = set()
        for l in lines:
            if l.startswith("uniqueMember:"):
                ref = l.split(":", 1)[1].strip()
                # Drop demo user refs; keep admin (now substituted) and others
                is_demo = any(f"uid={u}" in ref for u in DEMO_UUIDS)
                if not is_demo:
                    members.add(ref)
            else:
                non_member_lines.append(l)
        cn_val = None
        for l in non_member_lines:
            if l.startswith("cn:"):
                cn_val = l.split(":", 1)[1].strip()
                break
        group_blocks.append({
            "cn": cn_val,
            "lines": non_member_lines,
            "members": members,
        })

# ── Add admin to its groups ───────────────────────────────────────────────────

ADMIN_DN = f"uid={ADMIN_UUID},{LDAP_BASE_DN}"
for gb in group_blocks:
    if gb["cn"] in role_to_groups("ADMINISTRATOR"):
        gb["members"].add(ADMIN_DN)

# ── Add bootstrap users to their groups ──────────────────────────────────────

for uuid, role in [(U1_UUID, U1_ROLE), (U2_UUID, U2_ROLE)]:
    dn = f"uid={uuid},{LDAP_BASE_DN}"
    for gb in group_blocks:
        if gb["cn"] in role_to_groups(role):
            gb["members"].add(dn)

# ── Write output ──────────────────────────────────────────────────────────────

out_parts = ["# =====================\n# Groups\n# ====================="]

for gb in group_blocks:
    block_lines = gb["lines"][:]
    # Admin DN first, then others in stable alphabetical order
    for m in sorted(gb["members"],
                    key=lambda x: (0 if ADMIN_UUID in x else 1, x)):
        block_lines.append(f"uniqueMember: {m}")
    out_parts.append("\n".join(block_lines))

out_parts.append("# =====================\n# Users\n# =====================")

# Admin entry first
out_parts.append(admin_entry(ADMIN_UUID, ADMIN_LOGIN, ADMIN_PSEUDONYM, ADMIN_EMAIL, ADMIN_PW,
                              LDAP_BASE_DN, TODAY))

# Bootstrap users
for (uuid, pseudonym, first, last, lang, nat, email, pw, role,
         second_lang, third_lang, birthdate, description) in [
    (U1_UUID, U1_PSEUDONYM, U1_FIRST, U1_LAST, U1_LANG, U1_NAT, U1_EMAIL, U1_PW, U1_ROLE,
     U1_SECOND_LANG, U1_THIRD_LANG, U1_BIRTHDATE, U1_DESCRIPTION),
    (U2_UUID, U2_PSEUDONYM, U2_FIRST, U2_LAST, U2_LANG, U2_NAT, U2_EMAIL, U2_PW, U2_ROLE,
     U2_SECOND_LANG, U2_THIRD_LANG, U2_BIRTHDATE, U2_DESCRIPTION),
]:
    out_parts.append(user_entry(uuid, pseudonym, first, last, lang, nat, email, pw, role,
                                LDAP_BASE_DN, TODAY,
                                second_lang=second_lang or None,
                                third_lang=third_lang or None,
                                birthdate=birthdate or None,
                                description=description or None))

# Revised audit: the LDIF carries identities and password hashes — it is
# born unreadable to anyone but its owner.
_previous_umask = os.umask(0o077)
try:
    with open(OUT, "w") as f:
        f.write("\n\n".join(out_parts) + "\n")

finally:
    os.umask(_previous_umask)
os.chmod(OUT, 0o600)
print(f"[generate_ldif] Written {OUT}")
