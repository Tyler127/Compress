from pathlib import Path
from typing import List

from compressy.core.config import CompressionConfig
from compressy.core.ffmpeg_executor import FFmpegExecutor
from compressy.utils.logger import get_logger


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
        self.logger = get_logger()
        self.logger.debug(
            f"ImageCompressor initialized: quality={config.image_quality}, "
            f"resize={config.image_resize}, preserve_format={config.preserve_format}"
        )

    def compress(self, in_path: Path, out_path: Path) -> None:
        """
        Compress an image file.

        Args:
            in_path: Path to input image file
            out_path: Path to output image file
        """
        self.logger.debug(f"Compressing image: {in_path.name} -> {out_path.name}")
        ffmpeg_args = self._build_ffmpeg_args(in_path, out_path)
        self.logger.debug(f"FFmpeg args for {in_path.name}: {' '.join(ffmpeg_args)}")
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

        if self._should_convert_to_jpeg(output_ext):
            ffmpeg_args.extend(self._jpeg_conversion_args(input_ext))
        elif self.config.preserve_format:
            ffmpeg_args.extend(self._preserve_format_args(input_ext))

        ffmpeg_args.extend(["-y", str(out_path)])
        return ffmpeg_args

    def _should_convert_to_jpeg(self, output_ext: str) -> bool:
        return not self.config.preserve_format and output_ext in {".jpg", ".jpeg"}

    def _jpeg_conversion_args(self, input_ext: str) -> List[str]:
        args: List[str] = []
        filters: List[str] = []

        if input_ext in {".png", ".webp"}:
            filters.append("format=rgb24")
        if self._should_resize():
            filters.append(self._resize_filter_expression())

        args.extend(self._build_filter_args(filters))
        args.extend(["-q:v", str(self._jpeg_quality_value())])
        return args

    def _preserve_format_args(self, input_ext: str) -> List[str]:
        args: List[str] = []

        if input_ext in {".jpg", ".jpeg"}:
            args.extend(["-q:v", str(self._jpeg_quality_value())])
        elif input_ext == ".png":
            args.extend(["-compression_level", str(self._calculate_png_compression_level())])
        elif input_ext == ".webp":
            args.extend(["-quality", str(self._map_webp_quality())])
        else:
            args.extend(["-q:v", str(self._generic_quality_value())])

        args.extend(self._resize_filter_args())
        return args

    def _should_resize(self) -> bool:
        return self.config.image_resize is not None and self.config.image_resize < 100

    def _resize_filter_expression(self) -> str:
        resize_factor = self.config.image_resize / 100
        return f"scale=iw*{resize_factor}:ih*{resize_factor}:flags=lanczos"

    def _resize_filter_args(self) -> List[str]:
        if not self._should_resize():
            return []
        return ["-vf", self._resize_filter_expression()]

    @staticmethod
    def _build_filter_args(filters: List[str]) -> List[str]:
        if not filters:
            return []
        return ["-vf", ",".join(filters)]

    def _jpeg_quality_value(self) -> int:
        jpeg_quality = self._map_jpeg_quality()
        ffmpeg_q = int(2 + (31 - 2) * (100 - jpeg_quality) / 100)
        return max(2, min(31, ffmpeg_q))

    def _generic_quality_value(self) -> int:
        if self.config.image_quality <= 100:
            ffmpeg_q = int(2 + (31 - 2) * (100 - self.config.image_quality) / 100)
        else:
            ffmpeg_q = 2
        return max(2, min(31, ffmpeg_q))

    def _calculate_png_compression_level(self) -> int:
        compress_level = int(9 - (self.config.image_quality / 100) * 9)
        compress_level = max(0, min(9, compress_level))

        if compress_level < 6:
            if self.config.image_quality >= 80:
                compress_level = int(6 + ((self.config.image_quality - 80) / 20) * 3)
            else:
                compress_level = int((self.config.image_quality / 80) * 6)
            compress_level = max(0, min(9, compress_level))

        return compress_level

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
