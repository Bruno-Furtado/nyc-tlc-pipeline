# Contributing

Full conventions live in [docs/conventions.md](docs/conventions.md). Quick reference:

## Workflow
1. Never commit directly to `main`. Create a branch: `<type>/<kebab-description>` (e.g. `feat/extract-bronze`).
2. One PR per phase, squash merged. Title in Conventional Commits.
3. PR body: **What / Why / Notes**.

## Commits
Conventional Commits: `<type>(<scope>): <description>` (lowercase, imperative, no trailing period).
- types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `build`, `perf`, `style`
- scopes: `setup`, `config`, `ingest`, `bronze`, `silver`, `gold`, `analysis`, `jobs`

## Before committing
Run `ruff check src/` and `ruff format src/`. Enable the pre-commit hook once per clone:
```
git config core.hooksPath .githooks
```

## Code style
Logging (not print), fail-fast errors with clear messages, type hints required (ruff E/F/I/ANN).
Keep it simple and explainable.
