"""arXiv API client.

Calls the arXiv Atom API over HTTP, with retry/backoff and HTTPS→HTTP fallback.
"""

from __future__ import annotations

import random
import time
from typing import Optional

import requests

from PaperTracker.utils.log import log

ARXIV_HTTPS = "https://export.arxiv.org/api/query"
ARXIV_HTTP = "http://export.arxiv.org/api/query"

DEFAULT_TIMEOUT = 45.0
MAX_ATTEMPTS = 6
BASE_PAUSE = 1.5
MAX_SLEEP = 20
TOO_MANY_REQUESTS_BASE_PAUSE = 5.0
TOO_MANY_REQUESTS_MAX_SLEEP = 120.0

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

HEADERS = {
    "User-Agent": "paper-tracker/0.1 (+https://github.com/RainerSeventeen/paper-tracker)",
    "Accept": "application/atom+xml,application/xml;q=0.9,*/*;q=0.8",
}


class ArxivApiClient:
    """Low-level HTTP client for the arXiv Atom API.

    Responsible only for making network requests and returning the raw feed XML.
    Parsing and domain mapping are handled elsewhere.
    """

    def __init__(self) -> None:
        """Initialize the client with a reusable HTTP session.
        """
        self._session = requests.Session()

    def close(self) -> None:
        """Close the underlying HTTP session and release pooled connections.
        """
        self._session.close()

    def __enter__(self) -> ArxivApiClient:
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and close session."""
        self.close()

    def fetch_feed(
        self,
        *,
        search_query: str,
        start: int = 0,
        max_results: int = 10,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
        timeout: Optional[float] = None,
    ) -> str:
        """Fetch arXiv Atom feed XML using the official API endpoint.

        Args:
            search_query: arXiv API search_query string.
            start: Start offset.
            max_results: Maximum number of results.
            sort_by: Sort field.
            sort_order: Sort order.
            timeout: Optional request timeout in seconds.

        Returns:
            Atom feed XML text.

        Raises:
            Exception: Propagates the last request error after retries and HTTPS/HTTP fallback.
        """
        params = {
            "search_query": search_query,
            "start": str(start),
            "max_results": str(max_results),
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        last_err: Exception | None = None
        for base_url in (ARXIV_HTTPS, ARXIV_HTTP):
            try:
                log.debug(
                    "arXiv fetch feed: base_url=%s start=%s max_results=%s sort_by=%s sort_order=%s",
                    base_url,
                    start,
                    max_results,
                    sort_by,
                    sort_order,
                )
                resp = self._get_with_retry(base_url, params=params, timeout=timeout)
                resp.raise_for_status()
                log.debug("arXiv response ok: status=%s bytes=%s", resp.status_code, len(resp.text))
                return resp.text
            except Exception as e:  # noqa: BLE001 - keep last error for fallback
                last_err = e
                log.debug("arXiv fetch failed for %s: %s", base_url, e)
                continue

        assert last_err is not None
        raise last_err

    def _get_with_retry(
        self,
        base_url: str,
        *,
        params: dict[str, str],
        timeout: Optional[float],
    ) -> requests.Response:
        """Issue GET request with retry/backoff.

        Retries on timeouts/connection errors and selected HTTP status codes.

        Args:
            base_url: Endpoint base URL.
            params: Query parameters.
            timeout: Optional timeout seconds.

        Returns:
            requests.Response on success.

        Raises:
            Exception: Last observed error when all attempts failed.
        """
        timeout = timeout or DEFAULT_TIMEOUT
        last_err: Exception | None = None
        last_status_code: int | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            last_status_code = None
            try:
                log.debug("arXiv request attempt %d/%d to %s", attempt, MAX_ATTEMPTS, base_url)
                resp = self._session.get(base_url, params=params, headers=HEADERS, timeout=timeout)
                if resp.status_code in RETRYABLE_STATUS:
                    raise requests.exceptions.HTTPError(
                        f"HTTP {resp.status_code}",
                        response=resp,
                    )
                return resp
            except (
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError,
            ) as e:
                last_err = e
            except requests.exceptions.HTTPError as e:
                last_err = e
                st = getattr(e.response, "status_code", None)
                last_status_code = st if isinstance(st, int) else None
                if st not in RETRYABLE_STATUS:
                    break

            if attempt < MAX_ATTEMPTS:
                log.debug("arXiv retrying after attempt %d (error=%s)", attempt, last_err)
                self._sleep_backoff(attempt, status_code=last_status_code)

        assert last_err is not None
        raise last_err

    @staticmethod
    def _sleep_backoff(attempt: int, *, status_code: int | None = None) -> None:
        """Sleep with status-aware backoff.

        Args:
            attempt: Current attempt index (1-based).
            status_code: Last HTTP status code when available.
        """
        if status_code == 429:
            # arXiv does not provide reliable Retry-After for 429; use fixed exponential backoff.
            delay = min(TOO_MANY_REQUESTS_BASE_PAUSE * (2 ** (attempt - 1)), TOO_MANY_REQUESTS_MAX_SLEEP)
            time.sleep(delay)
            return

        delay = min(BASE_PAUSE * (2 ** (attempt - 1)) + random.uniform(0, 0.5), MAX_SLEEP)
        time.sleep(delay)
