"""
Tests for compressy.services.statistics module.
"""

import csv
from unittest.mock import patch

import pytest

from compressy.services.statistics import StatisticsManager, StatisticsTracker


@pytest.mark.unit
class TestStatisticsTracker:
    """Tests for StatisticsTracker class."""

    def test_initialization_non_recursive(self):
        """Test StatisticsTracker initialization in non-recursive mode."""
        tracker = StatisticsTracker(recursive=False)

        assert tracker.recursive is False
        assert tracker.stats["total_files"] == 0
        assert tracker.stats["processed"] == 0
        assert tracker.stats["skipped"] == 0
        assert tracker.stats["errors"] == 0
        assert "folder_stats" not in tracker.stats
        assert tracker.stats["files"] == []
        # Verify new type and format tracking fields exist
        assert tracker.stats["videos_processed"] == 0
        assert tracker.stats["images_processed"] == 0
        assert tracker.stats["format_stats"] == {}

    def test_initialization_recursive(self):
        """Test StatisticsTracker initialization in recursive mode."""
        tracker = StatisticsTracker(recursive=True)

        assert tracker.recursive is True
        assert "folder_stats" in tracker.stats
        assert tracker.stats["folder_stats"] == {}

    def test_add_file_info(self):
        """Test adding file information."""
        tracker = StatisticsTracker(recursive=False)
        file_info = {
            "name": "test.mp4",
            "original_size": 1000,
            "compressed_size": 500,
            "space_saved": 500,
            "compression_ratio": 50.0,
            "processing_time": 1.0,
            "status": "success",
        }

        tracker.add_file_info(file_info)

        assert len(tracker.stats["files"]) == 1
        assert tracker.stats["files"][0] == file_info

    def test_add_file_info_recursive(self):
        """Test adding file information in recursive mode."""
        tracker = StatisticsTracker(recursive=True)
        file_info = {
            "name": "test.mp4",
            "original_size": 1000,
            "compressed_size": 500,
            "space_saved": 500,
            "compression_ratio": 50.0,
            "processing_time": 1.0,
            "status": "success",
        }

        tracker.add_file_info(file_info, folder_key="subdir")

        assert len(tracker.stats["files"]) == 1
        assert "subdir" in tracker.stats["folder_stats"]
        assert len(tracker.stats["folder_stats"]["subdir"]["files"]) == 1

    def test_update_stats_processed(self):
        """Test updating stats for processed file."""
        tracker = StatisticsTracker(recursive=False)

        tracker.update_stats(1000, 500, 500, "processed")

        assert tracker.stats["processed"] == 1
        assert tracker.stats["total_compressed_size"] == 500
        assert tracker.stats["space_saved"] == 500

    def test_update_stats_with_type_and_format(self):
        """Test updating stats with file type and format tracking."""
        tracker = StatisticsTracker(recursive=False)

        tracker.update_stats(1000, 500, 500, "processed", file_type="video", file_extension="mp4")

        assert tracker.stats["processed"] == 1
        assert tracker.stats["videos_processed"] == 1
        assert tracker.stats["images_processed"] == 0
        assert tracker.stats["videos_original_size"] == 1000
        assert tracker.stats["videos_compressed_size"] == 500
        assert tracker.stats["videos_space_saved"] == 500
        assert "mp4" in tracker.stats["format_stats"]
        assert tracker.stats["format_stats"]["mp4"]["count"] == 1
        assert tracker.stats["format_stats"]["mp4"]["original_size"] == 1000
        assert tracker.stats["format_stats"]["mp4"]["compressed_size"] == 500
        assert tracker.stats["format_stats"]["mp4"]["space_saved"] == 500

    def test_update_stats_image_with_format(self):
        """Test updating stats for image file with format tracking."""
        tracker = StatisticsTracker(recursive=False)

        tracker.update_stats(2000, 1500, 500, "processed", file_type="image", file_extension="jpg")

        assert tracker.stats["images_processed"] == 1
        assert tracker.stats["videos_processed"] == 0
        assert tracker.stats["images_original_size"] == 2000
        assert tracker.stats["images_compressed_size"] == 1500
        assert tracker.stats["images_space_saved"] == 500
        assert "jpg" in tracker.stats["format_stats"]
        assert tracker.stats["format_stats"]["jpg"]["count"] == 1

    def test_update_stats_skipped(self):
        """Test updating stats for skipped file."""
        tracker = StatisticsTracker(recursive=False)

        tracker.update_stats(1000, 1000, 0, "skipped")

        assert tracker.stats["skipped"] == 1
        assert tracker.stats["total_compressed_size"] == 1000
        assert tracker.stats["space_saved"] == 0

    def test_update_stats_skipped_recursive(self):
        """Test updating stats for skipped files in recursive mode (lines 102-104)."""
        tracker = StatisticsTracker(recursive=True)

        tracker.update_stats(1000, 500, 0, "skipped", folder_key="subdir")

        assert tracker.stats["skipped"] == 1
        assert "subdir" in tracker.stats["folder_stats"]
        assert tracker.stats["folder_stats"]["subdir"]["skipped"] == 1
        assert tracker.stats["folder_stats"]["subdir"]["total_compressed_size"] == 500

    def test_update_stats_error(self):
        """Test updating stats for error."""
        tracker = StatisticsTracker(recursive=False)

        tracker.update_stats(1000, 0, 0, "error")

        assert tracker.stats["errors"] == 1
        assert tracker.stats["total_compressed_size"] == 0
        assert tracker.stats["space_saved"] == 0

    def test_update_stats_error_recursive(self):
        """Test updating stats for errors in recursive mode (lines 109-110)."""
        tracker = StatisticsTracker(recursive=True)

        tracker.update_stats(1000, 0, 0, "error", folder_key="subdir")

        assert tracker.stats["errors"] == 1
        assert "subdir" in tracker.stats["folder_stats"]
        assert tracker.stats["folder_stats"]["subdir"]["errors"] == 1

    def test_update_stats_recursive(self):
        """Test updating stats in recursive mode."""
        tracker = StatisticsTracker(recursive=True)

        tracker.update_stats(1000, 500, 500, "processed", folder_key="subdir")

        assert tracker.stats["processed"] == 1
        assert "subdir" in tracker.stats["folder_stats"]
        assert tracker.stats["folder_stats"]["subdir"]["processed"] == 1
        assert tracker.stats["folder_stats"]["subdir"]["total_compressed_size"] == 500

    def test_update_stats_recursive_video_with_format(self):
        """Test updating stats in recursive mode with video type and format."""
        tracker = StatisticsTracker(recursive=True)

        tracker.update_stats(1000, 500, 500, "processed", folder_key="subdir", file_type="video", file_extension="mp4")

        assert tracker.stats["videos_processed"] == 1
        assert "subdir" in tracker.stats["folder_stats"]
        folder_stat = tracker.stats["folder_stats"]["subdir"]
        assert folder_stat["videos_processed"] == 1
        assert folder_stat["videos_original_size"] == 1000
        assert folder_stat["videos_compressed_size"] == 500
        assert folder_stat["videos_space_saved"] == 500
        assert "mp4" in folder_stat["format_stats"]
        assert folder_stat["format_stats"]["mp4"]["count"] == 1

    def test_update_stats_recursive_image_with_format(self):
        """Test updating stats in recursive mode with image type and format."""
        tracker = StatisticsTracker(recursive=True)

        tracker.update_stats(2000, 1500, 500, "processed", folder_key="subdir", file_type="image", file_extension="jpg")

        assert tracker.stats["images_processed"] == 1
        folder_stat = tracker.stats["folder_stats"]["subdir"]
        assert folder_stat["images_processed"] == 1
        assert folder_stat["images_original_size"] == 2000
        assert folder_stat["images_compressed_size"] == 1500
        assert folder_stat["images_space_saved"] == 500

    def test_update_stats_skipped_video_recursive(self):
        """Test updating stats for skipped video in recursive mode."""
        tracker = StatisticsTracker(recursive=True)

        tracker.update_stats(1000, 1000, 0, "skipped", folder_key="subdir", file_type="video", file_extension="mp4")

        assert tracker.stats["videos_skipped"] == 1
        folder_stat = tracker.stats["folder_stats"]["subdir"]
        assert folder_stat["videos_skipped"] == 1
        assert folder_stat["videos_original_size"] == 1000
        assert folder_stat["videos_compressed_size"] == 1000
        assert "mp4" in folder_stat["format_stats"]
        assert folder_stat["format_stats"]["mp4"]["count"] == 1

    def test_update_stats_skipped_image_recursive(self):
        """Test updating stats for skipped image in recursive mode."""
        tracker = StatisticsTracker(recursive=True)

        tracker.update_stats(2000, 2000, 0, "skipped", folder_key="subdir", file_type="image", file_extension="png")

        assert tracker.stats["images_skipped"] == 1
        folder_stat = tracker.stats["folder_stats"]["subdir"]
        assert folder_stat["images_skipped"] == 1
        assert folder_stat["images_original_size"] == 2000
        assert folder_stat["images_compressed_size"] == 2000

    def test_update_stats_error_video_recursive(self):
        """Test updating stats for video error in recursive mode."""
        tracker = StatisticsTracker(recursive=True)

        tracker.update_stats(1000, 0, 0, "error", folder_key="subdir", file_type="video", file_extension="mp4")

        assert tracker.stats["videos_errors"] == 1
        folder_stat = tracker.stats["folder_stats"]["subdir"]
        assert folder_stat["videos_errors"] == 1

    def test_update_stats_error_image_recursive(self):
        """Test updating stats for image error in recursive mode."""
        tracker = StatisticsTracker(recursive=True)

        tracker.update_stats(2000, 0, 0, "error", folder_key="subdir", file_type="image", file_extension="jpg")

        assert tracker.stats["images_errors"] == 1
        folder_stat = tracker.stats["folder_stats"]["subdir"]
        assert folder_stat["images_errors"] == 1

    def test_add_total_file(self):
        """Test adding total file count."""
        tracker = StatisticsTracker(recursive=False)

        tracker.add_total_file(1000)

        assert tracker.stats["total_files"] == 1
        assert tracker.stats["total_original_size"] == 1000

    def test_add_total_file_recursive(self):
        """Test adding total file in recursive mode."""
        tracker = StatisticsTracker(recursive=True)

        tracker.add_total_file(1000, folder_key="subdir")

        assert tracker.stats["total_files"] == 1
        assert "subdir" in tracker.stats["folder_stats"]
        assert tracker.stats["folder_stats"]["subdir"]["total_files"] == 1

    def test_add_total_file_size_recursive(self):
        """Test add_total_file_size in recursive mode (lines 127-128).

        Note: This should increment folder-level total_files to ensure
        per-folder reports are generated correctly.
        """
        tracker = StatisticsTracker(recursive=True)

        tracker.add_total_file_size(1000, folder_key="subdir")

        assert tracker.stats["total_original_size"] == 1000
        assert tracker.stats["total_files"] == 0  # Should not increment global counter
        assert "subdir" in tracker.stats["folder_stats"]
        assert tracker.stats["folder_stats"]["subdir"]["total_original_size"] == 1000
        assert tracker.stats["folder_stats"]["subdir"]["total_files"] == 1  # Should increment folder counter

    def test_set_total_processing_time(self):
        """Test setting total processing time."""
        tracker = StatisticsTracker(recursive=False)

        tracker.set_total_processing_time(123.45)

        assert tracker.stats["total_processing_time"] == 123.45

    def test_get_stats(self):
        """Test getting statistics."""
        tracker = StatisticsTracker(recursive=False)
        tracker.add_total_file(1000)
        tracker.update_stats(1000, 500, 500, "processed")

        stats = tracker.get_stats()

        assert stats["total_files"] == 1
        assert stats["processed"] == 1
        assert stats["space_saved"] == 500


