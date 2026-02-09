"""Standalone fetch test runner.

Loads settings from a config file, fetches papers from the real arXiv API,
optionally applies deduplication, and renders output with ConsoleOutputWriter.

Usage:
    python test/pipeline/test_fetch_standalone.py [--config CONFIG_PATH]

Args:
    --config: Config file path (default: config/default.yml)
"""

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

from PaperTracker.config import load_config
from PaperTracker.renderers.console import ConsoleOutputWriter
from PaperTracker.renderers.mapper import map_papers_to_views
from PaperTracker.sources.arxiv.client import ArxivApiClient
from PaperTracker.sources.arxiv.source import ArxivSource
from PaperTracker.storage.db import DatabaseManager
from PaperTracker.storage.deduplicate import ReadOnlyDeduplicateStore, SqliteDeduplicateStore

# ============================================================================
# Logging configuration
# ============================================================================

LOG_DIR = Path("log/test")
LOG_LEVEL = logging.DEBUG

# ============================================================================
# Global settings - adjust as needed
# ============================================================================

# Whether to enable deduplication
ENABLE_DEDUP = True

# Query index to run (None means all queries)
QUERY_INDEX = None


def setup_logging(level: str = "INFO"):
    """Configure logging output with file handler.

    Logs to both console and log/test directory with DEBUG level.
    """
    # Create log directory
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Generate log filename with timestamp
    log_filename = f"test_fetch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = LOG_DIR / log_filename

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(LOG_LEVEL)

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler - use configured level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler - always DEBUG
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(LOG_LEVEL)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    logger.info(f"Debug log saved to: {log_path}")
    logger.debug("Debug logging enabled")


def print_summary(results: list, query_name: str, use_dedup: bool, elapsed_time: float) -> None:
    """Print fetch summary.

    Args:
        results: Paper list.
        query_name: Query name.
        use_dedup: Whether deduplication was enabled.
        elapsed_time: Elapsed seconds.
    """
    print(f"\n{'=' * 80}")
    print(f"Fetch complete: {query_name}")
    print(f"{'=' * 80}")
    print(f"  Query name: {query_name}")
    print(f"  Deduplication: {'ON' if use_dedup else 'OFF'}")
    print(f"  Paper count: {len(results)}")
    print(f"  Elapsed: {elapsed_time:.2f}s")

    if results:
        # Time distribution summary
        now = datetime.now(timezone.utc)
        timestamps = [p.updated or p.published for p in results if (p.updated or p.published)]

        if timestamps:
            newest = max(timestamps)
            oldest = min(timestamps)
            newest_days = (now - newest).days
            oldest_days = (now - oldest).days

            print("\n[Time distribution]")
            print(f"  Newest paper: {newest_days} days ago ({newest.date()})")
            print(f"  Oldest paper: {oldest_days} days ago ({oldest.date()})")
            print(f"  Time span: {oldest_days - newest_days} days")


def main():
    """Main entry: load config, fetch papers, and print results."""
    parser = argparse.ArgumentParser(description="Standalone fetch test runner")
    parser.add_argument(
        "--config",
        type=str,
        default="config/default.yml",
        help="Config file path (default: config/default.yml)",
    )
    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        return

    print(f"\n{'=' * 80}")
    print("Standalone fetch test runner")
    print(f"{'=' * 80}")
    print(f"Config file: {config_path}")
    print(f"Deduplication: {'ON' if ENABLE_DEDUP else 'OFF'}")
    if QUERY_INDEX is not None:
        print(f"Query scope: only index {QUERY_INDEX}")
    else:
        print("Query scope: all queries")

    config = load_config(config_path)
    setup_logging(config.runtime.level)

    # Initialize dedup store (wrapped as read-only)
    dedup_store = None
    db_manager = None
    if ENABLE_DEDUP and config.storage.enabled:
        db_path = Path(config.storage.db_path)
        if db_path.exists():
            print(f"Database path: {db_path}")
            db_manager = DatabaseManager(db_path)
            db_manager.__enter__()
            real_store = SqliteDeduplicateStore(db_manager)
            # Use read-only wrapper: allow dedup logic without DB writes.
            dedup_store = ReadOnlyDeduplicateStore(real_store)
            print("OK: Using read-only dedup mode (no DB writes)")
        else:
            print(f"WARN: Database not found, dedup disabled: {db_path}")
    elif not ENABLE_DEDUP:
        print("WARN: Deduplication disabled in script (ENABLE_DEDUP=False)")

    # Create arXiv source (inject read-only dedup store)
    client = ArxivApiClient()
    source = ArxivSource(
        client=client,
        scope=config.search.scope,
        keep_version=config.storage.keep_arxiv_version,
        search_config=config.search,
        dedup_store=dedup_store,
    )

    # Determine query set to run
    queries_to_run = []
    if QUERY_INDEX is not None:
        if 0 <= QUERY_INDEX < len(config.search.queries):
            queries_to_run = [config.search.queries[QUERY_INDEX]]
            print(f"Running query: index {QUERY_INDEX} - {queries_to_run[0].name}")
        else:
            print(
                f"ERROR: Query index out of range: {QUERY_INDEX} (total: {len(config.search.queries)})"
            )
            return
    else:
        queries_to_run = config.search.queries
        print(f"Running all queries: {len(queries_to_run)} total")

    print("\n[Search config]")
    print(f"  max_results:       {config.search.max_results}")
    print(f"  pull_every:        {config.search.pull_every} days")
    print(f"  fill_enabled:      {config.search.fill_enabled}")
    print(f"  max_lookback_days: {config.search.max_lookback_days} days")
    print(f"  max_fetch_items:   {config.search.max_fetch_items}")
    print(f"  fetch_batch_size:  {config.search.fetch_batch_size}")

    # Create console writer
    console_writer = ConsoleOutputWriter()

    # Run queries
    all_results = []
    for i, query in enumerate(queries_to_run):
        print(f"\n{'=' * 80}")
        print(f"Running query #{i+1}/{len(queries_to_run)}: {query.name}")
        print(f"{'=' * 80}")

        import time
        start_time = time.time()

        # Execute fetch
        results = source.search(
            query=query,
            max_results=config.search.max_results,
        )

        elapsed_time = time.time() - start_time

        # Print summary (dedup already handled in fetch strategy)
        print_summary(
            results=results,
            query_name=query.name or f"Query #{i+1}",
            use_dedup=dedup_store is not None,
            elapsed_time=elapsed_time,
        )

        # Render paper details with ConsoleOutputWriter
        if results:
            print("\n[Paper details]")
            # Convert to PaperView
            paper_views = map_papers_to_views(results)
            # Render via ConsoleOutputWriter
            console_writer.write_query_result(paper_views, query, config.search.scope)

            # Mark seen only after output is rendered.
            if dedup_store:
                dedup_store.mark_seen(results)

            all_results.extend(results)
        else:
            print("\nWARN: No papers matched the query")

    # Summary
    print(f"\n{'=' * 80}")
    print("Fetch summary")
    print(f"{'=' * 80}")
    print(f"  Queries run: {len(queries_to_run)}")
    print(f"  Papers total: {len(all_results)}")
    print(f"  Deduplication: {'ON' if dedup_store else 'OFF'}")

    if dedup_store and config.storage.enabled:
        print("\nOK: Database unchanged (read-only mode did not call mark_seen)")

    # Close database connection
    if db_manager:
        db_manager.__exit__(None, None, None)


if __name__ == "__main__":
    main()
