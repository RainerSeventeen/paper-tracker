"""arXiv 数据源适配。

将 query 构造、HTTP 拉取与 XML 解析组装为 `PaperSource` 的实现。
"""

from __future__ import annotations

from dataclasses import dataclass

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.services.search import PaperSource
from PaperTracker.sources.arxiv.client import ArxivApiClient
from PaperTracker.sources.arxiv.parser import parse_arxiv_feed
from PaperTracker.sources.arxiv.query import build_search_query


@dataclass(slots=True)
class ArxivSource(PaperSource):
    client: ArxivApiClient
    name: str = "arxiv"

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
            query: SearchQuery including keywords/categories/exclusions.
            max_results: Maximum number of results to return.
            sort_by: Sort field (submittedDate/lastUpdatedDate).
            sort_order: Sort order (ascending/descending).

        Returns:
            A list of Paper.
        """
        search_query = build_search_query(
            categories=query.categories,
            keywords=query.keywords,
            exclude_keywords=query.exclude_keywords,
            logic=query.logic,
        )
        xml = self.client.fetch_feed(
            search_query=search_query,
            start=0,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return list(parse_arxiv_feed(xml))
