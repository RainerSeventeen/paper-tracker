# TODO List

本文档记录项目的待办事项和性能优化建议。

## 性能优化

### 批量操作优化

**问题描述**：

当前 `PaperContentStore.save_papers` 方法中，每个论文都会执行一次 `SELECT` 查询来获取 `seen_paper_id`，效率低下。

**优化方案**：

使用批量查询和批量插入：

```python
def save_papers(self, papers: Sequence[Paper]) -> None:
    """Save full paper content to database.

    Args:
        papers: Papers to save (must already exist in seen_papers).
    """
    if not papers:
        return

    # 批量查询 seen_paper_id
    source_ids = [(p.source, p.id) for p in papers]
    placeholders = ','.join(['(?,?)'] * len(source_ids))
    query = f"SELECT source, source_id, id FROM seen_papers WHERE (source, source_id) IN ({placeholders})"
    flat_params = [item for pair in source_ids for item in pair]

    cursor = self.conn.execute(query, flat_params)
    id_map = {(row[0], row[1]): row[2] for row in cursor}

    # 批量插入
    rows = []
    for paper in papers:
        seen_paper_id = id_map.get((paper.source, paper.id))
        if not seen_paper_id:
            log.warning("Paper %s not in seen_papers, skipping", paper.id)
            continue

        code_urls = paper.extra.get("code_urls", [])
        project_urls = paper.extra.get("project_urls", [])

        rows.append((
            seen_paper_id,
            paper.source,
            paper.id,
            paper.title,
            json.dumps(list(paper.authors), ensure_ascii=False),
            paper.summary,
            int(paper.published.timestamp()) if paper.published else None,
            int(paper.updated.timestamp()) if paper.updated else None,
            paper.primary_category,
            json.dumps(list(paper.categories), ensure_ascii=False),
            paper.links.abstract,
            paper.links.pdf,
            json.dumps(code_urls, ensure_ascii=False),
            json.dumps(project_urls, ensure_ascii=False),
            paper.doi,
            json.dumps(dict(paper.extra), ensure_ascii=False)
        ))

    self.conn.executemany("""
        INSERT INTO paper_content (
            seen_paper_id, source, source_id, title, authors, summary,
            published_at, updated_at, primary_category, categories,
            abstract_url, pdf_url, code_urls, project_urls, doi, extra
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    self.conn.commit()
    log.debug("Saved %d papers to content store", len(rows))
```

**预期收益**：

- 减少数据库查询次数：从 N 次减少到 1 次（N 为论文数量）
- 提升插入效率：使用 `executemany` 批量插入
- 特别是在处理大量论文（>100）时，性能提升显著

**优先级**：中等（当前性能可接受，但处理大量论文时需要优化）

---

## 功能扩展

（暂无）

---

## 技术债务

（暂无）

---

## 文档待完善

（暂无）
