"""
Tests for compressy.core.config module.
"""

from pathlib import Path

import pytest

from compressy.core.config import CompressionConfig, ParameterValidator


@pytest.mark.unit
class TestCompressionConfig:
    """Tests for CompressionConfig dataclass."""

    def test_config_initialization_with_defaults(self, temp_dir):
        """Test CompressionConfig initialization with default values."""
        config = CompressionConfig(source_folder=temp_dir)

        assert config.source_folder == temp_dir
        assert config.video_crf == 23
        assert config.video_preset == "medium"
        assert config.video_resize is None
        assert config.image_quality == 100
        assert config.image_resize is None
        assert config.recursive is False
        assert config.overwrite is False
        assert config.ffmpeg_path is None
        assert config.progress_interval == 5.0
        assert config.keep_if_larger is False
        assert config.backup_dir is None
        assert config.preserve_format is False

    def test_config_initialization_with_custom_values(self, temp_dir):
        """Test CompressionConfig initialization with custom values."""
        backup_dir = temp_dir / "backup"
        config = CompressionConfig(
            source_folder=temp_dir,
            video_crf=18,
            video_preset="slow",
            video_resize=80,
            image_quality=85,
            image_resize=90,
            recursive=True,
            overwrite=True,
            ffmpeg_path="/custom/ffmpeg",
            progress_interval=2.0,
            keep_if_larger=True,
            backup_dir=backup_dir,
            preserve_format=True,
        )

        assert config.video_crf == 18
        assert config.video_preset == "slow"
        assert config.video_resize == 80
        assert config.image_quality == 85
        assert config.image_resize == 90
        assert config.recursive is True
        assert config.overwrite is True
        assert config.ffmpeg_path == "/custom/ffmpeg"
        assert config.progress_interval == 2.0
        assert config.keep_if_larger is True
        assert config.backup_dir == backup_dir
        assert config.preserve_format is True


