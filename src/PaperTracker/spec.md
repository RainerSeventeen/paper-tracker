# PaperTracker 运行逻辑与调用链

本文描述当前 `PaperTracker` 的最小可用核心功能：

- 输入：关键词（可选分类、排除词、排序参数）
- 行为：调用 arXiv API 抓取 Atom feed
- 输出：通过日志系统打印到命令行（`text` / `json`）

> 代码入口：`paper-tracker`（console script）或 `python -m PaperTracker`。

---

## 模块分区

- `PaperTracker/cli.py`
  - CLI 参数解析、组装查询对象、调用 service、将结果输出到 log。
- `PaperTracker/utils/log.py`
  - 统一日志输出格式：`时间 + 级别(DEBG/INFO/WARN/ERRO) + 文本`。
- `PaperTracker/core/*`
  - `SearchQuery`：搜索请求模型。
  - `Paper`/`PaperLinks`：统一的论文领域模型（跨数据源通用）。
- `PaperTracker/services/search.py`
  - `PaperSearchService`：用例层（application/service），负责调用 `PaperSource`。
  - `PaperSource`：数据源协议（可替换/可扩展）。
- `PaperTracker/sources/arxiv/*`
  - `query.py`：把 `SearchQuery` 转换为 arXiv `search_query` 字符串。
  - `client.py`：HTTP 拉取 arXiv Atom XML（HTTPS→HTTP fallback，带 retry/backoff）。
  - `parser.py`：解析 Atom XML → `Paper` 列表。
  - `source.py`：组装 query/client/parser，对外提供 `ArxivSource.search()`。
- `PaperTracker/renderers/console.py`
  - `render_text` / `render_json`：将 `Paper` 列表格式化为文本或 JSON 结构。

---

## 运行入口

### 方式 1：console script

由 `pyproject.toml` 注册：

- `paper-tracker = PaperTracker.cli:main`

安装后运行：

- `paper-tracker search --keyword "diffusion" --category cs.CV --max-results 5`

### 方式 2：模块运行

- `python -m PaperTracker search --keyword diffusion --max-results 5`

---

## 核心调用链（search 命令）

以 `paper-tracker search ...` 为例，调用链如下：

1. `PaperTracker.cli:main()`
2. `PaperTracker.cli:cli()`
   - 解析全局参数（如 `--log-level`）
   - 调用 `PaperTracker.utils.log:configure_logging()` 初始化 logger
3. `PaperTracker.cli:search_cmd()`
   - 解析并清洗参数（`_split_multi`）
   - 构造 `PaperTracker.core.query:SearchQuery`
   - 初始化 `PaperSearchService(source=ArxivSource(client=ArxivApiClient()))`
   - 调用 `PaperSearchService.search()`
4. `PaperTracker.services.search:PaperSearchService.search()`
   - 委托给 `source.search(...)`
5. `PaperTracker.sources.arxiv.source:ArxivSource.search()`
   - `PaperTracker.sources.arxiv.query:build_search_query(...)`
   - `PaperTracker.sources.arxiv.client:ArxivApiClient.fetch_feed(...)` 拉取 Atom XML
   - `PaperTracker.sources.arxiv.parser:parse_arxiv_feed(xml)` 解析为 `list[Paper]`
6. 回到 `PaperTracker.cli:search_cmd()`
   - `PaperTracker.renderers.console:render_text(...)` 或 `render_json(...)`
   - **逐行**用 `PaperTracker.utils.log:log.info(...)` 打印

---

## 时序视图（简化）

```text
User
  |
  |  paper-tracker search --keyword ...
  v
cli.py (click)
  |
  | configure_logging()
  v
search_cmd()
  |
  | PaperSearchService.search(query)
  v
PaperSearchService
  |
  | ArxivSource.search(query)
  v
ArxivSource
  |  build_search_query()
  |  ArxivApiClient.fetch_feed()  --->  arXiv API (network)
  |  parse_arxiv_feed()
  v
list[Paper]
  |
  | render_text()/render_json()
  v
log.info(...) (逐行输出)
```

---

## 可扩展点

- 新增数据源
  - 在 `PaperTracker/sources/<new_source>/` 实现：`client.py` + `parser.py` + `source.py`
  - 让 `<NewSource>` 实现 `PaperSource.search()` 并返回 `list[Paper]`
  - 在 `cli.py` 里替换/增加 source 选择逻辑（例如 `--source arxiv/xxx`）

- 新增输出形式
  - 在 `PaperTracker/renderers/` 增加新的 renderer（例如 Markdown/CSV）
  - CLI 增加 `--format md/csv` 并调用对应 renderer

