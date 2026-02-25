"""Storage domain configuration for persistence and arXiv id behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from PaperTracker.config.common import (
    expect_bool,
    expect_str,
    get_required_value,
    get_section,
)


@dataclass(frozen=True, slots=True)
class StorageConfig:
    """Storage configuration."""

    enabled: bool
    db_path: str
    content_storage_enabled: bool
    keep_arxiv_version: bool


def load_storage(raw: Mapping[str, Any]) -> StorageConfig:
    """Load storage domain config from raw mapping.

    Args:
        raw: Root configuration mapping.

    Returns:
        Parsed storage configuration.

    Raises:
        TypeError: If config types are invalid.
        ValueError: If required keys are missing.
    """
    storage_section = get_section(raw, "storage", required=True)
    return StorageConfig(
        enabled=expect_bool(
            get_required_value(storage_section, "enabled", "storage.enabled"),
            "storage.enabled",
        ),
        db_path=expect_str(
            get_required_value(storage_section, "db_path", "storage.db_path"),
            "storage.db_path",
        ),
        content_storage_enabled=expect_bool(
            get_required_value(
                storage_section, "content_storage_enabled", "storage.content_storage_enabled"
            ),
            "storage.content_storage_enabled",
        ),
        keep_arxiv_version=expect_bool(
            get_required_value(
                storage_section, "keep_arxiv_version", "storage.keep_arxiv_version"
            ),
            "storage.keep_arxiv_version",
        ),
    )


def check_storage(config: StorageConfig) -> None:
    """Validate storage domain constraints.

    Args:
        config: Parsed storage configuration.

    Raises:
        ValueError: If values violate storage constraints.
    """
    if not config.db_path.strip():
        raise ValueError("storage.db_path must not be empty")
