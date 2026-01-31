"""Factory functions for CLI component creation.

Centralizes component instantiation to reduce coupling between CLI and
implementations. Enables easy substitution for testing and extensions.
"""

from __future__ import annotations

from pathlib import Path

from PaperTracker.config import AppConfig
from PaperTracker.services.search import PaperSearchService
from PaperTracker.sources.arxiv.client import ArxivApiClient
from PaperTracker.sources.arxiv.source import ArxivSource
from PaperTracker.storage.content import PaperContentStore
from PaperTracker.storage.db import DatabaseManager
from PaperTracker.storage.deduplicate import SqliteDeduplicateStore
from PaperTracker.utils.log import log


class ServiceFactory:
    """Factory for creating search services."""

    @staticmethod
    def create_arxiv_service(config: AppConfig) -> PaperSearchService:
        """Create search service with ArxivSource.

        Args:
            config: Application configuration.

        Returns:
            Configured PaperSearchService instance.
        """
        return PaperSearchService(
            source=ArxivSource(
                client=ArxivApiClient(),
                scope=config.scope,
                keep_version=config.arxiv_keep_version,
            )
        )


class StorageFactory:
    """Factory for creating storage components."""

    @staticmethod
    def create_storage(
        config: AppConfig,
    ) -> tuple[DatabaseManager | None, SqliteDeduplicateStore | None, PaperContentStore | None]:
        """Create database manager and storage components.

        Args:
            config: Application configuration.

        Returns:
            Tuple of (db_manager, dedup_store, content_store).
            Components may be None if state management is disabled.
        """
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


