# External repository audit (ChatGPT), twelfth pass — 2 August 2026

**Provenance.** Twelfth pass of the external static audit (ChatGPT,
at Michaël Launay's request), on commit `4481288a` (trains 0079
through 0082 merged); previous pass on `777074c2`. Proposed overall
grade: **8.8/10** — stable at the series' high, with a **tenth domain
inaugurated: "Multi-agent harness: 7.6"** holding the grade back
while CI (9.0), Docker (9.1) and documentation (8.8) advance. Across
the passes: 6.5 → 6.9 → 6.7 → 7.1 → 7.8 → 8.2 → 8.5 → 8.6 → 8.4 →
8.3 → 8.8 → 8.8. (Translated from the French original.)

**Status.** Counter-reviewed the same day. The harness architecture
is validated without reserve — `AGENTS.md` natively recognised by
Codex and Kimi Code CLI, the `@AGENTS.md` import official on the
Claude Code side — and the six configuration findings are **all
founded**, one being particularly instructive: the `Read(./.env.*)`
pattern blocked the tracked `.env.example`, reproducing inside our
own harness the very class of mistake (over-broad pattern) the audit
series hunts everywhere else. Fixes delivered by train 0083 (merged
`b9e8bc51`): denies rewritten as precise sensitive paths
(`.env.example` readable again, `fnmatch` lock), both hashed locks
installed by the documented setup, an "Exact CI commands" section
quoting the workflows literally (the CI's ruff aligned **upward**
onto the two docker scripts), "guardrails" wording in `CLAUDE.md`,
`.gitignore` taught `.kimi-code/local.toml`, and the
`tests/test_agent_harness.py` suite §11 asked for (seven locks,
including command↔workflow parity). The optional `$schema` (P1.5)
stayed out, the schemastore URL being unconfirmed. **Reserve kept at
§13**: the third smoke run (Referer fix) was confirmed neither by the
auditor's connector nor by us at filing time.

## Follow-ups

0083 (harness P0+P1 fixes, chronicled above) and chapter
[14 — Developing with AI agents](../architecture/14_ai_agents.md)
(installation and configuration of the three agents, examples on this
repository). On the books: the P2 items (harness from a pristine
machine, discovery by all three agents), the observable green smoke,
and the unchanged application P3s — sanction persistence (design
decision in progress), LDIF serialiser, scan, external scheduler,
`.env.example`.

# Full text of the audit (twelfth pass, translated)

# Updated audit of the AlirPunkto repository — twelfth pass

**Date:** 2 August 2026 — **Repository:** `michaellaunay/alirpunkto`
— **Branch:** `master` — **Commit examined:** `4481288a…` —
**Previous audit:** `777074c2…`

## 1. Executive summary

Four commits were added since the previous pass: 1. documentary
archiving of the missing audits; 2. fix of the `.env` lookup from the
wheel-installed application; 3. addition of the multi-agent harness;
4. fix of the HTTPS smoke test to reproduce a real browser's
behaviour under the CSRF check.

The harness rests on: `AGENTS.md` as the common contract; `CLAUDE.md`
as the Claude Code layer; `.claude/settings.json` as the Claude
permission policy; `.claude/settings.local.json` excluded from Git
for local adaptations.

This architecture is pertinent: Codex officially recognises
`AGENTS.md` as the repository's instruction file; Kimi Code CLI also
loads the project's `AGENTS.md`; Claude Code uses `CLAUDE.md` and
supports the `@AGENTS.md` import, exactly as the repository does.

The Claude configuration is valid JSON and uses officially supported
fields: `permissions.allow`, `permissions.ask`, `permissions.deny`,
`permissions.defaultMode`.

The harness is however not yet error-free: 1. `Read(./.env.*)`
involuntarily blocks the tracked `.env.example`; 2. `docker/.env.test`,
which contains generated local credentials, is not explicitly denied
to Claude; 3. the installation described in `AGENTS.md` provides
neither Ruff nor Bandit; 4. the harness's quality commands do not
exactly match the CI's; 5. no test suite locks the harness files yet;
6. the Claude "blocks" can be bypassed by equivalent Bash commands
and must therefore be presented as guardrails, not absolute
confinement.

The harness is thus well designed but still partly misconfigured.

## 2. Updated evaluation

| Domain                            | Previous | New |
| --------------------------------- | -------: | --: |
| Application architecture          |      8.1 | 8.2 |
| Code quality                      |      8.4 | 8.5 |
| Unit and structural tests         |      9.4 | 9.4 |
| CI and integration tests          |      8.9 | 9.0 |
| Documentation                     |      8.6 | 8.8 |
| Dependencies and reproducibility  |      9.4 | 9.4 |
| Application security              |      9.1 | 9.1 |
| Docker security and operation     |      9.0 | 9.1 |
| Operations and observability      |      7.6 | 7.7 |
| Multi-agent harness               |        — | 7.6 |

