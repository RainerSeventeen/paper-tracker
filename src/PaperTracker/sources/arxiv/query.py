"""arXiv query compiler.

Compiles the internal, structured `SearchQuery` into an arXiv Atom API
`search_query` string.

Rules
- Field names in the internal schema are semantic and uppercase:
  TITLE / ABSTRACT / AUTHOR / JOURNAL / CATEGORY
- Terms without special syntax are treated as raw values.
- For a given field, the config supports three explicit operators:
  AND / OR / NOT

Mapping to arXiv fields
- TEXT     -> (ti OR abs)
- TITLE    -> ti
- ABSTRACT -> abs
- AUTHOR   -> au
- CATEGORY -> cat
- JOURNAL  -> (jr OR co)  (best-effort; arXiv does not have a strict journal field)
"""

from __future__ import annotations

import re
from typing import Iterable

from PaperTracker.core.query import FieldQuery, SearchQuery


_RE_NEEDS_QUOTE = re.compile(r"[\s-]")


def _quote(term: str) -> str:
    t = term.strip()
    if not t:
        return ""
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        return t
    if _RE_NEEDS_QUOTE.search(t):
        return f'"{t}"'
    return t


def _field_or(fields: Iterable[str], term: str) -> str:
    q = _quote(term)
    return "(" + " OR ".join(f"{f}:{q}" for f in fields) + ")"


def _expand_variants(keyword: str) -> list[str]:
    k = keyword.strip()
    out = {k}
    if " " in k:
        out.add(k.replace(" ", "-"))
    if "-" in k:
        out.add(k.replace("-", " "))
    return sorted(out, key=len, reverse=True)


def _term_group(fields: Iterable[str], term: str) -> str:
    variants = _expand_variants(term)
    parts = [_field_or(fields, v) for v in variants if v.strip()]
    return "(" + " OR ".join(parts) + ")"


def _compile_field(field: str, fq: FieldQuery) -> str:
    field = field.upper().strip()
    if field == "TEXT":
        arxiv_fields = ("ti", "abs")
    elif field == "TITLE":
        arxiv_fields = ("ti",)
    elif field == "ABSTRACT":
        arxiv_fields = ("abs",)
    elif field == "AUTHOR":
        arxiv_fields = ("au",)
    elif field == "CATEGORY":
        arxiv_fields = ("cat",)
    elif field == "JOURNAL":
        arxiv_fields = ("jr", "co")
    else:
        raise ValueError(f"Unsupported field for arXiv: {field}")

    and_terms = [t for t in fq.AND if str(t).strip()]
    or_terms = [t for t in fq.OR if str(t).strip()]
    not_terms = [t for t in fq.NOT if str(t).strip()]

    parts: list[str] = []

    for t in and_terms:
        parts.append(_term_group(arxiv_fields, str(t)))

    if or_terms:
        parts.append("(" + " OR ".join(_term_group(arxiv_fields, str(t)) for t in or_terms) + ")")

    positive = ""
    if parts:
        positive = "(" + " AND ".join(parts) + ")"

    if not_terms:
        neg = "(" + " OR ".join(_term_group(arxiv_fields, str(t)) for t in not_terms) + ")"
        if positive:
            return f"({positive} AND NOT {neg})"
        return f"(all:* AND NOT {neg})"

    return positive


def compile_search_query(*, query: SearchQuery, scope: SearchQuery | None = None) -> str:
    """Compile query + optional scope into an arXiv `search_query`.

    Args:
        query: Main query.
        scope: Optional global scope applied to every query.

    Returns:
        arXiv `search_query` string.
    """

    parts: list[str] = []

    def add_fields(q: SearchQuery) -> None:
        for field, fq in q.fields.items():
            compiled = _compile_field(field, fq)
            if compiled:
                parts.append(compiled)

    if scope is not None:
        add_fields(scope)
    add_fields(query)

    if not parts:
        return "all:*"
    if len(parts) == 1:
        return parts[0]
    return "(" + " AND ".join(parts) + ")"
