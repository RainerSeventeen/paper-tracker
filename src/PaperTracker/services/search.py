"""Search service layer.

Provides a stable use-case API to the CLI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.utils.log import log


class PaperSource(Protocol):
    """Protocol for an external paper data source."""

    name: str

    def search(
        self,
        query: SearchQuery,
        *,
        max_results: int,
    ) -> Sequence[Paper]:
        """Search papers using this source."""
        raise NotImplementedError


@dataclass(slots=True)
class PaperSearchService:
    """Application service that searches papers via a configured source."""

    source: PaperSource

    def search(
        self,
        query: SearchQuery,
        *,
        max_results: int = 20,
    ) -> Sequence[Paper]:
        """Search papers via the configured source.

        Args:
            query: Source-agnostic structured query.
            max_results: Maximum number of results to return.

        Returns:
            A sequence of Paper.
        """
        log.debug(
            "Search service start: source=%s max_results=%s",
            getattr(self.source, "name", "unknown"),
            max_results,
        )
        return self.source.search(
            query,
            max_results=max_results,
        )
