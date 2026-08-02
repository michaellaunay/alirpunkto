# External repository audit (ChatGPT), eighth pass — 2 August 2026

**Provenance.** Eighth pass of the external static audit (ChatGPT, at
Michaël Launay's request), on commit `2bc56291` (LDIF transport through
environment slots and group reconciliation); previous pass (the
seventh, graded 8.5 on `2c53ef8b`, text not transmitted). Proposed
overall grade: **8.6/10**. Across the passes: 6.5 → 6.9 → 6.7 → 7.1 →
7.8 → 8.2 → 8.5 → 8.6. The full text is reproduced in the second part
of this document (translated from the French original).

**Status.** Counter-reviewed the same day: **the four findings raised
against the 0074 train are grounded**, and the opening reproach — the
commit message wrongly claimed "this closes P2" — is owned. They are
fixed by patch 0076 (merged as `3fafc121`). Calendar note: the "Image"
section of the earlier findings (§11) describes the state *before* the
merge of the image-finishing train (0075, `72e65db2`), which already
covers the application wheel, `--only-binary`, the reduced context and
the APT snapshot mechanism.

## Counter-review

- **§4, personal data in `argv`**: grounded. The 0074 train had judged
  pseudonyms, roles, languages and nationalities to be "identifiers,
  not personal data" — a misjudgement, nationality above all. Fix in
  0076: the positional interface disappears for every user value; the
  command line carries only the two file paths, all values cross as
  NUL-delimited `NAME=VALUE` records on the generator's standard input
  (a pipe is visible to no one, touches no disk, carries any byte).
- **§5, missing password variable**: grounded — and severe on direct
  misuse of the generator: `os.environ.pop(name, "")` turned a
  forgotten password into the *valid* `{SSHA}` hash of the empty
  string. Fix in 0076: a required field that is missing **or empty**
  aborts the generator with the list of missing names, before anything
  is written; an unknown record name aborts too (a typo must fail
  loudly).
- **§7, "fail-closed" not enforced**: grounded — the write order was
  right but `_checked_modify`'s return value was ignored: the second
  write followed a failed first one. Fix in 0076: the second write of
  every pair is conditional (member-side grant only once the group
  side carries the record; group-side revocation only once the member
  side is clean).
- **§8, the union resurrects a stale state**: grounded — the
  resurrection scenario for a half-revoked Board/MAC role or a
  half-lifted sanction was real ("repaired in the wrong direction").
  Fix in 0076: the **member** side — what the application reads — is
  the authoritative current state; a lagging group-side record
  converges down. The resulting asymmetry is deliberate and
  documented: a grant whose member-side write failed is rolled back on
  the next pass (losing a grant is safe and re-runnable), a revocation
  converges until both sides are clean.
- **§9, scan cost** (members × groups): grounded, retained as a P3
  optimisation (groups loaded once, inverse table, paged search).
- **§10, missing tests**: the listed cases exist since 0076 —
  targeted write vetoes (failed group-side grant, failed member-side
  revocation), half-revoked Board latch and half-lifted sanction not
  resurrected, missing and empty passwords, `argv` reduced to the two
  paths.

## Decisions in force (reminder)

Unchanged. To which the auditor's P3 question is added: **enabling
LDAPS in the compose stack** — the validating mechanism is ready since
0073 (`Tls` + `LDAP_CA_CERT_FILE`); enabling it, and the certificate
tooling of the LDAP container, remain an operations decision of the
client.

## Follow-ups delivered and remaining

- **0076** (merged `3fafc121`): closes items 1 to 4 of the "P2 to
  finish" list and provides the tests of item 5.
- **P3 operations** (upcoming): compose LDAPS (client decision), scan
  optimisation, reminders out of the HTTP cycle, `.env.example`.
- **P4**: mypy progressively blocking, Ruff extended, coverage floor
  raised, Certbot and CSP tested. The auditor's first two listed items
  (application wheel, frozen APT) were already covered by 0075, merged
  after his examination.

# Full text of the audit (eighth pass, translated)

