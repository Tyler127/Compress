"""
Tests for compressy.utils.format module.
"""
import pytest
from compressy.utils.format import format_size


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

