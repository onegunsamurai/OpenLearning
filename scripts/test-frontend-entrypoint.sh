#!/usr/bin/env bash
# test-frontend-entrypoint.sh — Unit tests for frontend/docker-entrypoint.sh.
#
# Regression coverage for issue #159: the dev-mode anonymous volume at
# /app/node_modules persisted across rebuilds, so new dependencies added to
# package.json never made it into the running container. The entrypoint fixes
# that by running `npm install` whenever package-lock.json is newer than the
# install marker (or the marker is missing entirely).
#
# These tests run the entrypoint in a tmpdir with a fake `npm` on PATH so we
# can assert whether `npm install` was invoked without touching the real
# package manager.
#
# Usage: bash scripts/test-frontend-entrypoint.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENTRYPOINT="$REPO_ROOT/frontend/docker-entrypoint.sh"

if [ ! -x "$ENTRYPOINT" ]; then
  echo "Error: $ENTRYPOINT is not executable" >&2
  exit 1
fi

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

# make_sandbox — set up a tmpdir with a fake `npm` on PATH.
# The fake npm records every invocation to $SANDBOX/npm-calls.log and
# creates the install marker when called with `install`.
make_sandbox() {
  SANDBOX=$(mktemp -d)
  mkdir -p "$SANDBOX/bin"
  cat > "$SANDBOX/bin/npm" <<'EOF'
#!/bin/sh
echo "npm $*" >> "$SANDBOX/npm-calls.log"
if [ "$1" = "install" ]; then
  mkdir -p node_modules
  touch node_modules/.package-lock.json
fi
EOF
  chmod +x "$SANDBOX/bin/npm"
  : > "$SANDBOX/npm-calls.log"
  export SANDBOX
  export PATH="$SANDBOX/bin:$PATH"
}

cleanup_sandbox() {
  [ -n "${SANDBOX:-}" ] && rm -rf "$SANDBOX"
  SANDBOX=""
}

# run_entrypoint — run the entrypoint from inside the sandbox with `true` as CMD.
# Returns the exit code. Captures stdout/stderr into $SANDBOX/entrypoint.log.
run_entrypoint() {
  (
    cd "$SANDBOX"
    "$ENTRYPOINT" true
  ) > "$SANDBOX/entrypoint.log" 2>&1
}

assert_npm_called() {
  if grep -q "^npm install" "$SANDBOX/npm-calls.log"; then
    pass
  else
    fail "expected npm install to be called; log was: $(cat "$SANDBOX/npm-calls.log")"
  fi
}

assert_npm_not_called() {
  if [ -s "$SANDBOX/npm-calls.log" ]; then
    fail "expected npm to NOT be called; log was: $(cat "$SANDBOX/npm-calls.log")"
  else
    pass
  fi
}

# ── Tests ───────────────────────────────────────────────────────────────────

echo "Running frontend entrypoint tests..."
echo ""

# Scenario 1: fresh container — no node_modules at all.
begin_test "runs npm install when node_modules is missing"
make_sandbox
touch "$SANDBOX/package.json" "$SANDBOX/package-lock.json"
run_entrypoint
assert_npm_called
cleanup_sandbox

# Scenario 2: stale anonymous volume — node_modules exists but no marker.
begin_test "runs npm install when install marker is missing"
make_sandbox
touch "$SANDBOX/package.json" "$SANDBOX/package-lock.json"
mkdir -p "$SANDBOX/node_modules"
run_entrypoint
assert_npm_called
cleanup_sandbox

# Scenario 3: regression for #159 — lockfile updated after last install.
begin_test "runs npm install when package-lock.json is newer than marker"
make_sandbox
touch "$SANDBOX/package.json"
mkdir -p "$SANDBOX/node_modules"
# Marker exists but is older than the lockfile.
touch -t 202001010000 "$SANDBOX/node_modules/.package-lock.json"
touch -t 202601010000 "$SANDBOX/package-lock.json"
run_entrypoint
assert_npm_called
cleanup_sandbox

# Scenario 4: happy path — deps are already in sync, nothing to do.
begin_test "skips npm install when marker is newer than lockfile"
make_sandbox
touch "$SANDBOX/package.json"
mkdir -p "$SANDBOX/node_modules"
touch -t 202001010000 "$SANDBOX/package-lock.json"
touch -t 202601010000 "$SANDBOX/node_modules/.package-lock.json"
run_entrypoint
assert_npm_not_called
cleanup_sandbox

# Scenario 5: entrypoint must exec the CMD passed as argv.
begin_test "execs the CMD arguments after the install check"
make_sandbox
touch "$SANDBOX/package.json"
mkdir -p "$SANDBOX/node_modules"
touch "$SANDBOX/node_modules/.package-lock.json"
touch -t 202001010000 "$SANDBOX/package-lock.json"
touch -t 202601010000 "$SANDBOX/node_modules/.package-lock.json"
# Use `sh -c 'echo SENTINEL'` as CMD and verify SENTINEL is printed.
( cd "$SANDBOX" && "$ENTRYPOINT" sh -c 'echo SENTINEL_ENTRYPOINT_EXEC' ) \
  > "$SANDBOX/entrypoint.log" 2>&1
if grep -q "SENTINEL_ENTRYPOINT_EXEC" "$SANDBOX/entrypoint.log"; then
  pass
else
  fail "CMD was not exec'd; log was: $(cat "$SANDBOX/entrypoint.log")"
fi
cleanup_sandbox

# ── Summary ─────────────────────────────────────────────────────────────────

echo ""
echo "─────────────────────────────────────"
echo "Tests run:    $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo "─────────────────────────────────────"

if [ "$TESTS_FAILED" -gt 0 ]; then
  exit 1
fi