# Updated audit of the AlirPunkto repository — eighth pass

**Date:** 2 August 2026
**Repository:** `michaellaunay/alirpunkto`
**Branch:** `master`
**Commit examined:** `2bc562912856a20a777d38b748bece8b41916c97`
**Previous audit:** `2c53ef8bb5de1cc41debd7faeaabdd207fc6560d`

## 1. Executive summary

The new commit strongly improves the last two P2 findings:

* reduced data exposure during LDIF generation;
* reconciliation of the two representations of LDAP memberships:

  * `member.uniqueMemberOf`;
  * `group.uniqueMember`.

Passwords, names, e-mail addresses, birthdates and descriptions are no
longer passed on `generate_ldif.py`'s command line. Passwords are now
hashed directly inside the generator, removing the old fallback that
could pass a cleartext password through `argv`.

The group synchronisation now reads both sides of the relation,
computes a per-side differential and lets the periodic scan discover a
person present on only one of the two sides.

However, contrary to the commit message's claim, P2 cannot yet be
considered fully closed:

1. several personal values remain visible in `argv`;
2. an absent password variable silently produces the hash of an empty password;
3. the "fail-closed" ordering of LDAP writes is not actually conditional;
4. the union of the two sides can restore a membership that has become stale;
5. the new mechanism performs many LDAP searches per member.

The commit reports 999 tests passing and a coverage of 72.10%. No
status or GitHub Actions workflow is returned by the connector for this
SHA; these results are therefore declared by the commit, not
independently confirmed.

## 2. Updated evaluation

| Domain                            | Previous grade | New grade |
| --------------------------------- | -------------: | --------: |
| Application architecture          |            7.7 |       7.8 |
| Code quality                      |            7.8 |       8.0 |
| Tests                             |            9.0 |       9.2 |
| CI and automated checks           |            9.0 |       9.0 |
| Documentation                     |            8.0 |       8.0 |
| Dependencies and reproducibility  |            9.0 |       9.0 |
| Application security              |            8.6 |       8.8 |
| Docker security and operation     |            9.0 |       9.1 |
| Operations and observability      |            7.3 |       7.4 |

**Updated overall grade: 8.6/10**, against 8.5/10 previously.

---

# 3. LDIF passwords removed from `argv` — resolved

The three passwords are now passed in the process's own environment:

```text
GENERATE_LDIF_ADMIN_PW
GENERATE_LDIF_U1_PW
GENERATE_LDIF_U2_PW
```

The corresponding slots in `GENERATE_LDIF_ARGS` contain only `"-"`.

The generator:

1. reads the variable with `os.environ.pop()`;
2. immediately removes it from its environment;
3. generates the `{SSHA}` hash itself;
4. never writes the cleartext password into the LDIF.

The old mechanism using `slappasswd` and its cleartext fallback is gone
from `init.sh`. The tests also verify the absence of the passwords from
the output and the removal of the variables after reading.

**Status regarding passwords: resolved.**

---

# 4. Main personal information removed from `argv` — largely resolved

The following fourteen slots now use the environment:

* three passwords;
* the administrator's e-mail address;
* first name, last name, e-mail address, birthdate and description of
  each initial user.

The script passes fourteen dashes in the argument array and defines the
matching variables only for the Python invocation.

The generator reads and removes these variables through a common
function.

The tests verify:

* the use of the environment values;
* their absence from the LDIF when optional and not provided;
* their removal from the environment;
* the absence of the matching variables from the Bash array;
* the absence of the old incorrect comment about NUL-separated arguments.

## Reserve: not all personal data has left `argv`

The Bash array still directly passes:

* `ADMIN_LOGIN`;
* `ADMIN_PSEUDONYM`;
* the users' UUIDs;
* their roles;
* their pseudonyms;
* their languages;
* their nationalities;
* their second and third languages.

At the very least, pseudonyms, identifiers, roles and nationalities are
personal data. Nationality can even be particularly sensitive
information depending on the processing context.

The claim "no personal data goes through `argv`" is therefore too
broad.

**Overall status of the personal-data transport: partially resolved.**

