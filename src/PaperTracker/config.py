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
class LLMConfig:
    """LLM-related configuration."""

    enabled: bool = False
    provider: str = "openai-compat"
    base_url: str = "https://api.openai.com"
    model: str = "gpt-4o-mini"
    api_key_env: str = "LLM_API_KEY"
    timeout: int = 30
    target_lang: str = "zh"
    temperature: float = 0.0
    max_tokens: int = 800
    max_workers: int = 3
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 10.0
    retry_timeout_multiplier: float = 1.0
    enable_translation: bool = True
    enable_summary: bool = False


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
        output_dir: Directory for JSON output files.
        state_enabled: Whether to enable state management.
        state_db_path: Database path for state management (relative or absolute path).
        content_storage_enabled: Whether to enable content storage for full paper data.
        arxiv_keep_version: Whether to keep arXiv version suffix in the paper id.
        llm: LLM configuration settings.
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
    output_dir: str = "output"
    state_enabled: bool = False
    state_db_path: str = "database/papers.db"
    content_storage_enabled: bool = False
    arxiv_keep_version: bool = False
    llm: LLMConfig = LLMConfig()


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


def _get(d: Mapping[str, Any], key: str, default: Any = None) -> Any:
    """Get a key from a mapping with a default fallback.

    Args:
        d: Mapping to search.
        key: Key to fetch.
        default: Default value if missing.

    Returns:
        Value found at the key or the default.
    """
    if not isinstance(d, Mapping):
        return default
    return d.get(key, default)


def _get_section(raw: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    """Get a nested mapping section or return an empty mapping."""
    section = raw.get(key)
    if isinstance(section, Mapping):
        return section
    return {}


def _get_required(
    section: Mapping[str, Any], field_name: str, config_key: str, converter: type
) -> Any:
    """Get a required config field with validation and conversion.

    Args:
        section: The config section mapping.
        field_name: The field name in the section.
        config_key: The full config key path for error messages (e.g., "log.level").
        converter: Type converter function (str, int, bool, float).

    Returns:
        Converted field value.

    Raises:
        ValueError: If the field is missing.
    """
    value = _get(section, field_name)
    if value is None:
        raise ValueError(f"Missing required config: {config_key}")
    return converter(value)


def parse_config_dict(raw: Mapping[str, Any]) -> AppConfig:
    """Normalize a configuration mapping into `AppConfig`.

    Supported YAML structure (nested keys only; dotted keys are not supported):

    - `log.level`
    - `log.to_file`
    - `log.dir`
    - `scope` (optional)
      - Field mapping applied to every query.
    - `queries`
      - List of query objects.
      - Field keys and operator keys must be uppercase.
    - `search.max_results`
    - `search.sort_by`
    - `search.sort_order`
    - `output.format` - Output format for results
    - `output.dir` - Output directory for JSON files
    - `state.enabled` - Enable state management (deduplication)
    - `state.db_path` - Database path (relative or absolute; relative to working directory)
    - `state.content_storage_enabled` - Enable full content storage
    - `arxiv.keep_version`

    Args:
        raw: Parsed configuration mapping.

    Returns:
        Normalized application configuration.

    Raises:
        ValueError: If the config is malformed.
        TypeError: If required fields are missing or have wrong types.
    """

    log_obj = _get_section(raw, "log")
    log_level = _get_required(log_obj, "level", "log.level", str).upper()
    log_to_file = _get_required(log_obj, "to_file", "log.to_file", bool)
    log_dir = _get_required(log_obj, "dir", "log.dir", str)

    scope_obj = raw.get("scope")
    scope = _parse_search_query(scope_obj) if scope_obj is not None else None

    queries_obj = raw.get("queries")
    if not isinstance(queries_obj, list):
        raise TypeError("queries must be a list")
    queries = tuple(_parse_search_query(q) for q in queries_obj)

    search_obj = _get_section(raw, "search")
    max_results = _get_required(search_obj, "max_results", "search.max_results", int)
    sort_by = _get_required(search_obj, "sort_by", "search.sort_by", str)
    sort_order = _get_required(search_obj, "sort_order", "search.sort_order", str)

    output_obj = _get_section(raw, "output")
    output_format = _get_required(output_obj, "format", "output.format", str).lower()
    output_dir = _get_required(output_obj, "dir", "output.dir", str)

    state_obj = raw.get("state")
    if not isinstance(state_obj, Mapping):
        raise ValueError("Missing required config: state")

    state_enabled = _get_required(state_obj, "enabled", "state.enabled", bool)
    state_db_path = _get_required(state_obj, "db_path", "state.db_path", str)
    content_storage_enabled = _get_required(
        state_obj, "content_storage_enabled", "state.content_storage_enabled", bool
    )

    arxiv_obj = raw.get("arxiv")
    if not isinstance(arxiv_obj, Mapping):
        raise ValueError("Missing required config: arxiv")
    arxiv_keep_version = _get_required(arxiv_obj, "keep_version", "arxiv.keep_version", bool)

    # LLM configuration
    llm_obj = raw.get("llm")
    if not isinstance(llm_obj, Mapping):
        raise ValueError("Missing required config: llm")

    llm_config = LLMConfig(
        enabled=_get_required(llm_obj, "enabled", "llm.enabled", bool),
        provider=_get_required(llm_obj, "provider", "llm.provider", str),
        base_url=_get_required(llm_obj, "base_url", "llm.base_url", str),
        model=_get_required(llm_obj, "model", "llm.model", str),
        api_key_env=_get_required(llm_obj, "api_key_env", "llm.api_key_env", str),
        timeout=_get_required(llm_obj, "timeout", "llm.timeout", int),
        target_lang=_get_required(llm_obj, "target_lang", "llm.target_lang", str),
        temperature=_get_required(llm_obj, "temperature", "llm.temperature", float),
        max_tokens=_get_required(llm_obj, "max_tokens", "llm.max_tokens", int),
        max_workers=_get_required(llm_obj, "max_workers", "llm.max_workers", int),
        max_retries=_get_required(llm_obj, "max_retries", "llm.max_retries", int),
        retry_base_delay=_get_required(llm_obj, "retry_base_delay", "llm.retry_base_delay", float),
        retry_max_delay=_get_required(llm_obj, "retry_max_delay", "llm.retry_max_delay", float),
        retry_timeout_multiplier=_get_required(
            llm_obj, "retry_timeout_multiplier", "llm.retry_timeout_multiplier", float
        ),
        enable_translation=_get_required(llm_obj, "enable_translation", "llm.enable_translation", bool),
        enable_summary=_get_required(llm_obj, "enable_summary", "llm.enable_summary", bool),
    )

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
        output_dir=output_dir,
        state_enabled=state_enabled,
        state_db_path=state_db_path,
        content_storage_enabled=content_storage_enabled,
        arxiv_keep_version=arxiv_keep_version,
        llm=llm_config,
    )


