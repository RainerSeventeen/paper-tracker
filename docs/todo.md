# TODO List

本文档记录项目的待办事项和性能优化建议。

## LLM 集成功能

### 0. OpenAI 兼容 API 统一层（基础设施）

**说明**：
创建统一的 LLM 调用接口，支持任意 OpenAI 兼容的 API（DeepSeek、SiliconFlow、自建模型等）。这是所有 LLM 功能的基础。

- **核心函数**：`_chat_completions_request(base_url, api_key, model, messages, temperature, max_tokens, timeout)`
- **适配特性**：
  - 兼容三种 URL 写法（`api.xxx.com` / `api.xxx.com/v1` / `api.xxx.com/v1/chat/completions`）
  - 自动规范化为完整端点
  - 支持超时和错误重试机制
  - 支持自定义 temperature 和 max_tokens
- **配置示例**：
  ```yaml
  llm:
    base_url: "https://api.deepseek.com"        # 或 https://api.siliconflow.cn
    model: "deepseek-chat"                      # 或 Qwen/Qwen3-8B
    api_key_env: "OPENAI_COMPAT_API_KEY"
    temperature: 0.2
    max_tokens: 1024
  ```
- **参考实现**：`Arxiv-tracker/arxiv_tracker/llm.py:_chat_completions_request()`
- **优先级**：**高（必需，先实现）**

---

### 1. 论文摘要翻译（核心功能 - 优先实现）

**说明**：
将英文论文的题目、摘要字段翻译成中文。这是成本最低、价值最确定的 LLM 应用。

- **输入**：论文的 `title`、`summary`（arXiv 官方摘要）
- **输出**：`title_zh`、`summary_zh`
- **特点**：
  - ✅ Token 消耗最低（200-400 tokens/篇）
  - ✅ 成本低廉（可用免费 SiliconFlow API）
  - ✅ 质量稳定（100% 保留原意，不会改写）
  - ✅ 速度快（简单翻译，无需 LLM 思考）
- **实现方案**：
  ```python
  def translate_paper(item):
      """翻译论文题目和摘要"""
      messages = [
          {"role": "system", "content": "You are a precise academic translator..."},
          {"role": "user", "content": f"""
Translate to Simplified Chinese. Return JSON: {{"title_zh": "...", "summary_zh": "..."}}
Do not add commentary or change meaning.

Title: {item['title']}
Abstract: {item['summary']}
"""}
      ]
      result = call_llm(messages, temperature=0.0, max_tokens=800)
      return parse_json_loose(result)
  ```
- **配置示例**：
  ```yaml
  llm:
    enabled: true
    mode: "translate"  # translate | structure | both
    translate:
      enabled: true
      target_lang: "Chinese"
  ```
- **参考实现**：`Arxiv-tracker/arxiv_tracker/llm.py:call_llm_translate()`
- **优先级**：**⭐⭐⭐ 高（先做这个）**

---

### 2. 论文摘要结构化分析（可选增强）

**说明**：
使用 LLM 将论文摘要分解为结构化字段（动机、方法、结果、结论等）。适合需要更深度分析或构建知识图谱的场景。

#### 2.1 结构化字段提取
- **输出字段**：
  ```python
  {
      "tldr": "Too Long; Didn't Read（一句话总结）",
      "motivation": "研究动机和问题定义",
      "method": "核心方法和技术",
      "result": "实验结果和性能",
      "conclusion": "主要结论和启示"
  }
  ```
- **调用方式**：使用 Pydantic + function calling 获得结构化输出
- **特点**：
  - ✅ 论文内容结构化，便于后续处理
  - ✅ 支持按维度展示（只看方法、只看结果等）
  - ❌ Token 消耗较多（与翻译差不多）
  - ❌ LLM 分解质量依赖摘要原质量
- **参考实现**：`daily-arXiv-ai-enhanced/ai/enhance.py + structure.py`
- **优先级**：**中（可选，日后加）**

#### 2.2 并行处理优化
- **并行度**：使用 ThreadPoolExecutor 多线程加速（参考 daily-arXiv-ai-enhanced 的实现）
- **容错机制**：JSON 解析失败时自动用默认值填充
- **敏感词过滤**：可选敏感词检测和过滤（中国合规需求）
- **代码链接提取**：从摘要中自动提取 GitHub 链接和 star 数

---

### 3. LLM 生成式摘要（高级功能 - 可选）

**说明**：
使用 LLM 生成全新的总结（而非翻译或分解）。成本较高，但可作为高级选项。

#### 3.1 简洁双语总结
- **输出**：`digest_en` + `digest_zh` 两个字段
- **内容**：每段涵盖动机、方法、结果（共 1-2 段，合计 150-200 词）
- **成本**：中等（600-1000 tokens）
- **参考实现**：`Arxiv-tracker/arxiv_tracker/llm.py:call_llm_bilingual_summary()`
- **优先级**：**低（除非用户明确需要）**

#### 3.2 两阶段深度摘要
- **输出**：
  - `tldr`：1-2 句简洁总结
  - `method_card`：方法卡片（任务、方法、设计、数据、结果、局限）
  - `discussion`：3-5 个讨论问题
