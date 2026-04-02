# Threat Model: Issue #152 -- Isolated Docker Environments for Parallel Claude Code Worktrees

**Date:** 2026-04-02
**Feature:** `scripts/worktree-dev.sh` + dynamic Docker Compose override generation
**Scope:** Shell scripts, Docker Compose overrides, CORS configuration, port binding, volume isolation
**Methodology:** STRIDE per component and data flow

---

## 1. Architecture Overview

### Components

| ID | Component | Trust Level | Description |
|----|-----------|-------------|-------------|
| C1 | `scripts/worktree-dev.sh` | Local user (developer/agent) | Generates Docker Compose override, starts isolated stack |
| C2 | Generated `docker-compose.worktree.yml` | Ephemeral artifact | Per-worktree override with port mappings, CORS, env vars |
| C3 | PostgreSQL container (per worktree) | Internal service (Docker network) | Isolated database with namespaced volume |
| C4 | Backend container (per worktree) | Internal service (Docker network) | FastAPI app with dynamic CORS origins and FRONTEND_URL |
| C5 | Frontend container (per worktree) | Internal service (Docker network) | Next.js app with dynamic NEXT_PUBLIC_API_URL |
| C6 | `scripts/worktree-remove.sh` | Local user | Extended to tear down Docker stacks |
| C7 | Makefile targets | Local user | Entry points: `worktree-dev`, `worktree-dev-down`, `worktree-e2e` |
| C8 | Host filesystem | Local user | Worktree directories, symlinked `.env` files, Docker socket |

### Data Flows

| Flow | From | To | Data | Transport |
|------|------|----|------|-----------|
| F1 | Developer/Agent | C1 (worktree-dev.sh) | Issue number (CLI argument) | Shell argument |
| F2 | C1 | C2 (override file) | Port mappings, CORS origins, env vars, DB credentials | File write to disk |
| F3 | C2 | C3/C4/C5 (Docker Compose) | Service configuration, environment variables | Docker engine API |
| F4 | Host `.env` files | C4 (backend container) | API keys (Anthropic, GitHub, JWT secret, encryption key) | Docker volume mount / env_file |
| F5 | Host browser | C5 (frontend) | HTTP requests | TCP (localhost:3000+N) |
| F6 | C5 (frontend) | C4 (backend) | API requests (CORS-gated) | HTTP (Docker internal network + localhost:8000+N) |
| F7 | C4 (backend) | C3 (database) | SQL queries | TCP (Docker internal network, port 5432) |
| F8 | Host network | C3 (database) | Direct DB connections | TCP (localhost:5432+N) |

---

## 2. Trust Boundaries

```
+-------------------------------------------------------------------+
|  DEVELOPER WORKSTATION (Trusted)                                  |
|                                                                   |
|  [Developer / Claude Agent]                                       |
|       |                                                           |
|       | F1: issue number (untrusted CLI input)                    |
|       v                                                           |
|  [worktree-dev.sh]-----F2---->[docker-compose.worktree.yml]      |
|       |                             |                             |
|  =====[Trust Boundary: Docker]=====|==============================|
|       |                            v                              |
|       |    +--[Docker Network: openlearning-wt-N]----------+      |
|       |    |                                               |      |
|       |    |   [Frontend :3000+N] <---F5--- Host Browser   |      |
|       |    |        |                                      |      |
|       |    |        | F6 (CORS-gated)                      |      |
|       |    |        v                                      |      |
|       |    |   [Backend :8000+N] <--- .env secrets (F4)    |      |
|       |    |        |                                      |      |
|       |    |        | F7 (SQL)                             |      |
|       |    |        v                                      |      |
|       |    |   [PostgreSQL :5432+N] <---F8--- Host Tools   |      |
|       |    |                                               |      |
|       |    +-----------------------------------------------+      |
|                                                                   |
+-------------------------------------------------------------------+
```

