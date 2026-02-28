"""LLM domain configuration for enrichment pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

from PaperTracker.config.common import (
    expect_bool,
    expect_float,
    expect_int,
    expect_str,
    get_optional_value,
    get_required_value,
    get_section,
)


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """Store validated LLM settings for enrichment tasks."""

    enabled: bool
    provider: str
    base_url: str
    model: str
    api_key_env: str
    api_key: str
    timeout: int
    target_lang: str
    temperature: float
    max_tokens: int
    max_workers: int
    max_retries: int
    retry_base_delay: float
    retry_max_delay: float
    retry_timeout_multiplier: float
    enable_translation: bool
    enable_summary: bool


def load_llm(raw: Mapping[str, Any]) -> LLMConfig:
    """Load llm domain config from raw mapping.

    Args:
        raw: Root configuration mapping.

    Returns:
        Parsed LLM configuration.

    Raises:
        TypeError: If config types are invalid.
        ValueError: If required keys are missing.
    """
    section = get_section(raw, "llm", required=True)
    api_key_env = expect_str(get_required_value(section, "api_key_env", "llm.api_key_env"), "llm.api_key_env")
    return LLMConfig(
        enabled=expect_bool(get_required_value(section, "enabled", "llm.enabled"), "llm.enabled"),
        provider=expect_str(get_required_value(section, "provider", "llm.provider"), "llm.provider"),
        base_url=expect_str(get_optional_value(section, "base_url", ""), "llm.base_url"),
        model=expect_str(get_optional_value(section, "model", ""), "llm.model"),
        api_key_env=api_key_env,
        api_key=_load_api_key_from_env(api_key_env),
        timeout=expect_int(get_required_value(section, "timeout", "llm.timeout"), "llm.timeout"),
        target_lang=expect_str(get_required_value(section, "target_lang", "llm.target_lang"), "llm.target_lang"),
        temperature=expect_float(get_required_value(section, "temperature", "llm.temperature"), "llm.temperature"),
        max_tokens=expect_int(get_required_value(section, "max_tokens", "llm.max_tokens"), "llm.max_tokens"),
        max_workers=expect_int(get_required_value(section, "max_workers", "llm.max_workers"), "llm.max_workers"),
        max_retries=expect_int(get_required_value(section, "max_retries", "llm.max_retries"), "llm.max_retries"),
        retry_base_delay=expect_float(
            get_required_value(section, "retry_base_delay", "llm.retry_base_delay"),
            "llm.retry_base_delay",
        ),
        retry_max_delay=expect_float(
            get_required_value(section, "retry_max_delay", "llm.retry_max_delay"),
            "llm.retry_max_delay",
        ),
        retry_timeout_multiplier=expect_float(
            get_required_value(section, "retry_timeout_multiplier", "llm.retry_timeout_multiplier"),
            "llm.retry_timeout_multiplier",
        ),
        enable_translation=expect_bool(
            get_required_value(section, "enable_translation", "llm.enable_translation"),
            "llm.enable_translation",
        ),
        enable_summary=expect_bool(
            get_required_value(section, "enable_summary", "llm.enable_summary"),
            "llm.enable_summary",
        ),
    )


def check_llm(config: LLMConfig) -> None:
    """Validate llm domain constraints.

    Args:
        config: Parsed LLM configuration.

    Raises:
        ValueError: If values violate LLM constraints.
    """
    _check_non_empty(config.provider, "llm.provider")
    _check_non_empty(config.api_key_env, "llm.api_key_env")
    _check_non_empty(config.target_lang, "llm.target_lang")
    if config.enabled:
        if not config.base_url.strip():
            raise ValueError("llm.base_url is required when llm.enabled is true")
        if not config.model.strip():
            raise ValueError("llm.model is required when llm.enabled is true")
        if not config.api_key:
            raise ValueError(
                f"LLM enabled but {config.api_key_env} environment variable not set. "
                "Set it in your .env file or shell environment."
            )

    if config.timeout <= 0:
        raise ValueError("llm.timeout must be positive")
    if not 0.0 <= config.temperature <= 2.0:
        raise ValueError("llm.temperature must be between 0.0 and 2.0")
    if config.max_tokens <= 0:
        raise ValueError("llm.max_tokens must be positive")
    if config.max_workers <= 0:
        raise ValueError("llm.max_workers must be positive")
    if config.max_retries < 0:
        raise ValueError("llm.max_retries must be >= 0")
    if config.retry_base_delay < 0:
        raise ValueError("llm.retry_base_delay must be >= 0")
    if config.retry_max_delay < config.retry_base_delay:
        raise ValueError("llm.retry_max_delay must be >= llm.retry_base_delay")
    if config.retry_timeout_multiplier <= 0:
        raise ValueError("llm.retry_timeout_multiplier must be positive")


def _check_non_empty(value: str, config_key: str) -> None:
    """Validate non-empty string values."""
    if not value.strip():
        raise ValueError(f"{config_key} must not be empty")


def _load_api_key_from_env(api_key_env: str) -> str:
    """Load API key from environment variable."""
    return os.getenv(api_key_env, "").strip()
