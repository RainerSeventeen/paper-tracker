from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence


@dataclass(frozen=True, slots=True)
class PaperLinks:
    """Common link fields for a paper.

    Attributes:
        abstract: URL to the abstract/landing page.
        pdf: Direct URL to the PDF if available.
    """

    abstract: Optional[str] = None
    pdf: Optional[str] = None


@dataclass(frozen=True, slots=True)
class Paper:
    """Internal canonical paper model.

    This is the unified data format that all external sources must map to.

    Attributes:
        source: Source identifier (e.g. "arxiv").
        id: Source-specific unique identifier.
        title: Paper title.
        authors: Author names.
        abstract: Abstract text.
        published: First publication datetime if known.
        updated: Last update datetime if known.
        primary_category: Primary category/field if provided by the source.
        categories: Additional categories/tags.
        links: Common link URLs.
        doi: Digital Object Identifier if available.
        extra: Extension point for provider-specific fields.
    """

    source: str
    id: str
    title: str
    authors: Sequence[str]
    abstract: str
    published: Optional[datetime]
    updated: Optional[datetime]
    primary_category: Optional[str] = None
    categories: Sequence[str] = ()
    links: PaperLinks = PaperLinks()
    doi: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Keep a stable read-only mapping to support forward-compatible fields
        # without risking accidental mutation.
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))


@dataclass(frozen=True, slots=True)
class LLMGeneratedInfo:
    """LLM-generated enrichment for a paper.

    Supports two types of enrichment:
    - Translation: abstract_translation field
    - Summary: tldr, motivation, method, result, conclusion fields

    At least one enrichment type should be present.
    """

    source: str
    source_id: str
    language: str = "en"

    # Translation enrichment
    abstract_translation: str | None = None

    # Summary enrichment (structured key points)
    tldr: str | None = None              # Too Long; Didn't Read summary
    motivation: str | None = None        # Research motivation and background
    method: str | None = None            # Research methodology and approach
    result: str | None = None            # Experimental results and findings
    conclusion: str | None = None        # Conclusions and implications
