# Detailed Guide to weekly_publish.sh

> The following content was translated using a large language model (LLM)

> This document provides detailed instructions for the automated deployment script. For quick start, see scripts/README.md.

## Prerequisites

### System Dependencies

The script requires the following system tools:

```bash
git       # Version control
rsync     # File synchronization
nice      # CPU priority control
ionice    # IO priority control
```

Install on Ubuntu/Debian:

```bash
sudo apt-get install git rsync util-linux coreutils
```

### Project Dependencies

1. **Paper Tracker is installed**:
   ```bash
   cd /path/to/paper-tracker
   python -m pip install -e .
   ```

2. **Configuration files are ready**:
   - Create a custom config file (for example, `config/custom.yml`)
   - Configure API keys (in the `.env` file)

3. **GitHub repository permissions**:
   - Push permission to the repository
   - The `gh-pages` branch already exists, or the script has permission to create it

---

## Parameter Reference

| Parameter | Description |
|------|------|
| `--config <path>` | **Required**. Path to the Paper Tracker config file |
| `--dry-run` | Dry-run mode: disable LLM and storage, output HTML and exit, no push |
| `--publish-only` | Skip retrieval and publish directly using existing HTML files |

---

## Environment Variable Configuration

The script exposes only one necessary environment variable; all other paths are derived from the project root.

| Variable | Default | Description |
|------|--------|------|
| `REPO_DIR` | Parent directory of the script location (`scripts/../`) | Project root directory |
| `BRANCH_MAIN` | `main` | Main branch name |
| `BRANCH_PAGES` | `gh-pages` | GitHub Pages branch name |

**Derived paths (cannot be overridden by environment variables):**

| Path | Value |
|------|----|
| Publish worktree | `$REPO_DIR/site-publish` |
| Log directory | `$REPO_DIR/logs` |
| CLI executable | `$REPO_DIR/.venv/bin/paper-tracker` |

---

## Directory Structure

After running the script, the following structure will be created in the project directory:

```
/path/to/paper-tracker/          # REPO_DIR
├── .venv/                       # Python virtual environment
├── config/custom.yml            # Config file (specified by --config)
├── output/html/                 # Generated HTML files
│   ├── search_20260210_120000.html
│   ├── search_20260203_120000.html
│   └── assets/                  # Static assets
├── site/                        # Temporary build directory
│   ├── index.html               # Latest search result
│   ├── archive/                 # Historical search results
│   ├── assets/                  # Static assets
│   └── .nojekyll               # GitHub Pages config
├── site-publish/                # gh-pages branch worktree
│   ├── index.html
│   ├── archive/
│   ├── assets/
│   └── .nojekyll
└── logs/                        # Log files
    ├── weekly_publish_20260210_120000.log
    └── weekly_publish_20260203_120000.log
```

---

## Workflow Details

### 1. Initialization Phase

```bash
# Create log directory
mkdir -p "$LOG_DIR"

# Create timestamped log file
LOG_FILE="$LOG_DIR/weekly_publish_$(date +%Y%m%d_%H%M%S).log"

# Output key parameters
echo "[INFO] repo_dir=$REPO_DIR"
echo "[INFO] config_file=$CONFIG_FILE"
```

### 2. Code Update Phase

```bash
cd "$REPO_DIR"
git fetch origin
git checkout "$BRANCH_MAIN"
git pull --ff-only origin "$BRANCH_MAIN"
```

- Pull the latest code
- Fast-forward only, to avoid merge conflicts

### 3. Paper Retrieval Phase (Optional)

```bash
if [ "$PUBLISH_ONLY" != "1" ]; then
  # In dry-run, generate a temporary config overriding storage.enabled and llm.enabled
  ACTIVE_CONFIG="$CONFIG_FILE"
  if [ "$DRY_RUN" = "1" ]; then
    TMP_CONFIG="$(mktemp /tmp/pt_dryrun_XXXXXX.yml)"
    python -c "..." "$CONFIG_FILE" "$TMP_CONFIG"   # Write overridden YAML
    ACTIVE_CONFIG="$TMP_CONFIG"
  fi
  nice -n 10 ionice -c2 -n7 \
    "$PT_BIN" search --config "$ACTIVE_CONFIG"
fi
```

