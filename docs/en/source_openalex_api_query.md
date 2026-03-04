# OpenAlex API: `search` Parameter and Query Guide

> The following content was translated using a large language model (LLM)

This document explains how the OpenAlex Works API (`/works`) parameters are used in this project, as well as the project's query compilation and local post-filtering logic.

> Note: This document focuses on capabilities actually used by the current Paper Tracker implementation, not a full OpenAlex syntax manual.

---

## 1. Overview of OpenAlex Works API Request Parameters

A typical OpenAlex Works API request looks like:

```text
https://api.openalex.org/works?search=<QUERY>&filter=from_publication_date:2026-02-01&page=1&per-page=25&sort=publication_date:desc
```

Common parameters used by this project:

- `search`: Global boolean text search (focus of this document; the project currently compiles only `TITLE` / `ABSTRACT` / `TEXT` into this parameter)
- `filter`: Filter constraints (the project appends `from_publication_date:YYYY-MM-DD`)
- `page`: Page number (starts from 1)
- `per-page`: Items per page (maximum 200)
- `sort`: Sorting (fixed as `publication_date:desc` in this project)

Reference: <https://docs.openalex.org/>

---

## 2. `search` Query Expression (Project Compilation Strategy)

### 2.1 How Fields Map to `search`

OpenAlex accepts only a global `search` parameter and does **not** support field prefixes like `ti:`, `abs:`, or `au:`.

This project compiles terms from **only `TITLE`, `ABSTRACT`, and `TEXT`** into the `search` string, and joins field-level clauses with `AND`.

`AUTHOR`, `JOURNAL`, and `CATEGORY` are skipped during compilation and handled by downstream local filtering (see Section 3).

> Planned future support: `AUTHOR` can be mapped via `filter=author.display_name:<name>`; `JOURNAL` via `filter=primary_location.source.display_name:<name>`; `CATEGORY` via `filter=concepts.display_name:<name>` or topics.

`scope` and `query` are compiled as independent clauses, then combined with `AND`:

```text
<scope_clause> AND <query_clause>
```

### 2.2 Boolean Structure (Compilation Rules for AND / OR / NOT)

Compilation rules for the three operators under each field:

- `AND`: For multiple terms, wrap with parentheses and join by `AND`:
  - `"diffusion" AND "video"` -> `("diffusion" AND "video")`
  - Single term is quoted directly: `"diffusion"`
- `OR`: For multiple terms, wrap with parentheses and join by `OR`:
  - `("diffusion" OR "transformer")`
- `NOT`: For multiple terms, join by `OR` inside parentheses and prefix with `NOT`:
  - `NOT "survey"`
  - `NOT ("survey" OR "review")`

Clauses from different operators are joined by `AND`, and together form one field clause.

Notes:
- Every term is automatically wrapped in double quotes (phrase-safe).
- `NOT` terms participate in both upstream `search` compilation and downstream local NOT filtering (see Section 3).

---

## 3. Local Post-Filtering Logic (Two-Phase Filtering)

OpenAlex upstream `search` is full-text search without strict field-level precision guarantees. After receiving results, the project applies two local filtering phases in order:

### 3.1 Positive Field Matching (`apply_positive_filter`)

Each paper is strictly matched field by field. **All fields must pass** for the paper to be kept. Local matching targets are:

| Config Field | Local Match Target      |
|--------------|-------------------------|
| `TITLE`      | `paper.title`           |
| `ABSTRACT`   | `paper.abstract`        |
| `AUTHOR`     | Concatenated `paper.authors` |
| `JOURNAL`    | `paper.journal`         |
| `TEXT`       | `title + abstract`      |
| `CATEGORY`   | **Skipped (no match)**  |

Why `CATEGORY` is skipped in local post-filtering is explained in Section 4.

### 3.2 NOT Exclusion (`apply_not_filter`)

Runs independently of positive filtering. Removes papers whose title or abstract contains any NOT term (case-insensitive).

> "Double protection" for NOT terms: NOT terms in `TITLE` / `ABSTRACT` / `TEXT` are used both as upstream hints in `search` (to reduce upstream results) and as enforced local exclusion to guarantee filtering. NOT terms in `AUTHOR` / `JOURNAL` / `CATEGORY` currently take effect only in local filtering.

---

## 4. `CATEGORY` Behavior and Limitations

| Stage            | Behavior                                                         |
|------------------|------------------------------------------------------------------|
| Compilation      | **Skipped**, not compiled into `search`                          |
| Local Filtering  | **Skipped**, no local match is performed (treated as always true) |

**Reason**: OpenAlex records do not carry arXiv category codes (such as `cs.CV`). OpenAlex topic metadata (`primary_topic` / `concepts`) uses natural-language names (such as `Computer Vision`), so it cannot be filtered as precisely as arXiv `cat:`. Mixing these terms into global `search` may instead interfere with retrieval semantics.

**Practical effect**: `CATEGORY` is currently completely ineffective in OpenAlex mode. If topic constraints are needed, use `TITLE` or `ABSTRACT`.

> Planned future support: topic constraints via `filter=concepts.display_name:<name>` or `topics`.

---

## 5. Mapping to This Project's Configuration

This project uses structured queries (`scope` + `queries`) at the configuration layer, with unified field/operator semantics.

For details, see: [Detailed configuration parameter reference](./guide_configuration.md)

Semantic fields supported by the configuration layer:

- `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`
- Top-level `AND` / `OR` / `NOT` are equivalent to `TEXT` (title + abstract)

