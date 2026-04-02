# Issue #152: Isolated Docker Environments for Parallel Claude Code Worktrees

## 1. Story Summary

When running `/pipeline` in a git worktree (`.claude/worktrees/issue-<N>`), the local Docker dev environment fails due to port conflicts, symlinked `node_modules` breaking Turbopack, CORS mismatches on non-standard ports, and stale anonymous Docker volumes. This feature introduces a `make worktree-dev ISSUE=<N>` command that derives unique ports per issue number, generates a Docker Compose override, handles symlink cleanup, configures CORS dynamically, and ensures all services start cleanly with health checks. The goal is to enable fully automated, conflict-free parallel development environments that require zero manual troubleshooting.

**Actor:** Developer (human or Claude Code agent) running a pipeline or E2E tests inside a git worktree.
**Goal:** Start an isolated Docker dev environment (DB + backend + frontend) from a worktree with a single command, with no port conflicts against other worktrees or the main repo stack.
**Business value:** Eliminates brittle manual setup that wastes 15-30 minutes per worktree, unblocks truly parallel development, and makes the agent pipeline fully autonomous for E2E testing.

### Implicit Assumptions

- The issue number is always a positive integer, and the port derivation formula must produce valid, non-overlapping port numbers for any reasonable issue number.
- The Docker Compose override file is ephemeral (not committed) and generated fresh each time.
- The `worktree-create.sh` script currently symlinks `frontend/node_modules` indirectly (it runs `npm install` but if the main repo has a `node_modules` symlink, the worktree inherits git-tracked references). Investigation shows the script already runs `npm install` (line 169), so the symlink problem may come from a different path or from git worktree sharing.
- The backend container's internal port (8000) and frontend container's internal port (3000) remain fixed; only the host-mapped ports change.
- PostgreSQL data volumes should be per-worktree (namespaced) to avoid data conflicts between parallel environments.
- The user's existing `docker-compose.yml` and `docker-compose.dev.yml` remain unchanged for production and main-repo dev workflows.

## 2. Acceptance Criteria

### AC-1: Single-command isolated environment startup (Happy Path)

```
GIVEN a worktree exists at .claude/worktrees/issue-144
WHEN the developer runs `make worktree-dev ISSUE=144` from the repo root or worktree
THEN Docker Compose starts db, backend, and frontend services
  AND ports are derived from issue number (e.g., frontend: 3144, backend: 8144, db: 5544)
  AND all three services pass health checks before the command returns
  AND the command prints the accessible URLs (frontend, backend, db port)
```

### AC-2: Two worktrees running simultaneously without conflicts

```
GIVEN worktree issue-144 is running via `make worktree-dev ISSUE=144`
WHEN the developer runs `make worktree-dev ISSUE=145` for a second worktree
THEN the second stack starts successfully on different ports (frontend: 3145, backend: 8145, db: 5545)
  AND both stacks remain operational with independent databases
  AND neither stack's health checks fail
```

### AC-3: CORS automatically configured for worktree's frontend port

```
GIVEN `make worktree-dev ISSUE=144` is invoked
WHEN the backend starts
THEN the backend's CORS_ORIGINS environment variable includes http://localhost:3144
  AND the frontend's NEXT_PUBLIC_API_URL points to http://localhost:8144
  AND API calls from the frontend succeed without CORS errors
```

### AC-4: Symlink cleanup happens automatically

```
GIVEN frontend/node_modules is a symlink (pointing to the main repo's node_modules)
WHEN `make worktree-dev ISSUE=144` is invoked
THEN the symlink is removed and replaced with a real directory (via npm install)
  AND Docker containers start without Turbopack symlink errors
```

### AC-5: package-lock.json symlink handled

```
GIVEN frontend/package-lock.json is a symlink
WHEN `make worktree-dev ISSUE=144` is invoked
THEN the symlink is replaced with a real copy of the file
  AND npm install and Docker builds succeed
```

### AC-6: Stale volumes cleaned automatically

