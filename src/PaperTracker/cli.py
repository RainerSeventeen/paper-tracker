"""PaperTracker command-line entry.

Parses CLI options, configures logging, calls the search service, and prints
results.
"""

from __future__ import annotations

import json
from typing import Sequence

import click

from PaperTracker.core.query import SearchQuery
from PaperTracker.renderers.console import render_json, render_text
from PaperTracker.services.search import PaperSearchService
from PaperTracker.sources.arxiv.client import ArxivApiClient
from PaperTracker.sources.arxiv.source import ArxivSource
from PaperTracker.utils.log import configure_logging, log


def _split_multi(values: Sequence[str] | None) -> list[str]:
    """Split multi-value CLI options.

    Accepts repeated values and also supports comma/semicolon separated items.

    Args:
        values: Sequence of raw option strings.

    Returns:
        Flattened list of non-empty items.
    """
    out: list[str] = []
    for v in values or []:
        if not v:
            continue
        for part in v.replace(";", ",").split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


@click.group(help="PaperTracker: search papers and print in terminal.")
@click.option(
    "--log-level",
    type=click.Choice(["DEBG", "INFO", "WARN", "ERRO"], case_sensitive=False),
    default="INFO",
    show_default=True,
)
def cli(log_level: str) -> None:
    """CLI entry group.

    Args:
        log_level: One of DEBG/INFO/WARN/ERRO.
    """
    level_map = {
        "DEBG": "DEBUG",
        "INFO": "INFO",
        "WARN": "WARNING",
        "ERRO": "ERROR",
    }
    configure_logging(level=level_map.get(log_level.upper(), "INFO"))


@cli.command("search")
@click.option("--keyword", "keywords", multiple=True, required=True, help="Keyword; can repeat or comma-separate")
@click.option("--category", "categories", multiple=True, help="arXiv category like cs.CV; can repeat")
@click.option("--exclude", "exclude_keywords", multiple=True, help="Exclude keyword; can repeat")
@click.option("--logic", type=click.Choice(["AND", "OR"], case_sensitive=False), default="AND")
@click.option("--max-results", type=int, default=20, show_default=True)
@click.option(
    "--sort-by",
    type=click.Choice(["submittedDate", "lastUpdatedDate"], case_sensitive=False),
    default="submittedDate",
    show_default=True,
)
@click.option(
    "--sort-order",
    type=click.Choice(["ascending", "descending"], case_sensitive=False),
    default="descending",
    show_default=True,
)
@click.option("--format", "fmt", type=click.Choice(["text", "json"], case_sensitive=False), default="text")
def search_cmd(
    keywords: Sequence[str],
    categories: Sequence[str],
    exclude_keywords: Sequence[str],
    logic: str,
    max_results: int,
    sort_by: str,
    sort_order: str,
    fmt: str,
) -> None:
    """Search papers and print to console via logging.

    Args:
        keywords: Keyword list; can be repeated or comma-separated.
        categories: arXiv categories; can be repeated or comma-separated.
        exclude_keywords: Exclusion keywords; can be repeated or comma-separated.
        logic: Logic between category-group and keyword-group (AND/OR).
        max_results: Maximum number of papers.
        sort_by: Sort field.
        sort_order: Sort order.
        fmt: Output format (text/json).

    Raises:
        click.Abort: When the search fails.
    """
    try:
        query = SearchQuery(
            keywords=_split_multi(keywords),
            categories=_split_multi(categories),
            exclude_keywords=_split_multi(exclude_keywords),
            logic=logic.upper(),
        )

        log.info(
            "Query keywords=%s categories=%s exclude=%s logic=%s",
            list(query.keywords),
            list(query.categories),
            list(query.exclude_keywords),
            query.logic,
        )

        service = PaperSearchService(source=ArxivSource(client=ArxivApiClient()))
        papers = service.search(query, max_results=max_results, sort_by=sort_by, sort_order=sort_order)
        log.info("Fetched %d papers", len(papers))

        if fmt.lower() == "json":
            payload = json.dumps(render_json(papers), ensure_ascii=False, indent=2)
            for line in payload.splitlines():
                log.info(line)
        else:
            for line in render_text(papers).splitlines():
                log.info(line)
    except Exception as e:  # noqa: BLE001 - cli boundary
        log.error("Search failed: %s", e)
        raise click.Abort from e


def main() -> None:
    """Run PaperTracker CLI."""
    cli()
