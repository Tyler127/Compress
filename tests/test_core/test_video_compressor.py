"""
Tests for compressy.core.video_compressor module.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from compressy.core.config import CompressionConfig
from compressy.core.video_compressor import VideoCompressor


@pytest.mark.unit
class TestVideoCompressor:
    """Tests for VideoCompressor class."""

    def test_initialization(self, mock_config, mock_ffmpeg_executor):
        """Test VideoCompressor initialization."""
        compressor = VideoCompressor(mock_ffmpeg_executor, mock_config)

        assert compressor.ffmpeg == mock_ffmpeg_executor
        assert compressor.config == mock_config

    def test_build_ffmpeg_args_default(self, mock_config, mock_ffmpeg_executor):
        """Test building FFmpeg arguments with default config."""
        compressor = VideoCompressor(mock_ffmpeg_executor, mock_config)
        in_path = Path("input.mp4")
        out_path = Path("output.mp4")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        assert "-i" in args
        assert str(in_path) in args
        assert str(out_path) in args
        assert "-vcodec" in args
        assert "libx264" in args
        assert "-crf" in args
        assert str(mock_config.video_crf) in args
        assert "-preset" in args
        assert mock_config.video_preset in args
        assert "-acodec" in args
        assert "aac" in args
        assert "-b:a" in args
        assert "128k" in args
        assert "-map_metadata" in args
        assert "-y" in args

    def test_build_ffmpeg_args_custom_crf(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg arguments with custom CRF."""
        config = CompressionConfig(source_folder=temp_dir, video_crf=18)
        compressor = VideoCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.mp4")
        out_path = Path("output.mp4")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        crf_index = args.index("-crf")
        assert args[crf_index + 1] == "18"

    def test_build_ffmpeg_args_custom_preset(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg arguments with custom preset."""
        config = CompressionConfig(source_folder=temp_dir, video_preset="slow")
        compressor = VideoCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.mp4")
        out_path = Path("output.mp4")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        preset_index = args.index("-preset")
        assert args[preset_index + 1] == "slow"

    def test_compress_calls_ffmpeg(self, mock_config, mock_ffmpeg_executor, temp_dir):
        """Test that compress calls FFmpeg with correct arguments."""
        compressor = VideoCompressor(mock_ffmpeg_executor, mock_config)
        in_path = temp_dir / "input.mp4"
        out_path = temp_dir / "output.mp4"
        in_path.touch()

        compressor.compress(in_path, out_path)

        # Verify run_with_progress was called
        mock_ffmpeg_executor.run_with_progress.assert_called_once()
        call_args = mock_ffmpeg_executor.run_with_progress.call_args

        # Verify arguments
        args = call_args[0][0]
        assert "-i" in args
        assert str(in_path) in args
        assert str(out_path) in args

        # Verify progress_interval
        assert call_args[1]["progress_interval"] == mock_config.progress_interval
        assert call_args[1]["filename"] == in_path.name

    def test_compress_preserves_metadata(self, mock_config, mock_ffmpeg_executor, temp_dir):
        """Test that compress includes metadata preservation."""
        compressor = VideoCompressor(mock_ffmpeg_executor, mock_config)
        in_path = temp_dir / "input.mp4"
        out_path = temp_dir / "output.mp4"
        in_path.touch()

        compressor.compress(in_path, out_path)

        args = mock_ffmpeg_executor.run_with_progress.call_args[0][0]
        assert "-map_metadata" in args
        assert "0" in args

    def test_build_ffmpeg_args_no_resize(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg arguments with no video resize (None)."""
        config = CompressionConfig(source_folder=temp_dir, video_resize=None)
        compressor = VideoCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.mp4")
        out_path = Path("output.mp4")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Should not contain video filter
        assert "-vf" not in args

    def test_build_ffmpeg_args_resize_zero(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg arguments with video resize set to 0 (no resize)."""
        config = CompressionConfig(source_folder=temp_dir, video_resize=0)
        compressor = VideoCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.mp4")
        out_path = Path("output.mp4")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Should not contain video filter since 0 means no resize
        assert "-vf" not in args

    def test_build_ffmpeg_args_resize_100(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg arguments with video resize set to 100 (no resize)."""
        config = CompressionConfig(source_folder=temp_dir, video_resize=100)
        compressor = VideoCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.mp4")
        out_path = Path("output.mp4")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Should not contain video filter since 100 means 100% (no resize)
        assert "-vf" not in args

    def test_build_ffmpeg_args_with_resize(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg arguments with video resize."""
        config = CompressionConfig(source_folder=temp_dir, video_resize=75)
        compressor = VideoCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.mp4")
        out_path = Path("output.mp4")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Should contain video filter with scale
        assert "-vf" in args
        vf_index = args.index("-vf")
        assert "scale=iw*0.75:ih*0.75:flags=lanczos" in args[vf_index + 1]

    def test_build_ffmpeg_args_with_resize_50(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg arguments with 50% video resize."""
        config = CompressionConfig(source_folder=temp_dir, video_resize=50)
        compressor = VideoCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.mp4")
        out_path = Path("output.mp4")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Should contain video filter with scale
        assert "-vf" in args
        vf_index = args.index("-vf")
        assert "scale=iw*0.5:ih*0.5:flags=lanczos" in args[vf_index + 1]
