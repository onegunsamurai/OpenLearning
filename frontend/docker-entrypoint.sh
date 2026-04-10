#!/bin/sh
# docker-entrypoint.sh — Refresh node_modules if package-lock.json has changed.
#
# Context: docker-compose.dev.yml uses an anonymous volume at /app/node_modules
# to prevent the host's macOS-native node_modules from shadowing the container's
# Linux-native install. However, the anonymous volume persists across rebuilds,
# so when package.json gains a new dependency the volume reattaches stale
# node_modules on top of the freshly-installed image. This script detects that
# mismatch at container start and runs `npm ci` to resync.
#
# Decision logic:
#   1. If node_modules is missing or the install marker is absent → install.
#   2. If package-lock.json is newer than node_modules/.package-lock.json
#      (the marker npm writes after every successful install) → install.
#   3. Otherwise → skip; deps are already in sync.
#
# Install command: `npm ci` when a lockfile exists (deterministic, never
# rewrites the host lockfile via the bind mount), falling back to
# `npm install` only if package-lock.json is absent.
set -e

# Fail fast if the caller forgot to pass a CMD. `exec ""` would otherwise
# silently exit 127 in some shells, and we'd waste a full `npm ci` before
# hitting that failure — so gate on argv up front.
if [ "$#" -eq 0 ]; then
  echo "[entrypoint] error: no command provided to docker-entrypoint.sh" >&2
  exit 1
fi

MARKER="node_modules/.package-lock.json"
LOCKFILE="package-lock.json"

needs_install() {
  if [ ! -d node_modules ] || [ ! -f "$MARKER" ]; then
    return 0
  fi
  if [ ! -f "$LOCKFILE" ]; then
    return 1
  fi
  if [ "$LOCKFILE" -nt "$MARKER" ]; then
    return 0
  fi
  return 1
}

if needs_install; then
  if [ -f "$LOCKFILE" ]; then
    # Prefer `npm ci` for determinism: it refuses to run when package.json
    # and package-lock.json disagree, and it never rewrites the lockfile
    # (which matters because /app is a host bind mount — `npm install`
    # would silently edit the developer's checked-in lockfile on startup).
    echo "[entrypoint] package-lock.json changed or node_modules missing — running npm ci..."
    npm ci --no-audit --no-fund
  else
    # No lockfile: fall back to `npm install` so a bare `package.json`
    # still produces a working tree instead of failing hard.
    echo "[entrypoint] node_modules missing and no package-lock.json — running npm install..."
    npm install --no-audit --no-fund
  fi
elif [ -f "$LOCKFILE" ]; then
  echo "[entrypoint] node_modules is up to date with package-lock.json — skipping install."
else
  echo "[entrypoint] node_modules present and no package-lock.json — skipping install."
fi

exec "$@"
