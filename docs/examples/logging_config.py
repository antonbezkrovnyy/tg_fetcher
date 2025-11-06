"""Structured logging with Loki integration"""
import logging
import sys
import os
from datetime import datetime, UTC
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.fromtimestamp(record.created, UTC).isoformat()
        log_record['level'] = record.levelname
        log_record['service'] = os.getenv('SERVICE_NAME', 'telegram-fetcher')
        log_record['environment'] = os.getenv('ENVIRONMENT', 'development')
        if hasattr(record, 'channel'):
            log_record['channel'] = record.channel
        if hasattr(record, 'date'):
            log_record['date'] = record.date


def setup_logging(level=None, enable_console=True, enable_file=True, enable_loki=True, log_dir="/var/log"):
    log_level = (level or os.getenv('LOG_LEVEL', 'INFO')).upper()
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    logger.handlers.clear()
    
    formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    if enable_file and os.path.exists(log_dir):
        try:
            log_file = os.path.join(log_dir, f"fetcher-{datetime.now(UTC).strftime('%Y%m%d')}.log")
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, log_level))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not create file handler: {e}")
    
    if enable_loki:
        try:
            from loki_handler import get_loki_handler
            # Determine batch mode: prefer immediate if Loki is ready, else fallback to batch
            loki_url = os.getenv('LOKI_URL', 'http://loki:3100')
            batch = True
            try:
                import requests
                # Avoid deadlocks: silence requests/urllib3 debug logs during handler HTTP calls
                logging.getLogger('urllib3').setLevel(logging.WARNING)
                logging.getLogger('requests').setLevel(logging.WARNING)
                ready = requests.get(loki_url.rstrip('/') + '/ready', timeout=1)
                if ready.status_code == 200:
                    batch_env = os.getenv('LOKI_BATCH', 'true').lower()
                    batch = (batch_env == 'true' or batch_env == '1' or batch_env == 'yes')
                else:
                    logger.warning(f"Loki not ready (status {ready.status_code}), using batch handler")
            except Exception:
                logger.warning("Loki readiness probe failed, using batch handler")
            loki_handler = get_loki_handler(batch=batch)
            loki_handler.setLevel(getattr(logging, log_level))
            # Используем отдельный экземпляр форматтера для Loki во избежание гонок состояния
            loki_formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
            loki_handler.setFormatter(loki_formatter)
            logger.addHandler(loki_handler)
        except Exception as e:
            logger.warning(f"Could not create Loki handler: {e}")
    
    logger.info("Logging configured", extra={'log_level': log_level, 'console_enabled': enable_console, 'file_enabled': enable_file, 'loki_enabled': enable_loki})
    return logger


def get_logger(name, **context):
    logger = logging.getLogger(name)
    if context:
        logger = logging.LoggerAdapter(logger, context)
    return logger
