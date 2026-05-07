# PubMed API: `term` Parameter and Query Guide

> The following content was translated using a large language model (LLM)

This document explains how the NCBI E-utilities (`esearch.fcgi` + `efetch.fcgi`) parameters are used in this project, as well as the project's query compilation and local processing logic.

> Note: This document focuses on capabilities actually used by the current Paper Tracker implementation, not a full PubMed/E-utilities syntax manual.

---

## 1. Overview of NCBI E-utilities Request Parameters

PubMed retrieval uses a **two-stage** call: ESearch first to obtain a PMID list, then EFetch to retrieve the full XML records.

### 1.1 ESearch (fetch PMID list)

A typical request looks like:

```text
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&sort=pub_date&datetype=pdat&term=<TERM>&retstart=0&retmax=25&mindate=2026/04/01&maxdate=2026/05/07
```

Common parameters used by this project:

- `db`: fixed as `pubmed`
- `retmode`: fixed as `json`
- `sort`: fixed as `pub_date` (sort by publication date)
- `datetype`: fixed as `pdat` (filter by publication date)
- `term`: boolean search expression (focus of this document)
- `retstart`: starting offset of the result list (zero-based)
- `retmax`: maximum number of PMIDs to return per call
- `mindate` / `maxdate`: time window in `YYYY/MM/DD` format
- `api_key` (optional): NCBI API Key; raises rate limit from 3 req/s to 10 req/s
- `tool` / `email`: caller identifier and contact email (required by NCBI's polite-usage policy)

### 1.2 EFetch (fetch full records)

After ESearch returns PMIDs, EFetch is called with `id=<comma-separated PMIDs>` and returns a full `PubmedArticleSet` as XML:

```text
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id=12345,12346,...
```

Reference: <https://www.ncbi.nlm.nih.gov/books/NBK25501/>

> A single EFetch call accepts at most 200 PMIDs (GET length limit). `search.fetch_batch_size` should not exceed this value.

---

## 2. `term` Query Expression (Project Compilation Strategy)

### 2.1 How Fields Map to `term`

PubMed `term` uses the `"value"[TAG]` form for field-restricted searches. This project compiles configuration-layer fields into the following PubMed field tags:

| Config Field | PubMed Field Tag | Notes                                                                 |
|--------------|------------------|-----------------------------------------------------------------------|
| `TEXT`       | `[TIAB]`         | Title + Abstract                                                      |
| `TITLE`      | `[TIAB]`         | PubMed has no simple "title-only" equivalent, so `TITLE` is unified to TIAB |
| `ABSTRACT`   | `[TIAB]`         | Title + Abstract                                                      |
| `AUTHOR`     | `[AU]`           | Author                                                                |
| `JOURNAL`    | `[JT]`           | Full journal title                                                    |
| `CATEGORY`   | **Skipped**      | No PubMed equivalent (see Section 4)                                  |

> Note: `TITLE` and `ABSTRACT` collapse to the same `[TIAB]` tag in PubMed, so within the PubMed source you **cannot distinguish** "title-only" from "abstract-only" search; both match Title + Abstract. If strict title-only behavior is required, use the arXiv source.

`scope` and `query` are compiled as independent clauses, then combined with `AND`:

```text
<scope_clause> AND <query_clause>
```

### 2.2 Boolean Structure (Compilation Rules for AND / OR / NOT)

For each field (let `<TAG>` be its field tag), the three operators compile as follows:

- `AND`: each term expands to `"term"<TAG>`, joined by `AND`:
  - `["diffusion", "video"]` -> `"diffusion"[TIAB] AND "video"[TIAB]`
- `OR`: a single term expands directly; multiple terms are wrapped in parentheses and joined by `OR`:
  - Single term: `"diffusion"[TIAB]`
  - Multiple terms: `("diffusion"[TIAB] OR "transformer"[TIAB])`
- `NOT`: a single term is wrapped as `NOT (...)`; multiple terms are joined by `OR` inside parentheses with a `NOT` prefix:
  - Single term: `NOT ("survey"[TIAB])`
  - Multiple terms: `NOT ("survey"[TIAB] OR "review"[TIAB])`

Operator clauses inside one field are joined by `AND` to form a field clause. Multiple field clauses are then joined by `AND` (wrapped in parentheses when there is more than one).

Notes:

- Every term is automatically wrapped in double quotes (phrase-safe) and given a field tag.
- `NOT` terms are emitted directly into the upstream `term` and excluded by PubMed itself; this project does **not** apply additional local NOT filtering for PubMed.

---

## 3. Upstream Precision and Local Processing

PubMed `term` provides field-precise matching via field tags, so **the upstream already guarantees field precision**. Therefore, in this project the PubMed source:

- **Does not perform local positive field filtering** (no `apply_positive_filter` equivalent)
- **Does not perform local NOT fallback filtering** (NOT is already applied in the upstream `term`)
- **Discards records without a DOI**: while parsing `PubmedArticleSet`, if an article's `ArticleIdList` has no `IdType="doi"` entry, that record is dropped from the batch (to keep cross-source dedup fingerprints consistent)

> Effect on dedup: DOI is the preferred fingerprint for cross-source deduplication. PubMed records without a DOI cannot be reliably merged with arXiv/OpenAlex records, so they are dropped instead of kept.

---

## 4. `CATEGORY` Behavior and Limitations

| Stage           | Behavior                                                  |
|-----------------|-----------------------------------------------------------|
| Compilation     | **Skipped**, not compiled into `term`                     |
| Local filtering | **Not applicable** (PubMed source has no positive filter) |

**Reason**: PubMed has no equivalent of arXiv's `cat:cs.CV` taxonomy. PubMed itself uses MeSH (Medical Subject Headings) for topic indexing, but MeSH and arXiv categories are not interchangeable, and this project does not currently wire MeSH into query compilation.

**Important constraint**: if a query specifies **only** `CATEGORY` (or the query/scope as a whole has no mappable fields), the compiler raises `ValueError` to prevent an empty `term` from triggering an unbounded full-index recall on PubMed.

**Practical effect**: `CATEGORY` is currently completely ineffective in PubMed mode. For topic constraints, use `TITLE` / `ABSTRACT` / `TEXT`.

> Planned future support: MeSH-based topic constraints can be added via the `[MH]` (MeSH Terms) or `[MAJR]` (MeSH Major Topic) tags.

---

## 5. Time Window and Sorting

### 5.1 Time Filtering

The PubMed time window is enforced upstream via ESearch's `mindate` / `maxdate`, combined with `datetype=pdat` (publication date):

- Strict mode (default): `[now - pull_every, now]`
- Fill mode (`fill_enabled=true`): `[now - max_lookback_days, now]`; `max_lookback_days=-1` means no date restriction

Time strings use the PubMed-accepted `YYYY/MM/DD` format.

### 5.2 Sorting

ESearch always uses `sort=pub_date`, returning PMIDs in descending order by publication date. After all pages are collected, the project performs a final local descending sort by `paper.published` and truncates to `max_results`.

---

## 6. Authentication and Rate Limits

| Dimension       | Behavior                                                                       |
|-----------------|--------------------------------------------------------------------------------|
| API Key         | Read from environment variable `NCBI_API_KEY` (variable name configurable via `search.ncbi_api_key_env`) |
| Rate limit      | Without key: 3 req/s; with key: 10 req/s (NCBI official policy)               |
| Tool identifier | `search.ncbi_tool`, default `paper-tracker`                                    |
| Contact email   | `search.ncbi_email`, default empty string (recommended to set, per NCBI policy)|
| Timeout         | Single HTTP request: 30 seconds; total per-query timeout: 120 seconds          |
| Retry           | Auto-retry on 429 / 500 / 502 / 503 / 504 with exponential backoff, up to 4 attempts |
| Page interval   | Forced 1-second sleep between pages; 0.5-second sleep between ESearch and EFetch within one page |

---

## 7. Mapping to This Project's Configuration

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
  - NAME: example_pubmed
    OR: [diffusion]
    NOT: [survey]
    AUTHOR:
      OR: ["Yann LeCun"]
```

---

## 8. Examples

### 8.1 Title/Abstract Keywords + Exclude Surveys

Configuration:
```yml
TITLE:
  OR: [diffusion, video]
  NOT: [survey]
```

Compiled result (upstream `term`):
```text
(("diffusion"[TIAB] OR "video"[TIAB]) AND NOT ("survey"[TIAB]))
```

### 8.2 Recall with Multiple Parallel Keywords (top-level OR + NOT, equivalent to TEXT)

Configuration:
```yml
OR: ["vision-language model", "multimodal large language model"]
NOT: [survey, review]
```

Compiled result:
```text
("vision-language model"[TIAB] OR "multimodal large language model"[TIAB]) AND NOT ("survey"[TIAB] OR "review"[TIAB])
```

### 8.3 Field Combination (keywords + author + journal)

Configuration:
```yml
OR: [diffusion]
AUTHOR:
  OR: ["Yann LeCun"]
JOURNAL:
  OR: ["Nature"]
```

Compiled result:
```text
("diffusion"[TIAB] AND "Yann LeCun"[AU] AND "Nature"[JT])
```

### 8.4 Combining Global Scope with Query

`scope` and `query` are compiled into separate clauses and combined with `AND`:

```text
<scope_clause> AND <query_clause>
```

---

## 9. Common Notes

- **`TITLE` and `ABSTRACT` are indistinguishable in PubMed**; both compile to `[TIAB]`. For strict title-only precision, use the arXiv source.
- **`CATEGORY` is ineffective in PubMed**; a query that uses only `CATEGORY` will raise an error due to having no mappable fields. Use `TITLE` / `ABSTRACT` / `TEXT` instead.
- **Records without DOIs are discarded**, which may cause some PubMed records to be missing from results. This is the price of reliable cross-source deduplication.
- **Setting `NCBI_API_KEY` is recommended**: without it, the rate limit is low (3 req/s), and heavy paging may trigger sporadic 429 retries.
- **Setting `search.ncbi_email` is recommended**: NCBI's polite-usage policy expects a contact email.
- **`fetch_batch_size` should not exceed 200**: a single EFetch GET request accepts at most 200 PMIDs and will raise an error otherwise.
- To avoid YAML parsing ambiguity, terms with spaces or special characters should be quoted.
- Final result counts are jointly constrained by `search.max_results`, `search.max_fetch_items`, time window, and other settings.

---

## 10. Key Differences vs arXiv / OpenAlex

This section compares PubMed with the existing two sources to help users understand multi-source behavior and configure queries correctly.

### 10.1 API Protocol and Response Format

| Dimension       | arXiv                              | OpenAlex                | PubMed                                       |
|----------------|------------------------------------|-------------------------|----------------------------------------------|
| API type       | Atom/RSS XML (`/api/query`)        | REST JSON (`/works`)    | REST JSON (ESearch) + XML (EFetch)           |
| Call stages    | Single-stage                        | Single-stage            | **Two-stage** (ESearch -> IDs, EFetch -> details) |
| Abstract field | XML `<summary>` plain text          | Inverted abstract index, reconstructed locally | XML `<AbstractText>` (labelled sections concatenated locally) |

### 10.2 Query Parameter Structure

| Dimension             | arXiv                                | OpenAlex                                | PubMed                                       |
|----------------------|--------------------------------------|----------------------------------------|----------------------------------------------|
| Keyword parameter    | `search_query`                        | `search`                                | `term`                                       |
| Field syntax         | `field:value` (prefix)                | **None**, only global `search`          | `"value"[TAG]` (**suffix** field tag)         |
| Field precision      | Upstream-precise                       | Upstream full-text; local filter for precision | **Upstream-precise** (tag-driven)           |

### 10.3 Field Mapping Differences

| Config field | arXiv          | OpenAlex            | PubMed                                          |
|--------------|----------------|---------------------|-------------------------------------------------|
| `TITLE`      | `ti:`          | `search` full-text  | `[TIAB]` (**title+abstract, no title-only**)    |
| `ABSTRACT`   | `abs:`         | `search` full-text  | `[TIAB]`                                        |
| `AUTHOR`     | `au:`          | Skipped (local)     | `[AU]`                                          |
| `JOURNAL`    | `jr:`          | Skipped (local)     | `[JT]`                                          |
| `CATEGORY`   | `cat:cs.CV`    | **Skipped, ineffective** | **Skipped, ineffective**                   |

### 10.4 Local Filtering Strategy

| Dimension           | arXiv                  | OpenAlex                                | PubMed                                  |
|---------------------|------------------------|----------------------------------------|----------------------------------------|
| Upstream precision  | Field prefixes         | Full-text only                          | Field tags                              |
| Positive filtering  | None                    | Yes (`apply_positive_filter`)          | **None**                                |
| NOT filtering       | Upstream `ANDNOT` only | Upstream + local double protection      | Upstream `NOT` only                     |
| Missing DOI         | Kept                   | Kept                                    | **Discarded** (for cross-source dedup reliability) |

### 10.5 Time Field and Sorting

| Dimension             | arXiv                                              | OpenAlex                                           | PubMed                                       |
|----------------------|----------------------------------------------------|----------------------------------------------------|----------------------------------------------|
| Upstream time filter | None (locally filtered on `updated`)                | `filter=from_publication_date:...`                 | **`mindate` + `maxdate` (`pdat`)**           |
| Upstream sorting     | `sortBy=lastUpdatedDate&sortOrder=descending`      | `sort=publication_date:desc,relevance_score:desc`  | `sort=pub_date`                              |
| Time-field meaning   | Paper `updated` (latest version time)              | Paper `published`                                  | Paper `published` (publication date)         |

### 10.6 Request Rate

| Dimension       | arXiv                | OpenAlex                          | PubMed                                                  |
|-----------------|----------------------|----------------------------------|---------------------------------------------------------|
| Page interval   | No forced interval   | **Forced 3-second** page interval | **Forced 1-second** page interval (plus 0.5s within page) |
| Rate ceiling    | None explicit        | None explicit                     | 3 req/s without key / 10 req/s with key                |
| Timeout guard   | No global timeout    | Max 120s per query                | Max 120s per query                                      |
| Retry policy    | Generic backoff      | Generic backoff                   | 4 attempts, exponential backoff (429/5xx)              |

### 10.7 Coverage

| Dimension                | arXiv               | OpenAlex                                       | PubMed                                       |
|--------------------------|---------------------|-----------------------------------------------|---------------------------------------------|
| Content scope            | arXiv preprints     | Journals, conferences, preprints (broadest)    | Biomedical / life-science journal articles  |
| Publication state        | Usually preprint    | Includes formally published (`article`)        | Formally published articles (`article`)     |
| Topical bias             | CS / physics-heavy   | All disciplines                                | **Biomedicine / medicine / life sciences**  |
| Cross-source dedup pref. | None                 | Prefer keeping `article`                       | Prefer keeping `article`                    |

> **Usage tip**: PubMed is suited for biomedical topics (medical imaging, genomics, clinical NLP, etc.). If your search topic is unrelated to life sciences, enabling PubMed is likely to return few or no results.
