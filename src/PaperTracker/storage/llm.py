"""LLM generated data storage."""

from __future__ import annotations

import logging
import sqlite3
from typing import Sequence

from PaperTracker.core.models import LLMGeneratedInfo

log = logging.getLogger(__name__)


class LLMGeneratedStore:
    """Store for LLM-generated enrichment data."""

    def __init__(self, conn: sqlite3.Connection, provider: str, model: str) -> None:
        """Initialize LLM generated store.

        Args:
            conn: SQLite connection.
            provider: LLM provider name (e.g. "openai-compat").
            model: Model identifier (e.g. "deepseek-chat").
        """
        self.conn = conn
        self.provider = provider
        self.model = model

    def save(self, infos: Sequence[LLMGeneratedInfo]) -> None:
        """Save LLM-generated data to llm_generated table.

        Args:
            infos: LLM enrichment data to save.
        """
        if not infos:
            return

        for info in infos:
            # Get paper_content_id
            cursor = self.conn.execute(
                "SELECT id FROM paper_content WHERE source = ? AND source_id = ?",
                (info.source, info.source_id),
            )
            row = cursor.fetchone()
            if not row:
                log.warning(
                    "Paper not found in paper_content: %s/%s",
                    info.source,
                    info.source_id,
                )
                continue

            paper_content_id = row[0]

            # Insert LLM generated data
            self.conn.execute(
                """
                INSERT INTO llm_generated (
                    paper_content_id,
                    provider,
                    model,
                    language,
                    abstract_translation,
                    summary_tldr,
                    summary_motivation,
                    summary_method,
                    summary_result,
                    summary_conclusion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper_content_id,
                    self.provider,
                    self.model,
                    info.language,
                    info.abstract_translation,
                    info.tldr,
                    info.motivation,
                    info.method,
                    info.result,
                    info.conclusion,
                ),
            )

        self.conn.commit()
        log.debug("Saved LLM enrichment for %d papers", len(infos))

    def get_latest(
        self, source: str, source_id: str
    ) -> LLMGeneratedInfo | None:
        """Get latest LLM-generated data for a paper.

        Args:
            source: Paper source.
            source_id: Paper source ID.

        Returns:
            Latest LLM generated info, or None if not found.
        """
        cursor = self.conn.execute(
            """
            SELECT
                l.language,
                l.abstract_translation,
                l.summary_tldr,
                l.summary_motivation,
                l.summary_method,
                l.summary_result,
                l.summary_conclusion
            FROM llm_generated l
            JOIN paper_content c ON l.paper_content_id = c.id
            WHERE c.source = ? AND c.source_id = ?
            ORDER BY l.generated_at DESC
            LIMIT 1
            """,
            (source, source_id),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return LLMGeneratedInfo(
            source=source,
            source_id=source_id,
            language=row[0],
            abstract_translation=row[1],
            tldr=row[2],
            motivation=row[3],
            method=row[4],
            result=row[5],
            conclusion=row[6],
        )

    def get_batch_with_llm(
        self,
        sources_and_ids: Sequence[tuple[str, str]],
    ) -> dict[tuple[str, str], LLMGeneratedInfo]:
        """Batch get LLM data for multiple papers.

        Args:
            sources_and_ids: List of (source, source_id) tuples.

        Returns:
            Dictionary mapping (source, source_id) to LLM generated info.
        """
        if not sources_and_ids:
            return {}

        # Build placeholders for SQL IN clause
        placeholders = ",".join(["(?, ?)"] * len(sources_and_ids))
        params = [item for pair in sources_and_ids for item in pair]

        cursor = self.conn.execute(
            f"""
            SELECT
                c.source,
                c.source_id,
                l.language,
                l.abstract_translation,
                l.summary_tldr,
                l.summary_motivation,
                l.summary_method,
                l.summary_result,
                l.summary_conclusion
            FROM paper_content c
            LEFT JOIN (
                SELECT
                    paper_content_id,
                    language,
                    abstract_translation,
                    summary_tldr,
                    summary_motivation,
                    summary_method,
                    summary_result,
                    summary_conclusion,
                    ROW_NUMBER() OVER (PARTITION BY paper_content_id ORDER BY generated_at DESC) as rn
                FROM llm_generated
            ) l ON l.paper_content_id = c.id AND l.rn = 1
            WHERE (c.source, c.source_id) IN ({placeholders})
            """,
            params,
        )

        results = {}
        for row in cursor:
            if row[2]:  # Has LLM data
                key = (row[0], row[1])
                results[key] = LLMGeneratedInfo(
                    source=row[0],
                    source_id=row[1],
                    language=row[2],
                    abstract_translation=row[3],
                    tldr=row[4],
                    motivation=row[5],
                    method=row[6],
                    result=row[7],
                    conclusion=row[8],
                )

        return results
