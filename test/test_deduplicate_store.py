"""Tests for deduplication store behavior."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from PaperTracker.core.models import Paper
from PaperTracker.storage.db import DatabaseManager
from PaperTracker.storage.deduplicate import ReadOnlyDeduplicateStore, SqliteDeduplicateStore


class TestDeduplicateStore(unittest.TestCase):
    def test_filter_new_filters_cross_source_by_doi(self) -> None:
        tmp_db = Path(tempfile.mkdtemp()) / "papers.db"
        manager = DatabaseManager(tmp_db)
        try:
            store = SqliteDeduplicateStore(manager)
            stored = Paper(
                source="arxiv",
                id="2501.00001",
                title="Seen",
                authors=(),
                abstract="",
                published=datetime.now(timezone.utc),
                updated=None,
                doi="https://doi.org/10.5555/seen",
            )
            candidate = Paper(
                source="crossref",
                id="10.5555/seen",
                title="Seen from Crossref",
                authors=(),
                abstract="",
                published=datetime.now(timezone.utc),
                updated=None,
                doi="doi:10.5555/seen",
            )

            store.mark_seen([stored])
            filtered = store.filter_new([candidate])

            self.assertEqual(filtered, [])
        finally:
            manager.close()

    def test_filter_new_filters_by_source_and_source_id(self) -> None:
        tmp_db = Path(tempfile.mkdtemp()) / "papers.db"
        manager = DatabaseManager(tmp_db)
        try:
            store = SqliteDeduplicateStore(manager)
            stored = Paper(
                source="crossref",
                id="item-1",
                title="Seen",
                authors=(),
                abstract="",
                published=datetime.now(timezone.utc),
                updated=None,
                doi=None,
            )

            store.mark_seen([stored])
            filtered = store.filter_new([stored])

            self.assertEqual(filtered, [])
        finally:
            manager.close()

    def test_read_only_store_session_dedup_by_doi(self) -> None:
        tmp_db = Path(tempfile.mkdtemp()) / "papers.db"
        manager = DatabaseManager(tmp_db)
        try:
            real_store = SqliteDeduplicateStore(manager)
            store = ReadOnlyDeduplicateStore(real_store)

            first = Paper(
                source="arxiv",
                id="a1",
                title="First",
                authors=(),
                abstract="",
                published=datetime.now(timezone.utc),
                updated=None,
                doi="10.1234/xyz",
            )
            second = Paper(
                source="crossref",
                id="c1",
                title="Second",
                authors=(),
                abstract="",
                published=datetime.now(timezone.utc),
                updated=None,
                doi="https://doi.org/10.1234/xyz",
            )

            store.mark_seen([first])
            filtered = store.filter_new([second])

            self.assertEqual(filtered, [])
        finally:
            manager.close()


if __name__ == "__main__":
    unittest.main()
