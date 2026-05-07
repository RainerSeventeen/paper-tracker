# PubMed API: `term` 参数与查询说明

本文档说明 NCBI E-utilities（`esearch.fcgi` + `efetch.fcgi`）在本项目中的参数使用方式，以及项目的查询编译与本地处理逻辑。

> 说明：本文重点是 "Paper Tracker 当前实现实际使用的能力"，不是 PubMed/E-utilities 全量语法手册。

---

## 1. NCBI E-utilities 请求参数概览

PubMed 拉取由 **两阶段** 调用组成：先 ESearch 取 PMID 列表，再 EFetch 拿完整 XML。

### 1.1 ESearch（取 PMID 列表）

典型请求形如：

```text
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&sort=pub_date&datetype=pdat&term=<TERM>&retstart=0&retmax=25&mindate=2026/04/01&maxdate=2026/05/07
```

本项目使用的常用参数：

- `db`: 固定为 `pubmed`
- `retmode`: 固定为 `json`
- `sort`: 固定为 `pub_date`（按发表日期排序）
- `datetype`: 固定为 `pdat`（按发表日期过滤）
- `term`: 布尔检索表达式（本文重点）
- `retstart`: 结果起始偏移（从 0 开始）
- `retmax`: 单次返回 PMID 上限
- `mindate` / `maxdate`: 时间窗口，格式为 `YYYY/MM/DD`
- `api_key`（可选）: NCBI API Key，提供时速率上限从 3 req/s 提升至 10 req/s
- `tool` / `email`: 调用方标识与联系邮箱（NCBI 礼貌策略要求）

### 1.2 EFetch（取完整记录）

ESearch 拿到 PMID 后,以 `id=<PMID 逗号列表>` 请求 EFetch,以 XML 形式返回完整 `PubmedArticleSet`：

```text
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id=12345,12346,...
```

参考：<https://www.ncbi.nlm.nih.gov/books/NBK25501/>

> 单次 EFetch 最多 200 个 PMID（GET 请求长度限制）。`search.fetch_batch_size` 不应超过此值。

---

## 2. `term` 查询表达式（本项目编译方式）

### 2.1 字段如何映射到 `term`

PubMed 的 `term` 通过 `"value"[TAG]` 形式做字段限定。本项目把配置层的字段编译为以下 PubMed 字段标签：

| 配置字段    | PubMed 字段标签 | 说明                                            |
|-------------|-----------------|-------------------------------------------------|
| `TEXT`      | `[TIAB]`        | Title + Abstract                                |
| `TITLE`     | `[TIAB]`        | PubMed 无独立 "title-only" 标签的简单等价物，统一走 TIAB |
| `ABSTRACT`  | `[TIAB]`        | Title + Abstract                                |
| `AUTHOR`    | `[AU]`          | 作者                                            |
| `JOURNAL`   | `[JT]`          | 期刊全称                                         |
| `CATEGORY`  | **跳过，不映射** | PubMed 无对应字段（详见第 4 节）                 |

> 注意：`TITLE` 与 `ABSTRACT` 在 PubMed 下被合并到同一个 `[TIAB]` 标签下，因此在 PubMed source 内**不能区分** "只在标题" 与 "只在摘要" 的检索；两者均匹配 Title + Abstract。如果需要严格的 title-only 行为，请使用 arXiv source。

`scope` 与 `query` 各自编译为独立 clause，再以 `AND` 拼接：

```text
<scope_clause> AND <query_clause>
```

### 2.2 布尔结构（AND / OR / NOT 的编译规则）

每个字段下三种操作符的编译规则如下（设字段标签为 `<TAG>`）：

- `AND`：对每个词逐项展开为 `"term"<TAG>`，词间用 `AND` 连接：
  - `["diffusion", "video"]` → `"diffusion"[TIAB] AND "video"[TIAB]`
- `OR`：单词时直接展开；多词时整体用括号包裹，词间用 `OR` 连接：
  - 单词：`"diffusion"[TIAB]`
  - 多词：`("diffusion"[TIAB] OR "transformer"[TIAB])`
