"""Regression tests for SearchCommand persistence ordering."""

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from PaperTracker.cli.commands import SearchCommand
from PaperTracker.core.models import Paper, PaperLinks
from PaperTracker.core.query import SearchQuery
from PaperTracker.storage.content import PaperContentStore
from PaperTracker.storage.db import DatabaseManager
from PaperTracker.storage.deduplicate import SqliteDeduplicateStore


class _StubSearchService:
    def __init__(self, papers: list[Paper]) -> None:
        self._papers = papers

    def search(self, query: SearchQuery, *, max_results: int = 20) -> list[Paper]:
        del query, max_results
        return self._papers


class _StubOutputWriter:
    def write_query_result(self, paper_views, query, scope) -> None:
        del paper_views, query, scope


class TestSearchCommandPersistenceOrder(unittest.TestCase):
    def test_mark_seen_before_content_save(self) -> None:
        tmp_db = Path(tempfile.mkdtemp()) / "papers.db"
        manager = DatabaseManager(tmp_db)
        try:
            paper = Paper(
                source="arxiv",
                id="2501.00001",
                title="Test Paper",
                authors=("Alice",),
                abstract="Test abstract",
                published=datetime.now(timezone.utc),
                updated=datetime.now(timezone.utc),
                links=PaperLinks(abstract="https://arxiv.org/abs/2501.00001"),
            )

            query = SearchQuery(name="test", fields={})
            config = SimpleNamespace(
                search=SimpleNamespace(
                    queries=[query],
                    max_results=5,
                    scope=None,
                )
            )

            command = SearchCommand(
                config=config,
                search_service=_StubSearchService([paper]),
                dedup_store=SqliteDeduplicateStore(manager),
                content_store=PaperContentStore(manager),
                llm_service=None,
                llm_store=None,
                output_writer=_StubOutputWriter(),
            )

            command.execute()

            conn = manager.get_connection()
            seen_count = conn.execute("SELECT COUNT(*) FROM seen_papers").fetchone()[0]
            content_count = conn.execute("SELECT COUNT(*) FROM paper_content").fetchone()[0]

            self.assertEqual(seen_count, 1)
            self.assertEqual(content_count, 1)
        finally:
            manager.close()


if __name__ == "__main__":
    unittest.main()
