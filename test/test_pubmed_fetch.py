"""Unit tests for collect_pubmed_papers paged fetch strategy."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from PaperTracker.core.models import Paper, PaperLinks
from PaperTracker.sources.pubmed.fetch import TIMEOUT_SECONDS, collect_pubmed_papers


def _paper(pmid: str, year: int = 2024, month: int = 1, day: int = 1) -> Paper:
    return Paper(
        source="pubmed",
        id=pmid,
        title=f"Paper {pmid}",
        authors=(),
        abstract="",
        published=datetime(year, month, day, tzinfo=timezone.utc),
        updated=None,
        doi=f"10.1234/{pmid}",
        extra={"work_type": "article"},
    )


def _make_policy(
    max_results: int = 10,
    max_fetch_items: int = -1,
    fetch_batch_size: int = 5,
    pull_every: int = 7,
    fill_enabled: bool = False,
    max_lookback_days: int = 30,
) -> MagicMock:
    policy = MagicMock()
    policy.max_results = max_results
    policy.max_fetch_items = max_fetch_items
    policy.fetch_batch_size = fetch_batch_size
    policy.pull_every = pull_every
    policy.fill_enabled = fill_enabled
    policy.max_lookback_days = max_lookback_days
    return policy


class TestCollectPubmedPapers(unittest.TestCase):
    def test_normal_pagination_three_pages(self) -> None:
        # 3 pages: each returns 3 papers; last page returns upstream_count=0 → stop
        call_count = 0

        def fetch_page(term, mindate, maxdate, retstart, page_size):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                papers = [_paper(f"{retstart + i}") for i in range(3)]
                return papers, 3
            return [], 0

        policy = _make_policy(max_results=100, fetch_batch_size=3)
        with patch("PaperTracker.sources.pubmed.fetch.time_module.sleep"):
            result = collect_pubmed_papers("cancer", None, None, policy, fetch_page, None)

        self.assertEqual(call_count, 4)  # 3 pages + 1 empty → stop
        self.assertEqual(len(result), 9)

    def test_fetched_items_advances_by_upstream_count(self) -> None:
        """Parser dropping records should not trigger premature short-page stop."""
        # Page 1: upstream_count=5 but parser only returns 2 papers (3 dropped — no DOI)
        # Page 2: upstream_count=0 → stop
        call_sequence = [(2, 5), (0, 0)]  # (papers_returned, upstream_count)
        call_index = [0]

        def fetch_page(term, mindate, maxdate, retstart, page_size):
            n_papers, upstream = call_sequence[call_index[0]]
            call_index[0] += 1
            papers = [_paper(f"p{retstart + i}") for i in range(n_papers)]
            return papers, upstream

        policy = _make_policy(max_results=100, fetch_batch_size=5)
        with patch("PaperTracker.sources.pubmed.fetch.time_module.sleep"):
            result = collect_pubmed_papers("cancer", None, None, policy, fetch_page, None)

        # Page 1: upstream_count=5 (== page_size=5) → NOT a short page → continues
        # Page 2: upstream_count=0 → stop
        self.assertEqual(call_index[0], 2)
        self.assertEqual(len(result), 2)

    def test_max_fetch_items_stops_loop(self) -> None:
        def fetch_page(term, mindate, maxdate, retstart, page_size):
            papers = [_paper(f"{retstart + i}") for i in range(page_size)]
            return papers, page_size

        policy = _make_policy(max_results=100, max_fetch_items=10, fetch_batch_size=5)
        with patch("PaperTracker.sources.pubmed.fetch.time_module.sleep"):
            result = collect_pubmed_papers("cancer", None, None, policy, fetch_page, None)

        self.assertLessEqual(len(result), 10)

    def test_max_results_stops_loop(self) -> None:
        call_count = [0]

        def fetch_page(term, mindate, maxdate, retstart, page_size):
            call_count[0] += 1
            papers = [_paper(f"{retstart + i}") for i in range(page_size)]
            return papers, page_size

        policy = _make_policy(max_results=5, fetch_batch_size=5)
        with patch("PaperTracker.sources.pubmed.fetch.time_module.sleep"):
            result = collect_pubmed_papers("cancer", None, None, policy, fetch_page, None)

        self.assertLessEqual(len(result), 5)

    def test_dedup_store_filter_called(self) -> None:
        def fetch_page(term, mindate, maxdate, retstart, page_size):
            if retstart == 0:
                papers = [_paper("1"), _paper("2")]
                return papers, 2
            return [], 0

        dedup_store = MagicMock()
        dedup_store.filter_new_in_source.side_effect = lambda source, papers: papers[:1]

        policy = _make_policy(max_results=10, fetch_batch_size=5)
        with patch("PaperTracker.sources.pubmed.fetch.time_module.sleep"):
            result = collect_pubmed_papers("cancer", None, None, policy, fetch_page, dedup_store)

        dedup_store.filter_new_in_source.assert_called_once_with("pubmed", unittest.mock.ANY)
        self.assertEqual(len(result), 1)

    def test_short_page_stops_loop(self) -> None:
        """upstream_count < page_size → short page → break immediately."""
        call_count = [0]

        def fetch_page(term, mindate, maxdate, retstart, page_size):
            call_count[0] += 1
            # Return fewer than page_size upstream items
            return [_paper("1"), _paper("2")], 2  # page_size=5

        policy = _make_policy(max_results=100, fetch_batch_size=5)
        with patch("PaperTracker.sources.pubmed.fetch.time_module.sleep"):
            result = collect_pubmed_papers("cancer", None, None, policy, fetch_page, None)

        # Only one call because upstream_count(2) < page_size(5)
        self.assertEqual(call_count[0], 1)
        self.assertEqual(len(result), 2)

    def test_page_size_zero_breaks_immediately(self) -> None:
        """When max_fetch_items is exhausted, page_size=0 → break without calling fetch."""
        call_count = [0]

        def fetch_page(term, mindate, maxdate, retstart, page_size):
            call_count[0] += 1
            return [], 0

        # max_fetch_items=0 would be invalid config; simulate exhausted state by
        # setting max_fetch_items to a small number already satisfied
        policy = _make_policy(max_results=5, max_fetch_items=5, fetch_batch_size=5)

        # After fetching 5 items, max_fetch_items is reached. Next page_size=0 → break.
        def fetch_page2(term, mindate, maxdate, retstart, page_size):
            call_count[0] += 1
            papers = [_paper(f"{retstart + i}") for i in range(page_size)]
            return papers, page_size

        with patch("PaperTracker.sources.pubmed.fetch.time_module.sleep"):
            result = collect_pubmed_papers("cancer", None, None, policy, fetch_page2, None)

        # One page fetched (retstart=0, page_size=5), then fetched_items=5 >= max_fetch_items=5 → stop
        self.assertEqual(call_count[0], 1)
        self.assertEqual(len(result), 5)

    def test_timeout_protection(self) -> None:
        call_count = [0]
        # time() call sequence:
        #   1. start_time = time()           → 0.0
        #   2. first iteration: elapsed check → 0.0  (ok, proceed to fetch)
        #   3. second iteration: elapsed check → TIMEOUT+1 (stop)
        fake_times = [0.0, 0.0, TIMEOUT_SECONDS + 1.0] + [TIMEOUT_SECONDS + 1.0] * 5

        def fetch_page(term, mindate, maxdate, retstart, page_size):
            call_count[0] += 1
            return [_paper(f"{retstart}")], 5

        policy = _make_policy(max_results=100, fetch_batch_size=5)
        with patch("PaperTracker.sources.pubmed.fetch.time_module.sleep"), \
             patch("PaperTracker.sources.pubmed.fetch.time", side_effect=fake_times):
            collect_pubmed_papers("cancer", None, None, policy, fetch_page, None)

        # First call proceeds; second iteration hits timeout → break before second call
        self.assertEqual(call_count[0], 1)

    def test_final_sort_descending_by_published(self) -> None:
        def fetch_page(term, mindate, maxdate, retstart, page_size):
            if retstart == 0:
                papers = [
                    _paper("older", 2023, 1, 1),
                    _paper("newer", 2024, 6, 1),
                    _paper("oldest", 2022, 1, 1),
                ]
                return papers, 3
            return [], 0

        policy = _make_policy(max_results=10, fetch_batch_size=5)
        with patch("PaperTracker.sources.pubmed.fetch.time_module.sleep"):
            result = collect_pubmed_papers("cancer", None, None, policy, fetch_page, None)

        self.assertEqual(result[0].id, "newer")
        self.assertEqual(result[1].id, "older")
        self.assertEqual(result[2].id, "oldest")


if __name__ == "__main__":
    unittest.main()
