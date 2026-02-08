"""JSON output renderers.

Renders a list of `PaperView` into JSON-serializable objects.
Provides JsonFileWriter implementation for command output.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from PaperTracker.core.query import SearchQuery
from PaperTracker.renderers.base import OutputWriter
from PaperTracker.renderers.view_models import PaperView
from PaperTracker.utils.log import log


def render_json(papers: Iterable[PaperView]) -> list[dict]:
    """Render paper views into JSON-serializable Python objects.

    Args:
        papers: Iterable of paper views.

    Returns:
        A list of dicts with explicit LLM fields.
    """
    out: list[dict] = []
    for view in papers:
        d = {
            "source": view.source,
            "id": view.id,
            "title": view.title,
            "authors": list(view.authors),
            "abstract": view.abstract,
            "published": view.published,
            "updated": view.updated,
            "primary_category": view.primary_category,
            "categories": list(view.categories),
            "links": {
                "abstract": view.abstract_url,
                "pdf": view.pdf_url,
            },
            "doi": view.doi,
        }

        # Add LLM fields if present
        if view.abstract_translation:
            d["abstract_translation"] = view.abstract_translation

        summary_fields = {
            "tldr": view.tldr,
            "motivation": view.motivation,
            "method": view.method,
            "result": view.result,
            "conclusion": view.conclusion,
        }
        # Only include non-None summary fields
        summary_present = {k: v for k, v in summary_fields.items() if v is not None}
        if summary_present:
            d["summary"] = summary_present

        out.append(d)
    return out


class JsonFileWriter(OutputWriter):
    """Accumulate results and write to JSON file on finalize."""

    def __init__(self, base_dir: str) -> None:
        """Initialize JSON writer.

        Args:
            base_dir: Base output directory.
        """
        self.output_dir = Path(base_dir) / "json"
        self.all_results: list[dict] = []

    def write_query_result(
        self,
        papers: list[PaperView],
        query: SearchQuery,
        scope: SearchQuery | None,
    ) -> None:
        """Accumulate query result for later writing.

        Args:
            papers: List of paper views to display.
            query: The query that produced these results.
            scope: Optional global scope applied to the query.
        """
        self.all_results.append(
            {
                "scope": _fields_payload(scope) if scope else None,
                "name": query.name,
                "fields": _fields_payload(query),
                "papers": render_json(papers),
            }
        )

    def finalize(self, action: str) -> None:
        """Write accumulated results to JSON file.

        Args:
            action: The CLI command name (used in filename).
        """
        payload = json.dumps(self.all_results, ensure_ascii=False, indent=2)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{action}_{timestamp}.json"
        output_path = self.output_dir / filename
        output_path.write_text(payload, encoding="utf-8")
        log.info("JSON saved to %s", output_path)


def _fields_payload(q: SearchQuery) -> dict[str, dict[str, list[str]]]:
    """Convert search query fields to payload format.

    Args:
        q: SearchQuery to convert.

    Returns:
        Dictionary mapping field names to operator->terms mappings.
    """
    return {
        k: {
            "AND": list(v.AND),
            "OR": list(v.OR),
            "NOT": list(v.NOT),
        }
        for k, v in q.fields.items()
    }
