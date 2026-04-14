"""
Structured logging for ZettelForge (GOV-012 compliant).

Provides structlog-based JSON logging with OCSF-compatible timestamps,
dual output to stdout and rotating file, and a shared get_logger interface.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import structlog


_configured = False


def configure_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_to_stdout: bool = True,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 9,
) -> None:
    """Configure structlog with JSON output per GOV-012.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
        log_file: Path to rotating log file. None disables file logging.
        log_to_stdout: Whether to also log to stdout.
        max_bytes: Max bytes per log file before rotation.
        backup_count: Number of rotated backup files to keep.
    """
    global _configured
    if _configured:
        return

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = []

    if log_to_stdout:
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(numeric_level)
        handlers.append(stdout_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        file_handler.setLevel(numeric_level)
        handlers.append(file_handler)

    logging.basicConfig(
        format="%(message)s",
        level=numeric_level,
        handlers=handlers,
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="time"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    _configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a named structlog logger.

    Args:
        name: Logger name, typically module path (e.g. "zettelforge.memory").

    Returns:
        A bound structlog logger instance.
    """
    if not _configured:
        data_dir = os.environ.get("AMEM_DATA_DIR", str(Path.home() / ".amem"))
        log_file = str(Path(data_dir) / "logs" / "zettelforge.log")
        configure_logging(log_file=log_file)
    return structlog.get_logger(name)
