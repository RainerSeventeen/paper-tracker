from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class FieldQuery:
    """Per-field query conditions.

    The keys are intentionally simple and explicit:

    - `OR`: any term matches
    - `AND`: all terms must match
    - `NOT`: excluded terms

    Terms are raw strings (words or phrases). How a term maps to each source is
    handled by the source compiler.
    """

    OR: Sequence[str] = ()
    AND: Sequence[str] = ()
    NOT: Sequence[str] = ()


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """Normalized search intent passed through the service layer.

    This structure is designed for configuration readability and for compiling
    into different provider-specific query syntaxes.

    Attributes:
        name: Optional query name for display.
        fields: Mapping of field name to `FieldQuery`.
            Common fields are TITLE/ABSTRACT/AUTHOR/JOURNAL/CATEGORY.
            Special field TEXT means "default fields" (title+abstract).
    """

    name: str | None
    fields: Mapping[str, FieldQuery]
