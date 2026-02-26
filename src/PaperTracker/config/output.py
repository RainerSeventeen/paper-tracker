"""Output domain configuration for multi-format rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from PaperTracker.config.common import (
    expect_str,
    expect_str_list,
    get_optional_value,
    get_required_value,
    get_section,
)

_ALLOWED_FORMATS = {"console", "json", "markdown", "html"}


@dataclass(frozen=True, slots=True)
class OutputConfig:
    """Output configuration."""

    base_dir: str
    formats: tuple[str, ...]
    markdown_template_dir: str
    markdown_document_template: str
    markdown_paper_template: str
    markdown_paper_separator: str
    html_template_dir: str
    html_document_template: str
    html_paper_template: str


def load_output(raw: Mapping[str, Any]) -> OutputConfig:
    """Load output domain config from raw mapping.

    Args:
        raw: Root configuration mapping.

    Returns:
        Parsed output configuration.

    Raises:
        TypeError: If config types are invalid.
        ValueError: If required keys are missing.
    """
    section = get_section(raw, "output", required=True)
    formats = tuple(
        item.lower() for item in expect_str_list(get_required_value(section, "formats", "output.formats"), "output.formats")
    )

    markdown = get_section(section, "markdown", required=False) if "markdown" in formats else {}
    html = get_section(section, "html", required=False) if "html" in formats else {}

    return OutputConfig(
        base_dir=expect_str(get_required_value(section, "base_dir", "output.base_dir"), "output.base_dir"),
        formats=formats,
        markdown_template_dir=expect_str(
            get_optional_value(markdown, "template_dir", "template/markdown"),
            "output.markdown.template_dir",
        ),
        markdown_document_template=expect_str(
            get_optional_value(markdown, "document_template", "document.md"),
            "output.markdown.document_template",
        ),
        markdown_paper_template=expect_str(
            get_optional_value(markdown, "paper_template", "paper.md"),
            "output.markdown.paper_template",
        ),
        markdown_paper_separator=expect_str(
            get_optional_value(markdown, "paper_separator", "\n\n---\n\n"),
            "output.markdown.paper_separator",
        ),
        html_template_dir=expect_str(
            get_optional_value(html, "template_dir", "template/html/scholar"),
            "output.html.template_dir",
        ),
        html_document_template=expect_str(
            get_optional_value(html, "document_template", "document.html"),
            "output.html.document_template",
        ),
        html_paper_template=expect_str(
            get_optional_value(html, "paper_template", "paper.html"),
            "output.html.paper_template",
        ),
    )


def check_output(config: OutputConfig) -> None:
    """Validate output domain constraints.

    Args:
        config: Parsed output configuration.

    Raises:
        ValueError: If values violate output constraints.
    """
    if not config.base_dir.strip():
        raise ValueError("output.base_dir must not be empty")
    if not config.formats:
        raise ValueError("output.formats must include at least one format")

    unknown = set(config.formats) - _ALLOWED_FORMATS
    if unknown:
        raise ValueError(f"output.formats has unknown formats: {sorted(unknown)}")

    if "markdown" in config.formats:
        _check_non_empty(config.markdown_template_dir, "output.markdown.template_dir")
        _check_non_empty(config.markdown_document_template, "output.markdown.document_template")
        _check_non_empty(config.markdown_paper_template, "output.markdown.paper_template")

    if "html" in config.formats:
        _check_non_empty(config.html_template_dir, "output.html.template_dir")
        _check_non_empty(config.html_document_template, "output.html.document_template")
        _check_non_empty(config.html_paper_template, "output.html.paper_template")


def _check_non_empty(value: str, config_key: str) -> None:
    """Validate non-empty string values.

    Args:
        value: Config value.
        config_key: Full key path used in error messages.

    Raises:
        ValueError: If string is empty or whitespace-only.
    """
    if not value.strip():
        raise ValueError(f"{config_key} must not be empty")
