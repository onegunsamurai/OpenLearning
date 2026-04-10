#!/usr/bin/env bash
# test-frontend-entrypoint.sh — Unit tests for frontend/docker-entrypoint.sh.
#
# Regression coverage for issue #159: the dev-mode anonymous volume at
# /app/node_modules persisted across rebuilds, so new dependencies added to
# package.json never made it into the running container. The entrypoint fixes
# that by running `npm ci` whenever package-lock.json is newer than the
# install marker (or the marker is missing entirely). It falls back to
# `npm install` only when the lockfile itself is absent.
#
# These tests run the entrypoint in a tmpdir with a fake `npm` on PATH so we
# can assert whether `npm ci`/`npm install` was invoked without touching the
# real package manager.
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

# Snapshot PATH once so each sandbox starts from a clean slate instead of
# accumulating dead tmpdir prefixes across tests.
ORIGINAL_PATH="$PATH"

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
# creates the install marker when called with `install` or `ci`.
make_sandbox() {
  SANDBOX=$(mktemp -d)
  mkdir -p "$SANDBOX/bin"
  cat > "$SANDBOX/bin/npm" <<'EOF'
#!/bin/sh
echo "npm $*" >> "$SANDBOX/npm-calls.log"
if [ "$1" = "install" ] || [ "$1" = "ci" ]; then
  mkdir -p node_modules
  touch node_modules/.package-lock.json
fi
EOF
  chmod +x "$SANDBOX/bin/npm"
  : > "$SANDBOX/npm-calls.log"
  export SANDBOX
  # Reset PATH from the original snapshot so each sandbox adds exactly one
  # prefix instead of stacking on previous runs.
  export PATH="$SANDBOX/bin:$ORIGINAL_PATH"
}

cleanup_sandbox() {
  [ -n "${SANDBOX:-}" ] && rm -rf "$SANDBOX"
  SANDBOX=""
  export PATH="$ORIGINAL_PATH"
}

# Remove any dangling sandbox even if a test aborts under `set -e`.
trap cleanup_sandbox EXIT

# run_entrypoint — run the entrypoint from inside the sandbox with `true` as CMD.
# Captures the exit status without aborting the test script when the
# entrypoint itself exits non-zero (`set -e` would otherwise kill us).
# Stores the status in $ENTRYPOINT_STATUS and logs stdout/stderr to
# $SANDBOX/entrypoint.log.
run_entrypoint() {
  set +e
  (
    cd "$SANDBOX"
    "$ENTRYPOINT" true
  ) > "$SANDBOX/entrypoint.log" 2>&1
  ENTRYPOINT_STATUS=$?
  set -e
}

# Every success-path assertion must also verify the entrypoint exited 0.
# Otherwise a scenario could silently pass even if the entrypoint crashed
# *after* the npm step (e.g. a bug in the final `exec "$@"` guard).
_assert_exit_success() {
  if [ "${ENTRYPOINT_STATUS:-unset}" != "0" ]; then
    fail "expected exit status 0, got '${ENTRYPOINT_STATUS:-unset}'; log was: $(cat "$SANDBOX/entrypoint.log")"
    return 1
  fi
  return 0
}

assert_npm_not_called() {
  _assert_exit_success || return
  if [ -s "$SANDBOX/npm-calls.log" ]; then
    fail "expected npm to NOT be called; log was: $(cat "$SANDBOX/npm-calls.log")"
  else
    pass
  fi
}

assert_npm_ci_called() {
  _assert_exit_success || return
  if grep -q "^npm ci" "$SANDBOX/npm-calls.log"; then
    pass
  else
    fail "expected npm ci; log was: $(cat "$SANDBOX/npm-calls.log")"
  fi
}

assert_npm_install_called() {
  _assert_exit_success || return
  if grep -q "^npm install" "$SANDBOX/npm-calls.log" && \
     ! grep -q "^npm ci" "$SANDBOX/npm-calls.log"; then
    pass
  else
    fail "expected npm install (and not npm ci); log was: $(cat "$SANDBOX/npm-calls.log")"
  fi
}

# ── Tests ───────────────────────────────────────────────────────────────────

echo "Running frontend entrypoint tests..."
echo ""

