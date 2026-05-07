"""PubMed XML parser.

Parses PubmedArticleSet XML returned by NCBI EFetch into normalized Paper objects.
Records without a DOI are silently discarded to maintain deduplication tier consistency.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from PaperTracker.core.models import Paper, PaperLinks

logger = logging.getLogger(__name__)


def parse_pubmed_xml(xml_text: str) -> list[Paper]:
    """Parse PubmedArticleSet XML into a list of Paper objects.

    Records that lack a DOI are dropped and not included in the returned list.
    A DEBUG-level log entry records the count of skipped records.

    Args:
        xml_text: Raw PubmedArticleSet XML string from EFetch.

    Returns:
        List of normalized Paper objects (only records with a DOI).
    """
    root = ET.fromstring(xml_text)
    papers: list[Paper] = []
    skipped = 0

    for article in root.findall("PubmedArticle"):
        pmid = _extract_pmid(article)
        doi = _extract_doi(article)
        if not doi:
            skipped += 1
            logger.debug("PubMed: skipping PMID=%s — no DOI found", pmid or "?")
            continue

        title = _extract_title(article)
        abstract = _extract_abstract(article)
        authors = _extract_authors(article)
        published = _extract_published(article)
        pmc_id = _extract_pmc_id(article)
        categories = _extract_mesh_terms(article)
        links = _build_links(pmid, pmc_id)
        journal = _extract_journal(article)

        papers.append(
            Paper(
                source="pubmed",
                id=pmid or doi,
                title=title,
                authors=authors,
                abstract=abstract,
                published=published,
                updated=None,
                primary_category=categories[0] if categories else None,
                categories=categories,
                links=links,
                doi=doi,
                extra={
                    "work_type": "article",
                    "journal": journal or None,
                },
            )
        )

    if skipped:
        logger.debug("PubMed: skipped %d record(s) with no DOI in this batch", skipped)

    return papers


# ---------------------------------------------------------------------------
# Internal extraction helpers
# ---------------------------------------------------------------------------


def _extract_pmid(article: ET.Element) -> str:
    """Extract PMID text from MedlineCitation."""
    el = article.find(".//MedlineCitation/PMID")
    if el is not None and el.text:
        return el.text.strip()
    return ""


def _extract_title(article: ET.Element) -> str:
    """Extract article title, handling inline markup via itertext."""
    el = article.find(".//MedlineCitation/Article/ArticleTitle")
    if el is not None:
        return "".join(el.itertext()).strip()
    return "Untitled"


def _extract_abstract(article: ET.Element) -> str:
    """Extract abstract text, joining structured sections with label prefixes."""
    sections: list[str] = []
    for abstract_text in article.findall(".//Article/Abstract/AbstractText"):
        text = "".join(abstract_text.itertext()).strip()
        if not text:
            continue
        label = abstract_text.get("Label", "").strip()
        if label:
            sections.append(f"{label}: {text}")
        else:
            sections.append(text)
    return " ".join(sections)


def _extract_authors(article: ET.Element) -> tuple[str, ...]:
    """Extract author names as 'ForeName LastName' or just 'LastName'."""
    authors: list[str] = []
    for author in article.findall(".//AuthorList/Author"):
        last = _text_or_empty(author.find("LastName"))
        fore = _text_or_empty(author.find("ForeName"))
        if last and fore:
            authors.append(f"{fore} {last}")
        elif last:
            authors.append(last)
    return tuple(authors)


def _extract_published(article: ET.Element) -> datetime | None:
    """Extract publication date, preferring ArticleDate over PubDate."""
    # Prefer ArticleDate (electronic publication date)
    for article_date in article.findall(".//Article/ArticleDate"):
        parsed = _parse_structured_date(article_date)
        if parsed is not None:
            return parsed

    # Fall back to JournalIssue/PubDate
    pub_date = article.find(".//JournalIssue/PubDate")
    if pub_date is not None:
        parsed = _parse_pub_date(pub_date)
        if parsed is not None:
            return parsed

    return None


def _extract_doi(article: ET.Element) -> str:
    """Extract DOI from ArticleIdList; returns empty string when absent."""
    for article_id in article.findall(".//ArticleIdList/ArticleId"):
        if article_id.get("IdType") == "doi":
            text = (article_id.text or "").strip()
            if text:
                return text
    return ""


def _extract_pmc_id(article: ET.Element) -> str:
    """Extract PMC ID from ArticleIdList; returns empty string when absent."""
    for article_id in article.findall(".//ArticleIdList/ArticleId"):
        if article_id.get("IdType") == "pmc":
            text = (article_id.text or "").strip()
            if text:
                return text
    return ""


def _extract_mesh_terms(article: ET.Element) -> tuple[str, ...]:
    """Extract MeSH descriptor names as categories."""
    terms: list[str] = []
    for descriptor in article.findall(".//MeshHeadingList/MeshHeading/DescriptorName"):
        text = "".join(descriptor.itertext()).strip()
        if text:
            terms.append(text)
    return tuple(terms)


def _extract_journal(article: ET.Element) -> str:
    """Extract journal title using itertext to handle inline markup."""
    el = article.find(".//Journal/Title")
    if el is not None:
        return "".join(el.itertext()).strip()
    return ""


def _build_links(pmid: str, pmc_id: str) -> PaperLinks:
    """Build PaperLinks from PMID and optional PMC ID."""
    abstract_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None
    pdf_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/" if pmc_id else None
    return PaperLinks(abstract=abstract_url, pdf=pdf_url)


# ---------------------------------------------------------------------------
# Date parsing helpers
# ---------------------------------------------------------------------------


def _parse_structured_date(el: ET.Element) -> datetime | None:
    """Parse Year/Month/Day child elements into a UTC datetime."""
    year_text = _text_or_empty(el.find("Year"))
    month_text = _text_or_empty(el.find("Month"))
    day_text = _text_or_empty(el.find("Day"))
    return _build_datetime(year_text, month_text, day_text)


def _parse_pub_date(pub_date: ET.Element) -> datetime | None:
    """Parse PubDate element, including MedlineDate fallback."""
    # Try structured Year/Month/Day first
    parsed = _parse_structured_date(pub_date)
    if parsed is not None:
        return parsed

    # Fall back to MedlineDate (e.g. "2024 Jan-Feb" or "2024 Jan")
    medline = _text_or_empty(pub_date.find("MedlineDate"))
    if medline:
        return _parse_medline_date(medline)

    return None


def _parse_medline_date(medline_date: str) -> datetime | None:
    """Parse a MedlineDate string like '2024 Jan' or '2024 Jan-Feb'."""
    parts = medline_date.strip().split()
    if not parts:
        return None
    year_text = parts[0]
    month_text = parts[1].split("-")[0] if len(parts) > 1 else ""
    return _build_datetime(year_text, month_text, "")


_MONTH_MAP: dict[str, int] = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _build_datetime(year_text: str, month_text: str, day_text: str) -> datetime | None:
    """Build a UTC datetime from year/month/day text strings."""
    try:
        year = int(year_text.strip())
    except (ValueError, AttributeError):
        return None

    month = 1
    if month_text:
        stripped = month_text.strip()
        try:
            month = int(stripped)
        except ValueError:
            month = _MONTH_MAP.get(stripped.lower()[:3], 1)

    day = 1
    if day_text:
        try:
            day = int(day_text.strip())
        except ValueError:
            day = 1

    try:
        return datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None


def _text_or_empty(el: ET.Element | None) -> str:
    """Return stripped text of element, or empty string when absent."""
    if el is None:
        return ""
    return (el.text or "").strip()
