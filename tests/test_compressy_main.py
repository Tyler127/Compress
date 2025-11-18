"""
Tests for the main compressy.py script.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Import the main function from the root compressy.py
# Load it as a module since it's not in a package
_root_dir = Path(__file__).resolve().parent.parent
compressy_script = _root_dir / "compressy.py"

# Load with "compressy.py" as the module name so coverage can track it
# Coverage needs the module name to match the file pattern
spec = importlib.util.spec_from_file_location("compressy.py", compressy_script)
compressy_main = importlib.util.module_from_spec(spec)
sys.modules["compressy.py"] = compressy_main
spec.loader.exec_module(compressy_main)


@pytest.mark.unit
class TestCompressyMain:
    """Tests for the main compressy.py script."""

    def test_main_calls_argument_parser(self, capsys):
        """Test that main() creates an ArgumentParser."""
        # Test that ArgumentParser is called by checking error output
        with patch("sys.argv", ["compressy.py"]):
            with pytest.raises(SystemExit):
                compressy_main.main()

        output = capsys.readouterr()
        # Should show help or error message
        assert len(output.out) > 0 or len(output.err) > 0

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv", new=["compressy.py", str(Path("temp_dir"))])
    def test_main_with_source_folder(self, mock_config_class, mock_compressor_class, temp_dir, capsys):
        """Test main() with a source folder argument."""
        # Create a test video file
        video_file = temp_dir / "test.mp4"
        video_file.write_bytes(b"0" * 1000)

        # Update sys.argv to use actual temp_dir
        with patch("sys.argv", ["compressy.py", str(temp_dir)]):
            # Mock CompressionConfig
            mock_config = MagicMock()
            mock_config.source_folder = Path(temp_dir)
            mock_config_class.return_value = mock_config

            # Mock MediaCompressor
            mock_compressor = MagicMock()
            mock_stats = {
                "processed": 1,
                "skipped": 0,
                "errors": 0,
                "total_original_size": 1000,
                "total_compressed_size": 500,
                "space_saved": 500,
            }
            mock_compressor.compress.return_value = mock_stats
            mock_compressor_class.return_value = mock_compressor

            # Mock ReportGenerator
            with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
                mock_report_gen = MagicMock()
                mock_report_gen.generate.return_value = [temp_dir / "reports" / "test_report.json"]
                mock_report_gen_class.return_value = mock_report_gen

                # Mock StatisticsManager
                with patch("compressy.py.StatisticsManager") as mock_stats_mgr_class:
                    mock_stats_mgr = MagicMock()
                    mock_stats_mgr_class.return_value = mock_stats_mgr

                    result = compressy_main.main()

                    assert result == 0
                    mock_config_class.assert_called_once()
                    mock_compressor_class.assert_called_once_with(mock_config)
                    mock_compressor.compress.assert_called_once()

                    output = capsys.readouterr()
                    assert "Compression Complete!" in output.out
                    assert "Processed: 1 files" in output.out

    @patch("compressy.py.StatisticsManager")
    @patch("sys.argv", new=["compressy.py", "--view-stats"])
    def test_main_view_stats(self, mock_stats_mgr_class, temp_dir, capsys):
        """Test main() with --view-stats flag."""
        with patch("sys.argv", ["compressy.py", "--view-stats"]):
            mock_stats_mgr = MagicMock()
            mock_stats_mgr_class.return_value = mock_stats_mgr

            result = compressy_main.main()

            assert result == 0
            mock_stats_mgr.print_stats.assert_called_once()

    @patch("compressy.py.StatisticsManager")
    @patch("sys.argv", new=["compressy.py", "--view-history"])
    def test_main_view_history_all(self, mock_stats_mgr_class, temp_dir, capsys):
        """Test main() with --view-history flag (show all)."""
        with patch("sys.argv", ["compressy.py", "--view-history"]):
            mock_stats_mgr = MagicMock()
            mock_stats_mgr_class.return_value = mock_stats_mgr

            result = compressy_main.main()

            assert result == 0
            mock_stats_mgr.print_history.assert_called_once_with(limit=None)

    @patch("compressy.py.StatisticsManager")
    @patch("sys.argv", new=["compressy.py", "-h"])
    def test_main_view_history_short_flag(self, mock_stats_mgr_class, temp_dir, capsys):
        """Test main() with -h flag (short for --view-history)."""
        with patch("sys.argv", ["compressy.py", "-h"]):
            mock_stats_mgr = MagicMock()
            mock_stats_mgr_class.return_value = mock_stats_mgr

            result = compressy_main.main()

            assert result == 0
            mock_stats_mgr.print_history.assert_called_once_with(limit=None)

    @patch("compressy.py.StatisticsManager")
    @patch("sys.argv", new=["compressy.py", "--view-history", "5"])
    def test_main_view_history_limit(self, mock_stats_mgr_class, temp_dir, capsys):
        """Test main() with --view-history N flag (limit to N)."""
        with patch("sys.argv", ["compressy.py", "--view-history", "5"]):
            mock_stats_mgr = MagicMock()
            mock_stats_mgr_class.return_value = mock_stats_mgr

            result = compressy_main.main()

            assert result == 0
            mock_stats_mgr.print_history.assert_called_once_with(limit=5)

    @patch("compressy.py.StatisticsManager")
    @patch("sys.argv", new=["compressy.py", "--view-history", "0"])
    def test_main_view_history_zero(self, mock_stats_mgr_class, temp_dir, capsys):
        """Test main() with --view-history 0 flag (should show all)."""
        with patch("sys.argv", ["compressy.py", "--view-history", "0"]):
            mock_stats_mgr = MagicMock()
            mock_stats_mgr_class.return_value = mock_stats_mgr

            result = compressy_main.main()

            assert result == 0
            # view_history 0 should result in limit=None
            mock_stats_mgr.print_history.assert_called_once_with(limit=None)

    @patch("sys.argv", new=["compressy.py"])
    def test_main_missing_source_folder(self, capsys):
        """Test main() requires source_folder when not using view commands."""
        with patch("sys.argv", ["compressy.py"]):
            with pytest.raises(SystemExit):
                compressy_main.main()

        output = capsys.readouterr()
        # Should show error about source_folder being required
        assert "source_folder" in output.out.lower() or "source_folder" in output.err.lower()

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_with_all_arguments(self, mock_argv, mock_config_class, mock_compressor_class, temp_dir):
        """Test main() with all optional arguments."""
        video_file = temp_dir / "test.mp4"
        video_file.write_bytes(b"0" * 1000)

        backup_dir = temp_dir / "backup"
        mock_argv.__getitem__.side_effect = lambda i: [
            "compressy.py",
            str(temp_dir),
            "--video-crf",
            "26",
            "--video-preset",
            "fast",
            "--image-quality",
            "80",
            "--image-resize",
            "90",
            "--recursive",
            "--overwrite",
            "--ffmpeg-path",
            "/custom/path/ffmpeg",
            "--progress-interval",
            "2.0",
            "--keep-if-larger",
            "--backup-dir",
            str(backup_dir),
            "--preserve-format",
            "--preserve-timestamps",
        ][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = {
            "processed": 1,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000,
            "total_compressed_size": 500,
            "space_saved": 500,
        }
        mock_compressor_class.return_value = mock_compressor

        with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
            mock_report_gen = MagicMock()
            mock_report_gen.generate.return_value = [temp_dir / "reports" / "test_report.json"]
            mock_report_gen_class.return_value = mock_report_gen

            with patch("compressy.py.StatisticsManager"):
                result = compressy_main.main()

                assert result == 0
                # Verify CompressionConfig was called with all arguments
                call_kwargs = mock_config_class.call_args[1]
                assert call_kwargs["video_crf"] == 26
                assert call_kwargs["video_preset"] == "fast"
                assert call_kwargs["image_quality"] == 80
                assert call_kwargs["image_resize"] == 90
                assert call_kwargs["recursive"] is True
                assert call_kwargs["overwrite"] is True
                assert call_kwargs["ffmpeg_path"] == "/custom/path/ffmpeg"
                assert call_kwargs["progress_interval"] == 2.0
                assert call_kwargs["keep_if_larger"] is True
                assert call_kwargs["backup_dir"] == Path(backup_dir)
                assert call_kwargs["preserve_format"] is True
                assert call_kwargs["preserve_timestamps"] is True

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_with_size_filters_and_output_dir(
        self, mock_argv, mock_config_class, mock_compressor_class, temp_dir, capsys
    ):
        """Test main() handles min/max size, output dir, and video resolution options."""
        output_dir = temp_dir / "custom_output"
        mock_argv.__getitem__.side_effect = lambda i: [
            "compressy.py",
            str(temp_dir),
            "--min-size",
            "1MB",
            "--max-size",
            "5MB",
            "--output-dir",
            str(output_dir),
            "--video-resolution",
            "1280x720",
        ][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = {
            "processed": 1,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000,
            "total_compressed_size": 800,
            "space_saved": 200,
        }
        mock_compressor_class.return_value = mock_compressor

        with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
            mock_report_gen = MagicMock()
            mock_report_gen.generate.return_value = [output_dir / "reports" / "test_report.json"]
            mock_report_gen_class.return_value = mock_report_gen

            with patch("compressy.py.StatisticsManager"):
                result = compressy_main.main()

        assert result == 0

        # Verify CompressionConfig received parsed values
        call_kwargs = mock_config_class.call_args[1]
        assert call_kwargs["min_size"] == 1024 * 1024
        assert call_kwargs["max_size"] == 5 * 1024 * 1024
        assert call_kwargs["output_dir"] == output_dir
        assert call_kwargs["video_resolution"] == "1280x720"

        # Verify cmd_args includes optional parameters
        cmd_args = mock_report_gen.generate.call_args.kwargs["cmd_args"]
        assert cmd_args["min_size"] == "1MB"
        assert cmd_args["max_size"] == "5MB"
        assert cmd_args["output_dir"] == str(output_dir)
        assert cmd_args["video_resolution"] == "1280x720"

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_with_zero_original_size(self, mock_argv, mock_config_class, mock_compressor_class, temp_dir, capsys):
        """Test main() handles zero original_size correctly."""
        mock_argv.__getitem__.side_effect = lambda i: ["compressy.py", str(temp_dir)][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = {
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "space_saved": 0,
        }
        mock_compressor_class.return_value = mock_compressor

        with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
            mock_report_gen = MagicMock()
            mock_report_gen.generate.return_value = []
            mock_report_gen_class.return_value = mock_report_gen

            with patch("compressy.py.StatisticsManager"):
                result = compressy_main.main()

                assert result == 0
                output = capsys.readouterr()
                assert "Space saved: 0.00 B" in output.out or "Space saved: 0 B" in output.out

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_with_statistics_error(self, mock_argv, mock_config_class, mock_compressor_class, temp_dir, capsys):
        """Test main() handles statistics update errors gracefully."""
        video_file = temp_dir / "test.mp4"
        video_file.write_bytes(b"0" * 1000)

        mock_argv.__getitem__.side_effect = lambda i: ["compressy.py", str(temp_dir)][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = {
            "processed": 1,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000,
            "total_compressed_size": 500,
            "space_saved": 500,
        }
        mock_compressor_class.return_value = mock_compressor

        with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
            mock_report_gen = MagicMock()
            mock_report_gen.generate.return_value = [temp_dir / "reports" / "test_report.json"]
            mock_report_gen_class.return_value = mock_report_gen

            with patch("compressy.py.StatisticsManager") as mock_stats_mgr_class:
                mock_stats_mgr = MagicMock()
                mock_stats_mgr.update_cumulative_stats.side_effect = Exception("Statistics error")
                mock_stats_mgr_class.return_value = mock_stats_mgr

                result = compressy_main.main()

                assert result == 0  # Should still succeed
                output = capsys.readouterr()
                assert "Warning: Could not update statistics" in output.out
                assert "Compression Complete!" in output.out

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_with_compression_error(self, mock_argv, mock_config_class, mock_compressor_class, temp_dir, capsys):
        """Test main() handles compression errors."""
        mock_argv.__getitem__.side_effect = lambda i: ["compressy.py", str(temp_dir)][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.side_effect = Exception("Compression failed")
        mock_compressor_class.return_value = mock_compressor

        result = compressy_main.main()

        assert result == 1  # Should return error code
        output = capsys.readouterr()
        assert "Error: Compression failed" in output.out

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_recursive_multiple_reports(
        self, mock_argv, mock_config_class, mock_compressor_class, temp_dir, capsys
    ):
        """Test main() displays multiple reports message in recursive mode."""
        video_file = temp_dir / "test.mp4"
        video_file.write_bytes(b"0" * 1000)

        mock_argv.__getitem__.side_effect = lambda i: ["compressy.py", str(temp_dir), "--recursive"][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = {
            "processed": 1,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000,
            "total_compressed_size": 500,
            "space_saved": 500,
        }
        mock_compressor_class.return_value = mock_compressor

        with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
            mock_report_gen = MagicMock()
            # Multiple reports for recursive mode
            mock_report_gen.generate.return_value = [
                temp_dir / "reports" / "report1.json",
                temp_dir / "reports" / "report2.json",
            ]
            mock_report_gen_class.return_value = mock_report_gen

            with patch("compressy.py.StatisticsManager"):
                result = compressy_main.main()

                assert result == 0
                output = capsys.readouterr()
                assert "Reports generated: 2 reports" in output.out

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_no_reports(self, mock_argv, mock_config_class, mock_compressor_class, temp_dir, capsys):
        """Test main() handles no reports generated."""
        video_file = temp_dir / "test.mp4"
        video_file.write_bytes(b"0" * 1000)

        mock_argv.__getitem__.side_effect = lambda i: ["compressy.py", str(temp_dir)][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = {
            "processed": 1,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000,
            "total_compressed_size": 500,
            "space_saved": 500,
        }
        mock_compressor_class.return_value = mock_compressor

        with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
            mock_report_gen = MagicMock()
            mock_report_gen.generate.return_value = []  # No reports
            mock_report_gen_class.return_value = mock_report_gen

            with patch("compressy.py.StatisticsManager"):
                result = compressy_main.main()

                assert result == 0
                output = capsys.readouterr()
                assert "Report: N/A" in output.out

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_with_cmd_args_including_optional(self, mock_argv, mock_config_class, mock_compressor_class, temp_dir):
        """Test main() passes all cmd_args to report generator including optional ones."""
        backup_dir = temp_dir / "backup"
        mock_argv.__getitem__.side_effect = lambda i: [
            "compressy.py",
            str(temp_dir),
            "--video-crf",
            "26",
            "--video-preset",
            "fast",
            "--image-quality",
            "80",
            "--image-resize",
            "90",
            "--recursive",
            "--overwrite",
            "--ffmpeg-path",
            "/custom/ffmpeg",
            "--progress-interval",
            "2.0",
            "--keep-if-larger",
            "--backup-dir",
            str(backup_dir),
            "--preserve-format",
        ][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = {
            "processed": 1,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000,
            "total_compressed_size": 500,
            "space_saved": 500,
        }
        mock_compressor_class.return_value = mock_compressor

        with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
            mock_report_gen = MagicMock()
            mock_report_gen.generate.return_value = [temp_dir / "reports" / "test_report.json"]
            mock_report_gen_class.return_value = mock_report_gen

            with patch("compressy.py.StatisticsManager"):
                compressy_main.main()

                # Verify cmd_args passed to generate includes optional args
                call_kwargs = mock_report_gen.generate.call_args[1]
                cmd_args = call_kwargs["cmd_args"]
                assert cmd_args["ffmpeg_path"] == "/custom/ffmpeg"
                assert cmd_args["backup_dir"] == str(backup_dir)

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_with_only_ffmpeg_path(self, mock_argv, mock_config_class, mock_compressor_class, temp_dir):
        """Test main() includes ffmpeg_path in cmd_args when provided."""
        mock_argv.__getitem__.side_effect = lambda i: [
            "compressy.py",
            str(temp_dir),
            "--ffmpeg-path",
            "/custom/ffmpeg",
        ][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = {
            "processed": 1,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000,
            "total_compressed_size": 500,
            "space_saved": 500,
        }
        mock_compressor_class.return_value = mock_compressor

        with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
            mock_report_gen = MagicMock()
            mock_report_gen.generate.return_value = [temp_dir / "reports" / "test_report.json"]
            mock_report_gen_class.return_value = mock_report_gen

            with patch("compressy.py.StatisticsManager"):
                compressy_main.main()

                # Verify cmd_args includes ffmpeg_path but not backup_dir
                call_kwargs = mock_report_gen.generate.call_args[1]
                cmd_args = call_kwargs["cmd_args"]
                assert cmd_args["ffmpeg_path"] == "/custom/ffmpeg"
                assert "backup_dir" not in cmd_args

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_with_only_backup_dir(self, mock_argv, mock_config_class, mock_compressor_class, temp_dir):
        """Test main() includes backup_dir in cmd_args when provided."""
        backup_dir = temp_dir / "backup"
        mock_argv.__getitem__.side_effect = lambda i: [
            "compressy.py",
            str(temp_dir),
            "--backup-dir",
            str(backup_dir),
        ][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = {
            "processed": 1,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000,
            "total_compressed_size": 500,
            "space_saved": 500,
        }
        mock_compressor_class.return_value = mock_compressor

        with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
            mock_report_gen = MagicMock()
            mock_report_gen.generate.return_value = [temp_dir / "reports" / "test_report.json"]
            mock_report_gen_class.return_value = mock_report_gen

            with patch("compressy.py.StatisticsManager"):
                compressy_main.main()

                # Verify cmd_args includes backup_dir but not ffmpeg_path
                call_kwargs = mock_report_gen.generate.call_args[1]
                cmd_args = call_kwargs["cmd_args"]
                assert cmd_args["backup_dir"] == str(backup_dir)
                assert "ffmpeg_path" not in cmd_args

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_recursive_single_report(self, mock_argv, mock_config_class, mock_compressor_class, temp_dir, capsys):
        """Test main() displays single report message in recursive mode when only one report."""
        video_file = temp_dir / "test.mp4"
        video_file.write_bytes(b"0" * 1000)

        mock_argv.__getitem__.side_effect = lambda i: ["compressy.py", str(temp_dir), "--recursive"][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = {
            "processed": 1,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000,
            "total_compressed_size": 500,
            "space_saved": 500,
        }
        mock_compressor_class.return_value = mock_compressor

        with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
            mock_report_gen = MagicMock()
            # Single report in recursive mode
            mock_report_gen.generate.return_value = [temp_dir / "reports" / "report1.json"]
            mock_report_gen_class.return_value = mock_report_gen

            with patch("compressy.py.StatisticsManager"):
                result = compressy_main.main()

                assert result == 0
                output = capsys.readouterr()
                # Should show single report message, not multiple reports
                assert "Report: " in output.out
                assert "Reports generated: " not in output.out

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_with_short_flags(self, mock_argv, mock_config_class, mock_compressor_class, temp_dir):
        """Test main() handles multi-character short flags correctly."""
        output_dir = temp_dir / "custom_output"
        backup_dir = temp_dir / "backup"
        mock_argv.__getitem__.side_effect = lambda i: [
            "compressy.py",
            str(temp_dir),
            "-crf",
            "26",
            "-vp",
            "fast",
            "-vr",
            "80",
            "-iq",
            "82",
            "-ir",
            "75",
            "-r",
            "-o",
            "--ffmpeg-path",
            "/custom/path/ffmpeg",
            "-pi",
            "2.5",
            "-kl",
            "--backup-dir",
            str(backup_dir),
            "-pf",
            "-pt",
            "-m",
            "1MB",
            "-M",
            "5MB",
            "-d",
            str(output_dir),
            "-res",
            "720p",
        ][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = {
            "processed": 1,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000,
            "total_compressed_size": 800,
            "space_saved": 200,
        }
        mock_compressor_class.return_value = mock_compressor

        with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
            mock_report_gen = MagicMock()
            mock_report_gen.generate.return_value = [output_dir / "reports" / "test_report.csv"]
            mock_report_gen_class.return_value = mock_report_gen

            with patch("compressy.py.StatisticsManager"):
                result = compressy_main.main()

        assert result == 0

        call_kwargs = mock_config_class.call_args[1]
        assert call_kwargs["video_crf"] == 26
        assert call_kwargs["video_preset"] == "fast"
        assert call_kwargs["video_resize"] == 80
        assert call_kwargs["image_quality"] == 82
        assert call_kwargs["image_resize"] == 75
        assert call_kwargs["recursive"] is True
        assert call_kwargs["overwrite"] is True
        assert call_kwargs["ffmpeg_path"] == "/custom/path/ffmpeg"
        assert call_kwargs["progress_interval"] == 2.5
        assert call_kwargs["keep_if_larger"] is True
        assert call_kwargs["backup_dir"] == Path(backup_dir)
        assert call_kwargs["preserve_format"] is True
        assert call_kwargs["preserve_timestamps"] is True
        assert call_kwargs["min_size"] == 1024 * 1024
        assert call_kwargs["max_size"] == 5 * 1024 * 1024
        assert call_kwargs["output_dir"] == output_dir
        assert call_kwargs["video_resolution"] == "720p"

        cmd_args = mock_report_gen.generate.call_args.kwargs["cmd_args"]
        assert cmd_args["video_crf"] == 26
        assert cmd_args["video_preset"] == "fast"
        assert cmd_args["video_resize"] == 80
        assert cmd_args["image_quality"] == 82
        assert cmd_args["image_resize"] == 75
        assert cmd_args["recursive"] is True
        assert cmd_args["overwrite"] is True
        assert cmd_args["keep_if_larger"] is True
        assert cmd_args["progress_interval"] == 2.5
        assert cmd_args["preserve_format"] is True
        assert cmd_args["preserve_timestamps"] is True
        assert cmd_args["min_size"] == "1MB"
        assert cmd_args["max_size"] == "5MB"
        assert cmd_args["output_dir"] == str(output_dir)
        assert cmd_args["video_resolution"] == "720p"

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_statistics_error_with_traceback(
        self, mock_argv, mock_config_class, mock_compressor_class, temp_dir, capsys
    ):
        """Test main() prints traceback when statistics update fails."""
        video_file = temp_dir / "test.mp4"
        video_file.write_bytes(b"0" * 1000)

        mock_argv.__getitem__.side_effect = lambda i: ["compressy.py", str(temp_dir)][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = {
            "processed": 1,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000,
            "total_compressed_size": 500,
            "space_saved": 500,
        }
        mock_compressor_class.return_value = mock_compressor

        with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
            mock_report_gen = MagicMock()
            mock_report_gen.generate.return_value = [temp_dir / "reports" / "test_report.json"]
            mock_report_gen_class.return_value = mock_report_gen

            with patch("compressy.py.StatisticsManager") as mock_stats_mgr_class:
                mock_stats_mgr = MagicMock()
                mock_stats_mgr.update_cumulative_stats.side_effect = Exception("Statistics error")
                mock_stats_mgr_class.return_value = mock_stats_mgr

                result = compressy_main.main()

                assert result == 0
                output = capsys.readouterr()
                assert "Warning: Could not update statistics" in output.out
                assert "Traceback:" in output.out
                assert "Compression Complete!" in output.out

    @patch("compressy.py.MediaCompressor")
    @patch("compressy.py.CompressionConfig")
    @patch("sys.argv")
    def test_main_successful_compression_returns_zero(
        self, mock_argv, mock_config_class, mock_compressor_class, temp_dir
    ):
        """Test main() returns 0 on successful compression."""
        video_file = temp_dir / "test.mp4"
        video_file.write_bytes(b"0" * 1000)

        mock_argv.__getitem__.side_effect = lambda i: ["compressy.py", str(temp_dir)][i]

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = {
            "processed": 1,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 1000,
            "total_compressed_size": 500,
            "space_saved": 500,
        }
        mock_compressor_class.return_value = mock_compressor

        with patch("compressy.py.ReportGenerator") as mock_report_gen_class:
            mock_report_gen = MagicMock()
            mock_report_gen.generate.return_value = [temp_dir / "reports" / "test_report.json"]
            mock_report_gen_class.return_value = mock_report_gen

            with patch("compressy.py.StatisticsManager"):
                result = compressy_main.main()
                assert result == 0
