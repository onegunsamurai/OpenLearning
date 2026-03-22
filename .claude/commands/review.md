Review staged or branch changes for issues.

## Instructions

1. Determine what to review:
   - If there are staged changes: `git diff --cached`
   - Otherwise: `git diff main...HEAD` (all branch changes)
   - If neither has changes, tell the user and stop.

2. Categorize changes by stack:
   - **Backend (Python):** routes, models, agents, graph, tests
   - **Frontend (TypeScript):** components, pages, lib, tests
   - **Cross-stack:** API contract changes, codegen impacts

3. Review against project standards:
   - Code style (Ruff rules, ESLint, TypeScript strict mode)
   - API design (CamelModel, error handling, OpenAPI sync)
   - Security (secrets, injection, auth patterns)
   - Testing (coverage gaps, weak assertions, missing edge cases)
   - DRY violations and unnecessary complexity

4. Output findings in structured format:
   ```
   [SEVERITY] file_path:line_number
   Problem: <description>
   Fix: <suggested change>
   Impact: <what could go wrong>
   ```

5. Summarize: total findings by severity, and whether the changes are ready to commit.
