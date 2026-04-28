"""PubMed query compiler.

Compiles internal structured search queries into PubMed E-utilities term strings
with field-tag mapping and boolean operator handling.
"""

from __future__ import annotations

from PaperTracker.core.query import FieldQuery, SearchQuery

# Fields that map to PubMed query tags and contribute positive conditions.
# CATEGORY has no direct PubMed mapping and is skipped.
_FIELD_TAG_MAP: dict[str, str] = {
    "TEXT": "[TIAB]",
    "TITLE": "[TIAB]",
    "ABSTRACT": "[TIAB]",
    "AUTHOR": "[AU]",
    "JOURNAL": "[JT]",
}


def compile_pubmed_term(*, query: SearchQuery, scope: SearchQuery | None = None) -> str:
    """Compile query + optional scope into a PubMed E-utilities term string.

    CATEGORY fields are silently skipped (no PubMed mapping). If the resulting
    term has no positive conditions (AND/OR from any supported field), a
    ValueError is raised to prevent implicit full-index retrieval.

    Args:
        query: Main structured query.
        scope: Optional global scope merged before query with AND.

    Returns:
        PubMed term string ready for ESearch ``term`` parameter.

    Raises:
        ValueError: If the compiled term has no positive conditions.
    """
    parts: list[str] = []
    for source_query in (scope, query):
        if source_query is None:
            continue
        clause = _compile_query_clause(source_query)
        if clause:
            parts.append(clause)

    if not parts:
        raise ValueError(
            "PubMed query has no supported fields: "
            "CATEGORY-only or empty queries are not allowed"
        )

    return " AND ".join(parts)


def _compile_query_clause(search_query: SearchQuery) -> str:
    """Compile one SearchQuery into a PubMed boolean clause.

    Only fields with a known PubMed tag mapping contribute.  CATEGORY fields
    are skipped. Returns an empty string when no mappable fields are present.
    """
    field_clauses: list[str] = []
    for field_name, field_query in search_query.fields.items():
        tag = _FIELD_TAG_MAP.get(field_name.strip().upper())
        if tag is None:
            continue
        clause = _compile_field_clause(field_query, tag)
        if clause:
            field_clauses.append(clause)

    if not field_clauses:
        return ""
    if len(field_clauses) == 1:
        return field_clauses[0]
    return "(" + " AND ".join(field_clauses) + ")"


def _compile_field_clause(field_query: FieldQuery, tag: str) -> str:
    """Compile a FieldQuery into a PubMed boolean clause for one field tag."""
    and_terms = _normalize_terms(field_query.AND)
    or_terms = _normalize_terms(field_query.OR)
    not_terms = _normalize_terms(field_query.NOT)

    parts: list[str] = []

    for term in and_terms:
        parts.append(f'"{term}"{tag}')

    if or_terms:
        if len(or_terms) == 1:
            parts.append(f'"{or_terms[0]}"{tag}')
        else:
            inner = " OR ".join(f'"{t}"{tag}' for t in or_terms)
            parts.append(f"({inner})")

    if not_terms:
        if len(not_terms) == 1:
            neg = f'"{not_terms[0]}"{tag}'
        else:
            neg = "(" + " OR ".join(f'"{t}"{tag}' for t in not_terms) + ")"
        parts.append(f"NOT ({neg})" if len(not_terms) == 1 else f"NOT {neg}")

    return " AND ".join(parts)


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
