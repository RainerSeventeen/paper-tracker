# Paper Tracker

Paper Tracker 是一个最小化的论文追踪工具，核心目标是基于关键词查询 arXiv，并按配置输出结构化结果，便于持续跟踪新论文。

## 项目定位

- 现有功能：查询 arXiv 并输出结果
- 配置驱动：行为主要由 YAML 配置控制
- 可扩展：支持多输出格式与可选 LLM 增强

## 已实现功能

- 查询与筛选
  - 基于 arXiv API 查询论文
  - 支持字段化检索：`TITLE`、`ABSTRACT`、`AUTHOR`、`JOURNAL`、`CATEGORY`
  - 支持逻辑操作：`AND`、`OR`、`NOT`
  - 支持全局 `scope`（对所有 queries 生效）
- 拉取策略
  - 按时间窗口多轮拉取
  - 支持补齐策略（`fill_enabled`）与回看窗口（`max_lookback_days`）
  - 可配置分页与批量拉取参数
- 去重与存储
  - SQLite 去重（避免重复输出已见论文）
  - 可选保存论文内容
  - 可选保留 arXiv 版本号（如 `v1`）
- 输出能力
  - 支持 `console`、`json`、`markdown`、`html` 输出
  - 支持模板化渲染（Markdown/HTML）
- LLM 增强（可选）
  - 支持 OpenAI-compatible 接口
  - 支持摘要翻译与结构化总结
  - 支持并发与重试配置
- 工程支持
  - 命令行入口：`paper-tracker search`
  - 基础单元测试与 pipeline 测试
  - 自动化发布脚本（见 `scripts/weekly_publish.sh`）

## 快速开始

### 1. 环境要求

- Python `>= 3.10`

### 2. 安装

建议使用虚拟环境（如 `.venv/`）：

```bash
python -m pip install -e .
```

### 3. 环境变量（仅在启用 LLM 时必需）

```bash
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY 等
```

### 4. 运行

```bash
paper-tracker search --config config/default.yml
```

## 配置说明（最小必需）

至少需要关注两项：

- `queries`：至少 1 条查询
- `output.formats`：至少 1 种输出格式

建议不要直接修改 `config/default.yml`，而是复制一份为自定义配置：

```bash
cp config/default.yml config/custom.yml
paper-tracker search --config config/custom.yml
```

项目会首先从 `config/default.yml` 读取默认配置, 随后读取 `--config` 参数路径的文件, 对默认值进行覆盖, 所以请不要修改 `default.yml`

## 最小示例配置

```yml
queries:
  - NAME: example
    TITLE:
      OR: [diffusion model]
    ABSTRACT:
      NOT: [survey]

search:
  max_results: 5

output:
  base_dir: output
  formats: [console, json]
```

更多参数请看文档：

- [使用指南](./docs/zh/guide_user.md)
- [详细参数配置说明](./docs/zh/guide_configuration.md)
- [arXiv 查询语法说明](./docs/zh/source_arxiv_api_query.md)

## 许可证

本项目使用 [MIT License](./LICENSE)。

## 致谢

本仓库为独立实现，参考了以下项目的功能思路：

- [Arxiv-tracker](https://github.com/colorfulandcjy0806/Arxiv-tracker)
- [daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced)
