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
        output to the configured OutputWriter. Search behavior uses `config.search`.
        ArxivSource will handle multi-round fetching with time-based filtering
        and deduplication internally.
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

            # Search papers; ArxivSource chooses strategy based on search config.
            papers = self.search_service.search(
                query,
                max_results=self.config.search.max_results,
                sort_by="lastUpdatedDate",  # Ignored when search config is enabled.
                sort_order="descending",  # Ignored when search config is enabled.
            )
            log.info("Collected %d papers", len(papers))

            # Persist full paper content before rendering outputs.
            if self.content_store and papers:
                self.content_store.save_papers(papers)

            # Generate LLM enrichment.
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
