from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """Normalized search intent passed through the service layer.

    This object is source-agnostic: each data source is responsible for
    translating it into its own query language.

    Attributes:
        keywords: Required keywords to search for.
        categories: Optional category filters (e.g. arXiv "cs.CV").
        exclude_keywords: Optional keywords to exclude.
        logic: How to combine category-group and keyword-group ("AND"/"OR").
    """

    keywords: Sequence[str]
    categories: Sequence[str] = ()
    exclude_keywords: Sequence[str] = ()
    logic: str = "AND"  # between categories & keywords
