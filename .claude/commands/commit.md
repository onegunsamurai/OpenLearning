Create a conventional commit from staged changes.

## Instructions

1. Run `git diff --cached` to see what's staged. If nothing is staged, tell the user and stop.

2. Analyze the staged changes:
   - Categorize the type of change (feat, fix, docs, kb)
   - Identify the scope (which domain/component is affected)
   - Understand the *why* behind the changes, not just the *what*

3. Draft a commit message following project conventions:
   - Format: `<type>: <description>` (e.g., `feat: add GitHub OAuth login flow`)
   - Types: `feat:`, `fix:`, `docs:`, `kb:`
   - Keep the subject line under 72 characters
   - Add a body paragraph if the change needs explanation of *why*

4. Present the draft commit message to the user and ask for approval before committing.

5. After approval, create the commit. Do NOT push unless explicitly asked.
