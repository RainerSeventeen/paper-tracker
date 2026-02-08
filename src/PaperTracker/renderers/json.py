"""JSON output renderers.

Renders a list of `PaperView` into JSON-serializable objects.
Provides JsonFileWriter implementation for command output.
Also provides functions to read JSON files back into PaperView objects.
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


def load_json(json_data: dict) -> PaperView:
    """Load a single paper from JSON dict into PaperView.

    Args:
        json_data: Dictionary containing paper data in JSON format.

    Returns:
        PaperView object reconstructed from JSON data.
    """
    # Extract summary fields if present
    summary = json_data.get("summary", {})

    # Extract links
    links = json_data.get("links", {})

    return PaperView(
        source=json_data["source"],
        id=json_data["id"],
        title=json_data["title"],
        authors=json_data["authors"],
        abstract=json_data["abstract"],
        published=json_data.get("published"),
        updated=json_data.get("updated"),
        primary_category=json_data.get("primary_category"),
        categories=json_data.get("categories", []),
        abstract_url=links.get("abstract"),
        pdf_url=links.get("pdf"),
        doi=json_data.get("doi"),
        abstract_translation=json_data.get("abstract_translation"),
        tldr=summary.get("tldr"),
        motivation=summary.get("motivation"),
        method=summary.get("method"),
        result=summary.get("result"),
        conclusion=summary.get("conclusion"),
    )


def load_json_file(filepath: str | Path) -> list[PaperView]:
    """Load papers from a JSON file.

    The JSON file should contain an array of query results, where each result
    has a "papers" field containing paper objects.

    Args:
        filepath: Path to the JSON file.

    Returns:
        List of PaperView objects from all queries in the file.
    """
    path = Path(filepath)
    content = path.read_text(encoding="utf-8")
    data = json.loads(content)

    papers = []
    # Handle both formats: direct list of papers or query results
    if isinstance(data, list) and len(data) > 0:
        # Check if it's a list of query results
        if isinstance(data[0], dict) and "papers" in data[0]:
            # Extract papers from each query result
            for query_result in data:
                for paper_data in query_result["papers"]:
                    papers.append(load_json(paper_data))
        # Or a direct list of papers
        elif isinstance(data[0], dict) and "source" in data[0]:
            for paper_data in data:
                papers.append(load_json(paper_data))

    log.info("Loaded %d papers from %s", len(papers), path)
    return papers


def load_query_results(filepath: str | Path) -> list[tuple[SearchQuery, list[PaperView]]]:
    """Load complete query results from a JSON file.

    Reconstructs both the SearchQuery objects and their corresponding papers
    from the JSON file, preserving the original query structure.

    Args:
        filepath: Path to the JSON file.

    Returns:
        List of tuples, each containing (SearchQuery, list of PaperView).
    """
    from PaperTracker.core.query import FieldQuery

    path = Path(filepath)
    content = path.read_text(encoding="utf-8")
    data = json.loads(content)

    results = []

    if isinstance(data, list):
        for query_result in data:
            if not isinstance(query_result, dict) or "papers" not in query_result:
                continue

            # Reconstruct SearchQuery from fields
            fields = {}
            if "fields" in query_result and query_result["fields"]:
                for field_name, field_data in query_result["fields"].items():
                    fields[field_name] = FieldQuery(
                        AND=tuple(field_data.get("AND", [])),
                        OR=tuple(field_data.get("OR", [])),
                        NOT=tuple(field_data.get("NOT", []))
                    )

            query = SearchQuery(
                name=query_result.get("name", "Unnamed Query"),
                fields=fields
            )

            # Load papers for this query
            papers = [load_json(paper_data) for paper_data in query_result["papers"]]

            results.append((query, papers))

    log.info("Loaded %d queries with %d total papers from %s",
             len(results), sum(len(papers) for _, papers in results), path)

    return results
