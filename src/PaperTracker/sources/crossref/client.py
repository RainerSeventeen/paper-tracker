"""Crossref API client."""

from __future__ import annotations

import random
import time
from typing import Any
from typing import Mapping

import requests

from PaperTracker.utils.log import log

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
DEFAULT_TIMEOUT = 30.0
MAX_ATTEMPTS = 4
BASE_PAUSE = 0.8
MAX_SLEEP = 8.0
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

HEADERS = {
    "User-Agent": "paper-tracker/0.1 (+https://github.com/RainerSeventeen/paper-tracker)",
    "Accept": "application/json",
}


class CrossrefApiClient:
    """Low-level HTTP client for the Crossref REST API."""

    def __init__(self) -> None:
        """Initialize the client with a reusable HTTP session.
        """
        self._session = requests.Session()

    def close(self) -> None:
        """Close the underlying HTTP session.
        """
        self._session.close()

    def fetch_works(
        self,
        *,
        query_params: Mapping[str, str] | None,
        max_results: int,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch work items from Crossref.

        Args:
            query_params: Compiled Crossref ``query.*`` parameters.
            max_results: Number of items to request.
            timeout: Request timeout in seconds.

        Returns:
            List of Crossref work item mappings.
        """
        params = {
            "rows": str(max_results),
            "sort": "updated",
            "order": "desc",
        }
        if query_params:
            for key, value in query_params.items():
                normalized_key = str(key).strip()
                normalized_value = str(value).strip()
                if not normalized_key or not normalized_value:
                    continue
                params[normalized_key] = normalized_value

        response = self._get_with_retry(params=params, timeout=timeout or DEFAULT_TIMEOUT)
        response.raise_for_status()

        payload = response.json()
        message = payload.get("message", {}) if isinstance(payload, dict) else {}
        items = message.get("items", []) if isinstance(message, dict) else []
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]

    def _get_with_retry(self, *, params: dict[str, str], timeout: float) -> requests.Response:
        """Issue GET with retries for transient failures."""
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self._session.get(
                    CROSSREF_WORKS_URL,
                    params=params,
                    headers=HEADERS,
                    timeout=timeout,
                )
                if response.status_code in RETRYABLE_STATUS:
                    raise requests.HTTPError(
                        f"HTTP {response.status_code}",
                        response=response,
                    )
                return response
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as error:
                last_error = error
                if isinstance(error, requests.HTTPError):
                    status_code = getattr(error.response, "status_code", None)
                    if status_code not in RETRYABLE_STATUS:
                        raise
                if attempt < MAX_ATTEMPTS:
                    delay = min(BASE_PAUSE * (2 ** (attempt - 1)) + random.uniform(0, 0.3), MAX_SLEEP)
                    log.debug("Crossref retry attempt=%d/%d delay=%.2fs error=%s", attempt, MAX_ATTEMPTS, delay, error)
                    time.sleep(delay)

        assert last_error is not None
        raise last_error
