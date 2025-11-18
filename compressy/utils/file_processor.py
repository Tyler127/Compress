import os
import shutil
from pathlib import Path

from compressy.utils.logger import get_logger


# ============================================================================
# File Processor
# ============================================================================


class FileProcessor:
    """Handles file operations like path management and timestamp preservation."""

    @staticmethod
    def preserve_timestamps(src: Path, dst: Path) -> None:
        """Preserve file timestamps from source to destination."""
        logger = get_logger()
        try:
            st = src.stat()
            os.utime(dst, (st.st_atime, st.st_mtime))  # access, modified
            shutil.copystat(src, dst)  # copies creation time on Windows too
            logger.debug(f"Preserved timestamps for {dst.name}")
        except Exception as e:
            logger.warning(f"Failed to preserve timestamps for {dst.name}: {e}")

    @staticmethod
    def determine_output_path(source_file: Path, source_folder: Path, compressed_folder: Path, overwrite: bool) -> Path:
        """
        Determine the output path for a file.

        Args:
            source_file: Path to the source file
            source_folder: Path to the source folder
            compressed_folder: Path to the compressed folder
            overwrite: Whether to overwrite original files

        Returns:
            Path to the output file
        """
        logger = get_logger()
        if overwrite:
            out_path = source_file.parent / (source_file.stem + "_tmp" + source_file.suffix)
            logger.debug(f"Output path (overwrite mode): {out_path}")
            return out_path
        else:
            relative_path = source_file.relative_to(source_folder)
            out_path = compressed_folder / relative_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Output path (compressed folder): {out_path}")
            return out_path

    @staticmethod
    def handle_overwrite(original_path: Path, temp_path: Path) -> None:
        """Handle file overwrite by replacing original with temp file."""
        logger = get_logger()
        if temp_path.exists():
            temp_path.replace(original_path)
            logger.debug(f"Replaced original file with compressed version: {original_path.name}")
