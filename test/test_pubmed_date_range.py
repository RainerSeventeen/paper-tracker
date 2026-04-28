"""Unit tests for PubMed date range resolution."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from PaperTracker.sources.pubmed.source import _resolve_date_range


def _policy(
    fill_enabled: bool,
    max_lookback_days: int,
    pull_every: int = 7,
) -> MagicMock:
    policy = MagicMock()
    policy.fill_enabled = fill_enabled
    policy.max_lookback_days = max_lookback_days
    policy.pull_every = pull_every
    return policy


class TestResolveDateRange(unittest.TestCase):
    _NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    def test_fill_disabled_returns_pull_every_window(self) -> None:
        policy = _policy(fill_enabled=False, max_lookback_days=30, pull_every=7)
        mindate, maxdate = _resolve_date_range(policy, self._NOW)
        self.assertEqual(mindate, "2024/06/08")
        self.assertEqual(maxdate, "2024/06/15")

    def test_fill_enabled_unlimited_returns_none_none(self) -> None:
        policy = _policy(fill_enabled=True, max_lookback_days=-1)
        mindate, maxdate = _resolve_date_range(policy, self._NOW)
        self.assertIsNone(mindate)
        self.assertIsNone(maxdate)

    def test_fill_enabled_with_max_lookback(self) -> None:
        policy = _policy(fill_enabled=True, max_lookback_days=30)
        mindate, maxdate = _resolve_date_range(policy, self._NOW)
        self.assertEqual(mindate, "2024/05/16")
        self.assertEqual(maxdate, "2024/06/15")

    def test_date_format_is_yyyy_mm_dd_with_slashes(self) -> None:
        policy = _policy(fill_enabled=False, max_lookback_days=30, pull_every=7)
        mindate, maxdate = _resolve_date_range(policy, self._NOW)
        assert mindate is not None and maxdate is not None
        # Verify format: YYYY/MM/DD
        parts_min = mindate.split("/")
        parts_max = maxdate.split("/")
        self.assertEqual(len(parts_min), 3)
        self.assertEqual(len(parts_max), 3)
        self.assertEqual(len(parts_min[0]), 4)  # year
        self.assertEqual(len(parts_min[1]), 2)  # month
        self.assertEqual(len(parts_min[2]), 2)  # day

    def test_fill_enabled_max_lookback_1_day(self) -> None:
        policy = _policy(fill_enabled=True, max_lookback_days=1)
        mindate, maxdate = _resolve_date_range(policy, self._NOW)
        self.assertEqual(mindate, "2024/06/14")
        self.assertEqual(maxdate, "2024/06/15")


if __name__ == "__main__":
    unittest.main()
