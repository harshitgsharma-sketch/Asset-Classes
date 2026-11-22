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
  # The daily refresh Action rewrites data/*.json on GitHub. If those generated files are
  # the only conflicts, keep GitHub's copy (the next daily run rebuilds them) and go on.
  # Any other conflict: abort and push nothing.
  while [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; do
    conflicts="$(git diff --name-only --diff-filter=U)"
    if [ -z "$conflicts" ]; then
      GIT_EDITOR=true git rebase --continue >/dev/null 2>&1 || break
      continue
    fi
    if echo "$conflicts" | grep -qv '^data/.*\.json$'; then
      echo "conflict outside data/ ($(echo $conflicts | tr '\n' ' ')); aborting, nothing pushed"
      git rebase --abort; exit 1
    fi
    echo "conflict only in generated files ($(echo $conflicts | tr '\n' ' ')); keeping GitHub's copy"
    git checkout --ours -- $conflicts && git add -- $conflicts
    GIT_EDITOR=true git rebase --continue >/dev/null 2>&1 || true
  done
  if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
    echo "rebase did not finish; aborting, nothing pushed"; git rebase --abort; exit 1
  fi
fi

ahead="$(git rev-list --count origin/main..HEAD)"
if [ "$ahead" = "0" ]; then echo "nothing to push"; exit 0; fi
if git push -q origin main; then echo "pushed $ahead commit(s)"; else echo "push failed (check GitHub sign-in on this Mac)"; exit 1; fi
