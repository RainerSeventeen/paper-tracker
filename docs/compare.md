## 架构对比分析

### 原始 Arxiv-tracker 的核心功能

**主要特性：**

1. **LLM 双语摘要生成** - 英文+中文段落总结
2. **邮件推送系统** - QQ SMTP，支持 HTML 模板和附件
3. **静态网站生成** - GitHub Pages 发布，带主题切换
4. **链接补全** - 从 HTML/PDF 抓取 GitHub 代码链接
5. **去重与新鲜度** - 基于 JSON 文件的状态持久化
6. **翻译功能** - LLM 翻译标题和摘要
7. **分页抓取** - 自动翻页直到满足数量或时间窗口
8. **排除关键词** - 过滤不想要的论文

**架构特点：**

- 单体式设计，所有功能集中在 [`cli.py`](https://file+.vscode-resource.vscode-cdn.net/tmp/Arxiv-tracker/arxiv_tracker/cli.py:1) (513行)
- 直接在 CLI 层处理业务逻辑
- 配置驱动，功能开关灵活
- 面向实际使用场景（邮件订阅 + 网页展示）

### 你的 src 实现的设计

**已实现功能：**

1. ✅ **清晰的分层架构** - core/sources/services/renderers/storage
2. ✅ **SQLite 状态管理** - 比 JSON 更健壮的去重方案
3. ✅ **Protocol-based 设计** - 易于扩展多数据源
4. ✅ **结构化查询模型** - [`SearchQuery`](https://file+.vscode-resource.vscode-cdn.net/tmp/src/PaperTracker/core/query.py:1) 支持复杂布尔逻辑
5. ✅ **多查询支持** - 可在一次运行中执行多个查询
6. ✅ **JSON/Text 双输出** - 灵活的渲染器

**架构优势：**

- 模块化、可测试性强
- 关注点分离清晰
- 易于扩展新数据源（Semantic Scholar 等）
- 代码质量高（类型注解、文档字符串）

------

## 🎯 需要跟进设计的功能

### 1. **LLM 集成层** ⭐⭐⭐ (高优先级)

**缺失：** 完整的 LLM 摘要和翻译功能

**建议设计：**

```
src/PaperTracker/
├── llm/
│   ├── __init__.py
│   ├── client.py          # OpenAI-compatible 客户端
│   ├── summarizer.py      # 双语摘要生成
│   └── translator.py      # 标题/摘要翻译
```

**参考原项目：**

- [`llm.py`](https://file+.vscode-resource.vscode-cdn.net/tmp/Arxiv-tracker/arxiv_tracker/llm.py:1) - OpenAI 兼容接口
- [`summarizer.py`](https://file+.vscode-resource.vscode-cdn.net/tmp/Arxiv-tracker/arxiv_tracker/summarizer.py:1) - 双语总结逻辑

**实现要点：**

- 支持 DeepSeek/SiliconFlow 等兼容平台
- 双语摘要（英文段落 + 中文段落）
- 可配置的 system prompt
- 兜底策略（LLM 失败时用启发式方法）

------

### 2. **邮件推送模块** ⭐⭐⭐ (高优先级)

**缺失：** 邮件发送功能

**建议设计：**

```
src/PaperTracker/
├── notifiers/
│   ├── __init__.py
│   ├── email.py           # SMTP 邮件发送
│   └── templates/
│       └── email.html     # HTML 邮件模板
```

**参考原项目：**

- [`mailer.py`](https://file+.vscode-resource.vscode-cdn.net/tmp/Arxiv-tracker/arxiv_tracker/mailer.py:1) - SSL/STARTTLS 自动切换
- [`email_template.py`](https://file+.vscode-resource.vscode-cdn.net/tmp/Arxiv-tracker/arxiv_tracker/email_template.py:1) - HTML 模板渲染

**实现要点：**

- 支持 QQ/Gmail 等 SMTP
- HTML 富文本邮件
- Markdown/PDF 附件支持
- 防重发机制（进程级 + 文件标记）

------

### 3. **静态网站生成器** ⭐⭐ (中优先级)

**缺失：** GitHub Pages 网站生成

**建议设计：**

```
src/PaperTracker/
├── renderers/
│   ├── site.py            # 静态网站生成
│   └── templates/
│       ├── index.html     # 主页模板
│       └── archive.html   # 归档页模板
```

**参考原项目：**

- [`sitegen.py`](https://file+.vscode-resource.vscode-cdn.net/tmp/Arxiv-tracker/arxiv_tracker/sitegen.py:1) - 完整的网站生成逻辑

**实现要点：**

- 主题切换（light/dark/auto）
- 历史归档管理
- 折叠/展开控制
- 响应式设计

------

### 4. **链接补全功能** ⭐⭐ (中优先级)

**缺失：** 从 arXiv HTML/PDF 抓取代码链接

**建议设计：**

```
src/PaperTracker/
├── sources/arxiv/
│   ├── scraper.py         # HTML/PDF 链接抓取
│   └── parser.py          # (扩展现有)
```

**参考原项目：**

- [`extrascrape.py`](https://file+.vscode-resource.vscode-cdn.net/tmp/Arxiv-tracker/arxiv_tracker/extrascrape.py:1) - 链接补全逻辑

**实现要点：**

- 从 arXiv HTML 页面抓取 GitHub 链接
- PDF 首页扫描作为兜底
- 超时控制和错误处理

------

### 5. **分页抓取优化** ⭐ (低优先级)

**当前状态：** 单次请求固定数量

**建议改进：** 在 [`ArxivSource`](https://file+.vscode-resource.vscode-cdn.net/tmp/src/PaperTracker/sources/arxiv/source.py:1) 中实现：

- 自动翻页直到满足 `max_results`
- 结合时间窗口过滤（`since_days`）
- 避免重复抓取同一批结果

**参考原项目：**

- [`cli.py:219-251`](https://file+.vscode-resource.vscode-cdn.net/tmp/Arxiv-tracker/arxiv_tracker/cli.py:219) - 分页循环逻辑

------

## 🔧 需要重构的部分

### 1. **配置模型扩展** (重构优先级：中)

**当前问题：** [`config.py`](https://file+.vscode-resource.vscode-cdn.net/tmp/src/PaperTracker/config.py:1) 缺少以下配置：

- LLM 配置（base_url, model, api_key_env）
- 邮件配置（SMTP 服务器、端口、TLS 模式）
- 网站配置（主题、accent 颜色、保留历史数）
- 翻译配置（启用开关、目标语言、字段）
- 抓取配置（HTML/PDF 开关、超时）

**建议：** 参考 [`Arxiv-tracker/config.yaml`](https://file+.vscode-resource.vscode-cdn.net/tmp/Arxiv-tracker/config.yaml:1) 补全配置项

------

### 2. **状态管理增强** (重构优先级：低)

**当前实现：** [`SqliteStateStore`](https://file+.vscode-resource.vscode-cdn.net/tmp/src/PaperTracker/storage/state.py:1) 已经很好

**可选改进：**

- 添加时间窗口过滤（`since_days`）
- 支持"成功后才写入"的幂等性保证
- DOI 归一化去重（已有 schema 支持）

------

### 3. **CLI 命令扩展** (重构优先级：低)

**建议新增命令：**

```bash
paper-tracker search          # 现有
paper-tracker digest          # 新增：搜索 + 摘要 + 邮件 + 网站
paper-tracker translate       # 新增：翻译已有结果
paper-tracker site-gen        # 新增：从 JSON 生成网站
```

------

## 📊 功能对比表

| 功能       | 原 Arxiv-tracker | 你的 src   | 优先级 |
| :--------- | :--------------- | :--------- | :----- |
| arXiv 搜索 | ✅                | ✅          | -      |
| 结构化查询 | 基础             | ✅ 高级     | -      |
| 状态去重   | ✅ JSON           | ✅ SQLite   | -      |
| LLM 摘要   | ✅ 双语           | ❌          | ⭐⭐⭐    |
| LLM 翻译   | ✅                | ❌          | ⭐⭐⭐    |
| 邮件推送   | ✅                | ❌          | ⭐⭐⭐    |
| 网站生成   | ✅                | ❌          | ⭐⭐     |
| 链接补全   | ✅                | ❌          | ⭐⭐     |
| 分页抓取   | ✅                | 部分       | ⭐      |
| 多数据源   | ❌                | ✅ 架构支持 | -      |
| 代码质量   | 中               | ✅ 高       | -      |

------

## 🎯 推荐实施路线

### Phase 1: 核心功能补全 (1-2周)

1. LLM 集成（摘要 + 翻译）
2. 邮件推送模块
3. 配置模型扩展

### Phase 2: 用户体验增强 (1周)

1. 静态网站生成
2. 链接补全功能

### Phase 3: 优化与扩展 (可选)

1. 分页抓取优化
2. 新数据源接入（Semantic Scholar）
3. 更多输出格式（RSS、Markdown）

------

## 💡 架构建议

**保持你的优势：**

- ✅ 清晰的分层架构
- ✅ Protocol-based 可扩展设计
- ✅ 高代码质量

**借鉴原项目：**

- ✅ 配置驱动的功能开关
- ✅ 实用的邮件/网站功能
- ✅ 防重发等生产级细节

**最终目标：** 一个既有清晰架构又有完整功能的论文追踪系统，兼具可维护性和实用性。