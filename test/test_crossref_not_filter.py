"""Tests for Crossref NOT-term post-fetch filter."""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from PaperTracker.core.models import Paper
from PaperTracker.sources.crossref.query import apply_not_filter, extract_not_terms
from PaperTracker.core.query import FieldQuery, SearchQuery


def _make_paper(title: str = "", abstract: str = "") -> Paper:
    return Paper(
        source="crossref",
        id="test-id",
        title=title,
        authors=(),
        abstract=abstract,
        published=None,
        updated=None,
    )


def _make_query(not_terms: list[str]) -> SearchQuery:
    return SearchQuery(
        name="test",
        fields={"TEXT": FieldQuery(NOT=tuple(not_terms))},
    )


class TestExtractNotTerms(unittest.TestCase):
    def test_empty_query_returns_empty_set(self) -> None:
        query = _make_query([])
        result = extract_not_terms(query=query)
        self.assertEqual(result, frozenset())

    def test_single_not_term(self) -> None:
        query = _make_query(["survey"])
        result = extract_not_terms(query=query)
        self.assertEqual(result, frozenset({"survey"}))

    def test_terms_are_casefolded(self) -> None:
        query = _make_query(["Survey", "REVIEW"])
        result = extract_not_terms(query=query)
        self.assertEqual(result, frozenset({"survey", "review"}))

    def test_scope_not_terms_are_included(self) -> None:
        query = _make_query(["survey"])
        scope = _make_query(["review"])
        result = extract_not_terms(query=query, scope=scope)
        self.assertEqual(result, frozenset({"survey", "review"}))

    def test_none_scope_is_ignored(self) -> None:
        query = _make_query(["survey"])
        result = extract_not_terms(query=query, scope=None)
        self.assertEqual(result, frozenset({"survey"}))


class TestApplyNotFilter(unittest.TestCase):
    def test_empty_not_terms_returns_all_papers(self) -> None:
        papers = [_make_paper("A Survey of ML"), _make_paper("Diffusion Models")]
        result = apply_not_filter(papers, frozenset())
        self.assertEqual(result, papers)

    def test_filters_paper_with_not_term_in_title(self) -> None:
        keep = _make_paper("Diffusion Models in Vision")
        drop = _make_paper("A Survey of Diffusion Models")
        result = apply_not_filter([keep, drop], frozenset({"survey"}))
        self.assertEqual(result, [keep])

    def test_filters_paper_with_not_term_in_abstract(self) -> None:
        keep = _make_paper("Diffusion Models", abstract="We propose a new method.")
        drop = _make_paper("Diffusion Models", abstract="This survey reviews recent work.")
        result = apply_not_filter([keep, drop], frozenset({"survey"}))
        self.assertEqual(result, [keep])

    def test_matching_is_case_insensitive(self) -> None:
        drop = _make_paper("A SURVEY of Methods")
        result = apply_not_filter([drop], frozenset({"survey"}))
        self.assertEqual(result, [])

    def test_multiple_not_terms(self) -> None:
        keep = _make_paper("Diffusion Models")
        drop_survey = _make_paper("A Survey of Methods")
        drop_review = _make_paper("Review of Transformers")
        result = apply_not_filter([keep, drop_survey, drop_review], frozenset({"survey", "review"}))
        self.assertEqual(result, [keep])

    def test_empty_paper_list(self) -> None:
        result = apply_not_filter([], frozenset({"survey"}))
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
