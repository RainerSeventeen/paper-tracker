"""LLM service for batch paper enrichment."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Sequence

from PaperTracker.core.models import LLMGeneratedInfo, Paper
from PaperTracker.llm.provider import LLMProvider
from PaperTracker.utils.log import log


@dataclass(slots=True)
class LLMService:
    """High-level service for LLM-powered paper enhancement.

    Handles batch processing, concurrency, and error recovery.
    """

    provider: LLMProvider
    target_lang: str = "zh"
    max_workers: int = 3
    enabled: bool = True

    # Feature selection
    enable_translation: bool = True
    enable_summary: bool = True

    def generate_batch(self, papers: Sequence[Paper]) -> list[LLMGeneratedInfo]:
        """Generate LLM enrichment for a batch of papers in parallel.

        Args:
            papers: Papers to enrich.

        Returns:
            List of LLMGeneratedInfo objects for successful generations.
        """
        if not self.enabled or not papers:
            return []

        log.info(
            "Starting LLM batch: papers=%d workers=%d lang=%s translation=%s summary=%s",
            len(papers),
            self.max_workers,
            self.target_lang,
            self.enable_translation,
            self.enable_summary,
        )

        results: list[LLMGeneratedInfo] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_paper = {
                executor.submit(
                    self._generate_single,
                    paper,
                ): paper
                for paper in papers
            }

            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]
                try:
                    info = future.result()
                    if info is not None:
                        results.append(info)
                except Exception as e:  # noqa: BLE001
                    log.warning(
                        "LLM generation failed for paper %s: %s",
                        paper.id,
                        e,
                    )

        log.info(
            "LLM batch complete: success=%d/%d",
            len(results),
            len(papers),
        )

        return results

    def enrich_papers(
        self,
        papers: Sequence[Paper],
        infos: Sequence[LLMGeneratedInfo],
    ) -> list[Paper]:
        """Attach LLM-generated info into paper extra fields."""
        info_map = {(info.source, info.source_id): info for info in infos}

        enriched: list[Paper] = []
        for paper in papers:
            info = info_map.get((paper.source, paper.id))
            if not info:
                enriched.append(paper)
                continue

            extra_data = dict(paper.extra)

            if info.abstract_translation:
                extra_data["translation"] = {
                    "summary_translated": info.abstract_translation,
                    "language": info.language,
                }

            if info.tldr or info.motivation or info.method or info.result or info.conclusion:
                extra_data["summary"] = {
                    "tldr": info.tldr,
                    "motivation": info.motivation,
                    "method": info.method,
                    "result": info.result,
                    "conclusion": info.conclusion,
                }

            enriched.append(
                Paper(
                    source=paper.source,
                    id=paper.id,
                    title=paper.title,
                    authors=paper.authors,
                    abstract=paper.abstract,
                    published=paper.published,
                    updated=paper.updated,
                    primary_category=paper.primary_category,
                    categories=paper.categories,
                    links=paper.links,
                    doi=paper.doi,
                    extra=extra_data,
                )
            )

        return enriched

    def _generate_single(self, paper: Paper) -> LLMGeneratedInfo | None:
        """Generate LLM enrichment for a single paper.

        Generates both translation and summary based on configuration.

        Args:
            paper: Paper to enrich.

        Returns:
            LLMGeneratedInfo on success, otherwise None.
        """
        translation = None
        summary_dict = None

        # Generate translation if enabled
        if self.enable_translation:
            try:
                translation = self.provider.translate_abstract(
                    abstract=paper.abstract,
                    target_lang=self.target_lang,
                )
                translation = translation.strip() or None
            except Exception as e:  # noqa: BLE001
                log.warning("Translation failed for %s: %s", paper.id, e)

        # Generate summary if enabled
        if self.enable_summary:
            try:
                summary_dict = self.provider.generate_summary(
                    abstract=paper.abstract,
                    target_lang=self.target_lang,
                )
            except Exception as e:  # noqa: BLE001
                log.warning("Summary generation failed for %s: %s", paper.id, e)

        # Return None if both failed
        if translation is None and summary_dict is None:
            return None

        return LLMGeneratedInfo(
            source=paper.source,
            source_id=paper.id,
            language=self.target_lang,
            abstract_translation=translation,
            tldr=summary_dict.get("tldr") if summary_dict else None,
            motivation=summary_dict.get("motivation") if summary_dict else None,
            method=summary_dict.get("method") if summary_dict else None,
            result=summary_dict.get("result") if summary_dict else None,
            conclusion=summary_dict.get("conclusion") if summary_dict else None,
        )
