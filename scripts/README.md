# Weekly Publish Script - 自动化发布脚本

## 概述

`weekly_publish.sh` 是一个自动化脚本，用于定期执行论文检索并将生成的 HTML 报告发布到 GitHub Pages。

**核心功能：**
- 自动拉取最新代码
- 执行论文检索（可选）
- 构建静态站点
- 发布到 GitHub Pages (gh-pages 分支)
- 防止并发执行
- 完整的日志记录

---

## 前置要求

### 系统依赖

脚本需要以下系统工具：

```bash
git       # 版本控制
rsync     # 文件同步
flock     # 文件锁，防止并发
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

## 环境变量配置

所有配置项都可以通过环境变量覆盖默认值：

### 目录配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BASE_DIR` | `/home/automation/github_auto` | 基础工作目录 |
| `REPO_DIR` | `$BASE_DIR/paper-tracker` | 仓库克隆目录 |
| `PUBLISH_DIR` | `$BASE_DIR/publish` | gh-pages 分支工作树目录 |
| `STATE_DIR` | `$BASE_DIR/state` | 状态文件目录 |
| `LOG_DIR` | `$BASE_DIR/logs` | 日志文件目录 |
| `LOCK_FILE` | `$BASE_DIR/weekly_publish.lock` | 锁文件路径 |

### 仓库配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BRANCH_MAIN` | `main` | 主分支名称 |
| `BRANCH_PAGES` | `gh-pages` | GitHub Pages 分支名称 |

### 应用配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CONFIG_FILE` | `$REPO_DIR/config/custom.yml` | Paper Tracker 配置文件路径 |
| `PT_BIN` | `$REPO_DIR/.venv/bin/paper-tracker` | Paper Tracker 可执行文件路径 |
| `SKIP_SEARCH` | `0` | 跳过检索，仅发布现有 HTML（`1` 为跳过） |

---

## 目录结构说明

脚本运行后会创建以下目录结构：

```
/home/automation/github_auto/          # BASE_DIR
├── paper-tracker/                     # REPO_DIR (主仓库工作目录)
│   ├── .venv/                        # Python 虚拟环境
│   ├── config/custom.yml             # 配置文件
│   ├── output/html/                  # 生成的 HTML 文件
│   │   ├── search_20260210_120000.html
│   │   ├── search_20260203_120000.html
│   │   └── assets/                   # 静态资源
│   └── site/                         # 临时构建目录
│       ├── index.html               # 最新的搜索结果
│       ├── archive/                 # 历史搜索结果
│       ├── assets/                  # 静态资源
│       └── .nojekyll               # GitHub Pages 配置
├── publish/                          # PUBLISH_DIR (gh-pages 分支工作树)
│   ├── index.html
│   ├── archive/
│   ├── assets/
│   └── .nojekyll
├── state/                            # STATE_DIR (可用于存储状态)
├── logs/                             # LOG_DIR (日志文件)
│   ├── weekly_publish_20260210_120000.log
│   └── weekly_publish_20260203_120000.log
└── weekly_publish.lock               # LOCK_FILE (进程锁)
```

---

## 使用方法

### 基本使用

**1. 直接运行（使用默认配置）：**

```bash
./scripts/weekly_publish.sh
```

**2. 自定义配置运行：**

```bash
# 使用不同的基础目录
BASE_DIR=/opt/automation ./scripts/weekly_publish.sh

# 跳过检索，仅发布现有 HTML
SKIP_SEARCH=1 ./scripts/weekly_publish.sh

# 使用不同的配置文件
CONFIG_FILE=/path/to/my-config.yml ./scripts/weekly_publish.sh
```

**3. 组合多个环境变量：**

```bash
BASE_DIR=/opt/automation \
SKIP_SEARCH=1 \
BRANCH_MAIN=develop \
./scripts/weekly_publish.sh
```

### 设置 Cron 定时任务

**每周日凌晨 2 点运行：**

```bash
# 编辑 crontab
crontab -e

# 添加以下行（假设用户为 automation）
0 2 * * 0 /home/automation/github_auto/paper-tracker/scripts/weekly_publish.sh >> /home/automation/github_auto/logs/cron.log 2>&1
```

**使用环境变量的 cron 配置：**

```bash
# 在 crontab 顶部设置环境变量
BASE_DIR=/opt/automation
SKIP_SEARCH=0

# 定时任务
0 2 * * 0 $BASE_DIR/paper-tracker/scripts/weekly_publish.sh
```

**推荐的 cron 配置（完整示例）：**

```bash
# 环境变量
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
BASE_DIR=/home/automation/github_auto

# 每周日凌晨 2 点运行
0 2 * * 0 $BASE_DIR/paper-tracker/scripts/weekly_publish.sh

# 或者每天运行
0 2 * * * $BASE_DIR/paper-tracker/scripts/weekly_publish.sh
```

