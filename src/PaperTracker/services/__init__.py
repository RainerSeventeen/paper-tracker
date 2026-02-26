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
    """Create a search service with configured data sources.

    Args:
        config: Application configuration containing source settings.
        dedup_store: Optional deduplication store for source filtering.

    Returns:
        Configured PaperSearchService instance.
    """
    sources: list[PaperSource] = []
    for source_name in config.search.sources:
        if source_name == "arxiv":
            from PaperTracker.sources.arxiv.client import ArxivApiClient
            from PaperTracker.sources.arxiv.source import ArxivSource

            sources.append(
                ArxivSource(
                    client=ArxivApiClient(),
                    scope=config.search.scope,
                    keep_version=config.storage.keep_arxiv_version,
                    search_config=config.search,
                    dedup_store=dedup_store,
                )
            )
        elif source_name == "crossref":
            from PaperTracker.sources.crossref.client import CrossrefApiClient
            from PaperTracker.sources.crossref.source import CrossrefSource

            sources.append(
                CrossrefSource(
                    client=CrossrefApiClient(),
                    scope=config.search.scope,
                )
            )
        else:
            raise ValueError(f"Unsupported source in config.search.sources: {source_name}")

    return PaperSearchService(sources=tuple(sources), dedup_store=dedup_store)


__all__ = [
    "PaperSearchService",
    "PaperSource",
    "create_search_service",
]
