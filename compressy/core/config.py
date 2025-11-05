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
    image_quality: int = 100
    image_resize: Optional[int] = None
    recursive: bool = False
    overwrite: bool = False
    ffmpeg_path: Optional[str] = None
    progress_interval: float = 5.0
    keep_if_larger: bool = False
    backup_dir: Optional[Path] = None
    preserve_format: bool = False


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
        ParameterValidator.validate_image_resize(config.image_resize)

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
    def validate_image_resize(image_resize: Optional[int]) -> None:
        """Validate image resize value."""
        if image_resize is not None and not (1 <= image_resize <= 100):
            raise ValueError(f"image_resize must be between 1 and 100, got {image_resize}")
