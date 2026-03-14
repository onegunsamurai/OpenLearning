#!/usr/bin/env bash
set -euo pipefail

# Block .env files from being committed (except .env.example)
env_files=$(git diff --cached --name-only --diff-filter=ACR | grep '\.env' | grep -v '\.env\.example' || true)

if [ -n "$env_files" ]; then
  echo "ERROR: Attempting to commit .env file(s):"
  echo "$env_files"
  echo ""
  echo "These files may contain secrets. Remove them from staging with:"
  echo "  git reset HEAD <file>"
  exit 1
fi
