"""Tests for markdown file writer behavior."""

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from PaperTracker.config.output import OutputConfig
from PaperTracker.core.query import FieldQuery, SearchQuery
from PaperTracker.renderers.markdown import MarkdownFileWriter
from PaperTracker.renderers.view_models import PaperView


class TestMarkdownFileWriter(unittest.TestCase):
    def test_finalize_uses_configured_document_template(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temp_dir:
            temp_path = Path(temp_dir)
            template_dir = temp_path / "templates"
            output_base_dir = temp_path / "output"
            template_dir.mkdir(parents=True, exist_ok=True)

            (template_dir / "document.md").write_text(
                "CUSTOM DOCUMENT\nTIME: {timestamp}\n\n{papers}\n",
                encoding="utf-8",
            )
            (template_dir / "paper.md").write_text("### {paper_number}. {title}\n", encoding="utf-8")

            config = OutputConfig(
                base_dir=str(output_base_dir),
                formats=("markdown",),
                markdown_template_dir=str(template_dir.relative_to(REPO_ROOT)),
                markdown_document_template="document.md",
                markdown_paper_template="paper.md",
                markdown_paper_separator="\n\n---\n\n",
                html_template_dir="template/html/scholar",
                html_document_template="document.html",
                html_paper_template="paper.html",
            )

            writer = MarkdownFileWriter(config)
            writer.write_query_result(
                papers=[
                    PaperView(
                        source="arxiv",
                        id="1",
                        title="Template Driven Rendering",
                        authors=["Alice"],
                        abstract="sample",
                        published="2026-01-01",
                        updated=None,
                        primary_category=None,
                        categories=[],
                        abstract_url=None,
                        pdf_url=None,
                        doi=None,
                    )
                ],
                query=SearchQuery(name="q1", fields={"TEXT": FieldQuery(OR=["test"])}),
                scope=None,
            )
            writer.finalize("search")

            output_files = list((output_base_dir / "markdown").glob("search_*.md"))
            self.assertEqual(len(output_files), 1)
            content = output_files[0].read_text(encoding="utf-8")

            self.assertIn("CUSTOM DOCUMENT", content)
            self.assertIn("TIME:", content)
            self.assertIn("Template Driven Rendering", content)
            self.assertNotIn("# Paper Tracker Report", content)


if __name__ == "__main__":
    unittest.main()
