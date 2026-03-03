"""OpenAlex data source adapter.

Builds OpenAlex source behavior by delegating paged fetching and filtering to
the OpenAlex-specific multi-round strategy module.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.sources.openalex.client import OpenAlexApiClient
from PaperTracker.sources.openalex.fetch import collect_papers_with_time_filter_openalex

if TYPE_CHECKING:
    from PaperTracker.config import SearchConfig
    from PaperTracker.storage.deduplicate import SqliteDeduplicateStore


@dataclass(slots=True)
class OpenAlexSource:
    """OpenAlex-backed source adapter that returns normalized papers."""

    client: OpenAlexApiClient
    scope: SearchQuery | None = None
    search_config: SearchConfig | None = None
    dedup_store: SqliteDeduplicateStore | None = None
    name: str = "openalex"

    def search(self, query: SearchQuery, *, max_results: int) -> list[Paper]:
        """Search papers from OpenAlex and normalize the result set.

        Args:
            query: Structured user query to compile for OpenAlex.
            max_results: Maximum number of requested items.

        Returns:
            A list of normalized ``Paper`` objects.
        """
        if self.search_config is None:
            raise ValueError("OpenAlexSource.search_config is required for multi-round fetching")

        policy = (
            self.search_config
            if self.search_config.max_results == max_results
            else replace(self.search_config, max_results=max_results)
        )

        return collect_papers_with_time_filter_openalex(
            query=query,
            scope=self.scope,
            policy=policy,
            fetch_page_func=self._fetch_page,
            dedup_store=self.dedup_store,
        )

    def _fetch_page(
        self,
        params: dict[str, str],
        page: int,
        page_size: int,
    ) -> list[dict[str, object]]:
        """Fetch one OpenAlex works page for strategy callbacks."""
        return self.client.fetch_works_page(
            params=params,
            page=page,
            page_size=page_size,
        )

    def close(self) -> None:
        """Close resources held by the OpenAlex source adapter."""
        self.client.close()
