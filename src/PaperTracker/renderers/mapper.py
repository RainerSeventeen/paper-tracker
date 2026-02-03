"""Mapper for converting Paper domain models to PaperView display models.

Provides pure functions to extract and format data from Paper objects
(including LLM-enriched data in Paper.extra) into PaperView objects
suitable for output rendering.
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from PaperTracker.core.models import Paper
from PaperTracker.renderers.view_models import PaperView


def format_datetime(dt: datetime | None) -> str | None:
    """Format datetime to YYYY-MM-DD string for display.

    Args:
        dt: Datetime object or None.

    Returns:
        Formatted date string, or None if input is None.
    """
    return dt.strftime("%Y-%m-%d") if dt else None


def map_paper_to_view(paper: Paper) -> PaperView:
    """Map Paper domain model to PaperView display model.

    Extracts base fields from Paper and LLM-enriched data from Paper.extra.
    Formats temporal fields as strings for display consistency.

    Args:
        paper: Source paper object.

    Returns:
        PaperView with fields populated from paper and paper.extra.
    """
    # Extract LLM translation
    translation_data = paper.extra.get("translation", {})
    abstract_translation = translation_data.get("summary_translated")

    # Extract LLM summary
    summary_data = paper.extra.get("summary", {})
    tldr = summary_data.get("tldr")
    motivation = summary_data.get("motivation")
    method = summary_data.get("method")
    result = summary_data.get("result")
    conclusion = summary_data.get("conclusion")

    return PaperView(
        source=paper.source,
        id=paper.id,
        title=paper.title,
        authors=paper.authors,
        abstract=paper.abstract,
        published=format_datetime(paper.published),
        updated=format_datetime(paper.updated),
        primary_category=paper.primary_category,
        categories=paper.categories,
        abstract_url=paper.links.abstract,
        pdf_url=paper.links.pdf,
        doi=paper.doi,
        abstract_translation=abstract_translation,
        tldr=tldr,
        motivation=motivation,
        method=method,
        result=result,
        conclusion=conclusion,
    )


def map_papers_to_views(papers: Sequence[Paper]) -> list[PaperView]:
    """Batch map papers to views.

    Args:
        papers: List of paper objects.

    Returns:
        List of corresponding PaperView objects.
    """
    return [map_paper_to_view(p) for p in papers]
