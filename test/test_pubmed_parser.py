"""Unit tests for PubMed XML parser."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from PaperTracker.sources.pubmed.parser import parse_pubmed_xml

_MINIMAL_ARTICLE = """\
<PubmedArticle>
  <MedlineCitation>
    <PMID>12345678</PMID>
    <Article>
      <ArticleTitle>Test Title</ArticleTitle>
      <Abstract>
        <AbstractText>Simple abstract text.</AbstractText>
      </Abstract>
      <AuthorList>
        <Author>
          <LastName>Smith</LastName>
          <ForeName>John</ForeName>
        </Author>
      </AuthorList>
      <ArticleDate DateType="Electronic">
        <Year>2024</Year>
        <Month>3</Month>
        <Day>15</Day>
      </ArticleDate>
      <Journal>
        <Title>Nature Medicine</Title>
        <JournalIssue>
          <PubDate>
            <Year>2024</Year>
            <Month>Mar</Month>
          </PubDate>
        </JournalIssue>
      </Journal>
    </Article>
  </MedlineCitation>
  <PubmedData>
    <ArticleIdList>
      <ArticleId IdType="pubmed">12345678</ArticleId>
      <ArticleId IdType="doi">10.1234/test.2024.001</ArticleId>
    </ArticleIdList>
  </PubmedData>
</PubmedArticle>"""

_NO_DOI_ARTICLE = """\
<PubmedArticle>
  <MedlineCitation>
    <PMID>99999999</PMID>
    <Article>
      <ArticleTitle>No DOI Article</ArticleTitle>
      <Abstract>
        <AbstractText>Abstract text here.</AbstractText>
      </Abstract>
      <Journal>
        <Title>Some Journal</Title>
        <JournalIssue>
          <PubDate><Year>2023</Year></PubDate>
        </JournalIssue>
      </Journal>
    </Article>
  </MedlineCitation>
  <PubmedData>
    <ArticleIdList>
      <ArticleId IdType="pubmed">99999999</ArticleId>
    </ArticleIdList>
  </PubmedData>
</PubmedArticle>"""


def _wrap(articles: str) -> str:
    return f"<PubmedArticleSet>{articles}</PubmedArticleSet>"


class TestParsePubmedXml(unittest.TestCase):
    def test_standard_single_abstract(self) -> None:
        xml = _wrap(_MINIMAL_ARTICLE)
        papers = parse_pubmed_xml(xml)
        self.assertEqual(len(papers), 1)
        paper = papers[0]
        self.assertEqual(paper.title, "Test Title")
        self.assertEqual(paper.abstract, "Simple abstract text.")
        self.assertEqual(paper.doi, "10.1234/test.2024.001")
        self.assertEqual(paper.id, "12345678")
        self.assertEqual(paper.source, "pubmed")

    def test_multi_section_abstract_with_labels(self) -> None:
        article = """\
<PubmedArticle>
  <MedlineCitation>
    <PMID>11111111</PMID>
    <Article>
      <ArticleTitle>Multi-section Abstract</ArticleTitle>
      <Abstract>
        <AbstractText Label="BACKGROUND">Background text.</AbstractText>
        <AbstractText Label="METHODS">Methods text.</AbstractText>
        <AbstractText Label="RESULTS">Results text.</AbstractText>
      </Abstract>
      <Journal>
        <Title>Some Journal</Title>
        <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
      </Journal>
    </Article>
  </MedlineCitation>
  <PubmedData>
    <ArticleIdList>
      <ArticleId IdType="doi">10.1234/multi.2024</ArticleId>
    </ArticleIdList>
  </PubmedData>
</PubmedArticle>"""
        papers = parse_pubmed_xml(_wrap(article))
        self.assertEqual(len(papers), 1)
        abstract = papers[0].abstract
        self.assertIn("BACKGROUND: Background text.", abstract)
        self.assertIn("METHODS: Methods text.", abstract)
        self.assertIn("RESULTS: Results text.", abstract)

    def test_title_with_inline_markup(self) -> None:
        article = """\
<PubmedArticle>
  <MedlineCitation>
    <PMID>22222222</PMID>
    <Article>
      <ArticleTitle>Role of <i>BRCA1</i> in <sub>2</sub> repair</ArticleTitle>
      <Journal>
        <Title>J</Title>
        <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
      </Journal>
    </Article>
  </MedlineCitation>
  <PubmedData>
    <ArticleIdList>
      <ArticleId IdType="doi">10.1234/italic.2024</ArticleId>
    </ArticleIdList>
  </PubmedData>
</PubmedArticle>"""
        papers = parse_pubmed_xml(_wrap(article))
        self.assertEqual(len(papers), 1)
        self.assertIn("BRCA1", papers[0].title)
        self.assertIn("repair", papers[0].title)

    def test_article_date_preferred_over_pub_date(self) -> None:
        xml = _wrap(_MINIMAL_ARTICLE)
        papers = parse_pubmed_xml(xml)
        # ArticleDate says 2024-03-15, PubDate says 2024-Mar
        self.assertEqual(papers[0].published, datetime(2024, 3, 15, tzinfo=timezone.utc))

    def test_pub_date_fallback_medline_date(self) -> None:
        article = """\
