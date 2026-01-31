"""Storage layer for PaperTracker.

Provides database management, deduplication, and content storage
for paper tracking.
"""

from __future__ import annotations

from pathlib import Path

from PaperTracker.storage.content import PaperContentStore
from PaperTracker.storage.db import DatabaseManager
from PaperTracker.storage.deduplicate import SqliteDeduplicateStore
from PaperTracker.utils.log import log


def create_storage(
    config: AppConfig,  # type: ignore[name-defined]
) -> tuple[DatabaseManager | None, SqliteDeduplicateStore | None, PaperContentStore | None]:
    """Create database manager and storage components.

    Creates storage components based on configuration. Returns None for
    components that are not enabled.

    Args:
        config: Application configuration containing storage settings.

    Returns:
        Tuple of (db_manager, dedup_store, content_store).
        Components may be None if state management is disabled.
    """
    from PaperTracker.config import AppConfig

    db_manager = None
    dedup_store = None
    content_store = None

    if config.state_enabled:
        db_path = Path(config.state_db_path)
        db_manager = DatabaseManager(db_path)
        dedup_store = SqliteDeduplicateStore(db_manager)
        log.info("State management enabled: %s", db_path)

        if config.content_storage_enabled:
            content_store = PaperContentStore(db_manager)
            log.info("Content storage enabled: %s", db_path)

    return db_manager, dedup_store, content_store


__all__ = [
    "DatabaseManager",
    "SqliteDeduplicateStore",
    "PaperContentStore",
    "create_storage",
]
