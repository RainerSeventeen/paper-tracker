"""OpenAlex multi-round fetching strategy.

Collects OpenAlex pages with local filtering, optional persistent deduplication,
rate limiting, and deterministic final ordering.
"""

from __future__ import annotations

import logging
import time as time_module
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from time import time
from typing import TYPE_CHECKING, Any

from PaperTracker.core.models import Paper
from PaperTracker.sources.openalex.parser import parse_openalex_works
from PaperTracker.sources.openalex.query import (
    apply_not_filter,
    apply_positive_filter,
    compile_openalex_params,
    extract_not_terms,
)

if TYPE_CHECKING:
    from PaperTracker.config import SearchConfig
    from PaperTracker.core.query import SearchQuery
    from PaperTracker.storage.deduplicate import SqliteDeduplicateStore

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 120
REQUEST_INTERVAL = 3.0
OPENALEX_SORT = "publication_date:desc,relevance_score:desc"
OPENALEX_LANGUAGE_FILTER = "language:en"


def collect_papers_with_time_filter_openalex(
    query: SearchQuery,
    scope: SearchQuery | None,
    policy: SearchConfig,
    fetch_page_func: Callable[[dict[str, str], int, int], list[dict[str, Any]]],
    dedup_store: SqliteDeduplicateStore | None,
) -> list[Paper]:
    """Collect OpenAlex papers with paged filtering and optional source-local deduplication.

    Args:
        query: Query object for this fetch task.
        scope: Optional global scope merged into query compilation.
        policy: Fetch policy limits and time window configuration.
        fetch_page_func: Callback to fetch one page of OpenAlex works payloads.
        dedup_store: Optional deduplication store for paged fetch within OpenAlex.

    Returns:
        Filtered and source-locally deduplicated papers sorted by
        publication date descending (with relevance score as secondary key),
        capped at `policy.max_results`.
    """
    now = datetime.now(timezone.utc)
    start_time = time()
    params = compile_openalex_params(query=query, scope=scope)
    params = _attach_openalex_filters(params=params, search_config=policy, now=now)
    params = _attach_openalex_sort(params=params)
    not_terms = extract_not_terms(query=query, scope=scope)

    fetched_items = 0
    page_index = 1
    collected: list[Paper] = []

    while policy.max_fetch_items == -1 or fetched_items < policy.max_fetch_items:
        elapsed = time() - start_time
        if elapsed > TIMEOUT_SECONDS:
            logger.warning(
                "OpenAlex fetch timeout (%.1fs > %ds) - fetched %d items; stop",
                elapsed,
                TIMEOUT_SECONDS,
                fetched_items,
            )
            break

        page_size = _resolve_page_size(policy=policy, fetched_items=fetched_items)
        if page_size <= 0:
            break

        payload_items = fetch_page_func(params, page_index, page_size)
        if not payload_items:
            logger.info("OpenAlex upstream exhausted at page=%d; stop", page_index)
            break

        fetched_items += len(payload_items)
        page_papers = parse_openalex_works(payload_items)
        page_papers = apply_positive_filter(page_papers, query=query, scope=scope)
        page_papers = apply_not_filter(page_papers, not_terms)
        page_papers = _apply_time_window(papers=page_papers, search_config=policy, now=now)
        page_papers = _apply_relevance_score_floor(papers=page_papers, search_config=policy)

        if dedup_store is not None:
            page_papers = dedup_store.filter_new_in_source("openalex", page_papers)

        collected.extend(page_papers)

        if len(collected) >= policy.max_results:
            logger.info("OpenAlex reached target max_results=%d; stop", policy.max_results)
            break

        if policy.max_fetch_items != -1 and fetched_items >= policy.max_fetch_items:
            logger.info("OpenAlex reached max_fetch_items=%d; stop", policy.max_fetch_items)
            break

        if len(payload_items) < page_size:
            logger.info("OpenAlex received short page at page=%d; stop", page_index)
            break

        logger.debug("OpenAlex sleep %.1fs before next page", REQUEST_INTERVAL)
        time_module.sleep(REQUEST_INTERVAL)
        page_index += 1

    collected.sort(key=_resolve_quality_sort_key, reverse=True)
    return collected[: policy.max_results]


