"""
Tests for compressy.services.reports module.
"""

from unittest.mock import patch

import pytest

from compressy.services.reports import ReportGenerator


@pytest.mark.unit
class TestReportGenerator:
    """Tests for ReportGenerator class."""

    def test_initialization(self, temp_dir):
        """Test ReportGenerator initialization."""
        generator = ReportGenerator(temp_dir)

        assert generator.output_dir == temp_dir

    def test_generate_single_report_non_recursive(self, temp_dir):
        """Test generating single report for non-recursive mode."""
        generator = ReportGenerator(temp_dir)

        stats = {
            "total_files": 5,
            "processed": 4,
            "skipped": 1,
            "errors": 0,
            "total_original_size": 1000000,
            "total_compressed_size": 500000,
            "space_saved": 500000,
            "files": [],
        }

        report_paths = generator.generate(stats, "test_folder", recursive=False)

        assert len(report_paths) == 1
        assert report_paths[0].exists()
        assert "test_folder" in report_paths[0].name

    def test_generate_multiple_reports_recursive(self, temp_dir):
        """Test generating multiple reports for recursive mode."""
        generator = ReportGenerator(temp_dir)

        stats = {
            "total_files": 10,
            "processed": 8,
            "skipped": 2,
            "errors": 0,
            "total_original_size": 2000000,
            "total_compressed_size": 1000000,
            "space_saved": 1000000,
            "folder_stats": {
                "subdir1": {
                    "total_files": 5,
                    "processed": 4,
                    "skipped": 1,
                    "errors": 0,
                    "total_original_size": 1000000,
                    "total_compressed_size": 500000,
                    "space_saved": 500000,
                    "files": [],
                },
                "subdir2": {
                    "total_files": 5,
                    "processed": 4,
                    "skipped": 1,
                    "errors": 0,
                    "total_original_size": 1000000,
                    "total_compressed_size": 500000,
                    "space_saved": 500000,
                    "files": [],
                },
            },
            "files": [],
        }

        report_paths = generator.generate(stats, "test_folder", recursive=True)

        # Should have reports for each subfolder + aggregated report
        assert len(report_paths) >= 2

    def test_get_unique_path_no_conflict(self, temp_dir):
        """Test getting unique path when file doesn't exist."""
        generator = ReportGenerator(temp_dir)
        base_path = temp_dir / "test_report.csv"

        unique_path = generator._get_unique_path(base_path)

        assert unique_path == base_path

    def test_get_unique_path_with_conflict(self, temp_dir):
        """Test getting unique path when file exists (appends number)."""
        generator = ReportGenerator(temp_dir)
        base_path = temp_dir / "test_report.csv"
        base_path.touch()

        unique_path = generator._get_unique_path(base_path)

        assert unique_path != base_path
        assert unique_path.name == "test_report (1).csv"

    def test_get_unique_path_multiple_conflicts(self, temp_dir):
        """Test getting unique path with multiple existing files."""
        generator = ReportGenerator(temp_dir)
        base_path = temp_dir / "test_report.csv"
        (temp_dir / "test_report.csv").touch()
        (temp_dir / "test_report (1).csv").touch()
        (temp_dir / "test_report (2).csv").touch()

        unique_path = generator._get_unique_path(base_path)

        assert unique_path.name == "test_report (3).csv"

    def test_write_csv_report_contains_summary(self, temp_dir):
        """Test that CSV report contains summary section."""
        generator = ReportGenerator(temp_dir)
        report_path = temp_dir / "test_report.csv"

        stats = {
            "total_files": 5,
            "processed": 4,
            "skipped": 1,
            "errors": 0,
            "total_original_size": 1000000,
            "total_compressed_size": 500000,
            "space_saved": 500000,
            "files": [],
        }

        generator._write_csv_report(report_path, stats, "Test Report")

        assert report_path.exists()
        content = report_path.read_text()
        assert "Compression Report: Test Report" in content
        assert "Total Files Found" in content
        assert "Files Processed" in content

    def test_write_csv_report_contains_file_details(self, temp_dir):
        """Test that CSV report contains file details."""
        generator = ReportGenerator(temp_dir)
        report_path = temp_dir / "test_report.csv"

        stats = {
            "total_files": 2,
            "processed": 2,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000000,
            "total_compressed_size": 500000,
            "space_saved": 500000,
            "files": [
                {
                    "name": "test1.mp4",
                    "original_size": 500000,
                    "compressed_size": 250000,
                    "space_saved": 250000,
                    "compression_ratio": 50.0,
                    "processing_time": 1.5,
                    "status": "success",
                }
            ],
        }

        generator._write_csv_report(report_path, stats, "Test Report")

        content = report_path.read_text()
        assert "File Details" in content
        assert "test1.mp4" in content
        assert "Filename" in content

    def test_write_csv_report_contains_arguments(self, temp_dir):
        """Test that CSV report contains command arguments."""
        generator = ReportGenerator(temp_dir)
        report_path = temp_dir / "test_report.csv"

        stats = {
            "total_files": 0,
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "space_saved": 0,
            "files": [],
        }

        cmd_args = {
            "source_folder": "/test/folder",
            "video_crf": 23,
            "image_quality": 80,
            "recursive": True,
            "overwrite": False,
        }

        generator._write_csv_report(report_path, stats, "Test Report", cmd_args=cmd_args)

        content = report_path.read_text()
        assert "Arguments" in content
        assert "Source Folder" in content
        assert "/test/folder" in content

    def test_generate_handles_empty_folder_stats(self, temp_dir):
        """Test that generate handles empty folder_stats gracefully."""
        generator = ReportGenerator(temp_dir)

        stats = {
            "total_files": 0,
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "space_saved": 0,
            "folder_stats": {},
            "files": [],
        }

        report_paths = generator.generate(stats, "test_folder", recursive=True)

        # Should still generate a report (aggregated)
        assert len(report_paths) >= 1

    def test_generate_skips_empty_folders(self, temp_dir):
        """Test that generate skips folders with total_files == 0 (line 65)."""
        generator = ReportGenerator(temp_dir)

        stats = {
            "total_files": 5,
            "processed": 5,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000000,
            "total_compressed_size": 500000,
            "space_saved": 500000,
            "folder_stats": {
                "subfolder1": {
                    "total_files": 5,
                    "processed": 5,
                    "skipped": 0,
                    "errors": 0,
                    "total_original_size": 1000000,
                    "total_compressed_size": 500000,
                    "space_saved": 500000,
                    "files": [],
                },
                "empty_folder": {
                    "total_files": 0,  # Should be skipped (line 65)
                    "processed": 0,
                    "skipped": 0,
                    "errors": 0,
                    "total_original_size": 0,
                    "total_compressed_size": 0,
                    "space_saved": 0,
                    "files": [],
                },
            },
            "files": [],
        }

        report_paths = generator.generate(stats, "test_folder", recursive=True)

        # Should generate report for subfolder1 but not empty_folder
        assert len(report_paths) >= 1
        # Verify no report for empty_folder
        report_names = [p.name for p in report_paths]
        assert not any("empty_folder" in name for name in report_names)
        assert any("subfolder1" in name for name in report_names)

    def test_generate_handles_empty_folder_safe_name(self, temp_dir):
        """Test that generate handles empty or '.' folder_safe_name (line 71)."""
        generator = ReportGenerator(temp_dir)

        stats = {
            "total_files": 5,
            "processed": 5,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000000,
            "total_compressed_size": 500000,
            "space_saved": 500000,
            "folder_stats": {
                ".": {  # Should become "root"
                    "total_files": 5,
                    "processed": 5,
                    "skipped": 0,
                    "errors": 0,
                    "total_original_size": 1000000,
                    "total_compressed_size": 500000,
                    "space_saved": 500000,
                    "files": [],
                }
            },
            "files": [],
        }

        report_paths = generator.generate(stats, "test_folder", recursive=True)

        # Should generate report with "root" in name
        assert len(report_paths) >= 1
        report_names = [p.name for p in report_paths]
        assert any("root" in name for name in report_names)

    def test_get_unique_path_no_pattern_match(self, temp_dir):
        """Test _get_unique_path with base name that doesn't match pattern (line 137)."""
        generator = ReportGenerator(temp_dir)
        base_path = temp_dir / "report.csv"

        # Create the file so the code reaches the re.match section
        base_path.touch()

        # Patch re.match to return None to test the else branch (line 137)
        with patch("compressy.services.reports.re.match", return_value=None):
            unique_path = generator._get_unique_path(base_path)

        # Should still return a path (line 137 sets base_name_only = base_name)
        assert unique_path is not None
        # Should return a unique path with (1) since base_path exists
        assert unique_path != base_path
        assert "(1)" in str(unique_path)

    def test_write_csv_report_handles_existing_report(self, temp_dir, capsys):
        """Test that _write_csv_report handles existing report (line 165)."""
        generator = ReportGenerator(temp_dir)
        report_path = temp_dir / "test_report.csv"
        report_path.touch()  # Create existing report

        stats = {
            "total_files": 5,
            "processed": 4,
            "skipped": 1,
            "errors": 0,
            "total_original_size": 1000000,
            "total_compressed_size": 500000,
            "space_saved": 500000,
            "files": [],
        }

        generator._write_csv_report(report_path, stats, "Test Report")

        # Should print message about existing report
        captured = capsys.readouterr()
        assert "Report already exists" in captured.out or "creating:" in captured.out

    def test_write_csv_report_processing_time_hours(self, temp_dir):
        """Test _write_csv_report with processing time in hours (lines 196-205)."""
        generator = ReportGenerator(temp_dir)
        report_path = temp_dir / "test_report.csv"

        stats = {
            "total_files": 5,
            "processed": 4,
            "skipped": 1,
            "errors": 0,
            "total_original_size": 1000000,
            "total_compressed_size": 500000,
            "space_saved": 500000,
            "total_processing_time": 3661.5,  # 1 hour 1 minute 1.5 seconds
            "files": [],
        }

        generator._write_csv_report(report_path, stats, "Test Report")

        content = report_path.read_text()
        assert "Total Processing Time" in content
        assert "1h" in content
        assert "1m" in content

    def test_write_csv_report_processing_time_minutes(self, temp_dir):
        """Test _write_csv_report with processing time in minutes only."""
        generator = ReportGenerator(temp_dir)
        report_path = temp_dir / "test_report.csv"

        stats = {
            "total_files": 5,
            "processed": 4,
            "skipped": 1,
            "errors": 0,
            "total_original_size": 1000000,
            "total_compressed_size": 500000,
            "space_saved": 500000,
            "total_processing_time": 125.5,  # 2 minutes 5.5 seconds
            "files": [],
        }

        generator._write_csv_report(report_path, stats, "Test Report")

        content = report_path.read_text()
        assert "Total Processing Time" in content
        assert "2m" in content
        assert "5.5s" in content

    def test_write_csv_report_processing_time_seconds_only(self, temp_dir):
        """Test _write_csv_report with processing time in seconds only."""
        generator = ReportGenerator(temp_dir)
        report_path = temp_dir / "test_report.csv"

        stats = {
            "total_files": 5,
            "processed": 4,
            "skipped": 1,
            "errors": 0,
            "total_original_size": 1000000,
            "total_compressed_size": 500000,
            "space_saved": 500000,
            "total_processing_time": 45.7,  # 45.7 seconds
            "files": [],
        }

        generator._write_csv_report(report_path, stats, "Test Report")

        content = report_path.read_text()
        assert "Total Processing Time" in content
        assert "45.7s" in content

    def test_write_csv_report_includes_image_resize(self, temp_dir):
        """Test _write_csv_report includes image_resize when present (line 234)."""
        generator = ReportGenerator(temp_dir)
        report_path = temp_dir / "test_report.csv"

        stats = {
            "total_files": 0,
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "space_saved": 0,
            "files": [],
        }

        cmd_args = {"source_folder": "/test/folder", "image_resize": 75}

        generator._write_csv_report(report_path, stats, "Test Report", cmd_args=cmd_args)

        content = report_path.read_text()
        assert "Image Resize" in content
        assert "75%" in content

    def test_write_csv_report_includes_ffmpeg_path(self, temp_dir):
        """Test _write_csv_report includes ffmpeg_path when present (line 240)."""
        generator = ReportGenerator(temp_dir)
        report_path = temp_dir / "test_report.csv"

        stats = {
            "total_files": 0,
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "space_saved": 0,
            "files": [],
        }

        cmd_args = {"source_folder": "/test/folder", "ffmpeg_path": "/usr/bin/ffmpeg"}

        generator._write_csv_report(report_path, stats, "Test Report", cmd_args=cmd_args)

        content = report_path.read_text()
        assert "FFmpeg Path" in content
        assert "/usr/bin/ffmpeg" in content

    def test_write_csv_report_includes_backup_dir(self, temp_dir):
        """Test _write_csv_report includes backup_dir when present (line 242)."""
        generator = ReportGenerator(temp_dir)
        report_path = temp_dir / "test_report.csv"

        stats = {
            "total_files": 0,
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "space_saved": 0,
            "files": [],
        }

        cmd_args = {"source_folder": "/test/folder", "backup_dir": "/backup/path"}

        generator._write_csv_report(report_path, stats, "Test Report", cmd_args=cmd_args)

        content = report_path.read_text()
        assert "Backup Directory" in content
        assert "/backup/path" in content