- `NOT`：单词加 `NOT (...)` 包裹；多词括号内 `OR` 连接，加 `NOT` 前缀：
  - 单词：`NOT ("survey"[TIAB])`
  - 多词：`NOT ("survey"[TIAB] OR "review"[TIAB])`

各操作符 clause 之间用 `AND` 连接，构成一个字段子句。多个字段子句之间再以 `AND` 连接（多于一个时整体用括号包裹）。

说明：

- 每个 term 都会被加上双引号（短语安全），并附带字段标签。
- `NOT` 在编译阶段直接进入上游 `term`，由 PubMed 服务端排除，本项目对 PubMed 不再做本地 NOT 二次过滤。

---

## 3. 上游精度与本地处理

PubMed `term` 通过字段标签提供精确匹配能力，**上游已经保证字段精度**，因此 PubMed source 在本项目中：

- **不做本地正向字段过滤**（无 `apply_positive_filter` 等价逻辑）
- **不做本地 NOT 兜底过滤**（NOT 已通过 `term` 在上游生效）
- **会丢弃没有 DOI 的记录**：解析 `PubmedArticleSet` 时，若某篇文章的 `ArticleIdList` 中没有 `IdType="doi"` 的条目，该记录在该批次内被跳过（保证跨源去重的指纹一致性）

> 对去重的影响：因 DOI 是跨源去重的首选指纹，缺失 DOI 的 PubMed 记录无法可靠地与 arXiv/OpenAlex 合并，故选择丢弃而非保留。

---

## 4. `CATEGORY` 字段的行为与限制

| 阶段      | 行为                                                |
|-----------|-----------------------------------------------------|
| 编译阶段  | **跳过**，不编入 `term`                              |
| 本地过滤  | **不存在**（PubMed source 无本地正向过滤阶段）       |

**原因**：PubMed 没有与 arXiv `cat:cs.CV` 等价的分类码体系。其本身使用 MeSH（Medical Subject Headings）做主题索引，但 MeSH 词表与 arXiv 分类码并不互通，本项目暂未将 MeSH 接入查询编译。

**重要约束**：若一条 query 中**只**指定了 `CATEGORY`（或 query/scope 整体没有任何可映射的字段），编译器会抛出 `ValueError`，避免空 `term` 触发 PubMed 全库召回。

**实际效果**：`CATEGORY` 在 PubMed 中当前完全无效。如需按主题限定，请使用 `TITLE` / `ABSTRACT` / `TEXT`。

> 日后计划：如需按 MeSH 主题限定，可扩展 `[MH]`（MeSH Terms）或 `[MAJR]`（MeSH Major Topic）字段标签。

---

## 5. 时间窗口与排序

### 5.1 时间过滤

PubMed 的时间窗口由 ESearch 的 `mindate` / `maxdate` 直接在上游实现，配合 `datetype=pdat`（按发表日期）：

- 严格模式（默认）：`[now - pull_every, now]`
- 填充模式（`fill_enabled=true`）：`[now - max_lookback_days, now]`；`max_lookback_days=-1` 表示不附加日期限制

时间字符串使用 PubMed 接受的 `YYYY/MM/DD` 格式。

### 5.2 排序

ESearch 固定使用 `sort=pub_date`，按发表日期降序返回 PMID。本项目在所有页面收集完成后，再按 `paper.published` 时间戳做一次本地降序排序作为最终顺序，并按 `max_results` 截断。

---

## 6. 认证与速率

| 维度        | 行为                                                                   |
|-------------|------------------------------------------------------------------------|
| API Key     | 通过环境变量 `NCBI_API_KEY`（变量名可由 `search.ncbi_api_key_env` 配置）|
| 速率上限    | 无 Key：3 req/s；有 Key：10 req/s（NCBI 官方政策）                      |
| Tool 标识   | `search.ncbi_tool`，默认 `paper-tracker`                                |
| 联系邮箱    | `search.ncbi_email`，默认空字符串（建议设置以遵守 NCBI 礼貌策略）       |
| 超时        | 单次 HTTP 请求 30 秒；单次 query 总时长上限 120 秒                       |
| 重试        | 对 429 / 500 / 502 / 503 / 504 自动重试，指数退避，最多 4 次             |
| 翻页间隔    | 每页之间强制 sleep 1 秒；同一页 ESearch→EFetch 之间 sleep 0.5 秒         |

