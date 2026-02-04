# Markdown 导出指南

本文档介绍 Paper Tracker 的 Markdown 导出能力，包括配置、模板与输出结构。

---

## 1. 快速启用

在配置文件中启用 Markdown 输出：

```yml
output:
  base_dir: output
  formats: [markdown]

  markdown:
    template_dir: template/markdown/
    document_template: document.md
    paper_template: paper.md
    paper_separator: "\n\n---\n\n"
```

运行：

```bash
paper-tracker --config config/default.yml search
```

输出目录结构：

```
output/
  markdown/
    search_20260204_143022.md
```

---

## 2. 输出内容

Markdown 输出基于 `PaperView` 字段渲染，包含：

- 标题与作者
- 日期与分类
- PDF/Abstract 链接
- 摘要与翻译（如有）
- LLM Summary（如有）

缺失字段对应的整行会被自动移除。

---

## 3. 模板结构

模板位于 `template/markdown/`：

- `document.md`：文档级模板
- `paper.md`：论文级模板

模板占位符使用 `{field_name}`，支持以下字段：

```
paper_number, title, source, authors, doi,
updated, primary_category, categories, pdf_url,
abstract_url, abstract, abstract_translation,
tldr, motivation, method, result, conclusion,
timestamp, query
```

占位符对应字段为空时，该行会被删除。

---

## 4. 输出文件命名

输出文件命名格式固定为：`<action>_<timestamp>.md`

- `<action>`：命令名称（如 `search`）
- `<timestamp>`：生成时间（格式：`YYYYMMDD_HHMMSS`）

示例：`search_20260204_143022.md`

---

## 5. 自定义模板建议

- 尽量使用 Markdown 标题与列表结构，保证可读性
- 对可选字段单独占一行，便于条件渲染自动删除
- 保持模板简洁，避免复杂逻辑（仅支持占位符替换）
