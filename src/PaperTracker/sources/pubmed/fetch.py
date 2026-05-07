"""PubMed paged fetch strategy.

Collects PubMed papers across multiple ESearch+EFetch round trips with rate limiting,
optional source-local deduplication, and deterministic final ordering.
"""

from __future__ import annotations

import logging
import time as time_module
from collections.abc import Callable
from typing import TYPE_CHECKING

from PaperTracker.core.models import Paper

if TYPE_CHECKING:
    from PaperTracker.config import SearchConfig
    from PaperTracker.storage.deduplicate import SqliteDeduplicateStore

logger = logging.getLogger(__name__)

REQUEST_INTERVAL = 1.0
INTRA_PAGE_INTERVAL = 0.5
TIMEOUT_SECONDS = 120


def collect_pubmed_papers(
    term: str,
    mindate: str | None,
    maxdate: str | None,
    policy: SearchConfig,
    fetch_page_func: Callable[[str, str | None, str | None, int, int], tuple[list[Paper], int]],
    dedup_store: SqliteDeduplicateStore | None,
) -> list[Paper]:
    """Collect PubMed papers with pagination, rate limiting, and optional deduplication.

    Args:
        term: Compiled PubMed term string.
        mindate: Optional start date in YYYY/MM/DD format for ESearch.
        maxdate: Optional end date in YYYY/MM/DD format for ESearch.
        policy: Fetch policy with limits and batch size.
        fetch_page_func: Callback that executes one ESearch+EFetch round,
            returning ``(papers, upstream_count)``.
        dedup_store: Optional deduplication store for source-local filtering.

    Returns:
        Papers sorted by ``published`` descending, capped at ``policy.max_results``.
    """
    start_time = time_module.time()
    fetched_items = 0
    retstart = 0
    collected: list[Paper] = []

    while policy.max_fetch_items == -1 or fetched_items < policy.max_fetch_items:
        elapsed = time_module.time() - start_time
        if elapsed > TIMEOUT_SECONDS:
            logger.warning(
                "PubMed fetch timeout (%.1fs > %ds) - fetched %d items; stop",
                elapsed,
                TIMEOUT_SECONDS,
                fetched_items,
            )
            break

        page_size = _resolve_page_size(policy=policy, fetched_items=fetched_items)
        if page_size <= 0:
            break

        page_papers, upstream_count = fetch_page_func(term, mindate, maxdate, retstart, page_size)

        if upstream_count == 0:
            logger.info("PubMed upstream exhausted at retstart=%d; stop", retstart)
            break

        if dedup_store is not None:
            page_papers = dedup_store.filter_new_in_source("pubmed", page_papers)

        collected.extend(page_papers)
        fetched_items += upstream_count

        if len(collected) >= policy.max_results:
            logger.info("PubMed reached target max_results=%d; stop", policy.max_results)
            break

        if policy.max_fetch_items != -1 and fetched_items >= policy.max_fetch_items:
            logger.info("PubMed reached max_fetch_items=%d; stop", policy.max_fetch_items)
            break

        if upstream_count < page_size:
            logger.info("PubMed received short page at retstart=%d; stop", retstart)
            break

        logger.debug("PubMed sleep %.1fs before next page", REQUEST_INTERVAL)
        time_module.sleep(REQUEST_INTERVAL)
        retstart += page_size

    collected.sort(key=_sort_key, reverse=True)
    return collected[: policy.max_results]


def _resolve_page_size(*, policy: SearchConfig, fetched_items: int) -> int:
    """Resolve next page size respecting fetch_batch_size and max_fetch_items."""
    page_size = policy.fetch_batch_size
    if policy.max_fetch_items == -1:
        return page_size
    remaining = policy.max_fetch_items - fetched_items
    return max(0, min(page_size, remaining))


def _sort_key(paper: Paper) -> float:
    """Build sort key from published datetime for descending order."""
    if paper.published is not None:
        return paper.published.timestamp()
    return 0.0
