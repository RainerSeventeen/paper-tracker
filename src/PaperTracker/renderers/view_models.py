"""View models for output rendering.

Provides display-oriented data structures that separate presentation
concerns from domain models (Paper). Used by OutputWriter implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class PaperView:
    """Paper view model for output rendering.

    Separates display concerns from domain model (Paper).
    All fields are optional-aware to handle missing data gracefully.

    Attributes:
        source: Source identifier (e.g., "arxiv").
        id: Source-specific unique identifier.
        title: Paper title.
        authors: Author names.
        abstract: Abstract text.
        published: Publication date as YYYY-MM-DD string or None.
        updated: Last update date as YYYY-MM-DD string or None.
        primary_category: Primary category/field if provided.
        categories: Additional categories/tags.
        abstract_url: URL to the abstract/landing page.
        pdf_url: Direct URL to PDF if available.
        doi: Digital Object Identifier if available.
        abstract_translation: LLM-generated translation of the abstract.
        tldr: LLM-generated TL;DR summary.
        motivation: LLM-generated research motivation.
        method: LLM-generated methodology description.
        result: LLM-generated results summary.
        conclusion: LLM-generated conclusions.
    """

    # Basic metadata
    source: str
    id: str
    title: str
    authors: Sequence[str]
    abstract: str

    # Temporal info (formatted strings for display)
    published: str | None
    updated: str | None

    # Categorization
    primary_category: str | None
    categories: Sequence[str]

    # Links
    abstract_url: str | None
    pdf_url: str | None
    doi: str | None

    # LLM-generated content (translation)
    abstract_translation: str | None = None

    # LLM-generated content (summary)
    tldr: str | None = None
    motivation: str | None = None
    method: str | None = None
    result: str | None = None
    conclusion: str | None = None