**Key boundaries:**
1. **Shell input boundary** -- Issue number enters the script from CLI args (F1). This is the primary injection surface.
2. **Docker engine boundary** -- The script interacts with Docker via `docker compose` commands. Generated YAML is parsed by Docker.
3. **Network boundary** -- Ports are exposed from containers to the host. Default Docker behavior binds to `0.0.0.0`, exposing services to the local network.
4. **Secret boundary** -- `.env` files are symlinked into worktrees and passed to containers via `env_file` directives.

---

## 3. STRIDE Analysis Matrix

### 3.1 Component-Level STRIDE

| Component | S (Spoofing) | T (Tampering) | R (Repudiation) | I (Info Disclosure) | D (Denial of Service) | E (Elevation of Privilege) |
|-----------|:-:|:-:|:-:|:-:|:-:|:-:|
| C1: worktree-dev.sh | LOW | **MEDIUM** | LOW | LOW | LOW | **MEDIUM** |
| C2: Generated override file | LOW | **MEDIUM** | LOW | **HIGH** | LOW | LOW |
| C3: PostgreSQL container | LOW | LOW | LOW | **MEDIUM** | LOW | LOW |
| C4: Backend container | LOW | LOW | LOW | **MEDIUM** | LOW | LOW |
| C5: Frontend container | LOW | LOW | LOW | LOW | LOW | LOW |
| C6: worktree-remove.sh | LOW | LOW | LOW | LOW | LOW | LOW |
| C7: Makefile targets | LOW | **MEDIUM** | LOW | LOW | LOW | **MEDIUM** |

### 3.2 Detailed Threat Analysis

#### T-01: Shell Injection via Issue Number Input
- **STRIDE category:** Tampering, Elevation of Privilege
- **Component:** C1 (worktree-dev.sh), C7 (Makefile)
- **Risk:** MEDIUM
- **CWE:** CWE-78 (OS Command Injection)
- **Description:** The issue number flows from `make worktree-dev ISSUE=<input>` through Make's variable expansion into `bash scripts/worktree-dev.sh $(ISSUE)`. If the input is not strictly validated as a positive integer before use in shell commands (e.g., `docker compose -p openlearning-wt-$ISSUE`), an attacker or malformed input could inject shell metacharacters.
- **Current mitigation in worktree-create.sh:** Line 65 validates with `^[0-9]+$` regex. This pattern MUST be replicated in `worktree-dev.sh`.
- **Residual risk:** Make's `$(ISSUE)` expansion happens before bash receives the argument. A value like `1; rm -rf /` would be split by Make. However, the Makefile passes `$(ISSUE)` unquoted, which means Make will perform word splitting. The `set -euo pipefail` + regex validation in the script itself is the true defense.

#### T-02: Secrets Leaking into Generated Override File
- **STRIDE category:** Information Disclosure
- **Component:** C2 (docker-compose.worktree.yml)
- **Risk:** HIGH
- **CWE:** CWE-312 (Cleartext Storage of Sensitive Information), CWE-540 (Inclusion of Sensitive Information in Source Code)
- **OWASP:** A02:2021 Cryptographic Failures
- **Description:** The generated override file must NOT embed actual secret values (API keys, JWT secrets, encryption keys, GitHub OAuth credentials). If the script writes `ANTHROPIC_API_KEY=sk-ant-...` into the YAML, that file could be accidentally committed, logged, or read by other processes. The override file should use `env_file` directives referencing the existing `.env` symlinks, or use `${VAR}` environment variable interpolation that Docker Compose resolves at runtime.
- **Current state:** The base `docker-compose.yml` already uses `env_file: - path: ./backend/.env` (line 22-24). The override file should NOT duplicate or override secret-bearing env vars.

