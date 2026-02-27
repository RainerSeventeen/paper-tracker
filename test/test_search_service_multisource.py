"""Tests for multi-source search aggregation service."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.services.search import PaperSearchService


class _StubSource:
    def __init__(self, *, name: str, papers: list[Paper] | None = None, should_fail: bool = False) -> None:
        self.name = name
        self._papers = papers or []
        self._should_fail = should_fail

    def search(self, query: SearchQuery, *, max_results: int) -> list[Paper]:
        del query, max_results
        if self._should_fail:
            raise RuntimeError(f"{self.name} failed")
        return list(self._papers)

    def close(self) -> None:
        return


class _CloseStubSource(_StubSource):
    def __init__(self, *, name: str, should_fail_close: bool = False) -> None:
        super().__init__(name=name, papers=[])
        self.should_fail_close = should_fail_close
        self.closed = False

    def close(self) -> None:
        self.closed = True
        if self.should_fail_close:
            raise RuntimeError(f"{self.name} close failed")


class TestPaperSearchServiceMultiSource(unittest.TestCase):
    def test_dedup_by_doi_prefers_source_priority(self) -> None:
        query = SearchQuery(name="q", fields={})
        arxiv_paper = Paper(
            source="arxiv",
            id="a1",
            title="Same Paper",
            authors=(),
            abstract="",
            published=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated=datetime(2025, 1, 2, tzinfo=timezone.utc),
            doi="https://doi.org/10.1000/abc",
        )
        crossref_paper = Paper(
            source="crossref",
            id="c1",
            title="Same Paper",
            authors=(),
            abstract="",
            published=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated=datetime(2025, 1, 3, tzinfo=timezone.utc),
            doi="doi:10.1000/abc",
        )

        service = PaperSearchService(
            sources=(
                _StubSource(name="arxiv", papers=[arxiv_paper]),
                _StubSource(name="crossref", papers=[crossref_paper]),
            )
        )

        result = service.search(query, max_results=10)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].source, "arxiv")
        self.assertEqual(result[0].id, "a1")

    def test_title_fallback_dedup_requires_same_year(self) -> None:
        query = SearchQuery(name="q", fields={})
        title = "A Very Long Cross Source Duplicate Title For Testing"
        left = Paper(
            source="arxiv",
            id="a1",
            title=title,
            authors=(),
            abstract="",
            published=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated=None,
            doi=None,
        )
        right = Paper(
            source="crossref",
            id="c1",
            title="  a very long cross-source duplicate title for testing  ",
            authors=(),
            abstract="",
            published=datetime(2025, 2, 1, tzinfo=timezone.utc),
            updated=None,
            doi=None,
        )
        diff_year = Paper(
            source="crossref",
            id="c2",
            title=title,
            authors=(),
            abstract="",
            published=datetime(2024, 2, 1, tzinfo=timezone.utc),
            updated=None,
            doi=None,
        )

        service = PaperSearchService(
            sources=(
                _StubSource(name="arxiv", papers=[left]),
                _StubSource(name="crossref", papers=[right, diff_year]),
            )
        )

        result = service.search(query, max_results=10)

        self.assertEqual(len(result), 2)
        ids = {paper.id for paper in result}
        self.assertIn("a1", ids)
        self.assertIn("c2", ids)

    def test_single_source_failure_is_isolated(self) -> None:
        query = SearchQuery(name="q", fields={})
        paper = Paper(
            source="arxiv",
            id="a1",
            title="Paper",
            authors=(),
            abstract="",
            published=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated=None,
            doi=None,
        )

        service = PaperSearchService(
            sources=(
                _StubSource(name="arxiv", papers=[paper]),
                _StubSource(name="crossref", should_fail=True),
            )
        )

        result = service.search(query, max_results=10)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "a1")

    def test_all_sources_failure_raises(self) -> None:
        query = SearchQuery(name="q", fields={})
        service = PaperSearchService(
            sources=(
                _StubSource(name="arxiv", should_fail=True),
                _StubSource(name="crossref", should_fail=True),
            )
        )

        with self.assertRaisesRegex(RuntimeError, "All search sources failed"):
            service.search(query, max_results=10)

    def test_close_isolates_source_errors(self) -> None:
        healthy = _CloseStubSource(name="arxiv")
        failing = _CloseStubSource(name="crossref", should_fail_close=True)
        service = PaperSearchService(sources=(failing, healthy))

        service.close()

        self.assertTrue(failing.closed)
        self.assertTrue(healthy.closed)


if __name__ == "__main__":
    unittest.main()
