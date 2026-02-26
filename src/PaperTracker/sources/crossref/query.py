"""Crossref query compiler."""

from __future__ import annotations

from PaperTracker.core.query import SearchQuery


def compile_crossref_query(*, query: SearchQuery, scope: SearchQuery | None = None) -> str:
    """Compile internal query structure into a Crossref full-text query string."""
    positive_terms: list[str] = []
    negative_terms: list[str] = []

    for source_query in (scope, query):
        if source_query is None:
            continue
        for field_query in source_query.fields.values():
            positive_terms.extend(_normalize_terms(field_query.AND))
            positive_terms.extend(_normalize_terms(field_query.OR))
            negative_terms.extend(_normalize_terms(field_query.NOT))

    unique_positive = _dedup_preserve_order(positive_terms)
    unique_negative = _dedup_preserve_order(negative_terms)

    parts = [term for term in unique_positive]
    parts.extend(f"-{term}" for term in unique_negative)
    return " ".join(parts).strip()


def _normalize_terms(terms: object) -> list[str]:
    """Normalize arbitrary query terms into non-empty string list."""
    if not isinstance(terms, (list, tuple)):
        return []

    normalized: list[str] = []
    for term in terms:
        value = str(term).strip()
        if value:
            normalized.append(value)
    return normalized


def _dedup_preserve_order(terms: list[str]) -> list[str]:
    """Remove duplicates while preserving first occurrence order."""
    seen: set[str] = set()
    unique: list[str] = []
    for term in terms:
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(term)
    return unique