#### T-03: Port Binding to 0.0.0.0 Exposes Services to LAN
- **STRIDE category:** Information Disclosure, Elevation of Privilege
- **Component:** C3, C4, C5 (all containers)
- **Risk:** MEDIUM
- **CWE:** CWE-668 (Exposure of Resource to Wrong Sphere)
- **OWASP:** A01:2021 Broken Access Control
- **Description:** The existing `docker-compose.yml` uses port mappings like `"8000:8000"` which Docker maps to `0.0.0.0:8000`, exposing services to all network interfaces. On a shared Wi-Fi network (coffee shop, coworking space), the database (with default credentials `openlearning/openlearning`), the backend API, and the frontend would all be accessible to any device on the same network. This risk is multiplied by this feature: each worktree adds 3 more exposed ports.
- **Note:** This is a pre-existing vulnerability in the base compose files, not introduced by this feature. However, the generated override file has the opportunity to improve this by binding to `127.0.0.1` explicitly.

#### T-04: CORS Wildcard or Overly Permissive Origins
- **STRIDE category:** Spoofing, Tampering
- **Component:** C4 (backend), C2 (override generation)
- **Risk:** MEDIUM
- **CWE:** CWE-942 (Permissive Cross-domain Policy)
- **OWASP:** A01:2021 Broken Access Control
- **Description:** The override file sets `CORS_ORIGINS` for the backend. If the generation logic accidentally produces `["*"]` or includes origins beyond the specific worktree's frontend port, it weakens CORS protection. The existing codebase correctly uses an explicit list (line 9 of `config.py`: `["http://localhost:3000"]`).
- **Specific concern:** If the script constructs the JSON array string incorrectly (e.g., fails to escape or quote properly), the backend's Pydantic parser for `cors_origins: list[str]` may either reject it (safe failure) or misparse it. The script must produce a valid JSON array with exactly the required localhost origin.

#### T-05: Docker Network Cross-Talk Between Worktrees
- **STRIDE category:** Information Disclosure, Tampering
- **Component:** C3, C4, C5 (containers across worktrees)
- **Risk:** LOW
- **CWE:** CWE-668 (Exposure of Resource to Wrong Sphere)
- **Description:** Docker Compose creates a default network per project (`openlearning-wt-144_default`, `openlearning-wt-145_default`). As long as `COMPOSE_PROJECT_NAME` is correctly namespaced, containers from different worktrees will be on different Docker networks and cannot directly communicate. If `COMPOSE_PROJECT_NAME` is not set or is identical across worktrees, containers would share a network and could access each other's databases.
- **Current mitigation:** The analysis specifies `COMPOSE_PROJECT_NAME=openlearning-wt-<N>` per AC-8. This is sufficient.

#### T-06: Database Exposed on Host with Default Credentials
- **STRIDE category:** Information Disclosure, Tampering, Spoofing
- **Component:** C3 (PostgreSQL)
- **Risk:** MEDIUM (compounded by T-03)
- **CWE:** CWE-798 (Use of Hard-coded Credentials), CWE-1188 (Initialization with Hard-coded Default)
- **OWASP:** A07:2021 Identification and Authentication Failures
- **Description:** Both `docker-compose.yml` (line 5-7) and `docker-compose.dev.yml` (line 5-6) use hardcoded credentials: `POSTGRES_USER=openlearning`, `POSTGRES_PASSWORD=openlearning`. When the database port is exposed to the host (and potentially the LAN per T-03), anyone who can reach the port can authenticate. This is a pre-existing condition, but this feature exposes additional PostgreSQL instances (one per worktree) on predictable ports (`5432+N`).
- **Note:** For a local dev environment, this is standard practice. The risk is LOW in isolation (single-user dev machine) but escalates to MEDIUM when combined with T-03 on shared networks.

#### T-07: Volume Mount Traversal / Host Filesystem Access
- **STRIDE category:** Information Disclosure, Tampering
- **Component:** C4, C5 (backend/frontend containers in dev mode)
- **Risk:** LOW
- **CWE:** CWE-22 (Path Traversal)
- **Description:** In dev mode (`docker-compose.dev.yml`), the backend mounts `./backend:/app` and the frontend mounts `./frontend:/app`. The generated override must not expand mount paths to include parent directories or the host root. Since the override file is generated by the script (not user-supplied YAML), and paths are derived from known directory structures, the risk is low. However, if the worktree path contains special characters, the volume mount path in the generated YAML could break or be misinterpreted.
- **Mitigation:** The worktree directory naming convention (`issue-<N>` where N is a validated integer) prevents special characters in paths.

