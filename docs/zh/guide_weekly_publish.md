# weekly_publish.sh 详细说明

> 本文是自动化部署脚本的详细说明，对于快速上手请参见 scripts/README.md

## 前置要求

### 系统依赖

脚本需要以下系统工具：

```bash
git       # 版本控制
rsync     # 文件同步
nice      # CPU 优先级控制
ionice    # IO 优先级控制
```

在 Ubuntu/Debian 上安装：

```bash
sudo apt-get install git rsync util-linux coreutils
```

### 项目依赖

1. **Paper Tracker 安装完成**：
   ```bash
   cd /path/to/paper-tracker
   python -m pip install -e .
   ```

2. **配置文件准备**：
   - 创建自定义配置文件（如 `config/custom.yml`）
   - 配置 API 密钥（`.env` 文件）

3. **GitHub 仓库权限**：
   - 对仓库有推送权限
   - gh-pages 分支已创建或脚本有权限创建

---

## 参数说明

| 参数 | 说明 |
|------|------|
| `--config <path>` | **必填**。Paper Tracker 配置文件路径 |
| `--dry-run` | Dry-run 模式：关闭 LLM 与存储，输出 HTML 后退出，不推送 |
| `--publish-only` | 跳过检索，直接使用已有 HTML 文件发布 |

---

## 环境变量配置

脚本仅暴露一个必要的环境变量；其余路径全部从项目根目录推导。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `REPO_DIR` | 脚本所在目录的上一级（`scripts/../`） | 项目根目录 |
| `BRANCH_MAIN` | `main` | 主分支名称 |
| `BRANCH_PAGES` | `gh-pages` | GitHub Pages 分支名称 |

**推导路径（不可通过环境变量覆盖）：**

| 路径 | 值 |
|------|----|
| 发布 worktree | `$REPO_DIR/site-publish` |
| 日志目录 | `$REPO_DIR/logs` |
| CLI 可执行文件 | `$REPO_DIR/.venv/bin/paper-tracker` |

---

## 目录结构说明

脚本运行后会在项目目录内创建以下结构：

```
/path/to/paper-tracker/          # REPO_DIR
├── .venv/                       # Python 虚拟环境
├── config/custom.yml            # 配置文件（--config 指定）
├── output/html/                 # 生成的 HTML 文件
│   ├── search_20260210_120000.html
│   ├── search_20260203_120000.html
│   └── assets/                  # 静态资源
├── site/                        # 临时构建目录
│   ├── index.html               # 最新的搜索结果
│   ├── archive/                 # 历史搜索结果
│   ├── assets/                  # 静态资源
│   └── .nojekyll               # GitHub Pages 配置
├── site-publish/                # gh-pages 分支 worktree
│   ├── index.html
│   ├── archive/
│   ├── assets/
│   └── .nojekyll
└── logs/                        # 日志文件
    ├── weekly_publish_20260210_120000.log
    └── weekly_publish_20260203_120000.log
```

---

## 工作流程详解

### 1. 初始化阶段

```bash
# 创建日志目录
mkdir -p "$LOG_DIR"

# 创建带时间戳的日志文件
LOG_FILE="$LOG_DIR/weekly_publish_$(date +%Y%m%d_%H%M%S).log"

# 输出关键参数
echo "[INFO] repo_dir=$REPO_DIR"
echo "[INFO] config_file=$CONFIG_FILE"
```

### 2. 代码更新阶段

```bash
cd "$REPO_DIR"
git fetch origin
git checkout "$BRANCH_MAIN"
git pull --ff-only origin "$BRANCH_MAIN"
```

- 拉取最新代码
- 仅 fast-forward 合并，避免冲突

### 3. 论文检索阶段（可选）

