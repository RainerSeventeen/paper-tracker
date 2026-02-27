"""Search service layer for PaperTracker.

Provides abstraction over different paper search sources and factory
functions for component creation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PaperTracker.services.search import PaperSearchService, PaperSource
from PaperTracker.sources.registry import build_source

if TYPE_CHECKING:
    from PaperTracker.config import AppConfig
    from PaperTracker.storage.deduplicate import SqliteDeduplicateStore


def create_search_service(
    config: AppConfig,
    dedup_store: SqliteDeduplicateStore | None = None,
) -> PaperSearchService:
    """Create a search service with configured data sources.

    Args:
        config: Application configuration containing source settings.
        dedup_store: Optional deduplication store for source filtering.

    Returns:
        Configured PaperSearchService instance.
    """
    sources: list[PaperSource] = [
        build_source(source_name, config=config, dedup_store=dedup_store)
        for source_name in config.search.sources
    ]

    return PaperSearchService(sources=tuple(sources))


__all__ = [
    "PaperSearchService",
    "PaperSource",
    "create_search_service",
]
