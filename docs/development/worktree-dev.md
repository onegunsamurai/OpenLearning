# Worktree Docker Environments

Run isolated Docker dev environments for parallel development across git worktrees.
Each worktree gets unique ports derived from the issue number, preventing conflicts.

## Quick Start

```bash
# Create a worktree (if you haven't already)
make worktree-create ISSUE=144

# Start an isolated Docker environment
make worktree-dev ISSUE=144

# Or, from inside the worktree directory (auto-detects issue number)
cd .claude/worktrees/issue-144
make worktree-dev
```

## Port Scheme

Ports are deterministically derived from the issue number:

| Service  | Formula      | Example (ISSUE=144) |
|----------|-------------|---------------------|
| Frontend | 3000 + N    | 3144                |
| Backend  | 8000 + N    | 8144                |
| Database | 5432 + N    | 5576                |

Maximum supported issue number: **57535** (backend port would exceed 65535).

All ports bind to `127.0.0.1` (localhost only) for security.

## Commands

### Start environment

```bash
make worktree-dev ISSUE=<N>              # dev mode (default, hot-reload)
make worktree-dev ISSUE=<N> MODE=prod    # production-like build
```

### Stop environment

```bash
make worktree-dev-down ISSUE=<N>                  # stop, keep database
make worktree-dev-down ISSUE=<N> VOLUMES=yes      # stop and wipe database
```

### Run E2E tests

```bash
make worktree-e2e ISSUE=<N>
```

This starts the Docker stack (if not running), sets `BASE_URL` and `API_URL`
for Playwright, and runs the E2E test suite.

### View logs

```bash
docker compose -p openlearning-wt-<N> logs -f
docker compose -p openlearning-wt-<N> logs backend
```

### List worktrees with Docker status

```bash
make worktree-list
```

Shows an "up" or "down" Docker column for each worktree.

## How It Works

1. **Port derivation** — Unique ports from issue number, validated within 1024-65535
2. **Override file** — Generates `docker-compose.worktree.yml` inside the worktree dir
3. **Compose layering** — `docker-compose.yml` + `docker-compose.dev.yml` + worktree override
4. **Project isolation** — `COMPOSE_PROJECT_NAME=openlearning-wt-<N>` separates containers, networks, and volumes
5. **Symlink cleanup** — Fixes `node_modules` and `package-lock.json` symlinks before Docker start
6. **Health checks** — Waits up to 120s for all services to be healthy
7. **Cleanup integration** — `make worktree-remove` auto-stops Docker stacks

## Running Two Worktrees Simultaneously

```bash
# Terminal 1
make worktree-dev ISSUE=144
# Frontend: http://localhost:3144, Backend: http://localhost:8144

# Terminal 2
make worktree-dev ISSUE=145
# Frontend: http://localhost:3145, Backend: http://localhost:8145
```

Each stack has its own database, containers, and network. No conflicts.

## Troubleshooting

### Port already in use

```
Error: Docker Compose failed to start. Check if ports are already in use:
  lsof -i :3144
```

Another process is using the derived port. Stop it or use a different issue number.

### Docker not running

```
Error: Docker is not running. Start Docker Desktop and try again.
```

### Health check timeout

```
Error: Health checks did not pass within 120 seconds.
```

Container logs are dumped automatically. Common causes:
- Missing environment variables (check `.env` files)
- Database migration issues (check backend logs)
- Build failures (check the Docker build output above)

### Missing .env files

```
⚠ backend/.env not found in worktree.
```

Run `bash scripts/worktree-create.sh <N>` to set up symlinks, or manually copy
`.env` files from the repo root.

## Technical Details

- **Generated file**: `.claude/worktrees/issue-<N>/docker-compose.worktree.yml` (gitignored)
- **Project name**: `openlearning-wt-<N>`
- **Docker Compose V2** required (shipped with Docker Desktop)
- **Resource usage**: ~1GB RAM per stack. Aim for no more than ~10 simultaneous stacks.
- **CORS**: Automatically configured to `http://localhost:<frontend-port>`
- **Database**: Fresh PostgreSQL per worktree. Tables created by `init_db()` on backend startup.
