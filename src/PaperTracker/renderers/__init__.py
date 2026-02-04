"""Output renderers for command results.

Provides abstraction and implementations for writing search results to
various output formats (console, JSON).

The module exports the OutputWriter protocol for creating new output formats,
and a factory function to instantiate writers based on configuration.
"""

from __future__ import annotations

from PaperTracker.config import AppConfig
from PaperTracker.renderers.base import MultiOutputWriter, OutputWriter
from PaperTracker.renderers.console import ConsoleOutputWriter, render_text
from PaperTracker.renderers.json import JsonFileWriter, render_json
from PaperTracker.renderers.markdown import MarkdownFileWriter


def create_output_writer(config: AppConfig) -> OutputWriter:
    """Create output writer based on config.

    Args:
        config: Application configuration.

    Returns:
        Appropriate OutputWriter instance for configured format.
    """
    writers: list[OutputWriter] = []
    if "console" in config.output_formats:
        writers.append(ConsoleOutputWriter())
    if "json" in config.output_formats:
        writers.append(JsonFileWriter(config.output_base_dir))
    if "markdown" in config.output_formats:
        writers.append(MarkdownFileWriter(config.output_base_dir, config.output_markdown))

    if not writers:
        raise ValueError("No output writers configured")
    return MultiOutputWriter(writers)


__all__ = [
    "OutputWriter",
    "ConsoleOutputWriter",
    "JsonFileWriter",
    "MarkdownFileWriter",
    "MultiOutputWriter",
    "render_json",
    "render_text",
    "create_output_writer",
]
