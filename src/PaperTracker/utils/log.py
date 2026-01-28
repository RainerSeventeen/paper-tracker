"""PaperTracker logging utilities.

Provides a simple logger with a timestamp + abbreviated level prefix, and
centralizes logger initialization.
"""

from __future__ import annotations

import logging
from typing import Final


_LEVEL_ABBREV: Final[dict[int, str]] = {
    logging.DEBUG: "DEBG",
    logging.INFO: "INFO",
    logging.WARNING: "WARN",
    logging.ERROR: "ERRO",
    logging.CRITICAL: "ERRO",
}


class _AbbrevLevelFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: A003 - record is stdlib name
        """Format one log record with an abbreviated level.

        Args:
            record: Logging record.

        Returns:
            Formatted message string.
        """
        record.levelabbr = _LEVEL_ABBREV.get(record.levelno, record.levelname[:4])
        return super().format(record)


log = logging.getLogger("PaperTracker")


def configure_logging(*, level: str = "INFO") -> None:
    """Configure PaperTracker logger.

    Uses format: mm-dd HH:MM:SS [<LVL>] <message>
    where LVL is one of: DEBG/INFO/WARN/ERRO.
    """
    resolved_level = getattr(logging, (level or "INFO").upper(), logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(
        _AbbrevLevelFormatter(
            fmt="%(asctime)s [%(levelabbr)s] %(message)s",
            datefmt="%m-%d %H:%M:%S",
        )
    )

    log.handlers.clear()
    log.addHandler(handler)
    log.setLevel(resolved_level)
    log.propagate = False
