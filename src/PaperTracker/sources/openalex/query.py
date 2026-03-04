"""OpenAlex query compiler and post-fetch filters."""

from __future__ import annotations

from PaperTracker.core.models import Paper
from PaperTracker.core.query import FieldQuery
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
    clauses: list[str] = []
    for source_query in (scope, query):
        if source_query is None:
            continue
        query_clause = _build_query_clause(source_query)
        if query_clause:
            clauses.append(query_clause)

    search_text = " AND ".join(clauses).strip()
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


def apply_positive_filter(
    papers: list[Paper],
    *,
    query: SearchQuery,
    scope: SearchQuery | None = None,
) -> list[Paper]:
    """Apply strict local boolean matching for scope + query."""
    return [
        paper
        for paper in papers
        if _matches_query(paper=paper, search_query=query)
        and (scope is None or _matches_query(paper=paper, search_query=scope))
    ]


def _paper_matches_not_term(paper: Paper, not_terms: frozenset[str]) -> bool:
    """Return True when title or abstract contains a NOT term."""
    haystack = f"{paper.title} {paper.abstract}".casefold()
    return any(term in haystack for term in not_terms)


def _matches_query(*, paper: Paper, search_query: SearchQuery) -> bool:
    """Return True when all field clauses in a query are satisfied."""
    for field_name, field_query in search_query.fields.items():
        if not _matches_field_query(paper=paper, field_name=field_name, field_query=field_query):
            return False
    return True


def _matches_field_query(*, paper: Paper, field_name: str, field_query: FieldQuery) -> bool:
    """Evaluate field-level AND/OR/NOT against projected text."""
    if field_name.strip().upper() == "CATEGORY":
        # CATEGORY is an arXiv-specific field; OpenAlex does not carry it, skip filtering.
        return True
    haystack = _field_text(paper=paper, field_name=field_name).casefold()
    and_terms = [term.casefold() for term in _normalize_terms(field_query.AND)]
    or_terms = [term.casefold() for term in _normalize_terms(field_query.OR)]
    not_terms = [term.casefold() for term in _normalize_terms(field_query.NOT)]

    if and_terms and any(term not in haystack for term in and_terms):
        return False
    if or_terms and not any(term in haystack for term in or_terms):
        return False
    if not_terms and any(term in haystack for term in not_terms):
        return False
    return True


def _field_text(*, paper: Paper, field_name: str) -> str:
    """Project paper into field text used by local boolean filtering."""
    normalized = field_name.strip().upper()
    if normalized == "TITLE":
        return paper.title
    if normalized == "ABSTRACT":
        return paper.abstract
    if normalized == "AUTHOR":
        return " ".join(paper.authors)
    if normalized == "JOURNAL":
        return paper.journal
    # TEXT and unknown fields fallback to title + abstract.
    return f"{paper.title} {paper.abstract}"


def _build_query_clause(search_query: SearchQuery) -> str:
    """Build boolean clause for one SearchQuery."""
    field_clauses: list[str] = []
    for field_query in search_query.fields.values():
        field_clause = _build_field_clause(field_query)
        if field_clause:
            field_clauses.append(field_clause)
    return " AND ".join(field_clauses)


def _build_field_clause(field_query: FieldQuery) -> str:
    """Build boolean clause from a FieldQuery."""
    and_terms = _normalize_terms(field_query.AND)
    or_terms = _normalize_terms(field_query.OR)
    not_terms = _normalize_terms(field_query.NOT)
    clauses: list[str] = []

    if and_terms:
        if len(and_terms) == 1:
            clauses.append(_quote_term(and_terms[0]))
        else:
            clauses.append("(" + " AND ".join(_quote_term(term) for term in and_terms) + ")")

    if or_terms:
        if len(or_terms) == 1:
            clauses.append(_quote_term(or_terms[0]))
        else:
            clauses.append("(" + " OR ".join(_quote_term(term) for term in or_terms) + ")")

    if not_terms:
        if len(not_terms) == 1:
            clauses.append(f"NOT {_quote_term(not_terms[0])}")
        else:
            clauses.append("NOT (" + " OR ".join(_quote_term(term) for term in not_terms) + ")")

    return " AND ".join(clauses)


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


def _quote_term(term: str) -> str:
    """Quote term for OpenAlex boolean text query."""
    escaped = term.replace('"', '\\"')
    return f'"{escaped}"'