### Recommended fix

Completely remove the positional interface for user data and pass a
single structure:

* JSON on standard input;
* or a `0600` temporary file;
* or an anonymous file descriptor.

The command line should then contain no more than:

```text
generate_ldif.py --input-fd 0
```

---

# 5. Missing password variable — new risk

The function used for the environment slots returns an empty string
when the expected variable is absent:

```python
return os.environ.pop(env_name, "")
```

The empty password is then accepted by `_ensure_ssha()` and turned into
a valid `{SSHA}` hash.

A bad invocation can therefore silently create an account whose
password is empty.

`init.sh` does provide the three variables on the normal path, but the
generator remains directly usable and does not distinguish:

* mandatory fields;
* optional fields.

The tests only cover a missing variable for birthdates and
descriptions, not for passwords.

### Recommended fix

```python
def required_slot_from_env(value, env_name):
    if value != "-":
        raise ValueError(f"{env_name} must use the environment slot")
    result = os.environ.pop(env_name, None)
    if not result:
        raise ValueError(f"{env_name} is required")
    return result
```

**Severity: high on incorrect use of the generator.**

---

# 6. Reconciliation of the two LDAP sides — major improvement

`sync_member_groups()` now reads separately:

* the groups declared in the member's `uniqueMemberOf`;
* the groups whose `uniqueMember` contains the member's DN.

A divergence is logged before repair.

The code then computes four differentials:

```text
group_add
group_del
member_add
member_del
```

Each side therefore converges separately toward the target, unlike the
old code which computed a single differential from the member.

The tests notably demonstrate:

* the repair of a membership present only on the member;
* the repair of a membership present only on the group;
* the detection of a member existing only on the `uniqueMemberOf` side;
* the expected order of additions and removals.

**Status: substantial improvement.**

---

# 7. The "fail-closed" order is not actually enforced

The code calls `_checked_modify()` in the following order:

* addition: group, then member;
* removal: member, then group.

That order is relevant, since the application reads the member side.

However, the boolean returned by `_checked_modify()` is ignored.

## Example during an addition

1. the addition on the group fails;
2. `_checked_modify()` returns `False`;
3. the code continues regardless;
4. the addition on the member succeeds;
5. the application immediately sees the permission.

The behaviour is therefore not actually "fail-closed".

## Example during a removal

1. the removal on the member fails;
2. the code still removes the member from the group;
3. the application keeps seeing the membership on the member.

### Recommended fix

For each group, the second write must only run if the first one
succeeds:

```python
if _checked_modify(group_dn, group_change, operation):
    _checked_modify(member_dn, member_change, operation)
```

For a revocation, also stop processing the group when the member-side
removal fails.

**Failure-handling status: partially resolved.**

---

# 8. The union of the two sides can restore a stale state

The computation currently uses:

```python
current = member_side | group_side
```

This union is passed to the truth table.

That works well to repair some memberships computed from the member's
attributes. However, several persistent states are themselves derived
from the existing groups:

* sanction;
* board;
* mediation council;
* the corresponding suspended groups.

## Example: removal from the board

1. the member-side removal succeeds;
2. the group-side removal fails;
3. on the next scan, the union still contains `boardMembersGroup`;
4. the truth table considers the person still holds the role;
5. the group is re-added on the member side.

The divergence is "repaired", but in the wrong direction.

The same problem can appear when lifting a sanction while one of the
two sides lags behind.

### Recommended fix

Define an authoritative source for the persistent states.

Since the application reads `uniqueMemberOf`, a coherent approach would
be:

* use the member side as the authoritative state;
* write additions on the group side before the member;
* write removals on the member side before the group;
* never continue toward the authoritative side if the first write of an addition fails;
* use the scan to converge the group side toward the member.

Another solution is to store roles and sanctions in dedicated LDAP
attributes, then treat the groups as a derived view.

**Status: coherence risk still open.**

---

# 9. Daily scan: better coverage, higher cost

The daily scan now discovers members from:

* the groups' `uniqueMember`;
* the member entries' `uniqueMemberOf`.

