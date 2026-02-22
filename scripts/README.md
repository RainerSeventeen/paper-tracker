# Weekly Publish Script - 自动化发布脚本

`weekly_publish.sh` 是一个自动化脚本，用于定期执行论文检索并将生成的 HTML 报告发布到 GitHub Pages。

**核心功能：**
- 自动拉取最新代码
- 执行论文检索（可选）
- 构建静态站点
- 发布到 GitHub Pages (gh-pages 分支)
- 完整的日志记录
- Dry-run 模式：关闭 LLM 与存储，仅拉取并输出 HTML，不推送到 GitHub

---

## 快速开始

```bash
# 标准运行
./scripts/weekly_publish.sh --config config/custom.yml

# 跳过检索，直接发布已有 HTML
./scripts/weekly_publish.sh --config config/custom.yml --publish-only

# Dry-run：拉取论文、输出 HTML，不写库、不调 LLM、不推送 GitHub
./scripts/weekly_publish.sh --config config/custom.yml --dry-run

# 指定项目根目录（默认从脚本位置自动推导）
REPO_DIR=/opt/paper-tracker ./scripts/weekly_publish.sh --config config/custom.yml
```

---

详细说明（前置要求、环境变量、部署指南、故障排查等）参见 [docs/zh/guide_weekly_publish.md](../docs/zh/guide_weekly_publish.md)。
