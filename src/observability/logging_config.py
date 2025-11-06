"""Logging configuration for Telegram Fetcher Service."""
import logging
import sys
from typing import Optional

from pythonjsonlogger import jsonlogger


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    service_name: str = "telegram-fetcher",
) -> logging.Logger:
    """Setup structured logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
        service_name: Name of the service for log entries
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))
    
    if log_format == "json":
        # JSON formatter for structured logging
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
        )
    else:
        # Standard text formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get logger instance.
    
    Args:
        name: Logger name (uses service name if not provided)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name or "telegram-fetcher")
