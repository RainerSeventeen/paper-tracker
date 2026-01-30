"""YAML configuration loading for PaperTracker.

The CLI is intentionally minimal: most runtime parameters are read from a YAML
file to keep the command surface small and reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from PaperTracker.core.query import FieldQuery, SearchQuery


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Normalized runtime configuration.

    Attributes:
        log_level: Logging level for the CLI.
        log_to_file: Whether to mirror logs to a file.
        log_dir: Base directory for log files.
        scope: Optional global scope applied to every query.
        queries: Independent queries.
        max_results: Maximum number of papers.
        sort_by: Sort field.
        sort_order: Sort order.
        output_format: Output format (text/json).
        state_enabled: Whether to enable state management.
        state_db_path: Database path for state management.
        arxiv_keep_version: Whether to keep arXiv version suffix in the paper id.
    """

    log_level: str = "INFO"
    log_to_file: bool = True
    log_dir: str = "log"
    scope: SearchQuery | None = None
    queries: tuple[SearchQuery, ...] = ()
    max_results: int = 20
    sort_by: str = "submittedDate"
    sort_order: str = "descending"
    output_format: str = "text"
    state_enabled: bool = False
    state_db_path: str = "state/papers.db"
    arxiv_keep_version: bool = False


_ALLOWED_FIELDS = {"TITLE", "ABSTRACT", "AUTHOR", "JOURNAL", "CATEGORY"}
_ALLOWED_OPS = {"AND", "OR", "NOT"}


def _as_str_list(value: Any) -> list[str]:
    """Normalize a term list into a list of stripped strings.

    Args:
        value: A string, list of strings, or None.

    Returns:
        A list of non-empty, stripped strings.

    Raises:
        TypeError: If the input is not a string, list of strings, or None.
    """
    if value is None:
        return []
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError("Terms must be strings")
            s = item.strip()
            if s:
                out.append(s)
        return out
    raise TypeError("Terms must be a string or a list of strings")


def _parse_field_query(value: Any) -> FieldQuery:
    """Parse a field query mapping into a FieldQuery object.

    Args:
        value: Mapping containing AND/OR/NOT keys.

    Returns:
        A FieldQuery with normalized term lists.

    Raises:
        TypeError: If the value is not a mapping.
        ValueError: If unknown operators are provided.
    """
    if value is None:
        return FieldQuery()
    if not isinstance(value, Mapping):
        raise TypeError("Field config must be an object with AND/OR/NOT")
    unknown = {str(k) for k in value.keys()} - _ALLOWED_OPS
    if unknown:
        raise ValueError(f"Unknown operator(s): {sorted(unknown)}")

    and_terms = _as_str_list(value.get("AND"))
    or_terms = _as_str_list(value.get("OR"))
    not_terms = _as_str_list(value.get("NOT"))
    return FieldQuery(AND=tuple(and_terms), OR=tuple(or_terms), NOT=tuple(not_terms))


def _parse_search_query(value: Any) -> SearchQuery:
    """Parse a query mapping into a SearchQuery object.

    Args:
        value: Mapping containing query fields and optional NAME.

    Returns:
        A SearchQuery with normalized fields.

    Raises:
        TypeError: If the value is not a mapping or fields are invalid.
        ValueError: If required fields are missing or invalid.
    """
    if not isinstance(value, Mapping):
        raise TypeError("Each query must be an object")

    name = None
    if "NAME" in value:
        if not isinstance(value["NAME"], str):
            raise TypeError("NAME must be a string")
        name = value["NAME"].strip() or None

    fields: dict[str, FieldQuery] = {}
    # Shorthand: allow top-level AND/OR/NOT to mean "TEXT" (title+abstract).
    if any(k in value for k in _ALLOWED_OPS):
        fields["TEXT"] = _parse_field_query({op: value.get(op) for op in _ALLOWED_OPS if op in value})

    for k, v in value.items():
        if k == "NAME":
            continue
        if k in _ALLOWED_OPS:
            continue
        if not isinstance(k, str):
            raise TypeError("Field names must be strings")
        if k != k.upper():
            raise ValueError(f"Field keys must be uppercase: {k}")
        field = k.strip().upper()
        if field not in _ALLOWED_FIELDS:
            raise ValueError(f"Unknown field: {field}")
        fields[field] = _parse_field_query(v)

    if not fields:
        raise ValueError("Query must include at least one field")
    return SearchQuery(name=name, fields=fields)


