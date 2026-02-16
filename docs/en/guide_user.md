# User Guide

> The following content was translated using a large language model (LLM)

This is a quick-start guide for users, keeping only "content that must be configured to complete the retrieval goal", and providing minimal executable examples.

For complete parameter descriptions, see [Detailed Parameter Configuration](./guide_configuration.md)

---

## 1. Quick Start

**1) Install** (virtual environment recommended):

```bash
python -m pip install -e .
```

**2) (Optional) Enable LLM**:

```bash
cp .env.example .env
# Edit the .env file and fill in LLM_API_KEY
```

**3) Run**:

```bash
paper-tracker search --config config/default.yml
```

---

## 2. Configuration Files and Default Configuration

`config/default.yml` is the **default configuration**, please **do not** modify it.

If you want to customize the configuration, create a new file (e.g., `config/custom.yml`), then use it in the CLI. The program will merge your configuration with the default configuration: fields you write override default values, and fields you don't write continue to use default values.

Example:

```bash
paper-tracker search --config config/custom.yml
```

---

## 3. Required Configuration Items

### 3.1 Query Selection

- `queries`: At least 1 query
- `output.formats`: At least 1 output format

### 3.2 Strongly Recommended

- `search.max_results`: Limit the number of results returned per query
- `output.base_dir`: Output directory

### 3.3 Optional Configuration

- `scope`: Global filter for all queries (e.g., restrict to certain categories)
- `output.markdown` / `output.json`: Export templates
- `storage`: Deduplication and content storage
- `storage.keep_arxiv_version`: Whether to keep arXiv version numbers

### 3.4 Only Needed When Using LLM

- `llm.enabled: true` enables LLM functionality
- `llm.provider` (currently only supports `openai-compat`)
- `llm.api_key_env`: API KEY environment variable, which is the value set in `.env` (default `LLM_API_KEY`)
- `llm.base_url`: URL provided by the LLM service provider
- `llm.model`: Model name from the LLM service provider
- `llm.target_lang`: Target language for translation output (e.g., `zh`)
- `llm.enable_translation` / `llm.enable_summary`

Storage rules:
- `llm.enabled: true` can be enabled independently, without depending on the `storage` switch.
- LLM results are only written to SQL when both `llm.enabled: true` and `storage.content_storage_enabled: true`.

Also need to set the environment variable: `LLM_API_KEY` (or the variable name you customize in `api_key_env`).

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

Fields must be uppercase:
- `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`

Operators must be uppercase:
- `OR` / `AND` / `NOT`

### 4.3 `TEXT` Shorthand (Equivalent to TITLE + ABSTRACT)

If you don't need complex query functionality, you can directly configure `AND` and other fields under `queries`

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

### 5.1 Configuration Example

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

### 5.2 Translation Only / Summary Only / All Enabled

- Translation only: `enable_translation: true` + `enable_summary: false`
- Summary only: `enable_translation: false` + `enable_summary: true`
- Translation + Summary: Set both to `true`

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

# If you need LLM: uncomment and configure environment variable
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

## 7. Further Reading

- [Detailed Parameter Configuration](./guide_configuration.md)

- [arXiv Query Syntax](./source_arxiv_api_query.md)