#### T-08: Stale Override File Contains Outdated Configuration
- **STRIDE category:** Tampering, Information Disclosure
- **Component:** C2 (generated override)
- **Risk:** LOW
- **Description:** If a developer changes the issue number or the override file is not regenerated, stale configuration could cause CORS mismatches (benign failure) or point to a wrong database volume (data leakage between worktrees). The analysis states the file is generated fresh each time (AC-6, idempotent).

#### T-09: Make Variable Expansion Without Quoting
- **STRIDE category:** Tampering, Elevation of Privilege
- **Component:** C7 (Makefile)
- **Risk:** MEDIUM
- **CWE:** CWE-78 (OS Command Injection)
- **Description:** The existing Makefile pattern (lines 92-96) passes `$(ISSUE)` directly to bash scripts without quoting: `@bash scripts/worktree-create.sh $(ISSUE)`. If `ISSUE` contains spaces or shell metacharacters, Make will perform word splitting before bash sees the argument. While the script validates the argument, the split could cause the script to receive unexpected positional parameters.
- **Example:** `make worktree-dev ISSUE="1 --help"` would pass two arguments to the script. The `^[0-9]+$` regex check on `$1` would catch `"1"` as valid but the second argument could influence script behavior if positional argument parsing is not strict.

#### T-10: Docker Socket Access Implies Root-Equivalent Privileges
- **STRIDE category:** Elevation of Privilege
- **Component:** C1 (worktree-dev.sh)
- **Risk:** LOW (accepted risk for Docker-based development)
- **CWE:** CWE-250 (Execution with Unnecessary Privileges)
- **Description:** Any process that can execute `docker` commands effectively has root-equivalent access to the host (can mount any filesystem, run privileged containers, etc.). This is inherent to Docker Desktop usage and is not introduced by this feature. The script does not require or request elevated privileges beyond what Docker already provides.

#### T-11: Symlink Replacement Race Condition
- **STRIDE category:** Tampering
- **Component:** C1 (worktree-dev.sh symlink handling)
- **Risk:** LOW
- **CWE:** CWE-367 (TOCTOU Race Condition)
- **Description:** The script checks if `frontend/node_modules` is a symlink, removes it, then runs `npm install`. Between the check and the replacement, another process could recreate the symlink. In practice, this is extremely unlikely on a single-user dev machine, but the script should use atomic operations where possible (e.g., `rm -f` followed by `npm install` rather than check-then-act).

---

## 4. Attack Surface Inventory

### Entry Points

| ID | Entry Point | Type | Auth Required | Exposed To | Risk Level |
|----|-------------|------|---------------|------------|------------|
| EP-1 | `make worktree-dev ISSUE=<input>` | CLI (Make target) | Local user | Local machine | MEDIUM |
| EP-2 | `make worktree-dev-down ISSUE=<input>` | CLI (Make target) | Local user | Local machine | LOW |
| EP-3 | `make worktree-e2e ISSUE=<input>` | CLI (Make target) | Local user | Local machine | LOW |
| EP-4 | `localhost:3000+N` (frontend) | HTTP | None | Host + LAN (if 0.0.0.0) | MEDIUM |
| EP-5 | `localhost:8000+N` (backend API) | HTTP | JWT cookie | Host + LAN (if 0.0.0.0) | MEDIUM |
| EP-6 | `localhost:5432+N` (PostgreSQL) | TCP | DB credentials | Host + LAN (if 0.0.0.0) | MEDIUM |
| EP-7 | Generated override YAML file | File on disk | Filesystem permissions | Local processes | LOW |

### Data at Rest

