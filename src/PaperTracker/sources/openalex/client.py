"""OpenAlex API client."""

from __future__ import annotations

import random
import time
from typing import Any
from typing import Mapping

import requests

from PaperTracker.utils.log import log

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
DEFAULT_TIMEOUT = 30.0
MAX_ATTEMPTS = 4
BASE_PAUSE = 0.8
MAX_SLEEP = 8.0
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_PER_PAGE = 200
OPENALEX_SORT = "publication_date:desc"

HEADERS = {
    "User-Agent": "paper-tracker/0.1 (+https://github.com/RainerSeventeen/paper-tracker)",
    "Accept": "application/json",
}


class OpenAlexApiClient:
    """Low-level HTTP client for the OpenAlex Works API."""

    def __init__(self) -> None:
        """Initialize client with reusable HTTP session."""
        self._session = requests.Session()

    def close(self) -> None:
        """Close HTTP session and release pooled connections."""
        self._session.close()

    def fetch_works(
        self,
        *,
        params: Mapping[str, str] | None,
        max_results: int,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch OpenAlex works payloads with pagination.

        Args:
            params: Compiled OpenAlex query parameters.
            max_results: Maximum number of items to collect.
            timeout: Optional request timeout in seconds.

        Returns:
            A list of OpenAlex work payload mappings.
        """
        if max_results <= 0:
            return []

        query_params = self._normalize_params(params)
        request_timeout = timeout or DEFAULT_TIMEOUT

        items: list[dict[str, Any]] = []
        page = 1
        while len(items) < max_results:
            page_size = min(MAX_PER_PAGE, max_results - len(items))
            page_params = {
                **query_params,
                "per-page": str(page_size),
                "page": str(page),
                "sort": OPENALEX_SORT,
            }
            response = self._get_with_retry(params=page_params, timeout=request_timeout)
            response.raise_for_status()

            payload = response.json()
            batch = _extract_results(payload)
            if not batch:
                break

            items.extend(batch)
            if len(batch) < page_size:
                break
            page += 1

        return items[:max_results]

    def _get_with_retry(self, *, params: dict[str, str], timeout: float) -> requests.Response:
        """Issue GET request with retries for transient failures."""
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self._session.get(
                    OPENALEX_WORKS_URL,
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
                    log.debug("OpenAlex retry attempt=%d/%d delay=%.2fs error=%s", attempt, MAX_ATTEMPTS, delay, error)
                    time.sleep(delay)

        assert last_error is not None
        raise last_error

    @staticmethod
    def _normalize_params(params: Mapping[str, str] | None) -> dict[str, str]:
        """Normalize query parameters by dropping empty keys and values."""
        if not params:
            return {}

        normalized: dict[str, str] = {}
        for key, value in params.items():
            normalized_key = str(key).strip()
            normalized_value = str(value).strip()
            if not normalized_key or not normalized_value:
                continue
            normalized[normalized_key] = normalized_value
        return normalized


def _extract_results(payload: Any) -> list[dict[str, Any]]:
    """Extract ``results`` as a list of dict items from OpenAlex payload."""
    if not isinstance(payload, dict):
        return []

    results = payload.get("results")
    if not isinstance(results, list):
        return []

    return [item for item in results if isinstance(item, dict)]
