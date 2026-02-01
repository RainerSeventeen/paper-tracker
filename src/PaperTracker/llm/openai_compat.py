"""OpenAI-compatible LLM provider implementation."""

from __future__ import annotations

from dataclasses import dataclass

from PaperTracker.llm.client import LLMApiClient, extract_json
from PaperTracker.utils.log import log


@dataclass(slots=True)
class OpenAICompatProvider:
    """LLM provider using OpenAI-compatible chat completions API.

    Supports any API following OpenAI's chat completion spec:
    - OpenAI GPT models
    - DeepSeek
    - SiliconFlow
    - Local models via OpenAI-compatible servers
    """

    name: str
    client: LLMApiClient
    model: str
    temperature: float = 0.0
    max_tokens: int = 800

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
            target_lang: Target language code.

        Returns:
            Dictionary with translated fields:
            - title_translated: Translated title
            - summary_translated: Translated summary

        Raises:
            requests.HTTPError: If API request fails.
        """
        lang_names = {
            "zh": "Simplified Chinese",
            "en": "English",
            "ja": "Japanese",
            "ko": "Korean",
            "fr": "French",
            "de": "German",
            "es": "Spanish",
        }
        lang_name = lang_names.get(target_lang, "Simplified Chinese")

        system_prompt = (
            "You are a precise academic translator. "
            "Translate faithfully without adding commentary or changing meaning. "
            "Preserve technical terms and proper nouns."
        )

        user_prompt = f"""Translate the following paper metadata to {lang_name}.
Return ONLY a JSON object with these exact keys:
{{"title_translated": "...", "summary_translated": "..."}}

Do not include any other text outside the JSON.

Title: {title}

Abstract: {summary}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        log.debug("Translating paper to %s: title='%s...'", target_lang, title[:50])

        response_text = self.client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # Parse JSON response
        data = extract_json(response_text)

        result = {
            "title_translated": data.get("title_translated", "").strip(),
            "summary_translated": data.get("summary_translated", "").strip(),
        }

        if not result["title_translated"] or not result["summary_translated"]:
            log.warning("Translation incomplete: %s", result)

        return result
