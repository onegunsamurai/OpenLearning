---
name: git-workflow
description: Branch naming, commit message conventions, and pre-commit workflow
globs: []
---

# Git Workflow

## Branch Naming
- `feat/` — New features (e.g., `feat/user-authentication`)
- `fix/` — Bug fixes (e.g., `fix/assessment-timeout`)
- `docs/` — Documentation changes (e.g., `docs/contributing-guide`)
- `kb/` — Knowledge base contributions (e.g., `kb/frontend-engineering`)

## Commit Messages
Use conventional format with these prefixes:
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation
- `kb:` — Knowledge base

Write messages that explain *why*, not just *what*:
- Good: `feat: add GitHub OAuth login flow`
- Good: `fix: handle Claude API timeout during assessment`
- Bad: `update files`
- Bad: `fix bug`

## Before Committing
- Always run `make check` (lint + typecheck + test + build)
- Never use `--no-verify` to bypass pre-commit hooks — fix the underlying issue instead
- Stage specific files rather than `git add -A` to avoid committing secrets or build artifacts
