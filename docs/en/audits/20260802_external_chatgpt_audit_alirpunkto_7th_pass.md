# External repository audit (ChatGPT), seventh pass — 2 August 2026

**Provenance.** Seventh pass of the external static audit (ChatGPT, at
Michaël Launay's request), on commit `2c53ef8b` (LDAP TLS, keyed
cache, sealed token, Keycloak validation); previous pass on `e80f39e`.
Proposed overall grade: **8.5/10**. Across the passes: 6.5 → 6.9 → 6.7
→ 7.1 → 7.8 → 8.2 → 8.5. Text transmitted after the fact (on
2026-08-02) and filed for the record: this document describes the
repository after train 0073 — the "still open" findings have since
been addressed by 0074 through 0078. (Translated from the French
original.)

**Status (retrospective).** The audit validates the four fixes of
train 0073 (cache, validating LDAPS, sealing, response validation) and
notably salutes the cookie-budget test on a *hard-to-compress* token —
"markedly more reliable than a fake token made of one repeated
character". Four suggestions of lasting value remain on the books: a
**dedicated encryption key** for the SSO tokens
(`SSO_REFRESH_ENCRYPTION_KEY`, usage separation and targeted rotation
— P3); the **90-day cap made configurable** or documented as platform
policy (P3); a test of the **actual Set-Cookie header** produced by
the real Pyramid session factory; and the **real TLS negotiation
bench** (test CA, slapd on 636, real bind, refusal of a wrong
certificate) — which joins the still-open LDAPS operations decision.

## Follow-ups delivered

