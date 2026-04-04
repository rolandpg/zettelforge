"""Structured logging configuration per GOV-012 OCSF schema.

OCSF event classes used:
- 3001: Authentication
- 3003: Authorization
- 6002: API Activity
- 3005: Account Change
"""

import logging
import sys
from typing import Any

import structlog


def configure_logging(*, log_level: str = "INFO") -> None:
    """Configure structlog for OCSF-compatible JSON output.

    Per GOV-012: UTC timestamps, structured JSON, request_id correlation.
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
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
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)
