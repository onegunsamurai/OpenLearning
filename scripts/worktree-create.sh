#!/usr/bin/env bash
# worktree-create.sh — Create a git worktree for a GitHub issue.
# Usage: bash scripts/worktree-create.sh <issue-number> [prefix-override]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKTREE_BASE="$REPO_ROOT/.claude/worktrees"

# ── Helpers ──────────────────────────────────────────────────────────────────

usage() {
  echo "Usage: $0 <issue-number> [prefix]"
  echo ""
  echo "  issue-number   GitHub issue number (e.g., 127)"
  echo "  prefix         Branch prefix override: fix, feat, docs (default: inferred from labels)"
  echo ""
  echo "Example: $0 127"
  echo "         $0 127 fix"
  exit 1
}

slugify() {
  echo "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed 's/[^a-z0-9]/-/g' \
    | sed 's/--*/-/g' \
    | sed 's/^-//;s/-$//' \
    | cut -c1-40 \
    | sed 's/-$//'
}

get_prefix() {
  local labels="$1"
  if echo "$labels" | grep -qi "bug"; then
    echo "fix"
  elif echo "$labels" | grep -qi "documentation"; then
    echo "docs"
  else
    echo "feat"
  fi
}

symlink_if_exists() {
  local src="$1"
  local dst="$2"
  if [ -f "$src" ]; then
    mkdir -p "$(dirname "$dst")"
    ln -sf "$src" "$dst"
    echo "  ✓ Symlinked $(basename "$dst")"
  else
    echo "  ⚠ Skipped $(basename "$dst") — source not found: $src"
  fi
}

# ── Argument parsing ─────────────────────────────────────────────────────────

if [ $# -lt 1 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  usage
fi

ISSUE_NUM="$1"
PREFIX_OVERRIDE="${2:-}"

if ! [[ "$ISSUE_NUM" =~ ^[0-9]+$ ]]; then
  echo "Error: Issue number must be numeric, got '$ISSUE_NUM'" >&2
  exit 1
fi

# ── Prerequisite checks ─────────────────────────────────────────────────────

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: GitHub CLI (gh) is required. Install: brew install gh" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Error: Not authenticated with GitHub. Run: gh auth login" >&2
  exit 1
fi

# ── Fetch issue ──────────────────────────────────────────────────────────────

echo "Fetching issue #$ISSUE_NUM..."

ISSUE_JSON=$(gh issue view "$ISSUE_NUM" --json title,labels,state 2>&1) || {
  echo "Error: Could not fetch issue #$ISSUE_NUM. Does it exist?" >&2
  exit 1
}

ISSUE_TITLE=$(echo "$ISSUE_JSON" | jq -r '.title')
ISSUE_STATE=$(echo "$ISSUE_JSON" | jq -r '.state')
ISSUE_LABELS=$(echo "$ISSUE_JSON" | jq -r '[.labels[].name] | join(",")')

echo "  Title: $ISSUE_TITLE"
echo "  State: $ISSUE_STATE"

if [ "$ISSUE_STATE" = "CLOSED" ]; then
  echo "  ⚠ Warning: This issue is closed. Proceeding anyway."
fi

# ── Derive branch name ──────────────────────────────────────────────────────

if [ -n "$PREFIX_OVERRIDE" ]; then
  PREFIX="$PREFIX_OVERRIDE"
else
  PREFIX=$(get_prefix "$ISSUE_LABELS")
fi

SLUG=$(slugify "$ISSUE_TITLE")
BRANCH_NAME="${PREFIX}/issue-${ISSUE_NUM}-${SLUG}"

echo "  Branch: $BRANCH_NAME"

# ── Check for existing worktree ──────────────────────────────────────────────

WORKTREE_DIR="$WORKTREE_BASE/issue-$ISSUE_NUM"

if [ -d "$WORKTREE_DIR" ]; then
  echo "Error: Worktree already exists at $WORKTREE_DIR" >&2
  echo "  Use 'make worktree-remove ISSUE=$ISSUE_NUM' to remove it first." >&2
  exit 1
fi

# ── Check for existing branch ────────────────────────────────────────────────

BRANCH_EXISTS=""
if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$BRANCH_NAME" 2>/dev/null; then
  BRANCH_EXISTS="local"
elif git -C "$REPO_ROOT" show-ref --verify --quiet "refs/remotes/origin/$BRANCH_NAME" 2>/dev/null; then
  BRANCH_EXISTS="remote"
fi

# ── Create worktree ──────────────────────────────────────────────────────────

mkdir -p "$WORKTREE_BASE"

echo ""
echo "Creating worktree..."

if [ "$BRANCH_EXISTS" = "local" ]; then
  echo "  Reusing existing local branch: $BRANCH_NAME"
  git -C "$REPO_ROOT" worktree add "$WORKTREE_DIR" "$BRANCH_NAME"
elif [ "$BRANCH_EXISTS" = "remote" ]; then
  echo "  Tracking existing remote branch: $BRANCH_NAME"
  git -C "$REPO_ROOT" worktree add "$WORKTREE_DIR" -b "$BRANCH_NAME" "origin/$BRANCH_NAME"
else
  git -C "$REPO_ROOT" worktree add -b "$BRANCH_NAME" "$WORKTREE_DIR" main
fi

echo "  ✓ Worktree created at .claude/worktrees/issue-$ISSUE_NUM"

# ── Symlink gitignored files ─────────────────────────────────────────────────

echo ""
echo "Symlinking configuration files..."

symlink_if_exists "$REPO_ROOT/.env" "$WORKTREE_DIR/.env"
symlink_if_exists "$REPO_ROOT/.claude/settings.local.json" "$WORKTREE_DIR/.claude/settings.local.json"
symlink_if_exists "$REPO_ROOT/backend/.env" "$WORKTREE_DIR/backend/.env"
symlink_if_exists "$REPO_ROOT/frontend/.env.local" "$WORKTREE_DIR/frontend/.env.local"

# ── Install dependencies ─────────────────────────────────────────────────────

echo ""
echo "Installing dependencies..."

echo "  Frontend (npm install)..."
(cd "$WORKTREE_DIR/frontend" && npm install --silent 2>&1) || {
  echo "  ⚠ npm install failed — you may need to run it manually"
}

echo "  Backend (pip install)..."
(cd "$WORKTREE_DIR/backend" && pip install -r requirements.txt -q 2>&1) || {
  echo "  ⚠ pip install failed — you may need to run it manually"
}

# Install pre-commit hooks if pre-commit is available
if command -v pre-commit >/dev/null 2>&1; then
  (cd "$WORKTREE_DIR" && pre-commit install --allow-missing-config -q 2>&1) || true
fi

# ── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo "─────────────────────────────────────────────────"
echo "WORKTREE READY"
echo ""
echo "  Issue:    #$ISSUE_NUM — $ISSUE_TITLE"
echo "  Branch:   $BRANCH_NAME"
echo "  Path:     .claude/worktrees/issue-$ISSUE_NUM"
echo ""
echo "Next steps:"
echo "  cd .claude/worktrees/issue-$ISSUE_NUM"
echo "  claude                    # start Claude Code"
echo "  make dev                  # run dev server"
echo "  make check                # run all checks"
echo "─────────────────────────────────────────────────"
