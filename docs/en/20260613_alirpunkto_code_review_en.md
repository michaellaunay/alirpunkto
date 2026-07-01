# Code review — AlirPunkto — **update** (2026-06-26 dump)

> Original audit: `20260613_revue_de_code_alirpunkto.md` (2026-06-12 dump).
> This version revisits each point and states its status after verification against the **2026-06-26** dump.
> Line numbers = each file's internal numbering in the **new** dump.
> **Revision of 2026-06-27**: incorporates the fixes applied *after* the 2026-06-26 dump — **1.4** (LDAP filter injection), **1.6** (constant-time admin comparison), **1.7** (template traversal in `get_email`), **1.8** (user enumeration), **1.9** (link expiry via Fernet TTL), **1.10** (`decrypt_oid` failing cleanly), **1.11** (branding read from settings instead of `request.params`), **2.5** (`elections_view` crash) and **§4.14** (`get_member_by_email` annotation) are now fixed.
>
> **Revision of 2026-06-30**: full rebuild of the test suite (97 tests green; a `MemberRoles.get_i18n_id` consistency fix along the way), then fixes **2.2** (`get_access_permissions` *fail-closed* + logging of uncovered cases, and admin reading of candidatures), **2.1** (re-enabling the `voter` branch via comparison on `oid`s) and **2.3** (vote persistence via `_p_changed`, `vote_view` rename, robust session reads, LDAP result checked before approval, and vote *deadline* control).

> **Revision of 2026-06-30 (cont.)**: fixes **2.9** (`register_user_to_ldap` return contract normalized to `{'status':'error',…}`) and **2.10** (LDAP group DNs made consistent with group creation, PROVIDER unified on `providersGroup`, anti-`NameError` guard).

> **Revision of 2026-06-30 (cont. 2)**: fixes **2.6** (`update_ldap_member`: mapping unified on model names, `AttributeError`s raised, `MODIFY_REPLACE` instead of `MODIFY_DELETE`, non-mutable default argument) and **2.7** *partial* (`modify_member`: LDAP result correctly interpreted, password actually written via `update_member_password`, correct email template; type casting still pending).

> **Revision of 2026-07-01**: **§2 blocking-bugs section fully addressed** (2.1–2.12). Fix of the `lang2`/`lang3` block of **2.6** (scrambled during application: loss of the 2nd language and a residual `MODIFY_DELETE` — restored to `MODIFY_REPLACE` of the correct value), **2.7** *completed* (form values cast to the field's declared type via `get_type_hints(MemberDatas)`, with input-error handling), **2.4** (`manage_provider`: duplicate detection by email, full rewrite of the "update" branch, editable fields + `update` action in the template), **2.11** (password validator un-inverted via an adapter to `colander.Function`'s contract), **2.12** (the four `get_i18n_id` branches finally interpolate `name.lower()`), **2.8** (`KeyError` on `/logout?username=` removed) and **2.13** (robust SSO refresh: access token stored in session, `None` and expiry handled), **2.14** (`Members.get_instance` bound to the provided connection, end of cross-connection reuse) and **2.16** (`get_secret`: `os.environ.pop` instead of `del`, no more `KeyError` masking the `ValueError`) and **2.17** (`validate_challenge`: a missing answer counts as incorrect instead of raising `KeyError`). **The §2 blocking-bugs section is thereby fully addressed** (2.1–2.17 fixed; only 2.15/2.18 remained partially mitigated). **Then 2.15** (LDAP: host/port resolved at call time, SYNC singleton replaced by a fresh connection per call) and **2.18** (verifier-reminder scan throttled + locked) were completed: **all 18 §2 findings are now fixed**, each locked by tests. **Above all, a regression test suite was added for all these fixes**: 108 tests across 19 files, taking the suite from 97 to **205 green tests**; each test was verified to *fail* on the pre-fix code. See the new "Regression tests" section.

**Legend:** ✅ fixed · ⚠️ partial / mitigated · ❌ not fixed · 🆕 regression introduced since 2026-06-12

## Remediation history (git repository)

Mapping between repository commits and audit fixes, in chronological order. `§` refers to the finding number addressed below.

| Commit | Date | Fix | Finding |
|---|---|---|---|
| `05d3173` | 2026-06-13 | Encrypt passwords before DEBUG logging | §1.2 |
| `f1a88a8` | 2026-06-13 | Remove passwords from logged attributes | §1.2 |
| `b6458c6` | 2026-06-13 | Harden session cookie attributes | §1.1 |
| `9841a1c` | 2026-06-16 | CSRF protection on all mutating requests | §1.5 |
| `f453878` | 2026-06-27 | Escape inputs in LDAP filters | §1.4 (CWE-90) |
| `c3d603e` | 2026-06-27 | Constant-time comparison of admin credentials | §1.6 (CWE-208) |
| `0a40853` | 2026-06-27 | Validate `email_id` against template traversal | §1.7 (CWE-22) |
| `2e91661` | 2026-06-27 | Account anti-enumeration on password reset | §1.8 (CWE-204) |
| `39c7406` | 2026-06-27 | Reset/verification link expiry + *fail-closed* | §1.9 (CWE-613), §1.10 partial |
| `f5ca0d3` | 2026-06-27 | Harden `get_candidature_from_request` (invalid oid) | §1.10 (CWE-755) |
| `e0a9275` | 2026-06-27 | Branding read from constants + elections crash fix | §1.11 (CWE-601), §2.5 |
| `9e4f485` · `2832005` | 2026-06-30 | `MemberRoles.NONE` case in `get_i18n_id` | §2.12 (cousin) |
| `0786e92` | 2026-06-30 | Exclude private keys/certificates from source export | tooling hardening |
| `278d8be` | 2026-06-30 | Test suite rebuild (97 green) | test rebuild |
| `014525b` | 2026-06-30 | *Fail-closed* permissions + admin reading of candidatures | §2.2 |
| `d1e6d81` | 2026-06-30 | Re-enable the `voter` branch in `get_access_permissions` | §2.1 |
| `72848b9` | 2026-06-30 | Vote persistence + approval after LDAP success | §2.3 |
| `9851714` | 2026-06-30 | Close voting at the deadline | §2.3 |
| `6211c8d` | 2026-06-30 | Normalized LDAP return contract + consistent group DNs | §2.9, §2.10 |
| `f5af346` | 2026-07-01 | `modify_member`: LDAP result interpreted + password written | §2.7 |
| `2e55125` | 2026-07-01 | `update_ldap_member`: mapping on model names + `lang2`/`lang3` block | §2.6 |
| `a74e7de` | 2026-07-01 | Cast form values to the field's declared type | §2.7 |
| `6c4fe05` | 2026-07-01 | Repair the provider create/update branches | §2.4 |
| `bed73b3` | 2026-07-01 | Fix the inverted password validator | §2.11 |
| `a274cab` | 2026-07-01 | Interpolate `name` in the `get_i18n_id` fallbacks | §2.12 |
| `7774ec8` · `bd28bbb` · `8763cbb` · `233313a` | 2026-07-01 | Regression test suite (§2.1/2.2/2.3/2.6/2.7/2.9) | §2 tests |
| `0f96f3c` | 2026-07-01 | `logout`: safe session-key removal (`pop` instead of `del`) + tests | §2.8 |
| `fd3b14a` | 2026-07-01 | SSO: access token stored in session + robust refresh (`None`, expiry) | §2.13 |
| `46f3fac` | 2026-07-01 | `Members.get_instance` bound to the provided connection (end of cross-connection sharing) | §2.14 |
| `2532bf1` | 2026-07-01 | `get_secret`: `os.environ.pop` instead of `del` (no more `KeyError`) | §2.16 |
| `e184d28` | 2026-07-01 | `validate_challenge`: missing answer = incorrect (no more `KeyError`) | §2.17 |
| `b054be1` | 2026-07-01 | LDAP: host/port resolved at call time + fresh connection per call | §2.15 |
| `aa74de4` | 2026-07-01 | Throttle + lock the verifier-reminder scan | §2.18 |
| `946a65e` | 2026-07-01 | Configurable reminder interval (`VERIFIER_REMINDER_MIN_INTERVAL_SECONDS`, default 72h) | §2.18 |
| `cd9c558` | 2026-07-01 | Remove the mid-view explicit commit (candidate form rendering) | §3 (register) |
| `7613940` | 2026-07-01 | Remove the 6 other explicit commits in `register.py` (transaction-aware mailer) | §3 (register) |
| `4d7a045` | 2026-07-01 | Restore the LDAP guard around `random_voters` (`prepare_for_cooperator`) + tests | §3 (register) |
| `5faf180` | 2026-07-01 | Remove the 7 explicit commits in `forgot_password.py` (transaction-aware mailer) | §3 (forgot_password) |
| `14ca621` | 2026-07-01 | Remove the 4 explicit commits in `modify_member.py` (transaction-aware mailer) | §3 (modify_member) |
| `6d43891` | 2026-07-01 | Remove the 4 commits + 2 aborts in `vote.py` (`_p_changed` preserved) | §3 (vote) |
| `8cfbe99` | 2026-07-01 | Remove the 2 explicit commits in `manage_provider.py` (transaction-aware mailer) | §3 (manage_provider) |
| `501e3e9` | 2026-07-01 | Remove the explicit commit in `check_new_email.py` (`get_instance` preserved) | §3 (check_new_email) |

