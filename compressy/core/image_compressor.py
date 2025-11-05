from pathlib import Path
from typing import List

from compressy.core.config import CompressionConfig
from compressy.core.ffmpeg_executor import FFmpegExecutor

# ============================================================================
# Image Compressor
# ============================================================================


class ImageCompressor:
    """Handles image compression using FFmpeg."""

    def __init__(self, ffmpeg_executor: FFmpegExecutor, config: CompressionConfig):
        """
        Initialize image compressor.

        Args:
            ffmpeg_executor: FFmpeg executor instance
            config: Compression configuration
        """
        self.ffmpeg = ffmpeg_executor
        self.config = config

    def compress(self, in_path: Path, out_path: Path) -> None:
        """
        Compress an image file.

        Args:
            in_path: Path to input image file
            out_path: Path to output image file
        """
        ffmpeg_args = self._build_ffmpeg_args(in_path, out_path)
        self.ffmpeg.run_with_progress(
            ffmpeg_args,
            progress_interval=self.config.progress_interval,
            filename=in_path.name,
        )

    def _build_ffmpeg_args(self, in_path: Path, out_path: Path) -> List[str]:
        """
        Build FFmpeg arguments for image compression.

        Args:
            in_path: Input image path
            out_path: Output image path

        Returns:
            List of FFmpeg arguments
        """
        input_ext = in_path.suffix.lower()
        output_ext = out_path.suffix.lower()
        ffmpeg_args = ["-i", str(in_path)]

        # Check if we should convert to JPEG
        converting_to_jpeg = not self.config.preserve_format and output_ext in [
            ".jpg",
            ".jpeg",
        ]

        if converting_to_jpeg:
            # Convert all images to JPEG format
            # Handle transparency/alpha channel for PNG/WebP
            if input_ext in [".png", ".webp"]:
                # Remove alpha channel and convert to RGB for JPEG
                # JPEG doesn't support transparency
                if self.config.image_resize is not None and self.config.image_resize < 100:
                    resize_factor = self.config.image_resize / 100
                    ffmpeg_args.extend(
                        [
                            "-vf",
                            f"format=rgb24,scale=iw*{resize_factor}:ih*{resize_factor}:flags=lanczos",
                        ]
                    )
                else:
                    ffmpeg_args.extend(["-vf", "format=rgb24"])
            elif self.config.image_resize is not None and self.config.image_resize < 100:
                # JPEG input with resize
                resize_factor = self.config.image_resize / 100
                ffmpeg_args.extend(
                    [
                        "-vf",
                        f"scale=iw*{resize_factor}:ih*{resize_factor}:flags=lanczos",
                    ]
                )

            # JPEG quality mapping
            jpeg_quality = self._map_jpeg_quality()
            ffmpeg_q = int(2 + (31 - 2) * (100 - jpeg_quality) / 100)
            ffmpeg_q = max(2, min(31, ffmpeg_q))
            ffmpeg_args.extend(["-q:v", str(ffmpeg_q)])

        elif self.config.preserve_format:
            # Preserve original format - use format-specific compression
            if input_ext in [".jpg", ".jpeg"]:
                # JPEG quality mapping
                jpeg_quality = self._map_jpeg_quality()
                ffmpeg_q = int(2 + (31 - 2) * (100 - jpeg_quality) / 100)
                ffmpeg_q = max(2, min(31, ffmpeg_q))
                ffmpeg_args.extend(["-q:v", str(ffmpeg_q)])
            elif input_ext == ".png":
                # PNG compression - use compress_level (0-9) for zlib compression
                # Higher compression_level = better compression but slower
                # Map image_quality (0-100) to compression_level (0-9)
                # Lower quality = higher compression (more aggressive)
                # For PNG, we want to use maximum compression when quality is low
                compress_level = int(9 - (self.config.image_quality / 100) * 9)
                compress_level = max(0, min(9, compress_level))

                # PNG compression settings
                # Use compression_level for zlib compression
                # For better PNG compression, we should use compression_level >= 6 for good results
                # At quality 80, compress_level = 1 is too low - let's use a minimum of 6 for meaningful compression
                if compress_level < 6:
                    # Use at least level 6 for meaningful compression, or scale better
                    # Map quality 80-100 to compression_level 6-9
                    # Map quality 0-80 to compression_level 0-9
                    if self.config.image_quality >= 80:
                        compress_level = int(6 + ((self.config.image_quality - 80) / 20) * 3)  # 80->6, 100->9
                    else:
                        compress_level = int((self.config.image_quality / 80) * 6)  # 0->0, 80->6
                    compress_level = max(0, min(9, compress_level))

                # Use PNG encoder with compression level
                # prediction filters help but FFmpeg handles this automatically
                ffmpeg_args.extend(["-compression_level", str(compress_level)])
            elif input_ext == ".webp":
                # WebP quality mapping
                webp_quality = self._map_webp_quality()
                ffmpeg_args.extend(["-quality", str(webp_quality)])
            else:
                # Default: use quality parameter for other formats
                ffmpeg_q = (
                    int(2 + (31 - 2) * (100 - self.config.image_quality) / 100)
                    if self.config.image_quality <= 100
                    else 2
                )
                ffmpeg_args.extend(["-q:v", str(ffmpeg_q)])

            # Add resize filter if specified (only if not already added for JPEG conversion)
            if self.config.image_resize is not None and self.config.image_resize < 100:
                resize_factor = self.config.image_resize / 100
                ffmpeg_args.extend(
                    [
                        "-vf",
                        f"scale=iw*{resize_factor}:ih*{resize_factor}:flags=lanczos",
                    ]
                )

        # Add output arguments
        ffmpeg_args.extend(["-y", str(out_path)])

        return ffmpeg_args

    def _map_jpeg_quality(self) -> int:
        """Map image_quality (0-100) to JPEG quality (1-95)."""
        if self.config.image_quality >= 100:
            return 95
        elif self.config.image_quality >= 95:
            return self.config.image_quality - 5
        else:
            jpeg_quality = int((self.config.image_quality / 94) * 90)
            return max(1, min(90, jpeg_quality))

    def _map_webp_quality(self) -> int:
        """Map image_quality (0-100) to WebP quality (1-95)."""
        if self.config.image_quality >= 100:
            return 95
        elif self.config.image_quality >= 95:
            return self.config.image_quality - 5
        else:
            webp_quality = int((self.config.image_quality / 94) * 90)
            return max(1, min(90, webp_quality))
