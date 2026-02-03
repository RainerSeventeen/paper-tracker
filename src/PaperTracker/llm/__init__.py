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

    if not config.llm.enabled:
        return None

    # Get API key from environment
    api_key_env = config.llm.api_key_env or "OPENAI_API_KEY"
    api_key = os.getenv(api_key_env)

    if not api_key:
        raise ValueError(
            f"LLM enabled but {api_key_env} environment variable not set. "
            f"Set it in your .env file or shell environment."
        )

    # Create HTTP client with retry configuration
    client = LLMApiClient(
        base_url=config.llm.base_url,
        api_key=api_key,
        timeout=config.llm.timeout,
        max_retries=config.llm.max_retries,
        retry_base_delay=config.llm.retry_base_delay,
        retry_max_delay=config.llm.retry_max_delay,
        timeout_multiplier=config.llm.retry_timeout_multiplier,
    )

    # Create provider based on config
    provider_type = config.llm.provider.lower()

    if provider_type == "openai-compat":
        provider: LLMProvider = OpenAICompatProvider(
            name=f"OpenAI-Compatible ({config.llm.model})",
            client=client,
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}")

    # Create service
    service = LLMService(
        provider=provider,
        target_lang=config.llm.target_lang,
        max_workers=config.llm.max_workers,
        enabled=True,
        enable_translation=config.llm.enable_translation,
        enable_summary=config.llm.enable_summary,
    )

    log.info(
        "LLM service created: provider=%s model=%s lang=%s translation=%s summary=%s",
        provider.name,
        config.llm.model,
        config.llm.target_lang,
        config.llm.enable_translation,
        config.llm.enable_summary,
    )

    return service


__all__ = [
    "LLMProvider",
    "LLMService",
    "OpenAICompatProvider",
    "create_llm_service",
]
