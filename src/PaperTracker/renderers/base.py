"""Base classes for output writers.

Provides abstraction for writing search results to console or files.
Separates control flow from output logic for better testability.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

from PaperTracker.core.query import SearchQuery
from PaperTracker.renderers.view_models import PaperView


class OutputWriter(ABC):
    """Abstract base class for command output writers."""

    @abstractmethod
    def write_query_result(
        self,
        papers: list[PaperView],
        query: SearchQuery,
        scope: SearchQuery | None,
    ) -> None:
        """Write results from a single query.

        Args:
            papers: List of paper views to display.
            query: The query that produced these results.
            scope: Optional global scope applied to the query.
        """

    @abstractmethod
    def finalize(self, action: str) -> None:
        """Finalize output (e.g., write accumulated results to file).

        Args:
            action: The CLI command name (e.g., 'search').
        """


@dataclass(slots=True)
class MultiOutputWriter(OutputWriter):
    """Delegate output to multiple writers."""

    writers: Sequence[OutputWriter]

    def write_query_result(
        self,
        papers: list[PaperView],
        query: SearchQuery,
        scope: SearchQuery | None,
    ) -> None:
        """Send query results to all writers."""
        for writer in self.writers:
            writer.write_query_result(papers, query, scope)

    def finalize(self, action: str) -> None:
        """Finalize all writers."""
        for writer in self.writers:
            writer.finalize(action)
