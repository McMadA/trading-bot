"""Logging setup with dashboard handler for web UI access."""

import os
import logging
import threading
from collections import deque
from logging.handlers import RotatingFileHandler


class DashboardHandler(logging.Handler):
    """Custom handler that stores log records for the web dashboard."""

    def __init__(self, max_records=500):
        super().__init__()
        self._records = deque(maxlen=max_records)
        self._lock = threading.Lock()

    def emit(self, record):
        msg = self.format(record)
        with self._lock:
            self._records.append(msg)

    def get_records(self, count=100):
        with self._lock:
            items = list(self._records)
        return items[-count:]


def setup_logging(config):
    """Configure root logger with file, console, and dashboard handlers."""
    log_level = getattr(logging, config.get("logging.level", "INFO").upper(), logging.INFO)
    log_file = config.get("logging.file", "logs/trading.log")
    max_bytes = config.get("logging.max_bytes", 10485760)
    backup_count = config.get("logging.backup_count", 5)

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(log_level)

    # File handler
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # Dashboard handler
    dashboard_handler = DashboardHandler()
    dashboard_handler.setFormatter(formatter)
    root.addHandler(dashboard_handler)

    return dashboard_handler
