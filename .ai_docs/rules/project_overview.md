# Paper Tracker - Project Overview

## Project Identity

Paper Tracker is a minimal arXiv paper tracking tool refactored from scratch, focused on keyword-based search and clean output.

## Architecture Layers

The codebase follows a four-layer design pattern:

### 1. CLI Layer (`cli/` package)

Refactored in v0.1.1+ with dependency injection and factory pattern:

- **`ui.py`**: Click command definitions (thin entry points)
- **`runner.py`**: Component orchestration and resource lifecycle management
- **`commands.py`**: Business logic containers (e.g., `SearchCommand`)
- **`factories.py`**: Component factories (ServiceFactory, StorageFactory, OutputFactory)
- **`output.py`**: Output abstraction via `OutputWriter` Protocol

**Execution Flow**:
```
main() → cli() → search_cmd() → CommandRunner.run_search()
  ├─ create_search_service() → PaperSearchService
  ├─ create_storage() → (DatabaseManager, DeduplicateStore, ContentStore)
  ├─ create_output_writer() → OutputWriter (Console or JsonFile)
  └─ SearchCommand.execute() + writer.finalize()
```

### 2. Configuration Layer (`config/` package)

- **`config/app.py`**: Root orchestration (`load_config*`, `parse_config_dict`, cross-domain checks)
- **Domain modules**: `runtime.py`, `search.py`, `storage.py`, `output.py`, `llm.py`
- **`AppConfig`**: Root dataclass composed of domain configs
- **`SearchQuery`**: Structured queries with multiple `FieldQuery` objects

**Constraint**: YAML files must use spaces only (no tabs).

### 3. Query Compiler (`sources/arxiv/query.py`)

Translates structured `SearchQuery` into arXiv Atom API query strings:

- **Field Mappings**:
  - `TEXT` → `(ti OR abs)`
  - `TITLE` → `ti`
  - `ABSTRACT` → `abs`
  - `AUTHOR` → `au`
  - `CATEGORY` → `cat`
  - `JOURNAL` → `(jr OR co)` (best-effort)

- **Auto-expansion**: Generates space/hyphen variants (e.g., "neural network" → "neural network" OR "neural-network")

### 4. Data Source Layer (`sources/arxiv/`)

- **`client.py`**: HTTP client with HTTPS→HTTP fallback and exponential backoff retry
- **`parser.py`**: Parses Atom XML responses into `Paper` objects
- **`source.py`**: Wraps client/parser as `ArxivSource`

## Optional Features

### State Management

Enabled via `state.enabled: true`:
- Uses SQLite to track seen papers (`storage/deduplicate.py`)
- Auto-filters duplicates, outputs only new papers
- Database schema: `papers` (metadata) + `paper_content` (full text)

### LLM Translation (NEW in v0.1.0+)

Enabled via `llm.enabled: true` + `state.content_storage_enabled: true`:

**Architecture**:
```
src/PaperTracker/llm/
├── __init__.py           # Factory: create_llm_service()
├── provider.py           # Protocol: LLMProvider
├── client.py             # LLMApiClient (HTTP client)
├── openai_compat.py      # OpenAICompatProvider implementation
└── service.py            # LLMService (high-level orchestration)
```

**Workflow**:
1. Search papers from arXiv
2. Filter new papers (deduplication)
3. Translate new papers' summaries via LLM
4. Store papers with translations in database
5. Output results (console or JSON)

**Configuration**:
```yaml
llm:
  enabled: true
  provider: openai-compat  # Currently only this provider supported
  base_url: https://api.openai.com  # Any OpenAI-compatible endpoint
  model: gpt-4o-mini
  api_key_env: OPENAI_API_KEY
  timeout: 30
  target_lang: zh  # Supported: zh, en, ja, ko, fr, de, es
```

**Output**:
- **Text format**: Displays translated summary under "摘要(翻译):"
- **JSON format**: Adds `extra.translation.summary_translated` field

