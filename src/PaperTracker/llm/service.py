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
            "Starting LLM batch: papers=%d workers=%d lang=%s",
            len(papers),
            self.max_workers,
            self.target_lang,
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

    def _generate_single(self, paper: Paper) -> LLMGeneratedInfo | None:
        """Generate LLM enrichment for a single paper.

        Args:
            paper: Paper to enrich.

        Returns:
            LLMGeneratedInfo on success, otherwise None.

        Raises:
            Exception: If translation fails.
        """
        abstract_translation = self.provider.translate_abstract(
            abstract=paper.abstract,
            target_lang=self.target_lang,
        )
        abstract_translation = abstract_translation.strip()
        if not abstract_translation:
            return None

        return LLMGeneratedInfo(
            source=paper.source,
            source_id=paper.id,
            abstract_translation=abstract_translation,
            language=self.target_lang,
        )
