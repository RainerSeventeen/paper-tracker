"""Command runner for coordinating CLI execution.

Manages component lifecycle, resource cleanup, logging configuration,
and error handling for command execution.
"""

from __future__ import annotations

import click

from PaperTracker.cli.commands import SearchCommand
from PaperTracker.config import AppConfig
from PaperTracker.llm import create_llm_service
from PaperTracker.renderers import create_output_writer
from PaperTracker.services import create_search_service
from PaperTracker.storage import create_llm_store, create_storage
from PaperTracker.utils.log import configure_logging, log


class CommandRunner:
    """Orchestrates command execution with proper resource management.

    Handles logging configuration, component creation, database context
    management, and error handling for CLI commands.
    """

    def __init__(self, config: AppConfig) -> None:
        """Initialize command runner.

        Args:
            config: Application configuration.
        """
        self.config = config

    def run_search(self, action: str) -> None:
        """Execute search command with full resource management.

        Configures logging, creates components, executes search,
        and ensures proper cleanup of database connections.

        Args:
            action: The CLI command name (e.g., 'search').

        Raises:
            click.Abort: When the search fails.
        """
        configure_logging(
            level=self.config.runtime.level,
            action=action,
            log_to_file=self.config.runtime.to_file,
            log_dir=self.config.runtime.dir,
        )
        try:
            # Create storage components
            db_manager, dedup_store, content_store = create_storage(self.config)

            # Create service and output writer (pass dedup_store for arXiv multi-round fetching)
            search_service = create_search_service(self.config, dedup_store=dedup_store)
            output_writer = create_output_writer(self.config)

            # Create LLM service if enabled
            llm_service = create_llm_service(self.config)

            # Create LLM store if enabled
            llm_store = None
            if db_manager and llm_service:
                llm_store = create_llm_store(db_manager, self.config)

            # Create command with dependencies injected
            command = SearchCommand(
                config=self.config,
                search_service=search_service,
                dedup_store=dedup_store,
                content_store=content_store,
                output_writer=output_writer,
                llm_service=llm_service,
                llm_store=llm_store,
            )

            # Execute with proper resource cleanup
            if db_manager:
                with db_manager:
                    command.execute()
                    output_writer.finalize(action)
            else:
                command.execute()
                output_writer.finalize(action)

        except Exception as e:  # noqa: BLE001 - cli boundary
            log.error("Search failed: %s", e)
            raise click.Abort from e
