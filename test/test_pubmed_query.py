"""Unit tests for PubMed query compiler."""

from __future__ import annotations

import unittest

from PaperTracker.core.query import FieldQuery, SearchQuery
from PaperTracker.sources.pubmed.query import compile_pubmed_term


def _make_query(**fields: FieldQuery) -> SearchQuery:
    return SearchQuery(name=None, fields=fields)


class TestCompilePubmedTerm(unittest.TestCase):
    def test_text_and_single(self) -> None:
        query = _make_query(TEXT=FieldQuery(AND=("machine learning",)))
        result = compile_pubmed_term(query=query)
        self.assertEqual(result, '"machine learning"[TIAB]')

    def test_text_and_multiple(self) -> None:
        query = _make_query(TEXT=FieldQuery(AND=("deep learning", "cancer")))
        result = compile_pubmed_term(query=query)
        self.assertEqual(result, '"deep learning"[TIAB] AND "cancer"[TIAB]')

    def test_text_or_single(self) -> None:
        query = _make_query(TEXT=FieldQuery(OR=("alpha",)))
        result = compile_pubmed_term(query=query)
        self.assertEqual(result, '"alpha"[TIAB]')

    def test_text_or_multiple(self) -> None:
        query = _make_query(TEXT=FieldQuery(OR=("alpha", "beta")))
        result = compile_pubmed_term(query=query)
        self.assertIn('"alpha"[TIAB]', result)
        self.assertIn('"beta"[TIAB]', result)
        self.assertIn(" OR ", result)

    def test_text_not(self) -> None:
        query = _make_query(TEXT=FieldQuery(AND=("cancer",), NOT=("surgery",)))
        result = compile_pubmed_term(query=query)
        self.assertIn('"cancer"[TIAB]', result)
        self.assertIn('NOT', result)
        self.assertIn('"surgery"[TIAB]', result)

    def test_author_field(self) -> None:
        query = _make_query(AUTHOR=FieldQuery(AND=("Smith J",)))
        result = compile_pubmed_term(query=query)
        self.assertEqual(result, '"Smith J"[AU]')

    def test_journal_field(self) -> None:
        query = _make_query(JOURNAL=FieldQuery(AND=("Nature",)))
        result = compile_pubmed_term(query=query)
        self.assertEqual(result, '"Nature"[JT]')

    def test_category_only_raises(self) -> None:
        query = _make_query(CATEGORY=FieldQuery(OR=("cs.AI",)))
        with self.assertRaises(ValueError) as ctx:
            compile_pubmed_term(query=query)
        self.assertIn("CATEGORY-only", str(ctx.exception))

    def test_empty_fields_raises(self) -> None:
        # A query where all terms are empty strings after stripping
        query = _make_query(TEXT=FieldQuery(AND=("",), OR=("",)))
        with self.assertRaises(ValueError):
            compile_pubmed_term(query=query)

    def test_scope_and_query_combined(self) -> None:
        scope = _make_query(TEXT=FieldQuery(AND=("neuroscience",)))
        query = _make_query(TEXT=FieldQuery(OR=("fMRI", "EEG")))
        result = compile_pubmed_term(query=query, scope=scope)
        self.assertIn('"neuroscience"[TIAB]', result)
        self.assertIn(" AND ", result)
        self.assertTrue('"fMRI"[TIAB]' in result or '"EEG"[TIAB]' in result)

    def test_scope_category_only_with_valid_query(self) -> None:
        # scope is category-only (skipped), query has valid fields → should work
        scope = _make_query(CATEGORY=FieldQuery(OR=("cs.AI",)))
        query = _make_query(TEXT=FieldQuery(AND=("transformer",)))
        result = compile_pubmed_term(query=query, scope=scope)
        self.assertIn('"transformer"[TIAB]', result)

    def test_title_maps_to_tiab(self) -> None:
        query = _make_query(TITLE=FieldQuery(AND=("CRISPR",)))
        result = compile_pubmed_term(query=query)
        self.assertEqual(result, '"CRISPR"[TIAB]')

    def test_abstract_maps_to_tiab(self) -> None:
        query = _make_query(ABSTRACT=FieldQuery(AND=("genome editing",)))
        result = compile_pubmed_term(query=query)
        self.assertEqual(result, '"genome editing"[TIAB]')


if __name__ == "__main__":
    unittest.main()