@pytest.mark.unit
class TestStatisticsManager:
    """Tests for StatisticsManager class."""

    def test_initialization(self, temp_dir):
        """Test StatisticsManager initialization."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        assert manager.statistics_dir == stats_dir
        assert stats_dir.exists()
        assert manager.cumulative_stats_file == stats_dir / "statistics.csv"
        assert manager.run_history_file == stats_dir / "run_history.csv"

    def test_load_cumulative_stats_file_not_exists(self, temp_dir):
        """Test loading cumulative stats when file doesn't exist."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        stats = manager.load_cumulative_stats()

        assert stats["total_runs"] == 0
        assert stats["total_files_processed"] == 0
        assert stats["total_files_skipped"] == 0
        assert stats["total_files_errors"] == 0
        assert stats["total_original_size_bytes"] == 0
        assert stats["total_compressed_size_bytes"] == 0
        assert stats["total_space_saved_bytes"] == 0
        assert stats["last_updated"] is None

    def test_load_cumulative_stats_file_exists(self, temp_dir):
        """Test loading cumulative stats from existing file."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create CSV file with data (old format for backward compatibility)
        with open(manager.cumulative_stats_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "total_runs",
                    "total_files_processed",
                    "total_files_skipped",
                    "total_files_errors",
                    "total_original_size_bytes",
                    "total_compressed_size_bytes",
                    "total_space_saved_bytes",
                    "last_updated",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "total_runs": "5",
                    "total_files_processed": "100",
                    "total_files_skipped": "10",
                    "total_files_errors": "2",
                    "total_original_size_bytes": "1000000",
                    "total_compressed_size_bytes": "500000",
                    "total_space_saved_bytes": "500000",
                    "last_updated": "2024-01-01 12:00:00",
                }
            )

        stats = manager.load_cumulative_stats()

        assert stats["total_runs"] == 5
        assert stats["total_files_processed"] == 100
        assert stats["total_files_skipped"] == 10
        assert stats["total_files_errors"] == 2
        assert stats["total_original_size_bytes"] == 1000000
        assert stats["total_compressed_size_bytes"] == 500000
        assert stats["total_space_saved_bytes"] == 500000
        assert stats["last_updated"] == "2024-01-01 12:00:00"
        # Verify backward compatibility - new fields should default to 0
        assert stats["total_videos_processed"] == 0
        assert stats["total_images_processed"] == 0
        assert stats["format_stats_json"] == "{}"

    def test_load_cumulative_stats_with_invalid_format_json(self, temp_dir):
        """Test loading cumulative stats with invalid format JSON."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create CSV with invalid JSON
        with open(manager.cumulative_stats_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "total_runs",
                    "total_files_processed",
                    "format_stats_json",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "total_runs": "1",
                    "total_files_processed": "10",
                    "format_stats_json": "invalid json {",
                }
            )

        stats = manager.load_cumulative_stats()
        # Should pass through the value as-is (validation happens when used in print_stats)
        assert stats["total_runs"] == 1
        assert stats["format_stats_json"] == "invalid json {"

    def test_load_cumulative_stats_with_empty_format_json(self, temp_dir):
        """Test loading cumulative stats with empty format JSON."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create CSV with empty format_stats_json
        with open(manager.cumulative_stats_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "total_runs",
                    "format_stats_json",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "total_runs": "1",
                    "format_stats_json": "",
                }
            )

        stats = manager.load_cumulative_stats()
        # Empty string is passed through as-is (row.get returns "" if key exists with empty value)
        assert stats["total_runs"] == 1
        assert stats["format_stats_json"] == ""

    def test_load_cumulative_stats_empty_file(self, temp_dir):
        """Test loading cumulative stats from empty file."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create empty CSV file
        manager.cumulative_stats_file.touch()

        stats = manager.load_cumulative_stats()

        # Should return defaults
        assert stats["total_runs"] == 0

    def test_load_cumulative_stats_corrupted_file(self, temp_dir, capsys):
        """Test loading cumulative stats from corrupted file."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create a file that exists so we can trigger an error in the reading
        manager.cumulative_stats_file.touch()

        # Mock csv.DictReader to raise csv.Error when next() is called
        class MockDictReader:
            def __init__(self, *args, **kwargs):
                pass

            def __iter__(self):
                return self

            def __next__(self):
                raise csv.Error("Invalid CSV format")

        # Patch csv.DictReader to raise an error
        with patch("compressy.services.statistics.csv.DictReader", MockDictReader):
            stats = manager.load_cumulative_stats()

        # Should return defaults and print warning
        assert stats["total_runs"] == 0
        output = capsys.readouterr()
        assert "Warning" in output.out

    def test_load_cumulative_stats_unexpected_error(self, temp_dir, capsys):
        """Test loading cumulative stats handles unexpected errors (lines 212-214)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create file
        manager.cumulative_stats_file.touch()

        # Mock open to raise an unexpected exception
        with patch("builtins.open", side_effect=OSError("Unexpected error")):
            stats = manager.load_cumulative_stats()

        # Should return default stats
        assert stats["total_runs"] == 0
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "Unexpected" in captured.out

    def test_update_cumulative_stats(self, temp_dir):
        """Test updating cumulative statistics."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        run_stats = {
            "processed": 10,
            "skipped": 2,
            "errors": 1,
            "total_original_size": 1000000,
            "total_compressed_size": 500000,
            "space_saved": 500000,
        }

        manager.update_cumulative_stats(run_stats)

        # Reload and verify
        stats = manager.load_cumulative_stats()
        assert stats["total_runs"] == 1
        assert stats["total_files_processed"] == 10
        assert stats["total_files_skipped"] == 2
        assert stats["total_files_errors"] == 1
        assert stats["total_original_size_bytes"] == 1000000
        assert stats["total_space_saved_bytes"] == 500000
        assert stats["last_updated"] is not None

    def test_update_cumulative_stats_with_type_and_format(self, temp_dir):
        """Test updating cumulative statistics with type and format tracking."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        run_stats = {
            "processed": 10,
            "skipped": 2,
            "errors": 1,
            "total_original_size": 1000000,
            "total_compressed_size": 500000,
            "space_saved": 500000,
            "videos_processed": 7,
            "images_processed": 3,
            "videos_original_size": 700000,
            "videos_compressed_size": 350000,
            "videos_space_saved": 350000,
            "images_original_size": 300000,
            "images_compressed_size": 150000,
            "images_space_saved": 150000,
            "format_stats": {
                "mp4": {"count": 5, "original_size": 500000, "compressed_size": 250000, "space_saved": 250000},
                "jpg": {"count": 3, "original_size": 300000, "compressed_size": 150000, "space_saved": 150000},
            },
        }

        manager.update_cumulative_stats(run_stats)

        # Reload and verify
        stats = manager.load_cumulative_stats()
        assert stats["total_videos_processed"] == 7
        assert stats["total_images_processed"] == 3
        assert stats["total_videos_original_size_bytes"] == 700000
        assert stats["total_images_original_size_bytes"] == 300000

        import json

        format_stats = json.loads(stats["format_stats_json"])
        assert "mp4" in format_stats
        assert format_stats["mp4"]["count"] == 5
        assert "jpg" in format_stats
        assert format_stats["jpg"]["count"] == 3

    def test_save_cumulative_stats(self, temp_dir):
        """Test saving cumulative statistics."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Use default stats that include all new fields
        stats = manager.load_cumulative_stats()
        stats.update(
            {
                "total_runs": 5,
                "total_files_processed": 100,
                "total_files_skipped": 10,
                "total_files_errors": 2,
                "total_original_size_bytes": 1000000,
                "total_compressed_size_bytes": 500000,
                "total_space_saved_bytes": 500000,
                "last_updated": "2024-01-01 12:00:00",
            }
        )

        manager.save_cumulative_stats(stats)

        # Verify file was created
        assert manager.cumulative_stats_file.exists()

        # Verify content
        loaded_stats = manager.load_cumulative_stats()
        assert loaded_stats["total_runs"] == 5
        assert loaded_stats["total_files_processed"] == 100

    def test_save_cumulative_stats_permission_error(self, temp_dir, capsys):
        """Test saving cumulative stats handles PermissionError (lines 258-261)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        stats = {"total_runs": 10}

        # Mock open to raise PermissionError
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            manager.save_cumulative_stats(stats)

        captured = capsys.readouterr()
        assert "Warning" in captured.out or "Permission" in captured.out

    def test_save_cumulative_stats_general_error(self, temp_dir, capsys):
        """Test saving cumulative stats handles general errors (lines 258-261)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        stats = {"total_runs": 10}

        # Mock open to raise general exception
        with patch("builtins.open", side_effect=IOError("Disk full")):
            manager.save_cumulative_stats(stats)

        captured = capsys.readouterr()
        assert "Warning" in captured.out or "Error" in captured.out

    def test_append_run_history_new_file(self, temp_dir):
        """Test appending run history to new file."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        run_stats = {"processed": 5, "skipped": 1, "errors": 0, "space_saved": 500000}

        cmd_args = {
            "source_folder": "/test/folder",
            "video_crf": 23,
            "image_quality": 80,
            "recursive": False,
            "overwrite": False,
        }

        manager.append_run_history(run_stats, cmd_args)

        # Verify file was created
        assert manager.run_history_file.exists()

        # Verify content
        with open(manager.run_history_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["files_processed"] == "5"
            assert rows[0]["source_folder"] == "/test/folder"

    def test_append_run_history_existing_file(self, temp_dir):
        """Test appending run history to existing file."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Add first run
        manager.append_run_history({"processed": 5}, {"source_folder": "/test1"})

        # Add second run
        manager.append_run_history({"processed": 10}, {"source_folder": "/test2"})

        # Verify both runs are in file
        with open(manager.run_history_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2

    def test_append_run_history_permission_error(self, temp_dir, capsys):
        """Test appending run history handles PermissionError (lines 311-314)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        run_stats = {"processed": 5}
        cmd_args = {"source_folder": "/test"}

        # Mock open to raise PermissionError
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            manager.append_run_history(run_stats, cmd_args)

        captured = capsys.readouterr()
        assert "Warning" in captured.out or "Permission" in captured.out

    def test_append_run_history_general_error(self, temp_dir, capsys):
        """Test appending run history handles general errors (lines 311-314)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        run_stats = {"processed": 5}
        cmd_args = {"source_folder": "/test"}

        # Mock open to raise general exception
        with patch("builtins.open", side_effect=IOError("Disk full")):
            manager.append_run_history(run_stats, cmd_args)

        captured = capsys.readouterr()
        assert "Warning" in captured.out or "Error" in captured.out

    def test_print_stats_no_data(self, temp_dir, capsys):
        """Test printing stats when no data exists."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        manager.print_stats()

        output = capsys.readouterr()
        assert "No Statistics Available" in output.out

    def test_print_stats_with_data(self, temp_dir, capsys):
        """Test printing stats with data."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Add some data
        manager.update_cumulative_stats(
            {
                "processed": 10,
                "skipped": 2,
                "errors": 0,
                "total_original_size": 1000000,
                "total_compressed_size": 500000,
                "space_saved": 500000,
            }
        )

        manager.print_stats()

        output = capsys.readouterr()
        assert "Cumulative Compression Statistics" in output.out
        assert "10" in output.out  # processed files
        assert "Total Runs: 1" in output.out

    def test_print_stats_with_type_breakdown(self, temp_dir, capsys):
        """Test printing stats with type breakdown."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        run_stats = {
            "processed": 10,
            "skipped": 2,
            "errors": 1,
            "total_original_size": 1000000,
            "total_compressed_size": 500000,
            "space_saved": 500000,
            "videos_processed": 7,
            "images_processed": 3,
            "videos_skipped": 1,
            "images_skipped": 1,
            "videos_errors": 1,
            "images_errors": 0,
        }

        manager.update_cumulative_stats(run_stats)
        manager.print_stats()

        output = capsys.readouterr()
        assert "By Type:" in output.out
        assert "Videos:" in output.out
        assert "Images:" in output.out

    def test_print_stats_with_size_by_type(self, temp_dir, capsys):
        """Test printing stats with size breakdown by type."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        run_stats = {
            "processed": 10,
            "videos_processed": 7,
            "images_processed": 3,
            "videos_original_size": 700000,
            "videos_compressed_size": 350000,
            "videos_space_saved": 350000,
            "images_original_size": 300000,
            "images_compressed_size": 150000,
            "images_space_saved": 150000,
        }

        manager.update_cumulative_stats(run_stats)
        manager.print_stats()

        output = capsys.readouterr()
        assert "Size by Type:" in output.out
        assert "Videos:" in output.out
        assert "Images:" in output.out

    def test_print_stats_with_format_breakdown(self, temp_dir, capsys):
        """Test printing stats with format breakdown."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        run_stats = {
            "processed": 10,
            "format_stats": {
                "mp4": {"count": 5, "original_size": 500000, "compressed_size": 250000, "space_saved": 250000},
                "jpg": {"count": 3, "original_size": 300000, "compressed_size": 150000, "space_saved": 150000},
                "png": {"count": 2, "original_size": 200000, "compressed_size": 100000, "space_saved": 100000},
            },
        }

        manager.update_cumulative_stats(run_stats)
        manager.print_stats()

        output = capsys.readouterr()
        assert "By Format:" in output.out
        assert ".MP4:" in output.out
        assert ".JPG:" in output.out
        assert ".PNG:" in output.out

    def test_print_stats_with_empty_format_breakdown(self, temp_dir, capsys):
        """Test printing stats skips format section when all counts are zero."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        run_stats = {
            "processed": 1,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "space_saved": 0,
            "format_stats": {
                "mp4": {"count": 0, "original_size": 0, "compressed_size": 0, "space_saved": 0},
                "jpg": {"count": 0, "original_size": 0, "compressed_size": 0, "space_saved": 0},
            },
        }

        manager.update_cumulative_stats(run_stats)
        manager.print_stats()

        output = capsys.readouterr()
        assert "By Format:" not in output.out

    def test_print_stats_with_invalid_format_json(self, temp_dir, capsys):
        """Test printing stats handles invalid format JSON gracefully."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create stats with invalid JSON
        stats = manager.load_cumulative_stats()
        stats.update(
            {
                "total_runs": 1,
                "total_files_processed": 10,
                "format_stats_json": "invalid json {",
            }
        )
        manager.save_cumulative_stats(stats)

        manager.print_stats()

        output = capsys.readouterr()
        # Should not crash, just skip format display
        assert "Cumulative Compression Statistics" in output.out

    def test_print_stats_with_typeerror_format_json(self, temp_dir, capsys):
        """Test printing stats handles TypeError in JSON parsing gracefully."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create stats with format_stats_json that will cause TypeError
        # (like a non-string value that can't be parsed)
        stats = manager.load_cumulative_stats()
        stats.update(
            {
                "total_runs": 1,
                "total_files_processed": 10,
            }
        )
        manager.save_cumulative_stats(stats)

        # Mock json.loads to raise TypeError
        def mock_loads_raise_typeerror(*args, **kwargs):
            raise TypeError("Invalid type")

        with patch("compressy.services.statistics.json.loads", side_effect=mock_loads_raise_typeerror):
            manager.print_stats()

        output = capsys.readouterr()
        # Should not crash, just skip format display
        assert "Cumulative Compression Statistics" in output.out

    def test_print_stats_only_videos(self, temp_dir, capsys):
        """Test printing stats when only videos are processed."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        run_stats = {
            "processed": 5,
            "videos_processed": 5,
            "images_processed": 0,
            "videos_original_size": 500000,
            "videos_compressed_size": 250000,
            "videos_space_saved": 250000,
            "images_original_size": 0,
        }

        manager.update_cumulative_stats(run_stats)
        manager.print_stats()

        output = capsys.readouterr()
        assert "Videos:" in output.out
        # Should not show Images if count is 0
        output_lines = output.out.split("\n")
        has_images_line = any(
            "Images:" in line and ("processed" in line or "skipped" in line or "errors" in line)
            for line in output_lines
        )
        assert not has_images_line

    def test_print_stats_only_images(self, temp_dir, capsys):
        """Test printing stats when only images are processed."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        run_stats = {
            "processed": 3,
            "videos_processed": 0,
            "images_processed": 3,
            "images_original_size": 300000,
            "images_compressed_size": 150000,
            "images_space_saved": 150000,
            "videos_original_size": 0,
        }

        manager.update_cumulative_stats(run_stats)
        manager.print_stats()

        output = capsys.readouterr()
        assert "Images:" in output.out

    def test_load_run_history_no_file(self, temp_dir):
        """Test loading run history when file doesn't exist."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        history = manager.load_run_history()

        assert history == []

    def test_load_run_history_with_data(self, temp_dir):
        """Test loading run history with data."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Add some history
        manager.append_run_history({"processed": 5}, {"source_folder": "/test1"})
        manager.append_run_history({"processed": 10}, {"source_folder": "/test2"})

        history = manager.load_run_history()

        assert len(history) == 2
        assert history[0]["files_processed"] == "5"
        assert history[1]["files_processed"] == "10"

    def test_load_run_history_general_error(self, temp_dir, capsys):
        """Test loading run history handles general errors (lines 370-372)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create file
        manager.run_history_file.touch()

        # Mock open to raise an exception
        with patch("builtins.open", side_effect=IOError("Read error")):
            history = manager.load_run_history()

        # Should return empty list
        assert history == []
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "Error" in captured.out

    def test_print_history_no_data(self, temp_dir, capsys):
        """Test printing history when no data exists."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        manager.print_history()

        output = capsys.readouterr()
        assert "No Run History Available" in output.out

    def test_print_history_with_limit(self, temp_dir, capsys):
        """Test printing history with limit."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Add multiple runs
        for i in range(5):
            manager.append_run_history({"processed": i}, {"source_folder": f"/test{i}"})

        manager.print_history(limit=2)

        output = capsys.readouterr()
        # Should show 2 of 5 runs
        assert "2 of 5 runs shown" in output.out

    def test_print_history_with_hours(self, temp_dir, capsys):
        """Test print_history with processing time in hours (lines 413-422)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create history file with time > 3600 seconds (1 hour)
        manager.run_history_file.write_text(
            "timestamp,source_folder,files_processed,processing_time_seconds\n"
            "2024-01-01 12:00:00,/test/folder,5,3661.5\n"  # 1 hour 1 minute 1.5 seconds
        )

        manager.print_history()

        captured = capsys.readouterr()
        assert "Processing Time" in captured.out
        assert "1h" in captured.out
        assert "1m" in captured.out

    def test_print_history_with_minutes_only(self, temp_dir, capsys):
        """Test print_history with processing time in minutes only (lines 413-422)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create history file with time between 60 and 3600 seconds
        manager.run_history_file.write_text(
            "timestamp,source_folder,files_processed,processing_time_seconds\n"
            "2024-01-01 12:00:00,/test/folder,5,125.5\n"  # 2 minutes 5.5 seconds
        )

        manager.print_history()

        captured = capsys.readouterr()
        assert "Processing Time" in captured.out
        assert "2m" in captured.out
        assert "5.5s" in captured.out

    def test_print_history_with_seconds_only(self, temp_dir, capsys):
        """Test print_history with processing time in seconds only (lines 413-422)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create history file with time < 60 seconds
        manager.run_history_file.write_text(
            "timestamp,source_folder,files_processed,processing_time_seconds\n"
            "2024-01-01 12:00:00,/test/folder,5,45.7\n"  # 45.7 seconds
        )

        manager.print_history()

        captured = capsys.readouterr()
        assert "Processing Time" in captured.out
        assert "45.7s" in captured.out

    def test_safe_int_conversion_handles_empty_strings(self, temp_dir):
        """Test that safe integer conversion handles empty strings."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create CSV with empty values
        with open(manager.cumulative_stats_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "total_runs",
                    "total_files_processed",
                    "total_files_skipped",
                    "total_files_errors",
                    "total_original_size_bytes",
                    "total_compressed_size_bytes",
                    "total_space_saved_bytes",
                    "last_updated",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "total_runs": "",
                    "total_files_processed": "",
                    "total_files_skipped": "",
                    "total_files_errors": "",
                    "total_original_size_bytes": "",
                    "total_compressed_size_bytes": "",
                    "total_space_saved_bytes": "",
                    "last_updated": "",
                }
            )

        stats = manager.load_cumulative_stats()

        # Should default to 0 for integers
        assert stats["total_runs"] == 0
        assert stats["total_files_processed"] == 0
        assert stats["last_updated"] is None

    def test_safe_int_conversion_handles_value_error(self, temp_dir):
        """Test that _safe_int_conversion handles ValueError (lines 194-195)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create CSV with invalid integer values
        with open(manager.cumulative_stats_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "total_runs",
                    "total_files_processed",
                    "total_files_skipped",
                    "total_files_errors",
                    "total_original_size_bytes",
                    "total_compressed_size_bytes",
                    "total_space_saved_bytes",
                    "last_updated",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "total_runs": "not_a_number",
                    "total_files_processed": "invalid",
                    "total_files_skipped": "0",
                    "total_files_errors": "0",
                    "total_original_size_bytes": "0",
                    "total_compressed_size_bytes": "0",
                    "total_space_saved_bytes": "0",
                    "last_updated": "2024-01-01",
                }
            )

        stats = manager.load_cumulative_stats()

        # Should default to 0 for invalid integers
        assert stats["total_runs"] == 0
        assert stats["total_files_processed"] == 0

    def test_safe_int_conversion_handles_type_error(self, temp_dir):
        """Test that _safe_int_conversion handles TypeError (lines 194-195)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create CSV file, then mock the row to have None values
        manager.cumulative_stats_file.touch()

        # Mock csv.DictReader to return a row with None values
        class MockRow:
            def get(self, key, default=None):
                if key in ["total_runs", "total_files_processed"]:
                    return None  # This will cause TypeError when trying int(None)
                return "0"

        with patch("compressy.services.statistics.csv.DictReader") as mock_reader:
            mock_reader.return_value = [MockRow()]
            stats = manager.load_cumulative_stats()

        # Should default to 0 for None values
        assert stats["total_runs"] == 0
        assert stats["total_files_processed"] == 0