- Runs at low priority to reduce host impact
- `nice -n 10`: lower CPU priority
- `ionice -c2 -n7`: lower IO priority (best-effort class, priority 7)
- `--publish-only` skips this step
- In `--dry-run`, a temporary YAML is generated and forces `storage.enabled` and `llm.enabled` to `false`

### 4. Site Build Phase

```bash
rm -rf site
mkdir -p site/archive

latest="$(ls -t output/html/search_*.html 2>/dev/null | head -n 1)"

cp "$latest" site/index.html
cp -R output/html/assets site/assets
cp output/html/search_*.html site/archive/
touch site/.nojekyll
```

### 5. Dry-run Exit Point

After site build, if `--dry-run` is passed, the script exits directly and performs no git operations:

```bash
if [ "$DRY_RUN" = "1" ]; then
  echo "[INFO] dry-run complete: HTML built at $REPO_DIR/site/, no GitHub push"
  exit 0
fi
```

### 6. Publish Phase

```bash
# Ensure gh-pages worktree exists
if [ ! -e "$PUBLISH_DIR/.git" ]; then
  if git ls-remote --exit-code --heads origin "$BRANCH_PAGES"; then
    git worktree add "$PUBLISH_DIR" "$BRANCH_PAGES"
  else
    git worktree add -b "$BRANCH_PAGES" "$PUBLISH_DIR"
  fi
fi

# Sync content
rsync -a --delete --exclude='.git' site/ "$PUBLISH_DIR/"

cd "$PUBLISH_DIR"
git add -A

# Commit and push only when there are changes
if git diff --cached --quiet; then
  echo "[INFO] no site changes, skip push"
  exit 0
fi

git -c user.name="RainerAutomation" -c user.email="rainer@automation.local" \
  commit -m "docs: weekly publish $(date +%F)"
git push -u origin "$BRANCH_PAGES"
```

---

## First Deployment Guide

### Step 1: Clone the repository

```bash
git clone git@github.com:YourUsername/paper-tracker.git
cd paper-tracker
```

### Step 2: Configure Git credentials

**Method 1: SSH key (recommended)**

```bash
ssh-keygen -t ed25519 -C "automation@local"
# Add the public key to GitHub Settings -> SSH Keys
cat ~/.ssh/id_ed25519.pub
```

**Method 2: Personal Access Token (HTTPS)**

```bash
git config --global credential.helper store
# Enter token when pushing for the first time
# Username: YourUsername
# Password: ghp_xxxxxxxxxxxx (Personal Access Token)
```

### Step 3: Install Paper Tracker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env
# Edit .env and fill in API keys
```

### Step 4: Create a custom configuration

```bash
cp config/example.yml config/custom.yml
# Edit custom.yml, update query keywords, etc.
```

### Step 5: Test run

```bash
# Validate config with dry-run, no GitHub push
./scripts/weekly_publish.sh --config config/custom.yml --dry-run

# Check logs
tail -f logs/weekly_publish_*.log
```

### Step 6: Set up scheduled tasks

**Using cron:**

```bash
crontab -e
# Every Sunday at 2:00 AM
0 2 * * 0 /path/to/paper-tracker/scripts/weekly_publish.sh --config /path/to/paper-tracker/config/custom.yml
```

**Using systemd (recommended):**

Compared with cron, `systemd timer` is better for long-running scheduled tasks: centralized status/log viewing and catch-up execution after downtime (`Persistent=true`).

1. Create the service:

```bash
sudo tee /etc/systemd/system/paper-tracker-weekly.service >/dev/null <<'EOF'
[Unit]
Description=Paper Tracker weekly publish job
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=automation
Group=automation
WorkingDirectory=/path/to/paper-tracker
ExecStart=/path/to/paper-tracker/scripts/weekly_publish.sh --config /path/to/paper-tracker/config/custom.yml
EOF
```

2. Create the timer (example: every Wednesday at 3:00 AM, Beijing time):

```bash
sudo tee /etc/systemd/system/paper-tracker-weekly.timer >/dev/null <<'EOF'
[Unit]
Description=Run Paper Tracker weekly publish on schedule

