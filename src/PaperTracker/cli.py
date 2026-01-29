"""PaperTracker command-line entry.

Parses CLI options, configures logging, calls the search service, and prints
results.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import click

from PaperTracker.config import AppConfig, load_config
from PaperTracker.core.query import SearchQuery
from PaperTracker.renderers.console import render_json, render_text
from PaperTracker.services.search import PaperSearchService
from PaperTracker.sources.arxiv.client import ArxivApiClient
from PaperTracker.sources.arxiv.source import ArxivSource
from PaperTracker.utils.log import configure_logging, log


@click.group(help="PaperTracker: search papers and print in terminal.")
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("config/default.yml"),
    show_default=True,
    help="Path to YAML config file.",
)
@click.pass_context
def cli(ctx: click.Context, config_path: Path) -> None:
    """CLI entry group.

    Args:
        ctx: Click context.
        config_path: Path to YAML config file.
    """
    cfg = load_config(config_path)
    ctx.obj = cfg
    configure_logging(level=cfg.log_level)


@cli.command("search")
@click.pass_context
def search_cmd(ctx: click.Context) -> None:
    """Search papers and print to console via logging.

    All parameters are read from the YAML config passed to the root command.

    Args:
        ctx: Click context.

    Raises:
        click.Abort: When the search fails.
    """
    cfg = ctx.obj
    configure_logging(
        level=cfg.log_level,
        action=ctx.command.name,
        log_to_file=cfg.log_to_file,
        log_dir=cfg.log_dir,
    )
    try:
        service = PaperSearchService(source=ArxivSource(client=ArxivApiClient(), scope=cfg.scope))

        def _fields_payload(q: SearchQuery) -> dict[str, dict[str, list[str]]]:
            return {
                k: {
                    "AND": list(v.AND),
                    "OR": list(v.OR),
                    "NOT": list(v.NOT),
                }
                for k, v in q.fields.items()
            }

        all_results: list[dict] = []
        multiple = len(cfg.queries) > 1

        for idx, query in enumerate(cfg.queries, start=1):
            log.debug("Running query %d/%d name=%s fields=%s", idx, len(cfg.queries), query.name, query.fields)
            if multiple:
                log.info("=== Query %d/%d ===", idx, len(cfg.queries))
            if cfg.scope:
                log.info("scope=%s", cfg.scope.fields)
            if query.name:
                log.info("name=%s", query.name)
            log.info("fields=%s", dict(query.fields))

            papers = service.search(
                query,
                max_results=cfg.max_results,
                sort_by=cfg.sort_by,
                sort_order=cfg.sort_order,
            )
            log.info("Fetched %d papers", len(papers))

            if cfg.output_format == "json":
                all_results.append(
                    {
                        "scope": _fields_payload(cfg.scope) if cfg.scope else None,
                        "name": query.name,
                        "fields": _fields_payload(query),
                        "papers": render_json(papers),
                    }
                )
            else:
                for line in render_text(papers).splitlines():
                    log.info(line)

        if cfg.output_format == "json":
            payload = json.dumps(all_results, ensure_ascii=False, indent=2)
            for line in payload.splitlines():
                log.info(line)
    except Exception as e:  # noqa: BLE001 - cli boundary
        log.error("Search failed: %s", e)
        raise click.Abort from e


def main() -> None:
    """Run PaperTracker CLI."""
    cli()
