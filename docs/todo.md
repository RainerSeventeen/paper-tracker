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

### 接受更新推送

**问题描述**：

目前去重逻辑只按 `source_id` 判断，未记录论文上次 `updated_at` / 摘要变化，无法识别并区分“更新”与“新论文”。开启“接受老文章更新推送”的开关后，会漏报或误报。

**优化方案**：

- 在 `seen_papers` 增加 `last_updated_at`、`last_summary_hash`（或等价字段），用于判定是否发生有效更新。
- 同一 `source_id` 再次出现时，若 `updated_at` 或摘要 hash 变更，则标记为 update 并推送；否则按已读过滤。
- 渲染输出增加“更新”标记（例如在 `Paper.extra` 放入 `is_update` / `previous_updated_at`）。
- 开启更新推送时建议将排序切换到 `lastUpdatedDate` 以避免更新被排后。

**优先级**：中等（需要状态扩展；可先按 updated_at 判定，再逐步加入摘要 hash）

---

## 技术债务

（暂无）

---

## 文档待完善

（暂无）