@pytest.mark.unit
class TestParameterValidator:
    """Tests for ParameterValidator class."""

    def test_validate_valid_config(self, temp_dir):
        """Test validation of valid configuration."""
        config = CompressionConfig(
            source_folder=temp_dir,
            video_crf=23,
            video_preset="medium",
            image_quality=80,
            image_resize=90,
        )
        # Should not raise any exception
        ParameterValidator.validate(config)

    def test_validate_video_crf_valid_range(self):
        """Test validation of valid CRF values."""
        # Valid range: 0-51
        ParameterValidator.validate_video_crf(0)
        ParameterValidator.validate_video_crf(23)
        ParameterValidator.validate_video_crf(51)

    def test_validate_video_crf_invalid_low(self):
        """Test validation of CRF value below minimum."""
        with pytest.raises(ValueError, match="video_crf must be between 0 and 51"):
            ParameterValidator.validate_video_crf(-1)

    def test_validate_video_crf_invalid_high(self):
        """Test validation of CRF value above maximum."""
        with pytest.raises(ValueError, match="video_crf must be between 0 and 51"):
            ParameterValidator.validate_video_crf(52)

    def test_validate_image_quality_valid_range(self):
        """Test validation of valid image quality values."""
        # Valid range: 0-100
        ParameterValidator.validate_image_quality(0)
        ParameterValidator.validate_image_quality(50)
        ParameterValidator.validate_image_quality(100)

    def test_validate_image_quality_invalid_low(self):
        """Test validation of image quality below minimum."""
        with pytest.raises(ValueError, match="image_quality must be between 0 and 100"):
            ParameterValidator.validate_image_quality(-1)

    def test_validate_image_quality_invalid_high(self):
        """Test validation of image quality above maximum."""
        with pytest.raises(ValueError, match="image_quality must be between 0 and 100"):
            ParameterValidator.validate_image_quality(101)

    def test_validate_video_preset_valid(self):
        """Test validation of valid video presets."""
        valid_presets = [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ]
        for preset in valid_presets:
            ParameterValidator.validate_video_preset(preset)

    def test_validate_video_preset_invalid(self):
        """Test validation of invalid video preset."""
        with pytest.raises(ValueError, match="video_preset must be one of"):
            ParameterValidator.validate_video_preset("invalid_preset")

    def test_validate_video_resize_none(self):
        """Test validation of None video resize (valid)."""
        ParameterValidator.validate_video_resize(None)

    def test_validate_video_resize_valid_range(self):
        """Test validation of valid video resize values."""
        # Valid range: 0-100
        ParameterValidator.validate_video_resize(0)
        ParameterValidator.validate_video_resize(50)
        ParameterValidator.validate_video_resize(100)

    def test_validate_video_resize_invalid_low(self):
        """Test validation of video resize below minimum."""
        with pytest.raises(ValueError, match="video_resize must be between 0 and 100"):
            ParameterValidator.validate_video_resize(-1)

    def test_validate_video_resize_invalid_high(self):
        """Test validation of video resize above maximum."""
        with pytest.raises(ValueError, match="video_resize must be between 0 and 100"):
            ParameterValidator.validate_video_resize(101)

    def test_validate_image_resize_none(self):
        """Test validation of None image resize (valid)."""
        ParameterValidator.validate_image_resize(None)

    def test_validate_image_resize_valid_range(self):
        """Test validation of valid image resize values."""
        # Valid range: 1-100
        ParameterValidator.validate_image_resize(1)
        ParameterValidator.validate_image_resize(50)
        ParameterValidator.validate_image_resize(100)

    def test_validate_image_resize_invalid_low(self):
        """Test validation of image resize below minimum."""
        with pytest.raises(ValueError, match="image_resize must be between 1 and 100"):
            ParameterValidator.validate_image_resize(0)

    def test_validate_image_resize_invalid_high(self):
        """Test validation of image resize above maximum."""
        with pytest.raises(ValueError, match="image_resize must be between 1 and 100"):
            ParameterValidator.validate_image_resize(101)

    def test_validate_all_parameters(self, temp_dir):
        """Test validation of all parameters together."""
        config = CompressionConfig(
            source_folder=temp_dir,
            video_crf=25,
            video_preset="fast",
            video_resize=80,
            image_quality=90,
            image_resize=75,
        )
        # Should not raise
        ParameterValidator.validate(config)

    def test_validate_invalid_crf_in_config(self, temp_dir):
        """Test validation catches invalid CRF in config."""
        config = CompressionConfig(source_folder=temp_dir, video_crf=60)
        with pytest.raises(ValueError):
            ParameterValidator.validate(config)

    def test_validate_invalid_quality_in_config(self, temp_dir):
        """Test validation catches invalid image quality in config."""
        config = CompressionConfig(source_folder=temp_dir, image_quality=150)
        with pytest.raises(ValueError):
            ParameterValidator.validate(config)

    def test_validate_invalid_preset_in_config(self, temp_dir):
        """Test validation catches invalid preset in config."""
        config = CompressionConfig(source_folder=temp_dir, video_preset="invalid")
        with pytest.raises(ValueError):
            ParameterValidator.validate(config)

    def test_validate_invalid_video_resize_in_config(self, temp_dir):
        """Test validation catches invalid video resize in config."""
        config = CompressionConfig(source_folder=temp_dir, video_resize=150)
        with pytest.raises(ValueError):
            ParameterValidator.validate(config)

    def test_validate_invalid_resize_in_config(self, temp_dir):
        """Test validation catches invalid resize in config."""
        config = CompressionConfig(source_folder=temp_dir, image_resize=150)
        with pytest.raises(ValueError):
            ParameterValidator.validate(config)

    def test_validate_size_range_valid(self):
        """Test validation of valid size ranges."""
        # Both None is valid
        ParameterValidator.validate_size_range(None, None)
        # Only min_size
        ParameterValidator.validate_size_range(1024, None)
        # Only max_size
        ParameterValidator.validate_size_range(None, 1024 * 1024)
        # Both with min < max
        ParameterValidator.validate_size_range(1024, 1024 * 1024)
        # Equal values
        ParameterValidator.validate_size_range(1024, 1024)

    def test_validate_size_range_negative_min(self):
        """Test validation catches negative min_size."""
        with pytest.raises(ValueError, match="min_size must be non-negative"):
            ParameterValidator.validate_size_range(-1, None)

    def test_validate_size_range_negative_max(self):
        """Test validation catches negative max_size."""
        with pytest.raises(ValueError, match="max_size must be non-negative"):
            ParameterValidator.validate_size_range(None, -1)

    def test_validate_size_range_min_greater_than_max(self):
        """Test validation catches min_size > max_size."""
        with pytest.raises(ValueError, match="min_size.*cannot be greater than max_size"):
            ParameterValidator.validate_size_range(1024 * 1024, 1024)

    def test_validate_output_dir_valid(self, temp_dir):
        """Test validation of valid output_dir."""
        output_dir = temp_dir / "output"
        # Valid: output_dir without overwrite
        ParameterValidator.validate_output_dir(output_dir, False, temp_dir)
        # Valid: no output_dir with overwrite
        ParameterValidator.validate_output_dir(None, True, temp_dir)
        # Valid: no output_dir without overwrite
        ParameterValidator.validate_output_dir(None, False, temp_dir)

    def test_validate_output_dir_with_overwrite(self, temp_dir):
        """Test validation catches output_dir with overwrite."""
        output_dir = temp_dir / "output"
        with pytest.raises(ValueError, match="Cannot use --output-dir and --overwrite together"):
            ParameterValidator.validate_output_dir(output_dir, True, temp_dir)

    def test_validate_output_dir_same_as_source(self, temp_dir):
        """Test validation catches output_dir same as source_folder."""
        with pytest.raises(ValueError, match="output_dir cannot be the same as source_folder"):
            ParameterValidator.validate_output_dir(temp_dir, False, temp_dir)

    def test_validate_video_resolution_valid(self):
        """Test validation of valid video resolutions."""
        # None is valid
        ParameterValidator.validate_video_resolution(None)
        # Named resolutions
        ParameterValidator.validate_video_resolution("720p")
        ParameterValidator.validate_video_resolution("1080p")
        ParameterValidator.validate_video_resolution("4k")
        # Explicit resolutions
        ParameterValidator.validate_video_resolution("1920x1080")
        ParameterValidator.validate_video_resolution("1280x720")

    def test_validate_video_resolution_invalid(self):
        """Test validation catches invalid video resolution."""
        with pytest.raises(ValueError, match="Invalid video resolution"):
            ParameterValidator.validate_video_resolution("invalid")
        with pytest.raises(ValueError, match="Invalid video resolution"):
            ParameterValidator.validate_video_resolution("1920")

    def test_config_with_new_fields(self, temp_dir):
        """Test CompressionConfig with new fields."""
        output_dir = temp_dir / "output"
        config = CompressionConfig(
            source_folder=temp_dir,
            min_size=1024,
            max_size=1024 * 1024,
            output_dir=output_dir,
            video_resolution="1080p",
        )

        assert config.min_size == 1024
        assert config.max_size == 1024 * 1024
        assert config.output_dir == output_dir
        assert config.video_resolution == "1080p"

        # Should validate successfully
        ParameterValidator.validate(config)
