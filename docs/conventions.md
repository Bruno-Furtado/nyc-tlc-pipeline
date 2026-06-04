# Git convention

## Commits — Conventional Commits
`<type>(<scope>): <description>` — lowercase, imperative, no trailing period.
- types: feat, fix, docs, chore, refactor, test, build, perf, style
- scopes: setup, config, ingest, bronze, silver, gold, analysis, jobs

## Branch
`<type>/<kebab-description>` — e.g. `feat/extract-bronze`.
Never commit directly to `main` — all work happens on a branch (enforced by the pre-commit hook).

## Pull Request
- Title in Conventional Commits (becomes the squash commit).
- Body: **What / Why / Notes / Next**. One PR per phase.
- Before opening, review that all files are current — especially the Markdown (README, CLAUDE.md, docs/).

## Merge
Squash and merge. One commit per PR, linear history on `main`.

## Before committing
Run `ruff check src/` (and `ruff format src/`). Commit/push only when asked.
