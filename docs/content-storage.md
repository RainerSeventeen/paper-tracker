# 内容存储

## 概述

PaperTracker 提供了一个可选的**内容存储**功能,可以将完整的论文元数据持久化到 SQLite 数据库中。该功能独立于去重功能,支持以下高级用例:

- 构建带有完整元数据的本地论文库
- 添加 LLM 增强字段(例如翻译、摘要)
- 查询历史论文集合
- 分析论文随时间的趋势

启用后,从 arXiv 获取的每篇论文都会存储完整的元数据,包括标题、作者、摘要、类别、URL 和时间戳。

## 配置

内容存储通过 YAML 配置文件中的 `state.content_storage_enabled` 选项控制。

### 基本设置

```yaml
state:
  enabled: true                        # 必须启用才能使用内容存储
  db_path: null                        # 使用默认路径 database/papers.db
  content_storage_enabled: true        # 启用内容存储(默认配置已开启)
```

### 配置参数

- **`state.enabled`** (布尔值,必需): 必须为 `true` 才能启用内容存储
  - 内容存储依赖于去重功能(seen_papers 表)

- **`state.content_storage_enabled`** (布尔值): 启用/禁用完整内容存储
  - `true`: 将完整论文元数据保存到 `paper_content` 表
  - `false`: 仅跟踪已见论文用于去重(无完整内容)

- **`state.db_path`** (字符串,默认: `database/papers.db`): 数据库文件路径
  - 去重和内容存储共享此数据库
  - 绝对路径或项目相对路径
  - 如果为 `null`,默认使用 `database/papers.db`

## 工作原理

### 存储流程

1. **执行搜索**: 根据查询从 arXiv 获取论文
2. **去重**: 识别新论文(不在 `seen_papers` 中的论文)
3. **标记为已见**: 所有获取的论文插入/更新到 `seen_papers` 表
4. **内容存储**: 如果 `content_storage_enabled=true`,则将完整元数据保存到 `paper_content` 表

### 数据库模式

系统使用两个关联表:

#### `seen_papers` 表(去重)

跟踪之前见过的论文:

- `id`: 主键
- `source`: 数据源标识符(例如 "arxiv")
- `source_id`: 源内的唯一 ID(例如 "2601.21922")
- `doi`: 数字对象标识符(可选)
- `doi_norm`: 规范化的 DOI,用于跨源匹配
- `title`: 论文标题
- `first_seen_at`: 首次遇到时的 Unix 时间戳

#### `paper_content` 表(完整内容)

存储完整的论文元数据:

- `id`: 主键
- `seen_paper_id`: 外键,关联到 `seen_papers.id`
- `source`: 数据源标识符
- `source_id`: 唯一论文 ID
- `title`: 论文标题
- `authors`: JSON 数组,作者姓名
- `abstract`: 摘要文本
- `published_at`: 发布时间戳
- `updated_at`: 最后更新时间戳
- `fetched_at`: 创建此记录的时间
- `primary_category`: 主要 arXiv 类别
- `categories`: JSON 数组,所有类别
- `abstract_url`: 摘要页面链接
- `pdf_url`: PDF 文件链接
- `code_urls`: JSON 数组,代码仓库 URL(从 extra 提取)
- `project_urls`: JSON 数组,项目页面 URL(从 extra 提取)
- `doi`: 数字对象标识符
- `translation`: 翻译后的摘要文本（LLM 增强字段）
- `language`: 目标语言代码(例如 "zh", "en")
- `extra`: JSON 对象,附加元数据

**关键设计决策:**

- 通过 `seen_paper_id` 外键链接论文,确保引用完整性
- 不在 `seen_papers` 中的论文会被跳过并发出警告
- `fetched_at` 时间戳允许跟踪论文的检索时间
- JSON 字段支持灵活存储数组和嵌套数据
- 在 `seen_paper_id`、`source_id`、`fetched_at` 和 `primary_category` 上建立索引以提高查询效率

## 使用示例

### 示例 1: 启用内容存储

配置文件 (`config/papers.yml`):

```yaml
log:
  level: INFO
  to_file: true
  dir: log

state:
  enabled: true
  db_path: database/papers.db
  content_storage_enabled: true  # 启用完整内容存储

queries:
  - NAME: neural_compression
    OR:
      - Neural Image Compression
      - Learned Video Compression

search:
  max_results: 10
  sort_by: submittedDate
  sort_order: descending

output:
  format: text
```

运行搜索:

```bash
paper-tracker --config config/papers.yml search
```

输出:

```
State management enabled: database/papers.db
Content storage enabled: database/papers.db
Fetched 10 papers
New papers: 10 (filtered 0 duplicates)
[论文详情...]
```

### 示例 2: 查询统计信息

`PaperContentStore` 类提供了获取数据库统计信息的方法:

```python
from pathlib import Path
from PaperTracker.storage.db import DatabaseManager
from PaperTracker.storage.content import PaperContentStore

# 初始化数据库连接
db_manager = DatabaseManager(Path("database/papers.db"))
content_store = PaperContentStore(db_manager)

# 获取统计信息
stats = content_store.get_statistics()
print(f"Total records: {stats['total_records']}")
print(f"Unique papers: {stats['unique_papers']}")
print(f"Categories: {stats['categories']}")
```

