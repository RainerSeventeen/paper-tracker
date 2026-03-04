# Configuration and Environment

> The following content was translated using a large language model (LLM)

This document covers two parts:
1. How to configure and what each field means in the built-in default config (`src/PaperTracker/config/defaults.yml`)
2. How to configure `.env`

---

## 1. Configuration File Rules

- The CLI accepts only one argument: `--config <path>`

- Configuration uses nested YAML. Flat keys like `log.level` are not supported.

- The default config is built into the package (`src/PaperTracker/config/defaults.yml`). Do not modify it.

- Merge rule: mappings merge recursively; lists and scalars override as a whole.

Example (overriding only a few fields):
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

## 2. Default Configuration Field Reference

The following sections explain each field in the structure of the built-in default config. Each field includes: purpose, valid options/range, and an example.

### 2.1 `log`

- `level`: Controls CLI log level; valid values: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`. Unknown values will raise an error.

- `to_file`: Whether to also write logs to files (in addition to console output); valid values: `true` / `false`.

- `dir`: Root directory for log files; valid values: any valid directory path. Relative paths are based on the current working directory.

Example (one example for `log` is enough):
```yml
log:
  level: DEBUG
  to_file: true
  dir: log
```

### 2.2 `storage` (Deduplication and Content Storage)

- `enabled`: When enabled, deduplicates papers already seen to avoid duplicate output; valid values: `true` / `false`.

- `db_path`: SQLite database path for deduplication state and content storage; valid values: any valid file path. Relative paths are based on the current working directory; absolute paths start with `/`.

- `content_storage_enabled`: Whether to store full paper content in the database (title, abstract, authors, etc.) for later retrieval and reuse; valid values: `true` / `false`.

Example (one example for `storage` is enough):
```yml
storage:
  enabled: true
  db_path: database/papers.db
  content_storage_enabled: true
  keep_arxiv_version: false
```

### 2.3 `storage.keep_arxiv_version`

- `storage.keep_arxiv_version`: Whether to keep the version suffix in arXiv paper IDs; valid values: `true` / `false`.

Example (one example is enough):
```yml
storage:
  keep_arxiv_version: false
```

Notes:
- `false` (default): `2601.21922v1` -> `2601.21922`

- `true`: keeps version suffixes like `v1` / `v2`

### 2.4 `scope` (Optional Global Filters)

- `scope`: Global filtering conditions applied to **all** queries; valid values: same structure as `queries` (field names and operators must be uppercase). Allowed fields: `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`. Allowed operators: `AND` / `OR` / `NOT`.

- `scope.<FIELD>`: Search conditions for a specific field; valid values: field name must be uppercase and one of `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`.

- `scope.<FIELD>.AND`: "All keywords must match" in the same field; valid values: string or list of strings.

- `scope.<FIELD>.OR`: "Any keyword may match" in the same field; valid values: string or list of strings.

- `scope.<FIELD>.NOT`: Exclude certain keywords; valid values: string or list of strings.

Example (one example for `scope` is enough):
```yml
scope:
  CATEGORY:
    OR: [cs.CV, cs.LG]
  TITLE:
    NOT: ["survey", "review"]
```

### 2.5 `queries` (Required)

- `queries`: Query list. Each item is an independent query executed in sequence; valid values: non-empty array, each item is a query object.

- `queries[].NAME`: Human-readable query name, used only for logs and output display; valid values: non-empty string, optional.

- `queries[].<FIELD>`: Search condition for a specific field; valid values: field name must be uppercase and one of `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`.

- `queries[].AND / OR / NOT`: If `AND/OR/NOT` is written directly at query top level, it means searching the `TEXT` field (title + abstract); valid values: string or list of strings.

- `queries[].<FIELD>.AND`: "All keywords must match" in the same field; valid values: string or list of strings.

- `queries[].<FIELD>.OR`: "Any keyword may match" in the same field; valid values: string or list of strings.

- `queries[].<FIELD>.NOT`: Exclude certain keywords; valid values: string or list of strings.

Example (one example for `queries` is enough):

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

### 2.6 `search` (Fetch Strategy)

- `sources`: List of enabled sources; valid values: any non-empty combination of `arxiv` / `openalex`. Default: `[arxiv]`.
  - `arxiv`: Fetches preprints from arXiv Atom API. Supports `cat:` category matching (`CATEGORY` is effective).
  - `openalex`: Fetches from OpenAlex REST API, with broader coverage (journals/conferences/preprints), but **does not support arXiv category codes** (`CATEGORY` is ineffective in OpenAlex mode; see [OpenAlex Query Parameters](./source_openalex_api_query.md)).
  - When both are enabled, the service fetches in parallel and performs cross-source deduplication after aggregation (prefers published `article` records when duplicated).

- `max_results`: Target number of papers. Each query returns at most this many **new papers** (after deduplication); valid values: integer greater than 0.

- `pull_every`: Strict time-window size (days). Paper updated/published time must be in `[now - pull_every, now]`; valid values: integer greater than 0. Recommended: `7` (last week).

- `fill_enabled`: Whether papers outside the strict window can be considered (to fill up `max_results`); valid values: `true` / `false`.
  - `false` (strict mode): only papers in strict window can be candidates. The system still continues paginated fetching until a stop condition is reached (for example, target reached, strict-window boundary reached, or fetch limit reached).
  - `true` (fill mode): allows papers outside strict window (limited by `max_lookback_days`) to be candidates to fill target count; fetching still follows pagination strategy.

- `max_lookback_days`: Maximum lookback days for fill mode, effective only when `fill_enabled=true`; valid values: `-1` (unlimited) or integer greater than or equal to `pull_every`. Recommended: `30` (last month).

- `max_fetch_items`: Maximum number of raw paper items fetched for one query (including duplicates and filtered-out entries); valid values: `-1` (unlimited) or integer greater than 0. Recommended: `125` (to control API call volume).

- `fetch_batch_size`: Number of papers fetched per API request (page size); valid values: integer greater than 0. Recommended: `25`.

**Sorting strategy**:
- arXiv: fixed `lastUpdatedDate + descending` (latest updates first), with time filtering based on `updated`.
- OpenAlex: fixed `publication_date:desc` (latest publication first), with time filtering based on `published` (or `updated`), and a forced 3-second interval between pages due to API rate behavior.
- Sorting fields are not user-configurable for either source.

Example (one example for `search` is enough):
```yml
search:
  max_results: 10             # Target: return 10 new papers

  # Time-window settings
  pull_every: 7               # Strict window: last 7 days
  fill_enabled: false         # Strict mode, no fill
  max_lookback_days: 30       # If fill_enabled=true, look back up to 30 days
  max_fetch_items: 125        # Fetch at most 125 raw entries
  fetch_batch_size: 25        # 25 items per page
