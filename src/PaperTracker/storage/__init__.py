"""Storage layer for PaperTracker.

Provides database management, deduplication, and content storage
for paper tracking.
"""

from __future__ import annotations

from pathlib import Path

from PaperTracker.storage.content import PaperContentStore
from PaperTracker.storage.db import DatabaseManager
from PaperTracker.storage.deduplicate import SqliteDeduplicateStore
from PaperTracker.storage.llm import LLMGeneratedStore
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


def create_llm_store(
    db_manager: DatabaseManager,
    config: AppConfig,  # type: ignore[name-defined]
) -> LLMGeneratedStore | None:
    """Create LLM generated store from config.

    Args:
        db_manager: Database manager instance.
        config: Application config.

    Returns:
        LLM store if LLM is enabled, None otherwise.
    """
    from PaperTracker.config import AppConfig

    if not config.llm.enabled:
        return None

    return LLMGeneratedStore(
        conn=db_manager.conn,
        provider=config.llm.provider,
        model=config.llm.model,
    )


__all__ = [
    "DatabaseManager",
    "SqliteDeduplicateStore",
    "PaperContentStore",
    "LLMGeneratedStore",
    "create_storage",
    "create_llm_store",
]