| Data | Location | Sensitivity | Protection |
|------|----------|-------------|------------|
| Database contents | Docker named volume (`openlearning-wt-N_postgres-data`) | User data, assessment results | Docker volume isolation, default DB credentials |
| `.env` files | Symlinked from main repo into worktree | API keys, JWT secret, encryption key, OAuth secrets | Filesystem permissions, .gitignored |
| Generated override YAML | Worktree directory (`.claude/worktrees/issue-N/`) | Port mappings, CORS origins (no secrets if done correctly) | .gitignored (worktree dir is gitignored) |

### Data in Transit

| Data | Path | Sensitivity | Protection |
|------|------|-------------|------------|
| API requests | Browser -> Frontend -> Backend | User input, auth tokens | HTTP only (localhost), CORS |
| Database queries | Backend -> PostgreSQL | SQL queries, user data | Docker network (unencrypted but isolated) |
| OAuth flow | Backend -> GitHub API | OAuth code, access token | HTTPS (external), HTTP (localhost redirect) |

---

## 5. Security Requirements

### CRITICAL (Block architecture approval)

*None identified.* This feature operates entirely within the local development environment and does not introduce new production attack surfaces. All identified threats are MEDIUM or below.

### HIGH Priority

| ID | Threat | Requirement | Mitigation | Implementation Note | Validation |
|----|--------|-------------|------------|---------------------|------------|
| SR-01 | T-02 | Generated override file MUST NOT contain plaintext secrets | Use `env_file` directives or `${VAR}` interpolation for all sensitive values. Only set non-secret overrides (ports, CORS_ORIGINS, FRONTEND_URL, COMPOSE_PROJECT_NAME, NEXT_PUBLIC_API_URL) as literal values in the generated YAML. | Grep the generated file template in `worktree-dev.sh` for any reference to `API_KEY`, `SECRET`, `PASSWORD`, `TOKEN`, `ENCRYPTION`. The override should only contain: port mappings, CORS origins (localhost URLs), frontend URL, database URL (with the well-known dev credentials that are already in the base compose file), and project name. | Automated: `grep -iE '(api_key|secret|token|encryption)' docker-compose.worktree.yml` must return zero matches (excluding CORS/URL values). Manual: Review generated file after first implementation. |
| SR-02 | T-01, T-09 | Issue number input MUST be validated as a positive integer before any use in shell commands | Validate `$1` with regex `^[1-9][0-9]*$`. Reject with clear error on failure. No upper bound needed — preferred ports (base + N) are tried first; if unavailable or overflowing 65535, the script auto-finds free ports via `lsof`. Must happen BEFORE any use in variable expansion, docker commands, or file paths. | Replicate the validation pattern from `worktree-create.sh` line 65 (`^[0-9]+$`) but strengthen it: (a) reject `0`, (b) reject leading zeros to avoid octal interpretation. | Test: Verify script exits with error for inputs `0`, `-1`, `abc`, `1; rm`, `1$(whoami)`, empty string. Verify large numbers like `99999` succeed with clamped fallback ports. |
| SR-03 | T-04 | CORS_ORIGINS MUST be set to an explicit `http://localhost:<port>` value, never `*` | The script must produce `CORS_ORIGINS: '["http://localhost:<3000+N>"]'` with the exact computed port. No wildcard. No additional origins unless the base compose file's default origin is also needed. | Use a string template: `CORS_ORIGINS: '["http://localhost:${FRONTEND_PORT}"]'` where `FRONTEND_PORT` is arithmetically derived. | Automated: Parse the generated YAML and assert `CORS_ORIGINS` does not contain `*`. Manual: Inspect generated file. |

### MEDIUM Priority

