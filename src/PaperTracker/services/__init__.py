"""Search service layer for PaperTracker.

Provides abstraction over different paper search sources and factory
functions for component creation.
"""

from __future__ import annotations

from PaperTracker.services.search import PaperSearchService, PaperSource


def create_search_service(config: AppConfig) -> PaperSearchService:  # type: ignore[name-defined]
    """Create a search service with configured data source.

    Currently creates an ArxivSource-based service. Can be extended
    to support additional sources by checking config parameters.

    Args:
        config: Application configuration containing source settings.

    Returns:
        Configured PaperSearchService instance.
    """
    from PaperTracker.config import AppConfig
    from PaperTracker.sources.arxiv.client import ArxivApiClient
    from PaperTracker.sources.arxiv.source import ArxivSource

    return PaperSearchService(
        source=ArxivSource(
            client=ArxivApiClient(),
            scope=config.scope,
            keep_version=config.arxiv_keep_version,
        )
    )


__all__ = [
    "PaperSearchService",
    "PaperSource",
    "create_search_service",
]
