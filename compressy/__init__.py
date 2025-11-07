"""
Compressy - Media compression tool for videos and images.
"""

__version__ = "0.1.0"

# Package-level exports for convenience
from compressy.cli import main
from compressy.core.config import CompressionConfig, ParameterValidator
from compressy.core.ffmpeg_executor import FFmpegExecutor
from compressy.core.image_compressor import ImageCompressor
from compressy.core.media_compressor import MediaCompressor
from compressy.core.video_compressor import VideoCompressor
from compressy.services.backup import BackupManager
from compressy.services.reports import ReportGenerator
from compressy.services.statistics import StatisticsManager, StatisticsTracker
from compressy.utils.file_processor import FileProcessor
from compressy.utils.format import format_size, parse_resolution, parse_size


__all__ = [
    "CompressionConfig",
    "ParameterValidator",
    "MediaCompressor",
    "VideoCompressor",
    "ImageCompressor",
    "FFmpegExecutor",
    "ReportGenerator",
    "StatisticsManager",
    "StatisticsTracker",
    "BackupManager",
    "FileProcessor",
    "format_size",
    "parse_size",
    "parse_resolution",
    "main",
]
