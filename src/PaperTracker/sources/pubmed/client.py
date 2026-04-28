"""PubMed NCBI E-utilities API client.

Calls ESearch and EFetch endpoints over HTTP, with retry/backoff for transient errors.
"""

from __future__ import annotations

import random
import time
from collections.abc import Sequence
from typing import Any

import requests

from PaperTracker.utils.log import log

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
DEFAULT_TIMEOUT = 30.0
MAX_ATTEMPTS = 4
BASE_PAUSE = 0.8
MAX_SLEEP = 15.0
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
EFETCH_MAX_PMIDS = 200


class PubMedApiClient:
    """Low-level HTTP client for the NCBI E-utilities ESearch and EFetch APIs."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        tool: str = "paper-tracker",
        email: str = "",
    ) -> None:
        """Initialize client with optional NCBI credentials.

        Args:
            api_key: NCBI API key. When provided, rate limit rises to 10 req/s.
            tool: Tool identifier sent to NCBI for polite usage tracking.
            email: Contact email sent to NCBI. Skipped when empty.
        """
        self._api_key = api_key or None
        self._tool = tool
        self._email = email
        self._session = requests.Session()

    def esearch(
        self,
        *,
        term: str,
        retstart: int,
        retmax: int,
        mindate: str | None = None,
        maxdate: str | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Run an ESearch query and return the unwrapped esearchresult.

        Args:
            term: PubMed search term string.
            retstart: Zero-based offset of the first result to return.
            retmax: Maximum number of PMIDs to return.
            mindate: Optional start date in YYYY/MM/DD format.
            maxdate: Optional end date in YYYY/MM/DD format.
            timeout: Optional request timeout in seconds.

        Returns:
            Unwrapped ``esearchresult`` dict with ``idlist`` (list of str)
            and ``count`` (int).
        """
        params: dict[str, str] = {
            "db": "pubmed",
            "retmode": "json",
            "sort": "pub_date",
            "datetype": "pdat",
            "term": term,
            "retstart": str(retstart),
            "retmax": str(retmax),
        }
        if mindate:
            params["mindate"] = mindate
        if maxdate:
            params["maxdate"] = maxdate
        self._attach_credentials(params)

        response = self._get_with_retry(ESEARCH_URL, params=params, timeout=timeout or DEFAULT_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        result = payload["esearchresult"]
        return {
            "idlist": result.get("idlist", []),
            "count": int(result.get("count", 0)),
        }

    def efetch(
        self,
        *,
        pmids: Sequence[str],
        timeout: float | None = None,
    ) -> str:
        """Fetch full records for a list of PMIDs and return PubmedArticleSet XML.

        Args:
            pmids: List of PMID strings to fetch.
            timeout: Optional request timeout in seconds.

        Returns:
            PubmedArticleSet XML string.

        Raises:
            ValueError: If len(pmids) exceeds EFETCH_MAX_PMIDS.
        """
        if len(pmids) > EFETCH_MAX_PMIDS:
            raise ValueError(
                f"efetch() received {len(pmids)} PMIDs, which exceeds the safe GET limit "
                f"of {EFETCH_MAX_PMIDS}. Reduce fetch_batch_size."
            )

        params: dict[str, str] = {
            "db": "pubmed",
            "retmode": "xml",
            "id": ",".join(pmids),
        }
        self._attach_credentials(params)

        response = self._get_with_retry(EFETCH_URL, params=params, timeout=timeout or DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response.text

    def close(self) -> None:
        """Close HTTP session and release pooled connections."""
        self._session.close()

    def _get_with_retry(self, url: str, *, params: dict[str, str], timeout: float) -> requests.Response:
        """Issue GET request with retries for transient failures."""
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self._session.get(url, params=params, timeout=timeout)
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
                    log.debug(
                        "PubMed retry attempt=%d/%d delay=%.2fs error=%s",
                        attempt,
                        MAX_ATTEMPTS,
                        delay,
                        error,
                    )
                    time.sleep(delay)

        assert last_error is not None
        raise last_error

    def _attach_credentials(self, params: dict[str, str]) -> None:
        """Attach API key, tool, and email to params when non-empty."""
        if self._api_key:
            params["api_key"] = self._api_key
        if self._tool:
            params["tool"] = self._tool
        if self._email:
            params["email"] = self._email
