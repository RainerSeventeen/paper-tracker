# arXiv API: `search_query` Fields and Syntax

> The following content was translated using a large language model (LLM)

This document summarizes common fields and writing methods supported by the `search_query` parameter in the arXiv Atom API (`/api/query`), and describes the correspondence with this project's configuration.

> Note: Here "field" refers to the prefix in `search_query` (such as `cat:`, `ti:`), not the HTTP parameter name.

---

## 1. arXiv Atom API Request Parameters Overview

A typical arXiv Atom API request looks like:

```text
https://export.arxiv.org/api/query?search_query=<QUERY>&start=0&max_results=20&sortBy=submittedDate&sortOrder=descending
```

Common parameters:

- `search_query`: Search expression (focus of this document)
- `id_list`: Comma-separated list of arXiv IDs (use either `search_query` or `id_list`)
- `start`: Result start offset
- `max_results`: Number of results returned
- `sortBy`: Common values are `submittedDate` / `lastUpdatedDate`
- `sortOrder`: `ascending` / `descending`

This project currently only uses `search_query` + `start/max_results/sortBy/sortOrder`.

---

## 2. Fields (Field Prefix) of `search_query`

`search_query` uses `field:value` format for restricted searches. Here are common fields:

### 2.1 `cat:` (Category)

- Purpose: Filter by arXiv category
- Examples:
  - `cat:cs.CV`
  - `cat:cs.LG`
  - `(cat:cs.CV OR cat:cs.LG)`

For details, see [arXiv official documentation](https://arxiv.org/category_taxonomy)

`cs.CV` and similar values are arXiv classification codes (`<major>.<minor>`).

### 2.2 `ti:` (Title)

- Purpose: Search only in titles
- Examples:
  - `ti:diffusion`
  - `ti:"large language model"`

### 2.3 `abs:` (Abstract)

- Purpose: Search only in abstracts
- Examples:
  - `abs:transformer`

### 2.4 `au:` (Author)

- Purpose: Search by author name
- Examples:
  - `au:"Yann LeCun"`
  - `au:LeCun`

### 2.5 `co:` (Comments)

- Purpose: Search in comments field (many papers include conference/journal information here)
- Examples:
  - `co:ICCV`
  - `co:"NeurIPS 2024"`

### 2.6 `jr:` (Journal Reference)

- Purpose: Search in journal reference field
- Examples:
  - `jr:"Nature"`

### 2.7 `all:` (All Fields)

- Purpose: Search in arXiv's "all fields" (usually broader than `ti/abs`)
- Examples:
  - `all:diffusion`

### 2.8 `id:` (Identifier)

- Purpose: Search by arXiv identifier (related to the purpose of `id_list`)
- Examples:
  - `id:1234.5678`

---

## 3. Boolean Syntax of `search_query` (AND / OR / NOT)

arXiv query strings support boolean combinations and parenthetical grouping, common writing methods:

- `AND`:
  - `cat:cs.CV AND ti:diffusion`
- `OR`:
  - `cat:cs.CV OR cat:cs.LG`
- `NOT` / `AND NOT`:
  - `cat:cs.CV AND NOT ti:survey`
- Parenthetical grouping:
  - `(cat:cs.CV OR cat:cs.LG) AND (ti:diffusion OR abs:diffusion)`

Phrases (containing spaces) usually need to be wrapped in double quotes:

- `ti:"large language model"`

---

## 4. Correspondence with This Project's Configuration

This project uses structured queries in the configuration file (`queries` list)

For detailed explanation, see: [Detailed Parameter Configuration](./guide_configuration.md)

Configuration level uses semantic fields:

- `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`
- Also supports writing `AND`/`OR`/`NOT` directly at the query top level without specifying a field (equivalent to `TEXT`: title + abstract)

Each field supports three operator keys (required uppercase):

- `AND`: Must satisfy all (list)
- `OR`: Any one satisfies (list)
- `NOT`: Exclude (list)

This project compiles these structures into arXiv Atom API's `search_query`.

```yml
queries:
  - NAME: example
    CATEGORY:
      OR: [cs.CV]
    TITLE:
      OR: [diffusion]
      NOT: [survey]
```

Rules:

- This project compiles each query into arXiv's `search_query` before sending.

---

## 5. Examples

### 5.1 Write Only Values (Project Auto-expands Fields)

```text
diffusion AND "large language model"
```

### 5.2 Explicitly Specify Category + Title

```text
cat:cs.CV AND ti:diffusion AND NOT all:survey
```

### 5.3 Multiple Categories + Multiple Keywords

```text
(cat:cs.CV OR cat:cs.LG) AND (diffusion OR transformer) AND NOT all:survey
```

---

## 6. Common Precautions

- Multiple words without quotes are treated as multiple terms: `large language model` is equivalent to `large AND language AND model` (this project supports implicit AND).
- It is recommended to wrap the entire expression in single quotes in YAML so that the expression can use double quotes internally for phrases.
