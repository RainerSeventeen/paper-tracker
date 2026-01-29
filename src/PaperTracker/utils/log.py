"""PaperTracker logging utilities.

Provides a simple logger with a timestamp + abbreviated level prefix, and
centralizes logger initialization.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
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


def configure_logging(
    *,
    level: str = "INFO",
    action: str | None = None,
    log_to_file: bool = True,
    log_dir: str = "log",
) -> None:
    """Configure PaperTracker logger.

    Uses format: mm-dd HH:MM:SS [<LVL>] <message>
    where LVL is one of: DEBG/INFO/WARN/ERRO.

    Args:
        level: Logging level (e.g., INFO, DEBUG).
        action: CLI action name used to create the log file path.
        log_to_file: Whether to mirror logs to a file.
        log_dir: Base directory for log files.
    """
    resolved_level = getattr(logging, (level or "INFO").upper(), logging.INFO)

    formatter = _AbbrevLevelFormatter(
        fmt="%(asctime)s [%(levelabbr)s] %(message)s",
        datefmt="%m-%d %H:%M:%S",
    )

    handlers: list[logging.Handler] = []

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    if log_to_file and action:
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        log_root = Path(log_dir or "log")
        action_dir = log_root / action
        action_dir.mkdir(parents=True, exist_ok=True)
        log_path = action_dir / f"{action}_{timestamp}.log"
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    log.handlers.clear()
    for handler in handlers:
        log.addHandler(handler)
    log.setLevel(min(logging.DEBUG, resolved_level))
    log.propagate = False