| ID | Threat | Requirement | Mitigation | Implementation Note | Validation |
|----|--------|-------------|------------|---------------------|------------|
| SR-04 | T-03, T-06 | Generated override file SHOULD bind ports to `127.0.0.1` only | Use `"127.0.0.1:<host-port>:<container-port>"` format in the override file's port mappings. This prevents exposure to LAN. | This improves on the existing base compose files, which use the less-secure `"<port>:<port>"` format. The override file is the right place to tighten this since it only affects dev worktrees. | Test: Verify generated YAML port entries start with `127.0.0.1:`. Integration: Run `docker compose config` and confirm port bindings. |
| SR-05 | T-05 | COMPOSE_PROJECT_NAME MUST be unique per worktree and deterministically derived from issue number | Set `COMPOSE_PROJECT_NAME=openlearning-wt-<N>` in the override file or via `-p` flag. The project name must not collide with the main repo stack (which uses the default directory-name-based project name). | Use environment variable or `-p` flag: `docker compose -p "openlearning-wt-${ISSUE}" ...`. Ensure the project name only contains alphanumeric characters and hyphens. | Test: Start two worktree stacks and verify `docker ps` shows containers with different project prefixes. Verify `docker network ls` shows separate networks. |
| SR-06 | T-07 | Generated YAML volume mount paths MUST use the validated worktree directory path | Construct volume mount paths using the validated `WORKTREE_DIR` variable. Never interpolate unsanitized input into volume mount paths. | Since `WORKTREE_DIR` is constructed from `WORKTREE_BASE/issue-$ISSUE_NUM` where `ISSUE_NUM` is validated as a positive integer, the path is safe. Verify no additional user input flows into volume paths. | Code review: Trace all volume mount values in the generation template back to validated variables. |
| SR-07 | T-08 | Override file MUST be regenerated on every invocation (no stale reuse) | The script should overwrite any existing override file unconditionally. Use `--force-recreate -V` to ensure Docker does not reuse stale state. | Write the override file with `>` (truncate) not `>>` (append). The `--force-recreate -V` flags are already specified in the analysis (AC-6). | Test: Modify the override file manually, run `make worktree-dev`, verify the modification is gone. |

### LOW Priority

| ID | Threat | Requirement | Mitigation | Implementation Note | Validation |
|----|--------|-------------|------------|---------------------|------------|
| SR-08 | T-10 | Document that Docker access implies elevated host privileges | Add a note to the worktree dev documentation that Docker-based development requires Docker Desktop and that Docker containers have broad host access. | Documentation only. No code change needed. | Review docs. |
| SR-09 | T-11 | Symlink removal should be non-racy | Use `rm -f` (unconditional remove) followed by `npm install` rather than check-then-act. If the file is not a symlink, `rm -f` on a directory will fail harmlessly (use `rm -rf` for `node_modules` directory). | Replace `if [ -L node_modules ]; then rm node_modules; fi` with `[ -L frontend/node_modules ] && rm frontend/node_modules; npm install` in a single conditional chain. | Code review. |
| SR-10 | T-09 | Makefile should quote the ISSUE variable | Change Makefile targets from `@bash scripts/worktree-dev.sh $(ISSUE)` to `@bash scripts/worktree-dev.sh "$(ISSUE)"`. While the script validates input, defense in depth means preventing word splitting at the Make level too. | This should also be applied to the existing `worktree-create` and `worktree-remove` targets for consistency. | Test: Verify `make worktree-dev ISSUE="1 --help"` is passed as a single argument and rejected by the script. |
| SR-11 | General | Generated override file location MUST be within the gitignored worktree directory | Place the file at `.claude/worktrees/issue-<N>/docker-compose.worktree.yml`. Since `.claude/worktrees/` is already in `.gitignore` (line 66), this prevents accidental commit. | Use absolute paths with `-f` flags when invoking Docker Compose to handle the working directory correctly. | Test: Run `git status` after generating the file and verify it does not appear as untracked. |

---

## 6. Existing Security Patterns to Reuse

### Input Validation
- **`worktree-create.sh` line 65:** Validates issue number with `^[0-9]+$` regex. Reuse this pattern but strengthen with lower/upper bound checks.
- **`worktree-create.sh` line 4:** Uses `set -euo pipefail` for strict bash error handling. Must replicate in `worktree-dev.sh`.

