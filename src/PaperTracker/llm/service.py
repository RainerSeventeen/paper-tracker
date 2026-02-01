"""LLM service for batch paper translation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Sequence

from PaperTracker.core.models import Paper
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

    def translate_batch(self, papers: Sequence[Paper]) -> Sequence[Paper]:
        """Translate a batch of papers in parallel.

        Args:
            papers: Papers to translate.

        Returns:
            Papers with translations added to paper.extra['translation'].
            Papers that fail translation are returned unchanged.
        """
        if not self.enabled or not papers:
            return papers

        log.info(
            "Starting batch translation: papers=%d workers=%d lang=%s",
            len(papers),
            self.max_workers,
            self.target_lang,
        )

        # Create a list to preserve order
        results = list(papers)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all translation tasks
            future_to_index = {
                executor.submit(
                    self._translate_single,
                    paper,
                ): idx
                for idx, paper in enumerate(papers)
            }

            # Collect results as they complete
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    enhanced_paper = future.result()
                    results[idx] = enhanced_paper
                except Exception as e:  # noqa: BLE001
                    log.warning(
                        "Translation failed for paper %s: %s",
                        papers[idx].id,
                        e,
                    )
                    # Keep original paper on failure

        success_count = sum(
            1 for p in results if "translation" in p.extra
        )
        log.info(
            "Batch translation complete: success=%d/%d",
            success_count,
            len(papers),
        )

        return results

    def _translate_single(self, paper: Paper) -> Paper:
        """Translate a single paper.

        Args:
            paper: Paper to translate.

        Returns:
            Paper with translation added to extra field.

        Raises:
            Exception: If translation fails.
        """
        translation = self.provider.translate_paper(
            title=paper.title,
            summary=paper.summary,
            target_lang=self.target_lang,
        )

        # Add translation to paper.extra
        updated_extra = dict(paper.extra)
        updated_extra["translation"] = {
            "title": translation["title_translated"],
            "summary": translation["summary_translated"],
            "language": self.target_lang,
        }

        # Create new Paper instance with updated extra
        return Paper(
            source=paper.source,
            id=paper.id,
            title=paper.title,
            authors=paper.authors,
            summary=paper.summary,
            published=paper.published,
            updated=paper.updated,
            primary_category=paper.primary_category,
            categories=paper.categories,
            links=paper.links,
            doi=paper.doi,
            extra=updated_extra,
        )
