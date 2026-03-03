"""OpenAlex query compiler and post-fetch filters."""

from __future__ import annotations

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery


def compile_openalex_params(*, query: SearchQuery, scope: SearchQuery | None = None) -> dict[str, str]:
    """Compile query conditions into OpenAlex request parameters.

    OpenAlex supports a global ``search`` parameter. This compiler merges all
    positive terms from ``scope`` + ``query`` into one space-delimited search
    text.

    Args:
        query: User-level structured query.
        scope: Optional global scope merged before query.

    Returns:
        OpenAlex request parameters.
    """
    positive_terms: list[str] = []

    for source_query in (scope, query):
        if source_query is None:
            continue
        for field_query in source_query.fields.values():
            positive_terms.extend(_normalize_terms(field_query.AND))
            positive_terms.extend(_normalize_terms(field_query.OR))

    search_text = " ".join(_dedup_preserve_order(positive_terms)).strip()
    if not search_text:
        return {}
    return {"search": search_text}


def extract_not_terms(*, query: SearchQuery, scope: SearchQuery | None = None) -> frozenset[str]:
    """Collect normalized NOT terms for local post-fetch filtering.

    Args:
        query: User-level structured query.
        scope: Optional global scope.

    Returns:
        A case-insensitive set of excluded terms.
    """
    not_terms: list[str] = []
    for source_query in (scope, query):
        if source_query is None:
            continue
        for field_query in source_query.fields.values():
            not_terms.extend(_normalize_terms(field_query.NOT))
    return frozenset(term.casefold() for term in not_terms)


def apply_not_filter(papers: list[Paper], not_terms: frozenset[str]) -> list[Paper]:
    """Filter out papers that contain any NOT term in title or abstract.

    Args:
        papers: Candidate papers returned by OpenAlex.
        not_terms: Case-insensitive terms excluded by query.

    Returns:
        Papers that do not match NOT terms.
    """
    if not not_terms:
        return papers
    return [paper for paper in papers if not _paper_matches_not_term(paper, not_terms)]


def _paper_matches_not_term(paper: Paper, not_terms: frozenset[str]) -> bool:
    """Return True when title or abstract contains a NOT term."""
    haystack = f"{paper.title} {paper.abstract}".casefold()
    return any(term in haystack for term in not_terms)


def _normalize_terms(terms: object) -> list[str]:
    """Normalize raw terms into a non-empty string list."""
    if not isinstance(terms, (list, tuple)):
        return []

    normalized: list[str] = []
    for term in terms:
        value = str(term).strip()
        if value:
            normalized.append(value)
    return normalized


def _dedup_preserve_order(terms: list[str]) -> list[str]:
    """Drop duplicate terms while preserving first-seen order."""
    seen: set[str] = set()
    unique: list[str] = []
    for term in terms:
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(term)
    return unique
