# Pipeline development workflow rules

## Worktree isolation — required for all feature/fix work

Every feature or bug fix MUST run in its own git worktree to enable parallel development. Never work directly on `main`.

**Creating a worktree:**
```bash
bash scripts/worktree-create.sh <issue-number>
cd .claude/worktrees/issue-<number>
```

This script handles branch creation (prefix inferred from labels), env file symlinks, and dependency installation. All `make` targets, `git` commands, and relative paths work identically inside a worktree.

**Listing active worktrees:** `make worktree-list`

**Cleanup after PR merge:** `make worktree-remove ISSUE=<number> --delete-branch`

If you are already inside a worktree (check: `git rev-parse --show-toplevel` contains `.claude/worktrees/`), skip worktree creation and proceed with the current worktree.

## Mandatory workflow

When implementing a new feature, ALWAYS follow the pipeline phases in order. Never jump to coding without completing analysis and design phases.

### Phase gates — non-negotiable

1. **Design gate**: Architecture ADR, threat model, and API contracts must exist before any implementation begins. If asked to "just start coding", push back and run /pipeline or at minimum the architect + threat-modeler agents first.

2. **Commit gate**: Every commit must pass code review, security review, dead code check, performance review, and (for UI changes) accessibility audit. Use /quality-gate before every commit.

3. **Merge gate**: Full test suite (unit + integration + E2E + contract) must pass with ≥80% coverage, documentation must be verified in sync, and observability must be confirmed before merging.

## Agent delegation rules

### Always delegate, never inline
- Architecture decisions → architect agent (not inline reasoning)
- Security analysis → security-reviewer + threat-modeler agents
- Test writing → tdd-guide agent (tests FIRST, then implementation)
- Code review → code-reviewer agent (not self-review)
- Performance concerns → perf-analyzer agent

### Parallel execution
These agents are INDEPENDENT and must run in parallel, not sequentially:
- Phase 1: architect + threat-modeler + schema-designer
- Phase 4: code-reviewer + security-reviewer + refactor-cleaner + perf-analyzer + a11y-auditor
- Phase 6: doc-updater + observability-checker

### Retry policy
- Max 3 automatic retries for any failing gate
- After 3 failures: STOP and present the issues to the user for human decision
- Never silently skip a failing check

## Code quality standards

### Modularity requirements
- Single Responsibility: each module/file does ONE thing
- Open/Closed: extend via interfaces, not modification
- Dependency Inversion: depend on abstractions, not concrete implementations
- No file should exceed 300 lines. If it does, refactor.
- No function should exceed 50 lines. If it does, decompose.

### Test requirements
- Unit tests: every public function/method
- Integration tests: every cross-module boundary
- Contract tests: every API endpoint
- E2E tests: every acceptance criterion from the user story
- Coverage target: ≥80% per module, ≥70% overall

### Documentation requirements
- Every public API has JSDoc/docstring
- Architecture decisions have ADRs
- Complex logic has inline comments explaining WHY (not WHAT)
- README is accurate and up-to-date
- Changelog is maintained

### Security requirements
- All user input is validated and sanitized
- No secrets in code (use env vars)
- Authentication/authorization on every endpoint
- OWASP Top 10 compliance verified per commit
- Dependencies scanned for known vulnerabilities

### No dead code
- No unused exports
- No unreachable code paths
- No commented-out code blocks
- No orphan files (files not imported anywhere)
- Run refactor-cleaner before every merge
