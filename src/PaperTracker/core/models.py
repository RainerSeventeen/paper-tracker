from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence


@dataclass(frozen=True, slots=True)
class PaperLinks:
    abstract: Optional[str] = None
    pdf: Optional[str] = None


@dataclass(frozen=True, slots=True)
class Paper:
    source: str
    id: str
    title: str
    authors: Sequence[str]
    summary: str
    published: Optional[datetime]
    updated: Optional[datetime]
    primary_category: Optional[str] = None
    categories: Sequence[str] = ()
    links: PaperLinks = PaperLinks()

