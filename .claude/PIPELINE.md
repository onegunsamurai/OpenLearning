# Agentic Development Pipeline

An extension layer for [Everything Claude Code (ECC)](https://github.com/affaan-m/everything-claude-code) that adds a complete, gated development pipeline — from user story to merge-ready PR.

## What this adds to ECC

ECC provides excellent individual agents (planner, architect, tdd-guide, code-reviewer, security-reviewer, etc.). This pipeline adds:

1. **Missing agents** for gaps in the development lifecycle
2. **Orchestration** that chains agents in the correct order with gates
3. **Enforcement hooks** that prevent bypassing quality standards
4. **Feedback loops** that send review findings back for automated fixing

### New agents (8)

| Agent | Phase | Purpose |
|-------|-------|---------|
| `story-analyzer` | 0 | Structured acceptance criteria, edge cases, NFRs from user stories |
| `threat-modeler` | 1 | STRIDE threat analysis on architecture before code is written |
| `schema-designer` | 1 | Safe, backwards-compatible database migrations |
| `contract-tester` | 3 | Validates implementation matches API contracts |
| `perf-analyzer` | 4 | Algorithmic complexity, query analysis, bundle size, memory leaks |
| `a11y-auditor` | 4 | WCAG 2.1 AA compliance on UI changes |
| `integration-tester` | 5 | Cross-module boundary tests with real dependencies |
| `observability-checker` | 6 | Logging, metrics, tracing, error boundaries verification |

### New commands (3)

| Command | Purpose |
|---------|---------|
| `/pipeline "story"` | Full pipeline: analysis → design → plan → TDD → review → test → docs |
| `/quality-gate` | Run all 5 Phase 4 reviewers in parallel on current changes |
| `/doc-sync` | Verify documentation matches codebase |

### ECC agents used (unchanged)

| Agent | Phase | Role in pipeline |
|-------|-------|-----------------|
| `architect` | 1 | ADRs, component design, API contracts |
| `planner` | 2 | Task decomposition from architecture |
| `tdd-guide` | 3 | Red-green-refactor implementation |
| `build-error-resolver` | 3 | Fix compilation/type errors |
| `code-reviewer` | 4 | SOLID, DRY, readability, modularity |
| `security-reviewer` | 4 | OWASP audit, secrets detection |
| `refactor-cleaner` | 4 | Dead code, duplicates, unused exports |
| `e2e-runner` | 5 | Playwright E2E tests |
| `doc-updater` | 6 | Codemap, API docs, README, changelog |


## Usage

### Full pipeline (new features)
```
/pipeline "As a user, I want to reset my password via email so I can regain access to my account"
```

This runs the entire 7-phase pipeline. Each phase produces artifacts consumed by the next. Gates block progression until quality standards are met.

### Quick quality check (iterative development)
```
/quality-gate
```

Runs all 5 review agents (code, security, dead code, perf, a11y) in parallel on your uncommitted changes. Use this before every commit during normal development.

### Documentation freshness check
```
/doc-sync
/doc-sync --fix
```

Cross-references all documentation against the codebase. With `--fix`, delegates to doc-updater to repair stale docs.

### Using individual pipeline agents directly
```
# Analyze a story without running the full pipeline
Task: story-analyzer "As a user, I want to export my data as CSV"

# Run threat modeling on existing architecture
Task: threat-modeler "Analyze the authentication flow in src/auth/"

# Check performance of recent changes
Task: perf-analyzer "Review the changes in the last 3 commits"

# Verify observability
Task: observability-checker "Check observability for src/services/payment.ts"
```

### Combining with ECC commands
The pipeline commands work alongside ECC's existing commands:

```
# ECC's built-in commands still work
/plan "Add user authentication"     # ECC planner
/tdd                                 # ECC TDD guide
/code-review                         # ECC code reviewer
/security-scan                       # ECC security reviewer
/e2e                                 # ECC E2E runner

# Pipeline additions
/pipeline "user story"               # Full orchestrated pipeline
/quality-gate                        # Parallel review gate
/doc-sync                            # Documentation freshness
```

## Pipeline phases in detail

```
User Story
    │
    ▼
┌─────────────────────────────┐
│ Phase 0: ANALYSIS           │  story-analyzer
│ Acceptance criteria, NFRs,  │  (new)
│ edge cases, reuse scan      │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ Phase 1: DESIGN (parallel)  │  architect (ECC)
│ Architecture, threat model, │  threat-modeler (new)
│ schema, API contracts       │  schema-designer (new)
└─────────────┬───────────────┘
              │
         ═══ DESIGN GATE ═══
         ADR approved, 0 critical
         threats, contracts frozen
              │
              ▼
┌─────────────────────────────┐
│ Phase 2: PLANNING           │  planner (ECC)
│ Task decomposition,         │
│ dependency ordering         │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ Phase 3: TDD LOOP (per task)│  tdd-guide (ECC)
│ Red → Green → Refactor      │  build-error-resolver (ECC)
│ Contract validation         │  contract-tester (new)
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ Phase 4: QUALITY (parallel) │  code-reviewer (ECC)
│ 5 reviewers run at once     │  security-reviewer (ECC)
│ All must pass to commit     │  refactor-cleaner (ECC)
│                             │  perf-analyzer (new)
│                             │  a11y-auditor (new)
└─────────────┬───────────────┘
              │
         ═══ COMMIT GATE ═══
         0 critical, 0 high
              │
              ▼
┌─────────────────────────────┐
│ Phase 5: INTEGRATION & E2E  │  integration-tester (new)
│ Boundary tests, Playwright  │  e2e-runner (ECC)
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ Phase 6: DOCS & OBSERV.     │  doc-updater (ECC)
│ Sync docs, verify logging,  │  observability-checker (new)
│ metrics, tracing            │
└─────────────┬───────────────┘
              │
         ═══ MERGE GATE ═══
         All tests green, docs synced,
         coverage ≥80%, 0 vulns
              │
              ▼
         Merge-Ready PR
```

## Customization

### Adjusting coverage thresholds
Edit `.claude/rules/pipeline-workflow.md`:
```
- Coverage target: ≥80% per module, ≥70% overall
+ Coverage target: ≥90% per module, ≥85% overall
```

### Skipping agents for certain projects
If your project has no UI, the a11y-auditor will auto-skip. For other customizations, edit the command files in `.claude/commands/`.

### Adding project-specific security rules
Extend `threat-modeler.md` with project-specific threat patterns by adding rules to the bottom of the agent file.

### Changing the retry policy
Edit `/pipeline` command — search for "max 3 retries" and adjust.


## License

MIT — use freely, modify as needed. Built to extend ECC, not replace it.
