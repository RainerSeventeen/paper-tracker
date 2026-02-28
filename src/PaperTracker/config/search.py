"""Search domain configuration and query DSL parsing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from PaperTracker.config.common import (
    expect_bool,
    expect_int,
    expect_str,
    expect_str_list,
    get_required_value,
    get_section,
)
from PaperTracker.sources.registry import supported_source_names
from PaperTracker.core.query import FieldQuery, SearchQuery

_ALLOWED_FIELDS = {"TITLE", "ABSTRACT", "AUTHOR", "JOURNAL", "CATEGORY"}
_ALLOWED_OPS = {"AND", "OR", "NOT"}
_ALLOWED_SOURCES = frozenset(supported_source_names())


@dataclass(frozen=True, slots=True)
class SearchConfig:
    """Store validated search behavior, sources, and query settings."""

    scope: SearchQuery | None
    queries: tuple[SearchQuery, ...]
    max_results: int
    pull_every: int
    fill_enabled: bool
    max_lookback_days: int
    max_fetch_items: int
    fetch_batch_size: int
    sources: tuple[str, ...]


def load_search(raw: Mapping[str, Any]) -> SearchConfig:
    """Load search domain config from raw mapping.

    Args:
        raw: Root configuration mapping.

    Returns:
        Parsed search configuration.

    Raises:
        TypeError: If config types are invalid.
        ValueError: If required keys are missing.
    """
    scope_obj = raw.get("scope")
    scope = parse_search_query(scope_obj, "scope") if scope_obj is not None else None

    queries_obj = raw.get("queries")
    if queries_obj is None:
        raise ValueError("Missing required config: queries")
    if not isinstance(queries_obj, list):
        raise TypeError("queries must be a list")
    queries = tuple(parse_search_query(item, f"queries[{idx}]") for idx, item in enumerate(queries_obj))

    section = get_section(raw, "search", required=True)
    sources = _parse_sources(section.get("sources", ["arxiv"]))
    return SearchConfig(
        scope=scope,
        queries=queries,
        max_results=expect_int(get_required_value(section, "max_results", "search.max_results"), "search.max_results"),
        pull_every=expect_int(get_required_value(section, "pull_every", "search.pull_every"), "search.pull_every"),
        fill_enabled=expect_bool(
            get_required_value(section, "fill_enabled", "search.fill_enabled"),
            "search.fill_enabled",
        ),
        max_lookback_days=expect_int(
            get_required_value(section, "max_lookback_days", "search.max_lookback_days"),
            "search.max_lookback_days",
        ),
        max_fetch_items=expect_int(
            get_required_value(section, "max_fetch_items", "search.max_fetch_items"),
            "search.max_fetch_items",
        ),
        fetch_batch_size=expect_int(
            get_required_value(section, "fetch_batch_size", "search.fetch_batch_size"),
            "search.fetch_batch_size",
        ),
        sources=sources,
    )


def check_search(config: SearchConfig) -> None:
    """Validate search domain constraints.

    Args:
        config: Parsed search configuration.

    Raises:
        ValueError: If values violate search constraints.
    """
    if not config.queries:
        raise ValueError("queries must include at least one query")
    if config.max_results <= 0:
        raise ValueError("search.max_results must be positive")
    if config.pull_every <= 0:
        raise ValueError("search.pull_every must be positive")
    if config.max_lookback_days != -1 and config.max_lookback_days <= 0:
        raise ValueError("search.max_lookback_days must be -1 or positive")
    if config.fill_enabled and config.max_lookback_days != -1 and config.max_lookback_days < config.pull_every:
        raise ValueError(
            "search.max_lookback_days must be -1 or >= search.pull_every when search.fill_enabled=true"
        )
    if config.max_fetch_items == 0 or config.max_fetch_items < -1:
        raise ValueError("search.max_fetch_items must be -1 or positive")
    if config.fetch_batch_size <= 0:
        raise ValueError("search.fetch_batch_size must be positive")
    if not config.sources:
        raise ValueError("search.sources must include at least one source")


def _parse_sources(value: Any) -> tuple[str, ...]:
    """Parse and normalize configured source names.

    Args:
        value: Raw list value from ``search.sources``.

    Returns:
        Normalized, unique source names in configured order.

    Raises:
        TypeError: If value is not a string list.
        ValueError: If list is empty after normalization or contains unknown sources.
    """
    items = expect_str_list(value, "search.sources")

    normalized: list[str] = []
    seen: set[str] = set()
    for idx, item in enumerate(items):
        source = expect_str(item, f"search.sources[{idx}]").strip().lower()
        if not source:
            continue
        if source not in _ALLOWED_SOURCES:
            raise ValueError(f"search.sources has unknown source: {source}")
        if source in seen:
            continue
        seen.add(source)
        normalized.append(source)

    if not normalized:
        raise ValueError("search.sources must include at least one source")

    return tuple(normalized)


def parse_search_query(value: Any, config_key: str) -> SearchQuery:
    """Parse a query mapping into ``SearchQuery``.

    Args:
        value: Query mapping value.
        config_key: Full key path used in error messages.

    Returns:
        Parsed query object.

    Raises:
        TypeError: If query shape/types are invalid.
        ValueError: If query keys/operators are invalid.
    """
    if not isinstance(value, Mapping):
        raise TypeError(f"{config_key} must be an object")

    name = None
    if "NAME" in value:
        name = expect_str(value["NAME"], f"{config_key}.NAME").strip() or None

    fields: dict[str, FieldQuery] = {}
    if any(k in value for k in _ALLOWED_OPS):
        fields["TEXT"] = _parse_field_query({op: value.get(op) for op in _ALLOWED_OPS if op in value}, config_key)

    for key, field_value in value.items():
        if key == "NAME" or key in _ALLOWED_OPS:
            continue
        if not isinstance(key, str):
            raise TypeError(f"{config_key} field names must be strings")
        if key != key.upper():
            raise ValueError(f"{config_key} field keys must be uppercase: {key}")
        field = key.strip().upper()
        if field not in _ALLOWED_FIELDS:
            raise ValueError(f"{config_key} has unknown field: {field}")
        fields[field] = _parse_field_query(field_value, f"{config_key}.{field}")

    if not fields:
        raise ValueError(f"{config_key} must include at least one field")
    return SearchQuery(name=name, fields=fields)


def _parse_field_query(value: Any, config_key: str) -> FieldQuery:
    """Parse field-level query operators.

    Args:
        value: Field query mapping.
        config_key: Full key path used in error messages.

    Returns:
        Parsed field query object.

    Raises:
        TypeError: If field query type is invalid.
        ValueError: If unknown operators exist.
    """
    if value is None:
        return FieldQuery()
    if not isinstance(value, Mapping):
        raise TypeError(f"{config_key} must be an object with AND/OR/NOT")

    unknown = {str(k) for k in value.keys()} - _ALLOWED_OPS
    if unknown:
        raise ValueError(f"{config_key} has unknown operators: {sorted(unknown)}")

    and_terms = _as_terms(value.get("AND"), f"{config_key}.AND")
    or_terms = _as_terms(value.get("OR"), f"{config_key}.OR")
    not_terms = _as_terms(value.get("NOT"), f"{config_key}.NOT")
    return FieldQuery(AND=tuple(and_terms), OR=tuple(or_terms), NOT=tuple(not_terms))


def _as_terms(value: Any, config_key: str) -> list[str]:
    """Normalize terms from string/list into stripped list.

    Args:
        value: Raw terms value.
        config_key: Full key path used in error messages.

    Returns:
        Normalized non-empty terms.

    Raises:
        TypeError: If terms are not a string/list of strings.
    """
    if value is None:
        return []
    if isinstance(value, str):
        term = value.strip()
        return [term] if term else []
    terms = expect_str_list(value, config_key)
    out: list[str] = []
    for idx, item in enumerate(terms):
        normalized = expect_str(item, f"{config_key}[{idx}]").strip()
        if normalized:
            out.append(normalized)
    return out
