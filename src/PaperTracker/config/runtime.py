"""Runtime domain configuration (logging, process behavior)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from PaperTracker.config.common import (
    expect_bool,
    expect_str,
    get_required_value,
    get_section,
)

_ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Store validated runtime behavior settings."""

    level: str
    to_file: bool
    dir: str


def load_runtime(raw: Mapping[str, Any]) -> RuntimeConfig:
    """Load runtime configuration from raw mapping.

    Args:
        raw: Root configuration mapping.

    Returns:
        Parsed runtime configuration.

    Raises:
        TypeError: If config types are invalid.
        ValueError: If required keys are missing.
    """
    section = get_section(raw, "log", required=True)
    return RuntimeConfig(
        level=expect_str(get_required_value(section, "level", "log.level"), "log.level").upper(),
        to_file=expect_bool(get_required_value(section, "to_file", "log.to_file"), "log.to_file"),
        dir=expect_str(get_required_value(section, "dir", "log.dir"), "log.dir"),
    )


def check_runtime(config: RuntimeConfig) -> None:
    """Validate runtime domain constraints.

    Args:
        config: Parsed runtime configuration.

    Raises:
        ValueError: If values violate runtime constraints.
    """
    if config.level not in _ALLOWED_LOG_LEVELS:
        raise ValueError(f"log.level must be one of {sorted(_ALLOWED_LOG_LEVELS)}")
    if not config.dir.strip():
        raise ValueError("log.dir must not be empty")
