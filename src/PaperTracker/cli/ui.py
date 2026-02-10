"""Click CLI interface definitions.

Defines the command-line interface structure and routes commands
to their respective runners.
"""

from __future__ import annotations

from pathlib import Path

import click
from dotenv import load_dotenv

from PaperTracker.cli.runner import CommandRunner
from PaperTracker.config import load_config_with_defaults


@click.group(help="PaperTracker: search papers and print in terminal.")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """CLI entry group.

    Loads environment variables from .env file.

    Args:
        ctx: Click context.
    """
    # Load environment variables from .env file
    load_dotenv()


@cli.command("search")
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("config/default.yml"),
    show_default=True,
    help="Path to YAML config file (overrides defaults).",
)
@click.pass_context
def search_cmd(ctx: click.Context, config_path: Path) -> None:
    """Search papers and print to console via logging.

    All parameters are read from the YAML config.

    Args:
        ctx: Click context.
        config_path: Path to YAML config file.

    Raises:
        click.Abort: When the search fails.
    """
    cfg = load_config_with_defaults(config_path)
    runner = CommandRunner(cfg)
    runner.run_search(action=ctx.command.name)
