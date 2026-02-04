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
from PaperTracker.renderers.view_models import PaperView
from PaperTracker.utils.log import log


class TemplateNotFoundError(FileNotFoundError):
    """Raised when a template file cannot be found."""


class TemplateError(RuntimeError):
    """Raised when a template cannot be loaded."""


class OutputError(RuntimeError):
    """Raised when output cannot be written."""


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
            document_template=_load_template(
                output_config.markdown_template_dir,
                output_config.markdown_document_template,
            ),
            paper_template=_load_template(
                output_config.markdown_template_dir,
                output_config.markdown_paper_template,
            ),
            paper_separator=output_config.markdown_paper_separator,
            template_renderer=self.template_renderer,
        )
        self.pending_outputs: list[tuple[str, str]] = []

    def write_query_result(
        self,
        papers: list[PaperView],
        query: SearchQuery,
        scope: SearchQuery | None,
    ) -> None:
        """Render one query and store output for finalize.

        Args:
            papers: List of paper views to display.
            query: The query that produced these results.
            scope: Optional global scope applied to the query.
        """
        query_label = _query_label(query)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rendered = self.renderer.render(papers, query_label=query_label, timestamp=timestamp)
        self.pending_outputs.append((rendered, timestamp))

    def finalize(self, action: str) -> None:
        """Write all rendered markdown documents to disk.

        Args:
            action: The CLI command name (used in filename).
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OutputError(f"Failed to create output directory: {self.output_dir}") from exc

        for content, timestamp in self.pending_outputs:
            filename = f"{action}_{timestamp}.md"
            output_path = self.output_dir / filename
            try:
                output_path.write_text(content, encoding="utf-8")
            except OSError as exc:
                raise OutputError(f"Failed to write markdown file: {output_path}") from exc
            log.info("Markdown saved to %s", output_path)


def _load_template(template_dir: str, filename: str) -> str:
    """Load a template file from the configured directory."""
    root = Path.cwd().resolve()
    base_dir = Path(template_dir)
    if not base_dir.is_absolute():
        base_dir = root / base_dir
    template_path = (base_dir / filename).resolve()
    try:
        template_path.relative_to(root)
    except ValueError as exc:
        raise TemplateError(f"Template path must be inside project root: {template_path}") from exc

    if not template_path.exists():
        raise TemplateNotFoundError(f"Template file not found: {template_path}")

    try:
        return template_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TemplateError(f"Failed to read template: {template_path}") from exc


def _query_label(query: SearchQuery) -> str:
    """Return a human-readable label for the query."""
    if query.name:
        return query.name
    return "query"


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