Each field supports three operator keys (must be uppercase):

- `AND`: All terms must match (list)
- `OR`: Any term may match (list)
- `NOT`: Exclude (list)

```yml
queries:
  - NAME: example_openalex
    TITLE:
      OR: [diffusion]
      NOT: [survey]
    AUTHOR:
      OR: ["Yann LeCun"]
```

---

## 6. Examples

### 6.1 Title/Abstract Keywords + Exclude Surveys

Configuration:
```yml
TITLE:
  OR: [diffusion, video]
  NOT: [survey]
```

Compiled result (upstream `search`):
```text
("diffusion" OR "video") AND NOT "survey"
```

Local filtering: ensure title contains `diffusion` or `video`, and `survey` does not appear in title + abstract.

### 6.2 Recall with Multiple Parallel Keywords

Configuration:
```yml
OR: ["vision-language model", "multimodal large language model"]
NOT: [survey, review]
```

Compiled result:
```text
("vision-language model" OR "multimodal large language model") AND NOT ("survey" OR "review")
```

### 6.3 Combining Global Scope with Query

`scope` and `query` are compiled into separate clauses and combined with `AND`:

```text
<scope_clause> AND <query_clause>
```

---

## 7. Common Notes

- OpenAlex does not support field prefixes like `ti:`/`abs:`; use configuration-layer fields (`TITLE`/`ABSTRACT`, etc.).
- `CATEGORY` is not locally post-filtered in OpenAlex mode, so it cannot guarantee returning only papers from a specific topic; for precise filtering, use `TITLE` or `ABSTRACT`.
- To avoid YAML parsing ambiguity, terms with spaces or special characters should be quoted.
- Final result counts are jointly constrained by `search.max_results`, `search.max_fetch_items`, time window, and other settings.

---

## 8. Key Differences vs arXiv

This section compares OpenAlex and arXiv behaviors in this project, to help users understand multi-source behavior and configure queries correctly.

### 8.1 API Protocol and Response Format

| Dimension       | arXiv                                      | OpenAlex                                              |
|----------------|--------------------------------------------|-------------------------------------------------------|
| API type       | Atom/RSS XML (`/api/query`)                | REST JSON (`/works`)                                  |
| Abstract field | XML `<summary>` plain text                 | Inverted abstract index, reconstructed locally        |

### 8.2 Query Parameter Structure

| Dimension             | arXiv                                      | OpenAlex                                              |
|----------------------|--------------------------------------------|-------------------------------------------------------|
| Keyword parameter    | `search_query`                              | `search`                                              |
| Field-prefix support | Yes (`ti:`, `abs:`, `cat:`, `au:`, etc.)  | **No**, only global `search`                          |
| Field precision      | Upstream API can do field-precise matching | Upstream is full-text; precision relies on local filtering |

### 8.3 `CATEGORY` Support

This is the most significant source-level behavior difference:

| Stage            | arXiv                                      | OpenAlex                                              |
|------------------|--------------------------------------------|-------------------------------------------------------|
| Compilation      | Compiled as prefixes like `cat:cs.CV`      | **Skipped**, not included in `search`                 |
| Local filtering  | Not needed (already precise upstream)      | **Skipped**, treated as always true                   |
| Practical effect | Can precisely restrict arXiv category      | **Ineffective**, cannot restrict by arXiv category    |

Reason: OpenAlex records do not carry arXiv category codes. Its topic system (`primary_topic` / `concepts`) uses natural-language labels and cannot behave like `cat:` prefixes.

Recommended approach: when using OpenAlex, use `TITLE` or `ABSTRACT` terms instead of `CATEGORY` for topic constraints.

### 8.4 Local Post-Filtering

| Dimension        | arXiv                                      | OpenAlex                                              |
|-----------------|--------------------------------------------|-------------------------------------------------------|
| Upstream precision | Field prefixes already provide precision | Full-text search, insufficient field precision        |
| Positive filtering | No                                       | Yes (`apply_positive_filter`)                         |
| NOT filtering      | Upstream `ANDNOT` only                   | Upstream + local double protection (`apply_not_filter`) |

### 8.5 Time Field and Sorting

| Dimension          | arXiv                                               | OpenAlex                                               |
|-------------------|-----------------------------------------------------|--------------------------------------------------------|
| Upstream sorting  | `sortBy=lastUpdatedDate&sortOrder=descending`       | `sort=publication_date:desc`                           |
| Time filter field | Paper `updated` time                                | Paper `published` (or `updated`) time                  |
| Meaning           | Recently updated papers first                        | Recently published papers first                         |

Impact: arXiv may return older papers with recent version updates, while OpenAlex prioritizes publication date; mixed-source results can differ even with the same query.

### 8.6 Request Rate

| Dimension        | arXiv                         | OpenAlex                        |
|-----------------|-------------------------------|---------------------------------|
| Page interval   | No forced page interval       | **Forced 3-second** page interval |
| Timeout guard   | No global per-query timeout   | Max 120 seconds per query       |

OpenAlex fetches are usually slower than arXiv for the same `max_fetch_items`.

### 8.7 Coverage

| Dimension          | arXiv                            | OpenAlex                                        |
|-------------------|----------------------------------|-------------------------------------------------|
| Content scope     | arXiv preprints only             | Journals, conferences, preprints, and more      |
| Publication state | Usually preprint                 | Includes formally published versions (`article`) |
| Cross-source dedupe preference | N/A                 | Prefer keeping `article` during cross-source dedupe |