def _resolve_page_size(*, policy: SearchConfig, fetched_items: int) -> int:
    """Resolve next page size under `fetch_batch_size` and `max_fetch_items`."""
    page_size = policy.fetch_batch_size
    if policy.max_fetch_items == -1:
        return page_size
    remaining = policy.max_fetch_items - fetched_items
    return max(0, min(page_size, remaining))


def _attach_openalex_filters(
    *,
    params: dict[str, str],
    search_config: SearchConfig,
    now: datetime,
) -> dict[str, str]:
    """Attach OpenAlex filter expressions for date/language constraints."""
    filters: list[str] = []
    cutoff_days = _resolve_cutoff_days(search_config)
    if cutoff_days is not None:
        cutoff_date = (now - timedelta(days=cutoff_days)).date().isoformat()
        filters.append(f"from_publication_date:{cutoff_date}")
    filters.append(OPENALEX_LANGUAGE_FILTER)

    if not filters:
        return params

    filter_expr = ",".join(filters)
    existing_filter = params.get("filter", "").strip()
    merged_filter = f"{existing_filter},{filter_expr}" if existing_filter else filter_expr
    return {**params, "filter": merged_filter}


def _attach_openalex_sort(*, params: dict[str, str]) -> dict[str, str]:
    """Attach fixed OpenAlex sort strategy."""
    return {**params, "sort": OPENALEX_SORT}


def _apply_time_window(
    *,
    papers: list[Paper],
    search_config: SearchConfig,
    now: datetime,
) -> list[Paper]:
    """Filter papers by active search window cutoff."""
    cutoff_days = _resolve_cutoff_days(search_config)
    if cutoff_days is None:
        return papers

    cutoff = now - timedelta(days=cutoff_days)
    filtered: list[Paper] = []
    for paper in papers:
        timestamp = _resolve_openalex_timestamp(paper)
        if timestamp is None:
            continue
        if timestamp >= cutoff:
            filtered.append(paper)
    return filtered


def _resolve_cutoff_days(search_config: SearchConfig) -> int | None:
    """Resolve publication-date cutoff days from configured policy."""
    if search_config.fill_enabled:
        return None if search_config.max_lookback_days == -1 else search_config.max_lookback_days
    return search_config.pull_every


def _resolve_sort_timestamp(paper: Paper) -> datetime:
    """Resolve stable timestamp key for final ordering."""
    return _resolve_openalex_timestamp(paper) or datetime.min.replace(tzinfo=timezone.utc)


def _resolve_openalex_timestamp(paper: Paper) -> datetime | None:
    """Resolve OpenAlex candidate timestamp for time checks and ordering."""
    return paper.published or paper.updated


def _apply_relevance_score_floor(*, papers: list[Paper], search_config: SearchConfig) -> list[Paper]:
    """Filter by minimum OpenAlex relevance score when configured."""
    score_floor = search_config.openalex_relevance_threshold
    if score_floor <= 0:
        return papers
    return [paper for paper in papers if _resolve_relevance_score(paper) >= score_floor]


def _resolve_quality_sort_key(paper: Paper) -> tuple[float, float]:
    """Build final sort key: publication date first, relevance score second."""
    relevance = _resolve_relevance_score(paper)
    timestamp = _resolve_sort_timestamp(paper).timestamp()
    return timestamp, relevance


def _resolve_relevance_score(paper: Paper) -> float:
    """Read normalized relevance score from paper extra fields."""
    raw_score = paper.extra.get("relevance_score")
    if isinstance(raw_score, bool):
        return 0.0
    if isinstance(raw_score, (int, float)):
        return float(raw_score)
    return 0.0
