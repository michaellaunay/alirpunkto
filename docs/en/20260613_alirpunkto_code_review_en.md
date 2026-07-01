# Code Review — AlirPunkto — **updated** (2026-06-26 dump)

> Original audit: `20260613_revue_de_code_alirpunkto.md` (2026-06-12 dump).
> This version revisits each item and indicates its status after verification in the **2026-06-26** dump.
> Line numbers refer to the internal numbering of each file in the **new** dump.
> **2026-06-27 revision**: includes fixes applied *after* the 2026-06-26 dump — **1.4** (LDAP filter injection), **1.6** (constant-time admin comparison), **1.7** (template traversal in `get_email`), **1.8** (user enumeration), **1.9** (link expiration through Fernet TTL), **1.10** (`decrypt_oid` failing cleanly), **1.11** (branding read from settings instead of `request.params`), **2.5** (`elections_view` crash), and **§4.14** (`get_member_by_email` annotation) are now fixed.
>
> **2026-06-30 revision**: complete rebuild of the test suite (97 green tests; consistency fix for `MemberRoles.get_i18n_id` along the way), followed by fixes for **2.2** (`get_access_permissions` fail-closed + logging of uncovered cases, and administrator read access to candidatures), **2.1** (reactivation of the `voter` branch by comparing `oid` values), and **2.3** (vote persistence via `_p_changed`, `vote_view` rename, robust session reads, LDAP return-value check before approval, and vote deadline check).

> **2026-06-30 revision (continued)**: fixes for **2.9** (`register_user_to_ldap` return contract normalized as `{'status':'error',…}`) and **2.10** (LDAP group DNs made consistent with group creation, PROVIDER unified on `providersGroup`, anti-`NameError` guard).

> **2026-06-30 revision (continued 2)**: fixes for **2.6** (`update_ldap_member`: unified mapping on model names, raised `AttributeError`s, `MODIFY_REPLACE` instead of `MODIFY_DELETE`, non-mutable default argument) and **2.7** *partial* (`modify_member`: LDAP return value correctly interpreted, password effectively written through `update_member_password`, correct email template; type casting still pending).

