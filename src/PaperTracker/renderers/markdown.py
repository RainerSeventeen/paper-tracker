"""Markdown output renderers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence

from PaperTracker.config import OutputConfig
from PaperTracker.core.query import SearchQuery
from PaperTracker.renderers.base import OutputWriter
from PaperTracker.renderers.template_renderer import TemplateRenderer
from PaperTracker.renderers.template_utils import (
    OutputError,
    load_template,
    query_label,
)
from PaperTracker.renderers.view_models import PaperView
from PaperTracker.utils.log import log


@dataclass(frozen=True, slots=True)
class MarkdownRenderer:
    """Render paper views into Markdown content."""

    document_template: str
    paper_template: str
    paper_separator: str
    template_renderer: TemplateRenderer

    def render(self, papers: Sequence[PaperView], query_label: str, timestamp: str) -> str:
        """Render papers into a Markdown document.

        Args:
            papers: PaperView sequence.
            query_label: Query name for document header.
            timestamp: Timestamp string for document header.

        Returns:
            Rendered Markdown content.
        """
        paper_blocks: list[str] = []
        for idx, paper in enumerate(papers, start=1):
            context = _prepare_paper_context(paper, idx)
            paper_blocks.append(self.template_renderer.render_conditional(self.paper_template, context))

        papers_md = self.paper_separator.join(paper_blocks)
        document_context = {
            "timestamp": timestamp,
            "query": query_label,
            "papers": papers_md,
        }
        return self.template_renderer.render(self.document_template, document_context)

    def render_query_section(self, papers: Sequence[PaperView], query_label: str) -> str:
        """Render a single query section with its papers.

        Args:
            papers: PaperView sequence for this query.
            query_label: Query name for section header.

        Returns:
            Rendered query section content (without document wrapper).
        """
        paper_blocks: list[str] = []
        for idx, paper in enumerate(papers, start=1):
            context = _prepare_paper_context(paper, idx)
            paper_blocks.append(self.template_renderer.render_conditional(self.paper_template, context))

        papers_md = self.paper_separator.join(paper_blocks)

        # Render query section with header
        section = f"## 🔍 `{query_label}`\n\n{papers_md}"
        return section


class MarkdownFileWriter(OutputWriter):
    """Render markdown and write files on finalize."""

    def __init__(self, output_config: OutputConfig) -> None:
        """Initialize Markdown writer.

        Args:
            output_config: Output configuration.
        """
        self.output_dir = Path(output_config.base_dir) / "markdown"
        self.template_renderer = TemplateRenderer()
        self.renderer = MarkdownRenderer(
            document_template=load_template(
                output_config.markdown_template_dir,
                output_config.markdown_document_template,
            ),
            paper_template=load_template(
                output_config.markdown_template_dir,
                output_config.markdown_paper_template,
            ),
            paper_separator=output_config.markdown_paper_separator,
            template_renderer=self.template_renderer,
        )
        self.pending_sections: list[str] = []
        self.timestamp_dt: datetime | None = None

    def write_query_result(
        self,
        papers: list[PaperView],
        query: SearchQuery,
        scope: SearchQuery | None,
    ) -> None:
        """Render one query section and accumulate for finalize.

        Args:
            papers: List of paper views to display.
            query: The query that produced these results.
            scope: Optional global scope applied to the query.
        """
        # Record timestamp on first call
        if self.timestamp_dt is None:
            self.timestamp_dt = datetime.now()

        label = query_label(query)
        section = self.renderer.render_query_section(papers, query_label=label)
        self.pending_sections.append(section)

    def finalize(self, action: str) -> None:
        """Merge all query sections and write to a single markdown file.

        Args:
            action: The CLI command name (used in filename).
        """
        if not self.pending_sections:
            log.debug("No markdown sections to write")
            return

        # Use timestamp from first query, or generate new one if somehow missing
        timestamp_dt = self.timestamp_dt or datetime.now()
        timestamp_filename = timestamp_dt.strftime("%Y%m%d_%H%M%S")
        timestamp_display = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S")

        # Merge all query sections with separators
        query_separator = "\n\n---\n\n"
        all_sections = query_separator.join(self.pending_sections)

        # Build final document from configured template.
        final_content = self.template_renderer.render(
            self.renderer.document_template,
            {
                "timestamp": timestamp_display,
                "query": "all queries",
                "papers": all_sections,
                "query_sections": all_sections,
                "query_count": str(len(self.pending_sections)),
            },
        )

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OutputError(f"Failed to create output directory: {self.output_dir}") from exc

        filename = f"{action}_{timestamp_filename}.md"
        output_path = self.output_dir / filename
        try:
            output_path.write_text(final_content, encoding="utf-8")
        except OSError as exc:
            raise OutputError(f"Failed to write markdown file: {output_path}") from exc
        log.info("Markdown saved to %s", output_path)


def _prepare_paper_context(paper: PaperView, paper_number: int) -> Mapping[str, str]:
    """Prepare template context from PaperView."""
    return {
        "paper_number": str(paper_number),
        "title": paper.title or "",
        "source": paper.source or "",
        "authors": ", ".join(paper.authors) if paper.authors else "",
        "doi": paper.doi or "",
        "updated": paper.updated or paper.published or "",
        "primary_category": paper.primary_category or "",
        "categories": ", ".join(paper.categories) if paper.categories else "",
        "pdf_url": paper.pdf_url or "",
        "abstract_url": paper.abstract_url or "",
        "abstract": paper.abstract or "",
        "abstract_translation": paper.abstract_translation or "",
        "tldr": paper.tldr or "",
        "motivation": paper.motivation or "",
        "method": paper.method or "",
        "result": paper.result or "",
        "conclusion": paper.conclusion or "",
    }
