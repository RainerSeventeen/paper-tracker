"""OpenAlex source integration modules."""

from __future__ import annotations

from PaperTracker.sources.openalex.client import OpenAlexApiClient
from PaperTracker.sources.openalex.parser import parse_openalex_works
from PaperTracker.sources.openalex.query import (
    apply_not_filter,
    compile_openalex_params,
    extract_not_terms,
)
from PaperTracker.sources.openalex.source import OpenAlexSource

__all__ = [
    "OpenAlexApiClient",
    "OpenAlexSource",
    "compile_openalex_params",
    "extract_not_terms",
    "apply_not_filter",
    "parse_openalex_works",
]
