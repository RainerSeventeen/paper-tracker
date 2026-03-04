# OpenAlex API: `search` 参数与查询说明

本文档说明 OpenAlex Works API（`/works`）在本项目中的参数使用方式，以及项目的查询编译与本地精筛逻辑。

> 说明：本文重点是"Paper Tracker 当前实现实际使用的能力"，不是 OpenAlex 全量语法手册。

---

## 1. OpenAlex Works API 请求参数概览

OpenAlex Works API 的典型请求形如：

```text
https://api.openalex.org/works?search=<QUERY>&filter=from_publication_date:2026-02-01&page=1&per-page=25&sort=publication_date:desc
```

本项目使用的常用参数：

- `search`: 全局布尔文本搜索（本文重点，本项目仅将 TITLE / ABSTRACT / TEXT 字段编译进此参数）
- `filter`: 过滤条件（本项目会附加 `from_publication_date:YYYY-MM-DD`）
- `page`: 页码（从 1 开始）
- `per-page`: 每页条数（最大 200）
- `sort`: 排序（本项目固定为 `publication_date:desc`）

参考：<https://docs.openalex.org/>

---

## 2. `search` 查询表达式（本项目编译方式）

### 2.1 字段如何映射到 `search`

OpenAlex 只接受全局 `search` 参数，**没有** `ti:`、`abs:`、`au:` 这类字段前缀。

本项目**只将 `TITLE`、`ABSTRACT`、`TEXT` 三个字段**的词项编译进 `search` 字符串，字段子句之间用 `AND` 连接。

`AUTHOR`、`JOURNAL`、`CATEGORY` 字段在编译阶段被跳过，由下游本地过滤处理（见第 3 节）。

> 日后计划：`AUTHOR` 可通过 `filter=author.display_name:<name>` 实现；`JOURNAL` 可通过 `filter=primary_location.source.display_name:<name>` 实现；`CATEGORY` 可通过 `filter=concepts.display_name:<name>` 或 topics 实现。

`scope` 和 `query` 各自编译为独立 clause，再以 `AND` 拼接：

```text
<scope_clause> AND <query_clause>
```

### 2.2 布尔结构（AND / OR / NOT 的编译规则）

每个字段下三种操作符的编译规则如下：

- `AND`：多词时用括号包裹，词间用 `AND` 连接：
  - `"diffusion" AND "video"` → `("diffusion" AND "video")`
  - 单词时直接引用：`"diffusion"`
- `OR`：多词时用括号包裹，词间用 `OR` 连接：
  - `("diffusion" OR "transformer")`
- `NOT`：多词时括号内 `OR` 连接，加 `NOT` 前缀：
  - `NOT "survey"`
  - `NOT ("survey" OR "review")`

各操作符 clause 之间用 `AND` 连接，整个字段形成一个子句。

说明：
- 每个 term 会自动加双引号（短语安全）。
- `NOT` 词同时参与上游 `search` 编译，以及下游本地 NOT 过滤（见第 3 节）。

---

## 3. 本地精筛逻辑（两阶段过滤）

OpenAlex 上游的 `search` 是全文搜索，没有字段精度保证。本项目在收到结果后，会依次执行两阶段本地过滤：

### 3.1 正向字段匹配（`apply_positive_filter`）

对每篇论文逐字段严格匹配，**所有字段都必须满足**才保留。各字段的匹配文本如下：

| 配置字段    | 本地匹配目标         |
|-------------|----------------------|
| `TITLE`     | `paper.title`        |
| `ABSTRACT`  | `paper.abstract`     |
| `AUTHOR`    | `paper.authors` 拼接 |
| `JOURNAL`   | `paper.journal`      |
| `TEXT`      | `title + abstract`   |
| `CATEGORY`  | **跳过，不做匹配**   |

`CATEGORY` 字段在本地精筛阶段被跳过的原因见第 4 节。

### 3.2 NOT 排除（`apply_not_filter`）

独立于正向过滤运行，移除标题或摘要中包含任意 NOT 词的论文（大小写不敏感）。

> NOT 词"双重保险"：`TITLE`/`ABSTRACT`/`TEXT` 字段的 NOT 词既在 `search` 中作为文本提示（减少上游返回量），又在本地强制排除，确保排除效果。`AUTHOR`/`JOURNAL`/`CATEGORY` 字段的 NOT 词当前仅在本地过滤阶段生效。

---

## 4. `CATEGORY` 字段的行为与限制

| 阶段       | 行为                                                       |
|------------|------------------------------------------------------------|
| 编译阶段   | **跳过**，不编入 `search`                                  |
| 本地过滤   | **跳过**，不做任何本地匹配（视为条件始终成立）             |

**原因**：OpenAlex 的论文不携带 arXiv 分类码（如 `cs.CV`）。OpenAlex 的主题词（`primary_topic` / `concepts`）是自然语言名称（如 `Computer Vision`），无法像 arXiv `cat:` 一样做精确过滤；将其混入全局 `search` 反而会干扰召回语义。

**实际效果**：`CATEGORY` 在 OpenAlex 中当前完全无效。如需按主题限定，建议改用 `TITLE` 或 `ABSTRACT` 字段。

> 日后计划：支持通过 `filter=concepts.display_name:<name>` 或 `topics` 实现主题约束。

---

## 5. 与本项目配置的对应关系

本项目配置层使用结构化 query（`scope` + `queries`），字段与操作符沿用统一语义。

详细说明可以参考: [详细配置参数说明](./guide_configuration.md)

配置层支持语义字段：

- `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`
- 顶层 `AND`/`OR`/`NOT` 等价于 `TEXT`（标题+摘要）

每个字段下支持三个操作符键（要求大写）：

- `AND`: 必须同时满足（列表）
- `OR`: 任一满足即可（列表）
- `NOT`: 排除（列表）

```yml
queries:
  - NAME: example_openalex
    TITLE:
      OR: [diffusion]
      NOT: [survey]
    AUTHOR:
      OR: ["Yann LeCun"]
```

---

## 6. 示例

### 6.1 标题/摘要关键词 + 排除综述

配置：
```yml
TITLE:
  OR: [diffusion, video]
  NOT: [survey]
```

编译结果（上游 `search`）：
```text
("diffusion" OR "video") AND NOT "survey"
```

本地过滤：确认标题包含 `diffusion` 或 `video`，且标题+摘要不含 `survey`。

### 6.2 多关键词并列召回

配置：
```yml
OR: ["vision-language model", "multimodal large language model"]
NOT: [survey, review]
```

编译结果：
```text
("vision-language model" OR "multimodal large language model") AND NOT ("survey" OR "review")
```

### 6.3 结合全局 scope 与 query

scope 和 query 各自编译为 clause，最终以 `AND` 拼接：

```text
<scope_clause> AND <query_clause>
```

---

## 7. 常见注意事项

- OpenAlex 不支持 `ti:`/`abs:` 等字段前缀；请使用配置层字段（`TITLE`/`ABSTRACT` 等）。
- `CATEGORY` 在 OpenAlex 中不做本地精筛，不能保证只返回特定主题的论文；如需精确过滤，改用 `TITLE` 或 `ABSTRACT`。
- 为避免 YAML 解析歧义，包含空格或特殊字符的词建议用引号包裹。
- 最终结果数量受 `search.max_results`、`search.max_fetch_items`、时间窗口等共同控制。
