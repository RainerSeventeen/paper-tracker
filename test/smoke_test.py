"""Smoke test for PaperTracker CLI.

Run:
  python test/smoke_test.py

This script patches the arXiv HTTP client to avoid network access and validates
that the CLI can execute a basic query and render at least one result.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))


SMOKE_XML = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <title type="text">arXiv Query: smoke</title>
  <id>http://arxiv.org/api/</id>
  <updated>2020-01-02T00:00:00Z</updated>
  <entry>
    <id>http://arxiv.org/abs/1234.5678v1</id>
    <updated>2020-01-02T00:00:00Z</updated>
    <published>2020-01-01T00:00:00Z</published>
    <title>Smoke Test Paper</title>
    <summary>Just a test.</summary>
    <author>
      <name>Alice Example</name>
    </author>
    <link rel="alternate" type="text/html" href="http://arxiv.org/abs/1234.5678v1"/>
    <link title="pdf" rel="related" type="application/pdf" href="http://arxiv.org/pdf/1234.5678v1"/>
    <arxiv:primary_category term="cs.CV" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.CV" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>
"""


def _make_runner() -> CliRunner:
    """Create CliRunner with best-effort stderr capture."""
    try:
        return CliRunner(mix_stderr=True)
    except TypeError:
        # Older Click versions don't support mix_stderr.
        return CliRunner()


def main() -> int:
    from PaperTracker.cli import cli

    runner = _make_runner()
    with patch("PaperTracker.sources.arxiv.client.ArxivApiClient.fetch_feed", return_value=SMOKE_XML):
        result = runner.invoke(
            cli,
            [
                "search",
                "--keyword",
                "diffusion",
                "--max-results",
                "1",
                "--format",
                "text",
            ],
            catch_exceptions=False,
        )

    output = result.output
    assert result.exit_code == 0, output
    assert "Fetched 1 papers" in output, output
    assert "Smoke Test Paper" in output, output
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