**注意**: LLM 生成的翻译和摘要现在存储在独立的 `llm_generated` 表中,通过 `LLMGeneratedStore` 管理。详见 LLM 功能相关文档。

## 实现细节

### 模块结构

- **`storage/db.py`**: 数据库初始化、模式定义和 `DatabaseManager` 单例
- **`storage/deduplicate.py`**: `SqliteDeduplicateStore` 用于跟踪已见论文
- **`storage/content.py`**: `PaperContentStore` 用于完整论文元数据存储
- **`storage/__init__.py`**: 模块导出

### 关键类

#### `DatabaseManager`

使用单例模式管理共享的 SQLite 连接:

- 确保每个数据库路径只有一个连接
- 防止连接资源浪费和并发写入冲突
- 支持上下文管理器协议以自动清理
- 首次使用时初始化模式

#### `PaperContentStore`

处理完整论文内容存储(仅原始数据):

- `save_papers(papers)`: 保存论文列表的完整元数据
- `get_statistics()`: 获取数据库统计信息(总记录数、唯一论文数、类别等)

**注意**: LLM 相关数据(翻译、摘要)现在由 `LLMGeneratedStore` 管理,存储在独立的 `llm_generated` 表中。

### 集成点

1. **配置**: `config.py` 中的 `AppConfig` 数据类包含 `content_storage_enabled` 标志
2. **CLI**: `cli.py` 在启用时初始化 `DatabaseManager` 和 `PaperContentStore`
3. **数据库**: `db.py` 中的 `init_schema()` 自动创建模式
4. **去重**: 内容存储依赖 `seen_papers` 表建立外键关系

## 与去重的关系

内容存储和去重是**互补功能**:

| 功能 | 目的 | 表 | 必需 |
|------|------|-----|------|
| 去重 | 跟踪已见论文以过滤重复项 | `seen_papers` | 内容存储必需 |
| 内容存储 | 持久化完整论文元数据 | `paper_content` | 可选增强 |

**依赖关系**: 内容存储需要启用去重 (`state.enabled: true`),因为:
- `paper_content` 有指向 `seen_papers` 的外键
- 在保存内容之前必须先将论文标记为已见
- 这确保了引用完整性

**工作流程**:
1. 从 arXiv 获取论文
2. 去重识别新论文
3. 所有论文插入到 `seen_papers`(使用 UPSERT)
4. 如果启用内容存储,则将完整元数据保存到 `paper_content`

## 优势

### 对用户

- **本地库**: 构建可搜索的论文集合,无需依赖外部服务
- **离线访问**: 无需互联网连接即可查询论文元数据
- **自定义分析**: 分析趋势、跟踪研究领域、识别模式
- **LLM 集成**: 添加翻译、摘要或其他 AI 增强内容

### 对开发者

- **关注点分离**: 去重和内容存储使用独立的表
- **可扩展模式**: JSON 字段允许灵活的元数据,无需模式迁移
- **高效查询**: 对常见查询模式(时间、类别、source_id)建立索引
- **事务安全**: 单一连接防止并发写入冲突

## 限制

- **单进程**: 数据库不支持多进程并发写入
  - 并行运行时使用不同的 `db_path` 值
- **存储增长**: 完整内容存储会增加数据库大小
  - 长期运行的部署考虑定期清理或归档
- **无增量更新**: 论文在获取时按原样存储
  - 重新获取同一篇论文会创建重复条目(相同 source_id,不同 fetched_at)
- **外键约束**: 不在 `seen_papers` 中的论文无法存储
  - 正常操作中不应发生,但如果发生会发出警告

## 故障排查

### 内容未保存

**问题**: 论文出现在输出中但不在 `paper_content` 表中

**解决方案**:
1. 验证配置中 `state.content_storage_enabled: true`
2. 检查 `state.enabled: true`(内容存储必需)
3. 查找警告: `Paper X not in seen_papers, skipping content save`
4. 确保数据库路径可写

### 数据库锁定

**问题**: 错误 `database is locked`

**解决方案**: 确保没有其他 PaperTracker 进程正在使用同一数据库文件

```bash
# 检查正在运行的进程
ps aux | grep paper-tracker

# 终止冲突的进程
pkill -f paper-tracker
```

### 缺少字段

**问题**: 数据库中某些元数据字段为 `null`

**说明**: 并非所有论文都有所有字段(例如 DOI、代码 URL)
- 这是预期行为
- JSON 字段默认为空数组: `[]`
- 如果不可用,标量字段可能为 `null`

### 重置数据库

要重新开始并重新填充数据库:

```bash
rm database/papers.db
paper-tracker --config config/papers.yml search
```

## 未来增强

内容存储功能旨在支持:

1. **翻译服务**: 使用 LLM 自动翻译摘要
2. **论文推荐**: 分析存储的论文以建议相关工作
3. **导出功能**: 导出为 BibTeX、Markdown 或其他格式
4. **Web 界面**: 通过 Web UI 浏览和搜索存储的论文
5. **重复检测**: 使用 DOI 规范化进行跨源重复检测

这些功能可以在现有 `paper_content` 表的基础上构建,无需更改模式。

## 另见

- [存储和去重](./storage.md) - 仅使用去重功能
- [配置指南](./configuration.md) - 通用配置选项
- [测试指南](testing.md) - 测试存储功能