```bash
if [ "$PUBLISH_ONLY" != "1" ]; then
  # dry-run 时生成临时配置，覆盖 storage.enabled 和 llm.enabled
  ACTIVE_CONFIG="$CONFIG_FILE"
  if [ "$DRY_RUN" = "1" ]; then
    TMP_CONFIG="$(mktemp /tmp/pt_dryrun_XXXXXX.yml)"
    python -c "..." "$CONFIG_FILE" "$TMP_CONFIG"   # 写入覆盖后的 YAML
    ACTIVE_CONFIG="$TMP_CONFIG"
  fi
  nice -n 10 ionice -c2 -n7 \
    "$PT_BIN" search --config "$ACTIVE_CONFIG"
fi
```

- 使用低优先级执行，减少对主机的影响
- `nice -n 10`: CPU 优先级降低
- `ionice -c2 -n7`: IO 优先级降低（best-effort class, priority 7）
- `--publish-only` 跳过此步骤
- `--dry-run` 时自动生成临时 YAML，将 `storage.enabled` 和 `llm.enabled` 强制设为 `false`

### 4. 站点构建阶段

```bash
rm -rf site
mkdir -p site/archive

latest="$(ls -t output/html/search_*.html 2>/dev/null | head -n 1)"

cp "$latest" site/index.html
cp -R output/html/assets site/assets
cp output/html/search_*.html site/archive/
touch site/.nojekyll
```

### 5. Dry-run 退出点

站点构建完成后，若传入 `--dry-run`，脚本直接退出，不执行任何 git 操作：

```bash
if [ "$DRY_RUN" = "1" ]; then
  echo "[INFO] dry-run complete: HTML built at $REPO_DIR/site/, no GitHub push"
  exit 0
fi
```

### 6. 发布阶段

```bash
# 确保 gh-pages worktree 存在
if [ ! -e "$PUBLISH_DIR/.git" ]; then
  if git ls-remote --exit-code --heads origin "$BRANCH_PAGES"; then
    git worktree add "$PUBLISH_DIR" "$BRANCH_PAGES"
  else
    git worktree add -b "$BRANCH_PAGES" "$PUBLISH_DIR"
  fi
fi

# 同步内容
rsync -a --delete --exclude='.git' site/ "$PUBLISH_DIR/"

cd "$PUBLISH_DIR"
git add -A

# 仅在有变更时才提交推送
if git diff --cached --quiet; then
  echo "[INFO] no site changes, skip push"
  exit 0
fi

git -c user.name="RainerAutomation" -c user.email="rainer@automation.local" \
  commit -m "docs: weekly publish $(date +%F)"
git push -u origin "$BRANCH_PAGES"
```

---

## 初次部署指南

### Step 1: 克隆仓库

```bash
git clone git@github.com:YourUsername/paper-tracker.git
cd paper-tracker
```

### Step 2: 配置 Git 凭证

**方式 1: SSH 密钥（推荐）**

```bash
ssh-keygen -t ed25519 -C "automation@local"
# 将公钥添加到 GitHub Settings -> SSH Keys
cat ~/.ssh/id_ed25519.pub
```

**方式 2: Personal Access Token (HTTPS)**

```bash
git config --global credential.helper store
# 首次推送时输入 token
# Username: YourUsername
# Password: ghp_xxxxxxxxxxxx (Personal Access Token)
```

### Step 3: 安装 Paper Tracker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env
# 编辑 .env，填入 API 密钥
```

### Step 4: 创建自定义配置

```bash
cp config/example.yml config/custom.yml
# 编辑 custom.yml，修改查询关键词等
```

### Step 5: 测试运行

```bash
# dry-run 验证配置，不推送 GitHub
./scripts/weekly_publish.sh --config config/custom.yml --dry-run

# 检查日志
tail -f logs/weekly_publish_*.log
```

### Step 6: 设置定时任务

**使用 cron：**

```bash
crontab -e
# 每周日凌晨 2 点
0 2 * * 0 /path/to/paper-tracker/scripts/weekly_publish.sh --config /path/to/paper-tracker/config/custom.yml
```

**使用 systemd（推荐）：**

相比 cron，`systemd timer` 更适合长期运行任务：可统一查看状态、日志，支持掉电后补跑（`Persistent=true`）。

1. 创建 service：

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

2. 创建 timer（示例：每周三凌晨 3 点，北京时间）：

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

3. 启用并验证：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now paper-tracker-weekly.timer
systemctl list-timers --all | grep paper-tracker
```

