"""JSON output renderers.

Renders a list of `Paper` into JSON-serializable objects.
"""

from __future__ import annotations

from typing import Iterable

from PaperTracker.core.models import Paper


def render_json(papers: Iterable[Paper]) -> list[dict]:
    """Render papers into JSON-serializable Python objects.

    Args:
        papers: Iterable of papers.

    Returns:
        A list of dicts (datetime fields are converted to ISO strings).
    """
    out: list[dict] = []
    # Can not deepcopy MappingProxyType
    for paper in papers:
        d = {
            "source": paper.source,
            "id": paper.id,
            "title": paper.title,
            "authors": list(paper.authors),
            "summary": paper.summary,
            "published": paper.published.isoformat() if paper.published else None,
            "updated": paper.updated.isoformat() if paper.updated else None,
            "primary_category": paper.primary_category,
            "categories": list(paper.categories),
            "links": {
                "abstract": paper.links.abstract,
                "pdf": paper.links.pdf,
            },
            "extra": dict(paper.extra),
        }
        out.append(d)
    return out
