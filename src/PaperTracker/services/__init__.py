"""Search service layer for PaperTracker.

Provides abstraction over different paper search sources and factory
functions for component creation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PaperTracker.services.search import PaperSearchService, PaperSource

if TYPE_CHECKING:
    from PaperTracker.config import AppConfig
    from PaperTracker.storage.deduplicate import SqliteDeduplicateStore


def create_search_service(
    config: AppConfig,
    dedup_store: SqliteDeduplicateStore | None = None,
) -> PaperSearchService:
    """Create a search service with configured data source.

    Currently creates an ArxivSource-based service. Can be extended
    to support additional sources by checking config parameters.

    Args:
        config: Application configuration containing source settings.
        dedup_store: Optional deduplication store for arXiv-specific multi-round fetching.

    Returns:
        Configured PaperSearchService instance.
    """
    from PaperTracker.sources.arxiv.client import ArxivApiClient
    from PaperTracker.sources.arxiv.source import ArxivSource

    return PaperSearchService(
        source=ArxivSource(
            client=ArxivApiClient(),
            scope=config.scope,
            keep_version=config.arxiv_keep_version,
            search_config=config.search,
            dedup_store=dedup_store,
        )
    )


__all__ = [
    "PaperSearchService",
    "PaperSource",
    "create_search_service",
]
