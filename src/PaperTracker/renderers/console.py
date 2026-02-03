"""Console text output renderers.

Renders a list of `PaperView` into human-friendly text.
Provides ConsoleOutputWriter implementation for command output.
"""

from __future__ import annotations

from typing import Iterable

from PaperTracker.core.query import SearchQuery
from PaperTracker.renderers.base import OutputWriter
from PaperTracker.renderers.view_models import PaperView
from PaperTracker.utils.log import log


def render_text(papers: Iterable[PaperView]) -> str:
    """Render paper views into a human-readable text block.

    Args:
        papers: Iterable of paper views.

    Returns:
        A formatted string ready to be printed.
    """
    lines: list[str] = []
    for idx, view in enumerate(papers, start=1):
        authors = ", ".join(view.authors)
        lines.append(f"{idx}. {view.title}")
        lines.append(f"   Authors: {authors}")
        if view.primary_category:
            lines.append(f"   Category: {view.primary_category}")
        lines.append(f"   Published: {view.published or '-'}  Updated: {view.updated or '-'}")
        if view.abstract_url:
            lines.append(f"   Abs: {view.abstract_url}")
        if view.pdf_url:
            lines.append(f"   PDF: {view.pdf_url}")

        # Display translation if available
        if view.abstract_translation:
            lines.append(f"   Abs Translation: {view.abstract_translation}")

        # Display summary if available
        if any([view.tldr, view.motivation, view.method, view.result, view.conclusion]):
            lines.append("   --- Summary ---")
            if view.tldr:
                lines.append(f"   TLDR: {view.tldr}")
            if view.motivation:
                lines.append(f"   Motivation: {view.motivation}")
            if view.method:
                lines.append(f"   Method: {view.method}")
            if view.result:
                lines.append(f"   Result: {view.result}")
            if view.conclusion:
                lines.append(f"   Conclusion: {view.conclusion}")

        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


class ConsoleOutputWriter(OutputWriter):
    """Write results to console via logging."""

    def write_query_result(
        self,
        papers: list[PaperView],
        query: SearchQuery,
        scope: SearchQuery | None,
    ) -> None:
        """Write query result to console.

        Args:
            papers: List of paper views to display.
            query: The query that produced these results.
            scope: Optional global scope applied to the query.
        """
        for line in render_text(papers).splitlines():
            log.info(line)

    def finalize(self, action: str) -> None:
        """No-op for console output."""

