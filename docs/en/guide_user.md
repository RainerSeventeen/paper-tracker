# User Guide

> The following content was translated using a large language model (LLM)

This is a quick-start guide for users. It keeps only the content that must be configured to complete retrieval goals, and provides minimal runnable examples.

For complete parameter descriptions, see [Detailed Configuration Reference](./guide_configuration.md)

---

## 1. Quick Start

**1) Install** (virtual environment recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows
python -m pip install -e .
```

**2) (Optional) Enable LLM**:

```bash
cp .env.example .env
# Edit .env and fill in LLM_API_KEY
```

**3) Create and run a config**:

```bash
cp config/example.yml config/custom.yml
# Edit config/custom.yml and fill in query keywords
paper-tracker search --config config/custom.yml
```

---

## 2. Relationship Between User Config and Default Config

The program has built-in defaults (`src/PaperTracker/config/defaults.yml`). Users only need to provide **override fields**. Any field not written will automatically use the default.

`config/example.yml` is the provided template and can be copied directly for editing:

```bash
cp config/example.yml config/custom.yml
paper-tracker search --config config/custom.yml
```

Merge rule: mappings merge recursively; lists and scalars override as a whole.

---

## 3. Required Configuration Items

### 3.1 Query Selection

- `queries`: At least one query
- `output.formats`: At least one output format

### 3.2 Strongly Recommended

- `search.max_results`: Limit how many results each query returns
- `output.base_dir`: Output directory

### 3.3 Optional as Needed

- `search.sources`: Source list, default `[arxiv]`; set `[arxiv, openalex]` to enable dual-source retrieval
- `scope`: Global filter for all queries (for example, restricted categories)
- `output.markdown` / `output.json`: Export templates
- `storage`: Deduplication and content storage
- `storage.keep_arxiv_version`: Whether to keep arXiv version suffixes

### 3.4 Only Required When Using LLM

- `llm.enabled: true` enables LLM features
- `llm.provider` (currently only `openai-compat`)
- `llm.api_key_env`: API key environment variable, which is the value set in `.env` (default `LLM_API_KEY`)
- `llm.base_url`: URL provided by the LLM provider
- `llm.model`: Model provided by the LLM provider
- `llm.target_lang`: Target language for translation/summary output (full names recommended, for example `Simplified Chinese`)
- `llm.enable_translation` / `llm.enable_summary`

Storage rules:
- `llm.enabled: true` can be enabled independently, without requiring `storage` as a prerequisite switch.
- LLM results are written to SQL only when `llm.enabled: true` and `storage.content_storage_enabled: true`.

You also need an environment variable: `LLM_API_KEY` (or the custom variable name you set in `api_key_env`).

---

## 4. How to Write Queries

### 4.1 Minimal Structure

```yml
queries:
  - NAME: example
    TITLE:
      OR: [diffusion]
```

### 4.2 Common Fields

Field names must be uppercase:
- `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`

Operators must be uppercase:
- `OR` / `AND` / `NOT`

> **Note**: `CATEGORY` is effective only for arXiv (for example `cs.CV`, `cs.LG`). If OpenAlex is enabled, `CATEGORY` is fully skipped in OpenAlex (both compilation and local filtering), so it produces no filtering effect there. To constrain OpenAlex topics, use `TITLE` or `ABSTRACT` instead. See [OpenAlex Query Parameters](./source_openalex_api_query.md).

### 4.3 `TEXT` Shorthand (Equivalent to TITLE + ABSTRACT)

If you do not need complex query logic, you can directly configure `AND` and similar fields under `queries`.

```yml
queries:
  - NAME: compression
    OR: [Image Compression, Video Compression]
    NOT: [survey]
```

Equivalent to:

```yml
queries:
  - NAME: compression
    TEXT:
      OR: [Image Compression, Video Compression]
      NOT: [survey]
```

---

## 5. Minimal Usable LLM Configuration

### 5.1 Config Example

```yml
llm:
  enabled: true
  provider: openai-compat
  api_key_env: LLM_API_KEY
  base_url: https://api.openai.com/v1
  model: gpt-4o-mini
  target_lang: Simplified Chinese
  enable_translation: true
  enable_summary: false
```

### 5.2 Translation Only / Summary Only / Both Enabled

- Translation only: `enable_translation: true` + `enable_summary: false`
- Summary only: `enable_translation: false` + `enable_summary: true`
- Translation + summary: set both to `true`

---

## 6. Minimal Complete Configuration

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

# To use LLM: uncomment and configure environment variables
# llm:
#   enabled: true
#   provider: openai-compat
#   api_key_env: LLM_API_KEY
#   base_url: https://api.openai.com/v1
#   model: gpt-4o-mini
#   target_lang: Simplified Chinese
#   enable_translation: true
#   enable_summary: false
```

---

## 7. Further Reading

- [Detailed Configuration Reference](./guide_configuration.md)

- [arXiv Query Syntax Reference](./source_arxiv_api_query.md)

- [OpenAlex Query Parameters](./source_openalex_api_query.md)
