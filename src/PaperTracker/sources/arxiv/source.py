"""arXiv data source adapter.

Composes query building, HTTP fetching, and XML parsing with arXiv-specific
multi-round fetching strategy.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.sources.arxiv.client import ArxivApiClient
from PaperTracker.sources.arxiv.fetch import collect_papers_with_time_filter
from PaperTracker.sources.arxiv.parser import parse_arxiv_feed

if TYPE_CHECKING:
    from PaperTracker.config import SearchConfig
    from PaperTracker.storage.deduplicate import SqliteDeduplicateStore


@dataclass(slots=True)
class ArxivSource:
    """arXiv-backed source implementation.

    Translates `SearchQuery` into arXiv query syntax, fetches the Atom feed, and
    parses it into internal `Paper` objects. Supports arXiv-specific multi-round
    fetching with time-based filtering.
    """

    client: ArxivApiClient
    name: str = "arxiv"
    scope: SearchQuery | None = None
    keep_version: bool = False
    search_config: SearchConfig | None = None
    dedup_store: SqliteDeduplicateStore | None = None

    def search(
        self,
        query: SearchQuery,
        *,
        max_results: int,
    ) -> list[Paper]:
        """Search papers from arXiv.

        Always uses arXiv-specific multi-round fetching (time filtering +
        optional deduplication). `fill_enabled` only controls candidate
        inclusion window and does not control pagination behavior.

        Args:
            query: Structured query (field -> AND/OR/NOT terms).
            max_results: Target number of returned papers for this query.

        Returns:
            A list of Paper.
        """
        if self.search_config is None:
            raise ValueError("ArxivSource.search_config is required for multi-round fetching")

        policy = (
            self.search_config
            if self.search_config.max_results == max_results
            else replace(self.search_config, max_results=max_results)
        )

        return collect_papers_with_time_filter(
            query=query,
            scope=self.scope,
            policy=policy,
            fetch_page_func=self._fetch_page,
            dedup_store=self.dedup_store,
        )

    def _fetch_page(
        self,
        search_query_str: str,
        start: int,
        max_results: int,
        sort_by: str,
        sort_order: str,
    ) -> list[Paper]:
        """Fetch and parse one arXiv page for strategy callbacks.

        Args:
            search_query_str: Compiled arXiv query string.
            start: Start index for this page.
            max_results: Max results per page.
            sort_by: Sort field for arXiv API.
            sort_order: Sort order for arXiv API.

        Returns:
            Parsed papers from this page.
        """
        xml = self.client.fetch_feed(
            search_query=search_query_str,
            start=start,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return list(parse_arxiv_feed(xml, keep_version=self.keep_version))