[Timer]
OnCalendar=Wed *-*-* 03:00:00
Timezone=Asia/Shanghai
Persistent=true
Unit=paper-tracker-weekly.service

[Install]
WantedBy=timers.target
EOF
```

3. Enable and verify:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now paper-tracker-weekly.timer
systemctl list-timers --all | grep paper-tracker
```

4. Manually trigger once for verification:

```bash
sudo systemctl start paper-tracker-weekly.service
systemctl status paper-tracker-weekly.service -l --no-pager
journalctl -u paper-tracker-weekly.service -n 200 --no-pager
```

### Step 7: Configure GitHub Pages

1. Go to repository Settings -> Pages
2. Set Source to the `gh-pages` branch
3. Save

After a few minutes, visit `https://YourUsername.github.io/paper-tracker/`

---

## Troubleshooting

### Issue 1: HTML file not found

**Symptom:**
```
[ERROR] no HTML files found under output/html/search_*.html
```

**Cause:**
- First run with `--publish-only`
- Retrieval failed and no HTML was generated

**Solution:**
```bash
cd /path/to/paper-tracker
source .venv/bin/activate
paper-tracker search --config config/custom.yml

ls -la output/html/
```

### Issue 2: Git push failed

**Symptom:**
```
fatal: could not read Username for 'https://github.com'
Permission denied (publickey)
```

**SSH approach:**
```bash
ssh -T git@github.com
git remote set-url origin git@github.com:YourUsername/paper-tracker.git
```

**HTTPS approach:**
```bash
git config credential.helper store
cd /path/to/paper-tracker/site-publish
git push origin gh-pages
```

### Issue 3: Permission error

```bash
chmod +x /path/to/paper-tracker/scripts/weekly_publish.sh
```

### Issue 4: Worktree error

**Symptom:**
```
fatal: 'site-publish' already exists
```

```bash
cd /path/to/paper-tracker
git worktree list
git worktree remove site-publish --force
./scripts/weekly_publish.sh --config config/custom.yml
```

### Issue 5: systemd error `status=203/EXEC`

**Cause:** `ExecStart` path is wrong, or the script is not executable.

```bash
ls -l /path/to/paper-tracker/scripts/weekly_publish.sh
chmod +x /path/to/paper-tracker/scripts/weekly_publish.sh
sudo systemctl daemon-reload
sudo systemctl start paper-tracker-weekly.service
```

---

## Log Management

Log files are located in `$REPO_DIR/logs/`, with naming format `weekly_publish_YYYYMMDD_HHMMSS.log`.

```bash
# View latest logs
tail -f /path/to/paper-tracker/logs/weekly_publish_*.log

# Search errors
grep -r "ERROR" /path/to/paper-tracker/logs/

# Delete logs older than 30 days
find /path/to/paper-tracker/logs/ -name "weekly_publish_*.log" -mtime +30 -delete
```

---

## Advanced Configuration

### Multi-configuration deployment

Run multiple keyword configurations on the same machine:

```bash
# Machine learning papers
./scripts/weekly_publish.sh --config config/ml.yml

# Computer vision papers
./scripts/weekly_publish.sh --config config/cv.yml
```

### Publish to a custom domain

```bash
echo "papers.example.com" > /path/to/paper-tracker/site-publish/CNAME
git -C /path/to/paper-tracker/site-publish add CNAME
git -C /path/to/paper-tracker/site-publish commit -m "docs: add custom domain"
git -C /path/to/paper-tracker/site-publish push
```

Add a CNAME record in DNS settings pointing to `YourUsername.github.io`.

---

## Security Notes

1. **Protect sensitive information**: Do not commit `.env` to Git, and logs must not contain API keys
2. **Principle of least privilege**: Run with a dedicated automation user, and limit GitHub Token scope (only `repo`)
3. **Regular updates**: Update dependencies regularly and monitor GitHub security alerts
4. **Backups**: Regularly back up config files and keep key log files