### 使用 systemd 定时（推荐）

相比 cron，`systemd timer` 更适合长期运行任务：可统一查看状态、日志，支持掉电后补跑（`Persistent=true`）。

**1. 创建环境变量文件（可选但推荐）：**

```bash
cat > /home/automation/github_auto/paper-tracker/.env.publish <<'EOF'
BASE_DIR=/home/automation/github_auto
REPO_DIR=/home/automation/github_auto/paper-tracker
PUBLISH_DIR=/home/automation/github_auto/publish
STATE_DIR=/home/automation/github_auto/state
LOG_DIR=/home/automation/github_auto/logs
BRANCH_MAIN=main
BRANCH_PAGES=gh-pages
SKIP_SEARCH=0
CONFIG_FILE=/home/automation/github_auto/paper-tracker/config/custom.yml
PT_BIN=/home/automation/github_auto/paper-tracker/.venv/bin/paper-tracker
EOF
```

**2. 创建 service：**

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
WorkingDirectory=/home/automation/github_auto/paper-tracker
EnvironmentFile=-/home/automation/github_auto/paper-tracker/.env.publish
ExecStart=/home/automation/github_auto/paper-tracker/scripts/weekly_publish.sh
EOF
```

说明：`EnvironmentFile` 前面的 `-` 表示该文件缺失时不阻塞启动（脚本会使用默认值）。

**3. 创建 timer（示例：每周三凌晨 3 点，北京时间）：**

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

**4. 启用并验证：**

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now paper-tracker-weekly.timer
systemctl list-timers --all | grep paper-tracker
```

**5. 手动触发一次验证：**

```bash
sudo systemctl start paper-tracker-weekly.service
systemctl status paper-tracker-weekly.service -l --no-pager
journalctl -u paper-tracker-weekly.service -n 200 --no-pager
```

---

## 工作流程详解

脚本执行流程如下：

### 1. 初始化阶段

```bash
# 创建必要的目录
mkdir -p "$STATE_DIR" "$LOG_DIR"

# 获取进程锁，防止并发执行
flock -n 9 || exit 1

# 创建带时间戳的日志文件
LOG_FILE="$LOG_DIR/weekly_publish_$(date +%Y%m%d_%H%M%S).log"
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
if [ "$SKIP_SEARCH" != "1" ]; then
  nice -n 10 ionice -c2 -n7 \
    "$PT_BIN" search --config "$CONFIG_FILE"
fi
```

- 使用低优先级执行，减少对主机的影响
- `nice -n 10`: CPU 优先级降低
- `ionice -c2 -n7`: IO 优先级降低（best-effort class, priority 7）
- 可通过 `SKIP_SEARCH=1` 跳过此步骤

### 4. 站点构建阶段

```bash
# 清理旧的构建目录
rm -rf site
mkdir -p site/archive

# 找到最新的 HTML 文件
latest="$(ls -t output/html/search_*.html 2>/dev/null | head -n 1)"

# 复制文件到 site 目录
cp "$latest" site/index.html                  # 最新结果作为首页
cp -R output/html/assets site/assets          # 静态资源
cp output/html/search_*.html site/archive/    # 所有历史结果

# 创建 .nojekyll 文件，禁用 Jekyll 处理
touch site/.nojekyll
```

### 5. 发布准备阶段

```bash
# 如果 publish 目录不存在，创建 git worktree
if [ ! -e "$PUBLISH_DIR/.git" ]; then
  # 如果远程 gh-pages 分支存在，附加到它
  if git ls-remote --exit-code --heads origin "$BRANCH_PAGES"; then
    git worktree add "$PUBLISH_DIR" "$BRANCH_PAGES"
  else
    # 否则创建新的本地分支
    git worktree add -b "$BRANCH_PAGES" "$PUBLISH_DIR"
  fi
fi
```

- 使用 `git worktree` 管理 gh-pages 分支
- 首次运行会自动创建或连接到远程分支

### 6. 内容同步阶段

```bash
# 使用 rsync 同步内容
rsync -a --delete --exclude='.git' site/ "$PUBLISH_DIR/"
```

- `-a`: 归档模式，保留权限和时间戳
- `--delete`: 删除目标目录中多余的文件
- `--exclude='.git'`: 不删除 .git 目录

### 7. 提交推送阶段

```bash
cd "$PUBLISH_DIR"
git add -A

# 检查是否有变更
if git diff --cached --quiet; then
  echo "no site changes, skip push"
  exit 0
fi

# 提交并推送
git -c user.name="automation-bot" -c user.email="automation@local" \
  commit -m "docs: weekly publish $(date +%F)"
git push -u origin "$BRANCH_PAGES"
```

