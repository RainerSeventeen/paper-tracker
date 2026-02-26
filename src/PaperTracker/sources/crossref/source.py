"""Crossref source adapter."""

from __future__ import annotations

from dataclasses import dataclass

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.sources.crossref.client import CrossrefApiClient
from PaperTracker.sources.crossref.parser import parse_crossref_items
from PaperTracker.sources.crossref.query import compile_crossref_query


@dataclass(slots=True)
class CrossrefSource:
    """Crossref-backed paper source implementation."""

    client: CrossrefApiClient
    scope: SearchQuery | None = None
    name: str = "crossref"

    def search(self, query: SearchQuery, *, max_results: int) -> list[Paper]:
        """Search papers from Crossref REST API."""
        query_text = compile_crossref_query(query=query, scope=self.scope)
        items = self.client.fetch_works(query_text=query_text, max_results=max_results)
        return parse_crossref_items(items)

    def close(self) -> None:
        """Close source resources."""
        self.client.close()