0074 then 0076 (LDIF transport and group coherence — the two "still
open" items of its P2), 0075 (image reserves), 0078 (callers).
Chronicled in the filings of the 8th, 10th and 11th passes.

# Full text of the audit (seventh pass, translated)

# Updated audit of the AlirPunkto repository — seventh pass

**Date:** 2 August 2026 — **Repository:** `michaellaunay/alirpunkto` —
**Branch:** `master` — **Commit examined:**
`2c53ef8bb5de1cc41debd7faeaabdd207fc6560d` — **Previous audit:**
`e80f39e912e239cc267dda8489bc68cbc57f37ac`

## 1. Executive summary

The new commit addresses four important security findings: validation
of LDAPS connection certificates; fix of the global LDAP `Server`
object cache; encryption of the Keycloak refresh token in the session;
strict validation of the Keycloak endpoint responses.

Three findings can now be considered resolved: 1. the LDAP cache no
longer mixes different configurations; 2. the refresh token is no
longer readable in the signed cookie; 3. invalid Keycloak responses
are no longer used unchecked.

The "LDAP TLS" finding is only partially resolved: when LDAPS is
enabled the certificate is now validated; but the default generated
Docker stack still uses cleartext LDAP on port 389 with
`LDAP_USE_SSL=false`.

The commit reports 989 tests passing and 71.98% coverage. I could not
confirm these results independently: the GitHub connector returned no
Actions run and no status for this SHA.

## 2. Updated evaluation

| Domain                            | Previous | New |
| --------------------------------- | -------: | --: |
| Application architecture          |      7.5 | 7.7 |
| Code quality                      |      7.6 | 7.8 |
| Tests                             |      8.7 | 9.0 |
| CI and automated checks           |      9.0 | 9.0 |
| Documentation                     |      8.0 | 8.0 |
| Dependencies and reproducibility  |      9.0 | 9.0 |
| Application security              |      7.7 | 8.6 |
| Docker security and operation     |      9.0 | 9.0 |
| Operations and observability      |      7.2 | 7.3 |

**Updated overall grade: 8.5/10**, against 8.2/10 previously.

# 3. LDAP cache — resolved

The old code kept a single global `Server` object; the first call
imposed its host, port and SSL mode on every later one. The cache is
now a dictionary keyed by `(server_name, port, bool(use_ssl),
str(get_info), mock)`: two different configurations produce two
distinct objects, two identical calls reuse the same one.
`reset_ldap_connection()` now clears the whole cache.

The tests verify: call-time parameter resolution; no shared global
LDAP connection; distinction between two servers; reuse for identical
parameters; complete cache clearing.

# 4. LDAPS certificate validation — partially resolved

**4.1 Cryptographic validation — resolved.** LDAPS connections now
receive `Tls(validate=ssl.CERT_REQUIRED,
ca_certs_file=LDAP_CA_CERT_FILE)`. Without `LDAP_CA_CERT_FILE` the
code relies on the system trust store; the variable can also name a
deployment-specific bundle. The test verifies the cleartext server has
no TLS configuration, the LDAPS server differs, `use_ssl` is on, and
the validation level is `ssl.CERT_REQUIRED`. The interception
vulnerability by a rogue server presenting any certificate is thus
fixed for LDAPS connections.

**4.2 Encrypted transport by default — still open.** The init script
still generates `LDAP_PORT=389` and `LDAP_USE_SSL=false`; bind
credentials and LDAP data still cross unencrypted in the default
Docker configuration. The backend network limits exposure but does not
protect against a compromised container on that network, a host-side
capture, a future segmentation mistake, or an unwanted local
administrator. `LDAP_CA_CERT_FILE` is also not yet presented in
`.env.example`, which still documents the old LDAP configuration. The
current tests inspect the `Tls` object but perform no real negotiation
against an LDAP server with a test certificate.

*Next fix.* The test stack should: 1. generate a temporary CA;
2. issue a certificate for the LDAP service; 3. configure slapd on
636; 4. mount the CA into Pyramid; 5. enable `LDAP_USE_SSL=true`;
6. perform a real bind; 7. verify a wrong certificate or name is
refused.

# 5. Encrypted Keycloak refresh token — resolved

The refresh token is no longer stored directly in the signed session.
It is now UTF-8 encoded, zlib-compressed, Fernet-encrypted and
authenticated, and encoded for session storage:

```python
Fernet(get_secret(SECRET_KEY)).encrypt(
    zlib.compress(refresh_token.encode("utf-8"), 9)
)
```

Reading reverses the operation. The following return `None`: an old
cleartext token; tampered ciphertext; an undecodable value; a
correctly encrypted but uncompressed value; invalid compressed data.
The home page now exclusively uses `load_sso_refresh_token()`: an old
or corrupted session causes a clean logout rather than an exception or
the use of an invalid token.

*Cookie budget.* The test uses a 2,000-character token built to be
hard to compress, then checks the whole session stays under the
4,093-byte limit with extra margin — markedly more reliable than a
fake token made of one repeated character, which would have
artificially compressed extremely well.

*Minor reserves.* **Shared key**: the encryption reuses `SECRET_KEY`,
already employed by other cryptographic functions; a dedicated key
(`SSO_REFRESH_ENCRYPTION_KEY`) would give better usage separation, SSO
rotation without touching other secrets, and targeted SSO session
revocation — a recommended hardening, not a blocker. **Real cookie
test**: the budget test pickles a dict and adds a signature estimate;
a complementary test could check the actual Set-Cookie header produced
by the real Pyramid factory.

# 6. Keycloak response validation — resolved

Every HTTP 200 response of the token endpoints now goes through a
common validation function. It requires: valid JSON; a JSON object;
`access_token` a non-empty string; `refresh_token` a non-empty string;
`expires_in` a strictly positive integer; `refresh_expires_in` a
strictly positive integer; lifetimes at most 90 days; explicit refusal
of booleans even though Python counts them as integers. Errors are
logged without the response body, which may contain tokens.

The tests cover: non-JSON body; JSON that is not an object; missing
field; null or unusable token; string lifetime; boolean lifetime; zero
lifetime; unreasonably high lifetime; the initial authentication path;
the refresh path.

*Operational reserve.* The 90-day cap is hardcoded
(`_MAX_TOKEN_LIFETIME_SECONDS = 90 * 24 * 3600`). It probably suits
normal sessions but may refuse a legitimate Keycloak configuration
using refresh tokens beyond 90 days, offline sessions, or the
convention where `refresh_expires_in=0` means no expiry. The
application does not currently seem to request `offline_access`, but
the cap should ideally be configurable or documented as platform
security policy.

# 7. Security findings still open

**7.1 Bidirectional LDAP group synchronisation.** `conn.modify()`
results are now checked and logged, but the two writes remain
independent (group update; member update). One can succeed and the
other fail, creating a divergence between `uniqueMember` and
`uniqueMemberOf`. *Partially resolved.* A compensation, authoritative
reconciliation or explicit retry strategy remains necessary.

**7.2 LDIF information in process arguments.** `generate_ldif.py` can
read passwords from environment variables, and the smoke test uses the
mechanism correctly. However `docker/init.sh` still builds a Bash
array carrying the hashes or passwords, names, e-mail addresses,
birthdates and descriptions, expanded as classic positional arguments
— not NUL-separated variables, contrary to the script's comment.
*Partially resolved.* The configuration should cross through a 0600
temporary JSON file, standard input, or file descriptors.

**7.3 Periodic task inside NewRequest.** The verifier reminders are
still triggered inside the HTTP request cycle: no guarantee of
execution without traffic, multi-process coordination, single
execution after restart, or absence of slowdown on the triggering
request. *Open.*

**7.4 Outdated .env.example.** Still `MAIL_USE_TLS`/`MAIL_USE_SSL`
where the application reads `MAIL_TLS`/`MAIL_SSL`; still describes
`LDAP_SERVER` as a URL with scheme and port while the code uses a
separate host and port; the new `LDAP_CA_CERT_FILE` is absent. *Open.*

# 8. Build chain: remaining reserves

The previous pass's improvements hold: three separate locks; hashes;
multi-stage images; base image digests; no quality tooling in the
runtime; Docker smoke test; Gitleaks; the three locks audited.

Still open: **editable installation** (an application wheel would suit
an immutable image better); **native wheels** (the builder may compile
a source dependency whose shared libraries the final image lacks —
`--only-binary=:all:` would make the assumption explicit); **unfrozen
APT packages** (digest-pinned bases, but `apt-get` still fetches
build-time versions; the Python build is strongly reproducible, the
system layer not yet bit-for-bit).

# 9. Quality and technical debt

Deliberately progressive: mypy informative, not blocking; Ruff limited
to Pyflakes; `F841` still ignored; coverage floor at 68%; CSP to
enable and test; Certbot renewal not covered by the smoke test. No
longer delivery blockers — the next industrialisation debt.

# 10. Revised priorities

**P0 — closed**: Docker startup; Waitress configuration; Apache
routing; HTTPS smoke test; secret detection.

**P1 — closed**: separate locks; hashes; multi-stage image; minimal
runtime; pinned base images.

**P2 — largely addressed.** Resolved: LDAP cache; LDAPS certificate
validation; refresh token confidentiality; Keycloak response
validation. Still open: 1. actually enable LDAPS in the production
stack; 2. test a full LDAP TLS negotiation; 3. make the group
synchronisation coherent; 4. remove the LDIF data from `argv`.

**P3 — operations**: 1. move the reminders out of `NewRequest`;
2. fix `.env.example`; 3. document and mount private LDAP
authorities; 4. make the Keycloak maximum lifetime configurable;
5. introduce a dedicated refresh-token encryption key.

**P4 — finishing**: 1. build an application wheel; 2. freeze or
snapshot the APT dependencies; 3. enforce Python wheels; 4. make mypy
progressively blocking; 5. raise Ruff and coverage; 6. test Certbot
and the CSP.

# 11. Conclusion

Commit `2c53ef8…` closes several of the most important application
risks still present. The most significant advances: an LDAPS server
can no longer be accepted without certificate validation; one LDAP
configuration no longer pollutes connections using other parameters;
the refresh token is no longer exposed in clear in the cookie; a
malformed or inconsistent Keycloak response is cleanly rejected.

The main nuance concerns LDAP: the LDAPS mechanism is now safe when
enabled, but the shipped stack still uses unencrypted LDAP by default.

The major risks now concentrate on: the actually deployed LDAP
transport; the coherence of group writes; the sensitive data passed
through `argv`; the periodic tasks; a few reproducibility and security
policy aspects.

**Current evaluation: 8.5/10.** A grade around 8.8 to 9.0/10 would
become justified after enabling and testing LDAPS in Compose, fixing
the LDIF generator and transactionally securing the LDAP groups.
