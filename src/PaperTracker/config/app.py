from __future__ import annotations

"""Application config orchestration and YAML loading entrypoints."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from PaperTracker.config.llm import LLMConfig, check_llm, load_llm
from PaperTracker.config.output import OutputConfig, check_output, load_output
from PaperTracker.config.runtime import RuntimeConfig, check_runtime, load_runtime
from PaperTracker.config.search import SearchConfig, check_search, load_search
from PaperTracker.config.storage import StorageConfig, check_storage, load_storage


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Application root configuration."""

    runtime: RuntimeConfig
    search: SearchConfig
    output: OutputConfig
    storage: StorageConfig
    llm: LLMConfig


def parse_config_dict(raw: Mapping[str, Any]) -> AppConfig:
    """Parse normalized mapping into AppConfig."""
    runtime = load_runtime(raw)
    search = load_search(raw)
    output = load_output(raw)
    storage = load_storage(raw)
    llm = load_llm(raw)

    check_runtime(runtime)
    check_search(search)
    check_output(output)
    check_storage(storage)
    check_llm(llm)

    config = AppConfig(
        runtime=runtime,
        search=search,
        output=output,
        storage=storage,
        llm=llm,
    )
    check_cross_domain(config)
    return config


def load_config(path: Path) -> AppConfig:
    """Load YAML config file without default merge."""
    return load_config_with_defaults(path, default_path=path)


def load_config_with_defaults(
    config_path: Path, default_path: Path = Path("config/default.yml")
) -> AppConfig:
    """Load config by merging defaults and optional override."""
    base = parse_yaml(default_path.read_text(encoding="utf-8"))
    if config_path == default_path:
        return parse_config_dict(base)
    override = parse_yaml(config_path.read_text(encoding="utf-8"))
    merged = merge_config_dicts(base, override)
    return parse_config_dict(merged)


def check_cross_domain(config: AppConfig) -> None:
    """Validate cross-domain constraints."""
    if config.llm.enabled and not config.storage.enabled:
        raise ValueError("llm.enabled=true requires storage.enabled=true")
    if config.llm.enabled and not config.storage.content_storage_enabled:
        raise ValueError("llm.enabled=true requires storage.content_storage_enabled=true")


def parse_yaml(text: str) -> dict[str, Any]:
    """Parse raw YAML text into a mapping."""
    data = yaml.safe_load(text) or {}
    if not isinstance(data, Mapping):
        raise ValueError("Config root must be a mapping/object")
    return dict(data)


def merge_config_dicts(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Deep-merge two config mappings."""
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], Mapping) and isinstance(value, Mapping):
            merged[key] = merge_config_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged
