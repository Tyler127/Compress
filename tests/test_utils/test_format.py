"""
Tests for compressy.utils.format module.
"""

import pytest

from compressy.utils.format import format_size, parse_resolution, parse_size


@pytest.mark.unit
class TestFormatSize:
    """Tests for format_size function."""

    def test_format_bytes(self):
        """Test formatting bytes."""
        assert format_size(512) == "512.00 B"
        assert format_size(0) == "0.00 B"
        assert format_size(1) == "1.00 B"
        assert format_size(1023) == "1023.00 B"

    def test_format_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_size(1024) == "1.00 KB"
        assert format_size(2048) == "2.00 KB"
        assert format_size(1536) == "1.50 KB"
        assert format_size(1024 * 1023) == "1023.00 KB"

    def test_format_megabytes(self):
        """Test formatting megabytes."""
        assert format_size(1024 * 1024) == "1.00 MB"
        assert format_size(1024 * 1024 * 2) == "2.00 MB"
        assert format_size(1024 * 1024 * 1.5) == "1.50 MB"
        assert format_size(1024 * 1024 * 1023) == "1023.00 MB"

    def test_format_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_size(1024 * 1024 * 1024) == "1.00 GB"
        assert format_size(1024 * 1024 * 1024 * 2) == "2.00 GB"
        assert format_size(1024 * 1024 * 1024 * 1.5) == "1.50 GB"
        assert format_size(1024 * 1024 * 1024 * 1023) == "1023.00 GB"

    def test_format_terabytes(self):
        """Test formatting terabytes."""
        assert format_size(1024 * 1024 * 1024 * 1024) == "1.00 TB"
        assert format_size(1024 * 1024 * 1024 * 1024 * 2) == "2.00 TB"
        assert format_size(1024 * 1024 * 1024 * 1024 * 1.5) == "1.50 TB"

    def test_format_petabytes(self):
        """Test formatting petabytes (edge case)."""
        # Very large number that exceeds TB
        large_size = 1024 * 1024 * 1024 * 1024 * 1024
        result = format_size(large_size)
        assert "PB" in result
        assert "1.00" in result

    def test_format_rounding(self):
        """Test that values are rounded to 2 decimal places."""
        # 1536 bytes = 1.5 KB
        assert format_size(1536) == "1.50 KB"
        # 1537 bytes = 1.5009765625 KB, should round to 1.50 KB
        assert format_size(1537) == "1.50 KB"
        # 1538 bytes = 1.501953125 KB, should round to 1.50 KB
        assert format_size(1538) == "1.50 KB"

    def test_format_large_numbers(self):
        """Test formatting very large numbers."""
        # 10 TB
        size = 10 * 1024 * 1024 * 1024 * 1024
        assert format_size(size) == "10.00 TB"

        # 100 GB
        size = 100 * 1024 * 1024 * 1024
        assert format_size(size) == "100.00 GB"

    def test_format_exact_boundaries(self):
        """Test formatting at exact unit boundaries."""
        # Exactly 1 KB
        assert format_size(1024) == "1.00 KB"
        # Exactly 1 MB
        assert format_size(1024 * 1024) == "1.00 MB"
        # Exactly 1 GB
        assert format_size(1024 * 1024 * 1024) == "1.00 GB"
        # Exactly 1 TB
        assert format_size(1024 * 1024 * 1024 * 1024) == "1.00 TB"


