"""Base classes for output writers.

Provides abstraction for writing search results to console or files.
Separates control flow from output logic for better testability.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery


class OutputWriter(ABC):
    """Abstract base class for command output writers."""

    @abstractmethod
    def write_query_result(
        self,
        papers: list[Paper],
        query: SearchQuery,
        scope: SearchQuery | None,
    ) -> None:
        """Write results from a single query.

        Args:
            papers: List of papers found.
            query: The query that produced these results.
            scope: Optional global scope applied to the query.
        """

    @abstractmethod
    def finalize(self, action: str) -> None:
        """Finalize output (e.g., write accumulated results to file).

        Args:
            action: The CLI command name (e.g., 'search').
        """
