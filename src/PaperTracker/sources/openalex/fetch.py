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


def collect_papers_with_time_filter_openalex(
    query: SearchQuery,
    scope: SearchQuery | None,
    policy: SearchConfig,
    fetch_page_func: Callable[[dict[str, str], int, int], list[dict[str, Any]]],
    dedup_store: SqliteDeduplicateStore | None,
) -> list[Paper]:
    """Collect OpenAlex papers with paged filtering and optional deduplication.

    Args:
        query: Query object for this fetch task.
        scope: Optional global scope merged into query compilation.
        policy: Fetch policy limits and time window configuration.
        fetch_page_func: Callback to fetch one page of OpenAlex works payloads.
        dedup_store: Optional deduplication store.

    Returns:
        Filtered and deduplicated papers sorted by unified timestamp descending,
        capped at `policy.max_results`.
    """
    now = datetime.now(timezone.utc)
    start_time = time()
    params = compile_openalex_params(query=query, scope=scope)
    params = _attach_publication_date_filter(params=params, search_config=policy, now=now)
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

        if dedup_store is not None:
            page_papers = dedup_store.filter_new(page_papers)

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

    collected.sort(key=_resolve_sort_timestamp, reverse=True)
    return collected[: policy.max_results]


def _resolve_page_size(*, policy: SearchConfig, fetched_items: int) -> int:
    """Resolve next page size under `fetch_batch_size` and `max_fetch_items`."""
    page_size = policy.fetch_batch_size
    if policy.max_fetch_items == -1:
        return page_size
    remaining = policy.max_fetch_items - fetched_items
    return max(0, min(page_size, remaining))


def _attach_publication_date_filter(
    *,
    params: dict[str, str],
    search_config: SearchConfig,
    now: datetime,
) -> dict[str, str]:
    """Attach OpenAlex publication-date lower bound to request params."""
    cutoff_days = _resolve_cutoff_days(search_config)
    if cutoff_days is None:
        return params

    cutoff_date = (now - timedelta(days=cutoff_days)).date().isoformat()
    filter_expr = f"from_publication_date:{cutoff_date}"
    existing_filter = params.get("filter", "").strip()
    merged_filter = f"{existing_filter},{filter_expr}" if existing_filter else filter_expr
    return {**params, "filter": merged_filter}


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
