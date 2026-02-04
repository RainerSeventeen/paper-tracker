# LLM 增强功能

## 概述

PaperTracker 提供了 **LLM 增强功能**,可以使用大语言模型对论文摘要进行智能处理,提供两种类型的增强:

1. **摘要翻译**: 将英文摘要翻译为目标语言(中文、日语等)
2. **结构化摘要**: 提取论文的关键要点(TLDR、研究动机、方法、结果、结论)

这两种功能可以独立启用或禁用,支持灵活组合:
- 仅翻译
- 仅摘要
- 同时使用翻译和摘要

LLM 生成的数据存储在独立的 `llm_generated` 表中,不影响原始论文数据的存储。

## 功能特性

### 摘要翻译

将论文的英文摘要翻译为目标语言,帮助非英语母语用户快速理解论文内容。

**特点:**
- 支持多种目标语言(中文、日语、韩语、法语、德语、西班牙语)
- 使用专业的学术翻译提示词,保证术语准确性
- 翻译结果直接显示在控制台输出中

### 结构化摘要

从论文摘要中提取 5 个关键要点,形成结构化的论文分析:

| 字段 | 说明 |
|------|------|
| **TLDR** | Too Long; Didn't Read 极简总结 |
| **动机** | 研究背景和动机 |
| **方法** | 研究方法和技术路径 |
| **结果** | 实验结果和主要发现 |
| **结论** | 结论和影响 |

**特点:**
- 使用目标语言生成要点
- 提供结构化的论文分析,便于快速筛选论文
- 适合需要快速了解大量论文核心内容的场景

## 配置

### 基本配置

在配置文件中启用 LLM 功能:

```yaml
llm:
  enabled: true                           # 启用 LLM 功能
  provider: openai-compat                 # 提供商类型
  api_key_env: LLM_API_KEY               # API 密钥的环境变量名
  base_url: https://api.deepseek.com     # API 基础 URL
  model: deepseek-chat                   # 模型名称
  timeout: 30                             # 请求超时(秒)
  target_lang: zh                         # 目标语言
  temperature: 0.0                        # 采样温度(0.0 = 确定性)
  max_tokens: 1000                        # 最大响应 token 数
  max_workers: 3                          # 并行处理的 worker 数

  # 功能选择
  enable_translation: true                # 启用摘要翻译
  enable_summary: true                    # 启用结构化摘要
```

### 功能模式选择

根据需求选择不同的功能组合:

#### 模式 1: 仅翻译

```yaml
llm:
  enabled: true
  enable_translation: true
  enable_summary: false
  # ... 其他配置
```

适用场景:只需要阅读中文摘要,不需要结构化分析

#### 模式 2: 仅摘要

```yaml
llm:
  enabled: true
  enable_translation: false
  enable_summary: true
  # ... 其他配置
```

适用场景:能读懂英文但需要快速提取要点

#### 模式 3: 翻译 + 摘要

```yaml
llm:
  enabled: true
  enable_translation: true
  enable_summary: true
  # ... 其他配置
```

适用场景:需要全面的中文化和结构化分析

### 配置参数详解

#### 基础参数

- **`enabled`** (布尔值): 是否启用 LLM 功能
  - `true`: 启用,必须配置 API 密钥
  - `false`: 禁用,不会调用 LLM API

- **`provider`** (字符串): LLM 提供商类型
  - 当前支持: `openai-compat` (OpenAI 兼容接口)
  - 适用于 OpenAI、DeepSeek、SiliconFlow、Moonshot 等提供商

- **`api_key_env`** (字符串,默认: `LLM_API_KEY`): API 密钥的环境变量名
  - 从指定的环境变量读取 API 密钥
  - 密钥配置见 [环境变量配置](environment-variables.md)

- **`base_url`** (字符串): API 基础 URL
  - OpenAI: `https://api.openai.com/v1`
  - DeepSeek: `https://api.deepseek.com`
  - SiliconFlow: `https://api.siliconflow.cn/v1`

- **`model`** (字符串): 模型名称
  - 示例: `gpt-4o-mini`, `deepseek-chat`, `Qwen/Qwen2.5-7B-Instruct`
  - 需根据提供商支持的模型列表填写

#### 生成参数

- **`timeout`** (整数,默认: 30): 单次请求超时时间(秒)
  - 建议范围: 20-60 秒
  - 摘要生成比翻译耗时更长,可适当提高

- **`target_lang`** (字符串,默认: `zh`): 目标语言代码
  - 支持: `zh`(简体中文), `en`(英语), `ja`(日语), `ko`(韩语), `fr`(法语), `de`(德语), `es`(西班牙语)

