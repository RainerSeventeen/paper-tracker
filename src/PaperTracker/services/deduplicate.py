"""Cross-source batch deduplication for search service.

Provides duplicate-key building, winner selection, and field merge logic for
the aggregated result set after multiple sources are combined.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from PaperTracker.core.dedup import (
    build_title_author_year_fingerprint,
    normalize_doi,
)
from PaperTracker.core.models import Paper
from PaperTracker.utils.log import log


@dataclass(slots=True)
class _DedupGroup:
    """Mutable in-batch dedup group state."""

    winner: Paper
    keys: set[tuple[str, ...]]


def deduplicate_cross_source_batch(
    papers: Sequence[Paper],
    *,
    source_rank: dict[str, int],
) -> list[Paper]:
    """Deduplicate one aggregated batch across sources.

    Source adapters own deduplication while paging within their own fetch
    loops. This function only coordinates duplicate resolution after papers
    from all configured sources have been aggregated.

    Args:
        papers: Aggregated papers from all configured sources.
        source_rank: Source priority map where lower index means higher priority.

    Returns:
        Deduplicated papers with deterministic order.
    """
    # group_id → group state; key_to_group_id enables O(1) lookup by dedup key
    groups: dict[int, _DedupGroup] = {}
    key_to_group_id: dict[tuple[str, ...], int] = {}
    ordered_group_ids: list[int] = []  # preserves first-seen order for deterministic output
    next_group_id = 0
    dedup_hit_doi = 0
    dedup_hit_fingerprint = 0
    dedup_article_win_count = 0

    for paper in papers:
        keys = _build_dedup_keys(paper)
        matched_group_ids: list[int] = []
        doi_hit = False
        fingerprint_hit = False

        # find all existing groups that share at least one dedup key with this paper
        for key in keys:
            group_id = key_to_group_id.get(key)
            if group_id is None or group_id not in groups:
                continue
            if key[0] == "doi":
                doi_hit = True
            if key[0] == "fingerprint":
                fingerprint_hit = True
            if group_id not in matched_group_ids:
                matched_group_ids.append(group_id)

        if not matched_group_ids:
            # no match — start a new group for this paper
            group_id = next_group_id
            next_group_id += 1
            groups[group_id] = _DedupGroup(winner=paper, keys=set(keys))
            ordered_group_ids.append(group_id)
            for key in keys:
                key_to_group_id[key] = group_id
            continue

        if doi_hit:
            dedup_hit_doi += 1
        elif fingerprint_hit:
            dedup_hit_fingerprint += 1

        # merge all matched groups into the first one to handle transitive duplicates across keys
        primary_group_id = matched_group_ids[0]
        primary_group = groups[primary_group_id]

        for other_group_id in matched_group_ids[1:]:
            other_group = groups.pop(other_group_id, None)
            if other_group is None:
                continue
            primary_group.keys.update(other_group.keys)
            merged, article_win = _pick_winner_with_merge(
                primary_group.winner,
                other_group.winner,
                source_rank=source_rank,
            )
            primary_group.winner = merged
            if article_win:
                dedup_article_win_count += 1
            # remap all keys from the absorbed group to the primary group
            for key in other_group.keys:
                key_to_group_id[key] = primary_group_id

        # compete current paper against the group winner and backfill missing fields
        merged, article_win = _pick_winner_with_merge(
            primary_group.winner,
            paper,
            source_rank=source_rank,
        )
        primary_group.winner = merged
        if article_win:
            dedup_article_win_count += 1
        primary_group.keys.update(keys)
        for key in primary_group.keys:
            key_to_group_id[key] = primary_group_id

    result = [groups[group_id].winner for group_id in ordered_group_ids if group_id in groups]
    log.info(
        "Batch dedup stats: input=%d output=%d dedup_hit_doi=%d dedup_hit_fingerprint=%d dedup_article_win_count=%d",
        len(papers),
        len(result),
        dedup_hit_doi,
        dedup_hit_fingerprint,
        dedup_article_win_count,
    )
    return result


def _build_dedup_keys(paper: Paper) -> tuple[tuple[str, ...], ...]:
    """Build all eligible dedup keys for one paper."""
    keys: list[tuple[str, ...]] = []
    doi_norm = normalize_doi(paper.doi)
    if doi_norm:
        keys.append(("doi", doi_norm))

    fingerprint = build_title_author_year_fingerprint(paper)
    if fingerprint:
        keys.append(("fingerprint", fingerprint))

    if not keys:
        keys.append(("unique", paper.source, paper.id))
    return tuple(keys)


def _compare_paper_priority(left: Paper, right: Paper, source_rank: dict[str, int]) -> int:
    """Compare two papers and return negative when left has higher priority."""
    left_rank = _paper_rank(left, source_rank=source_rank)
    right_rank = _paper_rank(right, source_rank=source_rank)
    if left_rank < right_rank:
        return -1
    if left_rank > right_rank:
        return 1
    return 0


def _pick_winner_with_merge(
    left: Paper,
    right: Paper,
    *,
    source_rank: dict[str, int],
) -> tuple[Paper, bool]:
    """Pick winner and backfill winner's missing fields from loser."""
    if _compare_paper_priority(left, right, source_rank) <= 0:
        winner = left
        loser = right
    else:
        winner = right
        loser = left
    article_win = _work_type_tier(winner) == 0 and _work_type_tier(loser) != 0
    return _merge_missing_fields(winner, loser), article_win


def _paper_rank(paper: Paper, *, source_rank: dict[str, int]) -> tuple[int, int, int, str, str]:
    """Build deterministic ranking tuple for duplicate winner selection."""
    timestamp = paper.published or paper.updated
    if timestamp is None:
        time_rank = 10**18
    else:
        time_rank = -int(timestamp.timestamp())
    return (
        _work_type_tier(paper),
        source_rank.get(paper.source, len(source_rank)),
        time_rank,
        paper.source,
        paper.id,
    )


def _work_type_tier(paper: Paper) -> int:
    """Return work-type tier where lower value means higher priority."""
    work_type = str(paper.extra.get("work_type", "")).strip().lower()
    has_doi = bool(normalize_doi(paper.doi))
    if work_type == "article" and has_doi:
        return 0
    if work_type == "preprint" and not has_doi:
        return 1
    return 2


def _merge_missing_fields(winner: Paper, loser: Paper) -> Paper:
    """Backfill winner's missing fields from loser without overriding winner values."""
    merged_doi = winner.doi or loser.doi
    merged_authors = winner.authors or loser.authors
    merged_primary_category = winner.primary_category or loser.primary_category
    merged_categories = winner.categories or loser.categories

    merged_links = winner.links
    if winner.links.abstract is None and loser.links.abstract is not None:
        merged_links = replace(merged_links, abstract=loser.links.abstract)
    if merged_links.pdf is None and loser.links.pdf is not None:
        merged_links = replace(merged_links, pdf=loser.links.pdf)

    merged_extra = dict(winner.extra)
    if "work_type" not in merged_extra and "work_type" in loser.extra:
        merged_extra["work_type"] = loser.extra["work_type"]

    return replace(
        winner,
        doi=merged_doi,
        authors=merged_authors,
        primary_category=merged_primary_category,
        categories=merged_categories,
        links=merged_links,
        extra=merged_extra,
    )
