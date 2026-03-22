#!/usr/bin/env bash
# block-no-verify.sh — Block git commit/push with --no-verify flag.
# Called as a PreToolUse hook for Bash. Reads tool input JSON from stdin.
# Exit 0 = allow, Exit 2 = block.

set -euo pipefail

# Read stdin (tool input JSON)
input=$(cat)

# Extract command from JSON — prefer jq, fall back to python3
if command -v jq >/dev/null 2>&1; then
  command_str=$(echo "$input" | jq -r '.command // empty' 2>/dev/null)
else
  command_str=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('command',''))" 2>/dev/null)
fi

# If we couldn't extract a command, allow (fail open)
if [ -z "$command_str" ]; then
  exit 0
fi

# Check for --no-verify in git commit or git push commands
if echo "$command_str" | grep -qE 'git\s+(commit|push)' && echo "$command_str" | grep -q -- '--no-verify'; then
  echo "BLOCKED: --no-verify bypasses pre-commit hooks. Run \`make check\` to fix issues instead." >&2
  exit 2
fi

exit 0
