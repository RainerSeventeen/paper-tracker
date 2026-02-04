# 配置指南（`config.yml`）

本项目的 CLI 只接受一个参数：`--config <path>`。

配置只支持 YAML 嵌套结构（例如 `log:` 下的 `level`），不支持 `log.level` 这类扁平键写法。

`config/default.yml` 是完整默认配置文档。执行时会将 `--config` 指定的 YAML 作为覆盖文件，与默认配置进行合并：同路径字段覆盖，未提供字段使用默认值。合并规则为“mapping 递归合并，列表和标量整体覆盖”。

示例（只覆盖少量字段）：

```yml
log:
  level: DEBUG

search:
  max_results: 10

queries:
  - NAME: override
    OR: [diffusion]
```

运行：

```bash
paper-tracker --config custom.yml search
```

配置文件使用 YAML，核心目标是：**用户侧高可读、结构统一**；内部会将配置编译成不同数据源所需的查询格式（当前实现 arXiv）。

---

## 1. 最小可用示例

```yml
log:
  level: INFO
  to_file: true
  dir: log

queries:
  - NAME: example
    TITLE:
      OR: [diffusion]

search:
  max_results: 3

output:
  base_dir: output
  formats: [console]
```

运行：

```bash
paper-tracker --config config.yml search
```

---

## 2. 顶层字段

### 2.1 `log`

- `level`：可选，默认 `INFO`（目前为兼容保留，命令行输出固定为 INFO）
- `to_file`：可选，默认 `true`，写入 `log/<action>/<action>_<MMDDHHMMSS>.log`
- `dir`：可选，默认 `log`

示例：

```yml
log:
  level: DEBUG
  to_file: true
  dir: log
```

### 2.2 `scope`（可选）

全局范围过滤，会对 **所有** `queries` 生效（等价于将 scope 与每条 query 进行 AND）。

示例（限定分类）：

```yml
scope:
  CATEGORY:
    OR: [cs.CV, cs.LG]
```

### 2.3 `queries`（必选）

查询列表；每个元素是一条独立 query，依次执行并输出结果。

### 2.4 `search`

- `max_results`：每条 query 的最大返回数
- `sort_by`：`submittedDate` / `lastUpdatedDate`
- `sort_order`：`ascending` / `descending`

### 2.5 `output`

- `base_dir`: 输出根目录，默认 `output`
- `formats`: 输出格式列表，支持 `console` / `json` / `markdown`
  - `console`: 将结果通过日志输出到控制台
  - `json`: 将结果保存为 JSON 文件
  - `markdown`: 将结果保存为 Markdown 文件
- `markdown`: Markdown 导出配置（见下方示例）
- `json`: JSON 导出配置（文件名模板）

示例：

```yml
output:
  base_dir: output
  formats: [json, markdown]

  markdown:
    template_dir: template/markdown/
    document_template: document.md
    paper_template: paper.md
    paper_separator: "\n\n---\n\n"
```

### 2.6 `arxiv`

arXiv 专用选项。

- `keep_version`：是否保留 arXiv 版本号作为 `id`
  - `false`（默认）：`2601.21922v1` -> `2601.21922`
  - `true`：保留版本后缀（`2601.21922v1`）

### 2.7 `state`（可选）

状态管理（去重）与内容存储相关选项。

- `enabled`：是否启用状态管理（去重）
- `db_path`：SQLite 数据库路径
  - 支持相对路径（相对于当前工作目录）或绝对路径（以 `/` 开头）
  - 默认值：`database/papers.db`
- `content_storage_enabled`：是否启用完整内容存储（将完整论文元数据写入 `paper_content` 表）

说明：
- `content_storage_enabled` 依赖 `enabled: true`
- `config/default.yml` 中该选项目前为开启状态

### 2.8 `llm`（可选）

LLM 增强功能相关选项，支持摘要翻译和结构化摘要生成。

**基础配置**：
- `enabled`：是否启用 LLM 功能；启用后会对搜索结果进行翻译/摘要增强
- `provider`：提供商类型（当前为 `openai-compat`）
- `api_key_env`：API Key 的环境变量名（默认 `LLM_API_KEY`）
- `base_url`：OpenAI 兼容接口的 Base URL
- `model`：模型名称（例如 `gpt-4o-mini`、`deepseek-chat`）
- `timeout`：请求超时（秒）
- `target_lang`：目标语言（例如 `zh`）
- `temperature`：采样温度（0.0 = 确定性）
- `max_tokens`：最大响应 token 数
- `max_workers`：并发 worker 数（用于并行处理）

**功能选择**：
- `enable_translation`：是否启用摘要翻译（默认 `true`）
- `enable_summary`：是否启用结构化摘要生成（默认 `false`，包含 TLDR、动机、方法、结果、结论）

**重试配置**（用于应对网络超时和临时性 API 故障）：
- `max_retries`：最大重试次数（默认 3，设为 0 禁用重试）
- `retry_base_delay`：指数退避基础延迟（秒，默认 1.0）
- `retry_max_delay`：单次重试最大等待时间（秒，默认 10.0）
- `retry_timeout_multiplier`：每次重试的超时倍数（默认 1.0，即保持不变）

说明：
- 当 `llm.enabled: true` 时，必须设置对应的环境变量（默认 `LLM_API_KEY`），否则会报错并提示关闭或配置密钥。
- 重试机制对以下错误生效：网络超时、连接错误、HTTP 429/500/502/503/504。
- 不可重试的错误（如 HTTP 400/401/403）会立即失败。
- 功能使用详情、成本分析、故障排查等参见 [LLM 增强功能文档](llm-features.md)。

---

## 3. Query 结构（重点）

每条 query 是一个对象，包含：

- `NAME`（可选）：用于日志/输出标识
- 若干字段（必须大写）：
  - `TITLE`
  - `ABSTRACT`
  - `AUTHOR`
  - `JOURNAL`（arXiv 会 best-effort 映射到 `jr/co`，其它数据源可做更准确映射）
  - `CATEGORY`

字段的值是一个对象，支持三个操作符键（必须大写）：

- `OR`：任意一个 term 命中即可
- `AND`：所有 term 都要命中
- `NOT`：排除 term（等价于 `AND NOT (...)`）

term 可以写成字符串或字符串列表。

示例：

```yml
queries:
  - NAME: llm
    TITLE:
      OR:
        - large language model
        - LLM
      NOT: [survey, review]
    ABSTRACT:
      OR: [instruction tuning]
```

---

## 4. `TEXT` 简写（默认字段：标题 + 摘要）

如果你只关心“标题+摘要”关键词，支持在 query 顶层直接写 `AND/OR/NOT`，等价于内部字段 `TEXT`。

示例：

```yml
queries:
  - NAME: compression
    OR:
      - Image Compression
      - Video Compression
    NOT: survey
```

等价于：

```yml
queries:
  - NAME: compression
    TEXT:
      OR: [Image Compression, Video Compression]
      NOT: [survey]
```

---

## 5. 与 arXiv 字段的关系

本项目会把结构化 query 编译为 arXiv Atom API `search_query`。

- 更详细的 arXiv `search_query` 字段与语法说明见：`docs/arxiv-api-query.md`