This fixes the case of a person recorded only on their own LDAP object.

However, for each member, `sync_member_groups()` individually queries
each managed group. With twelve groups, the cost becomes approximately:

```text
number of members × number of groups
```

plus the member searches and the modifications.

On a large directory, the scan can generate several thousand or million
LDAP searches.

### Recommended fix

During the periodic scan:

1. load each group once;
2. build an inverse table `member → groups`;
3. load the members in a single paged search;
4. pass the precomputed state to the synchronisation function;
5. only re-query LDAP when a write fails.

**Severity: medium, mostly operational.**

---

# 10. Test results

The commit declares:

* ten new tests;
* 999 tests passing;
* a coverage of 72.10%;
* eleven failures observed on the repository's previous state.

The new tests effectively cover the nominal paths and the already
recorded divergences. They do not yet cover:

* the failure of the first write of an addition;
* the failure of the first write of a revocation;
* lifting a sanction with one side lagging;
* removing a Board/MAC role with one side lagging;
* an absent password variable;
* the presence of nationalities and pseudonyms in `argv`;
* scan performance on a large directory.

---

# 11. Earlier findings still open

## LDAP transport

LDAPS connections now validate certificates, but the Compose stack
still defaults to:

```text
LDAP_PORT=389
LDAP_USE_SSL=false
```

The encrypted transport is therefore not yet enabled in the shipped
deployment.

## Periodic tasks

Reminders are still triggered from `NewRequest`, which guarantees
neither execution without traffic nor uniqueness in a multi-process
environment.

## `.env.example`

The file remains inconsistent with the names actually used:

* `MAIL_USE_TLS` instead of `MAIL_TLS`;
* `MAIL_USE_SSL` instead of `MAIL_SSL`;
* outdated LDAP documentation;
* missing `LDAP_CA_CERT_FILE`.

## Image

Also still open:

* editable installation of the application;
* unfrozen APT packages;
* no `--only-binary=:all:` enforcement;
* a few development artefacts still copied.

## Quality debt

* mypy not blocking;
* Ruff limited to Pyflakes;
* `F841` ignored;
* coverage floor at 68%;
* Certbot renewal and CSP untested.

---

# 12. Revised priorities

## P0 — closed

* Docker startup;
* Waitress configuration;
* Apache routing;
* smoke test;
* secret detection.

## P1 — closed

* separated, hashed locks;
* multi-stage image;
* slimmed runtime;
* pinned images.

## P2 — almost closed, but not fully

Resolved:

* LDAP cache;
* LDAPS certificate validation;
* encrypted refresh token;
* Keycloak validation;
* LDIF passwords off `argv`;
* two-sided detection of LDAP divergences.

To finish:

1. make the generator's password variables mandatory;
2. remove the remaining personal data from `argv`;
3. condition the second writes on the success of the first ones;
4. choose an authoritative source for the persistent roles;
5. add tests injecting real LDAP failures.

## P3 — operations

1. enable and test LDAPS in Compose;
2. optimise the group scan;
3. move the reminders out of the HTTP cycle;
4. fix `.env.example`.

## P4 — finishing

1. build an application wheel;
2. freeze the APT dependencies;
3. make mypy progressively blocking;
4. extend Ruff;
5. raise the coverage floor;
6. test Certbot and the CSP.

---

# 13. Conclusion

Commit `2bc5629…` is a real and important improvement.

It notably fixes:

* the most serious exposure of passwords in process arguments;
* the cleartext hashing fallback;
* the impossibility of detecting a member recorded only on their own side;
* the use of a single differential for two different LDAP states.

It does not, however, fully close the two findings:

* several personal values remain in `argv`;
* the reconciliation can still continue a write after a failure;
* the union of the two sides can restore a stale role;
* the absence of an environment password can create the hash of an empty password.

**Current evaluation: 8.6/10.**

An evaluation around **8.9/10** would become justified after strictly
closing the LDIF transport, conditional handling of LDAP writes and
the definition of an authoritative source for roles and sanctions.