> **2026-07-01 revision**: **blocking-bugs section §2 fully handled** (2.1–2.12). Correction of the **2.6** `lang2`/`lang3` block (mixed up during application: loss of the second language and residual `MODIFY_DELETE` — restored to `MODIFY_REPLACE` with the correct value), **2.7** *completed* (form values cast to the field's declared type through `get_type_hints(MemberDatas)`, with input-error handling), **2.4** (`manage_provider`: duplicate detection by email, complete rewrite of the “update” branch, editable fields + `update` action in the template), **2.11** (password validator uninverted through an adapter matching the `colander.Function` contract), **2.12** (the four `get_i18n_id` branches finally interpolate `name.lower()`), and **2.8** (`KeyError` on `/logout?username=` removed). **Most importantly, a non-regression test suite has been added for all these fixes**: 67 tests across 9 files, increasing the suite from 97 to **164 green tests**; each test was verified as *failing* on the pre-fix code. See the new “Non-regression tests” section.

**Legend:** ✅ fixed · ⚠️ partial / mitigated · ❌ not fixed · 🆕 regression introduced since 2026-06-12

## Fix history (git repository)

Mapping between repository commits and audit fixes, in chronological order. `§` refers to the finding number handled below.

| Commit | Date | Fix | Finding |
|---|---|---|---|
| `05d3173` | 2026-06-13 | Encrypt passwords before DEBUG logging | §1.2 |
| `f1a88a8` | 2026-06-13 | Remove passwords from logged attributes | §1.2 |
| `b6458c6` | 2026-06-13 | Harden session-cookie attributes | §1.1 |
| `9841a1c` | 2026-06-16 | CSRF protection on all mutating requests | §1.5 |
| `f453878` | 2026-06-27 | Escape user input in LDAP filters | §1.4 (CWE-90) |
| `c3d603e` | 2026-06-27 | Constant-time comparison of admin credentials | §1.6 (CWE-208) |
| `0a40853` | 2026-06-27 | Validate `email_id` against template traversal | §1.7 (CWE-22) |
| `2e91661` | 2026-06-27 | Prevent account enumeration during password reset | §1.8 (CWE-204) |
| `39c7406` | 2026-06-27 | Expire reset/verification links + fail closed | §1.9 (CWE-613), §1.10 partial |
| `f5ca0d3` | 2026-06-27 | Harden `get_candidature_from_request` for invalid oids | §1.10 (CWE-755) |
| `e0a9275` | 2026-06-27 | Read branding from constants + fix elections crash | §1.11 (CWE-601), §2.5 |
| `9e4f485` · `2832005` | 2026-06-30 | Handle `MemberRoles.NONE` in `get_i18n_id` | §2.12 (related) |
| `0786e92` | 2026-06-30 | Exclude private keys/certificates from source export | tool hardening |
| `278d8be` | 2026-06-30 | Rebuild the test suite (97 green) | test reconstruction |
| `014525b` | 2026-06-30 | Fail-closed permissions + admin read access to candidatures | §2.2 |
| `d1e6d81` | 2026-06-30 | Reactivate the `voter` branch in `get_access_permissions` | §2.1 |
| `72848b9` | 2026-06-30 | Persist votes + approve only after LDAP succeeds | §2.3 |
| `9851714` | 2026-06-30 | Close voting at the deadline | §2.3 |
| `6211c8d` | 2026-06-30 | Normalized LDAP return contract + consistent group DNs | §2.9, §2.10 |
| `f5af346` | 2026-07-01 | `modify_member`: interpret LDAP return + write password | §2.7 |
| `2e55125` | 2026-07-01 | `update_ldap_member`: model-name mapping + `lang2`/`lang3` block | §2.6 |
| `a74e7de` | 2026-07-01 | Cast form values to the field's declared type | §2.7 |
| `6c4fe05` | 2026-07-01 | Repair provider creation/update branches | §2.4 |
| `bed73b3` | 2026-07-01 | Fix inverted password validator | §2.11 |
| `a274cab` | 2026-07-01 | Interpolate `name` in `get_i18n_id` fallbacks | §2.12 |
| `7774ec8` · `bd28bbb` · `8763cbb` · `233313a` | 2026-07-01 | Non-regression test suite (§2.1/2.2/2.3/2.6/2.7/2.9) | tests §2 |
| _“hash”_ | 2026-07-01 | `logout`: safe session-key removal (`pop` instead of `del`) + tests | §2.8 |

---

## Summary

Three security workstreams had already been handled in the 2026-06-26 dump: the session secret (1.1), passwords in logs (1.2), and CSRF protection (1.5). **Since then, seven additional flaws have been fixed**: LDAP filter injection (1.4), admin-credential comparison (1.6), template traversal in `get_email` (1.7), user enumeration (1.8), link expiration (1.9), clean failure of `decrypt_oid` (1.10), and branding read from settings rather than `request.params` (1.11) — plus the `get_member_by_email` annotation (§4.14), and, on the blocking-bug side, the `elections_view` crash (**2.5**, now fixed although the view remains a *stub*). A helper `encrypt_secret_for_logs()` has been added to `secret_manager.py` and is used everywhere a password was previously logged in cleartext. **In section 1, only 1.3 remains** (cleartext passwords in LDAP/ZODB). **All blocking bugs in section §2 (2.1 to 2.12) are now fixed** — 2.13 to 2.18 are distinct findings, with 2.15 and 2.18 still partially mitigated. Unchanged areas remain: transaction issues (§3), most minor bugs (§4), and quality debt (§5). The key point of the last pass is the addition of a **non-regression test suite covering every §2 fix** (67 tests, suite increased from 97 to 164 green tests): the absence of tests had allowed a bad application of fix 2.6 to slip through (`lang2`/`lang3` block mixed up → loss of the second language), now fixed and locked by a parametrized test. A small cosmetic regression remains in `register.pt` (CSRF token rendered as `type="d-none"`).

| Section | Fixed | Partial | Not fixed |
|---|---|---|---|
| 1. Critical security | 1.1, 1.2, **1.4**, 1.5, **1.6**, **1.7**, **1.8**, **1.9**, **1.10**, **1.11** | — | 1.3 |
| 2. Blocking bugs | **2.1**, **2.2**, **2.3**, **2.4**, **2.5**, **2.6**, **2.7**, **2.8**, **2.9**, **2.10**, **2.11**, **2.12** | 2.15, 2.18 | 2.13, 2.14, 2.16, 2.17 |
| 3. Transactions | — | — | all |
| 4. Minor bugs | **§4.14** | §4.18 | §4.1, §4.31, … (unchanged) |
| 5. Quality | — | — | typos, pkg_resources, pytz, types… |

---

## 1. Critical security flaws

### 1.1 Session cookie signed with a public constant — ✅ **fixed**
`__init__.py` l.184: `hash_object.update(get_secret(SECRET_KEY).encode('utf-8'))` — the **value** of the secret is now used. The factory also sets `httponly=True, secure=True, samesite='Lax'` (l.185). This matches the proposed fix.

### 1.2 Cleartext passwords in logs — ✅ **fixed**
New helper `encrypt_secret_for_logs()` (`secret_manager.py` l.59). Applied in:
- `views/login.py` l.125: `…with {encrypt_secret_for_logs(password)=}`;
- `views/forgot_password.py` l.221: same, plus a `log.info` without the password;
- `utils.py::register_user_to_ldap` l.987-988: `safe_attributes` removes `userPassword` from the dict before logging, and the explicit password is encrypted.

### 1.3 Passwords stored in cleartext — ❌ **not fixed**
- **LDAP**: `register_user_to_ldap` l.931 still sends `'userPassword': password` in cleartext; `update_member_password` l.1055 does `MODIFY_REPLACE` with the raw password. No `hashed()` nor `modify_password` in the code (only bootstrap accounts in LDIF are pre-hashed with `{SSHA}`).
- **ZODB**: `register.py` l.534-535 still copies all `request.params` fields matching `MemberDatas.__dataclass_fields__` (including `password`/`password_confirm`), and no `del data.password` has been added after LDAP creation. The candidate's password remains in cleartext in the database.

### 1.4 LDAP filter injection — ✅ **fixed** (post-dump, 2026-06-27)
`escape_filter_chars` (from `ldap3.utils.conv`) now wraps every user-controlled value in the five affected filters:
- `utils.py::get_member_by_email`: `f'(mail={escape_filter_chars(email.strip())})'`;
- `utils.py::is_valid_unique_pseudonym`: `f"(cn={escape_filter_chars(pseudonym)})"`;
- `utils.py::update_member_from_ldap`: `f'(uid={escape_filter_chars(oid)})'`;
- `utils.py::get_oid_from_pseudonym`: `f'(cn={escape_filter_chars(pseudonym)})'`;
- `views/login.py::check_password`: `f'(uid={escape_filter_chars(oid)})'`.

Static filters (`(objectClass=*)`, `(&(employeeType=cooperator)…)`) have no user input and remain unchanged. The dead import `get_ldap_server` was removed from `utils.py` at the same time.

### 1.5 CSRF not checked — ✅ **fixed**
- `__init__.py` l.187: `config.set_default_csrf_options(require_csrf=True)` — global protection active on all POST requests.
- All manual forms now carry the token: `login.pt`, `forgot_password.pt`, `manage_provider.pt`, `modify_member.pt`, `register.pt`, `vote.pt`, etc.
- *Secondary remainder*: `register.py` l.470 still keeps `#form.validate(items)` commented out (colander schema validation still absent), but this is no longer the CSRF protection mechanism. See also 🆕 below (`register.pt`).

### 1.6 Non-constant admin password comparison — ✅ **fixed** (post-dump, 2026-06-27)
`utils.py::is_admin` now compares username and password through `hmac.compare_digest` (constant time) on their UTF-8 bytes:
- no more short-circuiting `==` comparison → timing leak closed;
- encoded as `utf-8` (the `str` mode of `compare_digest` accepts only ASCII and would raise `TypeError`);
- `.strip()` removed from the password (leading/trailing spaces are meaningful again; kept on the username, without risk);
- both comparisons are evaluated before being combined, so the username result does not leak through timing either.

`hmac` import added.

### 1.7 `get_email`: illusory anti-injection + rendering driven by the URL — ✅ **fixed** (post-dump, 2026-06-27)
- **Traversal closed**: `email_id` is now validated by `VALID_EMAIL_ID = re.compile(r'[a-z0-9_]+')` through `fullmatch` before building `f"{email_id}.pt"`. No `/`, `\`, or `.` can appear anymore → impossible to leave `LC_MESSAGES`.
- **Blacklist removed**: the test `"python" in value` + `eval(|exec(|__import__` was removed. It protected nothing (values from `request.params` are passed to the ZPT engine as data, not as template source) and rejected legitimate inputs containing “python”.
- **Template variables**: already restricted to `expected_variables ∩ params` (unchanged).

### 1.8 User enumeration — ✅ **fixed** (post-dump, 2026-06-27)
The five exits from the `'submit'` step of `forgot_password.py` (unknown address, admin account, LDAP load failure, success, send failure) now return a **strictly identical** dict: `{"message": _('forget_email_sent'), "member": None, "form": None}`. The template therefore renders the same page in all cases — including form visibility, which depends on `not member`. The email is sent only if the account exists; other cases are logged server-side.

> **⚠️ Required follow-up**: `forget_email_sent` is now displayed even when no matching account exists. Its wording must remain **neutral** (“*if* an account exists, a link has been sent”) and must not state that an email has actually been sent. See the *Follow-up* section at the end of the document.
>
> **Residual limit (timing)**: the “account exists” path remains slower (LDAP reads, `commit`, sending) → enumeration remains possible through response time. Separate workstream (background sending).

### 1.9 Reset links without expiration — ✅ **fixed** (post-dump, 2026-06-27)
`decrypt_oid` now passes a `ttl` to `fernet.decrypt(decoded, ttl=ttl)`. Since the Fernet token is timestamped at creation (`encrypt_oid`), any link older than the TTL is rejected. The delay is carried by a new constant `OID_LINK_TTL_SECONDS` (24h by default, overridable through the `ALIRPUNKTO_OID_LINK_TTL_SECONDS` env var), read **on each call** (`ttl=None` parameter, then read in the body → no frozen default, overrideable by call and testable by monkeypatch).

### 1.10 `decrypt_oid` raises instead of returning `None` — ✅ **fixed** (post-dump, 2026-06-27)
`decrypt_oid` now wraps decoding and decryption in a `try/except (InvalidToken, ValueError, TypeError)` and returns `(None, None)` for any invalid, malformed, or expired token (`Fernet(secret)` stays outside the `try` so that a misconfigured key still surfaces). This contract matches what callers already expected: the `is None` branch in `check_new_email` (previously unreachable) becomes active, and `retrieve_candidature` as well as `forgot_password._retrieve_member` already test for `None` → a forged/expired `?oid` displays a clean page instead of a 500. The only unguarded caller, `get_candidature_from_request` (which was **dead code**), was hardened: all its failure modes return `None`, and the generic `raise Exception("Seed mismatch")` was removed.

### 1.11 `site_name` / `domain_name` taken from the request — ✅ **fixed** (post-dump, 2026-06-27)
The three views that read these values from `request.params` — `login_view`, `sso_login.callback_view`, and `elections_view` — now read the trusted constants `SITE_NAME` / `DOMAIN_NAME` / `ORGANIZATION_DETAILS`. There is no longer any read of these keys from `request.params`: the spoofing/phishing vector is closed. The constants receive default values (also fixing emails that displayed `None`). The env key `organization_details` is normalized to `ORGANIZATION_DETAILS` (see *Follow-up* for deployment caveat). Note: reads from `request.registry.settings.get('site_name'…)` in other views are a distinct and **trusted** source (server config), outside the scope.

---

## 2. Blocking bugs — **section 2.1–2.12 fixed** (2.15/2.18 partial; 2.13/2.14/2.16/2.17 remaining)

### 2.1 Verifiers without permissions — ✅ **fixed** (post-dump, 2026-06-30)
The `voter` branch in `get_access_permissions` tested `accessor.oid in accessed.voters` — a `str` compared to a list of `Voter` dataclass instances, therefore **always `False`**: dead branch, the voter fell through to the generic branch and, since 2.2, received `NO_MEMBER_PERMISSIONS` (denial). Fixed as `accessor.oid in {voter.oid for voter in accessed.voters}`. Empirically verified: a voter now receives `access['voter'][state]` for the seven candidature states (without warning), while a non-voter remains denied and logged (2.2 behavior unchanged).

### 2.2 `KeyError` on many (role, state) pairs — ✅ **fixed** (post-dump, 2026-06-30)
`get_access_permissions` performed five direct `access[…][…]` index lookups, exposed to `KeyError`/500. They now go through a helper `_resolve_permissions(externe, interne)` which: returns the cell if the pair exists; otherwise **logs a `warning`** identifying the missing pair and returns the deny-all fallback `NO_MEMBER_PERMISSIONS` (all fields `Permissions.NONE`). Double benefit: *fail-closed* (a gap denies instead of crashing) **and** visibility — any missing coverage is logged for immediate debugging. Empirically verified: present key → identical object (`is`) to the old access, no warning; absent key → `NO_MEMBER_PERMISSIONS` + warning.

In addition, the matrix has been **expanded for administrators**: a new profile `ADMIN_CANDIDATURE_PERMISSIONS` (read-only on all candidature fields; inherited member fields reuse the `ADMIN_MEMBER_PERMISSIONS` policy, so IBAN is masked and `seed` is not readable) is wired into `access['Administrator']` for the seven candidature states. An administrator can therefore inspect a candidature in progress (the 28 non-owner crashes are replaced by admin read access, and logged denial for other roles). Remaining gaps (`Owner` combinations not encountered during the registration flow, `Ordinary`/`Cooperator`/`Provider` access to a candidature) return a logged denial — see *Follow-up*.

### 2.3 Vote probably never persisted — ✅ **fixed** (post-dump, 2026-06-30)
Four points handled in `vote.py`: (1) **persistence** — `voter.vote = vote` mutates a `Voter` dataclass nested inside the `_voters` list of a persistent `Candidature` without marking it *dirty*; `candidature._p_changed = True` was added immediately after. **Proven with a real ZODB** (reopened `FileStorage`): without the flag the reloaded vote is `None` (lost), with the flag it is persisted. (2) **rename** of view `login_view` → `vote_view` (copy/paste leftover); (3) session read `request.session['site_name'/...]` → `.get(..., SITE_NAME/DOMAIN_NAME/ORGANIZATION_DETAILS)`, no more `KeyError` (consistent with 1.11); (4) **`register_user_to_ldap` result checked** — approval is performed only if the return value is `{'status': 'success'}` (defensive test `isinstance(...) and .get('status')=='success'`, robust against contract inconsistency 2.9); otherwise error logged, `abort()`, and message to user, so the candidature no longer moves to **APPROVED** on LDAP failure. Verified by driving `vote_view` (failure → remains `PENDING` + vote kept; success → `APPROVED`; non-dict return → remains `PENDING`). Full suite 97/97. **Vote deadline check subsequently implemented** (post-dump, 2026-06-30): if `candidature.verification_deadline` has passed, `vote_view` returns a `voting_period_ended` error and the template hides the form (missing deadline ⇒ no block; naive deadline normalized to UTC) — verified on 5 cases. Remaining functional points (see *Follow-up*): YES/NO tie semantics, `str` vs `VotingChoice` typing, result computation at deadline, and adding the i18n key.

### 2.4 Broken create/update branches in `manage_provider.py` — ✅ **fixed** (post-dump, 2026-07-01)
Several bugs handled. **Create branch**: `provider_email in providers` (where `providers` is a list of `User` objects, therefore always false) → `any(existing.email == provider_email for existing in providers)`; dead `get_member_by_oid(provider_email, …)` removed (email used as oid, always `None`). **Update branch**, completely rewritten: removal of `RegisterForm(request, schema=…, member=…)` (non-existent constructor), `form.validate`/`form.get_data`, and dead `manage_provider_schema`; it now reads `provider_email`/`provider_password` from `request.params`, validates through `is_valid_email(new_email, request)` and `is_valid_password`, updates email through `update_ldap_member(request, member, fields_to_update=['email'])` (third argument = **list of field names**, no longer a dict), updates password through `update_member_password`, sets valid state `MemberStates.DATA_MODIFIED` (old `MemberStates.ACTIVE` did not exist → `AttributeError`), and commits. **Template** `manage_provider.pt`: the “modify” form gets editable fields `provider_email`/`provider_password` and its button posts action **`update`** (it posted `submit`, which the view did not listen to → branch was unreachable). Three new `msgid`s (`provider_update_failed`, `provider_new_email_label`, `provider_new_password_label`). *Remaining cleanup (optional)*: imports/declarations now unused in the view (`RegisterForm`, `deform`, `Translator`, `manage_provider_schema`, etc.). Covered by `tests/test_manage_provider.py` (8 tests).

### 2.5 Guaranteed crash in `elections.py` — ✅ **fixed** (post-dump, 2026-06-27)
`get_candidatures(request)` now receives the `request` argument → no more `TypeError`/500 for a logged-in user. **Caveat**: the view remains a *stub* — it still returns `{"elections": []}`, the `candidatures` result is assigned but unused (F841), and `logged_in`/`username` are still read from `request.params`. Election filtering logic must be written (TODOs added). See *Follow-up*.

### 2.6 Inconsistent `update_ldap_member` mapping — ✅ **fixed** (post-dump, 2026-06-30)
Mutable default argument replaced by `None` + list built in the body using the **model names** (the ones tested by the body and pushed by callers). `'data.fullsurname'` → `'fullsurname'`; `'uniqueMemberOf'` → `'unique_member_of'` (+ `member.data.unique_member_of`); `member.data.dateErasureAllData` → `member.data.date_erasure_all_data` (no more `AttributeError`). `cooperativeBehaviourMark` converted to `str`. `MODIFY_DELETE` (which failed when the attribute was absent) replaced by `MODIFY_REPLACE` with an empty value (deletes if present, no-op otherwise). Verified by executing the function (mocked LDAP): a default call now builds **18 attributes** (vs ~4), `sn` is present, `cooperativeBehaviourMark` is a `str`, and empty languages use `MODIFY_REPLACE`. **Follow-up fix (2026-07-01)**: during application, the `lang2`/`lang3` block had been **mixed up** — the “`lang2` populated” case wrote empty `secondLanguage` (loss of second language), the “`lang2` empty” case targeted `thirdLanguage` (wrong attribute), and empty `lang3` still used `MODIFY_DELETE`. Restored: populated language → `MODIFY_REPLACE [value]`, empty → `MODIFY_REPLACE []`, on the correct attribute. Beneficial side-effect observed in `tests/test_ldap_utils.py` (parametrized over `lang2`/`lang3` combinations): this is exactly the test that should have existed to catch the regression.

### 2.7 `modify_member.py` misinterpreted return + ineffective password — ✅ **fixed** (post-dump, 2026-06-30 → completed 2026-07-01)
Fixed: (a) `if not sending_success` → `if fields_to_update and sending_success.get('status') != 'success'` (`update_ldap_member` always returns a *truthy* dict — an LDAP error was treated as a success); (b) **password branch**: after `is_valid_password`, the error is tested **and** `update_member_password` is now called and its return checked (the change had no effect); (c) `email_template` `"reset_password_email"` → `"check_new_email"` (the real template sent), and send status set on `accessed_member` (not `member`); (d) corrected `flash` (message first, queue `'error'` second); (e) same return bug in `check_new_email.py` (`if result is None` → test on `status`). **Type casting now implemented (2026-07-01)**: the `#@TODO cast the value to the right type` is resolved by helper `_coerce_member_data_value(field, raw)`, which converts the form value (always a `str`) to the field's declared type, resolved once through `get_type_hints(MemberDatas)` (`bool`/`int`/`float`); on invalid input (e.g. `"abc"` for `number_shares_owned`), the view returns `invalid_field_value` (new `msgid`) without writing anything. Beneficial side-effect: the comparison `getattr(...) != requested_value` now compares values of the same type, avoiding unnecessary LDAP updates (`"5" != 5` was always true). Verified: compile + targeted checks. Covered by `tests/test_modify_member.py` (8 tests, including int/float/bool casting and invalid-value rejection) and `tests/test_check_new_email.py` (3 tests).

### 2.8 `logout`: `KeyError` on `?username=` — ✅ **fixed** (post-dump, 2026-07-01)
`logout` read `username` from `request.params` then did `del request.session['username']` — but this key is **never** set in the session (the only occurrence of `'username'` in the code is the Keycloak token payload). `/logout?username=X` therefore raised a `KeyError` (500). The URL-parameter-driven block is replaced by an unconditional safe `request.session.pop('username', None)`; the function's other deletions were already guarded by `if X in request.session`. Covered by `tests/test_logout.py` (4 tests).

### 2.9 Inconsistent `register_user_to_ldap` return contract — ✅ **fixed** (post-dump, 2026-06-30)
The “invalid pseudonym” path returned `is_valid_unique_pseudonym`'s raw `{'error': …}` (with no `status` key), while callers read `result['status']` (and `register.py` also reads `result['message']`) → `KeyError`. Normalized as `{'status': 'error', 'message': error.get('error'), **error}`: the function's contract is respected while preserving `error`/`error_details`. Verified by executing the function with an invalid pseudonym → `{'status':'error','message':…,'error_details':…}`.

### 2.10 Inconsistent group DNs — ✅ **fixed** (post-dump, 2026-06-30)
Three points: (a) a PROVIDER's `uniqueMemberOf` pointed to `providerMembersGroup` whereas the group created/modified is `providersGroup` → unified on `providersGroup`; (b) the six group DNs re-prefixed `ou={LDAP_OU}`, whereas group creation (`__init__.py` l.159-160) and the user DN use `{LDAP_OU}` directly → extra `ou=` prefix removed, DNs now target where the groups actually exist; (c) `group_dn` was undefined for ADMINISTRATOR/`_` → potential `NameError` in the final log, fixed with `group_dn = None` + `if group_dn is not None` guard. Verified by executing `register_user_to_ldap` with a mocked LDAP connection: for COOPERATOR/ORDINARY/PROVIDER, the DN passed to `conn.modify` is **identical** to the one created by `__init__.py`, and `uniqueMemberOf` points to the same DN; ADMINISTRATOR performs no `modify` and does not raise.

### 2.11 Inverted password validator — ✅ **fixed** (post-dump, 2026-07-01)
`colander.Function` raises `Invalid` when the *callback* returns a *falsy* value (or a string, used as message) and considers a *truthy* non-string return value valid; `is_valid_password` does the opposite (`None` = valid, error dict otherwise). A **valid password was therefore rejected** and an **invalid one accepted** (demonstrated with real colander). Fixed by adapter `_validate_password(value)` returning `True` when valid and the error message otherwise; `schemas/register_form.py` l.173 becomes `validator = colander.Function(_validate_password)`. No new `msgid` (fallback `_('invalid_password')` already exists). Covered by `tests/test_register_form.py` (5 tests, including one on the actual `password` field validator in the schema). *Note*: the bug was harmless so far because `form.validate` remains commented out (see 1.5).

### 2.12 `get_i18n_id`: `return(f"name.lower()")` — ✅ **fixed** (post-dump, 2026-07-01)
The four default branches (`case _`) that returned the literal string `"name.lower()"` (an f-string missing braces) now interpolate `name.lower()` with each class's i18n prefix: `MemberStates` → `member_state_…`, `MemberTypes` → `member_types_…`, `Permissions` → `access_permissions_…`, `CandidatureStates` → `candidature_states_…` (mirroring the two already-correct fallbacks, `MemberRoles`/`role_types_…` and `VotingChoice`/`vote_types_…`). These are “should never happen” fallbacks preceded by `log.error`; the prefix can be adjusted if another convention is preferred. Covered by `tests/test_get_i18n_id.py` (8 tests, including a sweep ensuring no branch returns the literal anymore). **Note**: the rebuilt suite no longer freezes this behavior — old `tests/test_views.py` (which asserted `== "name.lower()"`) no longer contains these assertions, and the full suite passes (164) with the fix.

### 2.13 Fragile SSO refresh — ❌ **not fixed**
`home.py`: `refresh_keycloak_token` may return `None` → `sso_token['access_token']` l.51 `TypeError`; `request.headers['Authorization'] = f'Bearer {sso_token}'` l.55 (writes to the incoming request, and `sso_token` is a dict); default `"2020-01-01T00:00:00"` l.46 → immediate logout; refresh on every display. Same bugs in `login.py` l.78-79.

### 2.14 `Members.get_instance` ZODB singleton across connections — ❌ **not fixed**
`member.py` l.368 `_instance = None`, caching l.404, liveness test `'test' in Members._instance` l.386, and `Members.get_instance()` called without a connection l.722. Risk of `ConnectionStateError`/stale reads unchanged.

### 2.15 Global connection in `ldap_factory.py` — ⚠️ **partial**
Added `reset_ldap_connection()` and creation of a **fresh connection for strategies ≠ SYNC** (useful in tests). But for the **production SYNC strategy**, `_conn` remains a module-level singleton (l.135-151) → not thread-safe; default arguments `server_name=get_ldap_server_name()` (l.34) are still evaluated at import time. The core problem remains.

### 2.16 `secret_manager.py`: unguarded `del os.environ[...]` — ❌ **not fixed**
l.32/44-46/48/50: still `del os.environ[...]` (raises `KeyError` before the intended `ValueError`) instead of `os.environ.pop(name, None)`.

### 2.17 `validate_challenge`: `request.params[label]` → `KeyError` — ❌ **not fixed**
`register.py` l.401: still `request.params[label].strip()`. `.get(label, '')` not applied.

### 2.18 `remind_pending_verifiers` on every request — ⚠️ **partial**
Still subscribed to `NewRequest` (`__init__.py` l.66). Mitigations added: `if PYTEST_CURRENT_TEST` short-circuit, `try/except`, and idempotence flag `verifier_reminder_sent` (+ `verifier_reminder_sent_at`) in `send_verifier_reminder_emails` (l.820, 895-896). But still O(n) per request, without locking (possible concurrent double-send), and not moved to a scheduled task.

---

## Non-regression tests (added on 2026-07-01)

The absence of tests covering §2 fixes had allowed at least one silent regression to slip through (the `lang2`/`lang3` block of 2.6). A non-regression suite was therefore added — **one file per fix** — increasing the suite from 97 to **164 green tests**. For each one, the test was verified as *failing* on the pre-fix code (bug temporarily reintroduced), ensuring that it really catches the regression.

| File | Tests | Finding(s) | Key points |
|---|---|---|---|
| `test_model_permissions_access.py` | 11 | §2.1, §2.2 | voter recognition (comparison on `oid`), admin read access to candidatures (7 states), *fail-closed* denial for a missing cell |
| `test_vote.py` | 10 | §2.3 | **vote persistence proven with a real reopened `FileStorage`** (lost without `_p_changed`), deadline guard, session fallback, LDAP return interpretation on approval |
| `test_ldap_utils.py` | 10 | §2.6, §2.9 | 18 default attributes without `AttributeError`, corrected field names, `lang2`/`lang3` (anti-data-loss guard, never `MODIFY_DELETE`), invalid-pseudonym return contract |
| `test_modify_member.py` | 8 | §2.7 | LDAP return interpretation, effective password write, **`int`/`float`/`bool` casting**, and invalid-value rejection |
| `test_manage_provider.py` | 8 | §2.4 | access guards, duplicate detection by email, email/password update, LDAP failure propagation |
| `test_get_i18n_id.py` | 8 | §2.12 | all four fallbacks interpolate, none returns the literal, known names resolve |
| `test_register_form.py` | 5 | §2.11 | validator adapter, behavior through `colander.Function`, real `password` field validator |
| `test_check_new_email.py` | 3 | §2.7 | LDAP failure (error dict **or** `None`) is no longer treated as success, no commit |
| `test_logout.py` | 4 | §2.8 | `/logout?username=X` no longer raises, effective logout, purge of SSO/oid keys |

These tests rely on existing *fixtures* (`members_mapping`, `caplog`, `tmp_path`); LDAP and email sending are mocked, and ZODB is real only for vote persistence. No new dependency.

---

## 3. Transaction consistency — ❌ **not fixed**
25 explicit `transaction.commit()` calls remain (notably `forgot_password.py`, `modify_member.py`, `register.py`, `vote.py`), still combined with `pyramid_tm`. No single strategy adopted.

---

## 4. Lower-severity logical bugs (verified points)
- **§4.14** ✅ **fixed** (post-dump): `get_member_by_email` is now annotated `-> List[Entry]` and its docstring describes the real return value (list of LDAP entries, empty if none).
- **§4.1** ❌ `(objectClass=*)` still present (6 occurrences, including `get_ldap_member_list` l.155 and startup).
- **§4.18** ⚠️ `vote.pt` now filters `password` **and** `password_confirm` (l.30), but it remains a **blacklist**: `iban` and `date_erasure_all_data` are still exposed to voters. Switch to a whitelist.
- **§4.31** ❌ `get_majority_date` (`routes.py` l.33): still `timedelta(days=365*18)` instead of `relativedelta(years=18)`.
- Other items (§4.2 to §4.35, except §4.14) have not been touched; they remain valid.

---

## 5. Quality, style, maintenance — ❌ **not fixed**
- **Typos** still present, including in identifiers: `REGISTRED` (≈23×), `allready` (≈3×), `Coulb` (`member.py` l.366)…
- **`pkg_resources`** still imported (`__init__.py` l.19, `resource_filename` l.278-279) — deprecated.
- **`pytz`** still used.
- **Type annotations** are still widely misleading (`retrieve_candidature -> Union[Candidature, Dict]` but returns a tuple, `get_keycloak_token -> Optional[str]` but returns a dict, etc.); `get_member_by_email`, however, has been fixed (§4.14).
- No `ruff`/`mypy`/per-view functional tests added.

---

## 🆕 Regressions / points introduced since 2026-06-12
1. **`register.pt` l.207**: the CSRF token is rendered as `<input type="d-none" …>` instead of `type="hidden"`. An unknown type falls back to `text` → the field (and token) appears as an editable text box. The 9 other forms correctly use `type="hidden"`.
2. ~~**`tests/test_views.py`**: tests freezing `get_i18n_id` (`"name.lower()"`)~~ — ✅ **resolved**: bug 2.12 is fixed and the rebuilt suite no longer contains these assertions; the full suite (164) passes with the fix. Only the cosmetic **`register.pt`** regression (point 1) remains.

---

## Follow-up — debt left by the fixes (do not forget)
- **1.8 — neutral wording (required)**: `forget_email_sent` is now displayed even when no account matches. Reword the i18n string (fr **and** en) as a neutral message — e.g. “If an account is associated with this address, a reset link has just been sent.” — and **do not** state that an email was sent. Without this, enumeration stays closed but the message lies to the legitimate user.
- **1.8 — orphan i18n key (optional nit)**: `forget_admin_user` is no longer referenced after the fix → remove it from `.po`/`.pot`. (`forget_email_in_member_list` and `forget_email_send_error` may still be useful elsewhere: verify before removing.)
- **1.8 — timing channel (out of scope)**: equalize response time between “account exists” and “unknown account” (background email sending) to close timing-based enumeration.
- **1.7 — optional nit**: in `get_email.extract_zpt_variables`, replace `print(f"File not found…")` with `log.warning`.
- **1.9 — cleanup**: remove the now-obsolete `@TODO check the validity period` in `forgot_password.py` (l.83), and consider a shorter per-call TTL for password reset (e.g. `decrypt_oid(..., ttl=3600)`) than for email validation.
- **1.10 — PEP 8 nit**: hardening `get_candidature_from_request` left only one blank line before `generate_key` instead of two (E302) — restore for clean linting.
- **1.11 — deployment**: the env key has been normalized to `ORGANIZATION_DETAILS` (uppercase). Nothing in the repository defined the lowercase version, but an unversioned `.env`/docker-compose that sets `organization_details` must be renamed. (The `.ini` setting `organization_details` read through `registry.settings` is distinct and unchanged.)
- **2.5 — view to complete**: `elections_view` no longer crashes but remains a *stub* — `candidatures` assigned/unused (F841), `logged_in`/`username` still read from `request.params`, and election-filtering logic (TODO) still to implement.
- **2.2 — `access` matrix: remaining coverage**: administrators now read candidatures (profile `ADMIN_CANDIDATURE_PERMISSIONS`). Still **uncovered and therefore denied** (each denial logged as a `warning`, easing diagnostics): `Ordinary`/`Cooperator`/`Provider` access to a candidature, and `(candidature_state, type)` owner combinations that do not occur in the registration flow. The normal owner registration flow **is** covered. If other roles must see candidatures, add the corresponding cells (functional workstream, distinct from the 2.2 security hardening).
- **2.7 — type casting in `modify_member`**: ✅ **done** (2026-07-01) — helper `_coerce_member_data_value(field, raw)` using `get_type_hints(MemberDatas)` to convert `bool`/`int`/`float` before `setattr`, returning `invalid_field_value` on invalid input (new `msgid` added in `fr`/`en`). Dates remain handled through `date_parameters`. Locked by `tests/test_modify_member.py`.
- **2.3 — `vote.py` points**: ✅ deadline check now implemented. Remaining: (a) a **YES/NO tie rejects** the candidature (`count_yes > count_no` required) and `ABSTAIN` counts as an expressed vote — to confirm functionally; (b) `voter.vote` stores the **name** (`str`) instead of a `VotingChoice` — type properly; (c) **result computation at deadline** (@TODO l.153 “if date is passed, compute the result with the votes”) not done: a vote arriving after the deadline is now refused, but if all voters have not voted before the deadline, the candidature is never decided — it will need counting at the deadline (scheduled task / next access). Finally, **add the i18n key `voting_period_ended`** to the `fr`/`en` catalogs (otherwise the raw `msgid` is displayed).

---

## Remaining priorities (suggested order)
1. **Remaining security flaw**: **1.3** is the only remaining item in section 1 — hash passwords on the LDAP side (`register_user_to_ldap`, `update_member_password`) and purge `data.password` in ZODB after creation. This is the largest security issue still open.
2. **Remaining blocking bugs in §2**: 2.1–2.12 done and tested. Remaining: **2.13** (fragile SSO refresh), **2.14** (`Members` singleton across connections), **2.16** (`del os.environ`), **2.17** (`request.params[label]`); **2.15** / **2.18** remain partially mitigated.
3. **Robustness**: §3 single transaction strategy, 2.14/2.15 singletons, 2.18 outside the request cycle.
4. **Continuous work**: `ruff` + `mypy`; fix cosmetic regression `register.pt` (`type="d-none"` → `type="hidden"`); complete the *stubs* (`elections_view`, vote counting at deadline — cf. *Follow-up* 2.3); extend test coverage to sections §1 and §3.