- 仅在有变更时才提交推送
- 使用自动化身份提交

---

## 初次部署指南

### Step 1: 准备服务器环境

```bash
# 创建自动化用户（可选）
sudo useradd -m -s /bin/bash automation

# 切换到自动化用户
sudo su - automation

# 创建基础目录
mkdir -p /home/automation/github_auto
cd /home/automation/github_auto
```

### Step 2: 克隆仓库

```bash
# 克隆仓库（使用 SSH 或 HTTPS）
git clone git@github.com:YourUsername/paper-tracker.git
cd paper-tracker
```

### Step 3: 配置 Git 凭证

**方式 1: SSH 密钥（推荐）**

```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "automation@local"

# 将公钥添加到 GitHub
cat ~/.ssh/id_ed25519.pub
# 复制输出，添加到 GitHub Settings -> SSH Keys
```

**方式 2: Personal Access Token (HTTPS)**

```bash
# 配置 Git credential helper
git config --global credential.helper store

# 首次推送时输入 token
# Username: YourUsername
# Password: ghp_xxxxxxxxxxxx (Personal Access Token)
```

### Step 4: 安装 Paper Tracker

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e .

# 配置环境变量
cp .env.example .env
nano .env  # 编辑填入 API 密钥
```

### Step 5: 创建自定义配置

```bash
# 复制并修改配置文件
cp config/default.yml config/custom.yml
nano config/custom.yml  # 修改查询关键词等
```

### Step 6: 测试运行

```bash
# 手动运行一次，验证配置
./scripts/weekly_publish.sh

# 检查日志
tail -f logs/weekly_publish_*.log
```

### Step 7: 设置定时任务（cron 或 systemd）

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每周日凌晨 2 点）
0 2 * * 0 /home/automation/github_auto/paper-tracker/scripts/weekly_publish.sh
```

或者按上文《使用 systemd 定时（推荐）》创建 `paper-tracker-weekly.service` 和 `paper-tracker-weekly.timer`。

### Step 8: 配置 GitHub Pages

1. 访问仓库 Settings -> Pages
2. Source 选择 `gh-pages` 分支
3. 保存配置

等待几分钟后，访问 `https://YourUsername.github.io/paper-tracker/`

---

## 故障排查

### 问题 1: 锁文件错误

**症状：**
```
[WARN] another publish job is running
```

**原因：** 上一次运行未正常结束，锁文件未释放

**解决方案：**
```bash
# 检查是否有进程在运行
ps aux | grep weekly_publish

# 如果没有进程，删除锁文件
rm /home/automation/github_auto/weekly_publish.lock
```

### 问题 2: 未找到 HTML 文件

**症状：**
```
[ERROR] no HTML files found under output/html/search_*.html
```

**原因：**
- 首次运行且 `SKIP_SEARCH=1`
- 检索失败未生成 HTML

**解决方案：**
```bash
# 手动运行一次检索
cd /home/automation/github_auto/paper-tracker
source .venv/bin/activate
paper-tracker search --config config/custom.yml

# 检查输出目录
ls -la output/html/
```

### 问题 3: Git 推送失败

**症状：**
```
fatal: could not read Username for 'https://github.com'
Permission denied (publickey)
```

**原因：** Git 凭证配置问题

**解决方案：**

**SSH 方式：**
```bash
# 检查 SSH 密钥
ssh -T git@github.com

# 修改仓库 URL 为 SSH
git remote set-url origin git@github.com:YourUsername/paper-tracker.git
```

**HTTPS 方式：**
```bash
# 配置 credential helper
git config credential.helper store

# 手动推送一次，输入 token
cd /home/automation/github_auto/publish
git push origin gh-pages
```

### 问题 4: 权限错误

**症状：**
```
Permission denied
```

**解决方案：**
```bash
# 检查文件所有权
ls -la /home/automation/github_auto/

# 修复权限
sudo chown -R automation:automation /home/automation/github_auto/

# 确保脚本可执行
chmod +x scripts/weekly_publish.sh
```

### 问题 5: Worktree 错误

**症状：**
```
fatal: 'publish' already exists
```

**原因：** publish 目录状态异常

**解决方案：**
```bash
cd /home/automation/github_auto/paper-tracker

# 列出所有 worktree
git worktree list

# 删除异常的 worktree
git worktree remove publish --force

# 重新运行脚本
./scripts/weekly_publish.sh
```

### 问题 6: Cron 任务不执行

**症状：** 定时任务没有运行

**检查步骤：**

```bash
# 1. 检查 cron 服务状态
sudo systemctl status cron

# 2. 检查 crontab 配置
crontab -l

# 3. 检查 cron 日志
sudo tail -f /var/log/syslog | grep CRON

# 4. 手动运行脚本测试
/home/automation/github_auto/paper-tracker/scripts/weekly_publish.sh

# 5. 检查环境变量
# 在 crontab 顶部添加：
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
```

