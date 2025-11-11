"""
Integration tests for end-to-end workflows.
"""

from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from unittest.mock import MagicMock, patch

import pytest

from compressy.core.config import CompressionConfig
from compressy.core.media_compressor import MediaCompressor
from compressy.services.reports import ReportGenerator
from compressy.services.statistics import StatisticsManager


def _extract_output_path(ffmpeg_args):
    output_path = None
    skip_next = False
    for arg in ffmpeg_args:
        if skip_next:
            skip_next = False
            continue
        if arg == "-i":
            skip_next = True
            continue
        if isinstance(arg, (str, Path)):
            arg_str = str(arg)
            if not arg_str.startswith("-") and arg_str.lower().endswith((".mp4", ".jpg", ".jpeg")):
                output_path = Path(arg_str)
    return output_path


def _extract_input_path(ffmpeg_args):
    for idx, arg in enumerate(ffmpeg_args):
        if arg == "-i" and idx + 1 < len(ffmpeg_args):
            return ffmpeg_args[idx + 1]
    return None


def _successful_ffmpeg_side_effect(size_map):
    def _side_effect(ffmpeg_args, **kwargs):
        output_path = _extract_output_path(ffmpeg_args)
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            size = size_map.get(output_path.suffix.lower(), 100)
            output_path.write_bytes(b"0" * size)
        return CompletedProcess([], 0, b"", b"")

    return _side_effect


def _error_ffmpeg_side_effect(bad_keyword, size_map):
    def _side_effect(ffmpeg_args, **kwargs):
        input_path = _extract_input_path(ffmpeg_args)
        output_path = _extract_output_path(ffmpeg_args)
        if input_path and bad_keyword in input_path:
            raise CalledProcessError(1, [], b"", b"FFmpeg error")
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            size = size_map.get(output_path.suffix.lower(), 100)
            output_path.write_bytes(b"0" * size)
        return CompletedProcess([], 0, b"", b"")

    return _side_effect


@pytest.mark.integration
class TestEndToEnd:
    """Integration tests for complete workflows."""

    @patch("compressy.core.media_compressor.FFmpegExecutor")
    def test_full_compression_workflow(self, mock_ffmpeg_class, temp_dir):
        """Test complete compression workflow from start to finish."""
        mock_ffmpeg = MagicMock()
        mock_ffmpeg_class.return_value = mock_ffmpeg

        mock_ffmpeg.run_with_progress = MagicMock(
            side_effect=_successful_ffmpeg_side_effect({".mp4": 400, ".jpg": 300})
        )

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
        stats = compressor.compress()

        # Verify statistics
        assert stats["total_files"] == 2
        assert stats["processed"] == 2
        assert stats["errors"] == 0

    @patch("compressy.core.media_compressor.FFmpegExecutor")
    def test_workflow_with_error_recovery(self, mock_ffmpeg_class, temp_dir):
        """Test that workflow continues even when individual files fail."""
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
        mock_ffmpeg.run_with_progress = MagicMock(side_effect=_error_ffmpeg_side_effect("bad", {".mp4": 500}))

        stats = compressor.compress()

        # Should have processed one and errored one
        assert stats["errors"] == 1
        assert stats["processed"] == 1

    @patch("compressy.core.media_compressor.FFmpegExecutor")
    def test_workflow_with_report_generation(self, mock_ffmpeg_class, temp_dir):
        """Test complete workflow including report generation."""
        mock_ffmpeg = MagicMock()
        mock_ffmpeg_class.return_value = mock_ffmpeg
        mock_ffmpeg.run_with_progress = MagicMock(side_effect=_successful_ffmpeg_side_effect({".mp4": 500}))

        config = CompressionConfig(source_folder=temp_dir)

        test_file = temp_dir / "test.mp4"
        test_file.write_bytes(b"0" * 1000)

        compressor = MediaCompressor(config)
        stats = compressor.compress()

        # Generate report
        report_generator = ReportGenerator(temp_dir)
        report_paths = report_generator.generate(stats, "test_folder", recursive=False)

        assert len(report_paths) == 1
        assert report_paths[0].exists()

    @patch("compressy.core.media_compressor.FFmpegExecutor")
    def test_workflow_with_statistics_update(self, mock_ffmpeg_class, temp_dir):
        """Test complete workflow including statistics update."""
        mock_ffmpeg = MagicMock()
        mock_ffmpeg_class.return_value = mock_ffmpeg
        mock_ffmpeg.run_with_progress = MagicMock(side_effect=_successful_ffmpeg_side_effect({".mp4": 500}))

        config = CompressionConfig(source_folder=temp_dir)

        test_file = temp_dir / "test.mp4"
        test_file.write_bytes(b"0" * 1000)

        compressor = MediaCompressor(config)
        stats = compressor.compress()

        # Update statistics
        stats_dir = temp_dir / "statistics"
        stats_manager = StatisticsManager(stats_dir)
        stats_manager.update_cumulative_stats(stats)

        # Verify statistics were saved
        cumulative = stats_manager.load_cumulative_stats()
        assert cumulative["total_runs"] == 1
        assert cumulative["total_files_processed"] == stats["processed"]
