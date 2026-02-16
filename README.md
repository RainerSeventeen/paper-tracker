# Paper Tracker

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg)](https://github.com/rainerseventeen/paper-tracker/releases)
[![Last Commit](https://img.shields.io/github/last-commit/rainerseventeen/paper-tracker)](https://github.com/rainerseventeen/paper-tracker/commits)
[![Code Size](https://img.shields.io/github/languages/code-size/rainerseventeen/paper-tracker)](https://github.com/rainerseventeen/paper-tracker)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/rainerseventeen/paper-tracker/graphs/commit-activity)


Paper Tracker 是一个最小化的论文追踪工具，核心目标是基于关键词查询 arXiv，并按配置输出结构化结果，便于持续跟踪新论文。

**如果该项目对你有帮助, 请麻烦点一个 Star ⭐, 谢谢!**

## ✨ 效果展示

查看实际运行效果：[📄 部署发布页](https://rainerseventeen.github.io/paper-tracker/)

该页面展示了基于配置文件自动抓取并生成的论文列表，包含：
- 🔍 按关键词筛选的最新论文
- 📋 结构化的论文信息（标题、作者、摘要、链接）
- 🤖 可选的 LLM 增强摘要（如启用）

## 📦 已实现功能

- 🔍 **查询与筛选**: 
  - 基于 arXiv API 查询论文
  - 支持字段化检索：`TITLE`、`ABSTRACT`、`AUTHOR`、`JOURNAL`、`CATEGORY`
  - 支持逻辑操作：`AND`、`OR`、`NOT`
  - 支持全局 `scope`（对所有 queries 生效）
- 📥 **拉取策略**: 支持拉取更早的论文以补全预定论文数量

- 💾 **去重与存储**: SQLite 去重功能, 并存储论文内容供日后查询

- 📤 **输出能力**: 支持`json`、`markdown`、`html` 等格式输出, 支持替换模板 
- 🤖 **LLM 增强**: 支持 OpenAI-compatible 接口调用, 包括摘要翻译与结构化总结支持

## 🚀 快速开始

建议使用虚拟环境（如 `.venv/`）：
```bash
python3 -m venv .venv
```
执行安装
```bash
python -m pip install -e .
```

### (可选)配置 API 环境变量

如果启用 llm 总结则需要配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 LLM_API_KEY
```

### 运行命令

```bash
paper-tracker search --config config/default.yml
```

## ⚙️ 自定义配置

> 注意: 项目会首先从 `config/default.yml` 读取默认配置, 随后读取 `--config` 参数路径的文件, 对默认值进行覆盖, 所以请不要修改 `default.yml`

```bash
# 创建自定义的配置文件
cp config/default.yml config/custom.yml
```
修改 config/custom.yml 为个人设置后, 执行:

```bash
paper-tracker search --config config/custom.yml
```

至少需要关注两项：

- 🔎 `queries`：至少设置一条自定义查询请求方案
- 📤 `output.formats`：至少 1 种输出格式

📚 详细指引可以查看文档:
- [📖 使用指南](./docs/zh/guide_user.md)

- [⚙️ 详细参数配置说明](./docs/zh/guide_configuration.md)

- [🔍 arXiv 查询语法说明](./docs/zh/source_arxiv_api_query.md)

## 更新

如需更新到最新版本：

```bash
cd paper-tracker
git pull
python -m pip install -e . --upgrade
```

## 反馈

如遇到问题或有功能建议，欢迎在 [GitHub Issues](https://github.com/rainerseventeen/paper-tracker/issues) 提交。

请提供运行时的日志信息 (默认在 log/ 下)

## 许可证

本项目使用 [MIT License](./LICENSE)。

## 🙏 致谢

本仓库为独立实现，参考了以下项目的功能思路：

- [Arxiv-tracker](https://github.com/colorfulandcjy0806/Arxiv-tracker)
- [daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced)
