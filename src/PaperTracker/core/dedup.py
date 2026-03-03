"""Paper deduplication identity helpers.

Builds normalized DOI/title/author/year identities shared by service-level and storage-level deduplication.
"""

from __future__ import annotations

from datetime import datetime
import re

from PaperTracker.core.models import Paper

_TEXT_WS_RE = re.compile(r"\s+")
_TEXT_STRIP_RE = re.compile(r"[^a-z0-9 ]")
_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)
_TITLE_DEDUP_MIN_LEN = 24


def normalize_doi(doi: str | None) -> str:
    """Normalize DOI text into a canonical key."""
    if doi is None:
        return ""
    normalized = doi.strip().lower()
    for prefix in _DOI_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    return normalized.strip()


def normalize_title(title: str) -> str:
    """Normalize title text for conservative deduplication."""
    lowered = title.casefold()
    no_punctuation = _TEXT_STRIP_RE.sub(" ", lowered)
    return _TEXT_WS_RE.sub(" ", no_punctuation).strip()


def normalize_author(author: str) -> str:
    """Normalize author text for stable first-author identity."""
    lowered = author.casefold()
    no_punctuation = _TEXT_STRIP_RE.sub(" ", lowered)
    return _TEXT_WS_RE.sub(" ", no_punctuation).strip()


def resolve_year(paper: Paper) -> int | None:
    """Resolve best-effort comparable year from paper timestamps."""
    timestamp = paper.published or paper.updated
    if timestamp is None:
        return None
    return timestamp.year


def build_title_author_year_fingerprint(paper: Paper) -> str | None:
    """Build conservative fallback fingerprint for deduplication.

    Requires a sufficiently informative title, a non-empty first author, and
    a resolvable year to avoid false-positive merges.
    """
    title_norm = normalize_title(paper.title)
    if len(title_norm) < _TITLE_DEDUP_MIN_LEN:
        return None

    first_author_norm = ""
    for author in paper.authors:
        candidate = normalize_author(author)
        if candidate:
            first_author_norm = candidate
            break
    if not first_author_norm:
        return None

    year = resolve_year(paper)
    if year is None:
        return None

    return f"{title_norm}|{first_author_norm}|{year}"


def resolve_timestamp(paper: Paper) -> datetime | None:
    """Resolve primary comparable timestamp for ranking and sorting."""
    return paper.published or paper.updated