```
GIVEN a previous Docker run left stale anonymous volumes with broken node_modules
WHEN `make worktree-dev ISSUE=144` is invoked
THEN containers start with --force-recreate -V flags
  AND no stale volume data is reused
```

### AC-7: Health checks pass before command exits

```
GIVEN `make worktree-dev ISSUE=144` is invoked
WHEN all three services are starting
THEN the command waits for:
  - PostgreSQL to accept connections (pg_isready)
  - Backend /api/health to return 200
  - Frontend to respond on its port
THEN the command exits with code 0 only after all checks pass
```

### AC-8: COMPOSE_PROJECT_NAME isolation

```
GIVEN `make worktree-dev ISSUE=144` is invoked
WHEN Docker Compose creates containers, networks, and volumes
THEN the project name is namespaced (e.g., openlearning-wt-144)
  AND containers do not conflict with the main repo's docker compose stack
  AND named volumes (postgres-data) are namespaced per worktree
```

### AC-9: FRONTEND_URL configured for OAuth redirects

```
GIVEN `make worktree-dev ISSUE=144` is invoked
WHEN the backend starts
THEN the FRONTEND_URL environment variable is set to http://localhost:3144
  AND OAuth redirect URLs use the correct worktree-specific frontend port
```

### AC-10: Worktree dev teardown

```
GIVEN a worktree dev stack is running (issue-144)
WHEN the developer runs `make worktree-dev-down ISSUE=144`
THEN all containers, networks for that worktree are stopped and removed
  AND named volumes are optionally preserved (can be cleaned with a separate flag)
  AND no other worktree stacks are affected
```

### AC-11: Run from inside the worktree directory

```
GIVEN the developer is cd'd into .claude/worktrees/issue-144
WHEN they run `make worktree-dev` (without ISSUE= argument)
THEN the issue number is auto-detected from the directory name
  AND the environment starts correctly
```

### AC-12: Worktree-create.sh updated to skip node_modules symlink

```
GIVEN a new worktree is being created via `bash scripts/worktree-create.sh 155`
WHEN the script sets up the worktree
THEN frontend/node_modules is NOT symlinked from the main repo
  AND a real npm install is performed (this is already the case, but verify no symlink exists)
```

### AC-13: Documentation exists for worktree dev workflow

```
GIVEN a developer (or agent) needs to run isolated Docker environments
WHEN they consult the documentation
THEN docs/worktree-dev.md (or equivalent section in existing docs) explains:
  - How to start an isolated environment
  - Port derivation scheme
  - How to run E2E tests against the worktree environment
  - How to tear down the environment
  - Troubleshooting common issues
```

## 3. Edge Cases & Error States

| Scenario | Expected Behavior |
|---|---|
| Issue number is 0 | Script rejects with an error: issue number must be >= 1 |
| Issue number is very large (e.g., 99999) | Port derivation produces ports > 65535. Script detects this and exits with a clear error message explaining the port range overflow. |
| Issue number produces port collision with well-known service (e.g., ISSUE=306 -> frontend 3306 = MySQL default) | No special handling needed -- this is a dev environment. Document the port scheme so developers can avoid known conflicts. |
| Derived port is already in use by another (non-worktree) process | Docker Compose fails with "address already in use". Script catches this and suggests checking `lsof -i :<port>`. |
| Docker daemon is not running | Script detects Docker is unavailable and exits with a clear error message before attempting anything. |
| Worktree directory does not exist for the given ISSUE number | Script exits with an error: "Worktree for issue-N not found. Run `make worktree-create ISSUE=N` first." |
| frontend/node_modules is a real directory (not a symlink) | Script skips symlink removal; no-op for this step. |
| frontend/node_modules does not exist at all | Script runs npm install to create it. |
| frontend/package-lock.json is a real file (not a symlink) | Script skips copy; no-op. |
| frontend/package-lock.json does not exist | Script runs npm install which generates it. |
| ISSUE number has leading zeros (e.g., 0144) | Bash arithmetic strips leading zeros. Port derivation should work correctly. Validate. |
| Two worktrees with adjacent issue numbers (e.g., 144, 145) | Ports are unique (3144 vs 3145). No collision. |
| User runs `make worktree-dev ISSUE=144` twice in a row | Second invocation detects running containers and either restarts them (with --force-recreate) or warns that the stack is already running. |
| Docker Compose version does not support `--wait` flag | Fallback to polling health endpoints manually. `--wait` requires Docker Compose V2 (2.1+). |
| Backend health check times out (e.g., missing DB migrations) | Script times out after a configurable period (default 120s) and exits with error code, printing container logs for debugging. |
| Main repo Docker stack is already running on default ports | Worktree stack starts on different ports; no interference. |
| `make worktree-dev-down ISSUE=144` called when no stack is running | Script prints "No running stack for issue-144" and exits cleanly (code 0). |
| Multiple agents try to start the same worktree dev stack concurrently | First one wins; second gets "address already in use" or Docker lock error. Acceptable -- same worktree should not run twice. |
| Node.js version mismatch between host and Docker container | Docker container uses node:20-slim regardless of host. If host npm install differs, Docker `--force-recreate -V` ensures a fresh node_modules volume. |
| `.env` files missing in worktree (symlinks broken) | Script checks that required .env files exist and warns if missing, pointing to `worktree-create.sh`. |
| macOS Docker Desktop resource limits (memory/CPU) running multiple stacks | Not enforced by the script. Document that each stack requires ~1GB RAM as a guideline. |

