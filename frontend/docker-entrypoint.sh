#!/bin/sh
# docker-entrypoint.sh — Refresh node_modules if package-lock.json has changed.
#
# Context: docker-compose.dev.yml uses an anonymous volume at /app/node_modules
# to prevent the host's macOS-native node_modules from shadowing the container's
# Linux-native install. However, the anonymous volume persists across rebuilds,
# so when package.json gains a new dependency the volume reattaches stale
# node_modules on top of the freshly-installed image. This script detects that
# mismatch at container start and runs `npm install` to resync.
#
# Decision logic:
#   1. If node_modules is missing entirely → run npm install.
#   2. If package-lock.json is newer than node_modules/.package-lock.json
#      (the marker npm writes after every successful install) → run npm install.
#   3. Otherwise → skip; deps are already in sync.
set -e

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
  echo "[entrypoint] package-lock.json changed or node_modules missing — running npm install..."
  npm install --no-audit --no-fund
else
  echo "[entrypoint] node_modules is up to date with package-lock.json — skipping install."
fi

exec "$@"