- **`temperature`** (浮点数,默认: 0.0): 采样温度
  - 范围: 0.0 - 2.0
  - `0.0`: 确定性输出(推荐,保证一致性)
  - 更高的值会增加输出的随机性

- **`max_tokens`** (整数,默认: 1000): 最大响应 token 数
  - 翻译模式: 800 通常足够
  - 摘要模式: 建议 1000-1500(5 个要点需要更多 token)

- **`max_workers`** (整数,默认: 3): 并行处理的 worker 数
  - 控制同时处理的论文数量
  - 建议范围: 3-10,取决于 API 限流策略

#### 功能开关

- **`enable_translation`** (布尔值,默认: `true`): 启用摘要翻译
  - 禁用可减少 API 调用成本

- **`enable_summary`** (布尔值,默认: `false`): 启用结构化摘要
  - 默认禁用以控制成本
  - 摘要生成比翻译消耗更多 token

#### 重试配置

用于应对网络超时和临时性 API 故障:

- **`max_retries`** (整数,默认: 3): 最大重试次数
  - 设为 `0` 禁用重试
  - 建议范围: 2-5

- **`retry_base_delay`** (浮点数,默认: 1.0): 指数退避基础延迟(秒)
  - 第 n 次重试延迟 = min(base_delay * 2^n, max_delay)

- **`retry_max_delay`** (浮点数,默认: 10.0): 单次重试最大等待时间(秒)

- **`retry_timeout_multiplier`** (浮点数,默认: 1.0): 每次重试的超时倍数
  - 可设为 `1.5` 在重试时增加超时时间

### 环境变量配置

LLM 功能需要配置 API 密钥,详见 [环境变量配置文档](environment-variables.md#llm_api_key)。

快速配置:

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件,填入你的 API 密钥
# LLM_API_KEY=sk-your-actual-api-key-here
```

## 工作原理

### 处理流程

```
1. 搜索论文
   ↓
2. 去重过滤 (如启用)
   ↓
3. 保存原始数据到 paper_content 表 (如启用内容存储)
   ↓
4. LLM 批量处理 (如启用 LLM)
   ├── 翻译摘要 (如启用 enable_translation)
   └── 生成摘要 (如启用 enable_summary)
   ↓
5. 保存 LLM 数据到 llm_generated 表
   ↓
6. 将 LLM 数据注入到 Paper.extra 字段
   ↓
7. 渲染输出到控制台
```

### 并行处理

使用 `ThreadPoolExecutor` 并行处理多篇论文:

- `max_workers` 控制并发数
- 自动错误隔离:单篇论文失败不影响其他论文
- 按论文顺序收集结果

### 错误处理策略

1. **可重试错误**:
   - 网络超时 (`requests.Timeout`)
   - 连接错误 (`requests.ConnectionError`)
   - HTTP 429/500/502/503/504

2. **不可重试错误**(立即失败):
   - HTTP 400 (请求格式错误)
   - HTTP 401 (认证失败)
   - HTTP 403 (权限不足)

3. **降级处理**:
   - 翻译失败:跳过该论文的翻译,继续生成摘要
   - 摘要失败:跳过该论文的摘要,继续翻译
   - 两者都失败:该论文无 LLM 增强,但仍正常显示

## 数据库设计

### `llm_generated` 表结构

LLM 生成的数据存储在独立的表中,通过外键关联到 `paper_content`:

```sql
CREATE TABLE llm_generated (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_content_id INTEGER NOT NULL,
  generated_at INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER)),
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  language TEXT NOT NULL,
  abstract_translation TEXT,
  summary_tldr TEXT,
  summary_motivation TEXT,
  summary_method TEXT,
  summary_result TEXT,
  summary_conclusion TEXT,
  extra TEXT,
  FOREIGN KEY (paper_content_id) REFERENCES paper_content(id) ON DELETE CASCADE
);

CREATE INDEX idx_llm_generated_paper ON llm_generated(paper_content_id);
CREATE INDEX idx_llm_generated_time ON llm_generated(generated_at DESC);
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER | 主键 |
| `paper_content_id` | INTEGER | 关联的论文 ID(外键) |
| `generated_at` | INTEGER | 生成时间(Unix 时间戳) |
| `provider` | TEXT | LLM 提供商(如 `openai-compat`) |
| `model` | TEXT | 模型名称(如 `deepseek-chat`) |
| `language` | TEXT | 目标语言代码 |
| `abstract_translation` | TEXT | 翻译后的摘要 |
| `summary_tldr` | TEXT | TLDR 总结 |
| `summary_motivation` | TEXT | 研究动机 |
| `summary_method` | TEXT | 研究方法 |
| `summary_result` | TEXT | 实验结果 |
| `summary_conclusion` | TEXT | 结论 |
| `extra` | TEXT | 扩展字段(JSON) |

