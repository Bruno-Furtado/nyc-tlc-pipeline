# Git convention

## Commits — Conventional Commits
`<type>(<scope>): <description>` — lowercase, imperative, no trailing period.
- types: feat, fix, docs, chore, refactor, test, build, perf, style
- scopes: setup, config, ingest, bronze, silver, gold, analysis, jobs
- Signed with GPG (`commit.gpgsign = true`). The squash merge also yields a signed commit on `main`.

## Branch
`<type>/<kebab-description>` — e.g. `feat/extract-bronze`.
Never commit directly to `main` — all work happens on a branch (enforced by the pre-commit hook).

## Pull Request
- Title in Conventional Commits (becomes the squash commit).
- Body: **What / Why / Notes**. One PR per phase.
- Before opening, review that all files are current — especially the Markdown (README, CLAUDE.md, docs/).
- **Assignee:** the PR author. **Reviewer:** n/a while solo (GitHub forbids the author reviewing their own PR).
- **Milestone:** one per step, e.g. `Step 1 — setup`.
- **Labels:** one `area:<phase>` + one `type:<kind>` per PR (e.g. `area:setup` + `type:feat`).
- Commits credit Claude via the `Co-Authored-By` trailer.

## Merge
Squash and merge. One commit per PR, linear history on `main`.

## Release
Tag a release when a phase completes: git tag `vX.Y.Z` + a GitHub Release (e.g. `v0.1.0` at the
end of setup). The tag marks the milestone; the release notes summarize what shipped.

## Before committing
Run `ruff check src/` (and `ruff format src/`). Commit/push only when asked.
