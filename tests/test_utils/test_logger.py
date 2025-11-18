"""
Unit tests for the logging system.
"""

import logging
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

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
            log_level="DEBUG", log_dir=tmpdir, enable_console=True, enable_file=True, rotation_enabled=False
        )

        assert logger._log_dir == Path(tmpdir)
        assert logger._console_handler is not None
        assert logger._file_handler is not None


def test_logger_configuration_console_only():
    """Test logger with console output only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(log_level="INFO", log_dir=tmpdir, enable_console=True, enable_file=False)

        assert logger._console_handler is not None
        assert logger._file_handler is None


def test_logger_configuration_file_only():
    """Test logger with file output only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(log_level="INFO", log_dir=tmpdir, enable_console=False, enable_file=True)

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
            backup_count=3,
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
            backup_count=5,
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
                log_level="INFO", log_dir=tmpdir, enable_file=True, rotation_enabled=True, rotation_type="invalid"
            )


# ============================================================================
# Severity Level Tests
# ============================================================================


def test_all_severity_levels():
    """Test all RFC 5424 severity levels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(log_level="DEBUG", log_dir=tmpdir, enable_console=False, enable_file=True)

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
            log_level="WARNING", log_dir=tmpdir, enable_console=False, enable_file=True  # Only WARNING and above
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
    formatter = DetailedFormatter(fmt="%(asctime)s [%(levelname)s] [%(location)s] %(message)s")
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test_file.py", lineno=42, msg="Test message", args=(), exc_info=None
    )
    record.module = "test_module"
    record.funcName = "test_function"

    formatted = formatter.format(record)
    assert "test_module:test_function:42" in formatted
    assert "Test message" in formatted


def test_simple_formatter_no_location():
    """Test that SimpleFormatter doesn't include location."""
    formatter = SimpleFormatter(fmt="%(message)s")
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test_file.py", lineno=42, msg="Test message", args=(), exc_info=None
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
        logger.configure(log_level="DEBUG", log_dir=tmpdir, enable_console=False, enable_file=True)

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
        logger.configure(log_level="ERROR", log_dir=tmpdir, enable_console=False, enable_file=True)

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
        logger.configure(log_level="DEBUG", log_dir=tmpdir, enable_console=True, enable_file=False)

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
        logger.configure(log_level="DEBUG", log_dir=tmpdir, enable_console=False, enable_file=True)

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
        log_content = log_files[0].read_text(encoding="utf-8")

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


def test_detailed_formatter_exception_info():
    """Test DetailedFormatter handles exception info correctly."""
    formatter = DetailedFormatter()

    # Create a record with exc_info but no exc_text
    try:
        raise ValueError("test exception")
    except ValueError:
        import sys

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error",
            args=(),
            exc_info=sys.exc_info(),
        )
        record.exc_text = None  # Ensure it's None initially

        formatted = formatter.format(record)
        assert "Test error" in formatted
        # exc_text should be set by the formatter (line 51)
        assert record.exc_text is not None


def test_detailed_formatter_exception_info_already_set():
    """Test DetailedFormatter skips setting exc_text if already set."""
    formatter = DetailedFormatter()

    # Create a record with exc_info and exc_text already set
    try:
        raise ValueError("test exception")
    except ValueError:
        import sys

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error",
            args=(),
            exc_info=sys.exc_info(),
        )
        record.exc_text = "Already set"  # Set it beforehand

        # Should not overwrite existing exc_text (line 50 condition fails)
        formatted = formatter.format(record)
        assert "Test error" in formatted
        # exc_text should remain as set
        assert record.exc_text == "Already set"


def test_detailed_formatter_sets_exc_text_when_missing():
    """Test DetailedFormatter sets exc_text from exc_info when exc_text is not set (line 51)."""
    formatter = DetailedFormatter()

    # Create a record with exc_info but ensure exc_text is not set
    try:
        raise RuntimeError("test exception for line 51")
    except RuntimeError:
        import sys

        exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error for coverage",
            args=(),
            exc_info=exc_info,
        )

        # Mock the parent format method to return formatted string but clear exc_text
        # This simulates a scenario where exc_text is not set, allowing line 51 to execute
        original_format = logging.Formatter.format

        def mock_parent_format(self, record):
            # Call parent format but then clear exc_text to test our line 51
            result = original_format(self, record)
            # Clear exc_text after parent format so our code at line 51 will set it
            record.exc_text = None
            return result

        # Patch the parent format method to clear exc_text after it's set
        with patch.object(logging.Formatter, "format", mock_parent_format):
            # This should trigger line 51: record.exc_text = self.formatException(record.exc_info)
            formatted = formatter.format(record)

            assert "Test error for coverage" in formatted
            # After formatting, exc_text should be set by line 51
            assert hasattr(record, "exc_text")
            assert record.exc_text is not None
            assert "RuntimeError: test exception for line 51" in record.exc_text


def test_logger_handler_close_exception():
    """Test that logger handles exceptions when closing handlers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(log_level="DEBUG", log_dir=tmpdir, enable_console=False, enable_file=True)

        # Get the file handler
        handlers = logger._logger.handlers
        assert len(handlers) > 0

        # Mock close to raise exception
        with patch.object(handlers[0], "close", side_effect=Exception("Close error")):
            # Should not raise, just pass silently
            logger.configure(log_level="INFO", log_dir=tmpdir, enable_console=False, enable_file=True)


def test_logger_stream_flush_close_exceptions():
    """Test that logger handles exceptions when flushing/closing streams."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CompressyLogger()
        logger.configure(log_level="DEBUG", log_dir=tmpdir, enable_console=False, enable_file=True)

        # Get the file handler
        handlers = logger._logger.handlers
        assert len(handlers) > 0
        handler = handlers[0]

        # Create a mock handler with a stream that will raise exceptions
        from unittest.mock import MagicMock

        mock_handler = MagicMock()
        mock_stream = MagicMock()
        mock_stream.flush.side_effect = Exception("Flush error")
        mock_stream.close.side_effect = Exception("Close error")
        mock_handler.stream = mock_stream
        mock_handler.baseFilename = "test.log"

        # Should not raise, just pass silently
        logger._release_handler_stream(mock_handler)

        # Verify exceptions were caught (no exception raised)
        assert mock_stream.flush.called
        assert mock_stream.close.called
