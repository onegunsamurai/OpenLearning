#!/usr/bin/env bash
# worktree-remove.sh — Remove a git worktree for a GitHub issue.
# Usage: bash scripts/worktree-remove.sh <issue-number|--all> [--force] [--delete-branch]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKTREE_BASE="$REPO_ROOT/.claude/worktrees"

# ── Helpers ──────────────────────────────────────────────────────────────────

usage() {
  echo "Usage: $0 <issue-number|--all> [--force] [--delete-branch]"
  echo ""
  echo "  issue-number     GitHub issue number (e.g., 127)"
  echo "  --all            Remove all worktrees"
  echo "  --force          Skip confirmation and force-remove dirty worktrees"
  echo "  --delete-branch  Also delete the local branch after removing the worktree"
  echo ""
  echo "Example: $0 127"
  echo "         $0 127 --force --delete-branch"
  echo "         $0 --all --force"
  exit 1
}

remove_worktree() {
  local worktree_dir="$1"
  local force="$2"
  local delete_branch="$3"

  if [ ! -d "$worktree_dir" ]; then
    echo "Error: Worktree not found at $worktree_dir" >&2
    return 1
  fi

  # Get the branch name for this worktree
  local branch_name=""
  branch_name=$(git -C "$REPO_ROOT" worktree list --porcelain \
    | awk -v dir="$worktree_dir" '
      /^worktree / { wt=$2 }
      /^branch /   { if (wt == dir) { sub(/^branch refs\/heads\//, ""); print } }
    ')

  local issue_num
  issue_num=$(basename "$worktree_dir" | sed 's/issue-//')

  # Validate issue_num is numeric before using in docker compose commands
  if ! [[ "$issue_num" =~ ^[0-9]+$ ]]; then
    echo "  ⚠ Could not determine issue number from directory name" >&2
    issue_num=""
  fi

  # Check for uncommitted changes
  local dirty=""
  if [ -n "$(git -C "$worktree_dir" status --porcelain 2>/dev/null)" ]; then
    dirty="yes"
    echo "  ⚠ Worktree has uncommitted changes!"
  fi

  # Confirm unless --force
  if [ "$force" != "yes" ]; then
    echo "Remove worktree for issue #$issue_num on branch $branch_name? [y/N] "
    read -r confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
      echo "  Skipped."
      return 0
    fi
  fi

  # Stop Docker stack if running (after confirmation, before removal to free ports)
  if [ -n "$issue_num" ] && docker compose -p "openlearning-wt-${issue_num}" ps --quiet 2>/dev/null | grep -q .; then
    echo "  Stopping Docker stack for issue-${issue_num}..."
    docker compose -p "openlearning-wt-${issue_num}" down -v --timeout 10 2>/dev/null || true
    echo "  ✓ Docker stack stopped"
  fi

  # Remove generated override file
  rm -f "${worktree_dir}/docker-compose.worktree.yml"

  # Remove the worktree
  if [ "$dirty" = "yes" ] && [ "$force" = "yes" ]; then
    git -C "$REPO_ROOT" worktree remove --force "$worktree_dir"
  elif [ "$dirty" = "yes" ]; then
    echo "  Error: Worktree is dirty. Use --force to remove anyway." >&2
    return 1
  else
    git -C "$REPO_ROOT" worktree remove "$worktree_dir"
  fi

  echo "  ✓ Removed worktree .claude/worktrees/issue-$issue_num"

  # Optionally delete the branch
  if [ "$delete_branch" = "yes" ] && [ -n "$branch_name" ]; then
    if [ "$force" = "yes" ]; then
      git -C "$REPO_ROOT" branch -D "$branch_name" 2>/dev/null || true
    else
      git -C "$REPO_ROOT" branch -d "$branch_name" 2>/dev/null || {
        echo "  ⚠ Branch $branch_name has unmerged changes. Use --force to delete anyway."
      }
    fi
    echo "  ✓ Deleted branch $branch_name"
  elif [ -n "$branch_name" ]; then
    echo "  Branch $branch_name kept (delete with --delete-branch)"
  fi
}

# ── Argument parsing ─────────────────────────────────────────────────────────

if [ $# -lt 1 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  usage
fi

TARGET="$1"
shift

FORCE="no"
DELETE_BRANCH="no"

for arg in "$@"; do
  case "$arg" in
    --force) FORCE="yes" ;;
    --delete-branch) DELETE_BRANCH="yes" ;;
    *) echo "Unknown option: $arg" >&2; usage ;;
  esac
done

# ── Execute ──────────────────────────────────────────────────────────────────

if [ "$TARGET" = "--all" ]; then
  if [ ! -d "$WORKTREE_BASE" ]; then
    echo "No worktrees found."
    exit 0
  fi

  worktrees=("$WORKTREE_BASE"/issue-*)
  if [ ! -d "${worktrees[0]:-}" ]; then
    echo "No worktrees found."
    exit 0
  fi

  echo "Removing all worktrees..."
  for wt in "${worktrees[@]}"; do
    [ -d "$wt" ] || continue
    remove_worktree "$wt" "$FORCE" "$DELETE_BRANCH"
  done
elif [[ "$TARGET" =~ ^[0-9]+$ ]]; then
  remove_worktree "$WORKTREE_BASE/issue-$TARGET" "$FORCE" "$DELETE_BRANCH"
else
  echo "Error: Expected issue number or --all, got '$TARGET'" >&2
  usage
fi

# Prune any stale worktree entries
git -C "$REPO_ROOT" worktree prune 2>/dev/null || true
