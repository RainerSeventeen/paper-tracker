"""arXiv data source adapter.

Composes query building, HTTP fetching, and XML parsing into a `PaperSource`
implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.services.search import PaperSource
from PaperTracker.sources.arxiv.client import ArxivApiClient
from PaperTracker.sources.arxiv.parser import parse_arxiv_feed
from PaperTracker.sources.arxiv.query import compile_search_query


@dataclass(slots=True)
class ArxivSource(PaperSource):
    """`PaperSource` implementation backed by arXiv.

    Translates `SearchQuery` into arXiv query syntax, fetches the Atom feed, and
    parses it into internal `Paper` objects.
    """

    client: ArxivApiClient
    name: str = "arxiv"
    scope: SearchQuery | None = None

    def search(
        self,
        query: SearchQuery,
        *,
        max_results: int,
        sort_by: str,
        sort_order: str,
    ) -> list[Paper]:
        """Search papers from arXiv.

        Args:
            query: Structured query (field -> AND/OR/NOT terms).
            max_results: Maximum number of results to return.
            sort_by: Sort field (submittedDate/lastUpdatedDate).
            sort_order: Sort order (ascending/descending).

        Returns:
            A list of Paper.
        """
        search_query = compile_search_query(query=query, scope=self.scope)
        xml = self.client.fetch_feed(
            search_query=search_query,
            start=0,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return list(parse_arxiv_feed(xml))
