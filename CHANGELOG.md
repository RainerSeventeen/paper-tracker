# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Versioning Policy

- **PATCH** (0.1.x): Bug fixes, documentation updates, minor improvements with no API change
- **MINOR** (0.x.0): New features or breaking changes to configuration schema, CLI interface, or core pipeline — during `0.x` development, breaking changes bump MINOR rather than MAJOR
- **MAJOR** (1.0.0+): Declared stable release; breaking changes after `1.0.0` bump MAJOR per standard SemVer

A version bump is triggered when: a feature branch is merged to `main` and the change is user-visible or API-significant.

---

## [0.2.0] - 2026-05-07

### Added

- **PubMed source**: NCBI E-utilities integration with ESearch and EFetch support for biomedical literature retrieval
- **PubMed query compiler**: field-aware query conversion for title, abstract, author, journal, and category-style inputs
- **PubMed parser**: article metadata extraction for titles, abstracts, authors, journals, publication dates, DOIs, and links
- **PubMed fetch strategy**: paginated retrieval with rate limiting, timeout protection, source-local deduplication, and deterministic ordering
- **PubMed configuration**: source registration, default settings, example configuration, and optional `NCBI_API_KEY` environment support
- **PubMed documentation**: Chinese and English query guides plus README feature coverage for PubMed usage

### Changed

- **Multi-source retrieval**: expands the supported source set from arXiv and OpenAlex to arXiv, OpenAlex, and PubMed

## [0.1.0] - 2026-04-27

### Added

- **arXiv query engine**: keyword-based search with field selectors (`TITLE`, `ABSTRACT`, `AUTHOR`, `JOURNAL`, `CATEGORY`) and logical operators (`AND`, `OR`, `NOT`); global `scope` support
- **Multi-fetch pipeline**: pull additional older papers to fulfill a target count when recent results are insufficient
- **SQLite deduplication and storage**: deduplicate papers across runs; persist paper content for later retrieval
- **SQLite schema migration**: centralized schema versioning with automatic migration on startup
- **Output formats**: `json`, `markdown`, `html`; template-based rendering with replaceable templates
- **LLM integration**: OpenAI-compatible API support for abstract translation and structured summary; configurable `target_lang`
- **LLM reliability**: configurable retry mechanism with exponential backoff for API call failures; skip enrichment when abstract is missing
- **Config override system**: layered configuration with internal defaults and user override YAML; defaults bundled as package resource via `importlib.resources`
- **OpenAlex source**: multi-round fetching with time window filtering, language filter, and relevance filter
- **Multi-source pipeline**: simultaneous arXiv + OpenAlex search with cross-source deduplication
- **Weekly publish automation**: shell script for scheduled tracking and HTML page publishing
- **macOS automation script**: system-level scheduling support for periodic runs

### Fixed

- arXiv API 429 (rate limit) handling
- Papers marked as seen before content persistence was applied
- Config layering and output pipeline normalization
- LLM config decoupled from storage config
- arXiv source-level dedup and multi-round stop signal restored after multi-source refactor
- OpenAlex query compilation scoped to title/abstract fields only to reduce irrelevant results

[0.2.0]: https://github.com/rainerseventeen/paper-tracker/releases/tag/v0.2.0
[0.1.0]: https://github.com/rainerseventeen/paper-tracker/releases/tag/v0.1.0