## Output Behavior

- **`text` format**: Outputs to console via logging system
- **`json` format**: Writes to `<output_dir>/<action>_<timestamp>.json`

## Data Flow

```
YAML Config → AppConfig → SearchQuery
  ↓
ArxivSource.search() → Query Compiler → API Request
  ↓
XML Response → Parser → Paper[]
  ↓
(Optional) LLMService.translate_batch() → Add translations
  ↓
(Optional) DeduplicateStore.filter_new() → New Papers
  ↓
OutputWriter.write_query_result() → Console/File
```

## Design Principles

### Protocol-Based Abstractions

- **`OutputWriter` Protocol** (`renderers/base.py`): Enables pluggable output formats
  - Implementations: `ConsoleOutputWriter`, `JsonFileWriter`
  - Extend by: Create new class implementing protocol → Update `create_output_writer()` factory

- **`LLMProvider` Protocol** (`llm/provider.py`): Enables pluggable LLM backends
  - Implementations: `OpenAICompatProvider`
  - Future: Anthropic, Google, local models

### Factory Pattern

All component creation happens in module-level `__init__.py` factories:

- `services/__init__.py`: `create_search_service(config)`
- `storage/__init__.py`: `create_storage(config)`
- `renderers/__init__.py`: `create_output_writer(config)`
- `llm/__init__.py`: `create_llm_service(config)`

**Benefit**: Decouples creation logic from usage; easy to swap implementations.

### Dependency Injection

`SearchCommand` receives all dependencies via constructor:

```python
@dataclass(slots=True)
class SearchCommand:
    config: AppConfig
    search_service: PaperSearchService
    dedup_store: SqliteDeduplicateStore | None
    content_store: PaperContentStore | None
    llm_service: LLMService | None
    output_writer: OutputWriter
```

**Benefit**: Zero side effects; fully testable with mocks.

## Extension Points

### Add New Output Format (e.g., CSV)

1. Create `renderers/csv.py` implementing `OutputWriter`
2. Update `create_output_writer()` in `renderers/__init__.py`
3. Use in config: `output.format: csv`

### Add New Command (e.g., `export`)

1. Create `ExportCommand` in `commands.py`
2. Add `run_export()` method in `runner.py`
3. Add `@cli.command("export")` in `ui.py`

### Add New Data Source (e.g., Google Scholar)

1. Create `sources/scholar/` with client/parser/source
2. Update `create_search_service()` in `services/__init__.py`
3. Add `source_type` field to `AppConfig`

### Add New LLM Provider (e.g., Anthropic)

1. Create `llm/anthropic.py` implementing `LLMProvider`
2. Update `create_llm_service()` in `llm/__init__.py`
3. Use in config: `llm.provider: anthropic`

## Error Handling

- **LLM Translation**: Single paper failures don't stop batch; failed papers returned without translation
- **API Failures**: Exponential backoff retry (3 attempts) with timeout
- **Database Errors**: Managed in `DatabaseManager` context manager
- **CLI Errors**: Caught in `CommandRunner.run_search()` and converted to `click.Abort`

## Testing Strategy

- Test configs: `config/test/`
- Test scripts: `test/test_*.py`
- Run all tests: `python -m unittest discover -s test -p "test_*.py"`

## Key Files to Understand

1. **`cli/runner.py`**: Execution orchestration (start here)
2. **`config/app.py`**: Configuration assembly entrypoint
3. **`sources/arxiv/query.py`**: Query compilation logic
4. **`services/search.py`**: Core search business logic
5. **`llm/service.py`**: LLM translation orchestration
6. **`renderers/base.py`**: Output abstraction

## Current Status (v0.1.0)

Working features:
- ✅ arXiv keyword search
- ✅ Query compilation with field mapping
- ✅ Console and JSON output
- ✅ State management (deduplication)
- ✅ LLM translation (OpenAI-compatible APIs)
- ✅ Content storage (abstracts + translations)
