"""arXiv Atom feed parser.

Parses arXiv Atom XML into the unified internal `Paper` list.
"""

from __future__ import annotations

from datetime import datetime
import re
from urllib.parse import urlparse
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


def _normalize_arxiv_id(raw_id: str, *, keep_version: bool) -> str:
    """Normalize an arXiv id extracted from feed entries or URLs.

    Args:
        raw_id: Raw id or URL from the feed entry.
        keep_version: Whether to keep the version suffix (e.g., v1).

    Returns:
        Normalized arXiv id string (optionally without version).
    """
    if not raw_id:
        return ""

    value = raw_id.strip()
    if "arxiv.org" in value:
        parsed = urlparse(value)
        path = parsed.path or ""
        if "/abs/" in path:
            value = path.split("/abs/", 1)[1]
        elif "/pdf/" in path:
            value = path.split("/pdf/", 1)[1]
        else:
            value = path.lstrip("/")
        if value.endswith(".pdf"):
            value = value[:-4]

    value = value.strip("/")
    if not value:
        return raw_id
    if not keep_version:
        value = re.sub(r"v\d+$", "", value)
    return value


def parse_arxiv_feed(xml_text: str, *, keep_version: bool = False) -> Sequence[Paper]:
    """Parse arXiv Atom feed XML into Paper objects.

    Args:
        xml_text: Atom feed XML text.
        keep_version: Whether to keep the arXiv version suffix in the paper id.

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
        doi = None
        for link in entry.get("links", []):
            if link.get("rel") == "alternate":
                abstract_url = link.get("href")
            if link.get("title", "").lower() == "pdf" or link.get("type") == "application/pdf":
                pdf_url = link.get("href")
            href = link.get("href", "")
            if not doi and "doi.org" in href:
                doi = href

        if not doi:
            doi = entry.get("arxiv_doi") or entry.get("doi") or None

        primary_cat = getattr(getattr(entry, "arxiv_primary_category", {}), "term", None) or None
        categories = [t.get("term") for t in entry.get("tags", []) if t.get("term")]

        paper_id = _normalize_arxiv_id(entry.get("id") or "", keep_version=keep_version)

        items.append(
            Paper(
                source="arxiv",
                id=paper_id,
                title=title,
                authors=authors,
                summary=getattr(entry, "summary", ""),
                published=published,
                updated=updated,
                primary_category=primary_cat,
                categories=categories,
                links=PaperLinks(abstract=abstract_url, pdf=pdf_url),
                doi=doi,
            )
        )
    return items
