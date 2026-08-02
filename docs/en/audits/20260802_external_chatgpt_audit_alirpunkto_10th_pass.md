# External repository audit (ChatGPT), tenth pass — 2 August 2026

**Provenance.** Tenth pass of the external static audit (ChatGPT, at
Michaël Launay's request), on commit `3fafc121` (train 0076); previous
pass on `72e65db2`. Proposed overall grade: **8.3/10** — down for the
second time. Across the passes: 6.5 → 6.9 → 6.7 → 7.1 → 7.8 → 8.2 →
8.5 → 8.6 → 8.4 → 8.3. (Translated from the French original.)

**Status.** Counter-reviewed the same day: the four security fixes of
0076 are validated, and **the three reported P0s are well founded —
and of our own making**. The duplicate `args:` key comes from the 0075
insertion in front of an existing block the inspection never
displayed, and the "YAML OK" check was a false green (PyYAML swallows
duplicate keys where compose refuses the file); `smoke.yml` stayed on
the old interface because the 0076 migration grep stopped at
`tests/ docker/` without `.github/`; `init_test.sh` had never been
migrated — and its `hash_ssha` moreover pushed each password through
the hashing python's argv. §11 is the lesson: the tests inspected
*one* caller, not *the* callers. Fixes delivered by 0078 (merged
`777074c2`): common emitter `docker/ldif_records.sh` sourced by the
three callers, duplicate merged, `compose config --quiet` gate on both
files, seven transversal tests — evaluated by the eleventh pass
(8.8). The §3 wording reserve ("a pipe visible to no one") is also
fixed in the comments. Still open and tracked: the **persistence of a
new sanction** (§7, design decision in progress — three options on the
table) and the **LDIF serialisation** (§12, next code train).

## Follow-ups delivered

0078 (P0 + P1 coherence, chronicled in the eleventh-pass filing);
ahead: sanctions (P2, decision), LDIF serialiser, LDAPS (operations
decision), scan optimisation, reminder out of HTTP, `.env.example`.

# Full text of the audit (tenth pass, translated)

# Updated audit of the AlirPunkto repository — tenth pass

**Date:** 2 August 2026 — **Repository:** `michaellaunay/alirpunkto` —
**Branch:** `master` — **Commit examined:**
`3fafc1215915e0a92c882d19058c9767e1be51be` — **Previous audit:**
`72e65db2de566bc193c5d14130ac301594b4231a`

## 1. Executive summary

The new commit correctly fixes the four security reserves of the
previous pass: all user data bound for the LDIF now leaves `argv`; a
missing or empty required value fails the generation; the paired LDAP
writes are genuinely conditional; the member side becomes the
authoritative source for roles, sanctions and persistent memberships.
These fixes come with targeted tests injecting LDAP failures and
invalid LDIF inputs.

However, the Docker integration is currently blocked by **three P0
problems**: 1. `docker/docker-compose.yaml` still carries two `args:`
keys in the LDAP service; 2. the `smoke.yml` workflow still uses the
old positional interface of `generate_ldif.py`; 3. `docker/init_test.sh`
also uses the old interface. The smoke workflow and the local test
environment will therefore fail before they can test the stack. The
Docker P0 stays open.

The commit reports 1,015 tests passing and 72.10% coverage. The GitHub
connector however surfaces no status or workflow for this SHA — the
results are declared by the commit but not independently confirmed.

## 2. Updated evaluation

| Domain                            | Previous | New |
| --------------------------------- | -------: | --: |
| Application architecture          |      7.9 | 8.0 |
| Code quality                      |      8.1 | 8.3 |
| Unit and structural tests         |      9.1 | 9.2 |
| CI and integration tests          |      8.8 | 7.8 |
| Documentation                     |      8.0 | 8.0 |
| Dependencies and reproducibility  |      9.4 | 9.4 |
| Application security              |      8.8 | 9.1 |
| Docker security and operation     |      7.9 | 7.5 |
| Operations and observability      |      7.5 | 7.5 |

**Updated overall grade: 8.3/10**, against 8.4/10 previously.
Application security clearly progresses, but the smoke-workflow and
local-test-setup breaks prevent these fixes from being fully valued.

# 3. Whole-LDIF transport over standard input — resolved

The generator now accepts only two arguments: `generate_ldif.py
TEMPLATE OUT`. Every other value arrives on standard input as
`NAME=VALUE\0` records — passwords, UUIDs, logins, pseudonyms, roles,
names, e-mail addresses, languages, nationalities, birthdates,
descriptions included.

The production script builds these records with `printf` and pipes
them in:

```bash
generate_ldif_records | python3 docker/generate_ldif.py \
    "${LDIF_TEMPLATE}" "${LDIF_OUT}"
```

The command line now carries only the template and output paths. This
removes the permanent exposure in `/proc/<pid>/cmdline` and to the
classic process-listing tools.

*Wording reserve.* The comment claims a pipe is "visible to no one".
Not strictly exact: a root administrator, an authorised debugger or a
process with tracing rights can still observe a process's memory or
descriptors. The mechanism is nevertheless markedly safer than
`argv`, the environment or a persistent temporary file.

# 4. Required fields and empty passwords — resolved

The generator explicitly defines 25 required and 8 optional fields.
Before writing anything it collects the missing-or-empty required
names and aborts with the list; unknown record names also abort. The
tests cover: a missing password; an empty password; an unknown field
name; the LDIF's absence after failure; the optional character of
dates and descriptions. The risk of silently creating an account whose
password is the hash of the empty string is closed.

# 5. LDAP writes genuinely fail-closed — resolved for the tested cases

The old version ordered the writes correctly but ignored the first
operation's result. The new version really conditions the second
write. *Adding a membership*: group first, member only if the group
add succeeded. *Removing a membership*: member first, group only if
the member removal succeeded. The tests inject a precise refusal into
`conn.modify()` and verify a failed group-side add blocks the member
add, and a failed member-side removal preserves the group side.

# 6. Authoritative member side — coherent fix

The truth table previously used `current = member_side | group_side`;
a stale record present only on the group could restore a lifted
sanction or a removed Board/MAC role. The computation now uses
`current = member_side` alone. Tests verify an old Board role left
only on the group is removed, and an old sanction left only on the
group is not restored. Coherent with the application, which reads the
member side to determine rights.

# 7. Persistent reserve: a new sanction can be lost

The member side now carries the authoritative state; the truth table
derives the sanction from `current & {SANCTIONED,
SANCTIONED_MISSING_YEAR}` unless the event explicitly passes
`force_sanctioned`.

One scenario stays problematic: 1. an event applies a new sanction
with `force_sanctioned=True`; 2. the group-side write succeeds; 3. the
member-side write fails; 4. the function logs the failure but still
returns the computed target; 5. on the next pass the member side
carries no sanction; 6. the group-side leftover is treated as stale
and removed.

The comment deems a lost grant "safe and replayable". That assumption
suits an extra privilege, not necessarily a sanction, which is on the
contrary a restriction of rights. The new architecture therefore
correctly favours safety on revocation, but does not guarantee the
persistence of a new sanction when the authoritative write fails.

*Recommendation.* Sanctions and institutional roles should live in
dedicated LDAP attributes independent of the derived groups. Failing
that: return a structured result naming the writes that actually
succeeded; queue the operation for retry; explicitly replay the
sanction until the member side carries it; never merely return the
theoretical target after a failure.

**Status: open, medium-to-high severity depending on sanction usage.**

# 8. P0: production Compose still invalid

The LDAP service still carries two `args:` keys at the same level.
Depending on the YAML parser, the file is refused for the duplicate
key, or the second block replaces the first — in which case the Ubuntu
snapshot never reaches the OpenLDAP build.

*Required fix*: merge into a single
`args: {BUILD_WITH_DEBUG, UBUNTU_SNAPSHOT}` block. *Mandatory
control*: `docker compose --env-file docker/.env -f
docker/docker-compose.yaml config --quiet`.

**Status: open, P0.**

# 9. P0: smoke workflow incompatible with the new generator

The smoke workflow still uses `GENERATE_LDIF_ADMIN_PW`,
`GENERATE_LDIF_U1_PW`, `GENERATE_LDIF_U2_PW`, the `-` placeholders and
the old long positional argument list — while the generator now
refuses any invocation whose command line is not exactly two paths.

The workflow will therefore stop during "Generate a throwaway stack
configuration", before Compose validation, the image builds, the stack
startup, the Apache test and the Waitress proxy test. It currently
cannot fulfil its purpose.

*Required fix.* The workflow generation must use the same contract as
`init.sh` (the `emit` function, a pipe into the generator with the two
paths alone), and add `${COMPOSE_CMD} config --quiet` before the
build.

**Status: open, P0.**

# 10. P0: local test initialisation also broken

`docker/init_test.sh` still: 1. hashes the passwords itself; 2. calls
`generate_ldif.py` with the old positional interface; 3. passes user
data through `argv`. The generator will refuse the invocation for the
same reason as the smoke workflow. The documented
`./docker/init_test.sh` can therefore no longer produce
`docker/initials_users.test.generated.ldif`; the local test stack is
no longer initialisable by the intended path.

*Required fix.* Extract the NUL-record generation into a common tool
used by `docker/init.sh`, `docker/init_test.sh` and
`.github/workflows/smoke.yml`, avoiding three copies of the same
contract.

**Status: open, P0.**

# 11. Insufficient test coverage of the generator's callers

The transport tests inspect only `docker/init.sh`. They correctly
verify that caller no longer speaks the old contract — but they
inspect neither `docker/init_test.sh`, nor
`.github/workflows/smoke.yml`, nor other scripts or documentation
examples. The interface change therefore broke two callers without a
single failure in the declared suite.

*Recommended structural test.* Find every call to the generator and
require: exactly two arguments after the script name; stdin feeding;
no `GENERATE_LDIF_*` reference; no legacy positional list. A more
robust test would directly run `docker/init_test.sh` non-interactively,
the smoke workflow's preparation step, and `docker compose config
--quiet`.

# 12. LDIF serialisation to harden

The NUL transport correctly protects values between Bash and Python.
However the generator still interpolates several values straight into
LDIF lines (`f"sn: {last}"`, `f"cn: {pseudonym}"`,
`f"givenName: {first}"`, `f"description: {description}"`,
`f"mail: {email}"`). A value containing a newline can alter the LDIF
structure or inject a new attribute. `init.sh` currently collects
values line by line, which limits the risk on the normal interactive
path, but the generator now accepts arbitrary values directly on
stdin.

*Recommendation.* Use an LDIF serialisation function that refuses
`\0`, `\r` and `\n` in single-line fields; base64-encodes values LDIF
requires encoded; validates UUIDs, roles, languages and nationalities;
validates e-mail addresses and dates before writing.

**Status: open, medium hardening.**

# 13. Earlier findings still open

**Encrypted LDAP.** LDAPS certificates are validated when enabled, but
the shipped stacks still use cleartext LDAP on 389. **LDAP scan
performance.** The scan loads memberships with several searches per
member and per group; a one-pass inverse table would suit a large
directory better. **Periodic tasks.** Reminders still fire from
`NewRequest`, with no traffic-free execution or multi-process
coordination guarantee. **.env.example.** Still stale mail variables
and no proper LDAPS documentation. **Image chain.** The Pyramid image
is well finished, but remain: the optional APT snapshot; the dynamic
test-dependency install at local stack startup; no observed successful
smoke test. **Quality debt.** mypy not blocking; Ruff limited to the F
rules; `F841` ignored; coverage floor at 68%; Certbot and CSP
untested.

# 14. Revised priorities

**P0 — Docker integration.** 1. Merge the two `args` blocks of the
LDAP service. 2. Migrate `smoke.yml` to the NUL-on-stdin transport.
3. Migrate `init_test.sh` to the same contract. 4. Add `docker compose
config --quiet`. 5. Run the full smoke test in GitHub Actions.
6. Verify the build result and the HTTPS request through Apache.

**P1 — tool coherence.** 1. Create a common LDIF record generator.
2. Test every caller of `generate_ldif.py`. 3. Actually run the test
setup in CI. 4. Validate both Compose files with a strict parser.

**P2 — LDAP coherence.** 1. Guarantee the persistence of new sanctions
after a partial failure. 2. Return the real write state, not just the
computed target. 3. Introduce a retry or reconciliation queue.
4. Store sanctions and institutional roles in authoritative
attributes.

**P3 — hardening.** 1. Properly serialise the LDIF values. 2. Enable
and test LDAPS in Compose. 3. Optimise the LDAP scan. 4. Move the
periodic tasks out of the HTTP cycle. 5. Fix `.env.example`.

# 15. Conclusion

Commit `3fafc12…` correctly fixes the security findings on: personal
data exposure in `argv`; missing or empty passwords; write propagation
after a first failure; the involuntary restoration of revoked roles.
These fixes markedly advance the application code's security.

However, the LDIF interface migration was not propagated to all its
callers: the smoke workflow and the local test setup are now
incompatible with the generator, and the production Compose keeps its
duplicate `args` key.

The repository therefore currently has: good application security; a
well-built production image; solid unit tests; but a Docker
integration chain that is non-functional by static inspection.

**Current evaluation: 8.3/10.** After fixing the Compose, migrating
the two LDIF callers and an observable successful smoke test, the
grade could reach about **8.9/10**. The next update should first
verify the three P0 fixes and look for a genuinely successful smoke
run.
