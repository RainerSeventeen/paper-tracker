"""arXiv-specific multi-round fetching strategy.

Provides time-window filtering and optional fill mode to collect enough papers
while preserving deterministic sorting and optional persistent deduplication.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from time import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PaperTracker.config import SearchConfig
    from PaperTracker.core.models import Paper
    from PaperTracker.core.query import SearchQuery
    from PaperTracker.storage.deduplicate import SqliteDeduplicateStore

logger = logging.getLogger(__name__)

ARXIV_SORT_BY = "lastUpdatedDate"
ARXIV_SORT_ORDER = "descending"
TIMEOUT_SECONDS = 120


def collect_papers_with_time_filter(
    query: SearchQuery,
    scope: SearchQuery | None,
    policy: SearchConfig,
    fetch_page_func: Callable[[str, int, int, str, str], list[Paper]],
    dedup_store: SqliteDeduplicateStore | None,
) -> list[Paper]:
    """Collect papers with time filtering and optional persistent deduplication.

    This arXiv-specific strategy uses fixed sorting (`lastUpdatedDate` +
    `descending`), fetches pages until limits are hit, filters papers by strict
    and optional fill windows, then applies datastore deduplication.

    Args:
        query: Query object for this fetch task.
        scope: Optional global scope merged into query compilation.
        policy: Fetch policy limits and time window configuration.
        fetch_page_func: Paged fetch callback with arXiv API parameters.
        dedup_store: Optional deduplication store.

    Returns:
        Filtered and deduplicated papers sorted by timestamp descending,
        capped at `policy.max_results`.
    """
    from PaperTracker.sources.arxiv.query import compile_search_query

    candidates: list[Paper] = []
    page_offset = 0
    fetched_items = 0
    now = datetime.now(timezone.utc)
    start_time = time()

    search_query_str = compile_search_query(query=query, scope=scope)

    logger.info(
        "Start collecting papers - query: '%s', target: %d",
        query.name or "unnamed",
        policy.max_results,
    )

    while policy.max_fetch_items == -1 or fetched_items < policy.max_fetch_items:
        elapsed = time() - start_time
        if elapsed > TIMEOUT_SECONDS:
            logger.warning(
                "Fetch timeout (%.1fs > %ds) - fetched %d items, %d candidates; stop",
                elapsed,
                TIMEOUT_SECONDS,
                fetched_items,
                len(candidates),
            )
            break

        page = fetch_page_func(
            search_query_str,
            page_offset,
            policy.fetch_batch_size,
            ARXIV_SORT_BY,
            ARXIV_SORT_ORDER,
        )
        if not page:
            logger.info("No more upstream results at offset=%d; stop", page_offset)
            break

        fetched_items += len(page)
        page_num = page_offset // policy.fetch_batch_size + 1
        logger.info("Fetched page %d: %d items (total %d)", page_num, len(page), fetched_items)
        page_offset += policy.fetch_batch_size

        page_candidates = []
        for paper in page:
            if _can_include(
                paper,
                pull_every_days=policy.pull_every,
                fill_enabled=policy.fill_enabled,
                max_lookback_days=policy.max_lookback_days,
                now=now,
            ):
                page_candidates.append(paper)
            elif _resolve_timestamp(paper) is None:
                logger.debug("Skip paper without timestamp: %s", paper.id)

        candidates.extend(page_candidates)
        logger.debug("Page candidates: %d (total candidates %d)", len(page_candidates), len(candidates))

        if policy.max_fetch_items != -1 and fetched_items >= policy.max_fetch_items:
            logger.info("Reached max_fetch_items=%d; stop", policy.max_fetch_items)
            break

    if dedup_store:
        logger.info("Run persistent deduplication for %d candidates", len(candidates))
        new_items = dedup_store.filter_new(candidates)
        dedup_store.mark_seen(new_items)
        logger.info("Deduplication done - new papers: %d", len(new_items))
    else:
        new_items = candidates
        logger.debug("Persistent deduplication is disabled")

    new_items.sort(
        key=lambda paper: (
            paper.updated or paper.published or datetime.min.replace(tzinfo=timezone.utc)
        ),
        reverse=True,
    )
    result = new_items[: policy.max_results]

    if len(result) < policy.max_results:
        logger.warning(
            "Target not reached - target: %d, actual: %d (candidates %d, after dedup %d)",
            policy.max_results,
            len(result),
            len(candidates),
            len(new_items),
        )
    else:
        logger.info("Collection done - returning %d papers", len(result))

    return result


def _can_include(
    paper: Paper,
    *,
    pull_every_days: int,
    fill_enabled: bool,
    max_lookback_days: int,
    now: datetime,
) -> bool:
    """Decide whether a paper can enter the candidate set.

    Args:
        paper: Paper to evaluate.
        pull_every_days: Strict window size in days.
        fill_enabled: Whether fill mode is enabled.
        max_lookback_days: Maximum lookback in fill mode; `-1` means unlimited.
        now: Current UTC timestamp.

    Returns:
        True when the paper should be included; otherwise False.
    """
    if _is_in_strict_window(paper, pull_every_days, now):
        return True
    if fill_enabled and _is_in_fill_window(paper, max_lookback_days, now):
        return True
    return False


def _is_in_strict_window(paper: Paper, pull_every_days: int, now: datetime) -> bool:
    """Check whether a paper is inside the strict time window.

    Args:
        paper: Paper to evaluate.
        pull_every_days: Strict window size in days.
        now: Current UTC timestamp.

    Returns:
        True when paper timestamp is newer than strict cutoff.
    """
    timestamp = _resolve_timestamp(paper)
    if timestamp is None:
        return False
    return timestamp >= now - timedelta(days=pull_every_days)


def _is_in_fill_window(paper: Paper, max_lookback_days: int, now: datetime) -> bool:
    """Check whether a paper is inside the fill time window.

    Args:
        paper: Paper to evaluate.
        max_lookback_days: Fill lookback size in days; `-1` means unlimited.
        now: Current UTC timestamp.

    Returns:
        True when fill-window constraint is satisfied.
    """
    timestamp = _resolve_timestamp(paper)
    if timestamp is None:
        return False
    if max_lookback_days == -1:
        return True
    return timestamp >= now - timedelta(days=max_lookback_days)


def _resolve_timestamp(paper: Paper) -> datetime | None:
    """Resolve primary timestamp for sorting/filtering.

    Args:
        paper: Paper entity.

    Returns:
        `updated` when available, otherwise `published`; returns None when both
        are missing.
    """
    return paper.updated or paper.published