- **成本**：较高（900+ tokens）
- **参考实现**：`Arxiv-tracker/arxiv_tracker/llm.py:call_llm_two_stage()`
- **优先级**：**低（高级用户选项）**

---

### 4. 启发式摘要兜底

**说明**：
当 LLM 不可用或调用失败时，使用启发式算法降级处理。

- **实现内容**：
  - 关键词和任务检测（TASK_HINTS: Open-Vocabulary, Segmentation, Detection, Grounding, 3D Vision, Vision-Language 等）
  - 已知数据集识别（COCO, LVIS, ADE20K, ImageNet, LAION 等）
  - 摘要首句提取作为备用总结
- **优点**：保证无 LLM 时仍能输出有意义的内容
- **参考实现**：`Arxiv-tracker/arxiv_tracker/summarizer.py:heuristic_*` 函数
- **优先级**：**中（实现难度低，改善用户体验）**

---

### 5. 用户选择配置

**说明**：
允许用户灵活选择 LLM 处理模式。

```yaml
llm:
  enabled: true

  # 选择模式：translate | structure | bilingual | two_stage | all
  mode: "translate"

  # 翻译模式配置
  translate:
    enabled: true
    target_lang: "Chinese"

  # 结构化分析配置
  structure:
    enabled: false
    parallel_workers: 3
    check_sensitive: true  # 敏感词过滤

  # 生成式摘要配置（高级）
  generate:
    enabled: false
    type: "bilingual"  # bilingual | two_stage
    language: "both"
```

**模式说明**：
- `translate`：仅翻译（推荐，成本最低）
- `structure`：仅结构化分析（深度分析）
- `bilingual`：生成双语总结（创意总结）
- `two_stage`：生成两阶段摘要（完整分析）
- `all`：所有模式都运行（成本最高，提供最多选择）

- **优先级**：**中（第一版可以简化，只支持 translate）**

---

## 展示和分发功能（来自 Arxiv-tracker 学习）

### 5. 邮件推送功能

**说明**：
支持定期推送论文摘要到邮箱。

- **功能特性**：
  - QQ SMTP 集成（465/SSL 或 587/STARTTLS）
  - 多收件人支持（逗号或分号分隔）
  - 邮件附件选项（Markdown 或 PDF）
  - 发送前双检查（幂等防重）
- **配置示例**：
  ```yaml
  email:
    enabled: true
    subject: "[arXiv] Daily Digest"
    smtp_server: "smtp.qq.com"
    smtp_port: 465
    tls: "ssl"
    detail: "full"  # simple | full
    max_items: 10
    attach_md: true
  ```
- **优先级**：中（增强用户参与度，但需要邮件服务配置）

### 6. HTML 网页生成（GitHub Pages）

**说明**：
自动生成美观的 HTML 页面，展示论文列表和摘要，支持 GitHub Pages 部署。

- **功能特性**：
  - 论文卡片布局（带链接、摘要、标签等）
  - 历史归档与分页
  - 折叠/展开摘要
  - 主题选择（暗色/浅色）
  - 链接直接跳转（Abs/PDF/Code/Project）
- **优先级**：中（提升视觉效果，吸引使用）

---

## 数据管理和质量功能（来自 Arxiv-tracker 学习）

### 7. 增强去重和新鲜度管理

**说明**：
持久化论文状态，防止重复推送，同时支持论文更新检测。

#### 7.1 持久化去重状态
- **存储**：JSON 或 SQLite（见 `.state/seen.json`）
- **特点**：
  - 成功输出后再写入（幂等性）
  - 跨天去重
  - 支持 freshness 配置（仅展示最近 N 天的论文）
- **配置示例**：
  ```yaml
  freshness:
    since_days: 3
    unique_only: true
    state_path: ".state/seen.json"
    fallback_when_empty: false  # 当无新增时是否回退展示
  ```

#### 7.2 论文更新检测（待实现）
- **需求**：记录 `last_updated_at` 和 `last_summary_hash`
- **行为**：同一 `source_id` 再次出现时，若 `updated_at` 或摘要变更，标记为 update
- **输出**：增加 `is_update` 和 `previous_updated_at` 字段到 `Paper.extra`
- **优先级**：低（需要状态扩展，当前可先按 `updated_at` 判定）

### 8. 自动分页抓取

**说明**：
避免每次只拿同一批前 N 条记录（arXiv API 默认按相关性排序）。

- **实现**：
  - 支持 `start` 参数分页
  - 循环递增 `start`，累计结果直到达到 `max_results`
  - 防止同一批重复
- **益处**：发现更多相关论文，提升覆盖率
- **优先级**：中（需要修改 arXiv 查询逻辑）

### 9. 链接提取和补全

**说明**：
自动从论文页面提取代码、项目、补充材料等链接。

- **链接类型**：
  - 代码仓库（GitHub 等）
  - 项目主页
  - 补充材料
  - 相关论文
- **兜底策略**：若链接缺失，尝试扫描 PDF 首页或评论字段
- **优先级**：低（增强用户体验，但爬虫复杂度高）

---

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
