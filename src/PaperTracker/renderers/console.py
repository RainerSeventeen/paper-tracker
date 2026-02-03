"""Console text output renderers.

Renders a list of `Paper` into human-friendly text.
Provides ConsoleOutputWriter implementation for command output.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.renderers.base import OutputWriter
from PaperTracker.utils.log import log


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

        # Display translation if available
        if "translation" in paper.extra:
            trans = paper.extra["translation"]
            if trans.get("summary_translated"):
                lines.append(f"   Abs Translation: {trans['summary_translated']}")

        # Display summary if available
        if "summary" in paper.extra:
            summary = paper.extra["summary"]
            lines.append("   --- Summary ---")
            if summary.get("tldr"):
                lines.append(f"   TLDR: {summary['tldr']}")
            if summary.get("motivation"):
                lines.append(f"   Motivation: {summary['motivation']}")
            if summary.get("method"):
                lines.append(f"   Method: {summary['method']}")
            if summary.get("result"):
                lines.append(f"   Result: {summary['result']}")
            if summary.get("conclusion"):
                lines.append(f"   Conclusion: {summary['conclusion']}")

        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


class ConsoleOutputWriter(OutputWriter):
    """Write results to console via logging."""

    def write_query_result(
        self,
        papers: list[Paper],
        query: SearchQuery,
        scope: SearchQuery | None,
    ) -> None:
        """Write query result to console.

        Args:
            papers: List of papers found.
            query: The query that produced these results.
            scope: Optional global scope applied to the query.
        """
        for line in render_text(papers).splitlines():
            log.info(line)

    def finalize(self, action: str) -> None:
        """No-op for console output."""