## 4. Non-Functional Requirements

| Category | Requirement | Target |
|---|---|---|
| **Performance** | `make worktree-dev` cold start time (no cached images) | < 120 seconds on a typical M1/M2 Mac with warm Docker cache |
| **Performance** | `make worktree-dev` warm start time (images cached, no npm install needed) | < 30 seconds |
| **Performance** | Port derivation and override file generation | < 1 second |
| **Security** | No secrets hardcoded in generated override files | Override file uses env var references only; generated file is .gitignored |
| **Security** | Generated docker-compose.worktree.yml must not be committed | Added to .gitignore |
| **Security** | CORS_ORIGINS must not use wildcard `*` | Explicit `http://localhost:<port>` only |
| **Scalability** | Support at least 10 simultaneous worktree dev environments | Port scheme must produce unique, valid ports for ISSUE 1-999+ |
| **Reliability** | Script is idempotent: running it twice produces the same result | Second run recreates containers cleanly |
| **Reliability** | Health check timeout with clear error reporting | Timeout at 120s with container log dump |
| **Observability** | Script prints which ports are assigned, URLs, and container status | Human-readable output with clear section headers |
| **Observability** | Container logs accessible after startup | Standard `docker compose logs` works with the project name |
| **Internationalization** | N/A | Infrastructure tooling, English only |
| **Accessibility** | N/A | CLI tool, not a UI feature |

## 5. Reuse Candidates

### Scripts to extend (not replace)

| File | What to reuse | How |
|---|---|---|
| `scripts/worktree-create.sh` | Existing worktree setup logic, env file symlink pattern, argument parsing pattern, helper functions (`slugify`, `symlink_if_exists`) | Add a post-setup step to ensure node_modules is not a symlink. The script already runs `npm install` (line 169), so the fix may be minimal. |
| `scripts/worktree-remove.sh` | Teardown pattern, argument parsing, `--force` and `--all` flags | Add Docker stack teardown to the removal flow (stop containers + remove project volumes). |
| `scripts/worktree-list.sh` | Listing pattern, status column | Add a "Docker" column showing whether a worktree dev stack is running. |

### Docker Compose files to compose with (not modify)

| File | What to reuse | How |
|---|---|---|
| `docker-compose.yml` | Base service definitions (db, backend, frontend), health checks, volume definitions | The worktree override layers on top: `docker compose -f docker-compose.yml -f docker-compose.worktree-<N>.yml` |
| `docker-compose.dev.yml` | Dev overrides (volume mounts, hot reload commands) | Optionally compose with this for hot-reload dev environments: `docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.worktree-<N>.yml` |

### Backend configuration to extend

