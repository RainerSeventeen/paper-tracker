"""arXiv 查询构造。

把 `SearchQuery` 中的关键词/分类/排除词转为 arXiv API 的 `search_query` 字符串。
"""

from __future__ import annotations

import re
from typing import Iterable


FIELDS = ("ti", "abs", "co")


def _quote(term: str) -> str:
    """Quote a search term when it contains whitespace/hyphen.

    Args:
        term: Raw keyword.

    Returns:
        Quoted term if needed.
    """
    t = term.strip()
    if re.search(r"[\s-]", t):
        return f'"{t}"'
    return t


def _field_or(fields: Iterable[str], term: str) -> str:
    """Build a field OR group for arXiv query.

    Args:
        fields: arXiv search fields (e.g. ti/abs/co).
        term: Search term.

    Returns:
        Query snippet like '(ti:"x" OR abs:"x")'.
    """
    q = _quote(term)
    return "(" + " OR ".join(f"{f}:{q}" for f in fields) + ")"


def _expand_variants(keyword: str) -> list[str]:
    """Generate simple keyword variants for better recall.

    Args:
        keyword: Keyword string.

    Returns:
        Variant keywords (space<->hyphen) ordered by length desc.
    """
    k = keyword.strip()
    out = {k}
    if " " in k:
        out.add(k.replace(" ", "-"))
    if "-" in k:
        out.add(k.replace("-", " "))
    return sorted(out, key=len, reverse=True)


def _kw_group(keyword: str) -> str:
    """Build query group for a single keyword.

    Args:
        keyword: Keyword string.

    Returns:
        A query group snippet for arXiv search_query.
    """
    variants = _expand_variants(keyword)
    parts: list[str] = []
    for v in variants:
        parts.append(_field_or(FIELDS, v))
    return "(" + " OR ".join(parts) + ")"


def build_search_query(
    *,
    categories: Iterable[str],
    keywords: Iterable[str],
    exclude_keywords: Iterable[str],
    logic: str,
) -> str:
    """Build arXiv API search_query string.

    Args:
        categories: arXiv categories like cs.CV.
        keywords: Keyword list.
        exclude_keywords: Exclusion keywords.
        logic: Logic between category group and keyword group (AND/OR).

    Returns:
        A search_query string suitable for arXiv API.
    """
    cats = [c.strip() for c in categories if c and c.strip()]
    keys = [k.strip() for k in keywords if k and k.strip()]
    excs = [e.strip() for e in exclude_keywords if e and e.strip()]

    cat_q = ""
    key_q = ""
    exc_q = ""

    if cats:
        cat_q = "(" + " OR ".join(f"cat:{c}" for c in cats) + ")"
    if keys:
        key_q = "(" + " OR ".join(_kw_group(k) for k in keys) + ")"

    if excs:
        exc_q = " AND NOT (" + " OR ".join(_kw_group(e) for e in excs) + ")"

    if cat_q and key_q:
        op = "AND" if (logic or "AND").upper() == "AND" else "OR"
        positive_q = f"({cat_q} {op} {key_q})"
    elif cat_q:
        positive_q = cat_q
    elif key_q:
        positive_q = key_q
    else:
        positive_q = "all:*"

    return positive_q + exc_q
