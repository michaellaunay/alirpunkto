# External repository audit (ChatGPT), eleventh pass — 2 August 2026

**Provenance.** Eleventh pass of the external static audit (ChatGPT,
at Michaël Launay's request), on commit `777074c2` (train 0078);
previous pass on `3fafc121`, also covering the intermediate
documentation commit `32f9660a`. Proposed overall grade: **8.8/10** —
the highest of the series. Across the passes: 6.5 → 6.9 → 6.7 → 7.1 →
7.8 → 8.2 → 8.5 → 8.6 → 8.4 → 8.3 → 8.8. (Translated from the French
original.)

**Status.** Counter-reviewed the same day. The tenth pass's three P0s
are declared closed in the code, the centralised LDIF contract judged
"sound", the transversal tests "very satisfactory", and the
documentation a "strong improvement" — the auditor notes that the
earlier trains' mistakes are owned in writing rather than hidden. The
ceiling toward 9/10 is explicitly identified: **no successful smoke
run is observable yet** — an Actions visibility setting on the
repository side (the `push` and `pull_request` triggers exist), then a
first green run. Suggestions kept on the books: the **functional test
of the shared emitter** (§9: parity checks names, not the correctness
of each mapping — distinctive values, NUL-stream decoding,
record-by-record comparison); the **temporal reserve** on the filings
(§10: archived audits describe intermediate states — precisely the
role of each filing's provenance header); the **sanction persistence**
(§11, design decision in progress, three options presented to the
client); and the **LDIF serialisation** (§12, next code train).

## Follow-ups planned

Next code train: functional emitter test, LDIF serialiser, sanction
persistence (per the decision); operations side: make the Actions
visible and observe the first green smoke; then the test-stack CI (P1
items 3-4 — which converge with the client's proposal to attach
validation tests to it and, later, a bilingual user manual captured on
that stack).

# Full text of the audit (eleventh pass, translated)

# Updated audit of the AlirPunkto repository — eleventh pass

**Date:** 2 August 2026 — **Repository:** `michaellaunay/alirpunkto` —
**Branch:** `master` — **Commit examined:**
`777074c25f0c55c58a13cf166945cdde8dfeef77` — **Previous audit:**
`3fafc1215915e0a92c882d19058c9767e1be51be`

## 1. Executive summary

Two commits were added since the previous pass: 1. a documentation
commit archiving the audits and updating the architecture chapters;
2. a technical fix closing the three P0 breaks discovered during the
tenth pass.

The new train effectively fixes: the duplicate `args:` key of the LDAP
service; the old LDIF interface still used in `smoke.yml`; the old
LDIF interface still used in `init_test.sh`; the duplication of the
transport contract across several callers; the absence of Compose
validation before the build.

The LDIF contract is now centralised in `docker/ldif_records.sh`, used
by the three callers: `docker/init.sh`, `docker/init_test.sh`,
`.github/workflows/smoke.yml`. The smoke workflow now validates both
Compose files with `docker compose config --quiet` before building any
image. Seven new tests aim to prevent these regressions from
returning. The commit declares 1,022 tests passing and 72.10%
coverage.

The GitHub connector however still returns no status and no workflow
run for this SHA. The implementation and wiring are therefore verified
statically, but the smoke test's real success remains unconfirmed.

## 2. Updated evaluation

| Domain                            | Previous | New |
| --------------------------------- | -------: | --: |
| Application architecture          |      8.0 | 8.1 |
| Code quality                      |      8.3 | 8.4 |
| Unit and structural tests         |      9.2 | 9.4 |
| CI and integration tests          |      7.8 | 8.9 |
| Documentation                     |      8.0 | 8.6 |
| Dependencies and reproducibility  |      9.4 | 9.4 |
| Application security              |      9.1 | 9.1 |
| Docker security and operation     |      7.5 | 9.0 |
| Operations and observability      |      7.5 | 7.6 |

**Updated overall grade: 8.8/10**, against 8.3/10 previously. The
grade does not yet pass 9/10, mainly because the smoke test is still
not observable as having genuinely succeeded.

# 3. Production Compose — P0 resolved

The LDAP service now carries a single `args` block (`BUILD_WITH_DEBUG`
+ `UBUNTU_SNAPSHOT`). The duplicate YAML key is gone; both arguments
reach the same build — the optional diagnostics and the optional
Ubuntu snapshot pinning.

# 4. Compose validation before the build — resolved by wiring

The smoke workflow now carries a dedicated step before the build,
validating both Compose files with `config --quiet`. It will notably
catch: YAML errors Compose understands; duplicate keys its parser
rejects; invalid variable substitutions; inconsistent service
references; several structural configuration errors. The order is
right: the validation precedes "Build the images". The tests also
verify the two `config --quiet` calls, their position before the
build, and the absence of duplicate keys in both Compose files.

**Status: resolved by inspection.**

*Reserve.* The Python detector added in the tests is a minimal
analyser suited to the block-style YAML the project uses, not a full
YAML parser. Not blocking, since the CI must also run Docker Compose's
real parser — but with no visible run, only the static part is
demonstrated today.

# 5. Centralised LDIF contract — resolved

The NUL-record stream is no longer defined inline in `init.sh`. It is
centralised in `docker/ldif_records.sh`, exposing a single function,
`generate_ldif_records`, which emits the 25 required and 8 optional
fields the generator expects. Missing required values are emitted
empty, then rejected by the generator, which stays the single
validation authority.

The separation is sound: the shell adapts the different callers'
variable names; the generator checks the protocol; the generator
refuses missing, empty or unknown fields; the generator alone hashes
the passwords.

# 6. docker/init.sh — correctly migrated

The production initialisation explicitly creates the expected alias
(`ADMIN_UUID="${LDAP_ADMIN_OID}"`), then loads the emitter and uses
only the two paths on the command line. The production contract is
therefore coherent with the generator's.

# 7. docker/init_test.sh — correctly migrated

The test script no longer computes `{SSHA}` hashes itself. It now
defines the canonical values the emitter expects (administrator
account; first user; second user; roles; languages; nationalities;
descriptions; current date), loads the shared contract and sends the
records on standard input. The needed UUIDs and passwords are
initialised at the top of the script, with local defaults or values
from the environment.

**Status: resolved by inspection.**

*Reserve.* The smoke workflow does not actually run
`docker/init_test.sh` — it reproduces its own non-interactive setup.
`init_test.sh`'s compatibility is therefore protected by structural
tests, but its full execution remains to be exercised: LDIF
generation; certificate generation; `test.ini` creation or
normalisation; local stack startup.

# 8. Smoke workflow — LDIF interface repaired

The workflow no longer references `GENERATE_LDIF_ADMIN_PW`,
`GENERATE_LDIF_U1_PW`, `GENERATE_LDIF_U2_PW`. It defines the canonical
variables, loads the shared emitter and calls the generator with the
two allowed paths. The workflow is therefore again capable, in
principle, of reaching the following steps: Compose validation; image
builds; temporary certificate creation; stack startup; HTTPS request
through Apache; client-address propagation test; diagnostics and
teardown.

**Status: repaired by inspection.**

*Missing execution proof.* For commit `777074c…` the connector returns
no combined status and no associated workflow run. That does not
necessarily prove no workflow ran — the runs connector's coverage is
limited — but it does mean no success can be attested from the data
available here. The code P0 is closed; operational validation awaits
proof.

# 9. Transversal caller tests — clear improvement

The new `tests/test_ldif_callers.py` covers the three known callers
(`docker/init.sh`, `docker/init_test.sh`,
`.github/workflows/smoke.yml`). The tests verify: no duplicate Compose
keys; both LDAP build arguments present; each caller using the shared
emitter; no old `GENERATE_LDIF_*` variables; no user arguments after
the two paths; parity between the emitted fields and those the
generator declares; no password hashing in the shell scripts; the
Compose validation before the build.

**Status: very satisfactory.**

*Limit of the structural checks.* Parity checks record names, not the
correctness of each mapping. A mistake such as
`emit U1_NAT "${USER1_LANG}"` would keep the right name set while
sending a wrong value. The current mappings are correct by inspection,
but a small functional test of the shared emitter would strengthen the
contract: 1. set distinctive values for every variable; 2. run
`generate_ldif_records`; 3. decode the NUL stream; 4. compare each
record to its expected source variable.

# 10. Documentation — important update

The intermediate commit `32f9660…` archives the earlier audits in
French and English, then updates notably the chapters on LDAP groups,
authentication, security, testing and Docker deployment.

The documentation acknowledges the counter-reviews and earlier
overstatements, notably the premature claim that P2 was closed. This
traceability is positive: the history of decisions, fixes and limits
is not rewritten as though the mistakes had never existed.

**Status: strong improvement.**

*Temporal reserve.* Archived documents necessarily describe
intermediate states. They must stay clearly presented as historical
audits, not as the repository's current situation.

# 11. Important reserve: persistence of a new sanction

The previous fix made the member side authoritative to prevent an old
sanction or role left only on the group from being restored. That
choice correctly closes the resurrection risk.

The inverse scenario however stays open: 1. a new sanction is computed
with `force_sanctioned=True`; 2. the group-side add succeeds; 3. the
member-side add fails; 4. the next pass reads a member side without
the sanction; 5. the group-side leftover is treated as stale; 6. the
sanction may be removed instead of replayed.

The fail-closed order protects the application immediately: it reads
no sanction while the member does not carry it. But that precisely
means the user may go unsanctioned if the authoritative write fails.

*Recommendation.* Sanctions should have an authoritative state
independent of the derived groups — for example a dedicated LDAP
attribute; a persistent application record; an event journal; a
transactional retry queue. The function should also return the
operations actually applied, not only the computed theoretical target.

**Status: open, medium-to-high severity.**

# 12. LDIF serialisation — still to harden

The transport toward Python is now safe with respect to `argv`. Some
values however are still interpolated straight into the LDIF
(`f"sn: {last}"`, `f"cn: {pseudonym}"`, `f"givenName: {first}"`,
`f"description: {description}"`, `f"mail: {email}"`). A value carrying
`\r` or `\n` could alter the LDIF document's structure. The
interactive path naturally limits the risk, but `generate_ldif.py` is
now an autonomous interface fed by stdin.

*Recommended fix.* A common serialiser that refuses NULs and newlines
in single-line fields; base64-encodes values LDIF requires encoded;
validates UUIDs; restricts roles to the allowed values; validates
language and nationality codes; validates dates and e-mail addresses.

**Status: open.**

# 13. Other findings still open

**Encrypted LDAP by default.** LDAPS connections validate certificates
correctly, but the shipped stacks still use cleartext LDAP on 389.
**Group scan cost.** The periodic scan still performs many LDAP reads
per member and per group; a global read followed by an inverse table
would strongly cut the cost. **Periodic tasks in NewRequest.**
Reminders stay tied to HTTP traffic and the Pyramid process: no
execution without traffic; multi-process duplicate risk; no reliable
external scheduling. **.env.example.** The template still carries
inconsistent mail variable names and does not fully present the LDAPS
configuration. **Local Docker tests.** The test stack still installs
its extra dependencies at container startup; a dedicated test image
would be more autonomous and deterministic. **APT reproducibility.**
The snapshot mode exists but stays optional; builds without
`ALIRPUNKTO_UBUNTU_SNAPSHOT` keep using the moving Ubuntu archive.
**Progressive quality.** mypy not blocking; Ruff limited to the F
family; `F841` ignored; coverage floor at 68%; real Certbot and
renewal untested; CSP not enabled and tested.

# 14. Revised priorities

**P0 — closed in the code**: Compose without duplicate keys; smoke
workflow migrated; local setup migrated; Compose validation before
build; shared LDIF contract. The smoke workflow's real success remains
to be observed.

**P1 — integration validation**: 1. obtain a visible, successful
GitHub Actions run; 2. verify the Compose, build, healthcheck, Apache
and throttle steps; 3. run `init_test.sh` in a clean environment;
4. actually start the local test stack; 5. functionally test the
shared emitter's mappings.

**P2 — LDAP coherence and security**: 1. make sanctions persistent
despite a partial failure; 2. introduce a distinct authoritative
source for institutional states; 3. properly serialise the LDIF
values; 4. enable and test LDAPS in the shipped stacks; 5. optimise
the group relation scan.

**P3 — operations**: 1. move the periodic tasks out of `NewRequest`;
2. fix `.env.example`; 3. make the APT snapshot mandatory for
published images; 4. produce an autonomous test image; 5. test Certbot
and the CSP.

# 15. Conclusion

Commit `777074c…` correctly closes the three P0 breaks discovered
during the previous pass.

The most important gains: a valid production Compose again; the smoke
workflow restored; the local test setup restored; an LDIF contract
shared by every caller; transversal control of interface migrations;
Compose validation positioned before any build.

The quality of the reaction is also worth underlining: the comments
and the documentation explicitly acknowledge the defects the earlier
trains introduced rather than hiding them.

The repository now shows: a strongly locked Python chain; a clean,
minimal Pyramid image; markedly improved application security; a CI
well designed on paper; high structural coverage.

The main remaining gaps are now fewer but more specialised: no
execution proof for the smoke test; sanction persistence on partial
failure; LDIF serialisation; LDAPS not enabled by default; periodic
tasks and still-progressive quality.

**Current evaluation: 8.8/10.** An observable, successful smoke run,
followed by the LDIF hardening and the sanction persistence, would
durably cross the 9/10 threshold.
