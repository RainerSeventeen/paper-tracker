# Configuration & Environment

> The following content was translated using a large language model (LLM)

This document covers two parts:
1. Explanation and configuration method for **every field** in `config/default.yml`
2. Configuration method for `.env`

---

## 1. Configuration File Rules

- CLI accepts only one parameter: `--config <path>`

- Configuration is a YAML nested structure, does not support flat keys like `log.level`

- `config/default.yml` is the default configuration, please do not modify it

- Merge rule: mappings merge recursively, lists and scalars override as a whole

Example (override a few fields):
```yml
log:
  level: DEBUG

search:
  max_results: 10

queries:
  - NAME: override
    OR: [diffusion]
```

Run:
```bash
paper-tracker search --config config/custom.yml
```

---

## 2. `default.yml` Field Descriptions

The following explains each field in order of the `config/default.yml` structure. Each field includes: functional description, optional range, and example.

### 2.1 `log`

- `level`: Control CLI log level; Optional values: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`. An error is reported if an unknown value is filled in.

- `to_file`: Whether to write log files simultaneously (in addition to console output); Optional values: `true` / `false`.

- `dir`: Root path of log file directory; Optional values: Any valid directory path. Relative paths are relative to the current working directory.

Example (only one example for `log`):
```yml
log:
  level: DEBUG
  to_file: true
  dir: log
```

### 2.2 `storage` (Deduplication & Content Storage)

- `enabled`: When enabled, deduplicates already-seen papers to avoid duplicate output; Optional values: `true` / `false`.

- `db_path`: SQLite database storage path for deduplication state and content storage; Optional values: Any valid file path. Relative paths are relative to the current working directory; absolute paths start with `/`.

- `content_storage_enabled`: Whether to save complete paper content to the database (title, abstract, authors, etc.) for future retrieval and reuse; Optional values: `true` / `false`.

Example (only one example for `storage`):
```yml
storage:
  enabled: true
  db_path: database/papers.db
  content_storage_enabled: true
  keep_arxiv_version: false
```

### 2.3 `storage.keep_arxiv_version`

- `storage.keep_arxiv_version`: Whether to keep the version suffix of arXiv paper IDs; Optional values: `true` / `false`.

Example (only one example):
```yml
storage:
  keep_arxiv_version: false
```

Explanation:
- `false` (default): `2601.21922v1` -> `2601.21922`

- `true`: Keep version numbers `v1` / `v2`, etc.

### 2.4 `scope` (Optional, Global Filter Conditions)

- `scope`: Global filter conditions that apply to **all** queries; Optional values: Same structure as `queries` (field names and operators must be uppercase). Allowed fields: `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`. Allowed operators: `AND` / `OR` / `NOT`.

- `scope.<FIELD>`: Specify search conditions for a field; Optional values: Field names must be uppercase and can only be `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`.

- `scope.<FIELD>.AND`: "All keywords must match" within the same field; Optional values: String or list of strings.

- `scope.<FIELD>.OR`: "Any keyword match is acceptable" within the same field; Optional values: String or list of strings.

- `scope.<FIELD>.NOT`: Exclude certain keywords; Optional values: String or list of strings.

Example (only one example for `scope`):
```yml
scope:
  CATEGORY:
    OR: [cs.CV, cs.LG]
  TITLE:
    NOT: ["survey", "review"]
```

### 2.5 `queries` (Required)

- `queries`: List of queries, each element is an independent query executed and output sequentially; Optional values: Non-empty array; each element is a query object.

- `queries[].NAME`: Give the query a readable name, only used for logging and output display; Optional values: Non-empty string, can be omitted.

- `queries[].<FIELD>`: Specify search conditions for a field; Optional values: Field names must be uppercase and can only be `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`.

- `queries[].AND / OR / NOT`: When writing `AND/OR/NOT` directly at the top level of a query, it represents searching the `TEXT` field (title + abstract); Optional values: String or list of strings.

- `queries[].<FIELD>.AND`: "All keywords must match" within the same field; Optional values: String or list of strings.

- `queries[].<FIELD>.OR`: "Any keyword match is acceptable" within the same field; Optional values: String or list of strings.

- `queries[].<FIELD>.NOT`: Exclude certain keywords; Optional values: String or list of strings.

Example (only one example for `queries`):

```yml
queries:
  - NAME: neural_video_compression
    OR: ["Neural Video Compression", "Learned Video Compression"]
  - NAME: vqa
    TITLE:
      OR: ["Video Quality Assessment"]
  - NAME: no_surveys
    TITLE:
      NOT: ["survey", "review"]
