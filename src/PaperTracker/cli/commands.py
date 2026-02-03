"""Command implementations for PaperTracker CLI.

Encapsulates business logic for commands like search, separated from
CLI parameter handling and output formatting.
"""

from __future__ import annotations

from dataclasses import dataclass

from PaperTracker.config import AppConfig
from PaperTracker.llm import LLMService
from PaperTracker.renderers import OutputWriter
from PaperTracker.renderers.mapper import map_papers_to_views
from PaperTracker.services.search import PaperSearchService
from PaperTracker.storage.content import PaperContentStore
from PaperTracker.storage.deduplicate import SqliteDeduplicateStore
from PaperTracker.storage.llm import LLMGeneratedStore
from PaperTracker.utils.log import log


@dataclass(slots=True)
class SearchCommand:
    """Encapsulates search command business logic.

    Responsible for orchestrating search across multiple queries,
    managing deduplication, and delegating output to OutputWriter.
    """

    config: AppConfig
    search_service: PaperSearchService
    dedup_store: SqliteDeduplicateStore | None
    content_store: PaperContentStore | None
    llm_service: LLMService | None
    llm_store: LLMGeneratedStore | None
    output_writer: OutputWriter

    def execute(self) -> None:
        """Execute search for all configured queries.

        Iterates through queries, applies filtering, and delegates
        output to the configured OutputWriter. Handles deduplication
        and content storage if enabled.
        """
        multiple = len(self.config.queries) > 1

        for idx, query in enumerate(self.config.queries, start=1):
            log.debug(
                "Running query %d/%d name=%s fields=%s",
                idx,
                len(self.config.queries),
                query.name,
                query.fields,
            )
            if multiple:
                log.info("=== Query %d/%d ===", idx, len(self.config.queries))
            if self.config.scope:
                log.info("scope=%s", self.config.scope.fields)
            if query.name:
                log.info("name=%s", query.name)
            log.info("fields=%s", dict(query.fields))

            papers = self.search_service.search(
                query,
                max_results=self.config.max_results,
                sort_by=self.config.sort_by,
                sort_order=self.config.sort_order,
            )
            log.info("Fetched %d papers", len(papers))

            if self.dedup_store:
                new_papers = self.dedup_store.filter_new(papers)
                log.info(
                    "New papers: %d (filtered %d duplicates)",
                    len(new_papers),
                    len(papers) - len(new_papers),
                )

                # Mark as seen first (writes to seen_papers table)
                self.dedup_store.mark_seen(papers)

                # Save full content if enabled (writes to paper_content table)
                if self.content_store:
                    self.content_store.save_papers(papers)

                papers = new_papers

            # Generate LLM enrichment
            if self.llm_service and self.llm_store and papers:
                log.info("Generating LLM enrichment for %d papers", len(papers))
                infos = self.llm_service.generate_batch(papers)

                # Save to llm_generated table
                if infos:
                    self.llm_store.save(infos)

                # Inject enrichment data into paper.extra
                papers = self.llm_service.enrich_papers(papers, infos)

            # Map to view models for output
            paper_views = map_papers_to_views(papers)

            self.output_writer.write_query_result(paper_views, query, self.config.scope)
