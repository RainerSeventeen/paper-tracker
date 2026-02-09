# 配置与环境

本文档覆盖两部分：
1. `config/default.yml` 的**每个字段**说明与配置方式
2. `.env` 的配置方法

---

## 1. 配置文件规则

- CLI 只接受一个参数：`--config <path>`

- 配置为 YAML 嵌套结构，不支持 `log.level` 这类扁平键

- `config/default.yml` 是默认配置, 请不要修改

- 合并规则：mapping 递归合并，列表与标量整体覆盖

示例（覆盖少量字段）：
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

---

## 2. `default.yml` 字段说明

以下按 `config/default.yml` 的结构逐项说明。每个字段均包含：功能说明、可选范围、示例。

### 2.1 `log`

- `level`: 控制 CLI 日志等级; 可选值: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`。如果填写未知值会报错。

- `to_file`: 是否同时写入日志文件（除了控制台输出）; 可选值: `true` / `false`。

- `dir`: 日志文件目录根路径; 可选值: 任意合法目录路径。相对路径相对于当前工作目录。

示例（`log` 只给一个示例即可）：
```yml
log:
  level: DEBUG
  to_file: true
  dir: log
```

### 2.2 `storage`（去重与内容存储）

- `enabled`: 启用后会对已见过的论文做去重，避免重复输出; 可选值: `true` / `false`。

- `db_path`: SQLite 数据库存储路径，用于去重状态与内容存储; 可选值: 任意合法文件路径。相对路径相对于当前工作目录；绝对路径以 `/` 开头。

- `content_storage_enabled`: 是否保存完整论文内容到数据库（标题、摘要、作者等），用于后续检索与复用; 可选值: `true` / `false`。

示例（`storage` 只给一个示例即可）：
```yml
storage:
  enabled: true
  db_path: database/papers.db
  content_storage_enabled: true
  keep_arxiv_version: false
```

### 2.3 `storage.keep_arxiv_version`

- `storage.keep_arxiv_version`: 是否保留 arXiv 论文 ID 的版本后缀; 可选值: `true` / `false`。

示例（只给一个示例即可）：
```yml
storage:
  keep_arxiv_version: false
```

说明：
- `false`（默认）：`2601.21922v1` -> `2601.21922`

- `true`：保留版本号 `v1` / `v2` 等

### 2.4 `scope`（可选，全局过滤条件）

- `scope`: 对**所有**查询生效的全局过滤条件; 可选值: 与 `queries` 相同的结构（字段名和操作符必须大写）。允许字段：`TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`。允许操作符：`AND` / `OR` / `NOT`。

- `scope.<FIELD>`: 指定某个字段的检索条件; 可选值: 字段名必须大写，且只能是 `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`。

- `scope.<FIELD>.AND`: 同一字段内“所有关键词都要匹配”; 可选值: 字符串或字符串列表。

- `scope.<FIELD>.OR`: 同一字段内“任意关键词匹配即可”; 可选值: 字符串或字符串列表。

- `scope.<FIELD>.NOT`: 排除某些关键词; 可选值: 字符串或字符串列表。

示例（`scope` 只给一个示例即可）：
```yml
scope:
  CATEGORY:
    OR: [cs.CV, cs.LG]
  TITLE:
    NOT: ["survey", "review"]
```

### 2.5 `queries`（必选）

- `queries`: 查询列表，每个元素是一条独立 query，依次执行并输出结果; 可选值: 非空数组；每个元素是一个查询对象。

- `queries[].NAME`: 为该查询起一个可读名称，仅用于日志和输出展示; 可选值: 非空字符串，可省略。

- `queries[].<FIELD>`: 指定某个字段的检索条件; 可选值: 字段名必须大写，且只能是 `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`。

- `queries[].AND / OR / NOT`: 当在 query 顶层直接写 `AND/OR/NOT` 时，表示对 `TEXT` 字段（标题+摘要）搜索; 可选值: 字符串或字符串列表。

- `queries[].<FIELD>.AND`: 同一字段内“所有关键词都要匹配”; 可选值: 字符串或字符串列表。

- `queries[].<FIELD>.OR`: 同一字段内“任意关键词匹配即可”; 可选值: 字符串或字符串列表。

- `queries[].<FIELD>.NOT`: 排除某些关键词; 可选值: 字符串或字符串列表。

示例（`queries` 只给一个示例即可）：

```yml
queries:
  - NAME: neural_video_compression
    OR: ["Neural Video Compression", "Learned Video Compression"]
  - NAME: vqa
    TITLE:
      OR: ["Video Quality Assessment"]
  - NAME: no_surveys
    TITLE:
      NOT: ["survey", "review"]
```

### 2.6 `search`（拉取策略配置）

- `max_results`: 目标论文数量，每条 query 最多返回这么多篇**新论文**（去重后）; 可选值: 整数，必须大于 0。

- `pull_every`: strict 时间窗口大小（单位：天），论文的更新/发布时间必须在 `[now - pull_every, now]` 范围内; 可选值: 整数，必须大于 0。建议值：`7`（最近一周）。

- `fill_enabled`: 是否允许 strict 窗口外的论文进入候选（用于补满 `max_results`）; 可选值: `true` / `false`。
  - `false`（严格模式）：仅允许 strict 时间窗内的论文进入候选。系统仍会继续分页拉取，直到命中停止条件（例如达到目标、到达 strict 窗口边界、或触发抓取上限）。
  - `true`（补全模式）：允许 strict 窗口外（受 `max_lookback_days` 限制）的论文进入候选，用于补齐数量；同样始终按分页策略抓取。

- `max_lookback_days`: fill 的最大回溯天数（单位：天），仅在 `fill_enabled=true` 时生效; 可选值: `-1`（不限制）或大于等于 `pull_every` 的整数。建议值：`30`（最近一个月）。

- `max_fetch_items`: 单条 query 最大拉取的原始论文条目数（包括重复和被过滤的）; 可选值: `-1`（不限制）或大于 0 的整数。建议值：`125`（控制 API 调用次数）。

- `fetch_batch_size`: 每次 API 请求拉取的论文数量（分页大小）; 可选值: 整数，必须大于 0。建议值：`25`。

**排序策略**：arXiv 拉取时固定使用 `lastUpdatedDate` + `descending`（最新更新优先），不支持用户配置。

示例（`search` 只给一个示例即可）：
```yml
search:
  max_results: 10             # 目标返回 10 篇新论文

  # 时间窗口配置
  pull_every: 7               # strict 窗口：最近 7 天
  fill_enabled: false         # 严格模式，不补全
  max_lookback_days: 30       # 如果 fill_enabled=true，最多回溯 30 天
  max_fetch_items: 125        # 最多拉取 125 条原始数据
  fetch_batch_size: 25        # 每页 25 条
