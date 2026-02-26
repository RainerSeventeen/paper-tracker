"""Storage layer for PaperTracker.

Provides database management, deduplication, and content storage
for paper tracking.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PaperTracker.storage.content import PaperContentStore
from PaperTracker.storage.db import DatabaseManager
from PaperTracker.storage.deduplicate import ReadOnlyDeduplicateStore, SqliteDeduplicateStore
from PaperTracker.storage.llm import LLMGeneratedStore
from PaperTracker.storage.migration import run_migrations
from PaperTracker.utils.log import log

if TYPE_CHECKING:
    from PaperTracker.config import AppConfig


def create_storage(
    config: AppConfig,
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
    db_manager = None
    dedup_store = None
    content_store = None

    if config.storage.enabled:
        db_path = Path(config.storage.db_path)
        db_manager = DatabaseManager(db_path)
        dedup_store = SqliteDeduplicateStore(db_manager)
        log.info("State storage enabled: %s", db_path)

        if config.storage.content_storage_enabled:
            content_store = PaperContentStore(db_manager)
            log.info("Content storage enabled: %s", db_path)

    return db_manager, dedup_store, content_store


def create_llm_store(
    db_manager: DatabaseManager,
    config: AppConfig,
) -> LLMGeneratedStore | None:
    """Create LLM generated store from config.

    Args:
        db_manager: Database manager instance.
        config: Application config.

    Returns:
        LLM store if LLM and content storage are both enabled, None otherwise.
    """
    if not config.llm.enabled or not config.storage.content_storage_enabled:
        return None

    return LLMGeneratedStore(
        conn=db_manager.get_connection(),
        provider=config.llm.provider,
        model=config.llm.model,
    )


__all__ = [
    "DatabaseManager",
    "SqliteDeduplicateStore",
    "ReadOnlyDeduplicateStore",
    "PaperContentStore",
    "LLMGeneratedStore",
    "run_migrations",
    "create_storage",
    "create_llm_store",
]
