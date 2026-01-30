# 存储与去重

## 概述

PaperTracker 通过基于 SQLite 的状态管理支持增量输出与去重。启用后，系统会跟踪已见过的论文，并在后续搜索中仅输出新的论文。

## 配置

在你的 YAML 配置文件中添加 `state` 段落：

```yaml
state:
  enabled: true
  db_path: /absolute/path/to/database/state.db
```

### 参数

- **enabled**（布尔，默认：`false`）：启用或禁用状态管理
  - `true`：仅输出之前未见过的新论文
  - `false`：输出所有论文（不去重）

- **db_path**（字符串，默认：`database/state.db`）：SQLite 数据库文件的绝对路径或项目相对路径
  - 若目录不存在会自动创建
  - 若设置为 `null`，则使用 `database/state.sqlite`

## 工作原理

### 去重逻辑

1. **首次运行**：所有论文都视为新论文并输出
2. **后续运行**：论文会与数据库进行过滤比对
   - `source` 与 `source_id` 相同的论文视为重复
   - 仅输出新的论文
   - 所有抓取到的论文（新论文与重复论文）都会被标记为已见

### 数据库结构

系统使用单表 [`seen_papers`](../src/PaperTracker/storage/db.py)，结构如下：

- **source**：数据源标识（例如 "arxiv"）
- **source_id**：数据源内的唯一 ID
- **doi**：数字对象标识符（可选）
- **doi_norm**：规范化 DOI，用于跨来源匹配（自动生成）
- **title**：论文标题
- **first_seen_at**：首次发现的 UTC 时间戳

### DOI 提取

TODO: arxiv 实际上没有多少 doi，尤其对于新文章，所以对 aixiv 实际上没什么作用

系统会在可用时自动从 arXiv 论文中提取 DOI：
- 来自 `arxiv_doi` 或 `doi` 字段
- 来自包含 "doi.org" 的链接

DOI 规范化会移除常见前缀（`https://doi.org/`、`http://dx.doi.org/`、`doi:`）并转换为小写，以便一致匹配。

## 使用示例

### 初始配置

[`config/default.yml`](../config/default.yml:10)：
```yaml
state:
  enabled: true
  db_path: /home/user/paper-tracker/database/state.db

queries:
  - NAME: neural_compression
    OR:
      - Neural Compression
      - Learned Compression
```

### 第一次运行

```bash
paper-tracker --config config/default.yml search
```

输出：
```
State management enabled: /home/user/paper-tracker/database/state.db
Fetched 20 papers
New papers: 20 (filtered 0 duplicates)
```

### 第二次运行（相同查询）

```bash
paper-tracker --config config/default.yml search
```

输出：
```
State management enabled: /home/user/paper-tracker/database/state.db
Fetched 20 papers
New papers: 3 (filtered 17 duplicates)
```

仅会输出自上次运行以来新增的 3 篇论文。

## 实现细节

### 模块结构

- [`storage/__init__.py`](../src/PaperTracker/storage/__init__.py)：模块导出
- [`storage/db.py`](../src/PaperTracker/storage/db.py)：数据库初始化与结构
- [`storage/state.py`](../src/PaperTracker/storage/state.py)：[`SqliteStateStore`](../src/PaperTracker/storage/state.py) 实现

### 关键方法

- [`filter_new(papers)`](../src/PaperTracker/storage/state.py)：筛选仅保留新论文
- [`mark_seen(papers)`](../src/PaperTracker/storage/state.py)：在数据库中标记为已见
- [`close()`](../src/PaperTracker/storage/state.py)：关闭数据库连接

### 集成点

1. **配置**：[`config.py`](../src/PaperTracker/config.py) 中的 [`StateConfig`](../src/PaperTracker/config.py) 数据类
2. **模型**：[`Paper`](../src/PaperTracker/core/models.py) 模型新增 [`doi`](../src/PaperTracker/core/models.py) 字段
3. **解析器**：[`parser.py`](../src/PaperTracker/sources/arxiv/parser.py) 中的 DOI 提取
4. **CLI**：[`cli.py`](../src/PaperTracker/cli.py) 中的状态存储初始化与过滤

## 限制

- **单进程**：不支持并发访问。并行运行请使用不同的 `db_path`。
- **路径展开**：不支持 `~` 与环境变量。
- **无降级**：数据库初始化失败将直接终止搜索。

## 故障排查

### 数据库被锁

如果出现 "database is locked" 错误，请确保没有其他 PaperTracker 进程在使用同一数据库文件。

### 权限不足

确认 `db_path` 目录可写：
```bash
mkdir -p /path/to/state
chmod 755 /path/to/state
```

### 重置状态

要从头开始并再次看到所有论文：
```bash
rm /path/to/database/state.db
```
