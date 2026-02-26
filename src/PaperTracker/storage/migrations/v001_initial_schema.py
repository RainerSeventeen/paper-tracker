"""Migration v001: initial schema (seen_papers, paper_content, llm_generated)."""

from __future__ import annotations

from PaperTracker.storage.migration import Migration

MIGRATION = Migration(
    version=1,
    description="Initial schema: seen_papers, paper_content, llm_generated",
    sql="""
        CREATE TABLE IF NOT EXISTS seen_papers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source TEXT NOT NULL,
          source_id TEXT NOT NULL,
          doi TEXT,
          doi_norm TEXT GENERATED ALWAYS AS (
            CASE
              WHEN doi IS NULL OR trim(doi) = '' THEN NULL
              ELSE lower(
                trim(
                  replace(
                    replace(
                      replace(
                        replace(
                          replace(trim(doi), 'https://doi.org/', ''),
                        'http://doi.org/', ''),
                      'https://dx.doi.org/', ''),
                    'http://dx.doi.org/', ''),
                  'doi:', '')
                )
              )
            END
          ) STORED,
          title TEXT NOT NULL,
          first_seen_at INTEGER NOT NULL DEFAULT (
            CAST(strftime('%s','now') AS INTEGER)
          ),
          UNIQUE(source, source_id)
        );

        CREATE TABLE IF NOT EXISTS paper_content (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          seen_paper_id INTEGER NOT NULL,
          source TEXT NOT NULL,
          source_id TEXT NOT NULL,
          title TEXT NOT NULL,
          authors TEXT NOT NULL,
          abstract TEXT NOT NULL,
          published_at INTEGER,
          updated_at INTEGER,
          fetched_at INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER)),
          primary_category TEXT,
          categories TEXT,
          abstract_url TEXT,
          pdf_url TEXT,
          code_urls TEXT,
          project_urls TEXT,
          doi TEXT,
          extra TEXT,
          FOREIGN KEY (seen_paper_id) REFERENCES seen_papers(id) ON DELETE CASCADE,
          UNIQUE(source, source_id, fetched_at)
        );

        CREATE INDEX IF NOT EXISTS idx_seen_doi_norm
          ON seen_papers(doi_norm)
          WHERE doi_norm IS NOT NULL AND doi_norm <> '';

        CREATE INDEX IF NOT EXISTS idx_seen_first_seen
          ON seen_papers(first_seen_at);

        CREATE INDEX IF NOT EXISTS idx_content_seen_paper
          ON paper_content(seen_paper_id);

        CREATE INDEX IF NOT EXISTS idx_content_source_id
          ON paper_content(source, source_id);

        CREATE INDEX IF NOT EXISTS idx_content_fetched
          ON paper_content(fetched_at);

        CREATE INDEX IF NOT EXISTS idx_content_category
          ON paper_content(primary_category);

        CREATE TABLE IF NOT EXISTS llm_generated (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          paper_content_id INTEGER NOT NULL,
          generated_at INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER)),
          provider TEXT NOT NULL,
          model TEXT NOT NULL,
          language TEXT NOT NULL,
          abstract_translation TEXT,
          summary_tldr TEXT,
          summary_motivation TEXT,
          summary_method TEXT,
          summary_result TEXT,
          summary_conclusion TEXT,
          extra TEXT,
          FOREIGN KEY (paper_content_id) REFERENCES paper_content(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_llm_generated_paper
          ON llm_generated(paper_content_id);

        CREATE INDEX IF NOT EXISTS idx_llm_generated_time
          ON llm_generated(generated_at DESC);
    """,
)
