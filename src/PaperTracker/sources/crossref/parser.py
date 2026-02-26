"""Crossref payload parser."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from dateutil import parser as dt_parser

from PaperTracker.core.models import Paper, PaperLinks

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def parse_crossref_items(items: Sequence[Mapping[str, Any]]) -> list[Paper]:
    """Parse Crossref work items into unified Paper objects."""
    papers: list[Paper] = []

    for item in items:
        title = _first_non_empty_text(item.get("title"))
        if not title:
            title = "Untitled"

        source_id = _build_source_id(item, fallback_title=title)
        published = _extract_datetime(item, preferred_keys=("published-print", "published-online", "issued", "created"))
        updated = _extract_datetime(item, preferred_keys=("updated", "indexed", "created", "issued"))
        abstract = _clean_abstract(_safe_str(item.get("abstract")))
        doi = _safe_str(item.get("DOI")) or None

        subjects = _collect_str_list(item.get("subject"))
        papers.append(
            Paper(
                source="crossref",
                id=source_id,
                title=title,
                authors=_extract_authors(item.get("author")),
                abstract=abstract,
                published=published,
                updated=updated,
                primary_category=subjects[0] if subjects else None,
                categories=subjects,
                links=PaperLinks(abstract=_safe_str(item.get("URL")) or None),
                doi=doi,
            )
        )

    return papers


def _build_source_id(item: Mapping[str, Any], *, fallback_title: str) -> str:
    """Build deterministic source id for Crossref record."""
    doi = _safe_str(item.get("DOI"))
    if doi:
        return doi.lower()

    canonical_url = _safe_str(item.get("URL"))
    if canonical_url:
        return canonical_url

    year = _extract_year(item)
    author_hint = ""
    authors = item.get("author")
    if isinstance(authors, list) and authors:
        first = authors[0]
        if isinstance(first, dict):
            author_hint = _safe_str(first.get("family")) or _safe_str(first.get("name"))

    signature = f"{fallback_title.casefold()}|{year or ''}|{author_hint.casefold()}"
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:16]
    return f"crossref:{digest}"


def _extract_authors(raw_authors: Any) -> tuple[str, ...]:
    """Parse Crossref author objects into display names."""
    if not isinstance(raw_authors, list):
        return ()

    names: list[str] = []
    for author in raw_authors:
        if not isinstance(author, Mapping):
            continue
        given = _safe_str(author.get("given"))
        family = _safe_str(author.get("family"))
        full_name = " ".join(part for part in (given, family) if part).strip()
        if not full_name:
            full_name = _safe_str(author.get("name"))
        if full_name:
            names.append(full_name)
    return tuple(names)


def _extract_datetime(item: Mapping[str, Any], *, preferred_keys: Sequence[str]) -> datetime | None:
    """Extract datetime using Crossref date fields in preferred order."""
    for key in preferred_keys:
        value = item.get(key)
        if isinstance(value, Mapping):
            date_time = _safe_str(value.get("date-time"))
            if date_time:
                parsed = _parse_iso_datetime(date_time)
                if parsed is not None:
                    return parsed

            date_parts = value.get("date-parts")
            parsed_parts = _parse_date_parts(date_parts)
            if parsed_parts is not None:
                return parsed_parts

    return None


def _parse_iso_datetime(raw_value: str) -> datetime | None:
    """Parse ISO datetime text into timezone-aware datetime."""
    if not raw_value:
        return None
    try:
        parsed = dt_parser.isoparse(raw_value)
    except (TypeError, ValueError):
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_date_parts(raw_value: Any) -> datetime | None:
    """Parse Crossref date-parts arrays into datetime."""
    if not isinstance(raw_value, list) or not raw_value:
        return None

    first_parts = raw_value[0]
    if not isinstance(first_parts, list) or not first_parts:
        return None

    numbers: list[int] = []
    for idx, part in enumerate(first_parts[:3]):
        if isinstance(part, bool) or not isinstance(part, int):
            return None
        if idx == 1 and not 1 <= part <= 12:
            return None
        if idx == 2 and not 1 <= part <= 31:
            return None
        numbers.append(part)

    year = numbers[0]
    month = numbers[1] if len(numbers) >= 2 else 1
    day = numbers[2] if len(numbers) >= 3 else 1

    try:
        return datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None


def _extract_year(item: Mapping[str, Any]) -> int | None:
    """Extract best-effort publication year from Crossref metadata."""
    for key in ("issued", "published-print", "published-online", "created"):
        section = item.get(key)
        if not isinstance(section, Mapping):
            continue
        date_parts = section.get("date-parts")
        if (
            isinstance(date_parts, list)
            and date_parts
            and isinstance(date_parts[0], list)
            and date_parts[0]
            and isinstance(date_parts[0][0], int)
            and not isinstance(date_parts[0][0], bool)
        ):
            return date_parts[0][0]
    return None


def _clean_abstract(text: str) -> str:
    """Remove XML tags and normalize whitespace in abstract text."""
    if not text:
        return ""
    no_tags = _TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", no_tags).strip()


def _first_non_empty_text(value: Any) -> str:
    """Return first non-empty string from value/list value."""
    if isinstance(value, list):
        for item in value:
            text = _safe_str(item)
            if text:
                return text
        return ""
    return _safe_str(value)


def _collect_str_list(value: Any) -> tuple[str, ...]:
    """Collect non-empty strings from list-like values."""
    if not isinstance(value, list):
        return ()

    out: list[str] = []
    for item in value:
        text = _safe_str(item)
        if text:
            out.append(text)
    return tuple(out)


def _safe_str(value: Any) -> str:
    """Convert scalar value to stripped string."""
    if isinstance(value, str):
        return value.strip()
    return ""
