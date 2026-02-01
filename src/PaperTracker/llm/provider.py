"""LLM provider protocol and base types."""

from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Protocol for LLM translation providers.

    Implementations must support translating paper metadata to a target language.
    """

    name: str

    def translate_paper(
        self,
        title: str,
        summary: str,
        target_lang: str = "zh",
    ) -> dict[str, str]:
        """Translate paper title and summary.

        Args:
            title: Paper title in English.
            summary: Paper abstract in English.
            target_lang: Target language code (zh, en, ja, ko, fr, de, es).

        Returns:
            Dictionary with translated fields:
            - title_translated: Translated title
            - summary_translated: Translated summary

        Raises:
            Exception: If translation fails (caller should handle gracefully).
        """
        raise NotImplementedError
