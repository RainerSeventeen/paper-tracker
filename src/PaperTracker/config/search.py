from __future__ import annotations

"""Search domain configuration and query DSL parsing."""

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
from PaperTracker.core.query import FieldQuery, SearchQuery

_ALLOWED_FIELDS = {"TITLE", "ABSTRACT", "AUTHOR", "JOURNAL", "CATEGORY"}
_ALLOWED_OPS = {"AND", "OR", "NOT"}


@dataclass(frozen=True, slots=True)
class SearchConfig:
    """Search domain configuration."""

    scope: SearchQuery | None
    queries: tuple[SearchQuery, ...]
    max_results: int
    pull_every: int
    fill_enabled: bool
    max_lookback_days: int
    max_fetch_items: int
    fetch_batch_size: int


def load_search(raw: Mapping[str, Any]) -> SearchConfig:
    """Load search domain config from raw mapping."""
    scope_obj = raw.get("scope")
    scope = parse_search_query(scope_obj, "scope") if scope_obj is not None else None

    queries_obj = raw.get("queries")
    if not isinstance(queries_obj, list):
        raise TypeError("queries must be a list")
    queries = tuple(parse_search_query(item, f"queries[{idx}]") for idx, item in enumerate(queries_obj))

    section = get_section(raw, "search", required=True)
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
    )


def check_search(config: SearchConfig) -> None:
    """Validate search domain constraints."""
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


def parse_search_query(value: Any, config_key: str) -> SearchQuery:
    """Parse a query mapping into SearchQuery."""
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
    """Parse field-level query operators."""
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
    """Normalize terms from string/list into stripped list."""
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

