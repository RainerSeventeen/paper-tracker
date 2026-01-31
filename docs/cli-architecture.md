# CLI 架构指南

本文档说明 PaperTracker CLI 的重构设计，以及如何扩展新功能。

---

## 总览

重构后的 CLI 采用 **命令模式 + 工厂模式 + 依赖注入** 的设计，将复杂的单一函数拆分为职责清晰的模块。

### 模块结构

```
src/PaperTracker/
├── cli/
│   ├── __init__.py       # 包导出 + main() 入口点
│   ├── ui.py             # Click 命令行定义
│   ├── commands.py       # SearchCommand 业务逻辑
│   ├── factories.py      # 工厂函数（ServiceFactory, StorageFactory）
│   └── runner.py         # CommandRunner 运行协调
└── renderers/
    ├── __init__.py       # 导出 OutputWriter 协议 + 工厂函数
    ├── base.py           # OutputWriter 协议定义
    ├── console.py        # render_text + ConsoleOutputWriter 实现
    └── json.py           # render_json + JsonFileWriter 实现
```

### 执行流程

```
main()
  ↓
cli() [Click Group]
  ↓
search_cmd() [Click Command]
  ↓
CommandRunner.run_search()
  ├─ 配置日志
  ├─ ServiceFactory.create_arxiv_service() → PaperSearchService
  ├─ StorageFactory.create_storage() → (DatabaseManager, DeduplicateStore, ContentStore)
  ├─ create_output_writer() → OutputWriter
  │  └─ 在 renderers/__init__.py 中根据 config.output_format 决定实现
  ├─ SearchCommand(config, service, dedup, content, writer)
  └─ command.execute() + writer.finalize()
```

---

## 核心组件设计

### 1. OutputWriter Protocol (`renderers/base.py`)

定义输出抽象，支持多种输出方式：

```python
class OutputWriter(ABC):
    """Write command results to console or file."""

    def write_query_result(
        self,
        papers: list[Paper],
        query: SearchQuery,
        scope: SearchQuery | None,
    ) -> None:
        """处理单条查询的结果。"""

    def finalize(self, action: str) -> None:
        """最终化输出（如写入文件）。"""
```

**实现** (在各自的模块中)：

- `ConsoleOutputWriter` (`renderers/console.py`): 通过日志输出到控制台
- `JsonFileWriter` (`renderers/json.py`): 累积结果并写入 JSON 文件

**创建工厂** (`renderers/__init__.py`)：

```python
def create_output_writer(config: AppConfig) -> OutputWriter:
    """Create output writer based on config."""
    if config.output_format == "json":
        return JsonFileWriter(config.output_dir)
    return ConsoleOutputWriter()
```

**扩展**：
若要支持新的输出格式（如 CSV、Markdown）：

1. 在 `renderers/csv.py` 中实现新的 OutputWriter：
```python
class CsvOutputWriter(OutputWriter):
    def write_query_result(self, papers, query, scope):
        # 累积或直接写入 CSV
        pass

    def finalize(self, action):
        # 写入 CSV 文件
        pass
```

2. 在 `renderers/__init__.py` 中更新工厂函数：
```python
def create_output_writer(config: AppConfig) -> OutputWriter:
    if config.output_format == "json":
        return JsonFileWriter(config.output_dir)
    elif config.output_format == "csv":
        return CsvOutputWriter(config.output_dir)
    return ConsoleOutputWriter()
```

### 2. SearchCommand (`commands.py`)

封装搜索业务逻辑，通过依赖注入接收所有组件：

```python
@dataclass(slots=True)
class SearchCommand:
    config: AppConfig
    search_service: PaperSearchService
    dedup_store: SqliteDeduplicateStore | None
    content_store: PaperContentStore | None
    output_writer: OutputWriter

    def execute(self) -> None:
        """执行搜索（循环所有查询、应用去重、输出结果）。"""
```

**职责**：
- 遍历所有查询
- 调用搜索服务获取论文
- 应用去重过滤（如果启用）
- 委托输出写入器处理结果

**优点**：
- 零副作用，易于单元测试
- 依赖完全注入，易于 Mock

### 3. CommandRunner (`runner.py`)

协调所有组件的创建、配置和执行：

```python
class CommandRunner:
    """Orchestrates command execution with proper resource management."""

    def __init__(self, config: AppConfig):
        self.config = config

    def run_search(self, action: str) -> None:
        """Execute search with logging config and resource cleanup."""
```

