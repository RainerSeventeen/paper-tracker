"""CLI package for PaperTracker command orchestration.

This package contains the modular CLI components for the search command,
factored into separate modules for better maintainability and testability.
"""

from __future__ import annotations

__all__ = ["CommandRunner", "main"]

from PaperTracker.cli.runner import CommandRunner
from PaperTracker.cli.ui import cli


def main() -> None:
    """Run PaperTracker CLI.

    Entry point referenced by console script in pyproject.toml.
    """
    cli()