<PubmedArticle>
  <MedlineCitation>
    <PMID>33333333</PMID>
    <Article>
      <ArticleTitle>Medline Date Test</ArticleTitle>
      <Journal>
        <Title>J</Title>
        <JournalIssue>
          <PubDate>
            <MedlineDate>2024 Jan</MedlineDate>
          </PubDate>
        </JournalIssue>
      </Journal>
    </Article>
  </MedlineCitation>
  <PubmedData>
    <ArticleIdList>
      <ArticleId IdType="doi">10.1234/medline.2024</ArticleId>
    </ArticleIdList>
  </PubmedData>
</PubmedArticle>"""
        papers = parse_pubmed_xml(_wrap(article))
        self.assertEqual(len(papers), 1)
        pub = papers[0].published
        self.assertIsNotNone(pub)
        assert pub is not None
        self.assertEqual(pub.year, 2024)
        self.assertEqual(pub.month, 1)

    def test_no_doi_article_discarded(self) -> None:
        xml = _wrap(_NO_DOI_ARTICLE)
        papers = parse_pubmed_xml(xml)
        self.assertEqual(len(papers), 0)

    def test_mixed_with_and_without_doi(self) -> None:
        xml = _wrap(_MINIMAL_ARTICLE + _NO_DOI_ARTICLE)
        papers = parse_pubmed_xml(xml)
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].doi, "10.1234/test.2024.001")

    def test_author_name_concatenation(self) -> None:
        xml = _wrap(_MINIMAL_ARTICLE)
        papers = parse_pubmed_xml(xml)
        self.assertIn("John Smith", papers[0].authors)

    def test_author_last_name_only(self) -> None:
        article = """\
<PubmedArticle>
  <MedlineCitation>
    <PMID>44444444</PMID>
    <Article>
      <ArticleTitle>Lastonly</ArticleTitle>
      <AuthorList>
        <Author><LastName>Nakamura</LastName></Author>
      </AuthorList>
      <Journal>
        <Title>J</Title>
        <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
      </Journal>
    </Article>
  </MedlineCitation>
  <PubmedData>
    <ArticleIdList>
      <ArticleId IdType="doi">10.1234/last.2024</ArticleId>
    </ArticleIdList>
  </PubmedData>
</PubmedArticle>"""
        papers = parse_pubmed_xml(_wrap(article))
        self.assertIn("Nakamura", papers[0].authors)

    def test_mesh_terms_extracted_as_categories(self) -> None:
        article = """\
<PubmedArticle>
  <MedlineCitation>
    <PMID>55555555</PMID>
    <Article>
      <ArticleTitle>MeSH Test</ArticleTitle>
      <Journal>
        <Title>J</Title>
        <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
      </Journal>
    </Article>
    <MeshHeadingList>
      <MeshHeading>
        <DescriptorName>Neoplasms</DescriptorName>
      </MeshHeading>
      <MeshHeading>
        <DescriptorName>Genomics</DescriptorName>
      </MeshHeading>
    </MeshHeadingList>
  </MedlineCitation>
  <PubmedData>
    <ArticleIdList>
      <ArticleId IdType="doi">10.1234/mesh.2024</ArticleId>
    </ArticleIdList>
  </PubmedData>
</PubmedArticle>"""
        papers = parse_pubmed_xml(_wrap(article))
        self.assertIn("Neoplasms", papers[0].categories)
        self.assertIn("Genomics", papers[0].categories)

    def test_pmc_id_builds_pdf_link(self) -> None:
        article = """\
<PubmedArticle>
  <MedlineCitation>
    <PMID>66666666</PMID>
    <Article>
      <ArticleTitle>PMC Test</ArticleTitle>
      <Journal>
        <Title>J</Title>
        <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
      </Journal>
    </Article>
  </MedlineCitation>
  <PubmedData>
    <ArticleIdList>
      <ArticleId IdType="pubmed">66666666</ArticleId>
      <ArticleId IdType="pmc">PMC1234567</ArticleId>
      <ArticleId IdType="doi">10.1234/pmc.2024</ArticleId>
    </ArticleIdList>
  </PubmedData>
</PubmedArticle>"""
        papers = parse_pubmed_xml(_wrap(article))
        self.assertEqual(len(papers), 1)
        self.assertIsNotNone(papers[0].links.pdf)
        assert papers[0].links.pdf is not None
        self.assertIn("PMC1234567", papers[0].links.pdf)

    def test_no_pmc_id_pdf_is_none(self) -> None:
        xml = _wrap(_MINIMAL_ARTICLE)
        papers = parse_pubmed_xml(xml)
        self.assertIsNone(papers[0].links.pdf)

    def test_abstract_url_built_from_pmid(self) -> None:
        xml = _wrap(_MINIMAL_ARTICLE)
        papers = parse_pubmed_xml(xml)
        self.assertIsNotNone(papers[0].links.abstract)
        assert papers[0].links.abstract is not None
        self.assertIn("12345678", papers[0].links.abstract)
        self.assertIn("pubmed.ncbi.nlm.nih.gov", papers[0].links.abstract)

    def test_work_type_is_article(self) -> None:
        xml = _wrap(_MINIMAL_ARTICLE)
        papers = parse_pubmed_xml(xml)
        self.assertEqual(papers[0].extra.get("work_type"), "article")

    def test_journal_in_extra(self) -> None:
        xml = _wrap(_MINIMAL_ARTICLE)
        papers = parse_pubmed_xml(xml)
        self.assertEqual(papers[0].extra.get("journal"), "Nature Medicine")

    def test_empty_set(self) -> None:
        xml = "<PubmedArticleSet></PubmedArticleSet>"
        papers = parse_pubmed_xml(xml)
        self.assertEqual(papers, [])


if __name__ == "__main__":
    unittest.main()
