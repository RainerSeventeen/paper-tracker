"""OpenAlex API client."""

from __future__ import annotations

import random
import time
from collections.abc import Iterator
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

        items: list[dict[str, Any]] = []
        for batch in self.iter_works_pages(params=params, max_results=max_results, timeout=timeout):
            items.extend(batch)
            if len(items) >= max_results:
                break
        return items[:max_results]

    def iter_works_pages(
        self,
        *,
        params: Mapping[str, str] | None,
        max_results: int,
        timeout: float | None = None,
    ) -> Iterator[list[dict[str, Any]]]:
        """Iterate OpenAlex works payload pages.

        Args:
            params: Compiled OpenAlex query parameters.
            max_results: Maximum number of raw upstream items to fetch.
            timeout: Optional request timeout in seconds.

        Yields:
            OpenAlex raw work payloads per page.
        """
        if max_results <= 0:
            return

        fetched = 0
        page = 1
        while fetched < max_results:
            page_size = min(MAX_PER_PAGE, max_results - fetched)
            batch = self.fetch_works_page(
                params=params,
                page=page,
                page_size=page_size,
                timeout=timeout,
            )
            if not batch:
                break

            fetched += len(batch)
            yield batch
            if len(batch) < page_size:
                break
            page += 1

    def fetch_works_page(
        self,
        *,
        params: Mapping[str, str] | None,
        page: int,
        page_size: int,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch one OpenAlex works page.

        Args:
            params: Compiled OpenAlex query parameters.
            page: One-based page index.
            page_size: Number of items requested in this page.
            timeout: Optional request timeout in seconds.

        Returns:
            A list of OpenAlex work payload mappings.
        """
        if page <= 0 or page_size <= 0:
            return []

        query_params = self._normalize_params(params)
        request_timeout = timeout or DEFAULT_TIMEOUT
        page_params = {
            **query_params,
            "per-page": str(min(MAX_PER_PAGE, page_size)),
            "page": str(page),
            "sort": OPENALEX_SORT,
        }
        response = self._get_with_retry(params=page_params, timeout=request_timeout)
        response.raise_for_status()
        return _extract_results(response.json())

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
