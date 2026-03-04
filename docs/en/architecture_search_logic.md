# Search Logic Overview

> The following content was translated using a large language model (LLM)

This document describes the core search behavior of Paper Tracker, including paginated fetching, early stopping, deduplication, multi-source aggregation, and time-window filtering. It focuses on behavior and rules, not implementation details.

---

## End-to-End Flow

A search run executes in this order:

1. For each configured query, request all enabled sources (for example arXiv and OpenAlex).
2. Each source performs independent paginated fetching and accumulates source-level deduplicated results.
3. Merge all source results, then apply cross-source deduplication.
4. If LLM enhancement is enabled, generate translations/summaries in batch and inject them into paper data.
5. Render outputs in configured formats (console, JSON, Markdown, HTML).
6. Persist only **after successful output**: mark papers as seen and store snapshots.

Persisting after output avoids polluting deduplication state when output fails.

---

## Paginated Fetching

Source APIs return results in batches, so the system retrieves multiple pages.

### Batch Behavior

- Fetch fixed-size pages (`fetch_batch_size`).
- Keep fetching until stop conditions are hit.
- Apply rate-limit waits between requests.

### Stop Conditions (any one triggers stop)

- Current page is empty.
- Early-stop condition is met.
- Enough new papers are collected (`max_results`).
- Fetched item cap is reached (`max_fetch_items`, where `-1` means unlimited).
- Query runtime exceeds 120 seconds.

---

## Early Stopping

Early stop is an optimization based on reverse chronological ordering.

Trigger: the oldest paper on the current page is already outside the strict time window.

Since subsequent pages are older, later pages cannot contain in-window papers, so fetching can stop safely.

---

## Time Window

### Strict Window

`[now - pull_every days, now]`

Only papers updated/published in the last `pull_every` days are accepted.

### Fill Window (optional)

When `fill_enabled = true`, a wider lookback window is also allowed:

`[now - max_lookback_days days, now]`

- `max_lookback_days = -1` means unlimited lookback.
- Used to backfill older papers to reach target counts.

Constraint: if fill is enabled and `max_lookback_days != -1`, then `max_lookback_days >= pull_every`.

### Inclusion Rule

A paper becomes a candidate if either condition is true:

- It is inside the strict window.
- Fill is enabled and it is inside the fill window.

---

## Deduplication

Deduplication has three layers:

### Layer 1: Source-Local Dedup During Pagination

Within one source fetch, duplicates seen in earlier pages are removed immediately.

### Layer 2: Cross-Run Seen-Dedup

After successful output, newly seen papers are recorded in local storage. Next runs do not count seen papers as new.

### Layer 3: Cross-Source Batch Dedup

After aggregating all sources, records that refer to the same paper are merged.

Matching priority:

1. DOI (normalized exact match)
2. Fingerprint (`normalized title + first author + year`)
3. Same source ID

Winner selection:

- Prefer `article` records with DOI.
- Then prefer `preprint`.
- On ties, use configured source order and update time.

The winner keeps primary fields; missing fields can be backfilled from merged records.

---

## Multi-Source Aggregation

Paper Tracker supports arXiv + OpenAlex together.

### Fault Tolerance

- Sources run independently; one-source failure does not stop others.
- The query fails only if all sources fail.

### Merge Ordering

Merged results are sorted by:

1. Updated time (descending)
2. Source order in config
3. Paper ID

This order feeds cross-source dedup winner selection.

### Source Differences

| Dimension | arXiv | OpenAlex |
|---|---|---|
| Time filtering | Local filtering | API parameter + local re-check |
| Pagination | Offset | Page number |
| NOT filtering | Compiled into query | Local post-filter |
| `CATEGORY` field | Supported | Not supported (skipped) |

---

## Global Scope

The config can define a global `scope`, applied to all queries.

Logic: `(scope condition) AND (query condition)`.

Example: if `scope.CATEGORY` is `cs.CV`, all queries are constrained by that category without repeating it per query.

---

## Optional LLM Enhancement

When LLM is enabled, outputs can be enhanced before rendering:

- Abstract translation
- Structured summaries (motivation, method, results, conclusion)

Enhancement affects output fields only, not raw source data.

---

## Quick Config Reference

| Config Key | Meaning | Default |
|---|---|---|
| `pull_every` | Strict time window in days | 7 |
| `fill_enabled` | Enable fill window | true |
| `max_lookback_days` | Fill lookback limit (`-1` unlimited) | 30 |
| `fetch_batch_size` | Page size | 25 |
| `max_fetch_items` | Max fetched items per query (`-1` unlimited) | 125 |
| `max_results` | Max new papers per query | — |
