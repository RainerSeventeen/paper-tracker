"""HTTP client for OpenAI-compatible chat completion APIs."""

from __future__ import annotations

import json
import re
from typing import Any

import requests

from PaperTracker.utils.log import log


def normalize_endpoint(base_url: str) -> str:
    """Normalize base URL to full chat completions endpoint.

    Supports three input formats:
    1. https://api.xxx.com → https://api.xxx.com/v1/chat/completions
    2. https://api.xxx.com/v1 → https://api.xxx.com/v1/chat/completions
    3. https://api.xxx.com/v1/chat/completions → (unchanged)

    Args:
        base_url: Base URL or partial endpoint.

    Returns:
        Full chat completions endpoint URL.

    Raises:
        ValueError: If base_url is empty.
    """
    if not base_url:
        raise ValueError("base_url cannot be empty")

    url = base_url.rstrip("/")

    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return url + "/chat/completions"
    return url + "/v1/chat/completions"


def extract_json(text: str) -> dict[str, Any]:
    """Extract first JSON object from text (loose parsing).

    Useful for handling LLM responses that may include extra text
    before/after the JSON object.

    Args:
        text: Text potentially containing JSON.

    Returns:
        Parsed JSON object, or empty dict if parsing fails.
    """
    # Find first {...} block
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}

    json_str = match.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Try fixing common issues (trailing commas)
        fixed = re.sub(r",\s*([}\]])", r"\1", json_str)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return {}


class LLMApiClient:
    """HTTP client for OpenAI-compatible chat completion APIs.

    Supports any provider following the OpenAI chat completions API spec,
    including DeepSeek, SiliconFlow, Anthropic (via proxy), etc.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
    ) -> None:
        """Initialize API client.

        Args:
            base_url: Base URL (will be normalized to full endpoint).
            api_key: API authentication key.
            timeout: Request timeout in seconds.
        """
        self.endpoint = normalize_endpoint(base_url)
        self.api_key = api_key
        self.timeout = timeout
        log.debug("LLMApiClient initialized: endpoint=%s timeout=%d", self.endpoint, timeout)

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        """Send chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Model identifier (e.g., 'gpt-4o-mini', 'deepseek-chat').
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens in response.

        Returns:
            Response text from the model.

        Raises:
            requests.HTTPError: If API request fails.
            KeyError: If response format is unexpected.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        log.debug("Sending chat completion: model=%s messages=%d", model, len(messages))

        response = requests.post(
            self.endpoint,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = response.json()

        # Standard OpenAI format
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            # Fallback for non-standard implementations
            log.warning("Unexpected API response format: %s", e)
            return data.get("choices", [{}])[0].get("text", "")