@pytest.mark.unit
class TestParseSize:
    """Tests for parse_size function."""

    def test_parse_bytes(self):
        """Test parsing byte values."""
        assert parse_size("100B") == 100
        assert parse_size("1024B") == 1024
        assert parse_size("0B") == 0

    def test_parse_kilobytes(self):
        """Test parsing kilobyte values."""
        assert parse_size("1KB") == 1024
        assert parse_size("1K") == 1024
        assert parse_size("10KB") == 10 * 1024
        assert parse_size("1.5KB") == int(1.5 * 1024)

    def test_parse_megabytes(self):
        """Test parsing megabyte values."""
        assert parse_size("1MB") == 1024 * 1024
        assert parse_size("1M") == 1024 * 1024
        assert parse_size("10MB") == 10 * 1024 * 1024
        assert parse_size("1.5MB") == int(1.5 * 1024 * 1024)
        assert parse_size("500MB") == 500 * 1024 * 1024

    def test_parse_gigabytes(self):
        """Test parsing gigabyte values."""
        assert parse_size("1GB") == 1024 * 1024 * 1024
        assert parse_size("1G") == 1024 * 1024 * 1024
        assert parse_size("2GB") == 2 * 1024 * 1024 * 1024
        assert parse_size("1.5GB") == int(1.5 * 1024 * 1024 * 1024)

    def test_parse_terabytes(self):
        """Test parsing terabyte values."""
        assert parse_size("1TB") == 1024 * 1024 * 1024 * 1024
        assert parse_size("1T") == 1024 * 1024 * 1024 * 1024
        assert parse_size("2TB") == 2 * 1024 * 1024 * 1024 * 1024

    def test_parse_case_insensitive(self):
        """Test that parsing is case insensitive."""
        assert parse_size("1mb") == 1024 * 1024
        assert parse_size("1MB") == 1024 * 1024
        assert parse_size("1Mb") == 1024 * 1024
        assert parse_size("1kb") == 1024
        assert parse_size("1KB") == 1024
        assert parse_size("1gb") == 1024 * 1024 * 1024

    def test_parse_with_spaces(self):
        """Test parsing with whitespace."""
        assert parse_size("1 MB") == 1024 * 1024
        assert parse_size("  10KB  ") == 10 * 1024
        assert parse_size("1.5 GB") == int(1.5 * 1024 * 1024 * 1024)

    def test_parse_decimal_values(self):
        """Test parsing decimal values."""
        assert parse_size("1.5MB") == int(1.5 * 1024 * 1024)
        assert parse_size("0.5GB") == int(0.5 * 1024 * 1024 * 1024)
        assert parse_size("2.75KB") == int(2.75 * 1024)

    def test_parse_no_unit_defaults_to_bytes(self):
        """Test parsing numbers without units defaults to bytes."""
        assert parse_size("100") == 100
        assert parse_size("1024") == 1024

    def test_parse_invalid_format(self):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError, match="Invalid size format"):
            parse_size("invalid")
        with pytest.raises(ValueError, match="Invalid size format"):
            parse_size("10XB")
        with pytest.raises(ValueError, match="Invalid size format"):
            parse_size("MB10")

    def test_parse_negative_size(self):
        """Test that negative sizes raise ValueError."""
        with pytest.raises(ValueError, match="Size cannot be negative"):
            parse_size("-1MB")
        with pytest.raises(ValueError, match="Size cannot be negative"):
            parse_size("-100KB")

    def test_parse_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid size string"):
            parse_size("")

    def test_parse_none(self):
        """Test that None raises ValueError."""
        with pytest.raises(ValueError, match="Invalid size string"):
            parse_size(None)

    def test_parse_edge_cases(self):
        """Test edge cases."""
        assert parse_size("0MB") == 0
        assert parse_size("0.0GB") == 0


@pytest.mark.unit
class TestParseResolution:
    """Tests for parse_resolution function."""

    def test_parse_explicit_resolution(self):
        """Test parsing explicit WIDTHxHEIGHT format."""
        assert parse_resolution("1920x1080") == (1920, 1080)
        assert parse_resolution("1280x720") == (1280, 720)
        assert parse_resolution("3840x2160") == (3840, 2160)
        assert parse_resolution("640x480") == (640, 480)

    def test_parse_named_resolutions(self):
        """Test parsing named resolutions."""
        assert parse_resolution("480p") == (854, 480)
        assert parse_resolution("720p") == (1280, 720)
        assert parse_resolution("1080p") == (1920, 1080)
        assert parse_resolution("1440p") == (2560, 1440)
        assert parse_resolution("2160p") == (3840, 2160)

    def test_parse_k_resolutions(self):
        """Test parsing K resolutions."""
        assert parse_resolution("2k") == (2048, 1080)
        assert parse_resolution("4k") == (3840, 2160)
        assert parse_resolution("8k") == (7680, 4320)

    def test_parse_case_insensitive(self):
        """Test that parsing is case insensitive."""
        assert parse_resolution("720P") == (1280, 720)
        assert parse_resolution("1080P") == (1920, 1080)
        assert parse_resolution("4K") == (3840, 2160)
        assert parse_resolution("1920X1080") == (1920, 1080)

    def test_parse_with_spaces(self):
        """Test parsing with whitespace."""
        assert parse_resolution("  1920x1080  ") == (1920, 1080)
        assert parse_resolution("  720p  ") == (1280, 720)

    def test_parse_invalid_format(self):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError, match="Invalid resolution format"):
            parse_resolution("invalid")
        with pytest.raises(ValueError, match="Invalid resolution format"):
            parse_resolution("1920")
        with pytest.raises(ValueError, match="Invalid resolution format"):
            parse_resolution("1920-1080")
        with pytest.raises(ValueError, match="Invalid resolution format"):
            parse_resolution("1920x")

    def test_parse_negative_dimensions(self):
        """Test that negative or zero dimensions raise ValueError."""
        with pytest.raises(ValueError, match="Resolution dimensions must be positive"):
            parse_resolution("0x1080")
        with pytest.raises(ValueError, match="Resolution dimensions must be positive"):
            parse_resolution("1920x0")

    def test_parse_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid resolution string"):
            parse_resolution("")

    def test_parse_none(self):
        """Test that None raises ValueError."""
        with pytest.raises(ValueError, match="Invalid resolution string"):
            parse_resolution(None)
