# AGENTS.md — working agreement for coding agents on AlirPunkto

Read this file in full before touching anything. `CLAUDE.md` imports it
for Claude Code; point any other agent (Codex, Kimi, …) here first —
most modern coding CLIs pick this file up automatically, and a single
"read AGENTS.md" instruction covers the rest.

## What this project is

A Pyramid/ZODB web application managing cooperative memberships.
OpenLDAP is the source of truth for identities, roles and groups;
Keycloak is an optional SSO layer (never the sole authentication
point); Postfix sends the mail. Python 3.12. Application package:
`alirpunkto/`. Tests: `tests/` (pytest). Docker stacks under `docker/`
(production and test compose files). Documentation is bilingual under
`docs/fr/` and `docs/en/` (strict mirrors). External audit reports are
filed under `docs/*/audits/`.

## Environment setup — hashed locks only

```
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements-test.lock
mkdir -p var    # ZODB lock file lives here; a missing var/ causes
                # phantom zc.lockfile errors in otherwise green tests
```

Never `pip install` anything ad hoc: the three `requirements*.lock`
files are the only sources of packages (runtime, test, quality), each
hash-pinned. CI installs from them with `--require-hashes`.

## Canonical commands

Full suite — exactly what CI runs (the SECRET_KEY **must** be a Fernet
key; a random string breaks the SSO-seal tests):

```
LDAP_PASSWORD=test-ldap-password ADMIN_PASSWORD=test-admin-password \
MAIL_PASSWORD=test-mail-password DOMAIN_NAME=example.com \
SITE_NAME="AlirPunkto CI" PYTHONPATH=. \
SECRET_KEY="$(.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
.venv/bin/python -m pytest -q --cov=alirpunkto --cov-fail-under=68
```

Single file: same environment, `… -m pytest tests/test_x.py -q`.

Lint and security (both blocking in CI):

```
ruff check alirpunkto tests tools docker/apply_server_overrides.py docker/generate_ldif.py
bandit -q -ll -r alirpunkto
```

Compose sanity (PyYAML alone is NOT a validation — see hard rules):

```
docker compose --env-file docker/.env -f docker/docker-compose.yaml config --quiet
docker compose --env-file docker/.env -f docker/test-docker-compose.yaml config --quiet
```

## Delivery conventions — non-negotiable

- Work is delivered as **numbered patch files** (`git diff >
  NNNN-slug.patch`, gitignored) that apply cleanly with `git apply` on
  a **pristine clone of master**. Never push; the maintainer merges.
- **Conventional Commits, in English, with an expanded body**:
  problem → fix → evidence. Add the trailer
  `Refs: audit section N` when the change answers an external-audit
  finding.
- Every behavioural change ships with a **red/green demonstration**:
  the new or updated tests must FAIL on the previous state of the tree
  and pass after the change. State the counts.
- Docs are **bilingual mirrors**: touching `docs/fr/…` means updating
  the matching `docs/en/…` in the same patch (and vice versa).
- Language: **French with the maintainer; English in code, comments,
  commit messages and identifiers**.

## Hard rules — never do these

- Never commit secrets. No real `.env` in the tree, test values only —
  CI runs gitleaks over the **full history**.
- Never hand-edit a `requirements*.lock`: regenerate with
  `pip-compile --generate-hashes --allow-unsafe --strip-extras`,
  seeding the previous lock as input to avoid version drift.
- Never weaken a structural test so a new comment can pass: **reword
  the comment**. Several tests lock the absence of tokens
  (`slappasswd`, `pyproject.toml`, `GENERATE_LDIF_`, …) and your own
  prose can trip them.
- Every caller of `docker/generate_ldif.py` goes through the shared
  emitter `docker/ldif_records.sh` — one copy of the transport
  contract, enforced by `tests/test_ldif_callers.py`. When migrating
  ANY interface, grep **all** caller directories, `.github/` included.
- Do not "validate" compose files with PyYAML alone: its loader
  silently keeps duplicate keys where compose refuses the file. Use
  `docker compose config` or the strict reader in
  `tests/test_ldif_callers.py`.
- Settled maintainer decisions — do not reopen, do not "fix":
  1. the encrypted DEBUG password logs stay (RSA-OAEP to an
     environment public key, gated by env var);
  2. the module-level globals of `constants_and_globals` are
     intentional, and `.env` is read once;
  3. Keycloak is never the sole authentication point — direct LDAP
     login is a feature.
  LDAPS in the shipped compose stacks is an **open operations
  decision**: the validating mechanism exists, enabling it is the
  maintainer's call — implement nothing there unprompted.

## Testing gotchas — they will bite you

- `get_secret` POPs its environment variables into a cache on first
  call; a fixture clearing that cache must save and restore it, or
  later tests fail order-dependently.
- `get_keycloak_token` carries a `PYTEST_CURRENT_TEST` guard: patch it
  to `None` to exercise the real wire.
- The session-cookie budget is 4093 bytes; the token-seal budget test
  must use an **incompressible** token (compression runs before
  encryption).
- `find_dotenv` looks in the current directory first, then falls back
  to the historical frame walk (the wheel layout moved the module out
  of the repository) — see `constants_and_globals.py`.

## CI — three workflows, all must stay green

`tests.yml` (full suite from the hashed test lock), `quality.yml`
(ruff F rules blocking, bandit `-ll`, pip-audit over the three locks,
gitleaks over full history, mypy observational), `smoke.yml` (builds
the real images, validates both compose files, boots the production
stack, one HTTPS request through Apache, proves the real client
address reaches the throttle).
