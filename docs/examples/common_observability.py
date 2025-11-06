"""
Common observability utilities with fallbacks for missing modules.
Centralizes all metrics and logging configuration.
"""

import logging
from typing import Optional

# Fallback classes for missing observability modules
class MockLogger:
    """Fallback logger when real logging is unavailable."""
    def debug(self, *args, **kwargs): pass
    def info(self, msg, *args, **kwargs): 
        print(f"INFO: {msg}")
    def warning(self, msg, *args, **kwargs): 
        print(f"WARNING: {msg}")
    def error(self, msg, *args, **kwargs): 
        print(f"ERROR: {msg}")


class MockCounter:
    """Fallback counter metric."""
    def labels(self, *args, **kwargs): return self
    def inc(self, amount=1): pass


class MockHistogram:
    """Fallback histogram metric.""" 
    def labels(self, *args, **kwargs): return self
    def observe(self, value): pass


class MockGauge:
    """Fallback gauge metric."""
    def labels(self, *args, **kwargs): return self
    def set(self, value): pass


class MockMetricsExporter:
    """Fallback metrics exporter when Prometheus/observability is unavailable."""
    
    def __init__(self):
        pass
    
    def create_counter(self, name: str, description: str, labelnames=None):
        return MockCounter()
    
    def create_histogram(self, name: str, description: str, labelnames=None):
        return MockHistogram()
        
    def create_gauge(self, name: str, description: str, labelnames=None):
        return MockGauge()
    
    def record_messages_fetched(self, channel: str, count: int): 
        pass
    
    def record_fetch_duration(self, channel: str, duration: float): 
        pass
        
    def update_last_fetch_timestamp(self, channel: str, timestamp: float): 
        pass
        
    def update_progress_date(self, channel: str, date_str: str): 
        pass
        
    def record_fetch_error(self, channel: str, error_type: str): 
        pass
        
    def record_channel_processed(self): 
        pass


# Try to import real observability modules with fallbacks
try:
    from observability.metrics import MetricsExporter
    from observability.logging import setup_logging, get_logger
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    MetricsExporter = MockMetricsExporter
    setup_logging = lambda: None
    get_logger = lambda name: MockLogger()
    OBSERVABILITY_AVAILABLE = False


def get_metrics_exporter() -> MetricsExporter:
    """Get metrics exporter with automatic fallback."""
    return MetricsExporter()


def get_logger_safe(name: str):
    """Get logger with automatic fallback."""
    return get_logger(name)


def setup_logging_safe():
    """Setup logging with automatic fallback.""" 
    setup_logging()


# Standard metrics that all modules can use
class StandardMetrics:
    """Standard set of metrics used across all fetcher modules."""
    
    def __init__(self):
        self.exporter = get_metrics_exporter()
        
        # Core metrics
        self.messages_fetched = self.exporter.create_counter(
            'telegram_messages_fetched_total',
            'Total number of fetched messages',
            labelnames=['channel']
        )
        
        self.channels_processed = self.exporter.create_counter(
            'telegram_channels_processed_total', 
            'Total number of processed channels'
        )
        
        self.fetch_errors = self.exporter.create_counter(
            'telegram_fetch_errors_total',
            'Number of fetch errors',
            labelnames=['channel', 'error_type']
        )
        
        self.fetch_duration = self.exporter.create_histogram(
            'telegram_fetch_duration_seconds',
            'Time spent fetching messages (seconds)',
            labelnames=['channel']
        )
        
        self.last_fetch_timestamp = self.exporter.create_gauge(
            'telegram_last_fetch_timestamp',
            'Last successful fetch timestamp (Unix time)',
            labelnames=['channel']
        )
    
    def record_messages_fetched(self, channel: str, count: int):
        """Record number of messages fetched for a channel."""
        self.messages_fetched.labels(channel=channel).inc(count)
    
    def record_channel_processed(self):
        """Record that a channel was processed."""
        self.channels_processed.inc()
    
    def record_fetch_error(self, channel: str, error_type: str):
        """Record a fetch error."""
        self.fetch_errors.labels(channel=channel, error_type=error_type).inc()
    
    def record_fetch_duration(self, channel: str, duration: float):
        """Record fetch duration for a channel."""
        self.fetch_duration.labels(channel=channel).observe(duration)
    
    def update_last_fetch_timestamp(self, channel: str, timestamp: float):
        """Update last successful fetch timestamp."""
        self.last_fetch_timestamp.labels(channel=channel).set(timestamp)