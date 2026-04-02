#!/usr/bin/env bash
# worktree-list.sh — List active git worktrees for GitHub issues.
# Usage: bash scripts/worktree-list.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKTREE_BASE="$REPO_ROOT/.claude/worktrees"

# ── Check for worktrees ─────────────────────────────────────────────────────

if [ ! -d "$WORKTREE_BASE" ]; then
  echo "No active worktrees."
  exit 0
fi

worktrees=("$WORKTREE_BASE"/issue-*)
if [ ! -d "${worktrees[0]:-}" ]; then
  echo "No active worktrees."
  exit 0
fi

# ── Pre-fetch data (avoid N+1 subprocess calls) ─────────────────────────────

# Single docker ps call for all running containers (O(1) instead of O(N))
running_containers=$(docker ps --format '{{.Names}}' 2>/dev/null || echo "")

# Print header
printf "%-7s  %-50s  %-7s  %-8s  %s\n" "Issue" "Branch" "Status" "Docker" "Title"
printf "%-7s  %-50s  %-7s  %-8s  %s\n" "-----" "------" "------" "------" "-----"

for wt_dir in "${worktrees[@]}"; do
  [ -d "$wt_dir" ] || continue

  issue_num=$(basename "$wt_dir" | sed 's/issue-//')

  # Get branch name from git worktree list
  branch_name=$(git -C "$REPO_ROOT" worktree list --porcelain \
    | awk -v dir="$wt_dir" '
      /^worktree / { wt=$2 }
      /^branch /   { if (wt == dir) { sub(/^branch refs\/heads\//, ""); print } }
    ')

  # Check for uncommitted changes
  if [ -n "$(git -C "$wt_dir" status --porcelain 2>/dev/null)" ]; then
    status="dirty"
  else
    status="clean"
  fi

  # Fetch issue title (best-effort)
  title=""
  if command -v gh >/dev/null 2>&1; then
    title=$(gh issue view "$issue_num" --json title --jq '.title' 2>/dev/null) || title="(could not fetch)"
  fi

  # Truncate title if needed
  if [ ${#title} -gt 50 ]; then
    title="${title:0:47}..."
  fi

  # Check Docker stack status (string match against pre-fetched container names)
  docker_status="down"
  if echo "$running_containers" | grep -qF "openlearning-wt-${issue_num}"; then
    docker_status="up"
  fi

  printf "#%-6s  %-50s  %-7s  %-8s  %s\n" "$issue_num" "$branch_name" "$status" "$docker_status" "$title"
done
