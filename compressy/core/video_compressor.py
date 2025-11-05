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
        return [
            "-i",
            str(in_path),
            "-vcodec",
            "libx264",
            "-crf",
            str(self.config.video_crf),
            "-preset",
            self.config.video_preset,
            "-acodec",
            "aac",
            "-b:a",
            "128k",
            "-map_metadata",
            "0",
            "-y",  # Overwrite output file if it exists
            str(out_path),
        ]
