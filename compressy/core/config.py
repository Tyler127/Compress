from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ============================================================================
# Configuration Classes
# ============================================================================


@dataclass
class CompressionConfig:
    """Configuration for media compression."""

    source_folder: Path
    video_crf: int = 23
    video_preset: str = "medium"
    video_resize: Optional[int] = None
    image_quality: int = 100
    image_resize: Optional[int] = None
    recursive: bool = False
    overwrite: bool = False
    ffmpeg_path: Optional[str] = None
    progress_interval: float = 5.0
    keep_if_larger: bool = False
    backup_dir: Optional[Path] = None
    preserve_format: bool = False
    preserve_timestamps: bool = False
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    output_dir: Optional[Path] = None
    video_resolution: Optional[str] = None


# ============================================================================
# Parameter Validator
# ============================================================================


class ParameterValidator:
    """Validates compression parameters."""

    @staticmethod
    def validate(config: CompressionConfig) -> None:
        """Validate all parameters in the configuration."""
        ParameterValidator.validate_video_crf(config.video_crf)
        ParameterValidator.validate_image_quality(config.image_quality)
        ParameterValidator.validate_video_preset(config.video_preset)
        ParameterValidator.validate_video_resize(config.video_resize)
        ParameterValidator.validate_image_resize(config.image_resize)
        ParameterValidator.validate_size_range(config.min_size, config.max_size)
        ParameterValidator.validate_output_dir(config.output_dir, config.overwrite, config.source_folder)
        ParameterValidator.validate_video_resolution(config.video_resolution)

    @staticmethod
    def validate_video_crf(video_crf: int) -> None:
        """Validate video CRF value."""
        if not (0 <= video_crf <= 51):
            raise ValueError(f"video_crf must be between 0 and 51, got {video_crf}")

    @staticmethod
    def validate_image_quality(image_quality: int) -> None:
        """Validate image quality value."""
        if not (0 <= image_quality <= 100):
            raise ValueError(f"image_quality must be between 0 and 100, got {image_quality}")

    @staticmethod
    def validate_video_preset(video_preset: str) -> None:
        """Validate video preset."""
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
        if video_preset not in valid_presets:
            raise ValueError(f"video_preset must be one of {valid_presets}, got {video_preset}")

    @staticmethod
    def validate_video_resize(video_resize: Optional[int]) -> None:
        """Validate video resize value."""
        if video_resize is not None and not (0 <= video_resize <= 100):
            raise ValueError(f"video_resize must be between 0 and 100, got {video_resize}")

    @staticmethod
    def validate_image_resize(image_resize: Optional[int]) -> None:
        """Validate image resize value."""
        if image_resize is not None and not (1 <= image_resize <= 100):
            raise ValueError(f"image_resize must be between 1 and 100, got {image_resize}")

    @staticmethod
    def validate_size_range(min_size: Optional[int], max_size: Optional[int]) -> None:
        """Validate min_size and max_size values."""
        if min_size is not None and min_size < 0:
            raise ValueError(f"min_size must be non-negative, got {min_size}")
        if max_size is not None and max_size < 0:
            raise ValueError(f"max_size must be non-negative, got {max_size}")
        if min_size is not None and max_size is not None and min_size > max_size:
            raise ValueError(f"min_size ({min_size}) cannot be greater than max_size ({max_size})")

    @staticmethod
    def validate_output_dir(output_dir: Optional[Path], overwrite: bool, source_folder: Path) -> None:
        """Validate output directory configuration."""
        if output_dir is not None and overwrite:
            raise ValueError("Cannot use --output-dir and --overwrite together. Choose one.")
        if output_dir is not None and source_folder.resolve() == output_dir.resolve():
            raise ValueError("output_dir cannot be the same as source_folder")

    @staticmethod
    def validate_video_resolution(video_resolution: Optional[str]) -> None:
        """Validate video resolution format."""
        if video_resolution is None:
            return

        # Import parse_resolution to validate
        from compressy.utils.format import parse_resolution

        try:
            parse_resolution(video_resolution)
        except ValueError as e:
            raise ValueError(f"Invalid video resolution: {e}")
