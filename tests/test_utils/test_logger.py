"""
Unit tests for the logging system.
"""

import logging
import tempfile
import threading
from pathlib import Path

import pytest

from compressy.utils.logger import (
    ALERT,
    EMERGENCY,
    NOTICE,
    CompressyLogger,
    DetailedFormatter,
    SimpleFormatter,
    get_logger,
)


# ============================================================================
# Singleton Tests
# ============================================================================


def test_singleton_pattern():
    """Test that CompressyLogger is a singleton."""
    logger1 = CompressyLogger()
    logger2 = CompressyLogger()
    assert logger1 is logger2, "CompressyLogger should be a singleton"


def test_singleton_thread_safe():
    """Test that singleton is thread-safe."""
    instances = []

    def create_instance():
        instances.append(CompressyLogger())

    threads = [threading.Thread(target=create_instance) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # All instances should be the same object
    assert all(inst is instances[0] for inst in instances), "Singleton should be thread-safe"


def test_get_logger_returns_singleton():
    """Test that get_logger() returns the singleton instance."""
    logger1 = get_logger()
    logger2 = get_logger()
    assert logger1 is logger2, "get_logger() should return singleton"


# ============================================================================
# Configuration Tests
# ============================================================================


def test_logger_configuration_basic():
    """Test basic logger configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(
            log_level="DEBUG",
            log_dir=tmpdir,
            enable_console=True,
            enable_file=True,
            rotation_enabled=False
        )

        assert logger._log_dir == Path(tmpdir)
        assert logger._console_handler is not None
        assert logger._file_handler is not None


def test_logger_configuration_console_only():
    """Test logger with console output only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(
            log_level="INFO",
            log_dir=tmpdir,
            enable_console=True,
            enable_file=False
        )

        assert logger._console_handler is not None
        assert logger._file_handler is None


def test_logger_configuration_file_only():
    """Test logger with file output only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(
            log_level="INFO",
            log_dir=tmpdir,
            enable_console=False,
            enable_file=True
        )

        assert logger._console_handler is None
        assert logger._file_handler is not None


def test_logger_creates_log_directory():
    """Test that logger creates log directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "new_logs"
        assert not log_dir.exists()

        logger = CompressyLogger()
        logger.configure(log_level="INFO", log_dir=str(log_dir))

        assert log_dir.exists(), "Logger should create log directory"


def test_logger_rotation_size_based():
    """Test size-based log rotation configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(
            log_level="INFO",
            log_dir=tmpdir,
            enable_file=True,
            rotation_enabled=True,
            rotation_type="size",
            max_bytes=1024,
            backup_count=3
        )

        from logging.handlers import RotatingFileHandler
        assert isinstance(logger._file_handler, RotatingFileHandler)
        assert logger._file_handler.maxBytes == 1024
        assert logger._file_handler.backupCount == 3


def test_logger_rotation_time_based():
    """Test time-based log rotation configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(
            log_level="INFO",
            log_dir=tmpdir,
            enable_file=True,
            rotation_enabled=True,
            rotation_type="time",
            when="H",
            backup_count=5
        )

        from logging.handlers import TimedRotatingFileHandler
        assert isinstance(logger._file_handler, TimedRotatingFileHandler)
        assert logger._file_handler.backupCount == 5


def test_logger_rotation_invalid_type():
    """Test that invalid rotation type raises error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        with pytest.raises(ValueError, match="Invalid rotation_type"):
            logger.configure(
                log_level="INFO",
                log_dir=tmpdir,
                enable_file=True,
                rotation_enabled=True,
                rotation_type="invalid"
            )


# ============================================================================
# Severity Level Tests
# ============================================================================


def test_all_severity_levels():
    """Test all RFC 5424 severity levels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(
            log_level="DEBUG",
            log_dir=tmpdir,
            enable_console=False,
            enable_file=True
        )

        # Test all severity levels
        logger.emergency("Emergency message")
        logger.alert("Alert message")
        logger.critical("Critical message")
        logger.error("Error message")
        logger.warning("Warning message")
        logger.notice("Notice message")
        logger.info("Info message")
        logger.debug("Debug message")

        # Check that log file was created and has content
        log_files = list(Path(tmpdir).glob("*.log"))
        assert len(log_files) > 0, "Log file should be created"

        log_content = log_files[0].read_text()
        assert "Emergency message" in log_content
        assert "Alert message" in log_content
        assert "Critical message" in log_content
        assert "Error message" in log_content
        assert "Warning message" in log_content
        assert "Notice message" in log_content
        assert "Info message" in log_content
        assert "Debug message" in log_content


def test_custom_severity_levels_registered():
    """Test that custom severity levels are registered."""
    assert logging.getLevelName(EMERGENCY) == "EMERGENCY"
    assert logging.getLevelName(ALERT) == "ALERT"
    assert logging.getLevelName(NOTICE) == "NOTICE"


def test_log_level_filtering():
    """Test that log level filtering works correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(
            log_level="WARNING",  # Only WARNING and above
            log_dir=tmpdir,
            enable_console=False,
            enable_file=True
        )

        logger.debug("Debug message")
        logger.info("Info message")
        logger.notice("Notice message")
        logger.warning("Warning message")
        logger.error("Error message")

        log_files = list(Path(tmpdir).glob("*.log"))
        log_content = log_files[0].read_text()

        # Only WARNING and above should be logged
        assert "Debug message" not in log_content
        assert "Info message" not in log_content
        assert "Notice message" not in log_content
        assert "Warning message" in log_content
        assert "Error message" in log_content


# ============================================================================
# Formatter Tests
# ============================================================================


def test_detailed_formatter_includes_location():
    """Test that DetailedFormatter includes location information."""
    formatter = DetailedFormatter(fmt='%(asctime)s [%(levelname)s] [%(location)s] %(message)s')
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.module = "test_module"
    record.funcName = "test_function"

    formatted = formatter.format(record)
    assert "test_module:test_function:42" in formatted
    assert "Test message" in formatted


def test_simple_formatter_no_location():
    """Test that SimpleFormatter doesn't include location."""
    formatter = SimpleFormatter(fmt='%(message)s')
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )

    formatted = formatter.format(record)
    assert formatted == "Test message"
    assert ":" not in formatted  # No location markers