```

**Configuration constraints**:
- `pull_every > 0`
- If `fill_enabled=true`: `max_lookback_days == -1` or `max_lookback_days >= pull_every`
- `max_fetch_items == -1` or `max_fetch_items > 0`
- `fetch_batch_size > 0`

### 2.7 `output`

- `base_dir`: Output root directory; valid values: any valid directory path. Relative paths are based on the current working directory.

- `formats`: Output format list. Multiple formats can be enabled at once; valid values: any combination of `console` / `json` / `markdown` / `html` (at least one).

- `markdown.template_dir`: Markdown template directory; valid values: any non-empty directory path string.

- `markdown.document_template`: Document-level template file name (outer structure for the whole Markdown document); valid values: file name within the template directory.

- `markdown.paper_template`: Paper-level template file name (rendering structure for one paper); valid values: file name within the template directory.

- `markdown.paper_separator`: Separator string between papers; valid values: any string, can include newline `\n`.

Example (one example for `output` is enough):
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

Notes:
- `output.markdown.*` fields take effect only when `output.formats` includes `markdown`.
- `output.html.*` fields take effect only when `output.formats` includes `html`.

### 2.8 `llm`

- `enabled`: Whether to enable LLM features (translation/summary); valid values: `true` / `false`.

- `provider`: LLM provider type; valid values: currently only `openai-compat`.

- `base_url`: API base URL; valid values: any accessible HTTP(S) endpoint.

- `model`: Model name; valid values: determined by the service behind `base_url`.

- `api_key_env`: Environment variable name for API key; valid values: any non-empty string.

- `timeout`: Timeout per request (seconds); valid values: integer, recommended greater than 0.

- `target_lang`: Target language for translation and summary output; valid values: any non-empty language description string. Full language names are recommended (for example `Simplified Chinese` / `English` / `Japanese`).

- `temperature`: Sampling temperature that affects randomness; valid values: float, commonly `0.0` to `2.0`.

- `max_tokens`: Maximum response tokens; valid values: integer, recommended greater than 0.

- `max_workers`: Number of concurrent workers, affecting parallel paper processing; valid values: integer, recommended greater than or equal to 1.

- `enable_translation`: Whether to enable abstract translation; valid values: `true` / `false`.

- `enable_summary`: Whether to enable structured summary (TLDR, motivation, method, result, conclusion); valid values: `true` / `false`.

- `max_retries`: Maximum retry count (for timeout or transient errors); valid values: integer, `0` means no retry.

- `retry_base_delay`: Base delay for exponential backoff (seconds); valid values: float, recommended greater than or equal to 0.

- `retry_max_delay`: Maximum retry delay (seconds); valid values: float, recommended greater than or equal to 0.

- `retry_timeout_multiplier`: Timeout multiplier for each retry; valid values: float, `1.0` means no scaling.

Example (one example for `llm` is enough):
```yml
llm:
  enabled: true
  provider: openai-compat
  base_url: https://api.openai.com
  model: gpt-4o-mini
  api_key_env: LLM_API_KEY
  timeout: 30
  target_lang: Simplified Chinese
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

`.env` is used to store sensitive information (such as API keys).

### 3.1 Create `.env`

```bash
cp .env.example .env
```

### 3.2 `LLM_API_KEY`
Purpose: access key for the LLM API. By default, it is specified by `llm.api_key_env` (default `LLM_API_KEY`).
Valid range: non-empty string issued by the provider.

Example:
```bash
LLM_API_KEY=sk-your-actual-api-key-here
```

### 3.3 Notes
- `.env` is already in `.gitignore` and will not be committed.

- You can customize the variable name via `llm.api_key_env`.

- Variables with the same name in the shell have higher priority.

Temporary override example:
```bash
LLM_API_KEY=sk-temp paper-tracker search --config config.yml
```