| File | What to reuse | How |
|---|---|---|
| `backend/app/config.py` | `Settings.cors_origins` is already a `list[str]` from `pydantic-settings`, populated by `CORS_ORIGINS` env var | The override file sets `CORS_ORIGINS` as a JSON array string. No backend code changes needed. |
| `backend/app/config.py` | `Settings.frontend_url` is already configurable via env var | The override file sets `FRONTEND_URL`. No backend code changes needed. |

### Makefile patterns to follow

| File | Pattern | How |
|---|---|---|
| `Makefile` (lines 91-99) | Existing worktree targets pass `$(ISSUE)` to shell scripts | Follow the same pattern: `worktree-dev: @bash scripts/worktree-dev.sh $(ISSUE)` |
| `Makefile` (lines 79-89) | Docker targets use `docker compose -f` flags | Follow for the override compose file approach |

### Test patterns

| File | Pattern | How |
|---|---|---|
| No existing tests for shell scripts | N/A | Write a test script (`scripts/test-worktree-dev.sh`) that validates port derivation, override file generation, and symlink detection without actually starting Docker. |

## 6. Conflict Flags

| Area | Risk | Mitigation |
|---|---|---|
| `Makefile` | Adding new targets (`worktree-dev`, `worktree-dev-down`). Low risk of merge conflict since additions are appended to the end. | Append targets at the end of the worktree management section (after line 99). |
| `docker-compose.yml` | No modifications planned to this file. If another PR changes service definitions, the override file approach naturally adapts. | Keep the base file unchanged. |
| `docker-compose.dev.yml` | No modifications planned. The worktree override is a separate file. | Keep this file unchanged. |
| `scripts/worktree-create.sh` | Modification to add symlink detection/fix. If another PR modifies this script concurrently, merge conflicts possible around lines 155-175. | Keep the change minimal: add a check-and-fix block after `npm install`. |
| `scripts/worktree-remove.sh` | Addition of Docker teardown step. Low conflict risk since it's additive. | Add Docker cleanup before the `git worktree remove` call. |
| `.gitignore` | Adding `docker-compose.worktree-*.yml` pattern. Additive, low risk. | Append to the end of the file. |
| `backend/app/config.py` | No changes planned. CORS and FRONTEND_URL are already env-var configurable. | None needed. |
| `docs/development/setup.md` | Adding a worktree dev section. If docs are modified by another PR, low-risk merge conflict. | Add a new section rather than modifying existing content. |

## 7. Open Questions

1. **Port derivation formula for high issue numbers**: The proposed formula (e.g., frontend = `3000 + ISSUE`) breaks when ISSUE > 62535 (port > 65535). Should the script cap the issue number, use modular arithmetic (e.g., `3000 + (ISSUE % 1000)`), or simply validate and fail for out-of-range values?
   - **Recommendation**: Validate and fail with a clear message. Issue numbers above ~62000 are unlikely in practice, and modular arithmetic introduces collision risk. Keep it simple.

2. **Hot-reload vs production-like mode**: Should `make worktree-dev` use the dev compose file (with volume mounts and hot reload) or the production compose file? The issue description implies E2E testing, which may benefit from production-like builds.
   - **Recommendation**: Default to dev mode (volume mounts + hot reload) since agents need to iterate. Add a `MODE=prod` flag for production-like testing: `make worktree-dev ISSUE=144 MODE=prod`.

3. **Should `worktree-create.sh` be modified or should symlink handling be entirely in the new `worktree-dev.sh` script?** The issue proposes both updating `worktree-create.sh` AND having `worktree-dev.sh` handle symlinks.
   - **Recommendation**: Handle symlinks in `worktree-dev.sh` only, since that is the entry point for Docker environments. `worktree-create.sh` already runs `npm install` which creates a real `node_modules`. The symlink issue likely arises from a different source (e.g., git worktree sharing). Investigate root cause before modifying `worktree-create.sh`.

4. **Should `make worktree-dev-down` also run as part of `make worktree-remove`?** When a worktree is cleaned up, should the Docker stack be automatically torn down?
   - **Recommendation**: Yes. Add a Docker teardown step to `worktree-remove.sh` that checks if a stack is running and stops it. This prevents orphaned containers.

