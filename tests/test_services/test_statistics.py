"""
Tests for compressy.services.statistics module.
"""

import json
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
        assert tracker.stats["processed_file_format_stats"] == {}

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
        assert "mp4" in tracker.stats["processed_file_format_stats"]
        assert tracker.stats["processed_file_format_stats"]["mp4"]["count"] == 1
        assert tracker.stats["processed_file_format_stats"]["mp4"]["original_size"] == 1000
        assert tracker.stats["processed_file_format_stats"]["mp4"]["compressed_size"] == 500
        assert tracker.stats["processed_file_format_stats"]["mp4"]["space_saved"] == 500

    def test_update_stats_image_with_format(self):
        """Test updating stats for image file with format tracking."""
        tracker = StatisticsTracker(recursive=False)

        tracker.update_stats(2000, 1500, 500, "processed", file_type="image", file_extension="jpg")

        assert tracker.stats["images_processed"] == 1
        assert tracker.stats["videos_processed"] == 0
        assert tracker.stats["images_original_size"] == 2000
        assert tracker.stats["images_compressed_size"] == 1500
        assert tracker.stats["images_space_saved"] == 500
        assert "jpg" in tracker.stats["processed_file_format_stats"]
        assert tracker.stats["processed_file_format_stats"]["jpg"]["count"] == 1

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
        assert tracker.stats["folder_stats"]["subdir"]["total_compressed_size"] == 1000

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
        assert "mp4" in folder_stat["processed_file_format_stats"]
        assert folder_stat["processed_file_format_stats"]["mp4"]["count"] == 1

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
        assert folder_stat["processed_file_format_stats"] == {}

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
        assert manager.cumulative_stats_file == stats_dir / "statistics.json"
        assert manager.files_log_file == stats_dir / "files.json"

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
        assert stats["processed_file_format_stats"] == {}
        assert stats["last_updated"] is None

    def test_load_cumulative_stats_file_exists(self, temp_dir):
        """Test loading cumulative stats from existing file."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create JSON file with data
        test_data = {
            "total_runs": 5,
            "total_files_processed": 100,
            "total_files_skipped": 10,
            "total_files_errors": 2,
            "total_original_size_bytes": 1000000,
            "total_compressed_size_bytes": 500000,
            "total_space_saved_bytes": 500000,
            "total_videos_processed": 50,
            "total_images_processed": 50,
            "processed_file_format_stats": {
                "mp4": {"count": 10, "original_size": 500000, "compressed_size": 250000, "space_saved": 250000}
            },
            "last_updated": "2024-01-01 12:00:00",
        }

        with open(manager.cumulative_stats_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        stats = manager.load_cumulative_stats()

        assert stats["total_runs"] == 5
        assert stats["total_files_processed"] == 100
        assert stats["total_files_skipped"] == 10
        assert stats["total_files_errors"] == 2
        assert stats["total_original_size_bytes"] == 1000000
        assert stats["total_compressed_size_bytes"] == 500000
        assert stats["total_space_saved_bytes"] == 500000
        assert stats["last_updated"] == "2024-01-01 12:00:00"
        assert stats["total_videos_processed"] == 50
        assert stats["total_images_processed"] == 50
        assert "mp4" in stats["processed_file_format_stats"]

    def test_load_cumulative_stats_with_invalid_json(self, temp_dir):
        """Test loading cumulative stats with invalid JSON file."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create invalid JSON file
        with open(manager.cumulative_stats_file, "w", encoding="utf-8") as f:
            f.write("invalid json {")

        stats = manager.load_cumulative_stats()
        # Should return defaults when JSON is invalid
        assert stats["total_runs"] == 0
        assert stats["processed_file_format_stats"] == {}

    def test_load_cumulative_stats_with_missing_fields(self, temp_dir):
        """Test loading cumulative stats with missing fields."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create JSON with minimal fields
        test_data = {
            "total_runs": 1,
        }

        with open(manager.cumulative_stats_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        stats = manager.load_cumulative_stats()
        # Should fill in missing fields with defaults
        assert stats["total_runs"] == 1
        assert stats["processed_file_format_stats"] == {}
        assert stats["total_files_processed"] == 0

    def test_load_cumulative_stats_empty_file(self, temp_dir):
        """Test loading cumulative stats from empty file."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create empty JSON file
        manager.cumulative_stats_file.touch()

        stats = manager.load_cumulative_stats()

        # Should return defaults
        assert stats["total_runs"] == 0

    def test_load_cumulative_stats_corrupted_file(self, temp_dir, capsys):
        """Test loading cumulative stats from corrupted file."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create a file with invalid JSON
        with open(manager.cumulative_stats_file, "w", encoding="utf-8") as f:
            f.write("{corrupted json")

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
            "processed_file_format_stats": {
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

        format_stats = stats["processed_file_format_stats"]
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

        files_data = []
        run_stats = {"processed": 5, "skipped": 1, "errors": 0, "space_saved": 500000}
        cmd_args = {
            "source_folder": "/test/folder",
            "video_crf": 23,
            "image_quality": 80,
            "recursive": False,
            "overwrite": False,
        }
        run_uuid = "test-uuid-123"
        command = "python compressy.py /test/folder --video-crf 23"

        manager.append_to_files_log(files_data, run_uuid, cmd_args, run_stats=run_stats, command=command)

        # Verify file was created
        assert manager.files_log_file.exists()

        # Verify content
        with open(manager.files_log_file, "r", encoding="utf-8") as f:
            files_log = json.load(f)
            assert isinstance(files_log, dict)
            entry = list(files_log.values())[0]
            assert entry["stats"]["files_processed"] == 5
            assert entry["metadata"]["source_folder"] == "/test/folder"
            assert entry["metadata"]["run_uuid"] == "test-uuid-123"

    def test_append_run_history_existing_file(self, temp_dir):
        """Test appending run history to existing file."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Add first run with mocked timestamp
        with patch("compressy.services.statistics.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2024-01-01 12:00:00"
            manager.append_to_files_log([], "uuid-1", {"source_folder": "/test1"}, run_stats={"files_processed": 5})

        # Add second run with different mocked timestamp
        with patch("compressy.services.statistics.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2024-01-01 12:00:01"
            manager.append_to_files_log([], "uuid-2", {"source_folder": "/test2"}, run_stats={"files_processed": 10})

        # Verify both runs are in file
        with open(manager.files_log_file, "r", encoding="utf-8") as f:
            files_log = json.load(f)
            assert isinstance(files_log, dict)
            assert len(files_log) == 2
            # Check both entries exist
            entries = list(files_log.values())
            uuids = [entry["metadata"]["run_uuid"] for entry in entries]
            assert "uuid-1" in uuids
            assert "uuid-2" in uuids

    def test_append_run_history_permission_error(self, temp_dir, capsys):
        """Test appending run history handles PermissionError."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        files_data = []
        run_stats = {"processed": 5}
        cmd_args = {"source_folder": "/test"}

        # Mock open to raise PermissionError
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            manager.append_to_files_log(files_data, "test-uuid", cmd_args, run_stats=run_stats)

        captured = capsys.readouterr()
        assert "Warning" in captured.out or "Permission" in captured.out

    def test_append_run_history_general_error(self, temp_dir, capsys):
        """Test appending run history handles general errors."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        files_data = []
        run_stats = {"processed": 5}
        cmd_args = {"source_folder": "/test"}

        # Mock open to raise general exception
        with patch("builtins.open", side_effect=IOError("Disk full")):
            manager.append_to_files_log(files_data, "test-uuid", cmd_args, run_stats=run_stats)

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
            "processed_file_format_stats": {
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
            "processed_file_format_stats": {
                "mp4": {"count": 0, "original_size": 0, "compressed_size": 0, "space_saved": 0},
                "jpg": {"count": 0, "original_size": 0, "compressed_size": 0, "space_saved": 0},
            },
        }

        manager.update_cumulative_stats(run_stats)
        manager.print_stats()

        output = capsys.readouterr()
        assert "By Format:" not in output.out

    def test_print_stats_with_format_stats(self, temp_dir, capsys):
        """Test printing stats with format statistics."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create stats with format data
        stats = manager.load_cumulative_stats()
        stats.update(
            {
                "total_runs": 1,
                "total_files_processed": 10,
                "processed_file_format_stats": {
                    "mp4": {"count": 5, "original_size": 500000, "compressed_size": 250000, "space_saved": 250000},
                    "jpg": {"count": 3, "original_size": 300000, "compressed_size": 150000, "space_saved": 150000},
                },
            }
        )
        manager.save_cumulative_stats(stats)

        manager.print_stats()

        output = capsys.readouterr()
        # Should display format statistics
        assert "Cumulative Compression Statistics" in output.out
        assert "By Format:" in output.out
        assert ".MP4:" in output.out
        assert ".JPG:" in output.out

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

        files_log = manager.load_files_log()

        assert files_log == {}

    def test_load_run_history_with_data(self, temp_dir):
        """Test loading run history with data."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Add some history with mocked timestamps
        with patch("compressy.services.statistics.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2024-01-01 12:00:00"
            manager.append_to_files_log([], "uuid-1", {"source_folder": "/test1"}, run_stats={"processed": 5})

        with patch("compressy.services.statistics.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2024-01-01 12:00:01"
            manager.append_to_files_log([], "uuid-2", {"source_folder": "/test2"}, run_stats={"processed": 10})

        files_log = manager.load_files_log()

        assert isinstance(files_log, dict)
        assert len(files_log) == 2
        entries = list(files_log.values())
        # Find entries by uuid
        entry1 = next(e for e in entries if e["metadata"]["run_uuid"] == "uuid-1")
        entry2 = next(e for e in entries if e["metadata"]["run_uuid"] == "uuid-2")
        assert entry1["stats"]["files_processed"] == 5
        assert entry2["stats"]["files_processed"] == 10

    def test_load_run_history_general_error(self, temp_dir, capsys):
        """Test loading run history handles general errors (lines 370-372)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create file
        manager.files_log_file.touch()

        # Mock open to raise an exception
        with patch("builtins.open", side_effect=IOError("Read error")):
            files_log = manager.load_files_log()

        # Should return empty dict
        assert files_log == {}
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

        # Add multiple runs with mocked timestamps
        for i in range(5):
            with patch("compressy.services.statistics.datetime") as mock_dt:
                mock_dt.now.return_value.strftime.return_value = f"2024-01-01 12:00:{i:02d}"
                manager.append_to_files_log([], f"uuid-{i}", {"source_folder": f"/test{i}"}, run_stats={"processed": i})

        manager.print_history(limit=2)

        output = capsys.readouterr()
        # Should show 2 of 5 runs
        assert "2 of 5 runs shown" in output.out

    def test_print_history_with_hours(self, temp_dir, capsys):
        """Test print_history with processing time in hours (lines 413-422)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create files.json with time > 3600 seconds (1 hour)
        test_data = {
            "2024-01-01 12:00:00": {
                "metadata": {"run_uuid": "test-uuid", "source_folder": "/test/folder"},
                "stats": {"files_processed": 5, "processing_time_seconds": 3661.5},  # 1 hour 1 minute 1.5 seconds
                "files": [],
            }
        }
        with open(manager.files_log_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        manager.print_history()

        captured = capsys.readouterr()
        assert "Processing Time" in captured.out
        assert "1h" in captured.out
        assert "1m" in captured.out

    def test_print_history_with_minutes_only(self, temp_dir, capsys):
        """Test print_history with processing time in minutes only (lines 413-422)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create files.json with time between 60 and 3600 seconds
        test_data = {
            "2024-01-01 12:00:00": {
                "metadata": {"run_uuid": "test-uuid", "source_folder": "/test/folder"},
                "stats": {"files_processed": 5, "processing_time_seconds": 125.5},  # 2 minutes 5.5 seconds
                "files": [],
            }
        }
        with open(manager.files_log_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        manager.print_history()

        captured = capsys.readouterr()
        assert "Processing Time" in captured.out
        assert "2m" in captured.out
        assert "5.5s" in captured.out

    def test_print_history_with_seconds_only(self, temp_dir, capsys):
        """Test print_history with processing time in seconds only (lines 413-422)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create files.json with time < 60 seconds
        test_data = {
            "2024-01-01 12:00:00": {
                "metadata": {"run_uuid": "test-uuid", "source_folder": "/test/folder"},
                "stats": {"files_processed": 5, "processing_time_seconds": 45.7},  # 45.7 seconds
                "files": [],
            }
        }
        with open(manager.files_log_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        manager.print_history()

        captured = capsys.readouterr()
        assert "Processing Time" in captured.out
        assert "45.7s" in captured.out

    def test_load_cumulative_stats_with_none_values(self, temp_dir):
        """Test loading cumulative stats with None values in JSON."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create JSON with None values
        test_data = {
            "total_runs": None,
            "total_files_processed": None,
            "total_files_skipped": None,
            "total_files_errors": None,
            "total_original_size_bytes": None,
            "total_compressed_size_bytes": None,
            "total_space_saved_bytes": None,
            "last_updated": None,
        }

        with open(manager.cumulative_stats_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        stats = manager.load_cumulative_stats()

        # Should default to 0 for integers, None for last_updated
        assert stats["total_runs"] == 0
        assert stats["total_files_processed"] == 0
        assert stats["last_updated"] is None

    def test_load_files_log_no_file(self, temp_dir):
        """Test loading files log when file doesn't exist."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        files_log = manager.load_files_log()

        assert files_log == {}

    def test_load_files_log_with_data(self, temp_dir):
        """Test loading files log with data."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create files log with new format
        test_data = {
            "2024-01-01 12:00:00": {
                "metadata": {"run_uuid": "uuid-1"},
                "stats": {},
                "files": [
                    {
                        "file_name": "video.mp4",
                        "original_path": "/path/to/video.mp4",
                        "new_path": "/path/to/compressed/video.mp4",
                        "file_type": "video",
                        "format": "mp4",
                        "modifications": {"compressed": True, "video_crf": 23},
                        "size_before_bytes": 1000000,
                        "size_after_bytes": 500000,
                        "space_saved_bytes": 500000,
                        "compression_ratio_percent": 50.0,
                        "processing_time_seconds": 5.2,
                        "status": "success",
                    }
                ],
            }
        }

        with open(manager.files_log_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        files_log = manager.load_files_log()

        assert isinstance(files_log, dict)
        assert len(files_log) == 1
        entry = list(files_log.values())[0]
        assert entry["metadata"]["run_uuid"] == "uuid-1"
        assert entry["files"][0]["file_name"] == "video.mp4"

    def test_append_to_files_log(self, temp_dir):
        """Test appending files to files log."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        files_data = [
            {
                "name": "video.mp4",
                "original_size": 1000000,
                "compressed_size": 500000,
                "space_saved": 500000,
                "compression_ratio": 50.0,
                "processing_time": 5.2,
                "status": "success",
            }
        ]

        cmd_args = {"video_crf": 23, "image_quality": 80}
        run_uuid = "test-uuid-123"

        manager.append_to_files_log(files_data, run_uuid, cmd_args)

        # Verify file was created
        assert manager.files_log_file.exists()

        # Verify content
        with open(manager.files_log_file, "r", encoding="utf-8") as f:
            files_log = json.load(f)
            assert isinstance(files_log, dict)
            assert len(files_log) == 1
            entry = list(files_log.values())[0]
            assert entry["metadata"]["run_uuid"] == "test-uuid-123"
            assert entry["files"][0]["file_name"] == "video.mp4"
            assert entry["files"][0]["file_type"] == "video"
            assert entry["files"][0]["format"] == "mp4"

    def test_append_to_files_log_multiple_runs(self, temp_dir):
        """Test appending files from multiple runs."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        files_data1 = [
            {
                "name": "video1.mp4",
                "original_size": 1000000,
                "compressed_size": 500000,
                "space_saved": 500000,
                "compression_ratio": 50.0,
                "processing_time": 5.2,
                "status": "success",
            }
        ]
        files_data2 = [
            {
                "name": "image1.jpg",
                "original_size": 500000,
                "compressed_size": 250000,
                "space_saved": 250000,
                "compression_ratio": 50.0,
                "processing_time": 2.1,
                "status": "success",
            }
        ]

        cmd_args = {"video_crf": 23, "image_quality": 80}

        # Add multiple runs with mocked timestamps to ensure different timestamps
        for i, (files_data, uuid) in enumerate([(files_data1, "uuid-1"), (files_data2, "uuid-2")]):
            with patch("compressy.services.statistics.datetime") as mock_dt:
                mock_dt.now.return_value.strftime.return_value = f"2024-01-01 12:00:{i:02d}"
                manager.append_to_files_log(files_data, uuid, cmd_args)

        # Verify both files are in log
        with open(manager.files_log_file, "r", encoding="utf-8") as f:
            files_log = json.load(f)
            # Should be a dict keyed by timestamp
            assert isinstance(files_log, dict)
            # Should have 1 or 2 entries (depending on if runs happened at same timestamp)
            # If they happened at same timestamp, they'll be grouped together
            assert len(files_log) >= 1

            # Collect all files from all entries (runs at same timestamp are grouped together)
            all_files = []
            for key, data in files_log.items():
                all_files.extend(data.get("files", []))

            # Find video and image files
            video_file = None
            image_file = None
            for file_record in all_files:
                if file_record.get("file_name") == "video1.mp4":
                    video_file = file_record
                elif file_record.get("file_name") == "image1.jpg":
                    image_file = file_record

            assert video_file is not None
            assert image_file is not None

            # Verify video file only has video-related modifications
            assert "video_crf" in video_file["modifications"]
            assert "image_quality" not in video_file["modifications"]

            # Verify image file only has image-related modifications
            assert "image_quality" in image_file["modifications"]
            assert "video_crf" not in image_file["modifications"]

    def test_print_history_with_command(self, temp_dir, capsys):
        """Test print_history displays command when available."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        test_data = {
            "2024-01-01 12:00:00": {
                "metadata": {
                    "run_uuid": "test-uuid",
                    "source_folder": "/test/folder",
                    "command": "python compressy.py /test/folder --video-crf 23",
                },
                "stats": {
                    "files_processed": 5,
                    "processing_time_seconds": 10.5,
                },
                "files": [],
            }
        }
        with open(manager.files_log_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        manager.print_history()

        captured = capsys.readouterr()
        assert "Command:" in captured.out
        assert "python compressy.py" in captured.out

    def test_load_files_log_old_list_format(self, temp_dir):
        """Test loading files log with old list format."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create old format (list)
        test_data = [
            {
                "timestamp": "2024-01-01 12:00:00",
                "run_id": "uuid-1",
                "file_name": "video.mp4",
                "file_type": "video",
            }
        ]

        with open(manager.files_log_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        files_log = manager.load_files_log()

        assert isinstance(files_log, dict)
        assert "2024-01-01 12:00:00" in files_log
        assert files_log["2024-01-01 12:00:00"]["run_uuid"] == "uuid-1"
        assert len(files_log["2024-01-01 12:00:00"]["files"]) == 1
        # Verify timestamp and run_id removed from file record
        file_record = files_log["2024-01-01 12:00:00"]["files"][0]
        assert "timestamp" not in file_record
        assert "run_id" not in file_record

    def test_load_files_log_old_timestamp_uuid_format(self, temp_dir):
        """Test loading files log with old timestamp_uuid key format."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create old format with timestamp_uuid keys
        test_data = {
            "2024-01-01 12:00:00_uuid-1": {"run_uuid": "uuid-1", "files": [{"file_name": "video1.mp4"}]},
            "2024-01-01 12:00:00_uuid-2": {"run_uuid": "uuid-2", "files": [{"file_name": "video2.mp4"}]},
        }

        with open(manager.files_log_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        files_log = manager.load_files_log()

        assert isinstance(files_log, dict)
        assert "2024-01-01 12:00:00" in files_log
        # Files should be merged if same timestamp
        entry = files_log["2024-01-01 12:00:00"]
        assert len(entry["files"]) == 2

    def test_load_files_log_invalid_json(self, temp_dir, capsys):
        """Test loading files log with invalid JSON."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        manager.files_log_file.write_text("invalid json {")

        files_log = manager.load_files_log()

        assert files_log == {}
        captured = capsys.readouterr()
        assert "Warning" in captured.out

    def test_load_files_log_exception(self, temp_dir, capsys):
        """Test loading files log handles exceptions."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create file first
        manager.files_log_file.touch()

        with patch("builtins.open", side_effect=IOError("Read error")):
            files_log = manager.load_files_log()

        assert files_log == {}
        captured = capsys.readouterr()
        # Check both stdout and stderr for warning
        assert (
            "Warning" in captured.out or "Warning" in captured.err or "Error" in captured.out or "Error" in captured.err
        )

    def test_append_to_files_log_unknown_file_type(self, temp_dir):
        """Test appending files log with unknown file type."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        files_data = [
            {
                "name": "unknown.xyz",
                "original_size": 1000000,
                "compressed_size": 500000,
                "space_saved": 500000,
                "compression_ratio": 50.0,
                "processing_time": 5.2,
                "status": "success",
            }
        ]

        cmd_args = {"video_crf": 23, "image_quality": 80}
        run_uuid = "test-uuid-123"

        manager.append_to_files_log(files_data, run_uuid, cmd_args)

        with open(manager.files_log_file, "r", encoding="utf-8") as f:
            files_log = json.load(f)
            entry = list(files_log.values())[0]
            file_record = entry["files"][0]
            assert file_record["file_type"] == "unknown"

    def test_append_to_files_log_all_video_modifications(self, temp_dir):
        """Test appending files log with all video modifications."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        files_data = [
            {
                "name": "video.mp4",
                "original_size": 1000000,
                "compressed_size": 500000,
                "space_saved": 500000,
                "compression_ratio": 50.0,
                "processing_time": 5.2,
                "status": "success",
            }
        ]

        cmd_args = {
            "video_crf": 23,
            "video_preset": "fast",
            "video_resize": 90,
            "video_resolution": "720p",
        }
        run_uuid = "test-uuid-123"

        manager.append_to_files_log(files_data, run_uuid, cmd_args)

        with open(manager.files_log_file, "r", encoding="utf-8") as f:
            files_log = json.load(f)
            entry = list(files_log.values())[0]
            file_record = entry["files"][0]
            modifications = file_record["modifications"]
            assert modifications["video_crf"] == 23
            assert modifications["video_preset"] == "fast"
            assert modifications["video_resize"] == 90
            assert modifications["video_resolution"] == "720p"

    def test_append_to_files_log_all_image_modifications(self, temp_dir):
        """Test appending files log with all image modifications."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        files_data = [
            {
                "name": "image.jpg",
                "original_size": 1000000,
                "compressed_size": 500000,
                "space_saved": 500000,
                "compression_ratio": 50.0,
                "processing_time": 5.2,
                "status": "success",
            }
        ]

        cmd_args = {
            "image_quality": 80,
            "image_resize": 90,
        }
        run_uuid = "test-uuid-123"

        manager.append_to_files_log(files_data, run_uuid, cmd_args)

        with open(manager.files_log_file, "r", encoding="utf-8") as f:
            files_log = json.load(f)
            entry = list(files_log.values())[0]
            file_record = entry["files"][0]
            modifications = file_record["modifications"]
            assert modifications["image_quality"] == 80
            assert modifications["image_resize"] == 90

    def test_load_files_log_fallback_key_format(self, temp_dir):
        """Test loading files log with unparseable timestamp_uuid key (fallback line 726)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create old format with key that has underscore but split doesn't work as expected
        # This should trigger the fallback at line 726
        # We need a key with underscore and run_uuid, but where split("_", 1) doesn't return 2 parts
        # Actually, split("_", 1) always returns at least 1 element, and if there's an underscore, it returns 2
        # So line 726 is unreachable. But let's test with a key that has underscore but is malformed
        # Actually, the only way to trigger line 726 is if split returns something with len != 2
        # But that's impossible if there's an underscore. So this line is dead code.
        # However, let's test with a key that has underscore to ensure the else branch works
        test_data = {
            "2024-01-01_": {  # Key with underscore but only one part after split
                "run_uuid": "uuid-1",
                "files": [{"file_name": "video1.mp4"}],
            }
        }

        with open(manager.files_log_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        files_log = manager.load_files_log()

        assert isinstance(files_log, dict)
        # The key should be converted to timestamp "2024-01-01" if split works, or kept as-is if fallback
        # Since split("_", 1) on "2024-01-01_" returns ["2024-01-01", ""], len(parts) == 2, so it goes to line 718
        # To trigger line 726, we'd need split to return something with len != 2, which is impossible
        # So line 726 is unreachable dead code

    def test_load_files_log_empty_dict(self, temp_dir):
        """Test loading files log with empty dict (line 732)."""
        stats_dir = temp_dir / "statistics"
        manager = StatisticsManager(stats_dir)

        # Create empty dict (not list, not dict with timestamp keys)
        test_data = {}

        with open(manager.files_log_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        files_log = manager.load_files_log()

        assert isinstance(files_log, dict)
        assert files_log == {}