def load_config(path: Path) -> AppConfig:
    """Load YAML config file and normalize into `AppConfig`.

    This loads the config file as-is without merging with defaults.
    Equivalent to `load_config_with_defaults(path, default_path=path)`.

    Args:
        path: Path to the YAML config file.

    Returns:
        Normalized application configuration.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the YAML is invalid or the config is malformed.
        TypeError: If required fields are missing or have wrong types.
    """
    return load_config_with_defaults(path, default_path=path)


def _merge_config_dicts(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Deep-merge two configuration mappings.

    Mapping values are merged recursively. For other types (scalars, lists),
    the override replaces the base value.

    Args:
        base: Base configuration mapping.
        override: Override configuration mapping.

    Returns:
        Merged configuration mapping.
    """
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], Mapping) and isinstance(value, Mapping):
            merged[key] = _merge_config_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config_with_defaults(
    config_path: Path, default_path: Path = Path("config/default.yml")
) -> AppConfig:
    """Load config by merging defaults with an optional override.

    Args:
        config_path: Path to the user-provided config file (override).
        default_path: Path to the default config file.

    Returns:
        Normalized application configuration.

    Raises:
        OSError: If either file cannot be read.
        ValueError: If the YAML is invalid or the config is malformed.
        TypeError: If required fields are missing or have wrong types.
    """
    base = _parse_yaml(default_path.read_text(encoding="utf-8"))

    if config_path == default_path:
        return parse_config_dict(base)

    override = _parse_yaml(config_path.read_text(encoding="utf-8"))
    merged = _merge_config_dicts(base, override)
    return parse_config_dict(merged)
