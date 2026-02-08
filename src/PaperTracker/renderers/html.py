"""HTML output renderers."""

from __future__ import annotations

import html
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence
from urllib.parse import urlparse

from PaperTracker.config import OutputConfig
from PaperTracker.core.query import SearchQuery
from PaperTracker.renderers.base import OutputWriter
from PaperTracker.renderers.markdown import (
    OutputError,
    TemplateError,
    TemplateNotFoundError,
    _load_template,
    _query_label,
)
from PaperTracker.renderers.template_renderer import TemplateRenderer
from PaperTracker.renderers.view_models import PaperView
from PaperTracker.utils.log import log


@dataclass(frozen=True, slots=True)
class HtmlRenderer:
    """Render paper views into HTML content."""

    document_template: str
    paper_template: str
    template_renderer: TemplateRenderer

    def render_query_section(self, papers: Sequence[PaperView], query_label: str, query_id: str) -> str:
        """Render one query section.

        Args:
            papers: Sequence of papers.
            query_label: Query label shown in heading.
            query_id: Unique DOM id for section.

        Returns:
            HTML section string.
        """
        paper_blocks: list[str] = []
        for idx, paper in enumerate(papers, start=1):
            context = _prepare_paper_context_html(paper, idx)
            paper_blocks.append(self.template_renderer.render_conditional(self.paper_template, context))

        papers_html = "\n".join(paper_blocks)
        if not papers_html:
            papers_html = '<p class="empty-state">该 query 暂无结果。</p>'

        safe_query_label = html.escape(query_label)
        safe_query_label_attr = html.escape(query_label, quote=True)
        paper_count = len(papers)
        section = (
            f'<section id="{query_id}" class="query-section"'
            f' data-query-label="{safe_query_label_attr}"'
            f' data-paper-count="{paper_count}">\n'
        )
        section += "  <header class=\"query-header\">\n"
        section += f"    <h2>{safe_query_label}</h2>\n"
        section += f"    <p class=\"query-count\">{paper_count} 篇</p>\n"
        section += "  </header>\n"
        section += f"  <div class=\"query-content\">\n{papers_html}\n  </div>\n"
        section += "</section>"
        return section


class HtmlFileWriter(OutputWriter):
    """Render HTML and write files during finalization."""

    def __init__(self, output_config: OutputConfig) -> None:
        """Initialize HTML file writer.

        Args:
            output_config: Output configuration.
        """
        self.output_dir = Path(output_config.base_dir) / "html"
        self.template_dir = self._resolve_template_dir(output_config.html_template_dir)
        self.assets_dir = self.template_dir / "assets"

        self.template_renderer = TemplateRenderer()
        self.renderer = HtmlRenderer(
            document_template=_load_template(
                output_config.html_template_dir,
                output_config.html_document_template,
            ),
            paper_template=_load_template(
                output_config.html_template_dir,
                output_config.html_paper_template,
            ),
            template_renderer=self.template_renderer,
        )
        self.pending_sections: list[str] = []
        self.timestamp_dt: datetime | None = None
        self.query_id_counter: dict[str, int] = {}
        self.total_papers = 0

    def write_query_result(
        self,
        papers: list[PaperView],
        query: SearchQuery,
        scope: SearchQuery | None,
    ) -> None:
        """Render a query result section and queue it.

        Args:
            papers: List of paper views to display.
            query: Query used for this result.
            scope: Optional scope query.
        """
        del scope
        if self.timestamp_dt is None:
            self.timestamp_dt = datetime.now()

        query_label = _query_label(query)
        query_id = self._get_query_id(query_label)
        section = self.renderer.render_query_section(papers, query_label=query_label, query_id=query_id)
        self.pending_sections.append(section)
        self.total_papers += len(papers)

    def finalize(self, action: str) -> None:
        """Write final HTML document and synchronize assets.

        Args:
            action: CLI action name.

        Raises:
            OutputError: If output directory or file writing fails.
        """
        if not self.pending_sections:
            log.debug("No HTML sections to write")
            return

        timestamp_dt = self.timestamp_dt or datetime.now()
        timestamp_filename = timestamp_dt.strftime("%Y%m%d_%H%M%S")
        timestamp_display = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S")

        all_sections = "\n\n".join(self.pending_sections)
        final_content = self.template_renderer.render(
            self.renderer.document_template,
            {
                "timestamp": timestamp_display,
                "query_count": str(len(self.pending_sections)),
                "paper_count": str(self.total_papers),
                "query_sections": all_sections,
            },
        )

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OutputError(f"Failed to create output directory: {self.output_dir}") from exc

        filename = f"{action}_{timestamp_filename}.html"
        output_path = self.output_dir / filename
        try:
            output_path.write_text(final_content, encoding="utf-8")
        except OSError as exc:
            raise OutputError(f"Failed to write HTML file: {output_path}") from exc

        log.info("HTML saved to %s", output_path)
        self._copy_assets()

    def _get_query_id(self, query_label: str) -> str:
        """Generate a unique DOM id from query label.

        Args:
            query_label: Query label.

        Returns:
            Unique query section id.
        """
        slug = _slugify(query_label)
        count = self.query_id_counter.get(slug, 0) + 1
        self.query_id_counter[slug] = count
        if count == 1:
            return f"query-{slug}"
        return f"query-{slug}-{count}"

    def _copy_assets(self) -> None:
        """Copy template assets into output directory when changed."""
        if not self.assets_dir.exists():
            log.debug("No assets directory in template, skipping")
            return

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            dest_assets = self.output_dir / "assets"
            dest_assets.mkdir(exist_ok=True)
        except OSError as exc:
            log.warning("Failed to prepare assets directory: %s", exc)
            return

        for src_file in self.assets_dir.iterdir():
            if not src_file.is_file():
                continue

            dest_file = dest_assets / src_file.name
            try:
                if dest_file.exists() and src_file.stat().st_mtime <= dest_file.stat().st_mtime:
                    continue
                shutil.copy2(src_file, dest_file)
                log.debug("Copied asset: %s", src_file.name)
            except OSError as exc:
                log.warning("Failed to copy asset %s: %s", src_file.name, exc)

    def _resolve_template_dir(self, template_dir: str) -> Path:
        """Resolve template directory relative to project root.

        Args:
            template_dir: Configured template directory.

        Returns:
            Resolved template directory.

        Raises:
            TemplateError: If template path escapes repository root.
            TemplateNotFoundError: If template directory does not exist.
        """
        root = Path.cwd().resolve()
        base_dir = Path(template_dir)
        if not base_dir.is_absolute():
            base_dir = root / base_dir
        resolved = base_dir.resolve()

        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise TemplateError(f"Template path must be inside project root: {resolved}") from exc

        if not resolved.exists() or not resolved.is_dir():
            raise TemplateNotFoundError(f"Template directory not found: {resolved}")
        return resolved


