"""搜索服务层。

向上为 CLI 提供稳定的用例接口，向下通过 `PaperSource` 协议对接不同数据源。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery


class PaperSource(Protocol):
    name: str

    def search(
        self,
        query: SearchQuery,
        *,
        max_results: int,
        sort_by: str,
        sort_order: str,
    ) -> Sequence[Paper]:
        """Search papers using this source.

        Args:
            query: SearchQuery including keywords/categories/exclusions.
            max_results: Maximum number of results to return.
            sort_by: arXiv sorting field (source-specific).
            sort_order: Sorting order (source-specific).

        Returns:
            A sequence of Paper.
        """
        raise NotImplementedError


@dataclass(slots=True)
class PaperSearchService:
    source: PaperSource

    def search(
        self,
        query: SearchQuery,
        *,
        max_results: int = 20,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
    ) -> Sequence[Paper]:
        """Search papers via the configured PaperSource.

        Args:
            query: SearchQuery including keywords/categories/exclusions.
            max_results: Maximum number of results to return.
            sort_by: Sorting field.
            sort_order: Sorting order.

        Returns:
            A sequence of Paper.
        """
        return self.source.search(
            query,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order,
        )
