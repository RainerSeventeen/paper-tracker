# Paper Tracker

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg)](https://github.com/rainerseventeen/paper-tracker/releases)
[![Last Commit](https://img.shields.io/github/last-commit/rainerseventeen/paper-tracker)](https://github.com/rainerseventeen/paper-tracker/commits)
[![Code Size](https://img.shields.io/github/languages/code-size/rainerseventeen/paper-tracker)](https://github.com/rainerseventeen/paper-tracker)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/rainerseventeen/paper-tracker/graphs/commit-activity)

**[English](./README.en.md) | 中文**

Paper Tracker 是一个最小化的论文追踪工具，核心目标是基于关键词查询多个论文数据库（arXiv、OpenAlex），并按配置输出结构化结果，便于持续跟踪新论文。

**如果该项目对你有帮助, 请麻烦点一个 Star ⭐, 谢谢!**

## 效果展示

查看实际运行效果：[📄 部署发布页](https://rainerseventeen.github.io/paper-tracker/)

![HTML 输出结果演示](./docs/assets/html_output_preview.png)

## 已实现功能

- 🔍 **查询与筛选**:
  - 支持多数据源：`arxiv`（预印本）、`openalex`（期刊/会议/预印本），可同时启用
  - 支持字段化检索：`TITLE`、`ABSTRACT`、`AUTHOR`、`JOURNAL`、`CATEGORY`
  - 支持逻辑操作：`AND`、`OR`、`NOT`
  - 支持全局 `scope`（对所有 queries 生效）
  - 多源结果聚合后执行跨源去重


  | 数据源 | 数据类型 | query 字段支持 | 本地精筛 | 跨源去重 |
  |--------|----------|:--------------:|:--------:|:--------:|
  | `arxiv` | 预印本 | 完整 | — | ✅ |
  | `openalex` | 期刊 / 会议 / 预印本 | 部分 | ✅ | ✅ |

- 🧲 **拉取策略**: 支持拉取更早的论文以补全预定论文数量

- 🗃️ **去重与存储**: SQLite 去重功能, 并存储论文内容供日后查询

- 📤 **输出能力**: 支持`json`、`markdown`、`html` 等格式输出, 支持替换模板

- 🤖 **LLM 增强**: 支持 OpenAI-compatible 接口调用, 包括摘要翻译与结构化总结支持

- 🌐 **输出语言可配置**: 可通过 `llm.target_lang` 自定义翻译与总结输出语言（如 `Simplified Chinese`、`English`、`Japanese`）

## 快速开始

建议使用虚拟环境（如 `.venv/`）：
```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows
python -m pip install -e .     # Install
```

用内置示例配置直接运行：
```bash
paper-tracker search --config config/example.yml
```
## 自定义配置

复制示例配置，按需修改后运行：

```bash
cp config/example.yml config/custom.yml
# 修改 config/custom.yml 字段
paper-tracker search --config config/custom.yml
```

**以下为必填字段：**

- `queries`：至少设置一条查询
- `llm.base_url` / `llm.model`：当 `llm.enabled: true` 时必须指定

### (可选) 配置 LLM 环境变量

启用 LLM 摘要翻译时需要配置 API Key：

```bash
cp .env.example .env
# 编辑 .env，填入你的 LLM_API_KEY
```

📚 详细指引可以查看文档:
- [📖 使用指南](./docs/zh/guide_user.md)

- [⚙️ 详细参数配置说明](./docs/zh/guide_configuration.md)

- [🔍 查询内部逻辑说明](./docs/zh/architecture_search_logic.md)

- [🔍 arXiv 查询语法说明](./docs/zh/source_arxiv_api_query.md)

- [🔍 OpenAlex 查询语法说明](./docs/zh/source_openalex_api_query.md)

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

## 致谢

本仓库为独立实现，参考了以下项目的功能思路：

- [Arxiv-tracker](https://github.com/colorfulandcjy0806/Arxiv-tracker)
- [daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced)
