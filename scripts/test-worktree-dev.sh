#!/usr/bin/env bash
# test-worktree-dev.sh — Unit tests for worktree-dev.sh functions.
# Usage: bash scripts/test-worktree-dev.sh
#        INTEGRATION=1 bash scripts/test-worktree-dev.sh  # include Docker tests
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source the script under test (functions only, main is guarded)
source "$SCRIPT_DIR/worktree-dev.sh" --source-only

# ── TAP-like test framework ─────────────────────────────────────────────────

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
CURRENT_TEST=""

begin_test() {
  CURRENT_TEST="$1"
  TESTS_RUN=$((TESTS_RUN + 1))
}

pass() {
  TESTS_PASSED=$((TESTS_PASSED + 1))
  echo "  ✓ $CURRENT_TEST"
}

fail() {
  TESTS_FAILED=$((TESTS_FAILED + 1))
  echo "  ✗ $CURRENT_TEST — $1" >&2
}

assert_eq() {
  local expected="$1"
  local actual="$2"
  local msg="${3:-expected '$expected', got '$actual'}"
  if [ "$expected" = "$actual" ]; then
    pass
  else
    fail "$msg"
  fi
}

assert_contains() {
  local haystack="$1"
  local needle="$2"
  local msg="${3:-output does not contain '$needle'}"
  if echo "$haystack" | grep -qF "$needle"; then
    pass
  else
    fail "$msg"
  fi
}

assert_not_contains() {
  local haystack="$1"
  local needle="$2"
  local msg="${3:-output unexpectedly contains '$needle'}"
  if echo "$haystack" | grep -qiF "$needle"; then
    fail "$msg"
  else
    pass
  fi
}

assert_exit_code() {
  local expected="$1"
  local actual="$2"
  local msg="${3:-expected exit code $expected, got $actual}"
  if [ "$expected" = "$actual" ]; then
    pass
  else
    fail "$msg"
  fi
}

print_summary() {
  echo ""
  echo "─────────────────────────────────────────────────"
  echo "Results: $TESTS_RUN tests, $TESTS_PASSED passed, $TESTS_FAILED failed"
  echo "─────────────────────────────────────────────────"
  if [ "$TESTS_FAILED" -gt 0 ]; then
    exit 1
  fi
}

# ── Tests: validate_issue_number ─────────────────────────────────────────────

echo "validate_issue_number"

begin_test "accepts valid issue number 1"
(validate_issue_number "1" >/dev/null 2>&1)
assert_exit_code "0" "$?"

begin_test "accepts valid issue number 144"
(validate_issue_number "144" >/dev/null 2>&1)
assert_exit_code "0" "$?"

begin_test "accepts valid issue number 999"
(validate_issue_number "999" >/dev/null 2>&1)
assert_exit_code "0" "$?"

begin_test "accepts max issue number 57535"
(validate_issue_number "57535" >/dev/null 2>&1)
assert_exit_code "0" "$?"

begin_test "accepts large issue number 99999 (no upper bound)"
(validate_issue_number "99999" >/dev/null 2>&1)
assert_exit_code "0" "$?"

begin_test "rejects issue number 0"
rc=0; validate_issue_number "0" >/dev/null 2>&1 || rc=$?
assert_exit_code "1" "$rc"

begin_test "rejects negative number"
rc=0; validate_issue_number "-1" >/dev/null 2>&1 || rc=$?
assert_exit_code "1" "$rc"

begin_test "rejects non-numeric input"
rc=0; validate_issue_number "abc" >/dev/null 2>&1 || rc=$?
assert_exit_code "1" "$rc"

begin_test "rejects empty input"
rc=0; validate_issue_number "" >/dev/null 2>&1 || rc=$?
assert_exit_code "1" "$rc"

begin_test "rejects command injection attempt"
rc=0; validate_issue_number '1;rm' >/dev/null 2>&1 || rc=$?
assert_exit_code "1" "$rc"

begin_test "rejects subshell injection"
rc=0; validate_issue_number '1$(whoami)' >/dev/null 2>&1 || rc=$?
assert_exit_code "1" "$rc"

begin_test "handles leading zeros (0144 → rejects as starting with 0)"
rc=0; validate_issue_number "0144" >/dev/null 2>&1 || rc=$?
assert_exit_code "1" "$rc"

# ── Tests: is_port_free ──────────────────────────────────────────────────────

echo ""
echo "is_port_free"

begin_test "detects a likely-free high port as free"
# Port 59999 is very unlikely to be in use
is_port_free 59999
assert_exit_code "0" "$?"

# ── Tests: find_free_port ────────────────────────────────────────────────────

echo ""
echo "find_free_port"

begin_test "finds a free port starting from a high range"
result=$(find_free_port 59990)
if [ -n "$result" ] && [ "$result" -ge 59990 ] && [ "$result" -le 65535 ]; then
  pass
else
  fail "expected port in range 59990-65535, got '$result'"
fi

# ── Tests: derive_ports ──────────────────────────────────────────────────────

echo ""
echo "derive_ports"