---

## Summary

Three security workstreams had already been addressed in the 2026-06-26 dump: the session secret (1.1), passwords in logs (1.2) and CSRF protection (1.5). **Since then, seven more vulnerabilities have been fixed**: LDAP filter injection (1.4), admin credential comparison (1.6), template traversal in `get_email` (1.7), user enumeration (1.8), link expiry (1.9), clean failure of `decrypt_oid` (1.10) and branding read from settings rather than `request.params` (1.11) — plus the `get_member_by_email` annotation (§4.14) and, on the blocking-bugs side, the `elections_view` crash (**2.5**, now fixed although the view remains a *stub*). A utility `encrypt_secret_for_logs()` was added to `secret_manager.py` and is used everywhere a password was previously logged in cleartext. **In section 1, only 1.3 remains** (cleartext passwords in LDAP/ZODB). **The entire §2 blocking-bugs section (2.1 to 2.18) is now fixed** — all 18 findings, each locked by regression tests. Unchanged: the transaction issues (§3), most of the minor bugs (§4) and the quality debt (§5). The standout of the latest pass is the addition of a **regression test suite covering every §2 fix** (108 tests, suite taken from 97 to 205 green): the absence of tests had precisely let a bad application of fix 2.6 slip through (scrambled `lang2`/`lang3` block → loss of the 2nd language), since corrected and locked by a parametrized test. A small cosmetic regression remains in `register.pt` (CSRF token rendered as `type="d-none"`).

| Section | Fixed | Partial | Not fixed |
|---|---|---|---|
| 1. Critical security | 1.1, 1.2, **1.4**, 1.5, **1.6**, **1.7**, **1.8**, **1.9**, **1.10**, **1.11** | — | 1.3 |
| 2. Blocking bugs | **2.1**–**2.18** (all 18) | — | — |
| 3. Transactions | **6 views cleaned (24 commits/aborts removed) + `get_instance` justified** | — | — |
| 4. Minor bugs | **§4.14** | §4.18 | §4.1, §4.31, … (unchanged) |
| 5. Quality | — | — | typos, pkg_resources, pytz, types… |

---

## 1. Critical security vulnerabilities

### 1.1 Session cookie signed with a public constant — ✅ **fixed**
`__init__.py` l.184: `hash_object.update(get_secret(SECRET_KEY).encode('utf-8'))` — the secret's **value** is now used. The factory also sets `httponly=True, secure=True, samesite='Lax'` (l.185). Matches the proposed fix.

### 1.2 Passwords in cleartext in logs — ✅ **fixed**
New utility `encrypt_secret_for_logs()` (`secret_manager.py` l.59). Applied:
- `views/login.py` l.125: `…with {encrypt_secret_for_logs(password)=}`;
- `views/forgot_password.py` l.221: same, + a `log.info` without password;
- `utils.py::register_user_to_ldap` l.987-988: `safe_attributes` removes `userPassword` from the dict before logging, and the explicit password is encrypted.

### 1.3 Passwords stored in cleartext — ❌ **not fixed**
- **LDAP**: `register_user_to_ldap` l.931 still sends `'userPassword': password` in cleartext; `update_member_password` l.1055 does a `MODIFY_REPLACE` with the raw password. No `hashed()` or `modify_password` in the code (only the LDIF bootstrap accounts are pre-hashed `{SSHA}`).
- **ZODB**: `register.py` l.534-535 still copies every `request.params` field matching `MemberDatas.__dataclass_fields__` (including `password`/`password_confirm`), and no `del data.password` was added after LDAP creation. The candidate's password stays in cleartext in the database.

### 1.4 LDAP filter injection — ✅ **fixed** (post-dump, 2026-06-27)
`escape_filter_chars` (from `ldap3.utils.conv`) now wraps every user-controlled value in the five affected filters:
- `utils.py::get_member_by_email`: `f'(mail={escape_filter_chars(email.strip())})'`;
- `utils.py::is_valid_unique_pseudonym`: `f"(cn={escape_filter_chars(pseudonym)})"`;
- `utils.py::update_member_from_ldap`: `f'(uid={escape_filter_chars(oid)})'`;
- `utils.py::get_oid_from_pseudonym`: `f'(cn={escape_filter_chars(pseudonym)})'`;
- `views/login.py::check_password`: `f'(uid={escape_filter_chars(oid)})'`.