### 问题 7: systemd 报错 `Failed to load environment files`

**症状：**
```
Failed to load environment files: No such file or directory
```

**原因：** `EnvironmentFile=` 指向的文件不存在。

**解决方案：**
```bash
# 方案 1：创建环境变量文件
ls -l /home/automation/github_auto/paper-tracker/.env.publish

# 方案 2：允许缺失（推荐在 service 使用）
# EnvironmentFile=-/home/automation/github_auto/paper-tracker/.env.publish

sudo systemctl daemon-reload
sudo systemctl restart paper-tracker-weekly.timer
```

### 问题 8: systemd 报错 `status=203/EXEC`

**症状：**
```
Failed at step EXEC
... status=203/EXEC
```

**原因：** `ExecStart` 路径错误，或脚本没有执行权限。

**解决方案：**
```bash
# 检查脚本路径
ls -l /home/automation/github_auto/paper-tracker/scripts/weekly_publish.sh

# 添加执行权限
chmod +x /home/automation/github_auto/paper-tracker/scripts/weekly_publish.sh

# 检查 service 配置
sudo systemctl cat paper-tracker-weekly.service

# 重载并重试
sudo systemctl daemon-reload
sudo systemctl start paper-tracker-weekly.service
```

---

## 日志管理

### 日志文件位置

```bash
# 默认日志目录
$BASE_DIR/logs/

# 日志文件命名格式
weekly_publish_YYYYMMDD_HHMMSS.log
```

### 查看日志

```bash
# 查看最新日志
tail -f $BASE_DIR/logs/weekly_publish_*.log

# 查看特定日期的日志
ls -l $BASE_DIR/logs/ | grep 20260210

# 搜索错误
grep -r "ERROR" $BASE_DIR/logs/
```

### 日志清理

**手动清理：**

```bash
# 删除 30 天前的日志
find $BASE_DIR/logs/ -name "weekly_publish_*.log" -mtime +30 -delete
```

**自动清理（添加到 crontab）：**

```bash
# 每月 1 号凌晨清理旧日志
0 0 1 * * find /home/automation/github_auto/logs/ -name "weekly_publish_*.log" -mtime +30 -delete
```

---

## 高级配置

### 使用不同的 Python 环境

```bash
# 使用系统 Python
PT_BIN=/usr/local/bin/paper-tracker ./scripts/weekly_publish.sh

# 使用 conda 环境
PT_BIN=/home/automation/anaconda3/envs/paper/bin/paper-tracker ./scripts/weekly_publish.sh
```

### 发布到自定义域名

1. 在 `PUBLISH_DIR` 添加 `CNAME` 文件：

```bash
echo "papers.example.com" > $BASE_DIR/publish/CNAME
git -C $BASE_DIR/publish add CNAME
git -C $BASE_DIR/publish commit -m "docs: add custom domain"
git -C $BASE_DIR/publish push
```

2. 在 DNS 设置中添加 CNAME 记录指向 `YourUsername.github.io`

### 多仓库部署

```bash
# 仓库 1: 机器学习论文
BASE_DIR=/opt/ml-papers \
CONFIG_FILE=/opt/ml-papers/paper-tracker/config/ml.yml \
./scripts/weekly_publish.sh

# 仓库 2: 计算机视觉论文
BASE_DIR=/opt/cv-papers \
CONFIG_FILE=/opt/cv-papers/paper-tracker/config/cv.yml \
./scripts/weekly_publish.sh
```

### 邮件通知（可选）

在脚本末尾添加邮件通知：

```bash
# 在脚本最后添加
if [ $? -eq 0 ]; then
  echo "Publish completed successfully" | mail -s "Weekly Publish Success" admin@example.com
else
  echo "Publish failed, check logs" | mail -s "Weekly Publish Failed" admin@example.com
fi
```

---

## 安全注意事项

1. **保护敏感信息**
   - `.env` 文件不要提交到 Git
   - 日志文件不要包含 API 密钥
   - 使用环境变量传递密钥

2. **最小权限原则**
   - 使用专门的自动化用户运行脚本
   - 限制 GitHub Token 权限（仅 `repo` 范围）

3. **定期更新**
   - 定期更新依赖包
   - 监控 GitHub 安全告警

4. **备份**
   - 定期备份配置文件
   - 保留关键日志文件

---

## 相关文档

- [Paper Tracker 使用指南](../docs/zh/guide_user.md)
- [详细配置说明](../docs/zh/guide_configuration.md)
- [arXiv API 查询说明](../docs/zh/source_arxiv_api_query.md)

---

## 许可证

本脚本遵循项目许可证。
