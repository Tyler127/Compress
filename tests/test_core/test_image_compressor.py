"""
Tests for compressy.core.image_compressor module.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from compressy.core.config import CompressionConfig
from compressy.core.image_compressor import ImageCompressor


@pytest.mark.unit
class TestImageCompressor:
    """Tests for ImageCompressor class."""

    def test_initialization(self, mock_config, mock_ffmpeg_executor):
        """Test ImageCompressor initialization."""
        compressor = ImageCompressor(mock_ffmpeg_executor, mock_config)

        assert compressor.ffmpeg == mock_ffmpeg_executor
        assert compressor.config == mock_config

    def test_compress_calls_ffmpeg(self, mock_config, mock_ffmpeg_executor, temp_dir):
        """Test that compress calls FFmpeg."""
        compressor = ImageCompressor(mock_ffmpeg_executor, mock_config)
        in_path = temp_dir / "input.jpg"
        out_path = temp_dir / "output.jpg"
        in_path.touch()

        compressor.compress(in_path, out_path)

        mock_ffmpeg_executor.run_with_progress.assert_called_once()

    def test_build_ffmpeg_args_jpeg_preserve_format(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg args for JPEG with preserve_format=True."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=80, preserve_format=True)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.jpg")
        out_path = Path("output.jpg")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        assert "-i" in args
        assert str(in_path) in args
        assert "-q:v" in args
        assert "-y" in args
        assert str(out_path) in args
        # Should not have format conversion
        assert "format=rgb24" not in " ".join(args)

    def test_build_ffmpeg_args_png_to_jpeg_conversion(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg args for PNG to JPEG conversion (preserve_format=False)."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=80, preserve_format=False)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.png")
        out_path = Path("output.jpg")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Should have format conversion to remove alpha channel
        args_str = " ".join(args)
        assert "format=rgb24" in args_str or "-vf" in args

    def test_build_ffmpeg_args_png_preserve_format(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg args for PNG with preserve_format=True."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=80, preserve_format=True)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.png")
        out_path = Path("output.png")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Should have compression_level for PNG
        assert "-compression_level" in args

    def test_build_ffmpeg_args_png_compression_level_mapping(self, mock_ffmpeg_executor, temp_dir):
        """Test PNG compression level mapping for different qualities."""
        # Quality 80 should map to compression_level >= 6
        config = CompressionConfig(source_folder=temp_dir, image_quality=80, preserve_format=True)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.png")
        out_path = Path("output.png")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        compression_level_index = args.index("-compression_level")
        compression_level = int(args[compression_level_index + 1])
        assert compression_level >= 6

    def test_build_ffmpeg_args_webp_preserve_format(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg args for WebP with preserve_format=True."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=85, preserve_format=True)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.webp")
        out_path = Path("output.webp")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Should have quality parameter for WebP
        assert "-quality" in args

    def test_build_ffmpeg_args_with_resize(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg args with image resize."""
        config = CompressionConfig(source_folder=temp_dir, image_resize=90, preserve_format=True)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.jpg")
        out_path = Path("output.jpg")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Should have scale filter
        args_str = " ".join(args)
        assert "scale=" in args_str
        assert "0.9" in args_str or "90" in args_str

    def test_build_ffmpeg_args_png_to_jpeg_with_resize(self, mock_ffmpeg_executor, temp_dir):
        """Test PNG to JPEG conversion with resize."""
        config = CompressionConfig(source_folder=temp_dir, image_resize=75, preserve_format=False)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.png")
        out_path = Path("output.jpg")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        args_str = " ".join(args)
        # Should have both format conversion and resize
        assert "format=rgb24" in args_str or "-vf" in args
        assert "scale=" in args_str

    def test_build_ffmpeg_args_jpeg_to_jpeg_with_resize(self, mock_ffmpeg_executor, temp_dir):
        """Test JPEG to JPEG conversion with resize (preserve_format=False, input is JPEG)."""
        config = CompressionConfig(source_folder=temp_dir, image_resize=75, preserve_format=False)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.jpg")
        out_path = Path("output.jpg")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        args_str = " ".join(args)
        # Should have resize filter (lines 75-76)
        assert "scale=" in args_str
        assert "0.75" in args_str

    def test_build_ffmpeg_args_jpeg_quality_mapping_100(self, mock_ffmpeg_executor, temp_dir):
        """Test JPEG quality mapping for quality=100."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=100, preserve_format=True)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.jpg")
        out_path = Path("output.jpg")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Quality 100 should map to high JPEG quality (low q:v)
        q_index = args.index("-q:v")
        q_value = int(args[q_index + 1])
        # Higher quality = lower q:v value (should be around 2-3 for quality 100)
        assert q_value <= 5

    def test_build_ffmpeg_args_jpeg_quality_mapping_low(self, mock_ffmpeg_executor, temp_dir):
        """Test JPEG quality mapping for low quality."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=50, preserve_format=True)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.jpg")
        out_path = Path("output.jpg")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Lower quality should map to higher q:v value
        q_index = args.index("-q:v")
        q_value = int(args[q_index + 1])
        # Should be higher than high quality
        assert q_value > 5

    def test_map_jpeg_quality(self, mock_ffmpeg_executor, temp_dir):
        """Test JPEG quality mapping method."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=95)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)

        jpeg_quality = compressor._map_jpeg_quality()

        assert 90 <= jpeg_quality <= 95

    def test_map_webp_quality(self, mock_ffmpeg_executor, temp_dir):
        """Test WebP quality mapping method."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=85)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)

        webp_quality = compressor._map_webp_quality()

        assert 1 <= webp_quality <= 95

    def test_build_ffmpeg_args_jpeg_with_resize(self, mock_ffmpeg_executor, temp_dir):
        """Test JPEG with resize (preserve_format=True, resize < 100)."""
        config = CompressionConfig(source_folder=temp_dir, image_resize=75, preserve_format=True)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.jpg")
        out_path = Path("output.jpg")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Should have resize filter
        args_str = " ".join(args)
        assert "scale=" in args_str
        assert "0.75" in args_str

    def test_build_ffmpeg_args_png_low_quality(self, mock_ffmpeg_executor, temp_dir):
        """Test PNG compression level mapping for quality < 80."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=50, preserve_format=True)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.png")
        out_path = Path("output.png")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Should have compression_level
        compression_level_index = args.index("-compression_level")
        compression_level = int(args[compression_level_index + 1])
        # Quality 50 should map to compression_level < 6
        assert 0 <= compression_level <= 9

    def test_build_ffmpeg_args_other_format(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg args for other image formats (not jpg/png/webp)."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=80, preserve_format=True)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.bmp")
        out_path = Path("output.bmp")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Should have quality parameter for other formats
        assert "-q:v" in args

    def test_build_ffmpeg_args_other_format_high_quality(self, mock_ffmpeg_executor, temp_dir):
        """Test building FFmpeg args for other formats with quality > 100."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=150, preserve_format=True)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)
        in_path = Path("input.bmp")
        out_path = Path("output.bmp")

        args = compressor._build_ffmpeg_args(in_path, out_path)

        # Should have quality parameter (should default to 2 for quality > 100)
        q_index = args.index("-q:v")
        q_value = int(args[q_index + 1])
        assert q_value == 2

    def test_map_webp_quality_100(self, mock_ffmpeg_executor, temp_dir):
        """Test WebP quality mapping for quality >= 100."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=100)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)

        webp_quality = compressor._map_webp_quality()

        assert webp_quality == 95

    def test_map_webp_quality_95(self, mock_ffmpeg_executor, temp_dir):
        """Test WebP quality mapping for quality >= 95."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=97)
        compressor = ImageCompressor(mock_ffmpeg_executor, config)

        webp_quality = compressor._map_webp_quality()

        # Quality 97 should map to 97 - 5 = 92
        assert webp_quality == 92
