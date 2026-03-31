# /quality-gate — Run all Phase 4 quality agents in parallel

Quick command to run the full quality gate on current changes without running the entire pipeline. Useful for iterative development.

## Usage
```
/quality-gate
/quality-gate --story password-reset    # reference a specific story's security requirements
```

## Execution

Launch ALL of these agents in parallel using Task:

```
Task 1: code-reviewer
"Review all uncommitted changes. Check SOLID, DRY, naming, error handling, modularity, extensibility."

Task 2: security-reviewer
"Security audit on all uncommitted changes. OWASP Top 10. Check for secrets, injection, auth issues."

Task 3: refactor-cleaner
"Scan changed files for dead code, unused exports, duplicate logic."

Task 4: perf-analyzer
"Performance review of changed files. Check algorithmic complexity, DB queries, memory, bundle size."

Task 5: a11y-auditor
"Accessibility audit on changed UI files." (skip if no UI changes detected via: git diff --name-only | grep -E '\.(tsx|jsx|vue|svelte|html)')
```

## After all complete

Merge results into a single report:

```
## Quality gate report

### Code review: PASS/FAIL
[findings]

### Security review: PASS/FAIL
[findings]

### Dead code check: PASS/FAIL
[findings]

### Performance review: PASS/FAIL
[findings]

### Accessibility audit: PASS/FAIL (or SKIPPED)
[findings]

---
OVERALL: PASS / FAIL (X critical, Y high, Z medium)
```

If FAIL: list each blocking issue with file, line, and suggested fix.
If PASS: suggest committing with a conventional commit message.