**Updated overall grade: 8.8/10.** The Docker stack's maturity
progresses, but the Claude permission and environment-preparation
errors still prevent raising the overall grade.

## 3. Claude Code compatibility — correct

**3.1 Instruction loading.** `CLAUDE.md` begins with `@AGENTS.md`,
then adds only the Claude-specific rules: conversation in French;
code and commits in English; delivery as a numbered patch; no
`git push`; full test runs; respect of the `.claude/settings.json`
policy. Claude Code officially supports `CLAUDE.md` as project
memory, imports using the `@path` syntax, and the use of `@AGENTS.md`
to share instructions with other agents. Status: loading
configuration correct.

**3.2 Size and structure.** `AGENTS.md` is about 129 lines and
`CLAUDE.md` 19. The content stays organised by headings —
environment; commands; delivery; security rules; testing traps; CI.
This avoids a monolithic `CLAUDE.md` and keeps one contract common to
the three agents. Status: satisfactory.

## 4. Claude error: .env.example is blocked

The policy simultaneously contains `"allow": ["Read(./**)"]` and
`"deny": ["Read(./.env)", "Read(.env)", "Read(./.env.*)"]`. Claude's
read rules use gitignore-style patterns, and denies are evaluated
before asks and allows: a matching deny cannot be compensated by
`Read(./**)`.

The `./.env.*` pattern notably matches `.env.example`. Yet
`.env.example` is a Git-tracked file, meant precisely to be audited
and fixed — it already carries several identified inconsistencies:
`MAIL_USE_TLS` instead of `MAIL_TLS`; `MAIL_USE_SSL` instead of
`MAIL_SSL`; an ambiguous `LDAP_SERVER` example; no
`LDAP_CA_CERT_FILE`. Claude Code would thus be prevented from reading
a file it should be able to examine.

**Recommended fix.** Replace the broad pattern with precise sensitive
paths — `Read(./.env)`, `Read(.env)`, `Read(./docker/.env)`,
`Read(./docker/.env.test)`, `Read(./docker/secrets/**)`,
`Bash(git push:*)`, `Bash(rm -rf:*)`, the three lock-file edit denies
— and do not deny `.env.example`.

Status: configuration error confirmed. Severity: medium — it blocks a
legitimate activity rather than directly creating a leak.

## 5. Claude error: docker/.env.test stays readable

The policy denies `Read(./docker/.env)` but not `docker/.env.test`.
Yet `docker/init_test.sh` generates that file with, among others: the
local LDAP password; the administrator password; the test accounts'
passwords; a session key; the local stack's full configuration. Even
as local or test values, these remain credentials that should not be
automatically pulled into an agent's context. The file is correctly
gitignored, but Git exclusion is not a read restriction for Claude
Code.

**Required fix.** Add `Read(./docker/.env.test)` to
`permissions.deny`. The future variants can also be protected
explicitly — `Read(./docker/.env.local)`,
`Read(./docker/.env.production)` — without reintroducing a pattern
that would block tracked, non-sensitive examples.

Status: configuration error confirmed. Severity: medium.

## 6. Limit of the Claude permissions: guardrails, not absolute confinement

The policy directly denies `Edit(./requirements.lock)`, which blocks
Claude's edit tool on that file. It does not necessarily prevent a
modification performed through `sed`, a Python script, a shell
command, an approved patch, or another form of Bash command.
Likewise, `Bash(git push:*)` targets commands matching the pattern
but is not a general sandbox against every possible variant of a Git
operation.

The Claude documentation states that permission rules control tool
calls matching the declared patterns; a stricter policy may require
`PreToolUse` hooks, a sandbox, or a reduction of the available tools.

The `CLAUDE.md` sentence "blocks pushes, lock-file edits and .env
reads" is therefore slightly too absolute.

**Recommendation.** Use instead: "The permission policy provides
guardrails against direct pushes, lock-file edits and secret-file
reads. Do not bypass those guardrails through shell commands." For a
truly strict block, add a hook inspecting commands before execution.

Status: security limit, not a syntax error.

## 7. Codex compatibility — correct

Codex natively uses `AGENTS.md` for repository instructions. OpenAI
also documents nested `AGENTS.md` files with directory-bound scope.
The root file therefore suits Codex CLI, Codex tasks over the whole
repository, and instruction sharing with the other agents. No extra
`.codex` file is needed for these general instructions. Status:
compatible.

