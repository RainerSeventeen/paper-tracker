from __future__ import annotations

"""Storage domain configuration for persistence and arXiv id behavior."""

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
    """Load storage domain config from raw mapping."""
    state_section = get_section(raw, "state", required=True)
    arxiv_section = get_section(raw, "arxiv", required=True)
    return StorageConfig(
        enabled=expect_bool(get_required_value(state_section, "enabled", "state.enabled"), "state.enabled"),
        db_path=expect_str(get_required_value(state_section, "db_path", "state.db_path"), "state.db_path"),
        content_storage_enabled=expect_bool(
            get_required_value(state_section, "content_storage_enabled", "state.content_storage_enabled"),
            "state.content_storage_enabled",
        ),
        keep_arxiv_version=expect_bool(
            get_required_value(arxiv_section, "keep_version", "arxiv.keep_version"),
            "arxiv.keep_version",
        ),
    )


def check_storage(config: StorageConfig) -> None:
    """Validate storage domain constraints."""
    if not config.db_path.strip():
        raise ValueError("state.db_path must not be empty")

