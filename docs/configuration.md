# 配置指南（`config.yml`）

本项目的 CLI 只接受一个参数：`--config <path>`。

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
  format: text
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

- `format`: `text` / `json`
  - `text`: 将结果通过日志输出到控制台
  - `json`: 将结果保存为时间戳 JSON 文件
- `dir`: 可选，默认 `output`，指定 JSON 文件的输出目录

示例：

```yml
output:
  format: json
  dir: custom_output  # 输出文件到 custom_output/ 目录
```

### 2.6 `arxiv`

arXiv 专用选项。

- `keep_version`：是否保留 arXiv 版本号作为 `id`
  - `false`（默认）：`2601.21922v1` -> `2601.21922`
  - `true`：保留版本后缀（`2601.21922v1`）

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
