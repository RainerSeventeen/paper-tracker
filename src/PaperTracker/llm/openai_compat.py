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

    def translate_abstract(
        self,
        abstract: str,
        target_lang: str = "zh",
    ) -> str:
        """Translate paper abstract.

        Args:
            abstract: Paper abstract in English.
            target_lang: Target language code.

        Returns:
            Translated abstract text.

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

        user_prompt = f"""Translate the following paper abstract to {lang_name}.
Return ONLY a JSON object with this exact key:
{{"summary_translated": "..."}}

Do not include any other text outside the JSON.

Abstract: {abstract}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        log.debug("Translating abstract to %s", target_lang)

        response_text = self.client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        log.debug(response_text)

        # Parse JSON response
        data = extract_json(response_text)

        result = str(data.get("summary_translated", "") or "").strip()
        if not result:
            log.warning("Translation incomplete")
        return result

    def generate_summary(
        self,
        abstract: str,
        target_lang: str = "en",
    ) -> dict[str, str]:
        """Generate structured summary from paper abstract.

        Args:
            abstract: Paper abstract in English.
            target_lang: Target language for summary.

        Returns:
            Dictionary with keys: tldr, motivation, method, result, conclusion.

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
        lang_name = lang_names.get(target_lang, "English")

        system_prompt = (
            "You are a professional paper analyst. "
            "You should provide concise, detailed, and precise analysis using correct terminology. "
            "Avoid unnecessarily long replies."
        )

        user_prompt = f"""Please analyze the following abstract of a research paper.

Content:
{abstract}

Your output should be in {lang_name}.
Return ONLY a JSON object with these exact keys:
{{
  "tldr": "generate a too long; didn't read summary",
  "motivation": "describe the motivation in this paper",
  "method": "method of this paper",
  "result": "result of this paper",
  "conclusion": "conclusion of this paper"
}}

Do not include any other text outside the JSON."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        log.debug("Generating summary for abstract (lang=%s)", target_lang)

        response_text = self.client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # Parse JSON response
        data = extract_json(response_text)

        # Return dictionary with default values for missing fields
        return {
            "tldr": str(data.get("tldr", "") or "Summary generation failed"),
            "motivation": str(data.get("motivation", "") or "Motivation analysis unavailable"),
            "method": str(data.get("method", "") or "Method extraction failed"),
            "result": str(data.get("result", "") or "Result analysis unavailable"),
            "conclusion": str(data.get("conclusion", "") or "Conclusion extraction failed"),
        }
