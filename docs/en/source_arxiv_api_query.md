# arXiv API: `search_query` Fields and Syntax Reference

> The following content was translated using a large language model (LLM)

This document summarizes common fields and syntax supported by the `search_query` parameter in the arXiv Atom API (`/api/query`), and explains how they map to this project's configuration.

> Note: Here, "field" refers to the prefix inside `search_query` (for example, `cat:`, `ti:`), not an HTTP parameter name.

---

## 1. Overview of arXiv Atom API Request Parameters

A typical arXiv Atom API request looks like:

```text
https://export.arxiv.org/api/query?search_query=<QUERY>&start=0&max_results=20&sortBy=submittedDate&sortOrder=descending
```

Common parameters:

- `search_query`: Search expression (the focus of this document)
- `id_list`: Comma-separated list of arXiv IDs (use either `id_list` or `search_query`)
- `start`: Starting offset of results
- `max_results`: Number of returned results
- `sortBy`: Common values are `submittedDate` / `lastUpdatedDate`
- `sortOrder`: `ascending` / `descending`

This project currently only uses `search_query` + `start/max_results/sortBy/sortOrder`.

---

## 2. `search_query` Fields (Field Prefixes)

`search_query` uses the `field:value` form for constrained search. Common fields include:

### 2.1 `cat:` (Category)

- Purpose: Filter by arXiv category
- Examples:
  - `cat:cs.CV`
  - `cat:cs.LG`
  - `(cat:cs.CV OR cat:cs.LG)`

For details, see [arXiv official documentation](https://arxiv.org/category_taxonomy)

Values such as `cs.CV` are arXiv category codes (`<major>.<minor>`).

### 2.2 `ti:` (Title)

- Purpose: Search only in the title
- Examples:
  - `ti:diffusion`
  - `ti:"large language model"`

### 2.3 `abs:` (Abstract)

- Purpose: Search only in the abstract
- Examples:
  - `abs:transformer`

### 2.4 `au:` (Author)

- Purpose: Search by author name
- Examples:
  - `au:"Yann LeCun"`
  - `au:LeCun`

### 2.5 `co:` (Comments)

- Purpose: Search in the comments field (many papers include conference/journal information here)
- Examples:
  - `co:ICCV`
  - `co:"NeurIPS 2024"`

### 2.6 `jr:` (Journal Reference)

- Purpose: Search in the journal reference field
- Examples:
  - `jr:"Nature"`

### 2.7 `all:` (All Fields)

- Purpose: Search across arXiv-provided "all fields" (usually broader than `ti/abs`)
- Examples:
  - `all:diffusion`

### 2.8 `id:` (Identifier)

- Purpose: Search by arXiv identifier (related to `id_list` usage)
- Examples:
  - `id:1234.5678`

---

## 3. Boolean Syntax in `search_query` (AND / OR / NOT)

arXiv query strings support boolean composition and parenthesized grouping. Common forms:

- `AND`:
  - `cat:cs.CV AND ti:diffusion`
- `OR`:
  - `cat:cs.CV OR cat:cs.LG`
- `NOT` / `AND NOT`:
  - `cat:cs.CV AND NOT ti:survey`
- Parenthesized grouping:
  - `(cat:cs.CV OR cat:cs.LG) AND (ti:diffusion OR abs:diffusion)`

Phrases (containing spaces) usually need double quotes:

- `ti:"large language model"`

---

## 4. Mapping to This Project's Configuration

In this project, configuration files use structured queries (the `queries` list).

For details, see: [Detailed configuration parameter reference](./guide_configuration.md)

The configuration layer uses semantic fields:

- `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`
- You can also omit fields and place `AND`/`OR`/`NOT` directly at query top level (equivalent to `TEXT`: title + abstract)

Each field supports three operator keys (must be uppercase):

- `AND`: Must all be satisfied (list)
- `OR`: Any one is sufficient (list)
- `NOT`: Exclude (list)

This project compiles these structures into arXiv Atom API `search_query`.

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

- The project compiles each query into arXiv `search_query` before sending.

---

## 5. Examples

### 5.1 Values Only (Fields auto-expanded by the project)

```text
diffusion AND "large language model"
```

### 5.2 Explicit Category + Title

```text
cat:cs.CV AND ti:diffusion AND NOT all:survey
```

### 5.3 Multiple Categories + Multiple Keywords

```text
(cat:cs.CV OR cat:cs.LG) AND (diffusion OR transformer) AND NOT all:survey
```

---

## 6. Common Notes

- Multi-word text without quotes is treated as multiple terms: `large language model` is equivalent to `large AND language AND model` (this project supports implicit AND).
- In YAML, it is recommended to wrap the whole expression in single quotes so you can use double-quoted phrases inside.
