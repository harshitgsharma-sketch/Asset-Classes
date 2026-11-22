#!/bin/bash
# Weekly push of local work to GitHub.
# 1. Commits any changes inside knowledge/ (new or edited notes).
# 2. Rebases onto origin/main (the daily refresh Action commits there too).
# 3. Pushes every local commit on main.
# Run by the launchd agent com.assetclasses.weekly-push (Sundays 19:00), or by hand:
#   bash scripts/weekly_knowledge_push.sh
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$HOME/Library/Logs/asset-classes-weekly-push.log"
mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S') weekly push ==="
cd "$REPO" || { echo "repo not found: $REPO"; exit 1; }
export GIT_TERMINAL_PROMPT=0

branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$branch" != "main" ]; then echo "on branch $branch, not main; skipping"; exit 0; fi

if [ -n "$(git status --porcelain -- knowledge)" ]; then
  git add -A knowledge
  git commit -q -m "Knowledge: weekly update $(date '+%Y-%m-%d')" && echo "committed knowledge changes"
fi

if ! git pull -q --rebase --autostash origin main; then
  echo "pull/rebase failed; aborting so nothing is pushed half-merged"
  git rebase --abort 2>/dev/null
  exit 1
fi

ahead="$(git rev-list --count origin/main..HEAD)"
if [ "$ahead" = "0" ]; then echo "nothing to push"; exit 0; fi
if git push -q origin main; then echo "pushed $ahead commit(s)"; else echo "push failed (check GitHub sign-in on this Mac)"; exit 1; fi
