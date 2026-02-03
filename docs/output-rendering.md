# 输出渲染系统

## 概述

本文档完整说明 Paper Tracker 的输出渲染系统，包括视图模型架构、输出格式、配置选项、使用示例和扩展指南。

**核心设计理念**：通过视图模型（View Model）模式分离领域逻辑与展示逻辑，提供类型安全、易扩展的输出渲染系统。

---

## 目录

1. [架构设计](#架构设计)
2. [配置选项](#配置选项)
3. [输出格式](#输出格式)
4. [输出示例](#输出示例)
5. [扩展指南](#扩展指南)
6. [实现细节](#实现细节)
7. [技术优势](#技术优势)

---

## 架构设计

### 重构动机

在引入视图模型之前，输出渲染器直接使用领域模型 `Paper` 进行展示，存在以下问题：

1. **展示逻辑耦合**：日期格式化等展示逻辑分散在各个 renderer 中
2. **类型不明确**：LLM 生成的数据存储在 `Paper.extra` 字典中，缺乏类型提示和 IDE 支持
3. **职责不清**：领域模型既承担业务逻辑又承担展示职责
4. **维护困难**：修改输出格式需要在多个 renderer 中重复修改

### 分层结构

```
┌─────────────────────────────────────────────┐
│           CLI Commands Layer                │
│          (cli/commands.py)                  │
│   • 搜索论文                                │
│   • LLM 增强                                │
└──────────────────┬──────────────────────────┘
                   │ Paper (领域模型)
                   ↓
┌─────────────────────────────────────────────┐
│            Mapper Layer                     │
│         (renderers/mapper.py)               │
│   • Paper → PaperView 转换                  │
│   • 日期格式化                              │
│   • LLM 数据提取                            │
└──────────────────┬──────────────────────────┘
                   │ PaperView (视图模型)
                   ↓
┌─────────────────────────────────────────────┐
│         Renderers Layer                     │
│   • ConsoleOutputWriter (控制台)            │
│   • JsonFileWriter (JSON 文件)              │
│   • [可扩展其他格式]                        │
└─────────────────────────────────────────────┘
                   │
                   ↓
              用户看到的输出
```

### 核心组件

#### 1. OutputWriter 协议 (`renderers/base.py`)

定义所有输出格式的统一接口：

```python
class OutputWriter(ABC):
    """Write command results to console or file."""

    @abstractmethod
    def write_query_result(
        self,
        papers: list[PaperView],
        query: SearchQuery,
        scope: SearchQuery | None,
    ) -> None:
        """处理单条查询的结果。

        Args:
            papers: 论文视图模型列表
            query: 产生这些结果的查询
            scope: 应用到查询的全局范围（可选）
        """

    @abstractmethod
    def finalize(self, action: str) -> None:
        """最终化输出（如写入文件）。

        Args:
            action: 命令名称（如 "search"）
        """
```

**实现类**：
- `ConsoleOutputWriter`：输出到控制台（通过日志系统）
- `JsonFileWriter`：累积结果并写入 JSON 文件

#### 2. 视图模型 (`renderers/view_models.py`)

**职责**：
- 定义面向展示的数据结构
- 将 LLM 数据从动态字典提升为显式字段
- 提供类型安全的展示数据接口

**设计特点**：

```python
@dataclass(frozen=True, slots=True)
class PaperView:
    """论文视图模型，用于输出渲染。

    将展示关注点与领域模型 (Paper) 分离。
    所有字段都支持 None 以优雅处理缺失数据。
    """

    # 基础元数据
    source: str                    # 数据源标识（如 "arxiv"）
    id: str                        # 源特定的唯一标识符
    title: str                     # 论文标题
    authors: Sequence[str]         # 作者列表
    abstract: str                  # 摘要文本

    # 时间信息（格式化为字符串以便展示）
    published: str | None          # 发布日期（YYYY-MM-DD 格式）
    updated: str | None            # 更新日期（YYYY-MM-DD 格式）

    # 分类信息
    primary_category: str | None   # 主要类别
    categories: Sequence[str]      # 额外类别/标签

    # 链接
    abstract_url: str | None       # 摘要/落地页 URL
    pdf_url: str | None            # PDF 直接链接
    doi: str | None                # 数字对象标识符

    # LLM 生成内容（翻译）
    abstract_translation: str | None = None

    # LLM 生成内容（结构化摘要）
    tldr: str | None = None        # Too Long; Didn't Read 总结
    motivation: str | None = None  # 研究动机和背景
    method: str | None = None      # 研究方法和途径
    result: str | None = None      # 实验结果和发现
    conclusion: str | None = None  # 结论和影响
```

**关键区别**（vs 领域模型）：
| 字段 | Paper (领域模型) | PaperView (视图模型) |
|------|------------------|---------------------|
| 日期字段 | `datetime \| None` | `str \| None` (格式化) |
| LLM 数据 | `extra: Mapping` (动态) | 显式字段 (静态类型) |
| 职责 | 业务逻辑 | 展示逻辑 |

#### 3. 映射器 (`renderers/mapper.py`)

**职责**：
- 实现 `Paper` → `PaperView` 的转换
- 集中处理日期格式化逻辑
- 从 `Paper.extra` 字典中提取 LLM 数据

**核心函数**：

```python
def format_datetime(dt: datetime | None) -> str | None:
    """格式化日期时间为 YYYY-MM-DD 字符串。"""
    return dt.strftime("%Y-%m-%d") if dt else None


def map_paper_to_view(paper: Paper) -> PaperView:
    """将 Paper 领域模型映射为 PaperView 展示模型。

    提取基础字段和 Paper.extra 中的 LLM 增强数据。
    将时间字段格式化为字符串以保证展示一致性。
    """
    # 1. 格式化日期
    published = format_datetime(paper.published)
    updated = format_datetime(paper.updated)

    # 2. 提取 LLM 翻译数据
    translation_data = paper.extra.get("translation", {})
    abstract_translation = translation_data.get("summary_translated")

    # 3. 提取 LLM 摘要数据
    summary_data = paper.extra.get("summary", {})
    tldr = summary_data.get("tldr")
    motivation = summary_data.get("motivation")
    method = summary_data.get("method")
    result = summary_data.get("result")
    conclusion = summary_data.get("conclusion")

    # 4. 构造视图模型
    return PaperView(
        source=paper.source,
        id=paper.id,
        title=paper.title,
        authors=paper.authors,
        abstract=paper.abstract,
        published=published,
        updated=updated,
        primary_category=paper.primary_category,
        categories=paper.categories,
        abstract_url=paper.links.abstract,
        pdf_url=paper.links.pdf,
        doi=paper.doi,
        abstract_translation=abstract_translation,
        tldr=tldr,
        motivation=motivation,
        method=method,
        result=result,
        conclusion=conclusion,
    )


def map_papers_to_views(papers: Sequence[Paper]) -> list[PaperView]:
    """批量映射论文到视图模型。"""
    return [map_paper_to_view(p) for p in papers]
```

---

## 配置选项

### output 配置段

在配置文件（`config.yml`）中设置输出选项：

```yaml
output:
  format: text    # 输出格式：text 或 json
  dir: output     # JSON 文件输出目录（可选，默认 "output"）
```

### 配置参数详解

#### `format`（必选）

输出格式类型：

- **`text`**：控制台文本输出
  - 通过日志系统输出到标准输出
  - 人类友好的格式化展示
  - 适合交互式查看

- **`json`**：JSON 文件输出
  - 将结果保存为 JSON 文件
  - 文件名格式：`<action>_<MMDDHHMMSS>.json`
  - 适合程序化处理和存档

#### `dir`（可选，仅 JSON 格式使用）

- **默认值**：`output`
- **说明**：指定 JSON 文件的输出目录
- **示例**：
  ```yaml
  output:
    format: json
    dir: custom_output  # 输出到 custom_output/ 目录
  ```

### 配置示例

#### 示例 1: 控制台输出

```yaml
output:
  format: text
```

#### 示例 2: JSON 文件输出

```yaml
output:
  format: json
  dir: results  # 输出到 results/ 目录
```

---

## 输出格式

### 1. Console 文本输出

#### 基础输出格式

```
1. Learned Image Compression with Diffusion Models
   Authors: Zhang, Wei; Li, Ming; Chen, Yang
   Category: cs.CV
   Published: 2025-01-15  Updated: 2025-01-20
   Abs: https://arxiv.org/abs/2501.12345
   PDF: https://arxiv.org/pdf/2501.12345.pdf

2. Neural Video Compression via Temporal Context
   Authors: Wang, Hao; Liu, Jie
   Category: cs.CV
   Published: 2025-01-12  Updated: 2025-01-12
   Abs: https://arxiv.org/abs/2501.11223
   PDF: https://arxiv.org/pdf/2501.11223.pdf
```

#### 带 LLM 翻译的输出

当启用 LLM 翻译功能（`llm.enable_translation: true`）时：

```
1. Learned Image Compression with Diffusion Models
   Authors: Zhang, Wei; Li, Ming
   Category: cs.CV
   Published: 2025-01-15  Updated: 2025-01-20
   Abs: https://arxiv.org/abs/2501.12345
   PDF: https://arxiv.org/pdf/2501.12345.pdf
   Abs Translation: 本文提出了一种基于扩散模型的学习图像压缩方法。
                    传统的学习压缩方法在极低码率下重建质量不佳...
```

#### 带 LLM 摘要的输出

当启用 LLM 摘要功能（`llm.enable_summary: true`）时：

```
1. Learned Image Compression with Diffusion Models
   Authors: Zhang, Wei; Li, Ming
   Category: cs.CV
   Published: 2025-01-15  Updated: 2025-01-20
   Abs: https://arxiv.org/abs/2501.12345
   PDF: https://arxiv.org/pdf/2501.12345.pdf
   --- Summary ---
   TLDR: 提出基于扩散模型的图像压缩框架，在低码率下超越传统编解码器
   Motivation: 现有学习压缩方法在极低码率下重建质量不佳，扩散模型可生成高质量图像
   Method: 设计条件扩散模型作为解码器，结合率失真优化的编码器训练
   Result: 在 Kodak 数据集上，PSNR 提升 2.1dB，主观质量显著改善
   Conclusion: 扩散模型为学习图像压缩提供了新方向，但推理速度仍需优化
```

#### 完整 LLM 增强输出

同时启用翻译和摘要（`enable_translation: true` + `enable_summary: true`）：

```
1. Learned Image Compression with Diffusion Models
   Authors: Zhang, Wei; Li, Ming
   Category: cs.CV
   Published: 2025-01-15  Updated: 2025-01-20
   Abs: https://arxiv.org/abs/2501.12345
   PDF: https://arxiv.org/pdf/2501.12345.pdf
   Abs Translation: 本文提出了一种基于扩散模型的学习图像压缩方法...
   --- Summary ---
   TLDR: 提出基于扩散模型的图像压缩框架，在低码率下超越传统编解码器
   Motivation: 现有学习压缩方法在极低码率下重建质量不佳
   Method: 设计条件扩散模型作为解码器，结合率失真优化的编码器训练
   Result: 在 Kodak 数据集上，PSNR 提升 2.1dB
   Conclusion: 扩散模型为学习图像压缩提供了新方向
```

### 2. JSON 文件输出

#### 基础 JSON 结构

```json
{
  "action": "search",
  "timestamp": "2025-02-03T10:30:45",
  "results": [
    {
      "query_name": "neural_compression",
      "query_fields": {
        "TEXT": {
          "OR": ["Neural Image Compression", "Learned Video Compression"]
        }
      },
      "scope_fields": {
        "CATEGORY": {
          "OR": ["cs.CV", "cs.LG"]
        }
      },
      "papers": [
        {
          "source": "arxiv",
          "id": "2501.12345",
          "title": "Learned Image Compression with Diffusion Models",
          "authors": ["Zhang, Wei", "Li, Ming", "Chen, Yang"],
          "abstract": "We propose a novel approach...",
          "published": "2025-01-15",
          "updated": "2025-01-20",
          "primary_category": "cs.CV",
          "categories": ["cs.CV", "cs.LG"],
          "links": {
            "abstract": "https://arxiv.org/abs/2501.12345",
            "pdf": "https://arxiv.org/pdf/2501.12345.pdf"
          },
          "doi": null
        }
      ]
    }
  ]
}
```

#### 带 LLM 数据的 JSON 输出

当启用 LLM 功能时，JSON 中会包含额外字段：

```json
{
  "papers": [
    {
      "source": "arxiv",
      "id": "2501.12345",
      "title": "Learned Image Compression with Diffusion Models",
      "authors": ["Zhang, Wei", "Li, Ming"],
      "abstract": "We propose...",
      "published": "2025-01-15",
      "updated": "2025-01-20",
      "primary_category": "cs.CV",
      "categories": ["cs.CV", "cs.LG"],
      "links": {
        "abstract": "https://arxiv.org/abs/2501.12345",
        "pdf": "https://arxiv.org/pdf/2501.12345.pdf"
      },
      "doi": null,

      // LLM 翻译字段（如启用）
      "abstract_translation": "本文提出了一种基于扩散模型的学习图像压缩方法...",

      // LLM 摘要字段（如启用）
      "summary": {
        "tldr": "提出基于扩散模型的图像压缩框架，在低码率下超越传统编解码器",
        "motivation": "现有学习压缩方法在极低码率下重建质量不佳",
        "method": "设计条件扩散模型作为解码器，结合率失真优化的编码器训练",
        "result": "在 Kodak 数据集上，PSNR 提升 2.1dB，主观质量显著改善",
        "conclusion": "扩散模型为学习图像压缩提供了新方向，但推理速度仍需优化"
      }
    }
  ]
}
```

**重要变更**：
- `extra` 字典不再输出（重构前包含所有动态数据）
- LLM 数据以显式字段输出，提供更好的类型安全性
- 仅在数据存在时才包含 LLM 字段（避免空字段）

---

## 输出示例

### 示例 1: 基础搜索（无 LLM）

**配置**：
```yaml
llm:
  enabled: false

output:
  format: text

queries:
  - NAME: compression
    OR: [Image Compression, Video Compression]

search:
  max_results: 3
```

**输出**：
```
[INFO] Executing query: compression
[INFO] Found 3 papers

1. Learned Image Compression with Diffusion Models
   Authors: Zhang, Wei; Li, Ming
   Category: cs.CV
   Published: 2025-01-15  Updated: 2025-01-20
   Abs: https://arxiv.org/abs/2501.12345
   PDF: https://arxiv.org/pdf/2501.12345.pdf

2. Neural Video Compression via Temporal Context
   Authors: Wang, Hao; Liu, Jie
   Category: cs.CV
   Published: 2025-01-12  Updated: 2025-01-12
   Abs: https://arxiv.org/abs/2501.11223
   PDF: https://arxiv.org/pdf/2501.11223.pdf

3. End-to-End Optimized Image Compression
   Authors: Chen, Yang
   Category: cs.CV
   Published: 2025-01-10  Updated: 2025-01-10
   Abs: https://arxiv.org/abs/2501.10001
   PDF: https://arxiv.org/pdf/2501.10001.pdf
```

### 示例 2: 仅翻译

**配置**：
```yaml
llm:
  enabled: true
  enable_translation: true
  enable_summary: false
  target_lang: zh

output:
  format: text
```

**输出**：
```
[INFO] LLM translation enabled
[INFO] Processing 3 papers with LLM...
[INFO] Executing query: compression
[INFO] Found 3 papers

1. Learned Image Compression with Diffusion Models
   Authors: Zhang, Wei; Li, Ming
   Category: cs.CV
   Published: 2025-01-15  Updated: 2025-01-20
   Abs: https://arxiv.org/abs/2501.12345
   PDF: https://arxiv.org/pdf/2501.12345.pdf
   Abs Translation: 本文提出了一种基于扩散模型的学习图像压缩方法。
                    通过将扩散模型作为解码器，我们实现了在极低码率下
                    的高质量图像重建...
```

### 示例 3: 仅摘要

**配置**：
```yaml
llm:
  enabled: true
  enable_translation: false
  enable_summary: true
  target_lang: zh
```

**输出**：
```
1. Learned Image Compression with Diffusion Models
   Authors: Zhang, Wei; Li, Ming
   Category: cs.CV
   Published: 2025-01-15  Updated: 2025-01-20
   Abs: https://arxiv.org/abs/2501.12345
   PDF: https://arxiv.org/pdf/2501.12345.pdf
   --- Summary ---
   TLDR: 提出基于扩散模型的图像压缩框架，在低码率下超越传统编解码器
   Motivation: 现有学习压缩方法在极低码率下重建质量不佳，扩散模型可生成高质量图像
   Method: 设计条件扩散模型作为解码器，结合率失真优化的编码器训练
   Result: 在 Kodak 数据集上，PSNR 提升 2.1dB，主观质量显著改善
   Conclusion: 扩散模型为学习图像压缩提供了新方向，但推理速度仍需优化
```

### 示例 4: JSON 输出

**配置**：
```yaml
output:
  format: json
  dir: results
```

**命令**：
```bash
paper-tracker --config config.yml search
```

**输出文件**：`results/search_02031030.json`

**文件内容**：
```json
{
  "action": "search",
  "timestamp": "2025-02-03T10:30:45",
  "results": [
    {
      "query_name": "compression",
      "query_fields": {
        "TEXT": {
          "OR": ["Image Compression", "Video Compression"]
        }
      },
      "papers": [
        {
          "source": "arxiv",
          "id": "2501.12345",
          "title": "Learned Image Compression with Diffusion Models",
          "authors": ["Zhang, Wei", "Li, Ming"],
          "abstract": "We propose a novel approach...",
          "published": "2025-01-15",
          "updated": "2025-01-20",
          "primary_category": "cs.CV",
          "categories": ["cs.CV", "cs.LG"],
          "links": {
            "abstract": "https://arxiv.org/abs/2501.12345",
            "pdf": "https://arxiv.org/pdf/2501.12345.pdf"
          },
          "doi": null
        }
      ]
    }
  ]
}
```

---

## 扩展指南

### 添加新的输出格式

假设要添加 **Markdown 表格**输出格式：

#### 步骤 1: 实现 OutputWriter

创建 `src/PaperTracker/renderers/markdown.py`：

```python
"""Markdown table output renderer."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PaperTracker.core.query import SearchQuery
from PaperTracker.renderers.base import OutputWriter
from PaperTracker.renderers.view_models import PaperView
from PaperTracker.utils.log import log


def render_markdown_table(papers: Iterable[PaperView]) -> str:
    """将论文视图渲染为 Markdown 表格。

    Args:
        papers: 论文视图的可迭代对象

    Returns:
        Markdown 格式的表格字符串
    """
    lines = [
        "| # | Title | Authors | Category | Published | Links |",
        "|---|-------|---------|----------|-----------|-------|",
    ]

    for idx, view in enumerate(papers, start=1):
        authors = ", ".join(view.authors[:2])  # 只显示前两位作者
        if len(view.authors) > 2:
            authors += " et al."

        links = []
        if view.abstract_url:
            links.append(f"[Abs]({view.abstract_url})")
        if view.pdf_url:
            links.append(f"[PDF]({view.pdf_url})")
        links_str = " ".join(links)

        lines.append(
            f"| {idx} | {view.title} | {authors} | "
            f"{view.primary_category or '-'} | {view.published or '-'} | {links_str} |"
        )

    return "\n".join(lines) + "\n"


class MarkdownFileWriter(OutputWriter):
    """将查询结果输出到 Markdown 文件。"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: list[tuple[str, str, list[PaperView]]] = []

    def write_query_result(
        self,
        papers: list[PaperView],
        query: SearchQuery,
        scope: SearchQuery | None,
    ) -> None:
        """累积查询结果。"""
        query_name = query.name or "unnamed"
        table = render_markdown_table(papers)
        self.results.append((query_name, table, papers))

    def finalize(self, action: str) -> None:
        """写入 Markdown 文件。"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%m%d%H%M")
        filename = self.output_dir / f"{action}_{timestamp}.md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {action.capitalize()} Results\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")

            for query_name, table, papers in self.results:
                f.write(f"## Query: {query_name}\n\n")
                f.write(f"Found {len(papers)} papers:\n\n")
                f.write(table)
                f.write("\n")

        log.info(f"Markdown results written to: {filename}")
```

#### 步骤 2: 更新工厂函数

编辑 `src/PaperTracker/renderers/__init__.py`：

```python
from PaperTracker.config import AppConfig
from PaperTracker.renderers.base import OutputWriter
from PaperTracker.renderers.console import ConsoleOutputWriter
from PaperTracker.renderers.json import JsonFileWriter
from PaperTracker.renderers.markdown import MarkdownFileWriter  # 新增

__all__ = ["OutputWriter", "create_output_writer"]


def create_output_writer(config: AppConfig) -> OutputWriter:
    """根据配置创建输出写入器。

    Args:
        config: 应用配置

    Returns:
        相应的 OutputWriter 实现
    """
    if config.output_format == "json":
        return JsonFileWriter(config.output_dir)
    elif config.output_format == "markdown":  # 新增
        return MarkdownFileWriter(config.output_dir)
    return ConsoleOutputWriter()
```

#### 步骤 3: 使用新格式

在配置文件中指定新格式：

```yaml
output:
  format: markdown
  dir: markdown_output
```

**输出示例** (`markdown_output/search_02031030.md`)：

```markdown
# Search Results

Generated: 2025-02-03T10:30:45

## Query: compression

Found 3 papers:

| # | Title | Authors | Category | Published | Links |
|---|-------|---------|----------|-----------|-------|
| 1 | Learned Image Compression with Diffusion Models | Zhang, Wei, Li, Ming et al. | cs.CV | 2025-01-15 | [Abs](https://arxiv.org/abs/2501.12345) [PDF](https://arxiv.org/pdf/2501.12345.pdf) |
| 2 | Neural Video Compression via Temporal Context | Wang, Hao, Liu, Jie | cs.CV | 2025-01-12 | [Abs](https://arxiv.org/abs/2501.11223) [PDF](https://arxiv.org/pdf/2501.11223.pdf) |
| 3 | End-to-End Optimized Image Compression | Chen, Yang | cs.CV | 2025-01-10 | [Abs](https://arxiv.org/abs/2501.10001) [PDF](https://arxiv.org/pdf/2501.10001.pdf) |
```

### 扩展更多格式

使用相同模式可以轻松添加其他格式：

#### CSV 输出

```python
class CsvFileWriter(OutputWriter):
    """将结果输出为 CSV 文件。"""

    def write_query_result(self, papers, query, scope):
        # 使用 csv.DictWriter 写入
        pass
```

#### LaTeX 输出

```python
class LatexFileWriter(OutputWriter):
    """将结果输出为 LaTeX 表格。"""

    def write_query_result(self, papers, query, scope):
        # 生成 LaTeX \begin{table}...\end{table}
        pass
```

#### HTML 输出

```python
class HtmlFileWriter(OutputWriter):
    """将结果输出为 HTML 页面。"""

    def write_query_result(self, papers, query, scope):
        # 生成 HTML 表格，可以包含样式
        pass
```

---

## 实现细节

### 1. 命令层集成

**文件**：`src/PaperTracker/cli/commands.py`

```python
from PaperTracker.renderers.mapper import map_papers_to_views

@dataclass(slots=True)
class SearchCommand:
    config: AppConfig
    search_service: PaperSearchService
    output_writer: OutputWriter
    llm_service: LLMService | None = None

    def execute(self) -> None:
        """执行搜索命令。"""
        for query in self.config.queries:
            # 1. 搜索论文
            papers = self.search_service.search(query)

            # 2. LLM 增强（如果启用）
            if self.llm_service:
                infos = self.llm_service.generate_batch(papers)
                # 保存 LLM 数据到数据库...
                # 注入到 Paper.extra
                papers = self.llm_service.enrich_papers(papers, infos)

            # 3. 映射为视图模型
            paper_views = map_papers_to_views(papers)

            # 4. 输出
            self.output_writer.write_query_result(
                paper_views, query, self.config.scope
            )
```

### 2. 日期格式化统一

所有日期格式化逻辑集中在 `mapper.py` 中：

```python
def format_datetime(dt: datetime | None) -> str | None:
    """格式化日期时间为 YYYY-MM-DD 字符串以便展示。

    Args:
        dt: Datetime 对象或 None

    Returns:
        格式化的日期字符串，输入为 None 时返回 None
    """
    return dt.strftime("%Y-%m-%d") if dt else None
```

**优势**：
- **格式一致性**：所有输出格式使用相同的日期格式
- **单一职责**：渲染器不需要关心如何格式化日期
- **易于修改**：修改日期格式只需改一个地方

### 3. LLM 数据提取

从动态字典提升为类型安全的字段：

```python
# 提取翻译数据
translation_data = paper.extra.get("translation", {})
abstract_translation = translation_data.get("summary_translated")

# 提取摘要数据
summary_data = paper.extra.get("summary", {})
tldr = summary_data.get("tldr")
motivation = summary_data.get("motivation")
method = summary_data.get("method")
result = summary_data.get("result")
conclusion = summary_data.get("conclusion")
```

**重构前**（Console 渲染器）：

```python
# 分散的字典访问逻辑
if "translation" in paper.extra:
    trans = paper.extra["translation"]
    if trans.get("summary_translated"):
        lines.append(f"   Abs Translation: {trans['summary_translated']}")

if "summary" in paper.extra:
    summary = paper.extra["summary"]
    if summary.get("tldr"):
        lines.append(f"   TLDR: {summary['tldr']}")
```

**重构后**（Console 渲染器）：

```python
# 直接访问显式字段
if view.abstract_translation:
    lines.append(f"   Abs Translation: {view.abstract_translation}")

if view.tldr:
    lines.append(f"   TLDR: {view.tldr}")
```

### 4. 数据流转

```
Paper (core/models.py)
  └─> Mapper (renderers/mapper.py)
        ├─> 日期格式化: datetime → "YYYY-MM-DD"
        ├─> LLM 数据提取: extra dict → 显式字段
        └─> PaperView (renderers/view_models.py)
              └─> OutputWriter (renderers/base.py)
                    ├─> ConsoleOutputWriter → 控制台
                    ├─> JsonFileWriter → JSON 文件
                    └─> [其他格式] → 自定义输出
```

### 5. 文件结构

```
src/PaperTracker/
├── core/
│   └── models.py              # Paper (领域模型)
├── renderers/
│   ├── __init__.py            # 工厂函数: create_output_writer()
│   ├── base.py                # OutputWriter 协议定义
│   ├── view_models.py         # PaperView (视图模型) [新增]
│   ├── mapper.py              # Paper → PaperView 映射 [新增]
│   ├── console.py             # ConsoleOutputWriter 实现 [重构]
│   └── json.py                # JsonFileWriter 实现 [重构]
└── cli/
    └── commands.py            # SearchCommand 集成 [修改]
```

---

## 技术优势

### 1. 职责分离（Separation of Concerns）

**领域层** (`core.models.Paper`)：
- 表示业务实体
- 与数据源无关
- 包含业务逻辑

**展示层** (`renderers.view_models.PaperView`)：
- 专门用于输出渲染
- 包含格式化数据
- 展示逻辑与业务逻辑解耦

### 2. 类型安全（Type Safety）

**重构前**：
```python
# 运行时字典查找，无类型检查
summary = paper.extra.get("summary", {})
if summary.get("tldr"):  # 可能拼写错误，IDE 无法检测
    print(summary["tLdr"])  # 拼写错误！运行时才会发现
```

**重构后**：
```python
# 编译时类型检查
if view.tldr:  # IDE 自动补全，类型检查
    print(view.tldr)  # 拼写错误会被 IDE 立即标记
```

### 3. 维护性提升（Improved Maintainability）

| 任务 | 重构前 | 重构后 |
|------|--------|--------|
| 修改日期格式 | 修改所有 renderer | 修改 `format_datetime()` |
| 添加新字段 | 修改所有 renderer | 在 `PaperView` 中声明 |
| 添加新格式 | 实现新 renderer，重复逻辑 | 实现新 renderer，复用 mapper |

**示例**：添加 DOI 字段到输出

**重构前**：需要修改 3 个文件
- `renderers/console.py`：添加 DOI 展示逻辑
- `renderers/json.py`：添加 DOI 到 JSON
- 其他自定义 renderer：逐个修改

**重构后**：只需修改 1 个文件
- `renderers/view_models.py`：`doi: str | None` 已存在
- 所有 renderer 自动获得 DOI 字段访问

### 4. 测试友好（Testability）

**Mapper 纯函数测试**：
```python
def test_map_paper_with_llm_data():
    paper = Paper(
        source="arxiv",
        id="2501.12345",
        title="Test Paper",
        authors=["Author A"],
        abstract="Abstract",
        published=datetime(2025, 1, 15),
        updated=None,
        extra={
            "translation": {"summary_translated": "测试翻译"},
            "summary": {"tldr": "测试 TLDR"}
        }
    )

    view = map_paper_to_view(paper)

    assert view.id == "2501.12345"
    assert view.published == "2025-01-15"
    assert view.abstract_translation == "测试翻译"
    assert view.tldr == "测试 TLDR"
```

**视图模型不可变性测试**：
```python
def test_paperview_immutability():
    view = PaperView(...)

    # 不可变，无法修改
    with pytest.raises(FrozenInstanceError):
        view.title = "Modified"
```

### 5. 向后兼容（Backward Compatibility）

**Console 输出**：用户体验完全一致
- 格式保持不变
- LLM 数据展示方式不变

**JSON 输出**：结构基本一致
- 移除 `extra` 字典（动态数据）
- LLM 字段以显式结构输出
- 程序化解析更容易（有明确的字段名）

### 6. 扩展性（Extensibility）

**添加新输出格式无需修改现有代码**：
1. 实现新的 `OutputWriter`
2. 在工厂函数中注册
3. 配置文件中使用

**添加新展示字段**：
1. 在 `PaperView` 中声明
2. 在 mapper 中提取
3. 所有 renderer 自动支持

---

## 代码统计

本次重构的代码变更：

```
src/PaperTracker/cli/commands.py          |  6 ++-
src/PaperTracker/renderers/base.py        |  6 +--
src/PaperTracker/renderers/console.py     | 78 +++++++++-------------
src/PaperTracker/renderers/json.py        | 60 +++++++++++++-----
src/PaperTracker/renderers/mapper.py      | 84 +++++++++++++++++++++++++ [新增]
src/PaperTracker/renderers/view_models.py | 69 ++++++++++++++++++++++ [新增]
6 files changed, 229 insertions(+), 74 deletions(-)
```

**总结**：
- **新增**：153 行代码（2 个新文件）
- **重构**：74 行代码（4 个修改的文件）
- **净增**：229 行，删除 74 行

---

## 相关文档

- **[CLI 架构设计](cli-architecture.md)** - 命令层的整体架构
- **[LLM 功能说明](llm-features.md)** - LLM 增强功能的详细说明
- **[配置说明](configuration.md)** - 配置文件格式和选项
- **[内容存储](content-storage.md)** - 数据库存储机制

---

## 未来改进

### 功能改进

1. **更多输出格式**
   - LaTeX 表格（适合学术论文）
   - CSV 文件（适合 Excel 导入）
   - HTML 页面（带样式的网页展示）
   - Markdown 表格（适合 README 文档）

2. **自定义字段映射**
   - 允许用户配置哪些字段输出到哪些格式
   - 支持字段重命名和过滤

3. **多语言支持**
   - 视图模型可以包含多语言版本的字段
   - 根据用户配置选择展示语言

4. **模板系统**
   - 允许用户自定义输出模板
   - 支持 Jinja2 等模板引擎

### 架构改进

1. **输出管道**
   - 支持多个输出格式同时使用
   - 构建输出处理管道

2. **过滤和排序**
   - 在视图层添加过滤逻辑
   - 支持自定义排序规则

3. **增量输出**
   - 支持流式输出（对大量论文）
   - 避免内存累积

4. **输出验证**
   - 验证输出格式的正确性
   - 提供输出质量检查
