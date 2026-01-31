"""Output renderers for command results.

Provides abstraction and implementations for writing search results to
various output formats (console, JSON).

The module exports the OutputWriter protocol for creating new output formats,
and a factory function to instantiate writers based on configuration.
"""

from __future__ import annotations

from PaperTracker.config import AppConfig
from PaperTracker.renderers.base import OutputWriter
from PaperTracker.renderers.console import ConsoleOutputWriter, render_text
from PaperTracker.renderers.json import JsonFileWriter, render_json


def create_output_writer(config: AppConfig) -> OutputWriter:
    """Create output writer based on config.

    Args:
        config: Application configuration.

    Returns:
        Appropriate OutputWriter instance for configured format.
    """
    if config.output_format == "json":
        return JsonFileWriter(config.output_dir)
    return ConsoleOutputWriter()


__all__ = [
    "OutputWriter",
    "ConsoleOutputWriter",
    "JsonFileWriter",
    "render_json",
    "render_text",
    "create_output_writer",
]
