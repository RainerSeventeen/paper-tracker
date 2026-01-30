# Project Documentation Rules (Non-Obvious Only)

## Hidden Context & Counterintuitive Structure

- **Dual documentation languages**: README.md in Chinese, code comments/docstrings in English. [`configuration.md`](../../docs/configuration.md:1) also in Chinese.
- **Config schema documentation**: [`docs/configuration.md`](../../docs/configuration.md:1) is canonical reference for YAML structure - must be updated when config schema changes.
- **arXiv API details**: [`docs/arxiv-api-query.md`](../../docs/arxiv-api-query.md:1) contains arXiv-specific query syntax mapping - consult when modifying [`query.py`](../../src/PaperTracker/sources/arxiv/query.py:1).
- **TEXT field is synthetic**: TEXT field doesn't exist in arXiv API - it's internal shorthand that expands to `(ti OR abs)` during compilation.
- **JOURNAL field limitation**: JOURNAL maps to `(jr OR co)` in arXiv - not precise, documented as "best-effort" in [`query.py`](../../src/PaperTracker/sources/arxiv/query.py:19).
- **Scope vs Query relationship**: `scope` in config is global filter ANDed with every query - not immediately obvious from YAML structure.
- **Output format behavior**: `format: json` writes to [`output/`](../../output/) directory, NOT stdout; `format: text` logs to console via logging system.
- **Original project reference**: This is a rewrite from scratch of https://github.com/colorfulandcjy0806/Arxiv-tracker - original in [`Arxiv-tracker/`](../../Arxiv-tracker/) submodule for reference only.
- **Package structure**: Entry point is [`cli.py`](../../src/PaperTracker/cli.py:1) but can also run as `python -m PaperTracker` via [`__main__.py`](../../src/PaperTracker/__main__.py:1).
