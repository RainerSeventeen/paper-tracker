"""HTTP client for OpenAI-compatible chat completion APIs."""

from __future__ import annotations

import json
import random
import re
import time
from typing import Any, Final

import requests

from PaperTracker.utils.log import log


# Retryable HTTP status codes
RETRYABLE_STATUS: Final[set[int]] = {429, 500, 502, 503, 504}


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

    Supports configurable retry with exponential backoff.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        retry_max_delay: float = 10.0,
        timeout_multiplier: float = 1.0,
    ) -> None:
        """Initialize API client with retry configuration.

        Args:
            base_url: Base URL (will be normalized to full endpoint).
            api_key: API authentication key.
            timeout: Base request timeout in seconds.
            max_retries: Maximum number of retry attempts.
            retry_base_delay: Base delay for exponential backoff (seconds).
            retry_max_delay: Maximum delay between retries (seconds).
            timeout_multiplier: Timeout multiplier for each retry.
        """
        self.endpoint = normalize_endpoint(base_url)
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.retry_max_delay = retry_max_delay
        self.timeout_multiplier = timeout_multiplier

        log.debug(
            "LLMApiClient initialized: endpoint=%s timeout=%d max_retries=%d",
            self.endpoint,
            timeout,
            max_retries,
        )

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        """Send chat completion request with automatic retry.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Model identifier (e.g., 'gpt-4o-mini', 'deepseek-chat').
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens in response.

        Returns:
            Response text from the model.

        Raises:
            requests.HTTPError: If API request fails after all retries.
            requests.Timeout: If request times out after all retries.
            requests.ConnectionError: If connection fails after all retries.
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

        return self._post_with_retry(
            endpoint=self.endpoint,
            json=payload,
            headers=headers,
        )

    def _post_with_retry(
        self,
        endpoint: str,
        json: dict,
        headers: dict,
    ) -> str:
        """Execute POST request with retry logic.

        Args:
            endpoint: Full API endpoint URL.
            json: Request payload.
            headers: HTTP headers.

        Returns:
            Response content (message text).

        Raises:
            Exception: Last observed error after all retries exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):  # 0-indexed: 0, 1, 2, 3
            try:
                # Calculate dynamic timeout for this attempt
                current_timeout = self.timeout * (self.timeout_multiplier ** attempt)

                log.debug(
                    "LLM request attempt %d/%d: timeout=%.1fs",
                    attempt + 1,
                    self.max_retries + 1,
                    current_timeout,
                )

                response = requests.post(
                    endpoint,
                    json=json,
                    headers=headers,
                    timeout=current_timeout,
                )

                # Check for retryable HTTP errors
                if response.status_code in RETRYABLE_STATUS:
                    raise requests.HTTPError(
                        f"HTTP {response.status_code}",
                        response=response,
                    )

                # Raise for other HTTP errors (4xx, non-retryable 5xx)
                response.raise_for_status()

                # Success: parse and return
                data = response.json()
                try:
                    return data["choices"][0]["message"]["content"]
                except (KeyError, IndexError) as e:
                    log.warning("Unexpected API response format: %s", e)
                    return data.get("choices", [{}])[0].get("text", "")

            except (
                requests.Timeout,
                requests.ConnectionError,
            ) as e:
                last_error = e
                log.debug("LLM request failed (network): %s", type(e).__name__)

            except requests.HTTPError as e:
                last_error = e
                status = getattr(e.response, "status_code", None)

                # Don't retry client errors (except 429)
                if status and status not in RETRYABLE_STATUS:
                    log.error("LLM request failed (non-retryable): HTTP %s", status)
                    raise

                log.debug("LLM request failed (retryable): HTTP %s", status)

            # If not last attempt, wait before retry
            if attempt < self.max_retries:
                delay = self._calculate_backoff_delay(attempt)
                log.info(
                    "LLM retry %d/%d after %.1fs (error: %s)",
                    attempt + 1,
                    self.max_retries,
                    delay,
                    last_error,
                )
                time.sleep(delay)

        # All retries exhausted
        log.error(
            "LLM request failed after %d attempts: %s",
            self.max_retries + 1,
            last_error,
        )
        assert last_error is not None
        raise last_error

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter.

        Args:
            attempt: Current attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        # Exponential: base_delay * 2^attempt
        exponential_delay = self.retry_base_delay * (2 ** attempt)

        # Cap at max delay
        capped_delay = min(exponential_delay, self.retry_max_delay)

        # Add random jitter (±25%)
        jitter = random.uniform(0.75, 1.25)

        return capped_delay * jitter
