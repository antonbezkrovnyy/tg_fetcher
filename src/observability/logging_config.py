"""Logging configuration with Loki integration and structured logging.

Provides setup for both local logging (text/JSON) and remote logging to Loki
for centralized observability.
"""

import logging
import sys
from typing import Optional

from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""
    
    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        """Add custom fields to log record.
        
        Args:
            log_record: Dictionary to be logged
            record: Original LogRecord
            message_dict: Message dictionary from format string
        """
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = self.formatTime(record, self.datefmt)
        
        # Add level name
        log_record['level'] = record.levelname
        
        # Add logger name
        log_record['logger'] = record.name
        
        # Add thread info if available
        if hasattr(record, 'thread'):
            log_record['thread'] = record.thread
        
        # Add correlation_id if present in extra
        if hasattr(record, 'correlation_id'):
            log_record['correlation_id'] = record.correlation_id


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    service_name: str = "telegram-fetcher",
    loki_url: Optional[str] = None
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
    
    # === Console Handler ===
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if log_format == "json":
        # JSON formatter for structured logging
        json_formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(json_formatter)
    else:
        # Text formatter for human-readable output
        text_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(text_formatter)
    
    root_logger.addHandler(console_handler)
    
    # === Loki Handler (Optional) ===
    if loki_url:
        try:
            import logging_loki
            
            loki_handler = logging_loki.LokiHandler(
                url=f"{loki_url}/loki/api/v1/push",
                tags={"service": service_name},
                version="1",
            )
            loki_handler.setLevel(numeric_level)
            root_logger.addHandler(loki_handler)
            
            root_logger.info(
                f"Loki handler configured",
                extra={"loki_url": loki_url, "service": service_name}
            )
        except ImportError:
            root_logger.warning(
                "python-logging-loki not installed, skipping Loki handler. "
                "Install with: pip install python-logging-loki"
            )
        except Exception as e:
            root_logger.error(
                f"Failed to setup Loki handler: {e}",
                extra={"loki_url": loki_url}
            )
    
    root_logger.info(
        f"Logging configured",
        extra={
            "level": level,
            "format": log_format,
            "service": service_name,
            "loki_enabled": loki_url is not None
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for a module.
    
    Args:
        name: Logger name (usually __name__ from calling module)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def add_correlation_id(logger: logging.Logger, correlation_id: str) -> logging.LoggerAdapter:
    """Create logger adapter with correlation ID for request tracing.
    
    Args:
        logger: Base logger instance
        correlation_id: Unique identifier for request/operation tracing
        
    Returns:
        LoggerAdapter with correlation_id in extra fields
    """
    return logging.LoggerAdapter(logger, {'correlation_id': correlation_id})
