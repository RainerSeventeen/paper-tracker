"""Console text output renderers.

Renders a list of `Paper` into human-friendly text.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from PaperTracker.core.models import Paper


def _fmt_dt(dt: datetime | None) -> str:
    """Format datetime for console output.

    Args:
        dt: A datetime object or None.

    Returns:
        A short date string (YYYY-mm-dd) or "-" when dt is None.
    """
    if not dt:
        return "-"
    return dt.strftime("%Y-%m-%d")


def render_text(papers: Iterable[Paper]) -> str:
    """Render papers into a human-readable text block.

    Args:
        papers: Iterable of papers.

    Returns:
        A formatted string ready to be printed.
    """
    lines: list[str] = []
    for idx, paper in enumerate(papers, start=1):
        authors = ", ".join(paper.authors)
        lines.append(f"{idx}. {paper.title}")
        lines.append(f"   Authors: {authors}")
        if paper.primary_category:
            lines.append(f"   Category: {paper.primary_category}")
        lines.append(f"   Published: {_fmt_dt(paper.published)}  Updated: {_fmt_dt(paper.updated)}")
        if paper.links.abstract:
            lines.append(f"   Abs: {paper.links.abstract}")
        if paper.links.pdf:
            lines.append(f"   PDF: {paper.links.pdf}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

