#!/usr/bin/env python3
"""
docker/generate_ldif.py — Generate initials_users.generated.ldif

Called by docker/init.sh with positional arguments:
  template ldif_out base_dn
  admin_uuid admin_login admin_pseudonym admin_email admin_pw
  user1_uuid user1_role user1_pseudonym user1_first user1_last user1_lang user1_nat user1_email user1_pw
  user2_uuid user2_role user2_pseudonym user2_first user2_last user2_lang user2_nat user2_email user2_pw
  today

Fixes produced by this rewrite vs the previous sed/perl approach:
- Demo users (hardcoded UUIDs) are stripped from the template entirely.
- uniqueMember references to demo users are removed from all groups.
- The admin placeholder (00000000-...) is replaced by the real LDAP_ADMIN_OID.
- Group blocks are rebuilt cleanly with no duplicate or missing blank lines.
- Bootstrap users are added to the correct groups based on their role.
- No double "# Users" section in the output.
"""

import re
import sys

# ── Arguments ────────────────────────────────────────────────────────────────

if len(sys.argv) != 27:
    print(f"Usage: {sys.argv[0]} template out base_dn "
          "admin_uuid admin_login admin_pseudonym admin_email admin_pw "
          "u1_uuid u1_role u1_pseudonym u1_first u1_last u1_lang u1_nat u1_email u1_pw "
          "u2_uuid u2_role u2_pseudonym u2_first u2_last u2_lang u2_nat u2_email u2_pw "
          "today", file=sys.stderr)
    print(f"Received {len(sys.argv) - 1} arguments:", file=sys.stderr)
    for i, a in enumerate(sys.argv[1:], 1):
        print(f"  [{i:02d}] {repr(a)}", file=sys.stderr)
    sys.exit(1)

(TEMPLATE, OUT, LDAP_BASE_DN,
 ADMIN_UUID, ADMIN_LOGIN, ADMIN_PSEUDONYM, ADMIN_EMAIL, ADMIN_PW,
 U1_UUID, U1_ROLE, U1_PSEUDONYM, U1_FIRST, U1_LAST, U1_LANG, U1_NAT, U1_EMAIL, U1_PW,
 U2_UUID, U2_ROLE, U2_PSEUDONYM, U2_FIRST, U2_LAST, U2_LANG, U2_NAT, U2_EMAIL, U2_PW,
 TODAY) = sys.argv[1:]

# UUIDs of demo / placeholder users present in the template — strip them
DEMO_UUIDS = {
    "123a456a-bb78-9012-3456-7f890abc1d2e",
    "9eb02a19-b2b2-1bfb-9521-d7115b3a99d8",
}

# The old hardcoded admin placeholder — replaced by the real ADMIN_UUID
ADMIN_PLACEHOLDER = "00000000-0000-0000-0000-000000000000"

# ── Helpers ───────────────────────────────────────────────────────────────────

def role_to_groups(role: str) -> list[str]:
    groups = ["communityMembersGroup"]
    mapping = {
        "COPERATOR":       ["cooperatorsGroup"],
        "ORDINARY_MEMBER": ["ordinaryMembersGroup"],
        "BOARD_MEMBER":    ["boardMembersGroup", "cooperatorsGroup"],
        "ADMINISTRATOR":   ["administratorsGroup", "cooperatorsGroup",
                            "communityMembersGroup"],
    }
    groups += mapping.get(role, [])
    return list(set(groups))  # deduplicate


def user_entry(uuid, pseudonym, first, last, lang, nat, email, pw, role, base_dn, today):
    """cn is set to the pseudonym — this is the login identifier used by Pyramid
    (get_oid_from_pseudonym searches by cn, pseudonym_pattern enforces ASCII only)."""
    return "\n".join([
        f"dn: uid={uuid},{base_dn}",
        "objectClass: inetOrgPerson",
        "objectClass: alirpunktoPerson",
        f"uid: {uuid}",
        f"sn: {last}",
        f"cn: {pseudonym}",
        f"employeeNumber: {uuid}",
        f"employeeType: {role}",
        "isActive: TRUE",
        f"preferredLanguage: {lang}",
        f"givenName: {first}",
        f"nationality: {nat}",
        "cooperativeBehaviourMark: 0",
        f"mail: {email}",
        f"userPassword: {pw}",
        "numberSharesOwned: 1",
        f"dateEndValidityYearlyContribution: {today}",
    ])


def admin_entry(uuid, login, pseudonym, email, pw, base_dn, today):
    """Generate the LDAP admin entry using LDAP_ADMIN_OID as uid.
    cn is set to the pseudonym — the login identifier used by Pyramid."""
    return "\n".join([
        f"dn: uid={uuid},{base_dn}",
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
        f"userPassword: {pw}",
        "numberSharesOwned: 0",
        f"dateEndValidityYearlyContribution: {today}",
    ])

# ── Read and normalise template ───────────────────────────────────────────────

with open(TEMPLATE) as f:
    raw = f.read()

# Replace placeholder base DN
raw = raw.replace("dc=alirpunkto,dc=org", LDAP_BASE_DN)

# Replace admin placeholder UUID with the real LDAP_ADMIN_OID everywhere
raw = raw.replace(ADMIN_PLACEHOLDER, ADMIN_UUID)

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
for (uuid, pseudonym, first, last, lang, nat, email, pw, role) in [
    (U1_UUID, U1_PSEUDONYM, U1_FIRST, U1_LAST, U1_LANG, U1_NAT, U1_EMAIL, U1_PW, U1_ROLE),
    (U2_UUID, U2_PSEUDONYM, U2_FIRST, U2_LAST, U2_LANG, U2_NAT, U2_EMAIL, U2_PW, U2_ROLE),
]:
    out_parts.append(user_entry(uuid, pseudonym, first, last, lang, nat, email, pw, role,
                                LDAP_BASE_DN, TODAY))

with open(OUT, "w") as f:
    f.write("\n\n".join(out_parts) + "\n")

print(f"[generate_ldif] Written {OUT}")