### 设计亮点

1. **职责分离**: LLM 数据与原始论文数据分离,互不干扰
2. **版本追踪**: 记录 `provider` 和 `model`,便于对比不同模型效果
3. **时间索引**: 支持按生成时间查询最新数据
4. **级联删除**: 论文删除时自动清理关联的 LLM 数据
5. **可扩展性**: `extra` 字段预留扩展空间

## 使用示例

### 示例 1: 启用翻译功能

配置文件 (`config/papers.yml`):

```yaml
llm:
  enabled: true
  provider: openai-compat
  api_key_env: LLM_API_KEY
  base_url: https://api.deepseek.com
  model: deepseek-chat
  target_lang: zh
  max_workers: 5
  enable_translation: true
  enable_summary: false

queries:
  - NAME: neural_compression
    OR:
      - Neural Image Compression
      - Learned Video Compression

search:
  max_results: 5
```

运行搜索:

```bash
paper-tracker --config config/papers.yml search
```

输出示例:

```
[1/5] Learned Image Compression with Diffusion Models
   ID: 2501.12345
   Authors: Zhang, Wei; Li, Ming
   Category: cs.CV
   Published: 2025-01-15
   Abs: https://arxiv.org/abs/2501.12345
   PDF: https://arxiv.org/pdf/2501.12345.pdf
   摘要(翻译): 本文提出了一种基于扩散模型的学习图像压缩方法...
```

### 示例 2: 启用摘要功能

配置文件:

```yaml
llm:
  enabled: true
  enable_translation: false
  enable_summary: true
  max_tokens: 1500  # 摘要需要更多 token
  # ... 其他配置
```

输出示例:

```
[1/5] Learned Image Compression with Diffusion Models
   ID: 2501.12345
   --- 论文要点 ---
   TLDR: 提出基于扩散模型的图像压缩框架,在低码率下超越传统编解码器
   动机: 现有学习压缩方法在极低码率下重建质量不佳,扩散模型可生成高质量图像
   方法: 设计条件扩散模型作为解码器,结合率失真优化的编码器训练
   结果: 在 Kodak 数据集上,PSNR 提升 2.1dB,主观质量显著改善
   结论: 扩散模型为学习图像压缩提供了新方向,但推理速度仍需优化
```

### 示例 3: 同时启用翻译和摘要

配置文件:

```yaml
llm:
  enabled: true
  enable_translation: true
  enable_summary: true
  # ... 其他配置
```

输出将包含翻译后的摘要和结构化要点。

## 实现细节

### 核心模块

#### `llm/service.py`: `LLMService`

LLM 服务的核心协调器:

- **`generate_batch(papers)`**: 批量处理论文,返回 `LLMGeneratedInfo` 列表
- **`enrich_papers(papers, infos)`**: 将 LLM 数据注入到 `Paper.extra` 字段
- **`_generate_single(paper)`**: 处理单篇论文,生成翻译和/或摘要

关键逻辑:
- 使用 `ThreadPoolExecutor` 并行处理
- 翻译和摘要独立生成,互不影响
- 单个功能失败时降级处理

#### `llm/openai_compat.py`: `OpenAICompatProvider`

OpenAI 兼容接口的实现:

- **`translate_abstract(abstract, target_lang)`**: 翻译摘要
  - 使用专业学术翻译提示词
  - 返回纯文本(自动清理 JSON 外壳)

- **`generate_summary(abstract, target_lang)`**: 生成结构化摘要
  - 要求模型返回 JSON 格式
  - 包含 5 个关键字段
  - 自动解析和验证 JSON

#### `storage/llm.py`: `LLMGeneratedStore`

LLM 数据的存储层:

- **`save(infos)`**: 批量保存 LLM 生成的数据
  - 查找关联的 `paper_content_id`
  - 插入到 `llm_generated` 表
  - 记录 `provider` 和 `model` 元信息

- **`get_latest(source, source_id)`**: 获取最新的 LLM 数据
- **`get_batch_with_llm(sources_and_ids)`**: 批量查询 LLM 数据

### 数据流转

```
Paper (core/models.py)
  └─> LLMService.generate_batch()
        ├─> Provider.translate_abstract()  # 如启用
        ├─> Provider.generate_summary()    # 如启用
        └─> LLMGeneratedInfo
              ├─> LLMGeneratedStore.save()  # 持久化
              └─> LLMService.enrich_papers()
                    └─> Paper.extra['translation']  # 注入翻译
                    └─> Paper.extra['summary']      # 注入摘要
```

### Prompt 设计

#### 翻译 Prompt

```
System: You are a professional academic translator...

User: Translate the following research paper abstract to {language}.
      Keep academic terminology intact.

      Abstract: {abstract}
```

