# 使用指南

这是一份面向用户的快速上手指南，只保留“必须配置才能完成检索目标”的内容，并提供可直接运行的最小示例。

需要完整参数说明参见 [详细参数配置说明](./docs/zh/guide_configuration.md)

---

## 1. 快速开始

**1) 安装**（推荐虚拟环境）：

```bash
python -m pip install -e .
```

**2) （可选）启用 LLM**：

```bash
cp .env.example .env
# 编辑 .env 文件，填入 LLM_API_KEY
```

**3) 运行**：

```bash
paper-tracker --config config/default.yml search
```

---

## 2. 配置文件与默认配置的关系

`config/default.yml` 是**默认配置项**，请**不要**修改它。

如果你要自定义配置，请新建一个文件（例如 `config/custom.yml`），然后在 CLI 中使用它。程序会把你提供的配置与默认配置合并：你写的字段覆盖默认值，未写的字段继续使用默认值。

示例：

```bash
paper-tracker --config config/custom.yml search
```

---

## 3. 必须配置项

### 3.1 查询选择

- `queries`：至少 1 条查询
- `output.formats`：至少 1 种输出格式

### 3.2 强烈建议

- `search.max_results`：限制每条 query 返回数量
- `output.base_dir`：输出目录

### 3.3 按需配置

- `scope`：对所有 query 的全局过滤（例如限定分类）
- `output.markdown` / `output.json`：导出模板
- `state`：去重与内容存储
- `arxiv.keep_version`：是否保留 arXiv 版本号

### 3.4 只在使用 LLM 时需要

- `llm.enabled: true` 启动 llm 功能
- `llm.provider`（当前仅支持 `openai-compat`）
- `llm.api_key_env`: API KEY 环境变量, 就是 `.env` 中设置的值（默认 `LLM_API_KEY`）
- `llm.base_url`: llm 服务商提供的链接
- `llm.model`: llm 服务商的模型
- `llm.target_lang`: 输出的翻译的目标语言（例如 `zh` ）
- `llm.enable_translation` / `llm.enable_summary`

同时需要设置环境变量：`LLM_API_KEY`（或你在 `api_key_env` 中自定义的变量名）。

---

## 4. Query 怎么写

### 4.1 最小结构

```yml
queries:
  - NAME: example
    TITLE:
      OR: [diffusion]
```

### 4.2 常用字段

字段必须大写：
- `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`

操作符必须大写：
- `OR` / `AND` / `NOT`

### 4.3 `TEXT` 简写（等价于 TITLE + ABSTRACT）

如果你不需要那么复杂的查询功能, 可以直接在 `queries` 下方配置 `AND` 等字段

```yml
queries:
  - NAME: compression
    OR: [Image Compression, Video Compression]
    NOT: [survey]
```

等价于：

```yml
queries:
  - NAME: compression
    TEXT:
      OR: [Image Compression, Video Compression]
      NOT: [survey]
```

---

## 5. LLM 最小可用配置

### 5.1 配置示例

```yml
llm:
  enabled: true
  provider: openai-compat
  api_key_env: LLM_API_KEY
  base_url: https://api.openai.com/v1
  model: gpt-4o-mini
  target_lang: zh
  enable_translation: true
  enable_summary: false
```

### 5.2 只翻译 / 只摘要 / 全开

- 只翻译：`enable_translation: true` + `enable_summary: false`
- 只摘要：`enable_translation: false` + `enable_summary: true`
- 翻译 + 摘要：两个都设为 `true`

---

## 6. 最小可用完整配置

```yml
log:
  level: INFO

queries:
  - NAME: llm
    TITLE:
      OR: [large language model, LLM]
    ABSTRACT:
      NOT: [survey, review]

search:
  max_results: 5

output:
  base_dir: output
  formats: [console]

# 如需 LLM：取消注释并配置环境变量
# llm:
#   enabled: true
#   provider: openai-compat
#   api_key_env: LLM_API_KEY
#   base_url: https://api.openai.com/v1
#   model: gpt-4o-mini
#   target_lang: zh
#   enable_translation: true
#   enable_summary: false
```

---

## 7. 进一步阅读

- [详细参数配置说明](./guide_configuration.md)

- [arXiv 查询语法说明](./source_arxiv_api_query.md)
