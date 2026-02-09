from __future__ import annotations

"""Shared helpers for configuration loading and validation."""

from typing import Any, Mapping


def get_section(raw: Mapping[str, Any], key: str, *, required: bool) -> Mapping[str, Any]:
    """Return a mapping section from root config.

    Args:
        raw: Root configuration mapping.
        key: Section name.
        required: Whether the section must exist.

    Returns:
        Section mapping, or empty mapping for optional missing sections.

    Raises:
        ValueError: If section is required but missing.
        TypeError: If section is not a mapping.
    """
    section = raw.get(key)
    if section is None:
        if required:
            raise ValueError(f"Missing required config: {key}")
        return {}
    if not isinstance(section, Mapping):
        raise TypeError(f"{key} must be an object")
    return section


def get_required_value(section: Mapping[str, Any], field: str, config_key: str) -> Any:
    """Return a required field value from a section.

    Args:
        section: Section mapping.
        field: Field name in section.
        config_key: Full key path for error messages.

    Returns:
        Raw field value.

    Raises:
        ValueError: If field is missing.
    """
    if field not in section:
        raise ValueError(f"Missing required config: {config_key}")
    return section[field]


def get_optional_value(section: Mapping[str, Any], field: str, default: Any) -> Any:
    """Return optional field value with default."""
    return section.get(field, default)


def expect_str(value: Any, config_key: str) -> str:
    """Validate and return string value."""
    if not isinstance(value, str):
        raise TypeError(f"{config_key} must be a string")
    return value


def expect_bool(value: Any, config_key: str) -> bool:
    """Validate and return boolean value."""
    if not isinstance(value, bool):
        raise TypeError(f"{config_key} must be a boolean")
    return value


def expect_int(value: Any, config_key: str) -> int:
    """Validate and return integer value (excluding bool)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{config_key} must be an integer")
    return value


def expect_float(value: Any, config_key: str) -> float:
    """Validate and return float value from numeric input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{config_key} must be a number")
    return float(value)


def expect_str_list(value: Any, config_key: str) -> list[str]:
    """Validate a list of strings."""
    if not isinstance(value, list):
        raise TypeError(f"{config_key} must be a list")
    out: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str):
            raise TypeError(f"{config_key}[{idx}] must be a string")
        out.append(item)
    return out