#### 摘要 Prompt

```
System: You are a professional paper analyst...

User: Please analyze the following abstract...

      Return ONLY a JSON object with these exact keys:
      {
        "tldr": "...",
        "motivation": "...",
        "method": "...",
        "result": "...",
        "conclusion": "..."
      }
```

## 性能优化

### 控制 API 成本

1. **按需启用功能**:
   - 只需要阅读中文?仅启用翻译
   - 能读英文但需要快速筛选?仅启用摘要

2. **调整并发数**:
   ```yaml
   max_workers: 3  # 减少并发,避免超过 API 限流
   ```

3. **减少处理论文数**:
   ```yaml
   search:
     max_results: 10  # 只处理最相关的论文
   ```

4. **选择高性价比模型**:
   - DeepSeek-chat: 0.14¥/百万 token(输入)
   - GPT-4o-mini: 约 1.05¥/百万 token

### 减少延迟

1. **增加并发数**:
   ```yaml
   max_workers: 10  # 加快批量处理速度
   ```

2. **优化超时设置**:
   ```yaml
   timeout: 20  # 降低超时,快速失败
   max_retries: 1  # 减少重试次数
   ```

3. **禁用不需要的功能**:
   ```yaml
   enable_summary: false  # 摘要生成比翻译慢
   ```

## 限制和注意事项

### 功能限制

1. **依赖内容存储**:
   - LLM 数据保存到数据库需要启用 `state.content_storage_enabled: true`
   - 如果只想看控制台输出,可以禁用内容存储,但数据不会持久化

2. **语言支持**:
   - 当前仅支持将英文摘要翻译为其他语言
   - 不支持其他源语言(如中文论文翻译为英文)

3. **摘要质量**:
   - 取决于模型能力和 prompt 设计
   - 部分字段可能为空(如结果不明确)
   - 建议使用 GPT-4 系列或 DeepSeek-v3 以获得更好效果

### 成本考虑

同时启用翻译和摘要会显著增加 API 调用成本:

| 场景 | Token 消耗估算 | DeepSeek 成本(约) |
|------|----------------|-------------------|
| 仅翻译 | ~500-800 token/论文 | 0.0001¥/论文 |
| 仅摘要 | ~800-1200 token/论文 | 0.00015¥/论文 |
| 翻译+摘要 | ~1300-2000 token/论文 | 0.00025¥/论文 |

**示例**: 每天处理 100 篇论文(翻译+摘要模式):
- 月成本: 100 × 0.00025 × 30 = 0.75¥
- 年成本: 约 9¥

### 技术限制

1. **单进程处理**:
   - 数据库写入不支持多进程并发
   - 并行搜索时需使用不同的 `db_path`

2. **无重复检测**:
   - 同一篇论文多次搜索会重复生成 LLM 数据
   - 建议依赖去重功能避免重复处理

3. **网络依赖**:
   - 需要稳定的网络连接访问 LLM API
   - 网络问题会导致批量处理中断

## 故障排查

### 错误: "LLM_API_KEY environment variable not set"

**原因**: 启用了 LLM 功能但未配置 API 密钥

**解决方法**:
1. 创建 `.env` 文件并设置 `LLM_API_KEY`
2. 或在配置文件中设置 `llm.enabled: false`

详见 [环境变量配置](environment-variables.md)。

### 错误: "Failed to translate paper X"

**可能原因**:
1. 网络超时或连接失败
2. API 限流(HTTP 429)
3. API 密钥无效或余额不足

**解决方法**:
1. 检查网络连接
2. 增加 `timeout` 和 `max_retries`
3. 验证 API 密钥和账户余额
4. 降低 `max_workers` 避免触发限流

### LLM 数据未保存到数据库

**检查项**:
1. 确认 `state.content_storage_enabled: true`
2. 查看日志中是否有 `"Paper X not found in paper_content"` 警告
3. 验证数据库文件权限可写

### 摘要字段为空

**可能原因**:
1. 模型输出格式不符合预期
2. `max_tokens` 设置过小
3. 论文摘要信息不足

**解决方法**:
1. 增加 `max_tokens` 至 1500
2. 检查日志中的 API 响应
3. 尝试使用更强大的模型

### 处理速度慢

**优化方法**:
1. 增加 `max_workers` 提高并发
2. 选择响应更快的 API 提供商
3. 仅启用需要的功能(翻译或摘要)
4. 减少 `search` 中的 `max_results`

## 相关文档

- [环境变量配置](environment-variables.md) - API 密钥配置
- [配置指南](configuration.md) - 完整配置选项
- [内容存储](content-storage.md) - 数据库存储机制
- [测试指南](testing.md) - LLM 功能测试
