#!/usr/bin/env bash
# protect-files.sh — Guard secrets, auto-generated code, and lock files from edits.
# Called as a PreToolUse hook for Edit|Write. Reads tool input JSON from stdin.
# Exit 0 = allow, Exit 2 = block.

set -euo pipefail

# Read stdin (tool input JSON)
input=$(cat)

# Extract file_path from JSON — prefer jq, fall back to python3
if command -v jq >/dev/null 2>&1; then
  file_path=$(echo "$input" | jq -r '.file_path // empty' 2>/dev/null)
else
  file_path=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('file_path',''))" 2>/dev/null)
fi

# If we couldn't extract a file path, allow (fail open)
if [ -z "$file_path" ]; then
  exit 0
fi

# Normalize: get just the filename and relative path components
filename=$(basename "$file_path")
rel_path="$file_path"

# Protected patterns
case "$filename" in
  .env|.env.*)
    echo "BLOCKED: $filename is a secrets file. Do not read or modify environment files directly." >&2
    exit 2
    ;;
  *.pem|*.key)
    echo "BLOCKED: $filename is a credential file. Do not modify key/certificate files." >&2
    exit 2
    ;;
  package-lock.json)
    if echo "$rel_path" | grep -q "frontend"; then
      echo "BLOCKED: frontend/package-lock.json is managed by npm. Use 'npm install' to modify dependencies." >&2
      exit 2
    fi
    ;;
esac

# Protected directories / specific files
if echo "$rel_path" | grep -q "frontend/src/lib/generated/"; then
  echo "BLOCKED: frontend/src/lib/generated/ is auto-generated from OpenAPI. Run 'make generate-api' to regenerate." >&2
  exit 2
fi

if echo "$rel_path" | grep -qE "backend/openapi\.json$"; then
  echo "BLOCKED: backend/openapi.json is auto-generated. Run 'python scripts/export-openapi.py' to regenerate." >&2
  exit 2
fi

# File is not protected — allow
exit 0
