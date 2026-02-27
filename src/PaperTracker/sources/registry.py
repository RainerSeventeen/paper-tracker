"""Source registry and builders for search sources."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PaperTracker.config import AppConfig
    from PaperTracker.services.search import PaperSource
    from PaperTracker.storage.deduplicate import SqliteDeduplicateStore

SourceBuilder = Callable[["AppConfig", "SqliteDeduplicateStore | None"], "PaperSource"]


def build_source(
    source_name: str,
    *,
    config: AppConfig,
    dedup_store: SqliteDeduplicateStore | None,
) -> PaperSource:
    """Build one source instance by registry name."""
    registry = _source_builders()
    builder = registry.get(source_name)
    if builder is None:
        raise ValueError(f"Unsupported source in config.search.sources: {source_name}")
    return builder(config, dedup_store)


def supported_source_names() -> tuple[str, ...]:
    """Return all supported source names."""
    return tuple(_source_builders().keys())


def _source_builders() -> dict[str, SourceBuilder]:
    """Return source builder registry."""
    return {
        "arxiv": _build_arxiv_source,
        "crossref": _build_crossref_source,
    }


def _build_arxiv_source(config: AppConfig, dedup_store: SqliteDeduplicateStore | None) -> PaperSource:
    """Build arXiv source."""
    del dedup_store
    from PaperTracker.sources.arxiv.client import ArxivApiClient
    from PaperTracker.sources.arxiv.source import ArxivSource

    return ArxivSource(
        client=ArxivApiClient(),
        scope=config.search.scope,
        keep_version=config.storage.keep_arxiv_version,
        search_config=config.search,
    )


def _build_crossref_source(config: AppConfig, dedup_store: SqliteDeduplicateStore | None) -> PaperSource:
    """Build Crossref source."""
    del dedup_store
    from PaperTracker.sources.crossref.client import CrossrefApiClient
    from PaperTracker.sources.crossref.source import CrossrefSource

    return CrossrefSource(
        client=CrossrefApiClient(),
        scope=config.search.scope,
    )
