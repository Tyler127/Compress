"""
Integration tests for end-to-end workflows.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from compressy.core.config import CompressionConfig
from compressy.core.media_compressor import MediaCompressor
from compressy.services.reports import ReportGenerator
from compressy.services.statistics import StatisticsManager


@pytest.mark.integration
class TestEndToEnd:
    """Integration tests for complete workflows."""

    @patch("compressy.core.media_compressor.FFmpegExecutor")
    def test_full_compression_workflow(self, mock_ffmpeg_class, temp_dir):
        """Test complete compression workflow from start to finish."""
        # temp_dir fixture already creates the directory
        assert temp_dir.exists(), "temp_dir should exist from fixture"

        mock_ffmpeg = MagicMock()
        mock_ffmpeg_class.return_value = mock_ffmpeg

        # Mock FFmpeg to create output files when run
        def mock_run_with_progress(*args, **kwargs):
            # Extract output path from args
            args_list = list(args[0]) if args else []
            output_path = None
            for arg in args_list:
                if isinstance(arg, str) and not arg.startswith("-") and (arg.endswith(".mp4") or arg.endswith(".jpg")):
                    if "/compressed/" in arg or "\\compressed\\" in arg:
                        output_path = arg
                        break

            # Create output file that FFmpeg would create
            if output_path:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                if output_path.endswith(".mp4"):
                    output_file.write_bytes(b"0" * 400)
                elif output_path.endswith(".jpg"):
                    output_file.write_bytes(b"0" * 300)

            from subprocess import CompletedProcess

            return CompletedProcess([], 0, b"", b"")

        mock_ffmpeg.run_with_progress = MagicMock(side_effect=mock_run_with_progress)

        config = CompressionConfig(
            source_folder=temp_dir,
            video_crf=23,
            image_quality=80,
            recursive=False,
            overwrite=False,
        )

        # Create test files
        video_file = temp_dir / "test.mp4"
        video_file.write_bytes(b"0" * 1000)
        image_file = temp_dir / "test.jpg"
        image_file.write_bytes(b"0" * 500)

        compressor = MediaCompressor(config)

        # Store original methods before patching
        original_stat = Path.stat
        original_exists = Path.exists

        # Mock file sizes - use os.stat_result for proper attribute access
        def mock_stat(self, **kwargs):
            """Mock Path.stat() as an instance method."""
            path_str = str(self)
            # If file exists, use real stat (for files created by mock_run_with_progress)
            try:
                if original_exists(self):
                    return original_stat(self)
            except Exception:
                pass

            # Otherwise use mock values
            if self == video_file or path_str == str(video_file):
                size = 1000
            elif self == image_file or path_str == str(image_file):
                size = 500
            elif "compressed" in path_str:
                # Output files (compressed)
                if path_str.endswith("test.mp4"):
                    size = 400  # Smaller than original
                elif path_str.endswith("test.jpg"):
                    size = 300  # Smaller than original
                else:
                    size = 0
            else:
                size = 0
            # Create a proper stat_result-like object
            stat_result = os.stat_result((0, 0, 0, 0, 0, 0, size, 0, 0, 0))
            return stat_result

        # Mock exists to return True for source folder and files, False for output files
        def mock_exists(self):
            """Mock Path.exists() - return True for source folder and input files, False for output files."""
            # Source folder should exist
            if self == temp_dir:
                return True
            # Input files should exist
            if self in [video_file, image_file]:
                return True
            # For directory creation, check real existence
            if str(self).endswith("compressed"):
                return original_exists(self)
            # Output files don't exist yet
            return False

        # Mock is_file to return True for our test files
        def mock_is_file(self):
            """Mock Path.is_file() - return True for our test files."""
            return self in [video_file, image_file]

        # Mock mkdir to avoid FileExistsError on Windows
        original_mkdir = Path.mkdir

        def mock_mkdir(self, mode=0o777, parents=False, exist_ok=False):
            """Mock Path.mkdir() to handle exist_ok properly."""
            try:
                return original_mkdir(self, mode, parents, exist_ok)
            except FileExistsError:
                # On Windows, exist_ok=True sometimes still raises FileExistsError
                if exist_ok:
                    return
                raise

        with patch.object(Path, "stat", mock_stat):
            with patch.object(Path, "exists", mock_exists):
                with patch.object(Path, "is_file", mock_is_file):
                    with patch.object(Path, "mkdir", mock_mkdir):
                        stats = compressor.compress()

        # Verify statistics
        assert stats["total_files"] == 2
        assert stats["processed"] == 2
        assert stats["errors"] == 0

    @patch("compressy.core.media_compressor.FFmpegExecutor")
    def test_workflow_with_error_recovery(self, mock_ffmpeg_class, temp_dir):
        """Test that workflow continues even when individual files fail."""
        # temp_dir fixture already creates the directory
        assert temp_dir.exists(), "temp_dir should exist from fixture"

        mock_ffmpeg = MagicMock()
        mock_ffmpeg_class.return_value = mock_ffmpeg

        config = CompressionConfig(source_folder=temp_dir)

        # Create test files
        good_file = temp_dir / "good.mp4"
        good_file.write_bytes(b"0" * 1000)
        bad_file = temp_dir / "bad.mp4"
        bad_file.write_bytes(b"0" * 1000)

        # Create compressor first
        compressor = MediaCompressor(config)

        # Mock FFmpeg to fail for bad file, succeed for good file
        def mock_run_with_progress(*args, **kwargs):
            # Check if the input path contains "bad"
            args_list = list(args[0]) if args else []
            input_path = None
            output_path = None
            for i, arg in enumerate(args_list):
                if isinstance(arg, str) and arg == "-i" and i + 1 < len(args_list):
                    input_path = args_list[i + 1]
                elif isinstance(arg, str) and not arg.startswith("-") and arg.endswith(".mp4"):
                    output_path = arg

            if input_path and "bad" in input_path:
                from subprocess import CalledProcessError

                raise CalledProcessError(1, [], b"", b"FFmpeg error")

            # For good file, create the output file and return success
            if output_path:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_bytes(b"0" * 500)  # Create output file

            from subprocess import CompletedProcess

            return CompletedProcess([], 0, b"", b"")

        mock_ffmpeg.run_with_progress = MagicMock(side_effect=mock_run_with_progress)

        # Store original methods before patching
        original_stat = Path.stat
        original_exists = Path.exists

        def mock_stat(self, **kwargs):
            """Mock Path.stat() as an instance method."""
            path_str = str(self)
            # If file exists, use real stat (for files created by mock_run_with_progress)
            try:
                if original_exists(self):
                    return original_stat(self)
            except Exception:
                pass

            # Otherwise use mock values
            if self in [good_file, bad_file] or path_str in [
                str(good_file),
                str(bad_file),
            ]:
                size = 1000
            elif "compressed" in path_str and path_str.endswith("good.mp4"):
                size = 500
            else:
                size = 500
            # Create a proper stat_result-like object
            stat_result = os.stat_result((0, 0, 0, 0, 0, 0, size, 0, 0, 0))
            return stat_result

        # Mock exists to return True for source folder and input files, False for output files
        def mock_exists(self):
            """Mock Path.exists() - return True for source folder and input files, False for output files."""
            if self == temp_dir:
                return True
            if self in [good_file, bad_file]:
                return True
            # For directory creation, check real existence
            if str(self).endswith("compressed"):
                return original_exists(self)
            return False

        # Mock is_file to return True for our test files
        def mock_is_file(self):
            """Mock Path.is_file() - return True for our test files."""
            return self in [good_file, bad_file]

        # Store original exists for mkdir mock
        original_exists = Path.exists

        # Mock mkdir to avoid FileExistsError on Windows
        original_mkdir = Path.mkdir

        def mock_mkdir(self, mode=0o777, parents=False, exist_ok=False):
            """Mock Path.mkdir() to handle exist_ok properly."""
            try:
                return original_mkdir(self, mode, parents, exist_ok)
            except FileExistsError:
                # On Windows, exist_ok=True sometimes still raises FileExistsError
                if exist_ok:
                    return
                raise

        with patch.object(Path, "stat", mock_stat):
            with patch.object(Path, "exists", mock_exists):
                with patch.object(Path, "is_file", mock_is_file):
                    with patch.object(Path, "mkdir", mock_mkdir):
                        stats = compressor.compress()

        # Should have processed one and errored one
        assert stats["errors"] == 1
        assert stats["processed"] == 1

    @patch("compressy.core.media_compressor.FFmpegExecutor")
    def test_workflow_with_report_generation(self, mock_ffmpeg_class, temp_dir):
        """Test complete workflow including report generation."""
        # temp_dir fixture already creates the directory
        assert temp_dir.exists(), "temp_dir should exist from fixture"

        # Setup compression
        mock_ffmpeg = MagicMock()
        mock_ffmpeg_class.return_value = mock_ffmpeg
        mock_ffmpeg.run_with_progress.return_value.returncode = 0

        config = CompressionConfig(source_folder=temp_dir)

        test_file = temp_dir / "test.mp4"
        test_file.write_bytes(b"0" * 1000)

        compressor = MediaCompressor(config)

        def mock_stat(self, **kwargs):
            """Mock Path.stat() as an instance method."""
            if self == test_file:
                size = 1000
            else:
                size = 500
            # Create a proper stat_result-like object
            stat_result = os.stat_result((0, 0, 0, 0, 0, 0, size, 0, 0, 0))
            return stat_result

        # Mock exists to return True for source folder, False for output files
        def mock_exists(self):
            """Mock Path.exists() - return True for source folder, False for others."""
            if self == temp_dir:
                return True
            return False

        with patch.object(Path, "stat", mock_stat):
            with patch.object(Path, "exists", mock_exists):
                stats = compressor.compress()

        # Generate report
        report_generator = ReportGenerator(temp_dir)
        report_paths = report_generator.generate(stats, "test_folder", recursive=False)

        assert len(report_paths) == 1
        assert report_paths[0].exists()

    @patch("compressy.core.media_compressor.FFmpegExecutor")
    def test_workflow_with_statistics_update(self, mock_ffmpeg_class, temp_dir):
        """Test complete workflow including statistics update."""
        # temp_dir fixture already creates the directory
        assert temp_dir.exists(), "temp_dir should exist from fixture"

        # Setup compression
        mock_ffmpeg = MagicMock()
        mock_ffmpeg_class.return_value = mock_ffmpeg
        mock_ffmpeg.run_with_progress.return_value.returncode = 0

        config = CompressionConfig(source_folder=temp_dir)

        test_file = temp_dir / "test.mp4"
        test_file.write_bytes(b"0" * 1000)

        compressor = MediaCompressor(config)

        def mock_stat(self, **kwargs):
            """Mock Path.stat() as an instance method."""
            if self == test_file:
                size = 1000
            else:
                size = 500
            # Create a proper stat_result-like object
            stat_result = os.stat_result((0, 0, 0, 0, 0, 0, size, 0, 0, 0))
            return stat_result

        # Mock exists to return True for source folder, False for output files
        def mock_exists(self):
            """Mock Path.exists() - return True for source folder, False for others."""
            if self == temp_dir:
                return True
            return False

        with patch.object(Path, "stat", mock_stat):
            with patch.object(Path, "exists", mock_exists):
                stats = compressor.compress()

        # Update statistics
        stats_dir = temp_dir / "statistics"
        stats_manager = StatisticsManager(stats_dir)
        stats_manager.update_cumulative_stats(stats)

        # Verify statistics were saved
        cumulative = stats_manager.load_cumulative_stats()
        assert cumulative["total_runs"] == 1
        assert cumulative["total_files_processed"] == stats["processed"]
