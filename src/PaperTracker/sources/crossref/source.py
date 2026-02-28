"""Crossref source adapter."""

from __future__ import annotations

from dataclasses import dataclass

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.sources.crossref.client import CrossrefApiClient
from PaperTracker.sources.crossref.parser import parse_crossref_items
from PaperTracker.sources.crossref.query import apply_not_filter, compile_crossref_params, extract_not_terms


@dataclass(slots=True)
class CrossrefSource:
    """Crossref-backed source adapter that returns normalized papers."""

    client: CrossrefApiClient
    scope: SearchQuery | None = None
    name: str = "crossref"

    def search(self, query: SearchQuery, *, max_results: int) -> list[Paper]:
        """Search papers from Crossref and normalize the result set.

        Args:
            query: Structured user query to compile into Crossref parameters.
            max_results: Maximum number of items requested from Crossref.

        Returns:
            A list of normalized ``Paper`` objects filtered by NOT terms.
        """
        query_params = compile_crossref_params(query=query, scope=self.scope)
        items = self.client.fetch_works(query_params=query_params, max_results=max_results)
        papers = parse_crossref_items(items)
        not_terms = extract_not_terms(query=query, scope=self.scope)
        return apply_not_filter(papers, not_terms)

    def close(self) -> None:
        """Close resources held by the Crossref source adapter.
        """
        self.client.close()
