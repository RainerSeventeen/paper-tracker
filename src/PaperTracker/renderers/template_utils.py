"""Shared helpers and errors for template-based renderers."""

from __future__ import annotations

from pathlib import Path

from PaperTracker.core.query import SearchQuery


class TemplateNotFoundError(FileNotFoundError):
    """Raised when a template file cannot be found."""


class TemplateError(RuntimeError):
    """Raised when a template cannot be loaded."""


class OutputError(RuntimeError):
    """Raised when output cannot be written."""


def load_template(template_dir: str, filename: str) -> str:
    """Load a template file from the configured template directory.

    Args:
        template_dir: Base template directory from configuration.
        filename: Template file name relative to ``template_dir``.

    Returns:
        Template content decoded as UTF-8 text.

    Raises:
        TemplateError: If the resolved path escapes project root or file reading fails.
        TemplateNotFoundError: If the target template file does not exist.
    """
    root = Path.cwd().resolve()
    base_dir = Path(template_dir)
    if not base_dir.is_absolute():
        base_dir = root / base_dir
    template_path = (base_dir / filename).resolve()
    try:
        template_path.relative_to(root)
    except ValueError as exc:
        raise TemplateError(f"Template path must be inside project root: {template_path}") from exc

    if not template_path.exists():
        raise TemplateNotFoundError(f"Template file not found: {template_path}")

    try:
        return template_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TemplateError(f"Failed to read template: {template_path}") from exc


def query_label(query: SearchQuery) -> str:
    """Build a display label for a query in rendered outputs.

    Args:
        query: Search query object to label.

    Returns:
        The query name when available, otherwise ``"query"``.
    """
    if query.name:
        return query.name
    return "query"