5. **Database migration handling**: When a worktree starts a fresh PostgreSQL instance, does the backend automatically create tables (via `init_db()` in `main.py` lifespan)? If migrations are needed, the worktree DB needs them applied.
   - **Recommendation**: The backend's `init_db()` already handles table creation on startup. No additional migration step should be needed. Verify this works with a clean database during testing.

6. **Override file location**: Should the generated `docker-compose.worktree-<N>.yml` live in the repo root or inside the worktree directory?
   - **Recommendation**: Inside the worktree directory (`.claude/worktrees/issue-<N>/docker-compose.worktree.yml`) since (a) it's specific to that worktree, (b) the worktree directory is already .gitignored, and (c) it avoids cluttering the repo root. However, Docker Compose must be run from the repo root for context paths to resolve correctly -- use `-f` with absolute paths.

7. **E2E test integration**: Should `make worktree-dev` automatically configure Playwright's `BASE_URL` and `API_URL` for the worktree's ports? The current `playwright.config.ts` reads from `BASE_URL` and `API_URL` env vars.
   - **Recommendation**: Yes. After starting the stack, the script should print export commands (or write a `.env.worktree` file) that sets `BASE_URL=http://localhost:3<ISSUE>` and `API_URL=http://localhost:8<ISSUE>`. Add a `make worktree-e2e ISSUE=<N>` target that starts the stack and runs Playwright with the correct env vars.

## 8. Done Conditions

- [ ] `scripts/worktree-dev.sh` exists and is executable
- [ ] `make worktree-dev ISSUE=<N>` starts an isolated Docker stack with unique ports derived from issue number
- [ ] Port derivation formula: frontend = `3000 + ISSUE`, backend = `8000 + ISSUE`, db = `5432 + ISSUE`; validated to be within 1024-65535 range
- [ ] A `docker-compose.worktree.yml` override is generated inside the worktree directory with correct port mappings, CORS_ORIGINS, FRONTEND_URL, and NEXT_PUBLIC_API_URL
- [ ] `COMPOSE_PROJECT_NAME` is set to a unique value per worktree (e.g., `openlearning-wt-<N>`)
- [ ] Named volumes are namespaced per worktree to prevent data conflicts
- [ ] Symlink detection: if `frontend/node_modules` is a symlink, it is removed and `npm install` is run
- [ ] Symlink detection: if `frontend/package-lock.json` is a symlink, it is replaced with a real copy
- [ ] Containers start with `--force-recreate -V` to avoid stale anonymous volumes
- [ ] Health checks: the script waits for all three services to be healthy before exiting
- [ ] Health check timeout: exits with error after 120s and dumps container logs
- [ ] The script prints accessible URLs after successful startup
- [ ] `make worktree-dev-down ISSUE=<N>` tears down the worktree Docker stack
- [ ] `scripts/worktree-remove.sh` stops the Docker stack (if running) before removing the worktree
- [ ] Two worktrees can run simultaneously without port conflicts (verified manually or via test script)
- [ ] Script validates Docker is running before proceeding
- [ ] Script validates the worktree directory exists before proceeding
- [ ] Script handles edge cases: ISSUE=0 rejected, ISSUE > 62535 rejected with clear message
- [ ] Generated override files are .gitignored (pattern: `docker-compose.worktree*.yml` or files live in .gitignored worktree dirs)
- [ ] No secrets are hardcoded in the generated override file
- [ ] CORS is configured as explicit `http://localhost:<port>`, not wildcard
- [ ] Documentation exists for the worktree dev workflow (port scheme, usage, teardown, E2E integration)
- [ ] `docs/development/setup.md` updated with a worktree dev section
- [ ] Existing `make docker-up`, `make docker-dev`, `make docker-down` targets are unchanged and still work
- [ ] Existing `scripts/worktree-create.sh` continues to work without regressions
- [ ] Test script validates port derivation logic and override file generation
- [ ] `make check` passes (no lint or build regressions in existing code)
