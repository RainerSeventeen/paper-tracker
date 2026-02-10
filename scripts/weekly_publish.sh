#!/usr/bin/env bash
set -euo pipefail

# Directory and branch defaults; every value can be overridden via env vars.
BASE_DIR="${BASE_DIR:-/home/automation/github_auto}"
REPO_DIR="${REPO_DIR:-$BASE_DIR/paper-tracker}"
PUBLISH_DIR="${PUBLISH_DIR:-$BASE_DIR/publish}"
STATE_DIR="${STATE_DIR:-$BASE_DIR/state}"
LOG_DIR="${LOG_DIR:-$BASE_DIR/logs}"
LOCK_FILE="${LOCK_FILE:-$BASE_DIR/weekly_publish.lock}"
BRANCH_MAIN="${BRANCH_MAIN:-main}"
BRANCH_PAGES="${BRANCH_PAGES:-gh-pages}"
SKIP_SEARCH="${SKIP_SEARCH:-0}"

CONFIG_FILE="${CONFIG_FILE:-$REPO_DIR/config/custom.yml}"
PT_BIN="${PT_BIN:-$REPO_DIR/.venv/bin/paper-tracker}"

# Resolve required external binaries once.
GIT_BIN="$(command -v git)"
RSYNC_BIN="$(command -v rsync)"
FLOCK_BIN="$(command -v flock)"
NICE_BIN="$(command -v nice)"
IONICE_BIN="$(command -v ionice)"

mkdir -p "$STATE_DIR" "$LOG_DIR"

# Prevent concurrent runs: exit if another publisher already holds the lock.
exec 9>"$LOCK_FILE"
"$FLOCK_BIN" -n 9 || {
  echo "[WARN] another publish job is running"
  exit 1
}

# Persist all output to a timestamped log file while also printing to stdout.
LOG_FILE="$LOG_DIR/weekly_publish_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[INFO] start publish: $(date -Is)"
echo "[INFO] repo_dir=$REPO_DIR"
echo "[INFO] publish_dir=$PUBLISH_DIR"
echo "[INFO] config_file=$CONFIG_FILE"
echo "[INFO] skip_search=$SKIP_SEARCH"

cd "$REPO_DIR"
"$GIT_BIN" fetch origin
"$GIT_BIN" checkout "$BRANCH_MAIN"
"$GIT_BIN" pull --ff-only origin "$BRANCH_MAIN"

if [ "$SKIP_SEARCH" != "1" ]; then
  # Fast-fail if runtime prerequisites are missing.
  test -x "$PT_BIN" || {
    echo "[ERROR] paper-tracker executable not found: $PT_BIN"
    exit 1
  }
  test -f "$CONFIG_FILE" || {
    echo "[ERROR] config file not found: $CONFIG_FILE"
    exit 1
  }

  # Run search with lower CPU/IO priority to reduce impact on shared hosts.
  "$NICE_BIN" -n 10 "$IONICE_BIN" -c2 -n7 \
    "$PT_BIN" search --config "$CONFIG_FILE"
else
  echo "[INFO] skip search, publish existing HTML files only"
fi

# Build deployable site directory from generated HTML artifacts.
rm -rf site
mkdir -p site/archive

latest="$(ls -t output/html/search_*.html 2>/dev/null | head -n 1 || true)"
test -n "$latest" || {
  echo "[ERROR] no HTML files found under output/html/search_*.html"
  exit 1
}

cp "$latest" site/index.html
if [ -d output/html/assets ]; then
  cp -R output/html/assets site/assets
fi
cp output/html/search_*.html site/archive/
# Ensure GitHub Pages serves files as plain static content (no Jekyll processing).
touch site/.nojekyll

# Ensure publish worktree exists.
# If remote gh-pages exists, attach it; otherwise create a new local branch.
if [ ! -e "$PUBLISH_DIR/.git" ]; then
  if "$GIT_BIN" ls-remote --exit-code --heads origin "$BRANCH_PAGES" >/dev/null 2>&1; then
    "$GIT_BIN" worktree add "$PUBLISH_DIR" "$BRANCH_PAGES"
  else
    "$GIT_BIN" worktree add -b "$BRANCH_PAGES" "$PUBLISH_DIR"
  fi
fi

# Mirror site contents into publish worktree; delete stale files on destination.
"$RSYNC_BIN" -a --delete --exclude='.git' site/ "$PUBLISH_DIR/"

cd "$PUBLISH_DIR"
"$GIT_BIN" add -A
# Skip commit/push when generated output is unchanged.
if "$GIT_BIN" diff --cached --quiet; then
  echo "[INFO] no site changes, skip push"
  exit 0
fi

# Commit as automation identity and publish branch upstream.
"$GIT_BIN" -c user.name="automation-bot" -c user.email="automation@local" \
  commit -m "docs: weekly publish $(date +%F)"
"$GIT_BIN" push -u origin "$BRANCH_PAGES"

echo "[INFO] publish complete: $(date -Is)"
