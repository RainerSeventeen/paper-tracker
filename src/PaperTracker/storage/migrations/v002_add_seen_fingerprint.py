"""Migration v002: add and backfill fingerprint identity for seen papers."""

from __future__ import annotations

from PaperTracker.storage.migration import Migration

MIGRATION = Migration(
    version=2,
    description="Add title_author_year_fingerprint to seen_papers",
    sql="""
        ALTER TABLE seen_papers
          ADD COLUMN title_author_year_fingerprint TEXT;

        WITH latest_content AS (
          SELECT
            pc.source,
            pc.source_id,
            pc.title,
            pc.authors,
            pc.published_at,
            ROW_NUMBER() OVER (
              PARTITION BY pc.source, pc.source_id
              ORDER BY pc.fetched_at DESC, pc.id DESC
            ) AS row_num
          FROM paper_content pc
        ),
        normalized AS (
          SELECT
            lc.source,
            lc.source_id,
            (
              WITH RECURSIVE
              chars(pos, raw, normalized_text) AS (
                SELECT
                  1,
                  lower(COALESCE(lc.title, '')),
                  ''
                UNION ALL
                SELECT
                  pos + 1,
                  raw,
                  normalized_text || CASE
                    WHEN substr(raw, pos, 1) GLOB '[a-z0-9 ]' THEN substr(raw, pos, 1)
                    ELSE ' '
                  END
                FROM chars
                WHERE pos <= length(raw)
              ),
              collapsed(step, text_value) AS (
                SELECT
                  0,
                  COALESCE((SELECT normalized_text FROM chars ORDER BY pos DESC LIMIT 1), '')
                UNION ALL
                SELECT
                  step + 1,
                  replace(text_value, '  ', ' ')
                FROM collapsed
                WHERE instr(text_value, '  ') > 0
              )
              SELECT trim(text_value)
              FROM collapsed
              ORDER BY step DESC
              LIMIT 1
            ) AS title_norm,
            (
              WITH RECURSIVE
              chars(pos, raw, normalized_text) AS (
                SELECT
                  1,
                  lower(COALESCE(json_extract(lc.authors, '$[0]'), '')),
                  ''
                UNION ALL
                SELECT
                  pos + 1,
                  raw,
                  normalized_text || CASE
                    WHEN substr(raw, pos, 1) GLOB '[a-z0-9 ]' THEN substr(raw, pos, 1)
                    ELSE ' '
                  END
                FROM chars
                WHERE pos <= length(raw)
              ),
              collapsed(step, text_value) AS (
                SELECT
                  0,
                  COALESCE((SELECT normalized_text FROM chars ORDER BY pos DESC LIMIT 1), '')
                UNION ALL
                SELECT
                  step + 1,
                  replace(text_value, '  ', ' ')
                FROM collapsed
                WHERE instr(text_value, '  ') > 0
              )
              SELECT trim(text_value)
              FROM collapsed
              ORDER BY step DESC
              LIMIT 1
            ) AS first_author_norm,
            CASE
              WHEN lc.published_at IS NULL THEN NULL
              ELSE CAST(strftime('%Y', lc.published_at, 'unixepoch') AS INTEGER)
            END AS publish_year
          FROM latest_content lc
          WHERE lc.row_num = 1
        )
        UPDATE seen_papers
        SET title_author_year_fingerprint = (
          SELECT
            CASE
              WHEN length(normalized.title_norm) >= 24
                AND normalized.first_author_norm <> ''
                AND normalized.publish_year IS NOT NULL
              THEN normalized.title_norm || '|' || normalized.first_author_norm || '|' || normalized.publish_year
              ELSE NULL
            END
          FROM normalized
          WHERE normalized.source = seen_papers.source
            AND normalized.source_id = seen_papers.source_id
        )
        WHERE title_author_year_fingerprint IS NULL;

        CREATE INDEX IF NOT EXISTS idx_seen_title_author_year_fingerprint
          ON seen_papers(title_author_year_fingerprint)
          WHERE title_author_year_fingerprint IS NOT NULL
            AND title_author_year_fingerprint <> '';
    """,
)
