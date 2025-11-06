from pathlib import Path
from typing import List

from compressy.core.config import CompressionConfig
from compressy.core.ffmpeg_executor import FFmpegExecutor
from compressy.utils.logger import get_logger


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
        self.logger = get_logger()
        self.logger.debug(f"VideoCompressor initialized: crf={config.video_crf}, preset={config.video_preset}, resize={config.video_resize}")

    def compress(self, in_path: Path, out_path: Path) -> None:
        """
        Compress a video file.

        Args:
            in_path: Path to input video file
            out_path: Path to output video file
        """
        self.logger.debug(f"Compressing video: {in_path.name} -> {out_path.name}")
        ffmpeg_args = self._build_ffmpeg_args(in_path, out_path)
        self.logger.debug(f"FFmpeg args for {in_path.name}: {' '.join(ffmpeg_args)}")
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
        ffmpeg_args = ["-i", str(in_path)]
        
        # Add video resize filter if specified (and not 0 or 100)
        if self.config.video_resize is not None and 0 < self.config.video_resize < 100:
            resize_factor = self.config.video_resize / 100
            ffmpeg_args.extend([
                "-vf",
                f"scale=iw*{resize_factor}:ih*{resize_factor}:flags=lanczos"
            ])
        
        ffmpeg_args.extend([
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
        ])
        
        return ffmpeg_args