Static filters (`(objectClass=*)`, `(&(employeeType=cooperator)…)`) have no user input and remain unchanged. The dead import `get_ldap_server` was removed from `utils.py` along the way.

### 1.5 CSRF not verified — ✅ **fixed**
- `__init__.py` l.187: `config.set_default_csrf_options(require_csrf=True)` — global protection active on all POSTs.
- All hand-written forms now carry the token: `login.pt`, `forgot_password.pt`, `manage_provider.pt`, `modify_member.pt`, `register.pt`, `vote.pt`, etc.
- *Secondary remainder*: `register.py` l.470 keeps `#form.validate(items)` commented out (colander schema validation still absent), but this is no longer the CSRF protection mechanism. See also 🆕 below (`register.pt`).

### 1.6 Non-constant-time admin password comparison — ✅ **fixed** (post-dump, 2026-06-27)
`utils.py::is_admin` now compares login and password via `hmac.compare_digest` (constant-time) on their UTF-8 bytes:
- no more short-circuiting `==` comparison → timing leak closed;
- `utf-8` encoding (`compare_digest`'s `str` mode only accepts ASCII and would raise `TypeError`);
- `.strip()` removed from the password (leading/trailing spaces are significant again; kept on the login, harmlessly);
- both comparisons are evaluated before being combined, so the login result does not leak via timing either.

`hmac` import added.

### 1.7 `get_email`: illusory anti-injection + URL-driven rendering — ✅ **fixed** (post-dump, 2026-06-27)
- **Traversal closed**: `email_id` is now validated by `VALID_EMAIL_ID = re.compile(r'[a-z0-9_]+')` via `fullmatch` before building `f"{email_id}.pt"`. No more `/`, `\` or `.` possible → impossible to escape `LC_MESSAGES`.
- **Blocklist removed**: the `"python" in value` + `eval(|exec(|__import__` test is gone. It protected nothing (`request.params` values are passed to the ZPT engine as data, not as template source) and rejected legitimate inputs containing "python".
- **Template variables**: already restricted to `expected_variables ∩ params` (unchanged).

### 1.8 User enumeration — ✅ **fixed** (post-dump, 2026-06-27)
The five exit points of the `'submit'` step of `forgot_password.py` (unknown address, admin account, LDAP load failure, success, send failure) now return a **strictly identical** dict: `{"message": _('forget_email_sent'), "member": None, "form": None}`. The template therefore renders the same page in every case — including form visibility, which depends on `not member`. The email is only sent if the account exists; the other cases are logged server-side.

> **⚠️ Follow-up required**: `forget_email_sent` is now displayed even without a matching account. Its wording must stay **neutral** ("*if* an account exists, a link was sent") and not assert that an email was actually sent. See the *Follow-up* section at the end of the document.
>
> **Residual limit (timing)**: the "account exists" path stays slower (LDAP reads, `commit`, send) → enumeration possible via response time. Separate workstream (background sending).

### 1.9 Reset links without expiry — ✅ **fixed** (post-dump, 2026-06-27)
`decrypt_oid` now passes a `ttl` to `fernet.decrypt(decoded, ttl=ttl)`. Since the Fernet token is timestamped at creation (`encrypt_oid`), any link older than the TTL is rejected. The delay is carried by a new constant `OID_LINK_TTL_SECONDS` (24h by default, overridden by the env var `ALIRPUNKTO_OID_LINK_TTL_SECONDS`), read **on every call** (parameter `ttl=None` then read in the body → no frozen default, overridable per call and testable via monkeypatch).

### 1.10 `decrypt_oid` raises instead of returning `None` — ✅ **fixed** (post-dump, 2026-06-27)
`decrypt_oid` now wraps decode and decrypt in a `try/except (InvalidToken, ValueError, TypeError)` and returns `(None, None)` on any invalid, malformed or expired token (`Fernet(secret)` stays outside the `try` so a misconfigured key surfaces). This contract matches what the callers already expected: the `is None` branch of `check_new_email` (until now unreachable) becomes active, and both `retrieve_candidature` and `forgot_password._retrieve_member` already test `None` → a forged/expired `?oid` shows a clean page instead of a 500. The only unguarded caller, `get_candidature_from_request` (which was **dead code**), was hardened: all its failure modes return `None`, and the generic `raise Exception("Seed mismatch")` was removed.

### 1.11 `site_name` / `domain_name` taken from the request — ✅ **fixed** (post-dump, 2026-06-27)
The three views that read these values from `request.params` — `login_view`, `sso_login.callback_view` and `elections_view` — now read the trusted constants `SITE_NAME` / `DOMAIN_NAME` / `ORGANIZATION_DETAILS`. No more reading these keys from `request.params`: the spoofing/phishing vector is closed. The constants have default values (also fixes emails that displayed `None`). The env key `organization_details` is normalized to `ORGANIZATION_DETAILS` (see *Follow-up* for the deployment caveat). Note: the `request.registry.settings.get('site_name'…)` reads present in other views are a distinct and **trusted** source (server config), out of scope.

---

## 2. Blocking bugs — ✅ **section fully fixed** (2.1–2.18)

### 2.1 Verifiers without permissions — ✅ **fixed** (post-dump, 2026-06-30)
The `voter` branch of `get_access_permissions` tested `accessor.oid in accessed.voters` — a `str` compared to a list of `Voter` (dataclass), hence **always `False`**: dead branch, the voter fell into the generic branch and, since 2.2, received `NO_MEMBER_PERMISSIONS` (denial). Fixed to `accessor.oid in {voter.oid for voter in accessed.voters}`. Empirically verified: a voter now gets `access['voter'][state]` for the seven candidature states (no warning), while a non-voter stays denied and traced (2.2 behavior unchanged).

### 2.2 `KeyError` on many (role, state) pairs — ✅ **fixed** (post-dump, 2026-06-30)
`get_access_permissions` did five direct-index accesses `access[…][…]`, exposed to `KeyError`/500. They now go through a helper `_resolve_permissions(outer, inner)` that: returns the cell if the pair exists; otherwise **logs a `warning`** identifying the missing pair and returns the *deny-all* fallback `NO_MEMBER_PERMISSIONS` (all fields `Permissions.NONE`). Two benefits: *fail-closed* (a hole denies instead of crashing) **and** visibility — any gap is traced for immediate debugging. Empirically verified: key present → object identical (`is`) to the old access, no warning; key absent → `NO_MEMBER_PERMISSIONS` + one warning.

In addition, the matrix was **extended for the administrator**: a new profile `ADMIN_CANDIDATURE_PERMISSIONS` (read-only on all candidature fields; fields inherited from the member reuse the `ADMIN_MEMBER_PERMISSIONS` policy, so IBAN masked and `seed` not readable) is wired to `access['Administrator']` for the seven candidature states. An administrator can therefore view an in-progress candidature (the 28 non-owner crashes are replaced by a read for the admin, a traced denial for other roles). Remaining gaps (`Owner` combinations not encountered in the registration flow, `Ordinary`/`Cooperator`/`Provider` access to a candidature) return a logged denial — see *Follow-up*.

### 2.3 Vote probably never persisted — ✅ **fixed** (post-dump, 2026-06-30)
Four points addressed in `vote.py`: (1) **persistence** — `voter.vote = vote` mutates a `Voter` (dataclass) nested in a persistent `Candidature`'s `_voters` list without marking it *dirty*; added `candidature._p_changed = True` right after. **Proven against real ZODB** (`FileStorage` reopened): without the flag the re-read vote is `None` (lost), with the flag it is properly persisted. (2) **rename** of the `login_view` view → `vote_view` (copy-paste); (3) session reads `request.session['site_name'/...]` → `.get(..., SITE_NAME/DOMAIN_NAME/ORGANIZATION_DETAILS)`, no more `KeyError` (consistent with 1.11); (4) **`register_user_to_ldap` result checked** — approval only happens if the return is `{'status': 'success'}` (defensive test `isinstance(...) and .get('status')=='success'`, robust to the 2.9 contract inconsistency); otherwise error log, `abort()` and a message to the user, the candidature **no longer** becomes `APPROVED` on LDAP failure. Verified by driving `vote_view` (failure → stays `PENDING` + vote kept; success → `APPROVED`; non-dict return → stays `PENDING`). Full suite 97/97. **Vote deadline control then implemented** (post-dump, 2026-06-30): if `candidature.verification_deadline` has passed, `vote_view` returns a `voting_period_ended` error and the template hides the form (absent deadline ⇒ no blocking; *naive deadline* normalized to UTC) — verified across 5 cases. Remaining functional points (see *Follow-up*): YES/NO equality semantics, `str` vs `VotingChoice` typing, result computation at the deadline, and adding the i18n key.

### 2.4 `manage_provider.py` broken create/update branches — ✅ **fixed** (post-dump, 2026-07-01)
Several bugs addressed. **"create" branch**: `provider_email in providers` (where `providers` is a list of `User` objects, hence always false) → `any(existing.email == provider_email for existing in providers)`; the dead `get_member_by_oid(provider_email, …)` (email used as oid, always `None`) was removed. **"update" branch**, entirely rewritten: removal of `RegisterForm(request, schema=…, member=…)` (nonexistent constructor), of `form.validate`/`form.get_data` and of the dead `manage_provider_schema`; it now reads `provider_email`/`provider_password` from `request.params`, validates via `is_valid_email(new_email, request)` and `is_valid_password`, updates the email via `update_ldap_member(request, member, fields_to_update=['email'])` (3rd argument = **list of field names**, not a dict), the password via `update_member_password`, sets the valid state `MemberStates.DATA_MODIFIED` (the old `MemberStates.ACTIVE` did not exist → `AttributeError`) and commits. **Template** `manage_provider.pt`: the "modify" form gains editable fields `provider_email`/`provider_password` and its button posts the **`update`** action (it posted `submit`, which the view did not listen for → the branch was unreachable). Three new `msgid`s (`provider_update_failed`, `provider_new_email_label`, `provider_new_password_label`). *Remaining (optional) cleanup*: imports/declarations now unused in the view (`RegisterForm`, `deform`, `Translator`, `manage_provider_schema`, etc.). Covered by `tests/test_manage_provider.py` (8 tests).

### 2.5 `elections.py` guaranteed crash — ✅ **fixed** (post-dump, 2026-06-27)
`get_candidatures(request)` now receives the `request` argument → no more `TypeError`/500 for a logged-in user. **Caveat**: the view remains a *stub* — it always returns `{"elections": []}`, the `candidatures` result is assigned but unused (F841), and `logged_in`/`username` are still read from `request.params`. The election-filtering logic is still to be written (TODOs left). See *Follow-up*.

### 2.6 `update_ldap_member` inconsistent mapping — ✅ **fixed** (post-dump, 2026-06-30)
Mutable default argument replaced by `None` + list built in the body with the **model names** (those the body tests and the callers push). `'data.fullsurname'` → `'fullsurname'`; `'uniqueMemberOf'` → `'unique_member_of'` (+ `member.data.unique_member_of`); `member.data.dateErasureAllData` → `member.data.date_erasure_all_data` (no more `AttributeError`). `cooperativeBehaviourMark` cast to `str`. `MODIFY_DELETE` (which failed on an absent attribute) replaced by `MODIFY_REPLACE` with an empty value (removes if present, no-op otherwise). Verified by running the function (LDAP mocked): a default call now builds **18 attributes** (vs ~4), `sn` is present, `cooperativeBehaviourMark` is a `str`, and empty languages go through `MODIFY_REPLACE`. **Follow-up fix (2026-07-01)**: during application the `lang2`/`lang3` block had been **scrambled** — the "`lang2` set" case wrote `secondLanguage` **empty** (loss of the 2nd language), the "`lang2` empty" case targeted `thirdLanguage` (wrong attribute), and the empty `lang3` kept a `MODIFY_DELETE`. Restored: language set → `MODIFY_REPLACE [value]`, empty → `MODIFY_REPLACE []`, on the correct attribute. A beneficial side effect observed in `tests/test_ldap_utils.py` (parametrized on the `lang2`/`lang3` combinations): this is exactly the test that should have existed to catch the regression.

### 2.7 `modify_member.py` misinterpreted return + inoperative password — ✅ **fixed** (post-dump, 2026-06-30 → completed 2026-07-01)
Fixed: (a) `if not sending_success` → `if fields_to_update and sending_success.get('status') != 'success'` (the return of `update_ldap_member` is always a *truthy* dict — an LDAP error was taken for a success); (b) **password branch**: after `is_valid_password`, the error is tested **and** `update_member_password` is now called with its return checked (the change had no effect); (c) `email_template` `"reset_password_email"` → `"check_new_email"` (the actual template sent), and send status set on `accessed_member` (not `member`); (d) `flash` fixed (message 1st, `'error'` queue 2nd); (e) same return bug in `check_new_email.py` (`if result is None` → test on `status`). **Type casting now implemented (2026-07-01)**: the `#@TODO cast the value to the right type` is resolved by a helper `_coerce_member_data_value(field, raw)` that converts the form value (always a `str`) to the field's declared type, resolved once via `get_type_hints(MemberDatas)` (`bool`/`int`/`float`); on invalid input (e.g. `"abc"` for `number_shares_owned`), the view returns `invalid_field_value` (new `msgid`) without writing anything. Beneficial side effect: the `getattr(...) != requested_value` comparison now happens between values of the same type, avoiding superfluous LDAP updates (`"5" != 5` was always true). Verified: compile + targeted checks. Covered by `tests/test_modify_member.py` (8 tests, including the int/float/bool cast and rejection of an invalid value) and `tests/test_check_new_email.py` (3 tests).

### 2.8 `logout`: `KeyError` on `?username=` — ✅ **fixed** (post-dump, 2026-07-01)
`logout` read `username` from `request.params` then did `del request.session['username']` — but this key is **never** set in the session (the only occurrence of `'username'` in the code is the Keycloak token payload). `/logout?username=X` therefore raised a `KeyError` (500). The URL-parameter-driven block is replaced by an unconditional and safe `request.session.pop('username', None)`; the function's other removals were already guarded by `if X in request.session`. Covered by `tests/test_logout.py` (4 tests).

### 2.9 `register_user_to_ldap` inconsistent return contract — ✅ **fixed** (post-dump, 2026-06-30)
The "invalid pseudonym" path returned the `{'error': …}` from `is_valid_unique_pseudonym` as-is (without a `status` key), while callers read `result['status']` (and `register.py` also reads `result['message']`) → `KeyError`. Normalized to `{'status': 'error', 'message': error.get('error'), **error}`: this honors the contract of the function's other returns while keeping `error`/`error_details`. Verified by running the function with an invalid pseudonym → `{'status':'error','message':…,'error_details':…}`.

### 2.10 Inconsistent group DNs — ✅ **fixed** (post-dump, 2026-06-30)
Three points: (a) a PROVIDER's `uniqueMemberOf` pointed to `providerMembersGroup` whereas the group created/modified is `providersGroup` → unified on `providersGroup`; (b) the six group DNs re-prefixed `ou={LDAP_OU}` whereas group creation (`__init__.py` l.159-160) and the user DN use `{LDAP_OU}` directly → `ou=` prefix removed, the DNs now target where the groups actually exist; (c) `group_dn` was not defined for ADMINISTRATOR/`_` → potential `NameError` in the final log, fixed by `group_dn = None` + guard `if group_dn is not None`. Verified by running `register_user_to_ldap` with a mocked LDAP connection: for COOPERATOR/ORDINARY/PROVIDER the DN passed to `conn.modify` is **identical** to the one created by `__init__.py`, and `uniqueMemberOf` points to the same DN; ADMINISTRATOR does no `modify` and does not raise.

### 2.11 Inverted password validator — ✅ **fixed** (post-dump, 2026-07-01)
`colander.Function` raises `Invalid` when the callback returns a *falsy* value (or a string, used as the message) and considers a *truthy* non-string return valid; `is_valid_password` does the opposite (`None` = valid, error dict otherwise). A **valid password was therefore rejected** and an **invalid one accepted** (demonstrated with the real colander). Fixed by an adapter `_validate_password(value)` returning `True` if valid and the error message otherwise; `schemas/register_form.py` l.173 becomes `validator = colander.Function(_validate_password)`. No new `msgid` (the `_('invalid_password')` fallback already exists). Covered by `tests/test_register_form.py` (5 tests, including one on the schema's real `password` field validator). *Note*: the bug was harmless so far because `form.validate` remains commented out (cf. 1.5).

### 2.12 `get_i18n_id`: `return(f"name.lower()")` — ✅ **fixed** (post-dump, 2026-07-01)
The four default branches (`case _`) that returned the literal string `"name.lower()"` (an f-string without braces) now interpolate `name.lower()` with each class's i18n prefix: `MemberStates` → `member_state_…`, `MemberTypes` → `member_types_…`, `Permissions` → `access_permissions_…`, `CandidatureStates` → `candidature_states_…` (mirroring the two already-correct fallbacks, `MemberRoles`/`role_types_…` and `VotingChoice`/`vote_types_…`). These branches are "should never happen" fallbacks preceded by a `log.error`; the prefix is adjustable if another convention is preferred. Covered by `tests/test_get_i18n_id.py` (8 tests, including a sweep verifying no branch returns the literal any more). **Note**: the rebuilt suite no longer freezes this behavior — the old `tests/test_views.py` (which asserted `== "name.lower()"`) no longer contains those assertions, and the full suite passes (205) with the fix.

### 2.13 Fragile SSO refresh — ✅ **fixed** (post-dump, 2026-07-01)
The access token was never kept: `SSO_TOKEN` (session key) was written nowhere, and the `request.headers['Authorization'] = f'Bearer {sso_token}'` (in `home.py`, `login.py` **and** `sso_login.py`) have no effect — they modify the *incoming* request and embed the whole **dict**, not the token. Fixed: the three views now store `sso_token['access_token']` (the string) in `request.session[SSO_TOKEN]` (consistent with the logout purge). In `home.py`, the `None` return of `refresh_keycloak_token` is guarded (clean logout instead of `TypeError` on `['access_token']`), and a missing expiry triggers an explicit logout instead of the `"2020-01-01T00:00:00"` default (which caused a silent logout). In `login.py`, `request.session[SSO_EXPIRES_AT] = sso_token[SSO_EXPIRES_AT]` (a `KeyError` — `SSO_EXPIRES_AT` is the string `"SSO_EXPIRES_AT"`, absent from the Keycloak dict) is replaced by a computation from `refresh_expires_in`, like the two other views. Covered by `tests/test_home_sso.py` (4 tests); the existing test `test_views.py::test_home_view_refreshes_valid_sso_token` was updated (it checks the token in session, no longer the header). **Remaining** (distinct improvement): the refresh happens on every home render as long as the *refresh token* is valid — limiting it to when the access token is near expiry would require tracking `expires_in` separately.

### 2.14 `Members.get_instance` cross-connection ZODB singleton — ✅ **fixed** (post-dump, 2026-07-01)
The block `if Members._instance is not None: return Members._instance` was evaluated **before** the `connection` argument: once the cache was set, every request got that object — bound to a previous (sometimes closed) connection — instead of its own connection's object, hence `ConnectionStateError`/stale reads. Fixed: the connection is tested **first**; if provided, `get_instance` always re-reads `connection.root()['members']` and refreshes `_instance`. Since the *root factory* (`set_root_factory(root_factory)`) calls `get_instance(connection=conn)` on every request, the connection-less call in `generate_unique_oid` sees the current request's instance. The liveness check `'test' in _instance` that **re-raised** the exception (leaving the dead instance cached) is replaced, on the connection-less path, by a cache purge + explicit `TypeError`. Cross-connection reuse — the concrete risk — is removed; the underlying thread-safety issue remains (class-attribute singleton, cf. "Not thread safe!"). Covered by `tests/test_members_get_instance.py` (5 tests, real ZODB with two connections).

### 2.15 `ldap_factory.py` global connection — ✅ **fixed** (post-dump, 2026-07-01)
Two concrete problems addressed. (1) **Default arguments evaluated at import**: `get_ldap_server(server_name=get_ldap_server_name(), port=get_ldap_server_port())` and `get_ldap_connection(ldap_server=…, ldap_port=…)` froze host/port at module load → changed to `None` and resolved in the body (at call time). (2) **Module-level SYNC singleton connection** (`_conn`), not thread-safe (ldap3 SYNC connections interleave requests/responses across threads) and moreover *unbound* by the caller's `with` → singleton removed, **a fresh connection created on each call** (the two SYNC/non-SYNC branches merged). `reset_ldap_connection` now only resets `_server`. *Accepted residual*: for high load, a real pool (`REUSABLE` strategy) would be preferable; the per-call connection is correct and sufficient here. Covered by `tests/test_ldap_factory.py` (4 tests).

### 2.16 `secret_manager.py`: unguarded `del os.environ[...]` — ✅ **fixed** (post-dump, 2026-07-01)
The six `del os.environ[...]` in `get_secret` (l.32/44-46/48/50) are replaced by `os.environ.pop(..., None)`. Defensive deletion of secrets after reading is thus idempotent: no more `KeyError` when a variable is absent, and for `SECRET_KEY` the explicit `ValueError("You must provide a base64 value for SECRET_KEY")` finally applies instead of being masked by the `del`. Covered by `tests/test_secret_manager.py` (3 tests).

### 2.17 `validate_challenge`: `request.params[label]` → `KeyError` — ✅ **fixed** (post-dump, 2026-07-01)
`register.py` l.401: `request.params[label].strip()` raised `KeyError` (500) when the answer field `result_{key}` was absent (answer left blank). Replaced by `request.params.get(label, '').strip()`: a missing answer is `''`, different from the expected answer → returns `invalid_challenge` (a missing answer counts as incorrect). Covered by `tests/test_validate_challenge.py` (4 tests).

### 2.18 `remind_pending_verifiers` on every request — ✅ **fixed** (post-dump, 2026-07-01)
Still subscribed to `NewRequest`, but the scan (O(n) over candidatures) no longer runs **on every request**: added a module-level throttle (`_REMINDER_MIN_INTERVAL_SECONDS = 600`, `_reminder_last_run`) — a cheap lock-free check first — and a non-blocking `threading.Lock` (`acquire(blocking=False)`) with double-check, so only one thread runs the scan at a time and it runs at most once every 10 min (end of concurrent double-sending). The `PYTEST_CURRENT_TEST` short-circuit and the `try/except` are kept. The interval is **configurable**: a `production.ini` setting `verifier_reminder_min_interval_seconds` (higher priority) or the environment/`.env` variable `VERIFIER_REMINDER_MIN_INTERVAL_SECONDS`, with a **default of 72h**. *Accepted residual*: this is in-process scheduling triggered by requests; a real scheduled task (cron/APScheduler) would remain ideal. Covered by `tests/test_reminder_throttle.py` (3 tests).

---

## Regression tests (added on 2026-07-01)

The absence of tests covering the §2 fixes had let at least one silent regression slip through (the `lang2`/`lang3` block of 2.6). A regression suite was therefore added — **one file per fix** — taking the suite from 97 to **205 green tests**. For each one, the test was verified to *fail* on the pre-fix code (bug temporarily reintroduced), guaranteeing it catches the regression.

| File | Tests | Finding(s) | Key points |
|---|---|---|---|
| `test_model_permissions_access.py` | 11 | §2.1, §2.2 | voter recognition (comparison on `oid`s), admin reading of candidatures (7 states), *fail-closed* denial of an absent cell |
| `test_vote.py` | 11 | §2.3, §3 | **vote persistence proven against real reopened `FileStorage`** (lost without `_p_changed`), deadline guard, session fallback, LDAP return at approval; §3: vote preserved on LDAP failure without `abort` (real ZODB), no more explicit commit/abort |
| `test_ldap_utils.py` | 10 | §2.6, §2.9 | 18 default attributes without `AttributeError`, corrected field names, `lang2`/`lang3` (anti-data-loss guard, never `MODIFY_DELETE`), invalid-pseudonym return contract |
| `test_modify_member.py` | 10 | §2.7, §3 | LDAP return interpretation, actual password write, **`int`/`float`/`bool` cast** and rejection of an invalid value; §3: no `request.tm.commit()` (LDAP success and failure) |
| `test_manage_provider.py` | 10 | §2.4, §3 | access guards, duplicate detection by email, email/password update, LDAP-failure surfacing; §3: create and update without `request.tm.commit()` |
| `test_get_i18n_id.py` | 8 | §2.12 | the four fallbacks interpolate, none returns the literal, known names resolve |
| `test_register_form.py` | 5 | §2.11 | validator adapter, behavior via `colander.Function`, real `password` field validator |
| `test_check_new_email.py` | 3 | §2.7, §3 | an LDAP failure (error dict **or** `None`) is no longer taken for a success; §3: success without `request.tm.commit()` |
| `test_logout.py` | 4 | §2.8 | `/logout?username=X` no longer raises, effective logout, SSO/oid key purge |
| `test_home_sso.py` | 4 | §2.13 | a failing refresh → logout **without crashing**, access token stored in session (not a header), expired/absent window → logout |
| `test_members_get_instance.py` | 5 | §2.14 | instance bound to the passed connection (`_p_jar`), two connections → two distinct objects, cache/`TypeError` fallback |
| `test_secret_manager.py` | 3 | §2.16 | absent `SECRET_KEY` → `ValueError` (not `KeyError`), absent passwords without crash, secrets removed from the environment |
| `test_validate_challenge.py` | 4 | §2.17 | missing answer → `invalid_challenge` (not `KeyError`), correct answers → `None`, wrong → error, `strip` |
| `test_ldap_factory.py` | 4 | §2.15 | host/port defaults at `None` (resolved at call time), no more `_conn` singleton, `reset` clears `_server` |
| `test_reminder_throttle.py` | 4 | §2.18 | short-circuit under pytest, at most once per interval, re-run after interval, `production.ini` setting takes precedence |
| `test_register_email_validation.py` | 3 | §3 | state → `CONFIRMED_HUMAN` without explicit commit, form always rendered (even on email failure), challenge error |
| `test_register_transactions.py` | 5 | §3 | no more `request.tm.commit()` (`commit_candidature_changes`, `handle_unique_data_state`); `prepare_for_cooperator` returns `voters_not_selected` if `random_voters()` raises (LDAP guard) |
| `test_register_cooperator_journey.py` | 1 | §3 / journey | **full cooperator journey** DRAFT → EMAIL_VALIDATION → CONFIRMED_HUMAN → UNIQUE_DATA → PENDING (handlers in sequence, boundaries mocked) |
| `test_forgot_password.py` | 3 | §3 | reset request → `DATA_MODIFICATION_REQUESTED`, password change → `DATA_MODIFIED`, unknown address → neutral message (§1.8); no `request.tm.commit()` |

These tests rely on the existing *fixtures* (`members_mapping`, `caplog`, `tmp_path`); LDAP and email sending are mocked, ZODB is real only for vote persistence. No new dependency.

---

## 3. Transaction consistency — ✅ **addressed** (6 views cleaned; `get_instance` kept as a justified bootstrap)

**30 explicit calls** to `transaction.commit()` / `request.tm.commit()` remained, combined with `pyramid_tm`, distributed as: `register.py` (7), `forgot_password.py` (7), `modify_member.py` (4), `vote.py` (4), `manage_provider.py` (2), `check_new_email.py` (1), `member.py` (1).

**Strategy adopted**: rely on `pyramid_tm` (one transaction per request, a single *commit* at the end of the request) and remove the explicit mid-view *commits*, except those genuinely needed (out-of-request context). An explicit *commit* in the middle of a view rebinds the ZODB objects to a finished transaction and causes inconsistent reads/renders.

> **Verified — transaction-aware email sending**: `send_email` uses `pyramid_mailer`'s `mailer.send()` ("*the message is not sent until the transaction is committed*"), and there is **no** `send_immediately` anywhere in the code. Emails therefore only leave on the current transaction's *commit*; removing an intermediate *commit* never sends them before persistence — on the contrary, the email and the state change become atomic (same transaction). The "email only after *commit*" constraint therefore did not require the intermediate *commits*.

**`register.py` — fully cleaned (7 *commits* removed)**. The 1st (`handle_email_validation_state`) caused the candidate-form rendering bug: `request.tm.commit()` placed just before rendering → the `CONFIRMED_HUMAN` section (pseudonym field) only appeared after a page **refresh** (the template even contained a notice describing this workaround). The 6 others (`commit_candidature_changes`, `handle_confirmed_human_state`, `prepare_for_cooperator`, `_notify_verifiers_of_submission` — per-voter *commit* in a loop —, and `handle_unique_data_state` ×2) all followed the same pattern "*commit* to flush the queued email then record the `SENT` status": redundant, since the *mailer* is transaction-aware (the email leaves on pyramid_tm's final *commit*, atomically with the state and the status). The explicit *commits* are removed; `prepare_for_cooperator`'s `try/except` is **kept** (it guards the LDAP call `random_voters()`, not the *commit*). Side effects fixed: the candidate form is always rendered (even if the confirmation email fails), and per-voter sends are batched on the final *commit*. The `try/except` of `handle_confirmed_human_state` and `handle_unique_data_state` are **kept** (the `ERROR` status tracking is preserved); the one in `commit_candidature_changes`, which only guarded `add_email_send_status`, was removed. **Point of attention**: the removal commit (`7613940`) had also mistakenly removed `prepare_for_cooperator`'s `try/except`, which guards the LDAP call `random_voters()` (directory connection + attribute reads — can raise); without it, an LDAP outage gave a 500 instead of the clean `voters_not_selected` error. The guard was **restored** in a follow-up commit, with tests. Covered by `tests/test_register_email_validation.py` (3) and `tests/test_register_transactions.py` (5).

**`forgot_password.py` — 7 *commits* removed**. Same diagnosis: intermediate persistence (member loaded from LDAP, creation/insertion into the `MEMBERS_BEING_MODIFIED` BTree, state changes) and email *flushes*, all redundant with pyramid_tm (transaction-aware mailer). No downstream code reads a value that would depend on a *commit* (all objects are live in the request transaction). The now-unused `transaction = request.tm` local is removed. The **anti-enumeration** responses (§1.8, identical `forget_email_sent` in every case) are preserved. Covered by `tests/test_forgot_password.py` (3: reset request → `DATA_MODIFICATION_REQUESTED`, password change → `DATA_MODIFIED`, unknown address → neutral message — each without `request.tm.commit()`).

**`modify_member.py` — 4 *commits* removed** (l.183/315/339/456) + unused `transaction` local. Intermediate persistence (`member_state` → `DATA_MODIFICATION_REQUESTED`, `new_email`, `member_state` → `DATA_MODIFIED`) and *flush* of the `check_new_email` email, redundant with pyramid_tm. The email block's `try/except` (`SENT`/`ERROR` tracking) is kept. Covered by `tests/test_modify_member.py` (2 §3 tests added: LDAP success → `DATA_MODIFIED`, LDAP failure → stays `DATA_MODIFICATION_REQUESTED`, each without `request.tm.commit()`).

**`vote.py` — 4 *commits* + 2 `abort()` removed** (`_p_changed` §2.3 **preserved**). The trickiest case: the *commit* at l.115 locked the vote **before** the LDAP attempt, and the `abort()`s (LDAP failure, email failure) rolled back the rest. Removing the *commit* alone would have been **dangerous** — an `abort()` on LDAP failure would then have wiped the vote. The two `abort()`s are therefore removed as well: on LDAP failure the view returns the error without aborting, and pyramid_tm commits the vote (marked *dirty* by `_p_changed`), the state staying `PENDING` for a retry. **Proven against real ZODB**: `tests/test_vote.py::test_vote_view_preserves_vote_when_ldap_fails_across_reopen` checks that the vote survives an LDAP failure (and fails if the `abort` is reintroduced without the *commit*). The existing persistence tests now commit explicitly after `vote_view` to simulate pyramid_tm's end-of-request *commit*.

**`manage_provider.py` — 2 *commits* removed** (l.135 create: `register_user_to_ldap` + the `provider_created` email; l.186 update: `member_state` → `DATA_MODIFIED`), redundant with pyramid_tm (transaction-aware mailer). Covered by `tests/test_manage_provider.py` (2 §3 tests: create → `provider_created`, update → `DATA_MODIFIED` + `provider_updated`, each without `request.tm.commit()`).

**`check_new_email.py` — 1 *commit* removed** (l.84) + `transaction` local. Persistence of the changes (confirmed new email, `member_state` → `DATA_MODIFIED`) after the LDAP update, with no email sending — redundant with pyramid_tm. Covered by `tests/test_check_new_email.py` (the success test now checks the absence of `request.tm.commit()`).

**`member.py` — the `Members.get_instance` *commit* is KEPT** (justified exception, not removed). It is not a view *commit*: it persists the `members` singleton mapping **upon its one-time creation** (bootstrap, §2.14). Empirically verified: removing it breaks 3 §2.14 tests with `ConnectionStateError: Cannot close a connection joined to a transaction` — the creation **must** be committed to leave the connection in a clean state (and so other connections/requests see the same mapping). It runs only once (never in steady state), causes no stale render, and secures the bootstrap of the core data structure. Kept and documented rather than removed.

**§3 complete**: the **24 explicit view *commits*/aborts** were removed (register, forgot_password, modify_member, vote, manage_provider, check_new_email) in favor of pyramid_tm; the only model *commit* (`get_instance`) is kept as a justified bootstrap.

---

## 4. Lower-severity logic bugs (verified points)
- **§4.14** ✅ **fixed** (post-dump): `get_member_by_email` is now annotated `-> List[Entry]` and its docstring describes the actual return (list of LDAP entries, empty if none).
- **§4.1** ❌ `(objectClass=*)` still present (6 occurrences, including `get_ldap_member_list` l.155 and startup).
- **§4.18** ⚠️ `vote.pt` now filters `password` **and** `password_confirm` (l.30), but remains a **blocklist**: `iban` and `date_erasure_all_data` are still exposed to voters. Switch to an allowlist.
- **§4.31** ❌ `get_majority_date` (`routes.py` l.33): still `timedelta(days=365*18)` instead of `relativedelta(years=18)`.
- The other points (§4.2 to §4.35, except §4.14) were not touched; they remain valid.

---

## 5. Quality, style, maintenance — ❌ **not fixed**
- **Typos** still present, including in identifiers: `REGISTRED` (≈23×), `allready` (≈3×), `Coulb` (`member.py` l.366)…
- **`pkg_resources`** still imported (`__init__.py` l.19, `resource_filename` l.278-279) — deprecated.
- **`pytz`** still used.
- **Type annotations** still largely misleading (`retrieve_candidature -> Union[Candidature, Dict]` but returns a tuple, `get_keycloak_token -> Optional[str]` but returns a dict, etc.); `get_member_by_email` was, however, corrected (§4.14).
- No `ruff`/`mypy`/per-view functional tests added.

---

## 🆕 Regressions / issues introduced since 2026-06-12
1. **`register.pt` l.207**: the CSRF token is rendered with `<input type="d-none" …>` instead of `type="hidden"`. An unknown type falls back to `text` → the field (and the token) is shown as an editable text box. The 9 other forms correctly use `type="hidden"`.
2. ~~**`tests/test_views.py`**: tests freezing `get_i18n_id` (`"name.lower()"`)~~ — ✅ **resolved**: bug 2.12 is fixed and the rebuilt suite no longer contains those assertions; the full suite (205) passes with the fix. Only the cosmetic **`register.pt`** regression (point 1) remains.

---

## Follow-up — debt left by the fixes (not to be forgotten)
- **1.8 — neutral wording (required)**: `forget_email_sent` is now displayed even when no account matches. Reword the i18n string (fr **and** en) into a neutral message — e.g. "If an account is associated with this address, a reset link has just been sent." — and **do not** assert that an email was sent. Without this, enumeration stays closed but the message lies to the legitimate user.
- **1.8 — orphan i18n key (optional nit)**: `forget_admin_user` is no longer referenced after the fix → remove it from the `.po`/`.pot`. (`forget_email_in_member_list` and `forget_email_send_error` may still be used elsewhere: check before removing.)
- **1.8 — timing channel (out of scope)**: equalize the response time between "account exists" and "unknown account" (background email sending) to close timing enumeration.
- **1.7 — optional nit**: in `get_email.extract_zpt_variables`, replace the `print(f"File not found…")` with a `log.warning`.
- **1.9 — cleanup**: remove the now-obsolete `@TODO check the validity period` in `forgot_password.py` (l.83), and consider a shorter per-call TTL for password reset (e.g. `decrypt_oid(..., ttl=3600)`) than for email validation.
- **1.10 — PEP 8 nit**: hardening `get_candidature_from_request` left a single blank line before `generate_key` instead of two (E302) — restore for a clean lint.
- **1.11 — deployment**: the env key was normalized to `ORGANIZATION_DETAILS` (uppercase). Nothing in the repository defined the lowercase version, but an unversioned `.env`/docker-compose that sets `organization_details` must be renamed. (The `.ini` setting `organization_details` read via `registry.settings` is distinct and unchanged.)
- **2.5 — view to complete**: `elections_view` no longer crashes but remains a *stub* — `candidatures` assigned/unused (F841), `logged_in`/`username` still read from `request.params`, and the election-filtering logic (TODO) to implement.
- **2.2 — `access` matrix: remaining coverage**: the administrator now reads candidatures (`ADMIN_CANDIDATURE_PERMISSIONS` profile). Still **uncovered and therefore denied** (each denial is traced by a `warning`, which eases diagnosis): access by an `Ordinary`/`Cooperator`/`Provider` to a candidature, and the owner's `(candidature_state, type)` combinations that do not occur in the registration flow. The owner's normal registration flow **is** covered. If other roles must see candidatures, add the corresponding cells (a functional workstream, distinct from the 2.2 hardening).
- **2.7 — type casting in `modify_member`**: ✅ **done** (2026-07-01) — helper `_coerce_member_data_value(field, raw)` relying on `get_type_hints(MemberDatas)` to convert `bool`/`int`/`float` before `setattr`, returning an `invalid_field_value` error on invalid input (new `msgid` added in `fr`/`en`). Dates are still handled via `date_parameters`. Locked by `tests/test_modify_member.py`.
- **2.3 — `vote.py` points**: ✅ deadline control now implemented. Remaining: (a) a **YES/NO tie rejects** the candidature (`count_yes > count_no` required) and `ABSTAIN` counts as a cast vote — to confirm functionally; (b) `voter.vote` stores the **name** (`str`) instead of a `VotingChoice` — to type properly; (c) **result computation at the deadline** (@TODO l.153 "if date is passed, compute the result with the votes") not done: a vote arriving after the deadline is now rejected, but if not all voters voted before the deadline, the candidature is never decided — tallying will be needed at the deadline (scheduled task / on next access). Finally, **add the i18n key `voting_period_ended`** to the `fr`/`en` catalogs (otherwise the raw `msgid` is displayed).

---

## Remaining priorities (suggested order)
1. **Remaining security vulnerability**: **1.3** alone remains in section 1 — password hashing on the LDAP side (`register_user_to_ldap`, `update_member_password`) and purging `data.password` from ZODB after creation. This is the biggest security item still open.
2. **§2 blocking bugs**: ✅ **complete** — the 18 findings (2.1–2.18) fixed and tested.
3. **Robustness**: §3 single transaction strategy, 2.14/2.15 singletons, 2.18 out-of-request cycle.
4. **Continuous**: `ruff` + `mypy`; fix the cosmetic `register.pt` regression (`type="d-none"` → `type="hidden"`); complete the *stubs* (`elections_view`, vote tallying at the deadline — cf. *Follow-up* 2.3); extend test coverage to sections §1 and §3.