# ============================================================================
# File Output Tests
# ============================================================================


def test_log_file_creation():
    """Test that log file is created with correct naming."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(log_level="INFO", log_dir=tmpdir, enable_file=True)

        logger.info("Test message")

        # Check log file was created with correct pattern
        log_files = list(Path(tmpdir).glob("compressy_*.log"))
        assert len(log_files) == 1, "One log file should be created"
        assert "compressy_" in log_files[0].name


def test_log_file_content():
    """Test that log messages are written to file correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(
            log_level="DEBUG",
            log_dir=tmpdir,
            enable_console=False,
            enable_file=True
        )

        test_message = "Unique test message 12345"
        logger.info(test_message)

        log_files = list(Path(tmpdir).glob("*.log"))
        log_content = log_files[0].read_text()

        assert test_message in log_content
        assert "[INFO]" in log_content


def test_traceback_logging():
    """Test that exceptions with tracebacks are logged correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(
            log_level="ERROR",
            log_dir=tmpdir,
            enable_console=False,
            enable_file=True
        )

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.error("Error occurred", exc_info=True)

        log_files = list(Path(tmpdir).glob("*.log"))
        log_content = log_files[0].read_text()

        assert "Error occurred" in log_content
        assert "ValueError: Test exception" in log_content
        assert "Traceback" in log_content


# ============================================================================
# Console vs File Output Tests
# ============================================================================


def test_console_shows_info_and_above(capsys):
    """Test that console only shows INFO level and above."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(
            log_level="DEBUG",
            log_dir=tmpdir,
            enable_console=True,
            enable_file=False
        )

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")

        captured = capsys.readouterr()

        # Console should only show INFO and above
        assert "Debug message" not in captured.out
        assert "Info message" in captured.out
        assert "Warning message" in captured.out


def test_file_captures_all_levels():
    """Test that file captures all configured levels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(
            log_level="DEBUG",
            log_dir=tmpdir,
            enable_console=False,
            enable_file=True
        )

        logger.debug("Debug message")
        logger.info("Info message")
        logger.error("Error message")

        log_files = list(Path(tmpdir).glob("*.log"))
        log_content = log_files[0].read_text()

        # File should capture all levels
        assert "Debug message" in log_content
        assert "Info message" in log_content
        assert "Error message" in log_content


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_multiple_configure_calls():
    """Test that logger can be reconfigured."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()

        # First configuration
        logger.configure(log_level="INFO", log_dir=tmpdir)
        assert len(logger._logger.handlers) >= 1

        # Second configuration
        logger.configure(log_level="DEBUG", log_dir=tmpdir)
        # Handlers should be replaced, not duplicated
        assert len(logger._logger.handlers) <= 2  # Console + File at most


def test_logger_with_unicode_messages():
    """Test that logger handles unicode characters correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(log_level="INFO", log_dir=tmpdir, enable_file=True)

        unicode_message = "Test message with émojis 🎉 and spëcial çharacters"
        logger.info(unicode_message)

        log_files = list(Path(tmpdir).glob("*.log"))
        log_content = log_files[0].read_text(encoding='utf-8')

        assert unicode_message in log_content


def test_logger_with_extra_fields():
    """Test that logger handles extra fields correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(log_level="INFO", log_dir=tmpdir, enable_file=True)

        logger.info("Test with extras", extra={"custom_field": "custom_value"})

        log_files = list(Path(tmpdir).glob("*.log"))
        log_content = log_files[0].read_text()

        assert "Test with extras" in log_content


def test_get_underlying_logger():
    """Test that get_logger() returns correct logging.Logger instance."""
    logger = CompressyLogger()
    underlying = logger.get_logger()

    assert isinstance(underlying, logging.Logger)
    assert underlying.name == "compressy"

