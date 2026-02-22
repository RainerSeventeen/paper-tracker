#!/usr/bin/env bash
set -euo pipefail

# Parse flags.
DRY_RUN=0
PUBLISH_ONLY=0
CONFIG_FILE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)      DRY_RUN=1; shift ;;
    --publish-only) PUBLISH_ONLY=1; shift ;;
    --config)       CONFIG_FILE="$2"; shift 2 ;;
    --config=*)     CONFIG_FILE="${1#--config=}"; shift ;;
    *) echo "[ERROR] unknown argument: $1"; exit 1 ;;
  esac
done

test -n "$CONFIG_FILE" || { echo "[ERROR] --config <path> is required"; exit 1; }

# Single env var: project root directory.
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

# All paths derived from REPO_DIR.
PUBLISH_DIR="$REPO_DIR/site-publish"
LOG_DIR="$REPO_DIR/logs"
PT_BIN="$REPO_DIR/.venv/bin/paper-tracker"
BRANCH_MAIN="${BRANCH_MAIN:-main}"
BRANCH_PAGES="${BRANCH_PAGES:-gh-pages}"

# Resolve required external binaries once.
GIT_BIN="$(command -v git)"
RSYNC_BIN="$(command -v rsync)"
NICE_BIN="$(command -v nice)"
IONICE_BIN="$(command -v ionice)"

mkdir -p "$LOG_DIR"

# Persist all output to a timestamped log file while also printing to stdout.
LOG_FILE="$LOG_DIR/weekly_publish_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[INFO] start publish: $(date -Is)"
echo "[INFO] repo_dir=$REPO_DIR"
echo "[INFO] publish_dir=$PUBLISH_DIR"
echo "[INFO] config_file=$CONFIG_FILE"
echo "[INFO] publish_only=$PUBLISH_ONLY"
echo "[INFO] dry_run=$DRY_RUN"

cd "$REPO_DIR"
"$GIT_BIN" fetch origin
"$GIT_BIN" checkout "$BRANCH_MAIN"
"$GIT_BIN" pull --ff-only origin "$BRANCH_MAIN"

if [ "$PUBLISH_ONLY" != "1" ]; then
  # Fast-fail if runtime prerequisites are missing.
  test -x "$PT_BIN" || {
    echo "[ERROR] paper-tracker executable not found: $PT_BIN"
    exit 1
  }
  test -f "$CONFIG_FILE" || {
    echo "[ERROR] config file not found: $CONFIG_FILE"
    exit 1
  }

  # In dry-run mode, disable storage and LLM via a temporary config overlay.
  ACTIVE_CONFIG="$CONFIG_FILE"
  if [ "$DRY_RUN" = "1" ]; then
    TMP_CONFIG="$(mktemp /tmp/pt_dryrun_XXXXXX.yml)"
    trap 'rm -f "$TMP_CONFIG"' EXIT
    PYTHON_BIN="$(dirname "$PT_BIN")/python"
    "$PYTHON_BIN" -c "
import yaml, sys
with open(sys.argv[1]) as f:
    cfg = yaml.safe_load(f) or {}
cfg.setdefault('storage', {})['enabled'] = False
cfg.setdefault('llm', {})['enabled'] = False
with open(sys.argv[2], 'w') as f:
    yaml.dump(cfg, f)
" "$CONFIG_FILE" "$TMP_CONFIG"
    ACTIVE_CONFIG="$TMP_CONFIG"
    echo "[INFO] dry-run: storage and LLM disabled"
  fi

  # Run search with lower CPU/IO priority to reduce impact on shared hosts.
  "$NICE_BIN" -n 10 "$IONICE_BIN" -c2 -n7 \
    "$PT_BIN" search --config "$ACTIVE_CONFIG"
else
  echo "[INFO] publish-only: skipping search, using existing HTML files"
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

# In dry-run mode, skip all GitHub publishing steps.
if [ "$DRY_RUN" = "1" ]; then
  echo "[INFO] dry-run complete: HTML built at $REPO_DIR/site/, no GitHub push"
  exit 0
fi

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
"$GIT_BIN" -c user.name="RainerAutomation" -c user.email="rainer@automation.local" \
  commit -m "docs: weekly publish $(date +%F)"
"$GIT_BIN" push -u origin "$BRANCH_PAGES"

echo "[INFO] publish complete: $(date -Is)"
