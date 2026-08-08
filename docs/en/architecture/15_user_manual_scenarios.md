# 15. Validation scenarios and the self-generated user manual

## Principle

The user manual is not written: it is **generated**. Every
important journey is replayed by a real browser (Playwright)
against the local Docker test stack, screen by screen; each step
captures the screen and records a caption **in French and in
English**. The generator assembles captures and captions into
bilingual manual pages, published as a CI artifact on every run.
The structural consequence: the user documentation can no longer
lie — every picture comes from a journey continuous integration
just validated, and a changed screen breaks the scenario before it
can stale the manual.

## Architecture

- `tools/e2e_scenarios/framework.py` — the `Scenario` class:
  `step(page, slug, fr, en)` captures the screen
  (`<scenario>_NN_<slug>.png`) and records both captions into
  `manifest.json`; the signature **enforces** bilingualism.
  `fetch_email(recipient)` reads the test postfix capture mailbox
  (transport overridable through `E2E_MAIL_CMD`).
  `solve_all_challenges(body)` solves the four math challenges of
  the registration e-mail **without depending on operators**: the
  `n1 × n2 + n3` structure is fixed, so it extracts the first three
  number words of the line (English, French and Esperanto
  dictionaries) — a necessity learned from evidence: the e-mail
  template renders in Esperanto and the English catalog says
  "multiplied by", not "times".
- `tools/e2e_scenarios/scenario_registration.py` — the first two
  journeys: ordinary member registration (through the new
  account's first login) and Cooperator application (through the
  wait for verifiers). Every submission **verifies the reached
  screen** before captioning it: a refusal yields an explicit
  failure capture, never a success caption on an error screen.
- `tools/e2e_scenarios/run_all.py` — the strict runner.
- `tools/generate_user_manual.py` — manifest + captures →
  `manual/fr/*.md` and `manual/en/*.md` with images and an index.

## The test postal chain

The test stack's postfix is an **offline sink**
(`start_test_postfix.sh`): it accepts everything and relays
nothing. With `POSTFIX_LOCAL_CAPTURE=1` (set by the test compose),
mail **for the test domain** is kept in the local mailbox of the
`catchall` user — delivered as a Maildir
(`/home/catchall/Maildir/`, one file per message, since
`home_mailbox = Maildir/`) — while everything else stays
discarded: nothing ever leaves the stack. `maillog_file =
/dev/stdout` makes deliveries visible in `docker logs`.

## Operations

In CI: the `test-stack` workflow runs the scenarios after the
login journey, then publishes two artifacts — `user-manual` (the
illustrated fr/en pages) and `e2e-screenshots` (every capture,
failures included: diagnosis is built in).

Locally:

    bash docker/init_test.sh
    docker compose --env-file docker/.env.test \
        -f docker/test-docker-compose.yaml up -d --build
    python -m venv /tmp/e2e-venv && /tmp/e2e-venv/bin/pip install \
        --require-hashes -r requirements-e2e.lock
    /tmp/e2e-venv/bin/playwright install chromium
    cd tools/e2e_scenarios && E2E_SHOT_DIR=/tmp/e2e-shots \
        /tmp/e2e-venv/bin/python run_all.py
    /tmp/e2e-venv/bin/python ../generate_user_manual.py \
        /tmp/e2e-shots /tmp/user-manual

## Writing a new scenario

Create `scenario_<name>.py`, instantiate `Scenario(slug, title_fr,
title_en)`, walk the journey calling `step()` on every screen —
always both captions — then `close()`. Register the journey in
`run_all.py`. Rules learned from evidence: drive the **real
widgets** (the membership choice is a `<select>`; deform forms
submit through `<button type="submit">`, hence `_submit()`'s
composite selector; the deform date field is named `date`);
**verify every reached screen** before captioning it; never assume
the e-mail's language.

## What the scenarios have already caught

Their fifth run found a defect unit tests could not see:
`preferredLanguage` was set unguarded at LDAP creation, and the
ordinary journey never enters a language — **no ordinary member
could be created through the registration form at all** (train
0095: a guard on `lang1` plus a belt stripping every empty
attribute before `conn.add`). That is these journeys' reason to
exist: they live what users live.

Next scenario in the series: the **verifiers' vote**, which turns
the Cooperator candidate into a full Cooperator.
