# 14 — Developing with AI agents (Claude Code, Codex, Kimi)

The repository ships an audited **multi-agent harness** (twelfth
external pass): `AGENTS.md` is the shared contract — environment,
exact CI commands, delivery conventions, hard rules and testing
gotchas — read natively by Codex and Kimi Code CLI; `CLAUDE.md`
imports it (`@AGENTS.md`) and adds only the Claude Code specifics;
`.claude/settings.json` turns the rules into enforceable permissions;
`tests/test_agent_harness.py` locks the whole (valid JSON,
`.env.example` never blocked, documented commands in parity with the
workflows). This chapter explains how to install each agent and work
with it on this repository specifically.

Common principle, whatever the agent: the local deliverable is a
**numbered patch** (`git diff > NNNN-topic.patch`, gitignored) that
applies with `git apply` on a pristine clone of `master` — never
`git push`, the maintainer merges; every behavioural change ships
with its **red/green demonstration**; French is the conversation
language with the maintainer, English the language of code and
commits.

## Claude Code

**Prerequisites.** Node.js 18 or later, and access: either a Claude
subscription (Pro/Max — Claude Code is included, usage is shared with
the chat) or an Anthropic API key billed per token. Known trap: if
`ANTHROPIC_API_KEY` lingers in the shell, Claude Code silently uses
it and bills the API while ignoring the subscription — check with
`echo $ANTHROPIC_API_KEY` before the first session.

**Installation and first launch.**

```bash
npm install -g @anthropic-ai/claude-code
cd ~/path/to/alirpunkto
claude          # first time: sign in (subscription or API key)
```

Launched at the root, Claude Code loads `CLAUDE.md`, which imports
`AGENTS.md`: the agent knows from the start how the environment is
set up (the **two** hashed locks in `.venv`, the `mkdir -p var`), the
exact CI commands, the maintainer's three settled decisions never to
reopen, and the traps (the test `SECRET_KEY` must be a Fernet key,
`get_secret` pops the environment, and so on).

**The permission policy in practice.** `.claude/settings.json` is
versioned and shared: repository reads and the pytest/ruff/bandit
loop run **silently**; `git commit`, `git apply`, `pip install` and
`docker` **ask for confirmation**; reading `.env`, the sensitive
`docker/.env*` files and `docker/secrets/`, `git push`, `rm -rf` and
editing the three locks are **denied**. The tracked `.env.example`
stays readable — it is precisely a file to audit. These rules are
**guardrails** on matching tool calls, not an absolute sandbox: do
not bypass them through equivalent shell commands. Personal overrides
go into `.claude/settings.local.json` (gitignored).

**Example sessions on AlirPunkto.**

```text
> Set up the environment and run the full suite the way the CI does.
```

The agent creates `.venv` from `requirements-test.lock` then
`requirements-quality.lock` (`--require-hashes`), runs `mkdir -p
var`, exports the test environment (including a Fernet `SECRET_KEY`)
and executes pytest with coverage — the exact command lives in
`AGENTS.md`.

```text
> The twelfth audit asks for a validating LDIF serialiser (§12).
> Prepare train 0085: implementation, red/green tests, a patch
> that applies on master, an expanded commit message with the
> Refs trailer.
```

```text
> Why does tests/test_ldif_callers.py reject my comment?
```

(Expected agent answer: a structural lock forbids certain tokens in
the scripts — reword the comment, never weaken the lock.)

## Codex (OpenAI)

Codex CLI reads `AGENTS.md` at the root **natively**: no extra
configuration is needed for this repository.

**Installation** (Node.js 18+; ChatGPT Plus/Pro/Team account or an
OpenAI API key):

```bash
npm install -g @openai/codex     # the package is @openai/codex,
cd ~/path/to/alirpunkto          # not "codex" (an unrelated package)
codex
```

An official install script also exists
(`https://chatgpt.com/codex/install.sh`) as well as a Homebrew cask.

**On this repository.** The same example sessions hold verbatim —
the contract is the same file. **Codex cloud / PR mode** particular
(documented in `AGENTS.md`): the gitignored patch deliverable does
not suit a managed workspace preparing a pull request; in that mode,
modify the tracked tree and present the resulting diff — but never
push without the maintainer's explicit request.

## Kimi (Moonshot — Kimi K3 through Kimi Code CLI)

Kimi Code CLI also loads `AGENTS.md` natively (its `/init` command
can even generate one — unnecessary here, the file exists). Mind the
nuance: this compatibility belongs to the Kimi Code CLI **client**,
not to the Kimi K3 model — through the API, a web UI or another
orchestrator, provide `AGENTS.md` explicitly as project
instructions.

**Installation** (Kimi subscription or API key; `/login` on first
launch):

```bash
curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash
# or, with Node.js ≥ 22.19: npm install -g @moonshot-ai/kimi-code
cd ~/path/to/alirpunkto
kimi
```

Documented trap: the PyPI package `kimi-code` is the legacy Python
agent — the current Kimi Code lives on npm; a `kimi --version` in
`0.x` confirms the right product. The CLI's personal state
(`.kimi-code/local.toml`) is gitignored.

## Checking the harness itself

The harness is tested like the rest of the code:

```bash
.venv/bin/python -m pytest tests/test_agent_harness.py -q
```

These locks notably guarantee that the commands quoted in `AGENTS.md`
stay the exact copy of the workflows' — a drift on either the CI or
the documentation side fails the suite. Original findings: the
twelfth-pass filing,
`docs/en/audits/20260802_external_chatgpt_audit_alirpunkto_12th_pass.md`.
