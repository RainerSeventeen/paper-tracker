# Project Coding Rules (Non-Obvious Only)

## Critical Patterns Discovered

- **Custom YAML parser**: [`config.py`](../../src/PaperTracker/config.py:171) implements minimal YAML subset - tabs forbidden, only spaces. No external YAML library dependency.
- **Config field case sensitivity**: Field keys (TITLE/ABSTRACT/AUTHOR/JOURNAL/CATEGORY) and operators (AND/OR/NOT) MUST be uppercase in YAML configs or validation fails.
- **CLI parameter restriction**: New parameters MUST go in YAML config files, NOT as CLI flags. CLI intentionally minimal by design.
- **Import order requirement**: All Python files MUST start with `from __future__ import annotations` as first import, followed by stdlib, then third-party, then local imports.
- **Absolute imports only**: Use `from PaperTracker.module import X` - relative imports forbidden.
- **Keyword auto-expansion**: [`query.py`](../../src/PaperTracker/sources/arxiv/query.py:49) automatically expands space/hyphen variants (e.g., "neural network" → "neural network" OR "neural-network").
- **TEXT field shorthand**: Top-level AND/OR/NOT in query config is syntactic sugar for TEXT field, which internally maps to `(ti OR abs)`.
- **JOURNAL field mapping**: Maps to `(jr OR co)` in arXiv API - best-effort only, not precise.
- **JSON output location**: JSON format writes to [`output/`](../../output/) directory with timestamp, NOT stdout.
- **arXiv retry mechanism**: [`client.py`](../../src/PaperTracker/sources/arxiv/client.py:104) has HTTPS→HTTP fallback with exponential backoff - configurable via env vars (ARXIV_TIMEOUT, ARXIV_MAX_ATTEMPTS, ARXIV_PAUSE, ARXIV_MAX_SLEEP).
