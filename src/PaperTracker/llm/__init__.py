"""LLM module for PaperTracker.

Provides translation and other LLM-powered enhancements for papers.
"""

from __future__ import annotations

import os

from PaperTracker.llm.client import LLMApiClient
from PaperTracker.llm.openai_compat import OpenAICompatProvider
from PaperTracker.llm.provider import LLMProvider
from PaperTracker.llm.service import LLMService
from PaperTracker.utils.log import log


def create_llm_service(config) -> LLMService | None:
    """Create LLM service from configuration.

    Args:
        config: Application configuration containing LLM settings.

    Returns:
        Configured LLMService instance, or None if LLM is disabled.

    Raises:
        ValueError: If configuration is invalid (missing API key, etc.).
    """
    from PaperTracker.config import AppConfig

    if not config.llm_enabled:
        return None

    # Get API key from environment
    api_key_env = config.llm_api_key_env or "OPENAI_API_KEY"
    api_key = os.getenv(api_key_env)

    if not api_key:
        raise ValueError(
            f"LLM enabled but {api_key_env} environment variable not set. "
            f"Set it in your .env file or shell environment."
        )

    # Create HTTP client with retry configuration
    client = LLMApiClient(
        base_url=config.llm_base_url,
        api_key=api_key,
        timeout=config.llm_timeout,
        max_retries=config.llm_max_retries,
        retry_base_delay=config.llm_retry_base_delay,
        retry_max_delay=config.llm_retry_max_delay,
        timeout_multiplier=config.llm_retry_timeout_multiplier,
    )

    # Create provider based on config
    provider_type = config.llm_provider.lower()

    if provider_type == "openai-compat":
        provider: LLMProvider = OpenAICompatProvider(
            name=f"OpenAI-Compatible ({config.llm_model})",
            client=client,
            model=config.llm_model,
            temperature=config.llm_temperature,
            max_tokens=config.llm_max_tokens,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}")

    # Create service
    service = LLMService(
        provider=provider,
        target_lang=config.llm_target_lang,
        max_workers=config.llm_max_workers,
        enabled=True,
        enable_translation=config.llm_enable_translation,
        enable_summary=config.llm_enable_summary,
    )

    log.info(
        "LLM service created: provider=%s model=%s lang=%s translation=%s summary=%s",
        provider.name,
        config.llm_model,
        config.llm_target_lang,
        config.llm_enable_translation,
        config.llm_enable_summary,
    )

    return service


__all__ = [
    "LLMProvider",
    "LLMService",
    "OpenAICompatProvider",
    "create_llm_service",
]