# Scenario 1: fresh container — no node_modules at all, lockfile present.
begin_test "runs npm ci when node_modules is missing and lockfile exists"
make_sandbox
touch "$SANDBOX/package.json" "$SANDBOX/package-lock.json"
run_entrypoint
assert_npm_ci_called
cleanup_sandbox

# Scenario 2: stale anonymous volume — node_modules exists but no marker.
begin_test "runs npm ci when install marker is missing"
make_sandbox
touch "$SANDBOX/package.json" "$SANDBOX/package-lock.json"
mkdir -p "$SANDBOX/node_modules"
run_entrypoint
assert_npm_ci_called
cleanup_sandbox

# Scenario 3: regression for #159 — lockfile updated after last install.
begin_test "runs npm ci when package-lock.json is newer than marker"
make_sandbox
touch "$SANDBOX/package.json"
mkdir -p "$SANDBOX/node_modules"
# Marker exists but is older than the lockfile.
touch -t 202001010000 "$SANDBOX/node_modules/.package-lock.json"
touch -t 202601010000 "$SANDBOX/package-lock.json"
run_entrypoint
assert_npm_ci_called
cleanup_sandbox

# Scenario 4: happy path — deps are already in sync, nothing to do.
begin_test "skips install when marker is newer than lockfile"
make_sandbox
touch "$SANDBOX/package.json"
mkdir -p "$SANDBOX/node_modules"
touch -t 202001010000 "$SANDBOX/package-lock.json"
touch -t 202601010000 "$SANDBOX/node_modules/.package-lock.json"
run_entrypoint
assert_npm_not_called
cleanup_sandbox

# Scenario 5: fallback to `npm install` when the lockfile is missing entirely.
# Covers the "bare package.json" edge case rather than crashing with `npm ci`.
begin_test "falls back to npm install when package-lock.json is missing"
make_sandbox
touch "$SANDBOX/package.json"
# Deliberately no package-lock.json, no node_modules.
run_entrypoint
assert_npm_install_called
cleanup_sandbox

# Scenario 6: entrypoint must exec the CMD passed as argv.
begin_test "execs the CMD arguments after the install check"
make_sandbox
touch "$SANDBOX/package.json"
mkdir -p "$SANDBOX/node_modules"
touch "$SANDBOX/node_modules/.package-lock.json"
touch -t 202001010000 "$SANDBOX/package-lock.json"
touch -t 202601010000 "$SANDBOX/node_modules/.package-lock.json"
# Use `sh -c 'echo SENTINEL'` as CMD and verify SENTINEL is printed.
set +e
( cd "$SANDBOX" && "$ENTRYPOINT" sh -c 'echo SENTINEL_ENTRYPOINT_EXEC' ) \
  > "$SANDBOX/entrypoint.log" 2>&1
exec_status=$?
set -e
if [ "$exec_status" -eq 0 ] && grep -q "SENTINEL_ENTRYPOINT_EXEC" "$SANDBOX/entrypoint.log"; then
  pass
else
  fail "CMD was not exec'd (status=$exec_status); log was: $(cat "$SANDBOX/entrypoint.log")"
fi
cleanup_sandbox

# Scenario 7: fail loudly when no command is supplied, BEFORE running npm.
# Without this guard, `exec ""` would silently exit 127 in shells that allow
# it; the entrypoint should print a clear diagnostic, exit non-zero, and
# crucially NOT waste a full `npm ci` before discovering the missing CMD.
# We deliberately stage a state that WOULD trigger npm ci (missing marker)
# so that a regression moving the guard back below the install step would
# be caught by the "npm log is empty" assertion.
begin_test "errors out when no CMD is provided without running npm"
make_sandbox
touch "$SANDBOX/package.json" "$SANDBOX/package-lock.json"
# No node_modules → needs_install would return true if reached.
set +e
( cd "$SANDBOX" && "$ENTRYPOINT" ) > "$SANDBOX/entrypoint.log" 2>&1
no_cmd_status=$?
set -e
if [ "$no_cmd_status" -ne 0 ] \
   && grep -q "no command provided" "$SANDBOX/entrypoint.log" \
   && [ ! -s "$SANDBOX/npm-calls.log" ]; then
  pass
else
  fail "expected non-zero exit + diagnostic + no npm calls; status=$no_cmd_status log=$(cat "$SANDBOX/entrypoint.log") npm=$(cat "$SANDBOX/npm-calls.log")"
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
