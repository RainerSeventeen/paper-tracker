"""arXiv data source adapter.

Composes query building, HTTP fetching, and XML parsing into a `PaperSource`
implementation with arXiv-specific multi-round fetching strategy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.services.search import PaperSource
from PaperTracker.sources.arxiv.client import ArxivApiClient
from PaperTracker.sources.arxiv.fetch import collect_papers_with_time_filter
from PaperTracker.sources.arxiv.parser import parse_arxiv_feed
from PaperTracker.sources.arxiv.query import compile_search_query
from PaperTracker.utils.log import log

if TYPE_CHECKING:
    from PaperTracker.config import SearchConfig
    from PaperTracker.storage.deduplicate import SqliteDeduplicateStore


@dataclass(slots=True)
class ArxivSource(PaperSource):
    """`PaperSource` implementation backed by arXiv.

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
        sort_by: str,
        sort_order: str,
    ) -> list[Paper]:
        """Search papers from arXiv.

        Uses arXiv-specific multi-round fetching (time filtering + optional
        deduplication) when `search_config` is configured; otherwise falls back
        to single-page behavior for compatibility.

        Args:
            query: Structured query (field -> AND/OR/NOT terms).
            max_results: Maximum number of results to return.
            sort_by: Sort field used when `search_config` is not configured.
            sort_order: Sort order used when `search_config` is not configured.

        Returns:
            A list of Paper.
        """
        # Use multi-round strategy when search config is enabled.
        if self.search_config:
            return collect_papers_with_time_filter(
                query=query,
                scope=self.scope,
                policy=self.search_config,
                fetch_page_func=self._fetch_page,
                dedup_store=self.dedup_store,
            )

        # Backward-compatible single-page fetch.
        return self.search_page(
            query=query,
            start=0,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def search_page(
        self,
        query: SearchQuery,
        *,
        start: int,
        max_results: int,
        sort_by: str,
        sort_order: str,
    ) -> list[Paper]:
        """Search a single page of papers from arXiv.

        Args:
            query: Structured query (field -> AND/OR/NOT terms).
            start: Starting index for pagination.
            max_results: Maximum number of results to return in this page.
            sort_by: Sort field (submittedDate/lastUpdatedDate).
            sort_order: Sort order (ascending/descending).

        Returns:
            A list of Paper for this page.
        """
        search_query = compile_search_query(query=query, scope=self.scope)
        log.debug(
            "arXiv page query: %s (start=%s max_results=%s sort_by=%s sort_order=%s)",
            search_query,
            start,
            max_results,
            sort_by,
            sort_order,
        )
        xml = self.client.fetch_feed(
            search_query=search_query,
            start=start,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        items = list(parse_arxiv_feed(xml, keep_version=self.keep_version))
        log.debug("arXiv page parsed %d entries", len(items))
        return items

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
