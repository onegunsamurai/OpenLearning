#!/usr/bin/env bash
# worktree-dev.sh — Start an isolated Docker dev environment for a git worktree.
# Usage: bash scripts/worktree-dev.sh <issue-number> [--mode=dev|prod]
#        bash scripts/worktree-dev.sh --down <issue-number> [--volumes]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# If running from inside a worktree, resolve to the main repo root
if [[ "$REPO_ROOT" == */.claude/worktrees/* ]]; then
  REPO_ROOT="${REPO_ROOT%%/.claude/worktrees/*}"
fi

WORKTREE_BASE="$REPO_ROOT/.claude/worktrees"
HEALTH_TIMEOUT=120

# ── Helpers ──────────────────────────────────────────────────────────────────

usage() {
  cat <<'EOF'
Usage:
  worktree-dev.sh <issue-number> [--mode=dev|prod]     Start environment
  worktree-dev.sh --down <issue-number> [--volumes]    Stop environment
  worktree-dev.sh --help                               Show this help

Arguments:
  issue-number   GitHub issue number (positive integer)
  --mode         dev (default): hot-reload with volume mounts
                 prod: production-like build
  --down         Tear down the Docker stack
  --volumes      Also remove named volumes (database data) when tearing down

If ISSUE is omitted, it is auto-detected from the current directory name
(must match .claude/worktrees/issue-<N>).
EOF
  exit 0
}

log() { echo "  $*"; }
warn() { echo "  ⚠ $*" >&2; }
err() { echo "Error: $*" >&2; }

# ── Pure functions (tested in test-worktree-dev.sh) ──────────────────────────

validate_issue_number() {
  local input="$1"

  # Must be a positive integer starting with 1-9
  if ! [[ "$input" =~ ^[1-9][0-9]*$ ]]; then
    err "Issue number must be a positive integer (got '$input')."
    return 1
  fi

  return 0
}

is_port_free() {
  local port="$1"
  # lsof returns 0 if something is listening, 1 if nothing is
  ! lsof -i :"$port" >/dev/null 2>&1
}

find_free_port() {
  local start="$1"
  local port
  for port in $(seq "$start" 65535); do
    if is_port_free "$port"; then
      echo "$port"
      return 0
    fi
  done
  err "No free port found starting from $start"
  return 1
}

derive_ports() {
  local issue_num="$1"

  # Preferred ports based on issue number
  local pref_frontend=$((3000 + issue_num))
  local pref_backend=$((8000 + issue_num))
  local pref_db=$((5432 + issue_num))

  # Clamp preferred ports to valid range (1024-65535)
  [ "$pref_frontend" -gt 65535 ] && pref_frontend=10000
  [ "$pref_backend" -gt 65535 ] && pref_backend=20000
  [ "$pref_db" -gt 65535 ] && pref_db=30000

  # Use preferred port if free, otherwise find the next free one
  if is_port_free "$pref_frontend"; then
    FRONTEND_PORT=$pref_frontend
  else
    warn "Preferred frontend port $pref_frontend is in use, finding alternative..."
    FRONTEND_PORT=$(find_free_port "$pref_frontend") || return 1
  fi

  if is_port_free "$pref_backend"; then
    BACKEND_PORT=$pref_backend
  else
    warn "Preferred backend port $pref_backend is in use, finding alternative..."
    BACKEND_PORT=$(find_free_port "$pref_backend") || return 1
  fi

  if is_port_free "$pref_db"; then
    DB_PORT=$pref_db
  else
    warn "Preferred DB port $pref_db is in use, finding alternative..."
    DB_PORT=$(find_free_port "$pref_db") || return 1
  fi
}

detect_issue_from_dir() {
  local dir="$1"
  local base
  base=$(basename "$dir")
  if [[ "$base" =~ ^issue-([0-9]+)$ ]]; then
    echo "${BASH_REMATCH[1]}"
  fi
}

check_prerequisites() {
  local issue_num="$1"
  local worktree_dir="$2"

  # Docker daemon running
  if ! docker info >/dev/null 2>&1; then
    err "Docker is not running. Start Docker Desktop and try again."
    return 1
  fi

  # Worktree directory exists
  if [ ! -d "$worktree_dir" ]; then
    err "Worktree for issue-$issue_num not found at $worktree_dir"
    err "  Run: make worktree-create ISSUE=$issue_num"
    return 1
  fi

  # .env files (non-fatal warnings)
  if [ ! -f "$worktree_dir/backend/.env" ]; then
    warn "backend/.env not found in worktree. Backend may fail to start."
    warn "  Run: bash scripts/worktree-create.sh $issue_num"
  fi
  if [ ! -f "$worktree_dir/frontend/.env.local" ]; then
    warn "frontend/.env.local not found in worktree. Frontend may use defaults."
  fi

  return 0
}

handle_symlinks() {
  local worktree_dir="$1"
  local skip_npm="${2:-false}"
  local frontend_dir="$worktree_dir/frontend"
  local need_npm_install="false"

  # node_modules: remove if symlink
  if [ -L "$frontend_dir/node_modules" ]; then
    log "Removing symlinked node_modules..."
    rm "$frontend_dir/node_modules"
    need_npm_install="true"
  fi

  # node_modules: run npm install if missing
  if [ ! -d "$frontend_dir/node_modules" ]; then
    need_npm_install="true"
  fi

  # package-lock.json: replace symlink with real copy
  if [ -L "$frontend_dir/package-lock.json" ]; then
    log "Replacing symlinked package-lock.json with real copy..."
    local target
    target=$(readlink "$frontend_dir/package-lock.json")
    # Resolve relative targets
    if [[ "$target" != /* ]]; then
      target="$frontend_dir/$target"
    fi
    rm "$frontend_dir/package-lock.json"
    cp "$target" "$frontend_dir/package-lock.json"
  fi

  # Run npm install if needed (skip during testing)
  if [ "$need_npm_install" = "true" ] && [ "$skip_npm" != "true" ]; then
    log "Running npm install in worktree frontend..."
    (cd "$frontend_dir" && npm install --silent 2>&1) || {
      warn "npm install failed — Docker build may still succeed with its own install."
    }
  fi

  return 0
}

generate_override_yaml() {
  local issue_num="$1"
  local frontend_port="$2"
  local backend_port="$3"
  local db_port="$4"
  local worktree_dir="$5"
  local mode="$6"
  local output_file="$worktree_dir/docker-compose.worktree.yml"

  # Shared YAML header and port/env config
  local backend_volumes="" frontend_volumes=""
  if [ "$mode" = "dev" ]; then
    backend_volumes="
    volumes:
      - ${worktree_dir}/backend:/app"
    frontend_volumes="
    volumes:
      - ${worktree_dir}/frontend:/app
      - /app/node_modules"
  fi

  # Truncate and write (SR-07: never append)
  # !reset overrides inherited ports from base compose files instead of appending
  cat > "$output_file" <<YAML
# AUTO-GENERATED by scripts/worktree-dev.sh — do not edit
# Worktree: issue-${issue_num} | Ports: frontend=${frontend_port} backend=${backend_port} db=${db_port}
services:
  db:
    ports: !override
      - "127.0.0.1:${db_port}:5432"

  backend:
    ports: !override
      - "127.0.0.1:${backend_port}:8000"
    environment:
      CORS_ORIGINS: '["http://localhost:${frontend_port}"]'
      FRONTEND_URL: "http://localhost:${frontend_port}"${backend_volumes}

  frontend:
    ports: !override
      - "127.0.0.1:${frontend_port}:3000"
    environment:
      NEXT_PUBLIC_API_URL: "http://localhost:${backend_port}"${frontend_volumes}
YAML
}

# ── Compose command builder ──────────────────────────────────────────────────

build_compose_cmd() {
  local issue_num="$1"
  local worktree_dir="$2"
  local mode="$3"
  local project_name="openlearning-wt-${issue_num}"

  COMPOSE_CMD=(docker compose)

  # Use worktree as project directory so relative paths resolve there
  COMPOSE_CMD+=(--project-directory "$worktree_dir")

  # Layer compose files
  COMPOSE_CMD+=(-f "$REPO_ROOT/docker-compose.yml")

  if [ "$mode" = "dev" ]; then
    COMPOSE_CMD+=(-f "$REPO_ROOT/docker-compose.dev.yml")
  fi

  COMPOSE_CMD+=(-f "$worktree_dir/docker-compose.worktree.yml")
  COMPOSE_CMD+=(-p "$project_name")
}

# ── Health check ─────────────────────────────────────────────────────────────

wait_for_healthy() {
  local issue_num="$1"
  local frontend_port="$2"
  local backend_port="$3"
  local project_name="openlearning-wt-${issue_num}"

  log "Waiting for services to become healthy (timeout: ${HEALTH_TIMEOUT}s)..."

  local elapsed=0
  local interval=5
  local db_ok=false
  local backend_ok=false
  local frontend_ok=false

  while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
    # Check database via Docker container health
    if [ "$db_ok" != "true" ]; then
      if docker compose -p "$project_name" ps --format json 2>/dev/null \
          | grep -F '"Service":"db"' | grep -qF '"Health":"healthy"'; then
        db_ok=true
        log "Database: healthy"
      fi
    fi

    # Check backend via HTTP
    if [ "$backend_ok" != "true" ]; then
      if curl -sf "http://localhost:${backend_port}/api/health" >/dev/null 2>&1; then
        backend_ok=true
        log "Backend: healthy"
      fi
    fi

    # Check frontend via HTTP
    if [ "$frontend_ok" != "true" ]; then
      if curl -sf "http://localhost:${frontend_port}" >/dev/null 2>&1; then
        frontend_ok=true
        log "Frontend: healthy"
      fi
    fi

    if [ "$db_ok" = "true" ] && [ "$backend_ok" = "true" ] && [ "$frontend_ok" = "true" ]; then
      return 0
    fi

    sleep "$interval"
    elapsed=$((elapsed + interval))
  done

  # Timeout — dump logs for debugging
  err "Health checks did not pass within ${HEALTH_TIMEOUT} seconds."
  err "Dumping container logs for debugging..."
  echo "" >&2
  for svc in db backend frontend; do
    echo "--- $svc logs ---" >&2
    docker compose -p "$project_name" logs --tail=30 "$svc" 2>&1 >&2 || true
    echo "" >&2
  done
  return 1
}

# ── Main flows ───────────────────────────────────────────────────────────────

do_up() {
  local issue_num="$1"
  local mode="$2"
  local worktree_dir="$WORKTREE_BASE/issue-$issue_num"

  echo "Worktree dev environment starting (issue #$issue_num, mode: $mode)..."
  echo ""

  # Validate
  check_prerequisites "$issue_num" "$worktree_dir" || exit 1

  # Derive ports
  derive_ports "$issue_num"
  log "Ports: frontend=$FRONTEND_PORT, backend=$BACKEND_PORT, db=$DB_PORT"

  # Handle symlinks
  handle_symlinks "$worktree_dir"

  # Generate override
  generate_override_yaml "$issue_num" "$FRONTEND_PORT" "$BACKEND_PORT" "$DB_PORT" "$worktree_dir" "$mode"
  log "Generated docker-compose.worktree.yml"

  # Build compose command
  build_compose_cmd "$issue_num" "$worktree_dir" "$mode"

  # Start
  log "Starting Docker stack (openlearning-wt-$issue_num)..."
  echo ""
  if ! "${COMPOSE_CMD[@]}" up -d --build --force-recreate -V 2>&1; then
    err "Docker Compose failed to start. Check if ports are already in use:"
    err "  lsof -i :$FRONTEND_PORT"
    err "  lsof -i :$BACKEND_PORT"
    err "  lsof -i :$DB_PORT"
    exit 3
  fi
  echo ""

  # Health checks
  if ! wait_for_healthy "$issue_num" "$FRONTEND_PORT" "$BACKEND_PORT"; then
    exit 2
  fi

  # Success summary
  echo ""
  echo "─────────────────────────────────────────────────"
  echo "WORKTREE DEV ENVIRONMENT READY"
  echo ""
  echo "  Frontend:  http://localhost:$FRONTEND_PORT"
  echo "  Backend:   http://localhost:$BACKEND_PORT"
  echo "  Database:  localhost:$DB_PORT"
  echo ""
  echo "  Project:   openlearning-wt-$issue_num"
  echo ""
  echo "Useful commands:"
  echo "  docker compose -p openlearning-wt-$issue_num logs -f"
  echo "  make worktree-dev-down ISSUE=$issue_num"
  echo "  make worktree-e2e ISSUE=$issue_num"
  echo "─────────────────────────────────────────────────"
}

do_down() {
  local issue_num="$1"
  local remove_volumes="$2"
  local project_name="openlearning-wt-${issue_num}"

  # Check if stack is running
  if ! docker compose -p "$project_name" ps --quiet 2>/dev/null | grep -q .; then
    echo "No running stack for issue-$issue_num."
    exit 0
  fi

  echo "Stopping Docker stack for issue-$issue_num..."

  local down_args=(down --timeout 10)
  if [ "$remove_volumes" = "yes" ]; then
    down_args+=(-v)
    echo "  (also removing volumes)"
  fi

  docker compose -p "$project_name" "${down_args[@]}" 2>&1

  echo "  ✓ Stack stopped."
}

# ── Argument parsing ─────────────────────────────────────────────────────────

main() {
  local action="up"
  local issue_num=""
  local mode="dev"
  local remove_volumes="no"

  for arg in "$@"; do
    case "$arg" in
      --help|-h) usage ;;
      --down) action="down" ;;
      --volumes) remove_volumes="yes" ;;
      --mode=*) mode="${arg#--mode=}" ;;
      --source-only) return 0 ;;  # Used by test script to source functions only
      *)
        if [[ "$arg" =~ ^[0-9]+$ ]]; then
          issue_num="$arg"
        else
          err "Unknown argument: $arg"
          usage
        fi
        ;;
    esac
  done

  # Auto-detect issue from pwd if not provided
  if [ -z "$issue_num" ]; then
    issue_num=$(detect_issue_from_dir "$(pwd)")
    if [ -z "$issue_num" ]; then
      err "No issue number provided and could not auto-detect from current directory."
      err "  Run from inside a worktree, or provide ISSUE number: make worktree-dev ISSUE=<N>"
      exit 1
    fi
    log "Auto-detected issue #$issue_num from current directory"
  fi

  # Validate
  validate_issue_number "$issue_num" || exit 1

  # Validate mode
  if [ "$mode" != "dev" ] && [ "$mode" != "prod" ]; then
    err "Invalid mode '$mode'. Must be 'dev' or 'prod'."
    exit 1
  fi

  # Dispatch
  case "$action" in
    up) do_up "$issue_num" "$mode" ;;
    down) do_down "$issue_num" "$remove_volumes" ;;
  esac
}

# Only run main when executed directly, not when sourced
if [[ "${1:-}" != "--source-only" ]] && [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
