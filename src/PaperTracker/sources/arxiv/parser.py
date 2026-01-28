"""arXiv Atom feed parser.

Parses arXiv Atom XML into the unified internal `Paper` list.
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

import feedparser
from dateutil import parser as dt_parser

from PaperTracker.core.models import Paper, PaperLinks


def _parse_dt(dt: str | None) -> datetime | None:
    """Parse datetime string from arXiv feed.

    Args:
        dt: Datetime string (RFC3339-ish) or None.

    Returns:
        Parsed datetime, or None when input is empty.
    """
    if not dt:
        return None
    return dt_parser.parse(dt)


def parse_arxiv_feed(xml_text: str) -> Sequence[Paper]:
    """Parse arXiv Atom feed XML into Paper objects.

    Args:
        xml_text: Atom feed XML text.

    Returns:
        A sequence of Paper.
    """
    feed = feedparser.parse(xml_text)
    items: list[Paper] = []
    for entry in feed.entries:
        title = (entry.title or "").replace("\n", " ").strip()
        authors = [a.get("name", "") for a in entry.get("authors", [])] if "authors" in entry else []
        published = _parse_dt(entry.get("published"))
        updated = _parse_dt(entry.get("updated"))

        abstract_url = None
        pdf_url = None
        for link in entry.get("links", []):
            if link.get("rel") == "alternate":
                abstract_url = link.get("href")
            if link.get("title", "").lower() == "pdf" or link.get("type") == "application/pdf":
                pdf_url = link.get("href")

        primary_cat = getattr(getattr(entry, "arxiv_primary_category", {}), "term", None) or None
        categories = [t.get("term") for t in entry.get("tags", []) if t.get("term")]

        items.append(
            Paper(
                source="arxiv",
                id=entry.get("id") or "",
                title=title,
                authors=authors,
                summary=getattr(entry, "summary", ""),
                published=published,
                updated=updated,
                primary_category=primary_cat,
                categories=categories,
                links=PaperLinks(abstract=abstract_url, pdf=pdf_url),
            )
        )
    return items
