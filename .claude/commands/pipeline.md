# /pipeline — Full feature development pipeline

Run the complete agentic development pipeline from user story to merge-ready PR.

## Usage
```
/pipeline "As a user, I want to reset my password via email so I can regain access to my account"
```

## Execution sequence

You are an orchestrator. Execute each phase in order, using Task to delegate to specialized agents. DO NOT skip phases. DO NOT proceed past a gate until it passes.

### Phase 0: Worktree isolation

Before any work begins, create an isolated worktree so parallel pipelines don't conflict:

1. **If a GitHub issue number is known** (from the user story or explicit reference):
   ```bash
   bash scripts/worktree-create.sh <issue-number>
   cd .claude/worktrees/issue-<number>
   ```

2. **If no issue exists yet**, create one first:
   ```bash
   gh issue create --title "<short feature title>" --label enhancement
   ```
   Then create the worktree with the new issue number.

All subsequent phases operate from the worktree directory. `make` targets, `git` commands, and file paths work identically to the main worktree.

### Phase 0.5: Analysis & requirements
```
Task: story-analyzer
Input: The user story provided as argument
Wait for output: docs/stories/{slug}/analysis.md and criteria.json
```
Review the output. If there are open questions, STOP and ask the user before proceeding.

### Phase 1: Architecture & design (parallel)
Launch 3 agents in parallel:
```
Task 1: architect
Input: "Design the architecture for this feature based on docs/stories/{slug}/analysis.md. Produce ADR, component diagram, and API contracts."

Task 2: threat-modeler
Input: "Perform STRIDE threat modeling on the architecture in docs/stories/{slug}/. Output threat model and security requirements."

Task 3: schema-designer
Input: "Design schema changes for the feature described in docs/stories/{slug}/analysis.md"
```
Wait for ALL three to complete.

### DESIGN GATE
Before proceeding, verify:
- [ ] Architecture ADR exists and covers modularity, extensibility, separation of concerns
- [ ] Threat model has zero CRITICAL threats unmitigated
- [ ] API contracts are defined (OpenAPI, TypeScript interfaces, or equivalent)
- [ ] Schema migrations pass safety checklist
- [ ] No open questions remain

If gate fails: loop back to the failing agent with specific issues.

### Phase 2: Planning
```
Task: planner
Input: "Create implementation plan from docs/stories/{slug}/. Break into atomic TDD tasks. Mark parallelizable tasks."
Wait for output: implementation plan with ordered task list
```

### Phase 3: TDD implementation (per task)
For EACH task in the plan:
```
Step 3a — TDD:
Task: tdd-guide
Input: "Implement task: {task description}. Acceptance criteria: {from criteria.json}. Write tests first."

Step 3b — Build check:
Task: build-error-resolver
Input: "Fix any build errors from the latest changes"

Step 3c — Contract validation:
Task: contract-tester
Input: "Validate implementation matches API contracts in docs/stories/{slug}/"
```

### Phase 4: Quality gates (parallel — run ALL for each task)
Launch 5 agents in parallel:
```
Task 1: code-reviewer — "Review the code changes for this task"
Task 2: security-reviewer — "Security audit against docs/stories/{slug}/security-requirements.json"
Task 3: refactor-cleaner — "Check for dead code, duplicates, unused exports in changed files"
Task 4: perf-analyzer — "Performance review of changed files"
Task 5: a11y-auditor — "Accessibility audit of changed UI files" (skip if no UI changes)
```
Wait for ALL five. Merge results into single review report.

**COMMIT GATE**: If any agent reports CRITICAL or HIGH → fix and re-run Phase 4 (max 3 retries, then escalate to human).
If all pass → create commit with conventional commit message.

### Phase 5: Integration & E2E testing
```
Task 1: integration-tester
Input: "Write and run integration tests for the feature boundaries"

Task 2: e2e-runner
Input: "Write and run Playwright E2E tests covering acceptance criteria from docs/stories/{slug}/criteria.json"
```

### Phase 6: Documentation & observability (parallel)
```
Task 1: doc-updater
Input: "Update all documentation: codemap, API docs, README, CHANGELOG for this feature"

Task 2: observability-checker
Input: "Verify observability coverage for all new code paths"
```

### MERGE GATE
Final validation:
```bash
# Run full test suite
npm test -- --coverage

# Verify coverage threshold
# Check: coverage >= 80%

# Run E2E
npx playwright test

# Verify no known vulnerabilities
npm audit --production

# Verify docs are synced (doc-updater output)
```

If all pass → Generate PR summary with:
- Feature summary
- Architecture decisions made
- Test coverage report
- Security review summary
- Breaking changes (if any)
- Deployment notes
- Worktree cleanup command: `make worktree-remove ISSUE=<number> --delete-branch`

## Rules
- NEVER skip a phase. The pipeline exists for a reason.
- NEVER proceed past a failed gate. Fix first.
- Parallel agents should be launched with Task in parallel where noted.
- Each phase produces artifacts that downstream phases consume. Verify artifacts exist.
- If any agent fails 3 times on the same issue, STOP and request human review.
- Log progress to stdout so the developer can follow along.
