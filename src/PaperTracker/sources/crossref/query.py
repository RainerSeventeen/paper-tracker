"""Crossref query compiler and post-fetch filters."""

from __future__ import annotations

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery


_FIELD_TO_PARAMS: dict[str, tuple[str, ...]] = {
    "TEXT": ("query.bibliographic",),
    "TITLE": ("query.bibliographic",),
    "ABSTRACT": ("query.bibliographic",),
    "AUTHOR": ("query.author",),
    "JOURNAL": ("query.container-title",),
}


def compile_crossref_params(*, query: SearchQuery, scope: SearchQuery | None = None) -> dict[str, str]:
    """Compile internal query structure into Crossref ``query.*`` params."""
    positive_by_param: dict[str, list[str]] = {}
    negative_by_param: dict[str, list[str]] = {}

    for source_query in (scope, query):
        if source_query is None:
            continue
        for field, field_query in source_query.fields.items():
            param_keys = _FIELD_TO_PARAMS.get(field.upper().strip(), ())
            if not param_keys:
                continue
            positive_terms = _normalize_terms(field_query.AND) + _normalize_terms(field_query.OR)
            negative_terms = _normalize_terms(field_query.NOT)
            for param_key in param_keys:
                positive_by_param.setdefault(param_key, []).extend(positive_terms)
                negative_by_param.setdefault(param_key, []).extend(negative_terms)

    params: dict[str, str] = {}
    for param_key, positive_terms in positive_by_param.items():
        unique_positive = _dedup_preserve_order(positive_terms)
        unique_negative = _dedup_preserve_order(negative_by_param.get(param_key, []))
        parts = [term for term in unique_positive]
        parts.extend(f"-{term}" for term in unique_negative)
        query_text = " ".join(parts).strip()
        if query_text:
            params[param_key] = query_text
    return params


def extract_not_terms(*, query: SearchQuery, scope: SearchQuery | None = None) -> frozenset[str]:
    """Extract all NOT terms from query and optional scope for post-fetch filtering."""
    not_terms: list[str] = []
    for source_query in (scope, query):
        if source_query is None:
            continue
        for field_query in source_query.fields.values():
            not_terms.extend(_normalize_terms(field_query.NOT))
    return frozenset(term.casefold() for term in not_terms)


def apply_not_filter(papers: list[Paper], not_terms: frozenset[str]) -> list[Paper]:
    """Filter out papers whose title or abstract contains any NOT term (case-insensitive)."""
    if not not_terms:
        return papers
    return [p for p in papers if not _paper_matches_not_term(p, not_terms)]


def _paper_matches_not_term(paper: Paper, not_terms: frozenset[str]) -> bool:
    """Return True if paper title or abstract contains any NOT term."""
    haystack = f"{paper.title} {paper.abstract}".casefold()
    return any(term in haystack for term in not_terms)


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
