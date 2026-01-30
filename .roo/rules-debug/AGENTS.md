# Project Debug Rules (Non-Obvious Only)

## Hidden Debugging Context

- **Log level split**: Console output fixed at INFO level regardless of config; file logs respect configured level (DEBUG/INFO/etc). Set in [`log.py`](../../src/PaperTracker/utils/log.py:69).
- **Log abbreviations**: Log files use non-standard level names: DEBG/INFO/WARN/ERRO (not DEBUG/WARNING/ERROR). Defined in [`log.py`](../../src/PaperTracker/utils/log.py:15).
- **Log file location**: Logs written to `log/<action>/<action>_<MMDDHHMMSS>.log` - action is CLI command name (e.g., "search").
- **arXiv retry env vars**: Control retry behavior via environment variables:
  - `ARXIV_TIMEOUT` (default: 45s)
  - `ARXIV_MAX_ATTEMPTS` (default: 6)
  - `ARXIV_PAUSE` (default: 1.5s base)
  - `ARXIV_MAX_SLEEP` (default: 20s max backoff)
  - `ARXIV_UA` (custom User-Agent)
- **HTTPS→HTTP fallback**: [`client.py`](../../src/PaperTracker/sources/arxiv/client.py:82) tries HTTPS first, falls back to HTTP on failure - both attempts logged at DEBUG level.
- **Silent config errors**: Custom YAML parser in [`config.py`](../../src/PaperTracker/config.py:171) raises ValueError/TypeError on malformed config - check for tab characters (forbidden) and case sensitivity issues.
- **Query compilation debugging**: Enable DEBUG logging to see compiled arXiv search_query strings before API calls.
