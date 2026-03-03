"""OpenAlex source adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.sources.openalex.client import OpenAlexApiClient
from PaperTracker.sources.openalex.parser import parse_openalex_works
from PaperTracker.sources.openalex.query import (
    apply_not_filter,
    apply_positive_filter,
    compile_openalex_params,
    extract_not_terms,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from PaperTracker.config import SearchConfig


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class OpenAlexSource:
    """OpenAlex-backed source adapter that returns normalized papers."""

    client: OpenAlexApiClient
    scope: SearchQuery | None = None
    search_config: SearchConfig | None = None
    now_func: Callable[[], datetime] = _utc_now
    name: str = "openalex"

    def search(self, query: SearchQuery, *, max_results: int) -> list[Paper]:
        """Search papers from OpenAlex and normalize the result set.

        Args:
            query: Structured user query to compile for OpenAlex.
            max_results: Maximum number of requested items.

        Returns:
            A list of normalized ``Paper`` objects.
        """
        now = self.now_func()
        params = compile_openalex_params(query=query, scope=self.scope)
        params = _attach_publication_date_filter(params=params, search_config=self.search_config, now=now)
        fetch_limit = _resolve_fetch_limit(max_results=max_results, search_config=self.search_config)
        items = self.client.fetch_works(params=params, max_results=fetch_limit)
        papers = parse_openalex_works(items)
        papers = apply_positive_filter(papers, query=query, scope=self.scope)
        not_terms = extract_not_terms(query=query, scope=self.scope)
        filtered = apply_not_filter(papers, not_terms)
        filtered = _apply_time_window(papers=filtered, search_config=self.search_config, now=now)
        return filtered[:max_results]

    def close(self) -> None:
        """Close resources held by the OpenAlex source adapter."""
        self.client.close()


def _resolve_fetch_limit(*, max_results: int, search_config: SearchConfig | None) -> int:
    """Resolve upstream fetch size for OpenAlex pagination."""
    if search_config is None:
        return max_results

    if search_config.max_fetch_items == -1:
        return max_results

    return max(max_results, search_config.max_fetch_items)


def _attach_publication_date_filter(
    *,
    params: dict[str, str],
    search_config: SearchConfig | None,
    now: datetime,
) -> dict[str, str]:
    """Attach OpenAlex publication-date lower bound to request params."""
    if search_config is None:
        return params

    cutoff_days = _resolve_cutoff_days(search_config)
    if cutoff_days is None:
        return params

    cutoff_date = (now - timedelta(days=cutoff_days)).date().isoformat()
    filter_expr = f"from_publication_date:{cutoff_date}"
    existing_filter = params.get("filter", "").strip()
    merged_filter = f"{existing_filter},{filter_expr}" if existing_filter else filter_expr
    return {**params, "filter": merged_filter}


def _apply_time_window(
    *,
    papers: list[Paper],
    search_config: SearchConfig | None,
    now: datetime,
) -> list[Paper]:
    """Filter papers using configured search time windows.

    OpenAlex `updated_date` often represents metadata refresh time. To avoid
    old papers being treated as "new", this filter prefers publication time and
    only falls back to `updated` when `published` is missing.
    """
    if search_config is None:
        return papers

    cutoff_days = _resolve_cutoff_days(search_config)
    if cutoff_days is None:
        return papers
    cutoff = now - timedelta(days=cutoff_days)

    filtered: list[Paper] = []
    for paper in papers:
        timestamp = _resolve_openalex_timestamp(paper)
        if timestamp is None:
            continue
        if timestamp >= cutoff:
            filtered.append(paper)
    return filtered


def _resolve_openalex_timestamp(paper: Paper) -> datetime | None:
    """Resolve OpenAlex candidate timestamp for time-window checks."""
    return paper.published or paper.updated


def _resolve_cutoff_days(search_config: SearchConfig) -> int | None:
    """Resolve publication-date cutoff days from configured policy."""
    if search_config.fill_enabled:
        return None if search_config.max_lookback_days == -1 else search_config.max_lookback_days
    return search_config.pull_every
