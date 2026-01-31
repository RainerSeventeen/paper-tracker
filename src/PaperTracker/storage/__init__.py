"""Storage layer for PaperTracker."""

from __future__ import annotations

from PaperTracker.storage.deduplicate import SqliteDeduplicateStore

__all__ = ["SqliteStateStore"]
