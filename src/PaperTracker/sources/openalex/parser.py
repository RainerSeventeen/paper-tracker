"""OpenAlex payload parser."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from PaperTracker.core.models import Paper, PaperLinks


def parse_openalex_works(items: Sequence[Mapping[str, Any]]) -> list[Paper]:
    """Convert OpenAlex works payloads into normalized ``Paper`` objects.

    Args:
        items: OpenAlex ``results`` records represented as mappings.

    Returns:
        Internal canonical paper list.
    """
    papers: list[Paper] = []

    for item in items:
        title = _safe_str(item.get("title")) or "Untitled"
        work_id = _normalize_openalex_id(_safe_str(item.get("id")), fallback_title=title)

        published = _extract_published(item)
        updated = _extract_updated(item)
        authors = _extract_authors(item.get("authorships"))
        abstract = _rebuild_abstract(item.get("abstract_inverted_index"))
        doi = _normalize_doi(_safe_str(item.get("doi")))

        categories = _extract_categories(item)
        primary_category = categories[0] if categories else None
        abstract_url, pdf_url = _extract_links(item)

        papers.append(
            Paper(
                source="openalex",
                id=work_id,
                title=title,
                authors=authors,
                abstract=abstract,
                published=published,
                updated=updated,
                primary_category=primary_category,
                categories=categories,
                links=PaperLinks(abstract=abstract_url, pdf=pdf_url),
                doi=doi or None,
                extra={"work_type": _extract_work_type(item)},
            )
        )

    return papers


def _normalize_openalex_id(raw_id: str, *, fallback_title: str) -> str:
    """Normalize OpenAlex work id into a stable canonical identifier."""
    value = raw_id.strip()
    if value:
        marker = "openalex.org/"
        idx = value.casefold().find(marker)
        if idx >= 0:
            value = value[idx + len(marker):]
        value = value.strip("/")
    if value:
        return value

    fallback = fallback_title.casefold().strip()
    return f"openalex:{fallback or 'unknown'}"


def _extract_published(item: Mapping[str, Any]) -> datetime | None:
    """Extract publication date from OpenAlex work payload."""
    publication_date = _safe_str(item.get("publication_date"))
    if publication_date:
        parsed = _parse_date(publication_date)
        if parsed is not None:
            return parsed

    year_value = item.get("publication_year")
    if isinstance(year_value, int) and not isinstance(year_value, bool):
        try:
            return datetime(year_value, 1, 1, tzinfo=timezone.utc)
        except ValueError:
            return None

    return None


def _extract_updated(item: Mapping[str, Any]) -> datetime | None:
    """Extract updated timestamp from OpenAlex work payload."""
    updated_date = _safe_str(item.get("updated_date"))
    if not updated_date:
        return None
    return _parse_date(updated_date)


def _parse_date(value: str) -> datetime | None:
    """Parse ISO-like date/datetime into timezone-aware datetime."""
    text = value.strip()
    if not text:
        return None

    if len(text) == 10:
        try:
            return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _extract_authors(raw_authorships: Any) -> tuple[str, ...]:
    """Extract author display names from OpenAlex ``authorships``."""
    if not isinstance(raw_authorships, list):
        return ()

    authors: list[str] = []
    for authorship in raw_authorships:
        if not isinstance(authorship, Mapping):
            continue
        author = authorship.get("author")
        if not isinstance(author, Mapping):
            continue
        name = _safe_str(author.get("display_name"))
        if name:
            authors.append(name)
    return tuple(authors)


def _extract_categories(item: Mapping[str, Any]) -> tuple[str, ...]:
    """Extract OpenAlex topics/concepts as canonical categories."""
    categories: list[str] = []

    primary_topic = item.get("primary_topic")
    if isinstance(primary_topic, Mapping):
        primary_name = _safe_str(primary_topic.get("display_name"))
        if primary_name:
            categories.append(primary_name)

    concepts = item.get("concepts")
    if isinstance(concepts, list):
        for concept in concepts:
            if not isinstance(concept, Mapping):
                continue
            name = _safe_str(concept.get("display_name"))
            if name:
                categories.append(name)

    deduped: list[str] = []
    seen: set[str] = set()
    for category in categories:
        key = category.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(category)
    return tuple(deduped)


def _extract_links(item: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """Extract landing and PDF links from OpenAlex work payload."""
    abstract_url = _safe_str(item.get("id")) or None
    pdf_url: str | None = None

    best_location = item.get("best_oa_location")
    if isinstance(best_location, Mapping):
        pdf_candidate = _safe_str(best_location.get("pdf_url"))
        if pdf_candidate:
            pdf_url = pdf_candidate
        landing_candidate = _safe_str(best_location.get("landing_page_url"))
        if landing_candidate:
            abstract_url = landing_candidate

    open_access = item.get("open_access")
    if isinstance(open_access, Mapping):
        oa_url = _safe_str(open_access.get("oa_url"))
        if oa_url and abstract_url is None:
            abstract_url = oa_url

    return abstract_url, pdf_url


def _extract_work_type(item: Mapping[str, Any]) -> str:
    """Map OpenAlex work type into dedup-oriented coarse class."""
    raw_type = _safe_str(item.get("type")).casefold()
    if raw_type in {"article", "journal-article", "proceedings-article", "book-chapter"}:
        return "article"
    if raw_type in {"preprint", "posted-content"}:
        return "preprint"
    return "unknown"


def _rebuild_abstract(raw_index: Any) -> str:
    """Reconstruct abstract text from ``abstract_inverted_index``."""
    if not isinstance(raw_index, Mapping):
        return ""

    positioned_tokens: list[tuple[int, str]] = []
    for token, positions in raw_index.items():
        if not isinstance(token, str) or not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int) and not isinstance(position, bool):
                positioned_tokens.append((position, token))

    if not positioned_tokens:
        return ""

    positioned_tokens.sort(key=lambda item: item[0])
    return " ".join(token for _, token in positioned_tokens).strip()


def _normalize_doi(raw_doi: str) -> str:
    """Normalize DOI string into lowercase plain identifier."""
    normalized = raw_doi.strip().lower()
    if not normalized:
        return ""

    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break

    return normalized.strip()


def _safe_str(value: Any) -> str:
    """Convert scalar value into stripped string."""
    if isinstance(value, str):
        return value.strip()
    return ""
