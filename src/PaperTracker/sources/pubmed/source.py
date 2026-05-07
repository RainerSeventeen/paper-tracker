"""PubMed data source adapter.

Wires together query compilation, date-range resolution, and the paged
ESearch+EFetch fetch strategy into the PaperSource protocol.
"""

from __future__ import annotations

import time as time_module
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.sources.pubmed.client import PubMedApiClient
from PaperTracker.sources.pubmed.fetch import INTRA_PAGE_INTERVAL, collect_pubmed_papers
from PaperTracker.sources.pubmed.parser import parse_pubmed_xml
from PaperTracker.sources.pubmed.query import compile_pubmed_term

if TYPE_CHECKING:
    from PaperTracker.config import SearchConfig
    from PaperTracker.storage.deduplicate import SqliteDeduplicateStore


@dataclass(slots=True)
class PubMedSource:
    """PubMed-backed source adapter that returns normalized papers."""

    client: PubMedApiClient
    name: str = "pubmed"
    scope: SearchQuery | None = None
    search_config: SearchConfig | None = None
    dedup_store: SqliteDeduplicateStore | None = None

    def search(self, query: SearchQuery, *, max_results: int) -> list[Paper]:
        """Search papers from PubMed and return a normalized result set.

        Args:
            query: Structured user query compiled into PubMed term syntax.
            max_results: Maximum number of papers to return.

        Returns:
            A list of normalized Paper objects sorted by published date descending.

        Raises:
            ValueError: If search_config is not set or query has no supported fields.
        """
        if self.search_config is None:
            raise ValueError("PubMedSource.search_config is required for paged fetching")

        policy = (
            self.search_config
            if self.search_config.max_results == max_results
            else replace(self.search_config, max_results=max_results)
        )

        term = compile_pubmed_term(query=query, scope=self.scope)
        now = datetime.now(timezone.utc)
        mindate, maxdate = _resolve_date_range(policy, now)

        return collect_pubmed_papers(
            term=term,
            mindate=mindate,
            maxdate=maxdate,
            policy=policy,
            fetch_page_func=self._fetch_page,
            dedup_store=self.dedup_store,
        )

    def _fetch_page(
        self,
        term: str,
        mindate: str | None,
        maxdate: str | None,
        retstart: int,
        retmax: int,
    ) -> tuple[list[Paper], int]:
        """Execute one ESearch+EFetch round and return papers with upstream count.

        Args:
            term: PubMed term string.
            mindate: Optional start date filter (YYYY/MM/DD).
            maxdate: Optional end date filter (YYYY/MM/DD).
            retstart: Zero-based PMID offset for ESearch pagination.
            retmax: Maximum PMIDs to retrieve in this batch.

        Returns:
            Tuple of (parsed Paper list, upstream PMID count from ESearch idlist).
        """
        result = self.client.esearch(
            term=term,
            retstart=retstart,
            retmax=retmax,
            mindate=mindate,
            maxdate=maxdate,
        )
        pmids = result["idlist"]
        upstream_count = len(pmids)

        if upstream_count == 0:
            return [], 0

        time_module.sleep(INTRA_PAGE_INTERVAL)
        xml = self.client.efetch(pmids=pmids)
        return parse_pubmed_xml(xml), upstream_count

    def close(self) -> None:
        """Close resources held by the PubMed source adapter."""
        self.client.close()


def _resolve_date_range(
    policy: SearchConfig,
    now: datetime,
) -> tuple[str | None, str | None]:
    """Resolve PubMed date range strings from configured search policy.

    Args:
        policy: Active search configuration.
        now: Current UTC datetime used as the reference point.

    Returns:
        Tuple of (mindate, maxdate) as YYYY/MM/DD strings, or (None, None)
        when no date restriction applies.
    """
    if policy.fill_enabled:
        if policy.max_lookback_days == -1:
            return None, None
        mindate = (now - timedelta(days=policy.max_lookback_days)).strftime("%Y/%m/%d")
        maxdate = now.strftime("%Y/%m/%d")
        return mindate, maxdate

    mindate = (now - timedelta(days=policy.pull_every)).strftime("%Y/%m/%d")
    maxdate = now.strftime("%Y/%m/%d")
    return mindate, maxdate