**Reserve for Codex cloud.** The contract imposes a gitignored
`.patch` file, no push, and manual merging by the maintainer. That
convention fits a locally run Codex CLI very well. It fits less an
environment meant to prepare a commit or pull request directly: the
`.patch` being ignored, it does not appear in the tracked diff. It
would be useful to state in `AGENTS.md`: "For local agents, the
default deliverable is a numbered patch file. When running in a
managed PR or cloud workspace, modify the tracked working tree and
present the resulting diff, but never push unless the maintainer
explicitly requested that workflow." Status: portability limitation,
not blocking for Codex CLI.

## 8. Kimi K3 compatibility — correct through Kimi Code CLI

Kimi Code CLI supports a project-level `AGENTS.md` and can even
generate one with its initialisation command. The root file will thus
be usable when Kimi K3 runs through Kimi Code CLI in this repository.
Status: compatible with Kimi Code CLI.

**Important reserve.** This compatibility belongs to the Kimi Code
CLI client, not intrinsically to the Kimi K3 model. When Kimi K3 is
used through the API, a web interface, another IDE, or a third-party
orchestrator, nothing guarantees `AGENTS.md` is automatically
injected into its context: the client must explicitly read or pass
the file. The current sentence ("point any other agent here first —
most modern coding CLIs pick this file up automatically") is
reasonable but could be more precise: "Codex and Kimi Code CLI load
this file natively. For other clients, explicitly provide AGENTS.md
as project instructions."

**Kimi local state.** Kimi Code CLI can use local project state,
notably under `.kimi-code/`. It is prudent to ignore purely personal
files such as `.kimi-code/local.toml` without ignoring `.kimi-code/`
globally, so a possibly shared configuration or specialised agents
can be tracked later. Status: recommended improvement.

## 9. Reproducibility error: the quality tools are not installed

`AGENTS.md` asks to prepare the environment with a venv installing
`requirements-test.lock` only, then asks to run `ruff check …` and
`bandit …`. But Ruff and Bandit belong to
`requirements-quality.lock`, which the quality CI explicitly installs
before launching the tools. On a clean machine, after following only
the `AGENTS.md` procedure: `.venv/bin/ruff` does not exist;
`.venv/bin/bandit` does not exist; the system `ruff` and `bandit`
commands may be absent or the wrong version. This is a concrete
harness configuration error.

**Recommended fix.** Install both locked environments into the venv
(`--require-hashes`, test lock then quality lock), then always use
the virtualenv executables: `.venv/bin/ruff check alirpunkto tests
tools`; `.venv/bin/bandit -r alirpunkto tools -ll -q`;
`.venv/bin/pip-audit --no-deps --ignore-vuln PYSEC-2026-3447` over
the three locks. Another option is two distinct environments
(`.venv-test`, `.venv-quality`), at the cost of onboarding weight.

Status: configuration error confirmed. Severity: medium.

## 10. The harness commands do not exactly match the CI

**Ruff.** The harness asks `ruff check alirpunkto tests tools
docker/apply_server_overrides.py docker/generate_ldif.py`; the CI
runs `ruff check alirpunkto tests tools`. The harness is stricter
than the CI here — not dangerous, but the difference must be owned
and documented.

**Bandit.** The harness asks `bandit -q -ll -r alirpunkto`; the CI
runs `bandit -r alirpunkto tools -ll -q`. The harness thus omits
`tools/`, which the CI checks. An agent following only `AGENTS.md`
could report Bandit green while the CI fails in `tools/`.

**Pip-audit.** `AGENTS.md` cites security and the three workflows but
does not give the blocking local `pip-audit` command.

**Recommended fix.** Create a section clearly separating `## Exact CI
commands` from `## Additional local checks`; the first section's
commands must be copied literally from the workflows.

Status: inconsistency confirmed.

## 11. No test locks the harness yet

The repository has many structural tests for the workflows, the
Dockerfiles, the locks, the LDIF transport, and the Waitress
configuration. No specific test currently checks: that
`.claude/settings.json` is valid JSON; that `CLAUDE.md` still imports
`AGENTS.md`; that `.env.example` remains readable; that
`docker/.env.test` is denied; that the documented commands match the
CI; that the required tools are included in the installed locks; that
the Claude and Kimi local files are ignored. A repository search
returns no test dedicated to `AGENTS.md`, `CLAUDE.md` or
`.claude/settings.json`.

**Recommended test.** Add `tests/test_agent_harness.py` with at
minimum: JSON loading of `.claude/settings.json`; presence of
`@AGENTS.md` in `CLAUDE.md`; verification of the denies on `.env`,
`docker/.env`, `docker/.env.test`, `docker/secrets/**`; verification
that `.env.example` is not blocked; control that Ruff and Bandit are
pinned in `requirements-quality.lock`; comparison of the documented
commands with the workflows; verification of the Claude and Kimi
`.gitignore` entries.

Status: test debt.

## 12. Fix of the .env loading from the wheel

The first genuinely observed smoke run revealed a regression
introduced by the wheel installation. `find_dotenv()` historically
searched by walking up from the calling Python file; once the module
was installed in `site-packages`, that walk no longer met the `.env`
mounted in the container's working directory. The code now uses
`find_dotenv(usecwd=True) or find_dotenv()`, keeping the Docker
behaviour (where `.env` sits in the current directory) and the
historical fallback for non-container installations. A structural
test locks this form. Status: resolved.

## 13. State of the Docker smoke

The current commit's message states that the second observable run
reached: the full stack started; containers healthy; the HTTPS
request through Apache successful; failure only on the last
connection-throttle test. The cause was the absence of an Origin or
Referer header in curl's HTTPS POST requests, whereas a browser
normally provides it. The workflow now adds
`-e "https://${SERVER_NAME}/login"` to its shared curl array, and the
structural test checks the option stays present. The commit declares
1,023 tests passing, 72.10% coverage, and a successful local
reproduction of the throttle test after the Referer addition.

These results are reported by the developer. The GitHub connector
still returns neither a combined status nor a run associated with the
current SHA. The third smoke run, with the Referer fix, is therefore
not independently confirmed here.

Status: stack largely validated, the last full workflow still to
confirm.

## 14. Application findings still open

**Sanction persistence.** A new sanction can still be lost when the
group-side write succeeds, the member-side write fails, the next pass
treats the member side as authoritative, and the group-only leftover
is removed. A distinct authoritative source or a retry queue remains
recommended.

**LDIF serialisation.** Values transported cleanly over stdin are
still inserted into the LDIF without full serialisation of newlines
and base64-requiring values.

**Unencrypted LDAP by default.** LDAPS certificate validation exists,
but the shipped stacks still use port 389 without TLS by default —
explicitly the maintainer's call.

**Group-scan cost.** The scan still performs many LDAP reads per
group and per member.

**Periodic tasks.** Reminders remain triggered from `NewRequest`,
hence dependent on HTTP traffic and the current process.

**.env.example.** Still stale on the mail parameter names and
incomplete on LDAPS.

**Progressive quality.** mypy stays informative; Ruff stays limited
to the F family; `F841` stays ignored; the coverage floor is 68%;
real Certbot untested; CSP not enabled.

## 15. Revised priorities

**P0 — harness fixes.** 1. Replace `Read(./.env.*)` with explicit
sensitive paths. 2. Add `Read(./docker/.env.test)` to the denies.
3. Install `requirements-quality.lock` into the documented
environment. 4. Use the `.venv/bin/ruff` and `.venv/bin/bandit`
executables. 5. Align the Bandit and Ruff commands exactly on the CI.

**P1 — harness locking.** 1. Add `tests/test_agent_harness.py`.
2. Add `.kimi-code/local.toml` to `.gitignore`. 3. Clarify Codex
local versus Codex cloud. 4. Clarify Kimi Code CLI versus the other
Kimi K3 clients. 5. Possibly add `$schema` to
`.claude/settings.json` for editor validation.

**P2 — integration.** 1. Obtain an entirely green smoke run after the
Referer fix. 2. Run the harness from a pristine machine or container.
3. Verify each of the three agents actually discovers the
instructions. 4. Really test the documented commands with no globally
installed tool.

**P3 — application.** 1. Transactional sanction persistence. 2. LDIF
serialisation. 3. LDAP scan optimisation. 4. External scheduler for
the reminders. 5. `.env.example` update. 6. LDAPS, Certbot and CSP
tests.

## 16. Conclusion

The harness follows the right architecture: `AGENTS.md` is a common
contract recognised by Codex and Kimi Code CLI; `CLAUDE.md` imports
it correctly for Claude Code; `.claude/settings.json` is
syntactically valid; the project rules are precise and reflect the
lessons of the previous audits; the personal Claude adaptations stay
out of Git.

Two immediate configuration errors nevertheless exist:
1. `.env.example` is involuntarily denied to Claude;
2. `docker/.env.test` is not denied. To this adds a reproducibility
error: the installation procedure does not install the quality tools
it then requires.

The harness can therefore be used right now, but must not yet be
presented as entirely reliable or fully constraining.

**Harness evaluation: 7.6/10. Overall repository evaluation:
8.8/10.** After fixing the Claude permissions, aligning the commands
and adding a structural harness test, the multi-agent component could
reach about 9/10, and the overall grade progress toward 8.9–9.0/10 as
soon as a fully green smoke is observable.
