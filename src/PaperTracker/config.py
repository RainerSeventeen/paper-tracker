"""YAML configuration loading for PaperTracker.

The CLI is intentionally minimal: most runtime parameters are read from a YAML
file to keep the command surface small and reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping

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


_ALLOWED_FIELDS = {"TITLE", "ABSTRACT", "AUTHOR", "JOURNAL", "CATEGORY"}
_ALLOWED_OPS = {"AND", "OR", "NOT"}


def _as_str_list(value: Any) -> list[str]:
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


_RE_INT = re.compile(r"^[+-]?\d+$")
_RE_FLOAT = re.compile(r"^[+-]?(?:\d+\.\d*|\d*\.\d+)$")


def _strip_comment(line: str) -> str:
    """Remove trailing YAML-style comments.

    This is a minimal implementation intended for simple config files.
    """
    if "#" not in line:
        return line
    return line.split("#", 1)[0]


def _parse_scalar(text: str) -> Any:
    """Parse a scalar value from the minimal YAML subset."""
    s = text.strip()
    if s in {"", "null", "~"}:
        return None
    sl = s.lower()
    if sl == "true":
        return True
    if sl == "false":
        return False
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if _RE_INT.match(s):
        try:
            return int(s)
        except ValueError:
            return s
    if _RE_FLOAT.match(s):
        try:
            return float(s)
        except ValueError:
            return s
    return s


def _parse_inline_list(text: str) -> list[Any]:
    """Parse an inline list like `[a, b, "c d"]`."""
    inner = text.strip()[1:-1].strip()
    if not inner:
        return []
    parts = [p.strip() for p in inner.split(",")]
    return [_parse_value(p) for p in parts if p]


def _parse_value(text: str) -> Any:
    """Parse either a scalar or an inline list from the minimal YAML subset."""
    s = text.strip()
    if s.startswith("[") and s.endswith("]"):
        return _parse_inline_list(s)
    return _parse_scalar(s)


def _parse_yaml_minimal(text: str) -> dict[str, Any]:
    """Parse a small, YAML-like subset used by this project.

    Supported constructs:
    - Mappings: `key: value` and nested mappings via indentation
    - Lists: `key: [a, b]` and block lists with `- item`
    - Scalars: strings, ints, floats, booleans, null

    This is intentionally limited to avoid extra dependencies.
    """

    raw_lines = []
    for ln in text.splitlines():
        ln = _strip_comment(ln).rstrip("\n")
        if ln.strip() == "":
            continue
        if "\t" in ln:
            raise ValueError("Tabs are not supported in config indentation")
        raw_lines.append(ln.rstrip())

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(0, root)]

    def indent_of(s: str) -> int:
        return len(s) - len(s.lstrip(" "))

    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        indent = indent_of(line)
        content = line.strip()

        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()
        container = stack[-1][1]

        if content.startswith("- "):
            if not isinstance(container, list):
                raise ValueError(f"List item found where mapping was expected: {line!r}")

            item_text = content[2:].strip()
            # Support list-of-mappings with inline first key, e.g. `- NAME: q1`.
            if ":" in item_text:
                k, sep, rest = item_text.partition(":")
                if sep != ":":
                    raise ValueError(f"Invalid list mapping item: {line!r}")
                d: dict[str, Any] = {}
                if rest.strip():
                    d[k.strip()] = _parse_value(rest.strip())
                else:
                    d[k.strip()] = {}
                container.append(d)
                stack.append((indent + 2, d))
                i += 1
                continue

            container.append(_parse_value(item_text))
            i += 1
            continue

        key, sep, rest = content.partition(":")
        if sep != ":":
            raise ValueError(f"Invalid config line (missing ':'): {line!r}")
        key = key.strip()
        rest = rest.strip()
        if not isinstance(container, Mapping):
            raise ValueError(f"Mapping entry found where list was expected: {line!r}")

        if rest:
            container[key] = _parse_value(rest)
            i += 1
            continue

        # `key:` with a nested block. Decide dict vs list by looking ahead.
        j = i + 1
        while j < len(raw_lines) and raw_lines[j].strip() == "":
            j += 1
        if j >= len(raw_lines) or indent_of(raw_lines[j]) <= indent:
            container[key] = {}
            i += 1
            continue

        next_content = raw_lines[j].strip()
        nested: Any
        if next_content.startswith("- "):
            nested = []
        else:
            nested = {}
        container[key] = nested
        stack.append((indent_of(raw_lines[j]), nested))
        i += 1

    return root


def _get(d: Mapping[str, Any], path: str, default: Any = None) -> Any:
    """Get nested key from mapping by dotted path."""
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
    """

    raw = _parse_yaml_minimal(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise TypeError("Config root must be a mapping/object")

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
    )
