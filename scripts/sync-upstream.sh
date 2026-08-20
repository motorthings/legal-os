#!/usr/bin/env bash
#
# sync-upstream.sh — pull the latest claude-for-legal skills into legal-os.
#
# Vendored via git subtree at vendor/claude-for-legal. The upstream remote
# (upstream-legal = https://github.com/anthropics/claude-for-legal) is the
# source of the skill/plugin content; legal-os's runtime is the source of
# governance. This script updates the content only — never the runtime.
#
# Usage:
#   ./scripts/sync-upstream.sh            # pull latest main, pin, commit (no push)
#   ./scripts/sync-upstream.sh --dry-run  # fetch + report only, change nothing
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="vendor/claude-for-legal"
REMOTE="upstream-legal"
BRANCH="main"
PIN_FILE="vendor/claude-for-legal.pin"

cd "$REPO_ROOT"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

# Refuse to run on a dirty tree — subtree pulls are a merge, and we don't want
# to lose uncommitted work behind one.
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "error: working tree is dirty. Commit or stash before syncing." >&2
  exit 1
fi

# 1. Fetch the latest upstream. Never touches the working tree.
echo "==> fetching $REMOTE $BRANCH"
git fetch "$REMOTE" "$BRANCH"

OLD_PIN=""
if [[ -f "$PIN_FILE" ]]; then
  OLD_PIN="$(cat "$PIN_FILE")"
fi
NEW_PIN="$(git rev-parse "$REMOTE/$BRANCH")"

# 2. Already current? Stop.
if [[ -n "$OLD_PIN" && "$OLD_PIN" == "$NEW_PIN" ]]; then
  echo "already up to date at $NEW_PIN"
  exit 0
fi

echo "==> syncing claude-for-legal ${OLD_PIN:-<none>} -> $NEW_PIN"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "dry-run: fetched only. No subtree pull, no pin write, no commit."
  echo "changes would land under $PREFIX"
  exit 0
fi

# 3. Pull the subtree. This creates its own squash commit.
PRE_HEAD="$(git rev-parse HEAD)"
git subtree pull --prefix="$PREFIX" "$REMOTE" "$BRANCH" --squash

# 4. Record the new pin so the next run can short-circuit.
echo "$NEW_PIN" > "$PIN_FILE"
git add "$PIN_FILE"
git commit -m "chore: bump claude-for-legal pin to $NEW_PIN" --no-verify

# 5. Report what changed inside the vendored tree.
echo
echo "==> files changed:"
git diff --stat "$PRE_HEAD" HEAD -- "$PREFIX"
echo
echo "done. Review the diff, then:"
echo "  git push origin vendor/claude-for-legal   # or merge to main via PR"
