"""
Tests for compressy.utils.file_processor module.
"""

import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from compressy.utils.file_processor import FileProcessor


@pytest.mark.unit
class TestFileProcessor:
    """Tests for FileProcessor class."""

    def test_preserve_timestamps(self, temp_dir):
        """Test that timestamps are preserved correctly."""
        source_file = temp_dir / "source.txt"
        dest_file = temp_dir / "dest.txt"

        # Create source file
        source_file.write_text("test content")

        # Set specific timestamps on source
        original_mtime = 1234567890.0
        original_atime = 1234567890.0
        os.utime(source_file, (original_atime, original_mtime))

        # Create destination file
        dest_file.write_text("test content")

        # Preserve timestamps
        FileProcessor.preserve_timestamps(source_file, dest_file)

        # Verify timestamps were copied
        dest_stat = dest_file.stat()
        # Allow small tolerance for filesystem precision
        assert abs(dest_stat.st_mtime - original_mtime) < 1.0
        assert abs(dest_stat.st_atime - original_atime) < 1.0

    def test_determine_output_path_overwrite_mode(self, temp_dir):
        """Test output path determination in overwrite mode."""
        source_file = temp_dir / "test.mp4"
        source_file.touch()
        source_folder = temp_dir
        compressed_folder = temp_dir / "compressed"

        output_path = FileProcessor.determine_output_path(source_file, source_folder, compressed_folder, overwrite=True)

        # Should be temp file in same directory
        assert output_path.parent == source_file.parent
        assert output_path.stem == "test_tmp"
        assert output_path.suffix == ".mp4"

    def test_determine_output_path_non_overwrite_mode(self, temp_dir):
        """Test output path determination in non-overwrite mode."""
        source_file = temp_dir / "test.mp4"
        source_file.touch()
        source_folder = temp_dir
        compressed_folder = temp_dir / "compressed"

        output_path = FileProcessor.determine_output_path(
            source_file, source_folder, compressed_folder, overwrite=False
        )

        # Should be in compressed folder with relative path
        assert compressed_folder in output_path.parents
        assert output_path.name == "test.mp4"
        # Parent directory should be created
        assert output_path.parent.exists()

    def test_determine_output_path_nested_file(self, temp_dir):
        """Test output path for nested file in non-overwrite mode."""
        # Create nested structure
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        source_file = subdir / "test.mp4"
        source_file.touch()
        source_folder = temp_dir
        compressed_folder = temp_dir / "compressed"

        output_path = FileProcessor.determine_output_path(
            source_file, source_folder, compressed_folder, overwrite=False
        )

        # Should preserve relative path structure
        assert "subdir" in str(output_path)
        assert compressed_folder in output_path.parents
        assert output_path.name == "test.mp4"
        # Parent directories should be created
        assert output_path.parent.exists()

    def test_handle_overwrite_file_exists(self, temp_dir):
        """Test overwrite handling when temp file exists."""
        original_path = temp_dir / "original.mp4"
        temp_path = temp_dir / "original_tmp.mp4"

        # Create temp file with content
        temp_path.write_text("temp content")

        # Handle overwrite
        FileProcessor.handle_overwrite(original_path, temp_path)

        # Original should now have temp content
        assert original_path.exists()
        assert original_path.read_text() == "temp content"
        # Temp file should be gone
        assert not temp_path.exists()

    def test_handle_overwrite_file_not_exists(self, temp_dir):
        """Test overwrite handling when temp file doesn't exist."""
        original_path = temp_dir / "original.mp4"
        temp_path = temp_dir / "original_tmp.mp4"

        # Handle overwrite when temp doesn't exist
        FileProcessor.handle_overwrite(original_path, temp_path)

        # Original should not exist (nothing to replace)
        assert not original_path.exists()

    def test_preserve_timestamps_copies_all_times(self, temp_dir):
        """Test that preserve_timestamps copies all time attributes."""
        source_file = temp_dir / "source.txt"
        dest_file = temp_dir / "dest.txt"

        source_file.write_text("test")
        dest_file.write_text("test")

        # Set different times on source
        source_time = time.time() - 1000  # 1000 seconds ago
        os.utime(source_file, (source_time, source_time))

        # Preserve timestamps
        FileProcessor.preserve_timestamps(source_file, dest_file)

        # Verify timestamps match
        source_stat = source_file.stat()
        dest_stat = dest_file.stat()

        # Allow small tolerance
        assert abs(dest_stat.st_mtime - source_stat.st_mtime) < 1.0
        assert abs(dest_stat.st_atime - source_stat.st_atime) < 1.0

    def test_preserve_timestamps_exception_handler(self, temp_dir):
        """Test that preserve_timestamps handles exceptions gracefully."""
        source_file = temp_dir / "source.txt"
        dest_file = temp_dir / "dest.txt"

        source_file.write_text("test")
        dest_file.write_text("test")

        # Mock stat() to raise an exception
        with patch.object(Path, "stat", side_effect=OSError("Permission denied")):
            with patch("compressy.utils.file_processor.get_logger") as mock_get_logger:
                mock_logger = mock_get_logger.return_value

                # Should not raise, but log warning
                FileProcessor.preserve_timestamps(source_file, dest_file)

                # Should log warning
                mock_logger.warning.assert_called_once()
                call_args = mock_logger.warning.call_args
                assert "Failed to preserve timestamps" in str(call_args)