---

## 7. 与本项目配置的对应关系

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
  - NAME: example_pubmed
    OR: [diffusion]
    NOT: [survey]
    AUTHOR:
      OR: ["Yann LeCun"]
```

---

## 8. 示例

### 8.1 标题/摘要关键词 + 排除综述

配置：
```yml
TITLE:
  OR: [diffusion, video]
  NOT: [survey]
```

编译结果（上游 `term`）：
```text
(("diffusion"[TIAB] OR "video"[TIAB]) AND NOT ("survey"[TIAB]))
```

### 8.2 多关键词并列召回（顶层 OR + NOT，等价于 TEXT）

配置：
```yml
OR: ["vision-language model", "multimodal large language model"]
NOT: [survey, review]
```

编译结果：
```text
("vision-language model"[TIAB] OR "multimodal large language model"[TIAB]) AND NOT ("survey"[TIAB] OR "review"[TIAB])
```

### 8.3 字段组合（关键词 + 作者 + 期刊）

配置：
```yml
OR: [diffusion]
AUTHOR:
  OR: ["Yann LeCun"]
JOURNAL:
  OR: ["Nature"]
```

编译结果：
```text
("diffusion"[TIAB] AND "Yann LeCun"[AU] AND "Nature"[JT])
```

### 8.4 结合全局 scope 与 query

scope 和 query 各自编译为 clause，最终以 `AND` 拼接：

```text
<scope_clause> AND <query_clause>
```

---

## 9. 常见注意事项

- **`TITLE` 与 `ABSTRACT` 在 PubMed 下不可区分**，两者均编译为 `[TIAB]`；如需 title-only 精度，请使用 arXiv source。
- **`CATEGORY` 在 PubMed 中无效**，单独使用 `CATEGORY` 的 query 会因为没有可映射字段而抛错；请使用 `TITLE` / `ABSTRACT` / `TEXT` 替代。
- **缺少 DOI 的论文会被丢弃**，可能会导致部分 PubMed 记录无法进入结果集；这是为了保证跨源去重的可靠性。
- **建议设置 `NCBI_API_KEY`**：未配置时速率上限较低（3 req/s），翻页较多时容易因偶发 429 触发重试。
- **建议设置 `search.ncbi_email`**：NCBI E-utilities 礼貌策略推荐传入联系邮箱。
- **`fetch_batch_size` 不要超过 200**：EFetch 单次 GET 请求 PMID 上限为 200，超过会抛错。
- 为避免 YAML 解析歧义，包含空格或特殊字符的词建议用引号包裹。
- 最终结果数量受 `search.max_results`、`search.max_fetch_items`、时间窗口等共同控制。

---

## 10. 与 arXiv / OpenAlex 的主要差异

本节对比 PubMed 与已有两个 source 在本项目中的核心逻辑差异，帮助用户理解三源行为并正确配置。

### 10.1 API 协议与响应格式

| 维度       | arXiv                       | OpenAlex                | PubMed                              |
|------------|-----------------------------|-------------------------|-------------------------------------|
| API 类型   | Atom/RSS XML（`/api/query`）| REST JSON（`/works`）   | REST JSON（ESearch）+ XML（EFetch） |
| 调用阶段   | 单阶段                       | 单阶段                  | **两阶段**（ESearch 取 ID → EFetch 取详情） |
| 摘要存储   | XML `<summary>` 直接文本     | 倒排索引，需本地重建    | XML `<AbstractText>`（含 Label 的结构化段落由本地拼接） |

### 10.2 查询参数结构

| 维度          | arXiv                                  | OpenAlex                  | PubMed                                |
|---------------|----------------------------------------|---------------------------|---------------------------------------|
| 关键词参数名  | `search_query`                         | `search`                  | `term`                                |
| 字段前缀语法  | `field:value`（前缀）                  | **无**，仅全局 `search`   | `"value"[TAG]`（**后缀**字段标签）    |
| 字段精度      | 上游精确                                | 上游全文，本地精筛保证精度 | **上游精确**（标签生效）              |

### 10.3 字段映射差异

| 配置字段    | arXiv          | OpenAlex      | PubMed                |
|-------------|----------------|---------------|-----------------------|
| `TITLE`     | `ti:`          | `search` 全文 | `[TIAB]`（**title+abstract，无 title-only**） |
| `ABSTRACT`  | `abs:`         | `search` 全文 | `[TIAB]`              |
| `AUTHOR`    | `au:`          | 跳过（本地）  | `[AU]`                |
| `JOURNAL`   | `jr:`          | 跳过（本地）  | `[JT]`                |
| `CATEGORY`  | `cat:cs.CV` 等 | **跳过，无效**| **跳过，无效**        |

### 10.4 本地过滤策略

| 维度        | arXiv                | OpenAlex                       | PubMed                          |
|-------------|----------------------|--------------------------------|---------------------------------|
| 上游精度    | 字段前缀已保证       | 全文搜索，精度不足              | 字段标签已保证                  |
| 本地正向过滤| 无                   | 有（`apply_positive_filter`）  | **无**                          |
| NOT 过滤    | 仅上游 `ANDNOT`      | 上游 + 本地双重保险             | 仅上游 `NOT`                    |
| DOI 缺失处理| 保留                 | 保留                           | **丢弃**（保证跨源去重可靠性）  |

### 10.5 时间字段与排序策略

| 维度          | arXiv                                          | OpenAlex                             | PubMed                              |
|---------------|------------------------------------------------|--------------------------------------|-------------------------------------|
| 上游时间过滤  | 无（本地过滤 `updated`）                        | `filter=from_publication_date:...`   | **`mindate` + `maxdate`（`pdat`）** |
| 上游排序参数  | `sortBy=lastUpdatedDate&sortOrder=descending`  | `sort=publication_date:desc,relevance_score:desc` | `sort=pub_date`            |
| 时间字段含义  | 论文 `updated`（最新版本时间）                  | 论文 `published`                     | 论文 `published`（发表日期）        |

### 10.6 请求频率

| 维度        | arXiv         | OpenAlex                | PubMed                                |
|-------------|---------------|-------------------------|---------------------------------------|
| 翻页间隔    | 无强制间隔    | **强制 3 秒** 翻页间隔  | **强制 1 秒** 翻页间隔（页内再 0.5 秒）|
| 速率上限    | 无显式上限    | 无显式上限              | 3 req/s（无 Key）/ 10 req/s（有 Key） |
| 超时保护    | 无全局超时    | 单次 query 最长 120 秒  | 单次 query 最长 120 秒                |
| 重试策略    | 通用退避      | 通用退避                | 4 次重试，指数退避（429/5xx）         |

### 10.7 数据覆盖范围

| 维度       | arXiv             | OpenAlex                                       | PubMed                          |
|------------|-------------------|-----------------------------------------------|---------------------------------|
| 内容范围   | arXiv 预印本       | 期刊、会议、预印本（覆盖最广）                  | 生物医学 / 生命科学领域期刊论文 |
| 发表状态   | 通常预印本         | 含正式发表版本（`article`）                    | 正式发表论文（`article`）       |
| 主题倾向   | 计算机/物理为主    | 全学科                                          | **生物医学/医学/生命科学**      |
| 跨源去重优先| 无优先级           | 优先保留 `article` 类型                        | 优先保留 `article` 类型         |

> **使用建议**：PubMed 适合生物医学相关主题（如医学影像、基因组学、临床 NLP）；如果你的检索主题与生命科学无关，启用 PubMed 大概率召回较少。
