"""OpenAlex source adapter."""

from __future__ import annotations

from dataclasses import dataclass

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.sources.openalex.client import OpenAlexApiClient
from PaperTracker.sources.openalex.parser import parse_openalex_works
from PaperTracker.sources.openalex.query import apply_not_filter, compile_openalex_params, extract_not_terms


@dataclass(slots=True)
class OpenAlexSource:
    """OpenAlex-backed source adapter that returns normalized papers."""

    client: OpenAlexApiClient
    scope: SearchQuery | None = None
    name: str = "openalex"

    def search(self, query: SearchQuery, *, max_results: int) -> list[Paper]:
        """Search papers from OpenAlex and normalize the result set.

        Args:
            query: Structured user query to compile for OpenAlex.
            max_results: Maximum number of requested items.

        Returns:
            A list of normalized ``Paper`` objects.
        """
        params = compile_openalex_params(query=query, scope=self.scope)
        items = self.client.fetch_works(params=params, max_results=max_results)
        papers = parse_openalex_works(items)
        not_terms = extract_not_terms(query=query, scope=self.scope)
        return apply_not_filter(papers, not_terms)

    def close(self) -> None:
        """Close resources held by the OpenAlex source adapter."""
        self.client.close()
