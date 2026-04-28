"""Unit tests for PubMedApiClient (mock requests)."""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from PaperTracker.sources.pubmed.client import EFETCH_MAX_PMIDS, PubMedApiClient


def _mock_response(body: str | dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    if isinstance(body, dict):
        mock.json.return_value = body
        mock.text = json.dumps(body)
    else:
        mock.text = body
        mock.json.return_value = json.loads(body) if body.startswith("{") else {}
    return mock


class TestPubMedApiClientEsearch(unittest.TestCase):
    def _client(self, **kwargs: object) -> PubMedApiClient:
        return PubMedApiClient(**kwargs)  # type: ignore[arg-type]

    def test_esearch_unwraps_esearchresult(self) -> None:
        payload = {
            "header": {"type": "esearch"},
            "esearchresult": {
                "idlist": ["11111111", "22222222", "33333333"],
                "count": "3",
            },
        }
        client = self._client()
        with patch.object(client._session, "get", return_value=_mock_response(payload)):
            result = client.esearch(term="cancer", retstart=0, retmax=10)
        self.assertEqual(result["idlist"], ["11111111", "22222222", "33333333"])
        self.assertEqual(result["count"], 3)
        self.assertIsInstance(result["count"], int)

    def test_tool_empty_not_sent(self) -> None:
        payload = {
            "esearchresult": {"idlist": [], "count": "0"},
        }
        client = PubMedApiClient(tool="", email="")
        with patch.object(client._session, "get", return_value=_mock_response(payload)) as mock_get:
            client.esearch(term="test", retstart=0, retmax=5)
            call_kwargs = mock_get.call_args
            params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
            self.assertNotIn("tool", params)
            self.assertNotIn("email", params)

    def test_email_empty_not_sent(self) -> None:
        payload = {
            "esearchresult": {"idlist": [], "count": "0"},
        }
        client = PubMedApiClient(email="")
        with patch.object(client._session, "get", return_value=_mock_response(payload)) as mock_get:
            client.esearch(term="test", retstart=0, retmax=5)
            call_kwargs = mock_get.call_args
            params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
            self.assertNotIn("email", params)

    def test_api_key_none_not_sent(self) -> None:
        payload = {
            "esearchresult": {"idlist": [], "count": "0"},
        }
        client = PubMedApiClient(api_key=None)
        with patch.object(client._session, "get", return_value=_mock_response(payload)) as mock_get:
            client.esearch(term="test", retstart=0, retmax=5)
            call_kwargs = mock_get.call_args
            params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
            self.assertNotIn("api_key", params)

    def test_api_key_sent_when_provided(self) -> None:
        payload = {
            "esearchresult": {"idlist": [], "count": "0"},
        }
        client = PubMedApiClient(api_key="mykey123")
        with patch.object(client._session, "get", return_value=_mock_response(payload)) as mock_get:
            client.esearch(term="test", retstart=0, retmax=5)
            call_kwargs = mock_get.call_args
            params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
            self.assertEqual(params.get("api_key"), "mykey123")


class TestPubMedApiClientEfetch(unittest.TestCase):
    def test_efetch_returns_xml(self) -> None:
        xml_body = "<PubmedArticleSet><PubmedArticle/></PubmedArticleSet>"
        client = PubMedApiClient()
        with patch.object(client._session, "get", return_value=_mock_response(xml_body)):
            result = client.efetch(pmids=["12345678"])
        self.assertEqual(result, xml_body)

    def test_efetch_over_limit_raises(self) -> None:
        client = PubMedApiClient()
        too_many = [str(i) for i in range(EFETCH_MAX_PMIDS + 1)]
        with self.assertRaises(ValueError) as ctx:
            client.efetch(pmids=too_many)
        self.assertIn("exceeds", str(ctx.exception))

    def test_efetch_exactly_at_limit(self) -> None:
        xml_body = "<PubmedArticleSet></PubmedArticleSet>"
        client = PubMedApiClient()
        exactly = [str(i) for i in range(EFETCH_MAX_PMIDS)]
        with patch.object(client._session, "get", return_value=_mock_response(xml_body)):
            result = client.efetch(pmids=exactly)
        self.assertEqual(result, xml_body)


if __name__ == "__main__":
    unittest.main()
