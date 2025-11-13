"""Logging configuration with Loki integration and structured logging.

Provides setup for both local logging (text/JSON) and remote logging to Loki
for centralized observability.

Adds a ContextFilter to inject core fields (service, environment, host,
version, git_sha) into every record and supports optional Loki batching.
"""

import logging
import os
import socket
import sys
from typing import Optional

from pythonjsonlogger import jsonlogger


class _ExcludeLoggerFilter(logging.Filter):
    """Filter out records coming from specific logger name prefixes.

    This prevents feedback loops when a handler (e.g., Loki) uses libraries
    like `requests` that also emit logs routed to the same handlers.
    """

    def __init__(self, *prefixes: str) -> None:
        super().__init__()
        self._prefixes = tuple(prefixes)

    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name
        return not any(name.startswith(p) for p in self._prefixes)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(
        self, log_record: dict, record: logging.LogRecord, message_dict: dict
    ) -> None:
        """Add custom fields to log record.

        Args:
            log_record: Dictionary to be logged
            record: Original LogRecord
            message_dict: Message dictionary from format string
        """
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record["timestamp"] = self.formatTime(record, self.datefmt)

        # Add level name
        log_record["level"] = record.levelname

        # Add logger name
        log_record["logger"] = record.name

        # Add thread info if available
        if hasattr(record, "thread"):
            log_record["thread"] = record.thread

        # Add correlation_id if present in extra
        if hasattr(record, "correlation_id"):
            log_record["correlation_id"] = record.correlation_id

        # Include common context fields if present
        for key in ("service", "environment", "host", "version", "git_sha"):
            if hasattr(record, key):
                log_record[key] = getattr(record, key)


class _ContextFilter(logging.Filter):
    """Inject default context fields into every log record if missing."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service = service_name
        self._environment = os.getenv("ENVIRONMENT", "development")
        # Prefer ENV HOSTNAME over socket hostname for consistency in containers
        self._host = os.getenv("HOSTNAME", socket.gethostname())
        self._version = os.getenv("APP_VERSION", None)
        self._git_sha = os.getenv("GIT_SHA", None)

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "service"):
            record.service = self._service
        if not hasattr(record, "environment"):
            record.environment = self._environment
        if not hasattr(record, "host"):
            record.host = self._host
        if self._version and not hasattr(record, "version"):
            record.version = self._version
        if self._git_sha and not hasattr(record, "git_sha"):
            record.git_sha = self._git_sha
        return True


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    service_name: str = "telegram-fetcher",
    loki_url: Optional[str] = None,
) -> None:
    """Setup logging with console and optional Loki handlers.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format - 'json' or 'text'
        service_name: Service name for log labels
        loki_url: Optional Loki URL for remote logging (e.g., http://loki:3100)
    """
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Install context filter (adds service/environment/host/version/git_sha)
    root_logger.addFilter(_ContextFilter(service_name))

    # === Console Handler ===
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if log_format == "json":
        # JSON formatter for structured logging
        json_formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(logger)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(json_formatter)
    else:
        # Text formatter for human-readable output
        text_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(text_formatter)

    root_logger.addHandler(console_handler)

    # === Loki Handler (Optional) ===
    if loki_url:
        try:
            import logging_loki
            loki_handler = None
            # Optional batching via LokiQueueHandler (best-effort)
            enable_batch = os.getenv("LOKI_BATCH", "false").lower() in ("1", "true", "yes")
            if enable_batch and hasattr(logging_loki, "LokiQueueHandler"):
                try:
                    # Some versions support capacity/batch_size; keep minimal to avoid API mismatch
                    loki_handler = logging_loki.LokiQueueHandler(
                        url=f"{loki_url}/loki/api/v1/push",
                        tags={"service": service_name},
                        version="1",
                    )
                except Exception:
                    loki_handler = None
            if loki_handler is None:
                loki_handler = logging_loki.LokiHandler(
                    url=f"{loki_url}/loki/api/v1/push",
                    tags={"service": service_name},
                    version="1",
                )
            loki_handler.setLevel(numeric_level)
            # Avoid recursive logging when pushing to Loki
            # via requests/urllib3/logging_loki
            loki_handler.addFilter(
                _ExcludeLoggerFilter(
                    "requests",
                    "urllib3",
                    "logging_loki",
                )
            )
            root_logger.addHandler(loki_handler)

            # Additionally, raise levels and stop propagation for noisy deps
            for noisy in ("requests", "urllib3", "logging_loki"):
                nl = logging.getLogger(noisy)
                nl.setLevel(max(logging.WARNING, numeric_level))
                nl.propagate = False

            # Reduce Telethon verbosity by default
            tlog = logging.getLogger("telethon")
            tlog.setLevel(max(logging.WARNING, numeric_level))
            tlog.propagate = False

            root_logger.info(
                "Loki handler configured",
                extra={
                    "loki_url": loki_url,
                    "service": service_name,
                },
            )
        except ImportError:
            root_logger.warning(
                "python-logging-loki not installed, skipping Loki handler. "
                "Install with: pip install python-logging-loki"
            )
        except Exception as e:
            root_logger.error(
                f"Failed to setup Loki handler: {e}", extra={"loki_url": loki_url}
            )

    root_logger.info(
        "Logging configured",
        extra={
            "level": level,
            "format": log_format,
            "service": service_name,
            "loki_enabled": loki_url is not None,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for a module.

    Args:
        name: Logger name (usually __name__ from calling module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def add_correlation_id(
    logger: logging.Logger, correlation_id: str
) -> logging.LoggerAdapter:
    """Create logger adapter with correlation ID for request tracing.

    Args:
        logger: Base logger instance
        correlation_id: Unique identifier for request/operation tracing

    Returns:
        LoggerAdapter with correlation_id in extra fields
    """
    return logging.LoggerAdapter(logger, {"correlation_id": correlation_id})