# Mock is_port_free to always return free (for deterministic tests)
_real_is_port_free=$(declare -f is_port_free)
is_port_free() { return 0; }

begin_test "issue 1 → preferred frontend=3001 when free"
derive_ports 1
assert_eq "3001" "$FRONTEND_PORT"

begin_test "issue 1 → preferred backend=8001 when free"
assert_eq "8001" "$BACKEND_PORT"

begin_test "issue 1 → preferred db=5433 when free"
assert_eq "5433" "$DB_PORT"

begin_test "issue 144 → preferred frontend=3144 when free"
derive_ports 144
assert_eq "3144" "$FRONTEND_PORT"

begin_test "issue 144 → preferred backend=8144 when free"
assert_eq "8144" "$BACKEND_PORT"

begin_test "issue 144 → preferred db=5576 when free"
assert_eq "5576" "$DB_PORT"

begin_test "issue 99999 → clamps frontend to 10000 when overflow"
derive_ports 99999
assert_eq "10000" "$FRONTEND_PORT"

begin_test "issue 99999 → clamps backend to 20000 when overflow"
assert_eq "20000" "$BACKEND_PORT"

begin_test "issue 99999 → clamps db to 30000 when overflow"
assert_eq "30000" "$DB_PORT"

# Restore real is_port_free
eval "$_real_is_port_free"

# ── Tests: detect_issue_from_pwd ─────────────────────────────────────────────

echo ""
echo "detect_issue_from_pwd"

begin_test "detects issue from /path/.claude/worktrees/issue-144"
result=$(detect_issue_from_dir "/some/path/.claude/worktrees/issue-144")
assert_eq "144" "$result"

begin_test "detects issue from /path/.claude/worktrees/issue-7"
result=$(detect_issue_from_dir "/some/path/.claude/worktrees/issue-7")
assert_eq "7" "$result"

begin_test "returns empty for non-worktree path"
result=$(detect_issue_from_dir "/some/path/not-a-worktree")
assert_eq "" "$result"

begin_test "returns empty for repo root"
result=$(detect_issue_from_dir "/Users/crewmaty/OpenLearning")
assert_eq "" "$result"

# ── Tests: generate_override_yaml ────────────────────────────────────────────

echo ""
echo "generate_override_yaml"

TMPDIR_TEST=$(mktemp -d)
trap 'rm -rf "$TMPDIR_TEST"' EXIT

begin_test "generates valid YAML with correct frontend port binding (dev mode)"
generate_override_yaml 144 3144 8144 5576 "$TMPDIR_TEST" "dev"
yaml_content=$(cat "$TMPDIR_TEST/docker-compose.worktree.yml")
assert_contains "$yaml_content" "127.0.0.1:3144:3000"

begin_test "generates correct backend port binding"
assert_contains "$yaml_content" "127.0.0.1:8144:8000"

begin_test "generates correct db port binding"
assert_contains "$yaml_content" "127.0.0.1:5576:5432"

begin_test "uses !override on db ports to replace base compose ports"
assert_contains "$yaml_content" "ports: !override"

begin_test "generates correct CORS_ORIGINS"
assert_contains "$yaml_content" 'CORS_ORIGINS:'

begin_test "CORS_ORIGINS uses explicit localhost (not wildcard)"
assert_contains "$yaml_content" "http://localhost:3144"

begin_test "CORS_ORIGINS does not contain wildcard"
assert_not_contains "$yaml_content" '"*"'

begin_test "generates correct FRONTEND_URL"
assert_contains "$yaml_content" "FRONTEND_URL: \"http://localhost:3144\""

begin_test "generates correct NEXT_PUBLIC_API_URL"
assert_contains "$yaml_content" "NEXT_PUBLIC_API_URL: \"http://localhost:8144\""

begin_test "starts with AUTO-GENERATED comment"
first_line=$(head -1 "$TMPDIR_TEST/docker-compose.worktree.yml")
assert_contains "$first_line" "AUTO-GENERATED"

begin_test "does not contain secrets (api_key)"
assert_not_contains "$yaml_content" "api_key"

begin_test "does not contain secrets (secret)"
# Check for 'secret' but allow 'secret' in the word 'secrets' which isn't there
# Actually just check there's no SECRET= or secret: pattern
assert_not_contains "$yaml_content" "SECRET="

begin_test "does not contain secrets (token)"
assert_not_contains "$yaml_content" "TOKEN="

begin_test "dev mode includes backend volume mount"
assert_contains "$yaml_content" "$TMPDIR_TEST/backend:/app"

begin_test "dev mode includes frontend volume mount"
assert_contains "$yaml_content" "$TMPDIR_TEST/frontend:/app"

begin_test "dev mode includes anonymous node_modules volume"
assert_contains "$yaml_content" "/app/node_modules"

begin_test "prod mode does NOT include volume mounts"
generate_override_yaml 144 3144 8144 5576 "$TMPDIR_TEST" "prod"
yaml_prod=$(cat "$TMPDIR_TEST/docker-compose.worktree.yml")
assert_not_contains "$yaml_prod" "/app"