def _parse_yaml(text: str) -> dict[str, Any]:
    """Parse YAML configuration text using PyYAML.

    Args:
        text: Raw YAML string.

    Returns:
        Parsed YAML data as a mapping.

    Raises:
        ValueError: If the YAML root is not a mapping.
        yaml.YAMLError: If the YAML is invalid.
    """
    data = yaml.safe_load(text) or {}
    if not isinstance(data, Mapping):
        raise ValueError("Config root must be a mapping/object")
    return dict(data)


def _get(d: Mapping[str, Any], path: str, default: Any = None) -> Any:
    """Get nested key from mapping by dotted path.

    Args:
        d: Mapping to search.
        path: Dotted key path (e.g., "log.level").
        default: Default value if missing.

    Returns:
        Value found at the path or the default.
    """
    cur: Any = d
    for key in path.split("."):
        if not isinstance(cur, Mapping) or key not in cur:
            return default
        cur = cur[key]
    return cur


def load_config(path: Path) -> AppConfig:
    """Load YAML config file and normalize into `AppConfig`.

    Supported YAML structure (both flat and nested keys are accepted):

    - `log_level` / `log.level`
    - `log_to_file` / `log.to_file`
    - `log_dir` / `log.dir`
    - `scope` (optional)
      - Field mapping applied to every query.
    - `queries`
      - List of query objects.
      - Field keys and operator keys must be uppercase.
    - `search.max_results` / `max_results`
    - `search.sort_by` / `sort_by`
    - `search.sort_order` / `sort_order`
    - `output.format` / `format`
    - `arxiv.keep_version`
    
    Args:
        path: Path to the YAML config file.

    Returns:
        Normalized application configuration.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the YAML is invalid or the config is malformed.
        TypeError: If required fields are missing or have wrong types.
    """

    raw = _parse_yaml(path.read_text(encoding="utf-8"))

    log_level = str(_get(raw, "log.level", _get(raw, "log_level", "INFO")) or "INFO").upper()
    log_to_file = bool(_get(raw, "log.to_file", _get(raw, "log_to_file", True)))
    log_dir = str(_get(raw, "log.dir", _get(raw, "log_dir", "log")) or "log")

    scope_obj = raw.get("scope")
    scope = _parse_search_query(scope_obj) if scope_obj is not None else None

    queries_obj = raw.get("queries")
    if not isinstance(queries_obj, list):
        raise TypeError("queries must be a list")
    queries = tuple(_parse_search_query(q) for q in queries_obj)

    max_results = int(_get(raw, "search.max_results", _get(raw, "max_results", 20)) or 20)
    sort_by = str(_get(raw, "search.sort_by", _get(raw, "sort_by", "submittedDate")) or "submittedDate")
    sort_order = str(_get(raw, "search.sort_order", _get(raw, "sort_order", "descending")) or "descending")

    output_format = str(_get(raw, "output.format", _get(raw, "format", "text")) or "text").lower()

    state_obj = raw.get("state", )
    state_enabled = bool(_get(state_obj, "enabled", False))
    state_db_path_raw = _get(state_obj, "db_path", None)
    if state_db_path_raw is None:
        state_db_path = "state/papers.db"
    else:
        state_db_path = str(state_db_path_raw)
    arxiv_keep_version = bool(_get(raw, "arxiv.keep_version", False))

    if not queries:
        raise ValueError("Missing required config: queries")
    if output_format not in {"text", "json"}:
        raise ValueError("output.format must be text or json")

    return AppConfig(
        log_level=log_level,
        log_to_file=log_to_file,
        log_dir=log_dir,
        scope=scope,
        queries=queries,
        max_results=max_results,
        sort_by=sort_by,
        sort_order=sort_order,
        output_format=output_format,
        state_enabled=state_enabled,
        state_db_path=state_db_path,
        arxiv_keep_version=arxiv_keep_version,
    )
