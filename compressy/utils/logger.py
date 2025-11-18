"""
Comprehensive logging system with RFC 5424 syslog severity levels.

This module provides a singleton logger that outputs to both console and file,
with configurable log rotation and detailed error tracking.
"""

import logging
import sys
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path


# ============================================================================
# RFC 5424 Syslog Severity Levels
# ============================================================================

# Map RFC 5424 severity levels to Python logging levels
# RFC 5424: 0=Emergency, 1=Alert, 2=Critical, 3=Error, 4=Warning, 5=Notice, 6=Informational, 7=Debug
EMERGENCY = 70  # Custom level above CRITICAL
ALERT = 60  # Custom level above ERROR but below CRITICAL
NOTICE = 25  # Custom level between INFO and WARNING

# Add custom levels to logging
logging.addLevelName(EMERGENCY, "EMERGENCY")
logging.addLevelName(ALERT, "ALERT")
logging.addLevelName(NOTICE, "NOTICE")


# ============================================================================
# Custom Formatter
# ============================================================================


class DetailedFormatter(logging.Formatter):
    """Formatter with location tracking (module:function:line)."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with detailed location information."""
        # Add location information
        location = f"{record.module}:{record.funcName}:{record.lineno}"
        record.location = location

        # Format the message
        formatted = super().format(record)

        # Add exception info if present (for file handler)
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        return formatted


class SimpleFormatter(logging.Formatter):
    """Simple formatter for console output (no location info)."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with simple format for console."""
        return super().format(record)


# ============================================================================
# Singleton Logger
# ============================================================================


class CompressyLogger:
    """
    Thread-safe singleton logger for Compressy application.

    Features:
    - RFC 5424 syslog severity levels
    - Dual output: console (INFO+) and file (all levels)
    - Location tracking in file logs
    - Full tracebacks to file, simplified to console
    - Optional log rotation (size or time based)
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Ensure only one instance exists (thread-safe singleton)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize logger (only once)."""
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._logger = logging.getLogger("compressy")
        self._logger.setLevel(logging.DEBUG)  # Capture all levels
        self._logger.propagate = False  # Don't propagate to root logger

        self._console_handler = None
        self._file_handler = None
        self._log_dir = None

        self._cleanup_handlers()

    def configure(
        self,
        log_level: str = "INFO",
        log_dir: str = "logs",
        enable_console: bool = True,
        enable_file: bool = True,
        rotation_enabled: bool = False,
        rotation_type: str = "size",
        max_bytes: int = 10485760,  # 10 MB
        backup_count: int = 5,
        when: str = "midnight",
    ) -> None:
        """
        Configure the logger with specified settings.

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files
            enable_console: Enable console output
            enable_file: Enable file output
            rotation_enabled: Enable log rotation
            rotation_type: Type of rotation ("size" or "time")
            max_bytes: Max bytes for size-based rotation
            backup_count: Number of backup files to keep
            when: When to rotate for time-based rotation (e.g., "midnight", "H")
        """
        self._cleanup_handlers()

        # Reset references
        self._console_handler = None
        self._file_handler = None
        self._log_dir = None

        # Set log level
        level = getattr(logging, log_level.upper(), logging.INFO)
        self._logger.setLevel(level)

        # Configure console handler
        if enable_console:
            self._console_handler = logging.StreamHandler(sys.stdout)
            self._console_handler.setLevel(logging.INFO)  # Console shows INFO and above
            console_formatter = SimpleFormatter(fmt="%(message)s")
            self._console_handler.setFormatter(console_formatter)
            self._logger.addHandler(self._console_handler)

        # Configure file handler
        if enable_file:
            # Create log directory
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            self._log_dir = log_path

            # Create log filename with date
            log_filename = f"compressy_{datetime.now().strftime('%Y%m%d')}.log"
            log_file = log_path / log_filename

            # Choose handler based on rotation settings
            if rotation_enabled:
                if rotation_type == "size":
                    self._file_handler = RotatingFileHandler(
                        log_file,
                        maxBytes=max_bytes,
                        backupCount=backup_count,
                        encoding="utf-8",
                        delay=True,
                    )
                elif rotation_type == "time":
                    self._file_handler = TimedRotatingFileHandler(
                        log_file,
                        when=when,
                        backupCount=backup_count,
                        encoding="utf-8",
                        delay=True,
                    )
                else:
                    raise ValueError(f"Invalid rotation_type: {rotation_type}. Must be 'size' or 'time'.")
            else:
                self._file_handler = logging.FileHandler(log_file, encoding="utf-8", delay=True)

            self._enable_auto_release(self._file_handler)
            self._file_handler.setLevel(level)  # File captures all configured levels
            file_formatter = DetailedFormatter(
                fmt="%(asctime)s [%(levelname)s] [%(location)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            self._file_handler.setFormatter(file_formatter)
            self._logger.addHandler(self._file_handler)

    def get_logger(self) -> logging.Logger:
        """Get the underlying logger instance."""
        return self._logger

    def _cleanup_handlers(self) -> None:
        """Close and remove all handlers from the logger."""
        handlers = list(self._logger.handlers)
        for handler in handlers:
            self._release_handler_stream(handler)
            try:
                handler.close()
            except Exception:
                pass
            self._logger.removeHandler(handler)

    @staticmethod
    def _release_handler_stream(handler: logging.Handler) -> None:
        """Flush and close handler stream without marking handler as closed."""
        if not hasattr(handler, "baseFilename"):
            return
        stream = getattr(handler, "stream", None)
        if stream is None:
            return
        try:
            stream.flush()
        except Exception:
            pass
        try:
            stream.close()
        except Exception:
            pass
        handler.stream = None  # type: ignore[attr-defined]

    def _enable_auto_release(self, handler: logging.Handler) -> None:
        """Ensure handler releases underlying stream after each emit."""
        original_emit = handler.emit

        def emit(record: logging.LogRecord, *, _original_emit=original_emit, _handler=handler):
            _original_emit(record)
            self._release_handler_stream(_handler)

        handler.emit = emit  # type: ignore[assignment]

    # Convenience methods for RFC 5424 severity levels

    def emergency(self, msg: str, *args, **kwargs) -> None:
        """Log emergency message (severity 0 - system is unusable)."""
        self._logger.log(EMERGENCY, msg, *args, **kwargs)

    def alert(self, msg: str, *args, **kwargs) -> None:
        """Log alert message (severity 1 - action must be taken immediately)."""
        self._logger.log(ALERT, msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        """Log critical message (severity 2 - critical conditions)."""
        self._logger.critical(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        """Log error message (severity 3 - error conditions)."""
        self._logger.error(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log warning message (severity 4 - warning conditions)."""
        self._logger.warning(msg, *args, **kwargs)

    def notice(self, msg: str, *args, **kwargs) -> None:
        """Log notice message (severity 5 - normal but significant condition)."""
        self._logger.log(NOTICE, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        """Log informational message (severity 6 - informational messages)."""
        self._logger.info(msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log debug message (severity 7 - debug-level messages)."""
        self._logger.debug(msg, *args, **kwargs)


# ============================================================================
# Global Logger Instance
# ============================================================================


def get_logger() -> CompressyLogger:
    """
    Get the global CompressyLogger instance.

    Returns:
        Singleton CompressyLogger instance
    """
    return CompressyLogger()