```

**配置约束**：
- `pull_every > 0`
- `fill_enabled=true` 时：`max_lookback_days == -1` 或 `max_lookback_days >= pull_every`
- `max_fetch_items == -1` 或 `max_fetch_items > 0`
- `fetch_batch_size > 0`

### 2.7 `output`

- `base_dir`: 输出根目录; 可选值: 任意合法目录路径。相对路径相对于当前工作目录。

- `formats`: 输出格式列表，可同时输出多种格式; 可选值: `console` / `json` / `markdown` / `html` 的任意组合（至少一个）。

- `markdown.template_dir`: Markdown 模板目录; 可选值: 任意非空目录路径字符串。

- `markdown.document_template`: 文档级模板文件名（生成整份 Markdown 文档的外层结构）; 可选值: 模板目录中的文件名。

- `markdown.paper_template`: 论文级模板文件名（单篇论文的渲染结构）; 可选值: 模板目录中的文件名。

- `markdown.paper_separator`: 多篇论文之间的分隔符字符串; 可选值: 任意字符串；可包含 `\n` 换行。

示例（`output` 只给一个示例即可）：
```yml
output:
  base_dir: output/
  formats: [console, json, markdown]
  markdown:
    template_dir: template/markdown/
    document_template: document.md
    paper_template: paper.md
    paper_separator: "\n\n---\n\n"
```

说明：
- 只有当 `output.formats` 包含 `markdown` 时，上述 `output.markdown.*` 字段才会生效。
- 只有当 `output.formats` 包含 `html` 时，`output.html.*` 字段才会生效。

### 2.8 `llm`

- `enabled`: 是否启用 LLM 相关功能（翻译/摘要）; 可选值: `true` / `false`。

- `provider`: LLM 提供商类型; 可选值: 目前仅支持 `openai-compat`。

- `base_url`: API Base URL; 可选值: 任意可访问的 HTTP(S) 接口地址。

- `model`: 模型名称; 可选值: 具体由 `base_url` 对应的服务决定。

- `api_key_env`: API Key 对应的环境变量名; 可选值: 任意非空字符串。

- `timeout`: 单次请求超时（秒）; 可选值: 整数，建议大于 0。

- `target_lang`: 目标语言，用于翻译与摘要输出语言; 可选值: 任意语言标识字符串。推荐使用 `zh` / `en` / `ja` / `ko` / `fr` / `de` / `es` 等。

- `temperature`: 采样温度，影响输出随机性; 可选值: 浮点数，常用 `0.0` ~ `2.0`。

- `max_tokens`: 最大响应 token 数; 可选值: 整数，建议大于 0。

- `max_workers`: 并发 worker 数，影响同时处理论文的数量; 可选值: 整数，建议大于等于 1。

- `enable_translation`: 是否启用摘要翻译; 可选值: `true` / `false`。

- `enable_summary`: 是否启用结构化摘要（TLDR、动机、方法、结果、结论）; 可选值: `true` / `false`。

- `max_retries`: 最大重试次数（用于超时或临时错误）; 可选值: 整数，`0` 表示不重试。

- `retry_base_delay`: 指数退避基础延迟（秒）; 可选值: 浮点数，建议大于等于 0。

- `retry_max_delay`: 最大重试延迟（秒）; 可选值: 浮点数，建议大于等于 0。

- `retry_timeout_multiplier`: 每次重试的超时倍数; 可选值: 浮点数，`1.0` 表示不放大。

示例（`llm` 只给一个示例即可）：
```yml
llm:
  enabled: true
  provider: openai-compat
  base_url: https://api.openai.com
  model: gpt-4o-mini
  api_key_env: LLM_API_KEY
  timeout: 30
  target_lang: zh
  temperature: 0.2
  max_tokens: 1000
  max_workers: 3
  enable_translation: true
  enable_summary: true
  max_retries: 3
  retry_base_delay: 1.0
  retry_max_delay: 10.0
  retry_timeout_multiplier: 1.0
```

---

## 3. `.env` 配置

`.env` 用于存放敏感信息（如 API Key）。

### 3.1 创建 `.env`

```bash
cp .env.example .env
```

### 3.2 `LLM_API_KEY`
功能说明：LLM API 的访问密钥，默认由 `llm.api_key_env` 指定（默认 `LLM_API_KEY`）。
可选范围：非空字符串，由提供商颁发。

示例：
```bash
LLM_API_KEY=sk-your-actual-api-key-here
```

### 3.3 说明
- `.env` 已在 `.gitignore` 中，不会提交

- 可以通过 `llm.api_key_env` 自定义变量名

- shell 中同名变量优先级更高

临时覆盖示例：
```bash
LLM_API_KEY=sk-temp paper-tracker --config config.yml search
```
