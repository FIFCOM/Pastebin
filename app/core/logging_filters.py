"""
Logging filters used by the application logging configuration.
"""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

HEALTH_CHECK_PATHS = frozenset({"/api/health", "/api/health/"})


def _path_from_record(record: logging.LogRecord) -> str | None:
    args = record.args
    if isinstance(args, tuple | list) and len(args) >= 3:
        return _normalize_path(str(args[2]))

    if isinstance(args, dict):
        for key in ("path", "request_line"):
            value = args.get(key)
            if value is not None:
                return _normalize_path(str(value))

    return _normalize_path(record.getMessage())


def _normalize_path(value: str) -> str | None:
    value = value.strip().strip('"')
    if not value:
        return None

    parts = value.split()
    if len(parts) >= 2 and parts[1].startswith("/"):
        value = parts[1]

    parsed = urlsplit(value)
    return parsed.path or None


class ExcludeHealthCheckAccessFilter(logging.Filter):
    """Drop Uvicorn access log records for health check probes."""

    def filter(self, record: logging.LogRecord) -> bool:
        return _path_from_record(record) not in HEALTH_CHECK_PATHS
