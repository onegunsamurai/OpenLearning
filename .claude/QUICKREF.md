# Pipeline quick reference

## Daily workflow cheatsheet

### Starting a new feature
```
/pipeline "As a user, I want to ..."
```
This runs everything. Go get coffee — it handles analysis, design, planning, TDD, reviews, testing, and docs.

### Iterative development (most common)
```
# You're coding, ready to commit
/quality-gate

# If it passes, commit happens automatically
# If it fails, fix the issues it reports, then:
/quality-gate
```

### Before a PR / merge
```
# Full test suite + doc sync + observability check
/doc-sync
# Then verify all tests pass
```

### Individual agent shortcuts
```
# "I need to understand this story better"
Task: story-analyzer "paste your story here"

# "Is this architecture secure?"
Task: threat-modeler "analyze src/auth/ and src/api/"

# "Will this migration break things?"
Task: schema-designer "add a status column to the orders table"

# "Is my API matching the contract?"
Task: contract-tester "validate src/api/routes/ against docs/api-spec.yaml"

# "Is this performant?"
Task: perf-analyzer "review src/services/search.ts"

# "Is this accessible?"
Task: a11y-auditor "audit src/components/Modal.tsx"

# "Are my docs stale?"
/doc-sync --fix

# "Does this have proper logging/metrics?"
Task: observability-checker "check src/services/payment.ts"
```

## Gate failure quick fixes

### Code reviewer says CRITICAL
→ Usually: missing error handling, exposed internals, broken abstraction
→ Fix the code, run `/quality-gate` again

### Security reviewer says CRITICAL
→ Usually: hardcoded secret, SQL injection, missing auth check
→ Fix immediately — these are real vulnerabilities

### Perf analyzer says CRITICAL
→ Usually: O(n²) in a hot path, unbounded query, missing pagination
→ Restructure the algorithm, add LIMIT, add index

### A11y auditor says CRITICAL
→ Usually: no keyboard access, missing form labels, zero contrast
→ Add semantic HTML, ARIA attributes, proper labels

### Refactor cleaner flags issues
→ Usually: dead exports, duplicate utility functions, orphan files
→ Delete the dead code, consolidate duplicates

### Doc sync out of sync
→ Run `/doc-sync --fix` to auto-repair
→ Or manually update the flagged docs

## What runs when

| Trigger | What runs |
|---------|-----------|
| `/pipeline "story"` | All 7 phases, all agents |
| `/quality-gate` | 5 agents in parallel (code, security, dead code, perf, a11y) |
| `/doc-sync` | Doc freshness cross-reference |
| `git commit` (via hook) | Checks gate report age and status |
| After any commit (via hook) | Reminds to check docs if code changed |

## Coverage targets

| Test type | Target | When written |
|-----------|--------|-------------|
| Unit tests | 80%+ per module | Phase 3 (TDD) |
| Integration tests | All boundaries | Phase 5 |
| Contract tests | All API endpoints | Phase 3 |
| E2E tests | All acceptance criteria | Phase 5 |
