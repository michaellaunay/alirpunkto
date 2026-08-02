# CLAUDE.md

@AGENTS.md

## Claude Code specifics

- Speak **French** with the maintainer (Michaël); keep all code,
  comments, identifiers and commit messages in **English**.
- Default deliverable: a numbered patch file at the repository root
  (gitignored) plus the expanded commit message in your reply — never
  `git push`; the maintainer merges.
- Run the full suite before proposing a patch and quote the exact
  green count and coverage figure.
- The permission policy in `.claude/settings.json` provides
  **guardrails** against direct pushes, lock-file edits and
  secret-file reads — it gates matching tool calls, it is not an
  absolute sandbox. Do not bypass those guardrails through shell
  commands; ask the maintainer instead.
- When a change answers an external-audit finding, cite the pass and
  section (`Refs: audit section N`) and check whether the finding's
  filing under `docs/*/audits/` needs a follow-up note.