**职责**：
- 配置日志系统
- 创建所有组件（通过工厂）
- 管理数据库上下文（使用 `with` 语句）
- 捕获并报告异常

### 4. Factories (`factories.py`)

集中管理组件创建，解耦 CLI 与具体实现：

```python
class ServiceFactory:
    @staticmethod
    def create_arxiv_service(config: AppConfig) -> PaperSearchService:
        """创建带 ArxivSource 的搜索服务。"""

class StorageFactory:
    @staticmethod
    def create_storage(config: AppConfig) -> tuple[...]:
        """创建数据库管理器和存储组件。"""

class OutputFactory:
    @staticmethod
    def create_writer(config: AppConfig) -> OutputWriter:
        """根据配置创建输出写入器。"""
```

**扩展**：
要添加新的数据源（如 Google Scholar），添加新的工厂方法：

```python
class ServiceFactory:
    @staticmethod
    def create_scholar_service(config: AppConfig) -> PaperSearchService:
        """创建带 ScholarSource 的搜索服务。"""
```

然后在 `CommandRunner` 或 `cli/ui.py` 中根据配置选择。

### 5. Click UI (`ui.py`)

仅负责参数解析和委托：

```python
@click.group()
@click.option("--config", ...)
@click.pass_context
def cli(ctx, config_path):
    cfg = load_config(config_path)
    ctx.obj = cfg

@cli.command("search")
@click.pass_context
def search_cmd(ctx):
    runner = CommandRunner(ctx.obj)
    runner.run_search(action=ctx.command.name)
```

**特点**：
- 薄层入口点，无业务逻辑
- 易于添加新命令（创建新的 `@cli.command()`)

---

## 如何扩展

### 添加新命令

例如，添加 `export` 命令导出已保存的论文：

1. 在 `commands.py` 中创建新的 Command 类：
```python
@dataclass(slots=True)
class ExportCommand:
    config: AppConfig
    # ... 其他依赖

    def execute(self) -> None:
        # 实现导出逻辑
        pass
```

2. 在 `runner.py` 中添加运行方法：
```python
def run_export(self, action: str) -> None:
    # 创建组件并执行
    pass
```

3. 在 `ui.py` 中添加 Click 命令：
```python
@cli.command("export")
@click.pass_context
def export_cmd(ctx):
    runner = CommandRunner(ctx.obj)
    runner.run_export(action=ctx.command.name)
```

### 添加新的输出格式

例如，支持 Markdown 输出：

1. 在 `renderers/markdown.py` 中实现新的 Writer：
```python
class MarkdownOutputWriter(OutputWriter):
    def write_query_result(self, papers, query, scope):
        # 格式化为 Markdown
        pass

    def finalize(self, action):
        # 写入 .md 文件
        pass
```

2. 在 `renderers/__init__.py` 中更新 `create_output_writer()` 工厂：
```python
from PaperTracker.renderers.markdown import MarkdownOutputWriter

def create_output_writer(config: AppConfig) -> OutputWriter:
    if config.output_format == "markdown":
        return MarkdownOutputWriter(config.output_dir)
    elif config.output_format == "json":
        return JsonFileWriter(config.output_dir)
    return ConsoleOutputWriter()
```

3. 在配置文件中使用：
```yaml
output:
  format: markdown
```

### 添加新的数据源

例如，支持 Google Scholar：

1. 创建 `sources/scholar/` 包，实现 Scholar API 客户端和源

2. 在 `factories.py` 中添加工厂方法：
```python
@staticmethod
def create_scholar_service(config: AppConfig) -> PaperSearchService:
    return PaperSearchService(
        source=ScholarSource(
            client=ScholarApiClient(),
            # ...
        )
    )
```

3. 根据配置选择数据源（例如通过 `config.source_type` 字段）

---

## 配置扩展性

`AppConfig` 可以轻松扩展新的配置项：

1. 在 `config.py` 的 `AppConfig` dataclass 中添加字段
2. 在 `load_config()` 中添加解析逻辑
3. 相关模块通过 `config` 参数获取新配置

例如，`output.dir` 的添加：

```python
@dataclass(frozen=True, slots=True)
class AppConfig:
    # ... 其他字段
    output_dir: str = "output"  # 新增

# 在 load_config() 中
output_dir = str(_get(raw, "output.dir", "output") or "output")

# 在 JsonFileWriter 中使用
self.output_dir = config.output_dir
```

---