begin_test "prod mode includes NEXT_PUBLIC_API_URL build arg"
assert_contains "$yaml_prod" "NEXT_PUBLIC_API_URL: \"http://localhost:8144\""

begin_test "prod mode build args section exists"
assert_contains "$yaml_prod" "build:"

begin_test "override file is truncated (not appended) on regeneration"
generate_override_yaml 200 3200 8200 5632 "$TMPDIR_TEST" "dev"
yaml_regen=$(cat "$TMPDIR_TEST/docker-compose.worktree.yml")
assert_not_contains "$yaml_regen" "3144" "old port 3144 should not be present after regeneration"

# ── Tests: handle_symlinks ───────────────────────────────────────────────────

echo ""
echo "handle_symlinks"

TMPDIR_SYMLINKS=$(mktemp -d)

begin_test "removes node_modules symlink"
mkdir -p "$TMPDIR_SYMLINKS/frontend"
mkdir -p "$TMPDIR_SYMLINKS/real_node_modules"
ln -sf "$TMPDIR_SYMLINKS/real_node_modules" "$TMPDIR_SYMLINKS/frontend/node_modules"
handle_symlinks "$TMPDIR_SYMLINKS" "true"  # skip_npm=true for testing
if [ -L "$TMPDIR_SYMLINKS/frontend/node_modules" ]; then
  fail "node_modules is still a symlink"
else
  pass
fi

begin_test "leaves real node_modules directory alone"
mkdir -p "$TMPDIR_SYMLINKS/frontend/node_modules"
touch "$TMPDIR_SYMLINKS/frontend/node_modules/.keep"
handle_symlinks "$TMPDIR_SYMLINKS" "true"
if [ -f "$TMPDIR_SYMLINKS/frontend/node_modules/.keep" ]; then
  pass
else
  fail "real node_modules was incorrectly modified"
fi

begin_test "handles missing node_modules gracefully"
rm -rf "$TMPDIR_SYMLINKS/frontend/node_modules"
rc=0; handle_symlinks "$TMPDIR_SYMLINKS" "true" 2>/dev/null || rc=$?
assert_exit_code "0" "$rc"

begin_test "replaces package-lock.json symlink with real copy"
echo '{"lockfileVersion": 3}' > "$TMPDIR_SYMLINKS/real_lockfile.json"
ln -sf "$TMPDIR_SYMLINKS/real_lockfile.json" "$TMPDIR_SYMLINKS/frontend/package-lock.json"
handle_symlinks "$TMPDIR_SYMLINKS" "true"
if [ -L "$TMPDIR_SYMLINKS/frontend/package-lock.json" ]; then
  fail "package-lock.json is still a symlink"
else
  pass
fi

begin_test "real package-lock.json has correct content after symlink replacement"
content=$(cat "$TMPDIR_SYMLINKS/frontend/package-lock.json")
assert_contains "$content" "lockfileVersion"

begin_test "leaves real package-lock.json alone"
echo '{"lockfileVersion": 3}' > "$TMPDIR_SYMLINKS/frontend/package-lock.json"
handle_symlinks "$TMPDIR_SYMLINKS" "true"
if [ ! -L "$TMPDIR_SYMLINKS/frontend/package-lock.json" ] && [ -f "$TMPDIR_SYMLINKS/frontend/package-lock.json" ]; then
  pass
else
  fail "real package-lock.json was incorrectly modified"
fi

begin_test "handles missing package-lock.json gracefully"
rm -f "$TMPDIR_SYMLINKS/frontend/package-lock.json"
rc=0; handle_symlinks "$TMPDIR_SYMLINKS" "true" 2>/dev/null || rc=$?
assert_exit_code "0" "$rc"

begin_test "handles broken package-lock.json symlink gracefully"
ln -sf "/nonexistent/path/package-lock.json" "$TMPDIR_SYMLINKS/frontend/package-lock.json"
rc=0; handle_symlinks "$TMPDIR_SYMLINKS" "true" 2>/dev/null || rc=$?
assert_exit_code "0" "$rc"

begin_test "broken symlink is removed"
if [ -L "$TMPDIR_SYMLINKS/frontend/package-lock.json" ]; then
  fail "broken symlink was not removed"
else
  pass
fi

rm -rf "$TMPDIR_SYMLINKS"

# ── Integration tests (require Docker) ───────────────────────────────────────

if [ "${INTEGRATION:-0}" = "1" ]; then
  echo ""
  echo "integration tests (Docker required)"

  begin_test "generated YAML is valid docker compose config"
  TMPDIR_INT=$(mktemp -d)
  generate_override_yaml 152 3152 8152 5584 "$TMPDIR_INT" "dev"
  docker compose \
    -f "$REPO_ROOT/docker-compose.yml" \
    -f "$REPO_ROOT/docker-compose.dev.yml" \
    -f "$TMPDIR_INT/docker-compose.worktree.yml" \
    --project-directory "$TMPDIR_INT" \
    config >/dev/null 2>&1
  assert_exit_code "0" "$?"
  rm -rf "$TMPDIR_INT"
fi

# ── Summary ──────────────────────────────────────────────────────────────────

print_summary