```

### 2.6 `search` (Fetch Strategy Configuration)

- `max_results`: Target number of papers, each query returns at most this many **new papers** (after deduplication); Optional values: Integer, must be greater than 0.

- `pull_every`: Strict time window size (in days), paper update/release time must be within `[now - pull_every, now]`; Optional values: Integer, must be greater than 0. Recommended value: `7` (last week).

- `fill_enabled`: Whether to allow papers outside the strict window to become candidates (to fill up to `max_results`); Optional values: `true` / `false`.
  - `false` (strict mode): Only papers within the strict time window are allowed to become candidates. The system still continues paginated fetches until it hits a stop condition (e.g., reaching the target, reaching the strict window boundary, or hitting the fetch limit).
  - `true` (fill mode): Allow papers outside the strict window (limited by `max_lookback_days`) to become candidates to fill the target count; also always fetch according to pagination strategy.

- `max_lookback_days`: Maximum lookback days for fill (in days), only effective when `fill_enabled=true`; Optional values: `-1` (unlimited) or an integer greater than or equal to `pull_every`. Recommended value: `30` (last month).

- `max_fetch_items`: Maximum raw papers fetched for a single query (including duplicates and filtered items); Optional values: `-1` (unlimited) or an integer greater than 0. Recommended value: `125` (to control API call count).

- `fetch_batch_size`: Number of papers fetched per API request (page size); Optional values: Integer, must be greater than 0. Recommended value: `25`.

**Sorting Strategy**: arXiv fetching always uses `lastUpdatedDate` + `descending` (most recently updated first), user configuration is not supported.

Example (only one example for `search`):
```yml
search:
  max_results: 10             # Target: return 10 new papers

  # Time window configuration
  pull_every: 7               # Strict window: last 7 days
  fill_enabled: false         # Strict mode, no fill
  max_lookback_days: 30       # If fill_enabled=true, look back at most 30 days
  max_fetch_items: 125        # Fetch at most 125 raw items
  fetch_batch_size: 25        # 25 items per page
```

**Configuration Constraints**:
- `pull_every > 0`
- When `fill_enabled=true`: `max_lookback_days == -1` or `max_lookback_days >= pull_every`
- `max_fetch_items == -1` or `max_fetch_items > 0`
- `fetch_batch_size > 0`

### 2.7 `output`

- `base_dir`: Output root directory; Optional values: Any valid directory path. Relative paths are relative to the current working directory.

- `formats`: List of output formats, can output multiple formats simultaneously; Optional values: Any combination of `console` / `json` / `markdown` / `html` (at least one).

- `markdown.template_dir`: Markdown template directory; Optional values: Any non-empty directory path string.

- `markdown.document_template`: Document-level template file name (generates the outer structure of the entire Markdown document); Optional values: File name in the template directory.

- `markdown.paper_template`: Paper-level template file name (rendering structure of a single paper); Optional values: File name in the template directory.

- `markdown.paper_separator`: Separator string between multiple papers; Optional values: Any string; can contain `\n` newline.

Example (only one example for `output`):
```yml
output:
  base_dir: output/
  formats: [console, json, markdown]
  markdown:
    template_dir: template/markdown/
    document_template: document.md
    paper_template: paper.md
    paper_separator: "\n\n---\n\n"
```

Explanation:
- The `output.markdown.*` fields above only take effect when `output.formats` includes `markdown`.
- The `output.html.*` fields only take effect when `output.formats` includes `html`.

### 2.8 `llm`

- `enabled`: Whether to enable LLM-related functionality (translation/summary); Optional values: `true` / `false`.

- `provider`: LLM provider type; Optional values: Currently only supports `openai-compat`.

- `base_url`: API Base URL; Optional values: Any accessible HTTP(S) interface address.

- `model`: Model name; Optional values: Determined by the service corresponding to `base_url`.

- `api_key_env`: Environment variable name corresponding to the API Key; Optional values: Any non-empty string.

- `timeout`: Single request timeout (seconds); Optional values: Integer, recommended greater than 0.

- `target_lang`: Target language for translation and summary output; Optional values: Any language identifier string. Recommended: `zh` / `en` / `ja` / `ko` / `fr` / `de` / `es`, etc.

- `temperature`: Sampling temperature, affects output randomness; Optional values: Float, commonly `0.0` ~ `2.0`.

- `max_tokens`: Maximum response tokens; Optional values: Integer, recommended greater than 0.

- `max_workers`: Number of concurrent workers, affects the number of papers processed simultaneously; Optional values: Integer, recommended greater than or equal to 1.

- `enable_translation`: Whether to enable abstract translation; Optional values: `true` / `false`.

- `enable_summary`: Whether to enable structured summary (TLDR, motivation, method, results, conclusion); Optional values: `true` / `false`.

- `max_retries`: Maximum number of retries (for timeouts or temporary errors); Optional values: Integer, `0` means no retry.

- `retry_base_delay`: Exponential backoff base delay (seconds); Optional values: Float, recommended greater than or equal to 0.

- `retry_max_delay`: Maximum retry delay (seconds); Optional values: Float, recommended greater than or equal to 0.

- `retry_timeout_multiplier`: Timeout multiplier for each retry; Optional values: Float, `1.0` means no amplification.

Example (only one example for `llm`):
```yml
llm:
  enabled: true
  provider: openai-compat
  base_url: https://api.openai.com
  model: gpt-4o-mini
  api_key_env: LLM_API_KEY
  timeout: 30
  target_lang: zh
  temperature: 0.2
  max_tokens: 1000
  max_workers: 3
  enable_translation: true
  enable_summary: true
  max_retries: 3
  retry_base_delay: 1.0
  retry_max_delay: 10.0
  retry_timeout_multiplier: 1.0
```

---

## 3. `.env` Configuration

`.env` is used to store sensitive information (such as API Keys).

### 3.1 Create `.env`

```bash
cp .env.example .env
```

### 3.2 `LLM_API_KEY`
Description: Access key for LLM API, specified by default in `llm.api_key_env` (default `LLM_API_KEY`).
Optional range: Non-empty string, issued by the provider.

Example:
```bash
LLM_API_KEY=sk-your-actual-api-key-here
```

### 3.3 Notes
- `.env` is in `.gitignore` and will not be committed

- You can customize the variable name via `llm.api_key_env`

- Same-name variables in the shell have higher priority

Example of temporary override:
```bash
LLM_API_KEY=sk-temp paper-tracker search --config config.yml
```
