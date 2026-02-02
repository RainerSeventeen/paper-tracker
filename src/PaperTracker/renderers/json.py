"""JSON output renderers.

Renders a list of `Paper` into JSON-serializable objects.
Provides JsonFileWriter implementation for command output.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.renderers.base import OutputWriter
from PaperTracker.utils.log import log


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
            "abstract": paper.abstract,
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


class JsonFileWriter(OutputWriter):
    """Accumulate results and write to JSON file on finalize."""

    def __init__(self, output_dir: str) -> None:
        """Initialize JSON writer.

        Args:
            output_dir: Directory where to write output files.
        """
        self.output_dir = Path(output_dir)
        self.all_results: list[dict] = []

    def write_query_result(
        self,
        papers: list[Paper],
        query: SearchQuery,
        scope: SearchQuery | None,
    ) -> None:
        """Accumulate query result for later writing.

        Args:
            papers: List of papers found.
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
        output_path = self.output_dir / f"{action}_{timestamp}.json"
        output_path.write_text(payload, encoding="utf-8")
        log.info("JSON saved to %s", output_path)
