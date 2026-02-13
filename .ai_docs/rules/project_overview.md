# Paper Tracker 项目概览（当前实现）

## 项目定位

Paper Tracker 是一个最小化论文追踪工具：根据配置中的关键词查询 arXiv API，按配置输出论文列表，并可选进行去重持久化与 LLM 增强。

## 真实入口与主调用链

当前代码入口链路如下：

```text
src/PaperTracker/__main__.py
  -> PaperTracker.cli.main()
  -> cli.ui: cli()/search_cmd()
  -> CommandRunner.run_search(action)
  -> SearchCommand.execute()
```

`SearchCommand.execute()` 的每轮查询流程：

```text
SearchService.search(query)
  -> ArxivSource.search(...)
  -> collect_papers_with_time_filter(...)
  -> map_papers_to_views(...)
  -> output_writer.write_query_result(...)
  -> dedup_store.mark_seen(...) / content_store.save_papers(...) / llm_store.save(...)
```

## 模块分层（按代码现状）

### 1. CLI 层（`src/PaperTracker/cli/`）

- `ui.py`：Click 命令定义，`search` 命令加载配置并调用 runner。
- `runner.py`：生命周期编排（日志、依赖创建、异常边界、资源回收）。
- `commands.py`：命令业务逻辑（`SearchCommand`）。
- `__init__.py`：导出 `main()` 给 `__main__.py` 与 console script 使用。

### 2. 配置层（`src/PaperTracker/config/`）

- 根配置：`AppConfig(runtime/search/output/storage/llm)`。
- 入口：`load_config_with_defaults()`，以 `config/default.yml` 为基线并深度合并覆盖配置。
- 查询 DSL：`SearchQuery` + `FieldQuery`，支持 `scope` + `queries`。

### 3. 服务与数据源层（`services/` + `sources/arxiv/`）

- `PaperSearchService`：对上提供稳定 `search()` 接口。
- `ArxivSource`：组合 query 编译、分页拉取、解析与策略过滤。
- `collect_papers_with_time_filter()`：按时间窗口与策略分页抓取，并在抓取阶段执行去重过滤。
- `query.py`：将 `SearchQuery` 编译为 arXiv `search_query`（`TEXT/TITLE/ABSTRACT/AUTHOR/CATEGORY/JOURNAL` 映射）。

### 4. 输出层（`src/PaperTracker/renderers/`）

- 抽象：`OutputWriter`。
- 聚合：`MultiOutputWriter`（一次运行可并行写多个输出格式）。
- 实现：`console`、`json`、`markdown`、`html`。
- 工厂：`create_output_writer(config)` 按 `output.formats` 组装 writer 列表。

### 5. 存储层（`src/PaperTracker/storage/`）

- `create_storage()`：根据 `storage.enabled` 创建数据库组件。
- `SqliteDeduplicateStore`：`seen_papers` 去重状态。
- `PaperContentStore`：`paper_content` 论文内容快照。
- `LLMGeneratedStore`：`llm_generated` LLM 生成结果。

### 6. LLM 层（`src/PaperTracker/llm/`）

- `create_llm_service()`：按配置创建 provider + service。
- `LLMService`：并发批处理，支持“仅翻译 / 仅总结 / 两者都启用”。
- `LLMProvider`：provider 协议，目前实现为 `openai-compat`。

## 当前关键配置字段（以代码为准）

- 存储域使用 `storage.*`（不是旧的 `state.*`）：
  - `storage.enabled`
  - `storage.db_path`
  - `storage.content_storage_enabled`
  - `storage.keep_arxiv_version`
- 输出域使用 `output.formats` 多选：`console/json/markdown/html`。
- LLM 域关键字段：
  - `llm.enabled` / `llm.provider` / `llm.base_url` / `llm.model`
  - `llm.api_key_env`（默认示例是 `LLM_API_KEY`）
  - `llm.enable_translation` / `llm.enable_summary`

## 数据结构与字段约定

- `SearchQuery`：`name + fields`，`fields` 的 value 为 `FieldQuery(AND/OR/NOT)`。
- `Paper`：统一论文模型，含 `extra` 扩展字段（只读映射）。
- `LLMGeneratedInfo`：LLM 增强结构（翻译 + summary 五元组）。

LLM 增强在内存中写入 `Paper.extra` 的约定：

- `extra.translation.summary_translated`
- `extra.translation.language`
- `extra.summary.tldr|motivation|method|result|conclusion`

JSON 输出（`renderers/json.py`）会将上述信息映射为顶层字段：

- `abstract_translation`
- `summary.{tldr,motivation,method,result,conclusion}`

## 存储表结构（SQLite）

由 `storage/db.py:init_schema()` 初始化三张主表：

- `seen_papers`：去重主表（source/source_id 唯一）。
- `paper_content`：论文内容快照，关联 `seen_papers`。
- `llm_generated`：LLM 结果，关联 `paper_content`。

## 事实边界说明

本文件只描述“当前实现事实与调用链”，不作为编码规范文档。
如代码与本文冲突，以代码为准，并应同步更新本文档。
