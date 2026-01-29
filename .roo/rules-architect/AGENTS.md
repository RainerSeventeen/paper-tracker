# Project Architecture Rules (Non-Obvious Only)

## Hidden Architectural Constraints

- **Service layer abstraction**: [`PaperSource`](../../src/PaperTracker/services/search.py:17) is Protocol-based (structural typing) - sources must implement `search()` method but don't inherit from base class.
- **Query compilation separation**: Query structure in [`core/query.py`](../../src/PaperTracker/core/query.py:1) is source-agnostic; each source (e.g., arXiv) has its own compiler in `sources/<name>/query.py`.
- **Scope merging strategy**: Global `scope` from config is ANDed with each query during compilation in [`query.py`](../../src/PaperTracker/sources/arxiv/query.py:107) - not merged at config level.
- **Renderer independence**: Renderers in [`renderers/`](../../src/PaperTracker/renderers/) operate on domain models ([`Paper`](../../src/PaperTracker/core/models.py:1)), not source-specific data - enables multi-source support.
- **Frozen dataclasses everywhere**: All models use `@dataclass(frozen=True, slots=True)` for immutability and memory efficiency - don't add mutable state.
- **No dependency injection framework**: Dependencies manually wired in [`cli.py`](../../src/PaperTracker/cli.py:67) - intentionally simple, no DI container.
- **Config parsing is custom**: [`config.py`](../../src/PaperTracker/config.py:171) implements minimal YAML subset to avoid external dependencies - limited feature set by design.
- **Logging is centralized**: Single logger instance `log` from [`utils/log.py`](../../src/PaperTracker/utils/log.py:38) used throughout - don't create module-level loggers.
- **Click context passing**: Config loaded once in CLI group, passed via Click context to subcommands - don't reload config in subcommands.
- **Atom feed parsing**: Uses `feedparser` library for arXiv XML - parser in [`parser.py`](../../src/PaperTracker/sources/arxiv/parser.py:1) handles feed-to-domain mapping.
