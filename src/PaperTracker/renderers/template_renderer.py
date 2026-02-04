"""Template rendering utilities for markdown output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Mapping

from PaperTracker.utils.log import log


_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


@dataclass(slots=True)
class TemplateRenderer:
    """Render templates with placeholder substitution and conditional lines."""

    warned_placeholders: set[str] = field(default_factory=set)

    def render(self, template: str, context: Mapping[str, str]) -> str:
        """Render a template using plain placeholder replacement.

        Args:
            template: Raw template content.
            context: Placeholder mapping.

        Returns:
            Rendered content with placeholders replaced.
        """
        self._warn_unknown_placeholders(template, context)
        return template.format_map(_SafeFormatDict(context))

    def render_conditional(self, template: str, context: Mapping[str, str]) -> str:
        """Render a template and remove lines with empty fields.

        Lines that include placeholders with empty values are omitted.
        Unknown placeholders are kept as-is.

        Args:
            template: Raw template content.
            context: Placeholder mapping.

        Returns:
            Rendered content with conditional lines removed.
        """
        output_lines: list[str] = []
        for line in template.splitlines():
            placeholders = _PLACEHOLDER_RE.findall(line)
            if not placeholders:
                output_lines.append(line)
                continue

            unknown = [key for key in placeholders if key not in context]
            if unknown:
                self._warn_unknown_keys(unknown)

            known = [key for key in placeholders if key in context]
            if known and any(not context.get(key, "") for key in known):
                continue

            output_lines.append(line.format_map(_SafeFormatDict(context)))

        return "\n".join(output_lines)

    def _warn_unknown_placeholders(self, template: str, context: Mapping[str, str]) -> None:
        placeholders = _PLACEHOLDER_RE.findall(template)
        unknown = [key for key in placeholders if key not in context]
        if unknown:
            self._warn_unknown_keys(unknown)

    def _warn_unknown_keys(self, keys: list[str]) -> None:
        for key in keys:
            if key in self.warned_placeholders:
                continue
            self.warned_placeholders.add(key)
            log.warning("Unknown template placeholder: %s", key)


class _SafeFormatDict(dict[str, str]):
    def __missing__(self, key: str) -> str:  # noqa: D401 - simple behavior
        return "{" + key + "}"
