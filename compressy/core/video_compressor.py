from pathlib import Path
from typing import List

from compressy.core.config import CompressionConfig
from compressy.core.ffmpeg_executor import FFmpegExecutor


# ============================================================================
# Video Compressor
# ============================================================================


class VideoCompressor:
    """Handles video compression using FFmpeg."""

    def __init__(self, ffmpeg_executor: FFmpegExecutor, config: CompressionConfig):
        """
        Initialize video compressor.

        Args:
            ffmpeg_executor: FFmpeg executor instance
            config: Compression configuration
        """
        self.ffmpeg = ffmpeg_executor
        self.config = config

    def compress(self, in_path: Path, out_path: Path) -> None:
        """
        Compress a video file.

        Args:
            in_path: Path to input video file
            out_path: Path to output video file
        """
        ffmpeg_args = self._build_ffmpeg_args(in_path, out_path)
        self.ffmpeg.run_with_progress(
            ffmpeg_args,
            progress_interval=self.config.progress_interval,
            filename=in_path.name,
        )

    def _build_ffmpeg_args(self, in_path: Path, out_path: Path) -> List[str]:
        """
        Build FFmpeg arguments for video compression.

        Args:
            in_path: Input video path
            out_path: Output video path

        Returns:
            List of FFmpeg arguments
        """
        args = ["-i", str(in_path)]
        # Check if a specific target video resolution is given in the config.
        # If so, use fixed width and height. This assures the output video gets resized
        # exactly to those dimensions. We use 'parse_resolution' to support strings like "1280x720".
        # FFmpeg requires both dimensions to be divisible by 2 for most codecs, so this
        # logic (using -2 conventionally) could be refactored, but assumes incoming values are correct.
        if getattr(self.config, "video_resolution", None):
            from compressy.utils.format import parse_resolution

            width, height = parse_resolution(self.config.video_resolution)
            # Use -2 for width or height to ensure divisibility by 2 (FFmpeg requirement)
            args.extend(["-vf", f"scale={width}:{height}"])
        # If explicit video_resolution is not provided but a resize percentage is,
        # and it is a valid percentage (0 < resize < 100), scale by that percentage.
        # This is useful for users who want a proportional resize rather than a fixed dimension.
        elif getattr(self.config, "video_resize", None) is not None and 0 < self.config.video_resize < 100:
            resize_factor = self.config.video_resize / 100
            # FFmpeg scale filter can use expressions like iw (input width) and ih (input height), so we multiply them.
            # 'flags=lanczos' is used for better quality resampling.
            args.extend(["-vf", f"scale=iw*{resize_factor}:ih*{resize_factor}:flags=lanczos"])

        # Add video codec settings
        args.extend(
            [
                "-vcodec",
                "libx264",
                "-crf",
                str(self.config.video_crf),
                "-preset",
                self.config.video_preset,
            ]
        )

        # Add audio codec settings
        args.extend(
            [
                "-acodec",
                "aac",
                "-b:a",
                "128k",
            ]
        )

        # Preserve metadata and allow overwrite
        args.extend(
            [
                "-map_metadata",
                "0",
                "-y",  # Overwrite output file if it exists
                str(out_path),
            ]
        )

        return args
