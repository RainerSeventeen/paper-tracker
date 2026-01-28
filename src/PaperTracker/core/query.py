from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class SearchQuery:
    keywords: Sequence[str]
    categories: Sequence[str] = ()
    exclude_keywords: Sequence[str] = ()
    logic: str = "AND"  # between categories & keywords