def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug.

    Args:
        text: Source text.

    Returns:
        Slug string with only ``a-z``, ``0-9`` and ``-``.
    """
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug or "query"


def _escape_url(url: str) -> str:
    """Validate and escape URLs used in HTML attributes.

    Args:
        url: Raw URL.

    Returns:
        Escaped URL when valid, or an empty string.
    """
    if not url:
        return ""

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        log.warning("Disallowed URL scheme: %s (URL: %s)", parsed.scheme, url)
        return ""
    return html.escape(url, quote=True)


def _prepare_paper_context_html(paper: PaperView, paper_number: int) -> Mapping[str, str]:
    """Prepare escaped template context from a paper view.

    Args:
        paper: Paper view model.
        paper_number: Sequence number in query section.

    Returns:
        Placeholder mapping used by templates.
    """
    doi_url = _build_doi_url(paper.doi)
    pdf_url = _escape_url(paper.pdf_url or "")
    abstract_url = _escape_url(paper.abstract_url or "")
    has_links = bool(pdf_url or abstract_url or doi_url)

    return {
        "paper_number": str(paper_number),
        "title": html.escape(paper.title or ""),
        "source": html.escape(paper.source or ""),
        "authors": html.escape(", ".join(paper.authors) if paper.authors else ""),
        "doi": html.escape(paper.doi or ""),
        "doi_url": doi_url,
        "updated": html.escape(paper.updated or paper.published or ""),
        "primary_category": html.escape(paper.primary_category or ""),
        "categories": html.escape(", ".join(paper.categories) if paper.categories else ""),
        "pdf_url": pdf_url,
        "abstract_url": abstract_url,
        "links_state": "has-links" if has_links else "no-links",
        "abstract": html.escape(paper.abstract or ""),
        "abstract_translation": html.escape(paper.abstract_translation or ""),
        "tldr": html.escape(paper.tldr or ""),
        "motivation": html.escape(paper.motivation or ""),
        "method": html.escape(paper.method or ""),
        "result": html.escape(paper.result or ""),
        "conclusion": html.escape(paper.conclusion or ""),
    }


def _build_doi_url(doi: str | None) -> str:
    """Build an escaped DOI URL from a DOI string.

    Args:
        doi: Raw DOI string or URL.

    Returns:
        Validated DOI URL, or empty string when DOI is missing/invalid.
    """
    if not doi:
        return ""

    normalized = doi.strip()
    if not normalized:
        return ""

    if normalized.startswith(("http://", "https://")):
        return _escape_url(normalized)

    return _escape_url(f"https://doi.org/{normalized}")