### CORS Configuration
- **`backend/app/config.py` line 9:** `cors_origins: list[str]` is populated from the `CORS_ORIGINS` environment variable via pydantic-settings. Accepts a JSON array string. The override file should set this as `'["http://localhost:<port>"]'`.
- **`backend/app/main.py` lines 65-71:** CORS middleware uses `settings.cors_origins` directly. No wildcard fallback exists -- if `CORS_ORIGINS` is malformed, pydantic-settings will raise a validation error and the app will fail to start (safe failure mode).

### Secret Management
- **`.env` symlinks:** `worktree-create.sh` lines 158-161 symlink `.env` files from the main repo. The override file should use `env_file` to load these, not duplicate their contents.
- **`.gitignore` line 66:** `.claude/worktrees/` is gitignored, covering any generated files within worktree directories.

### Authentication
- **JWT via cookies:** `backend/app/deps.py` handles JWT cookie auth. Cookie flags (`httponly=True, samesite=lax, secure=<https-dependent>`) are set in `backend/app/services/auth_service.py` lines 88-94. For `http://localhost:*`, `secure` will be `False`, which is correct for local dev.
- **`frontend_url` setting:** `backend/app/config.py` line 19 defaults to `http://localhost:3000`. The override file sets `FRONTEND_URL` to the worktree-specific port, which flows into OAuth redirect URLs and cookie domain logic.

### Docker Patterns
- **Health checks:** Defined in `docker-compose.yml` lines 13-17 (db), 30-40 (backend). The override file should NOT redefine health checks -- they should be inherited from the base file.
- **`env_file` directive:** `docker-compose.yml` lines 22-24 use `env_file` with `required: false`. The override file should preserve this pattern.

### Port Convention
- **Base ports:** Frontend=3000, Backend=8000, DB=5432 (in `docker-compose.dev.yml`). The derivation `base + ISSUE_NUM` is used as the preferred port. If the preferred port exceeds 65535, it clamps to a safe fallback range. If any preferred port is already in use, the script auto-finds the next free port via `lsof`.

---

## 7. Recommendations Summary

| Priority | Action | Blocks Implementation? |
|----------|--------|----------------------|
| HIGH | Validate issue number as positive integer before any shell use (SR-02) | Yes |
| HIGH | Never embed secrets in generated override YAML (SR-01) | Yes |
| HIGH | CORS must be explicit localhost origin, never wildcard (SR-03) | Yes |
| MEDIUM | Bind ports to 127.0.0.1 in override file (SR-04) | No, but strongly recommended |
| MEDIUM | Namespace COMPOSE_PROJECT_NAME per worktree (SR-05) | Yes (functional requirement) |
| MEDIUM | Validate volume mount paths use only sanitized variables (SR-06) | No |
| MEDIUM | Always overwrite override file, never append (SR-07) | No |
| LOW | Document Docker privilege implications (SR-08) | No |
| LOW | Non-racy symlink removal (SR-09) | No |
| LOW | Quote ISSUE variable in Makefile targets (SR-10) | No |
| LOW | Ensure override file is within gitignored directory (SR-11) | No |

---

## 8. Out of Scope

The following are pre-existing conditions not introduced by this feature and are therefore noted but not actionable within this issue:

1. **Hardcoded database credentials** in `docker-compose.yml` and `docker-compose.dev.yml` (`openlearning/openlearning`). Standard for local dev but would be a vulnerability if these compose files were used in non-local environments.
2. **No CSP headers** on the backend. The FastAPI app does not set Content-Security-Policy, X-Frame-Options, or X-Content-Type-Options headers.
3. **No rate limiting** on auth endpoints in development mode. The `slowapi` references in the codebase appear to be in tests/documentation only.
4. **All base compose ports bind to 0.0.0.0.** The override file can fix this for worktree stacks (SR-04), but the base compose files remain exposed. Consider a separate issue for that.