4. 手动触发一次验证：

```bash
sudo systemctl start paper-tracker-weekly.service
systemctl status paper-tracker-weekly.service -l --no-pager
journalctl -u paper-tracker-weekly.service -n 200 --no-pager
```

### Step 7: 配置 GitHub Pages

1. 访问仓库 Settings -> Pages
2. Source 选择 `gh-pages` 分支
3. 保存配置

等待几分钟后，访问 `https://YourUsername.github.io/paper-tracker/`

---

## 故障排查

### 问题 1: 未找到 HTML 文件

**症状：**
```
[ERROR] no HTML files found under output/html/search_*.html
```

**原因：**
- 首次运行且使用了 `--publish-only`
- 检索失败未生成 HTML

**解决方案：**
```bash
cd /path/to/paper-tracker
source .venv/bin/activate
paper-tracker search --config config/custom.yml

ls -la output/html/
```

### 问题 2: Git 推送失败

**症状：**
```
fatal: could not read Username for 'https://github.com'
Permission denied (publickey)
```

**SSH 方式：**
```bash
ssh -T git@github.com
git remote set-url origin git@github.com:YourUsername/paper-tracker.git
```

**HTTPS 方式：**
```bash
git config credential.helper store
cd /path/to/paper-tracker/site-publish
git push origin gh-pages
```

### 问题 3: 权限错误

```bash
chmod +x /path/to/paper-tracker/scripts/weekly_publish.sh
```

### 问题 4: Worktree 错误

**症状：**
```
fatal: 'site-publish' already exists
```

```bash
cd /path/to/paper-tracker
git worktree list
git worktree remove site-publish --force
./scripts/weekly_publish.sh --config config/custom.yml
```

### 问题 5: systemd 报错 `status=203/EXEC`

**原因：** `ExecStart` 路径错误，或脚本没有执行权限。

```bash
ls -l /path/to/paper-tracker/scripts/weekly_publish.sh
chmod +x /path/to/paper-tracker/scripts/weekly_publish.sh
sudo systemctl daemon-reload
sudo systemctl start paper-tracker-weekly.service
```

---

## 日志管理

日志文件位于 `$REPO_DIR/logs/`，命名格式为 `weekly_publish_YYYYMMDD_HHMMSS.log`。

```bash
# 查看最新日志
tail -f /path/to/paper-tracker/logs/weekly_publish_*.log

# 搜索错误
grep -r "ERROR" /path/to/paper-tracker/logs/

# 删除 30 天前的日志
find /path/to/paper-tracker/logs/ -name "weekly_publish_*.log" -mtime +30 -delete
```

---

## 高级配置

### 多配置部署

同一台机器运行多个关键词配置：

```bash
# 机器学习论文
./scripts/weekly_publish.sh --config config/ml.yml

# 计算机视觉论文
./scripts/weekly_publish.sh --config config/cv.yml
```

### 发布到自定义域名

```bash
echo "papers.example.com" > /path/to/paper-tracker/site-publish/CNAME
git -C /path/to/paper-tracker/site-publish add CNAME
git -C /path/to/paper-tracker/site-publish commit -m "docs: add custom domain"
git -C /path/to/paper-tracker/site-publish push
```

在 DNS 设置中添加 CNAME 记录指向 `YourUsername.github.io`。

---

## 安全注意事项

1. **保护敏感信息**：`.env` 文件不要提交到 Git，日志文件不要包含 API 密钥
2. **最小权限原则**：使用专门的自动化用户运行，限制 GitHub Token 权限（仅 `repo` 范围）
3. **定期更新**：定期更新依赖包，监控 GitHub 安全告警
4. **备份**：定期备份配置文件，保留关键日志文件
