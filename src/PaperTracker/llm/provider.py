"""LLM provider protocol and base types."""

from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Protocol for LLM providers.

    Implementations must support generating enrichment fields, such as translation.
    """

    name: str

    def translate_abstract(
        self,
        abstract: str,
        target_lang: str = "zh",
    ) -> str:
        """Translate paper abstract.

        Args:
            abstract: Paper abstract in English.
            target_lang: Target language code (zh, en, ja, ko, fr, de, es).

        Returns:
            Translated abstract text.

        Raises:
            Exception: If translation fails (caller should handle gracefully).
        """
        raise NotImplementedError

    def generate_summary(
        self,
        abstract: str,
        target_lang: str = "en",
    ) -> dict[str, str]:
        """Generate structured summary from paper abstract.

        Args:
            abstract: Paper abstract in English.
            target_lang: Target language for summary (en, zh, etc).

        Returns:
            Dictionary with keys: tldr, motivation, method, result, conclusion.
            All values are strings.

        Raises:
            Exception: If generation fails (caller should handle gracefully).
        """
        raise NotImplementedError
