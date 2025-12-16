import shutil
import subprocess  # nosec B404
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from compressy.core.config import CompressionConfig, ParameterValidator
from compressy.core.ffmpeg_executor import FFmpegExecutor
from compressy.core.image_compressor import ImageCompressor
from compressy.core.video_compressor import VideoCompressor
from compressy.services.backup import BackupManager
from compressy.services.statistics import StatisticsTracker
from compressy.utils.file_processor import FileProcessor
from compressy.utils.format import format_size


# ============================================================================
# Media Compressor
# ============================================================================


class MediaCompressor:
    """Main orchestrator for media compression."""

    def __init__(self, config: CompressionConfig):
        """
        Initialize media compressor with configuration.

        Args:
            config: Compression configuration
        """
        self.config = config
        self.ffmpeg = FFmpegExecutor(config.ffmpeg_path)
        self.video_compressor = VideoCompressor(self.ffmpeg, config)
        self.image_compressor = ImageCompressor(self.ffmpeg, config)
        self.file_processor = FileProcessor()
        self.stats = StatisticsTracker(config.recursive)
        self.backup_manager = BackupManager() if config.backup_dir else None

        # File extension lists
        self.video_exts = [".mp4", ".mov", ".mkv", ".avi"]
        self.image_exts = [".jpg", ".jpeg", ".png", ".webp"]

    def compress(self) -> Dict:
        """
        Execute compression workflow.

        Returns:
            Dictionary with compression statistics
        """
        # Validate parameters
        ParameterValidator.validate(self.config)

        # Validate source folder exists
        if not self.config.source_folder.exists():
            raise FileNotFoundError(f"Source folder does not exist: {self.config.source_folder}")

        # Create backup if specified
        if self.backup_manager and self.config.backup_dir:
            self.backup_manager.create_backup(self.config.source_folder, self.config.backup_dir)

        # Track total processing time
        start_time = time.time()

        # Setup compressed folder (determine before collecting files to exclude it)
        if self.config.output_dir:
            compressed_folder = self.config.output_dir
        else:
            compressed_folder = self.config.source_folder / "compressed"

        # Collect files (exclude files in compressed folder)
        all_files = self._collect_files(compressed_folder)

        if not all_files:
            print("No media files found to compress.")
            result = self.stats.get_stats()
            if not self.config.recursive:
                result.pop("folder_stats", None)
            return result

        if not self.config.overwrite:
            compressed_folder.mkdir(parents=True, exist_ok=True)

        total_files_count = len(all_files)
        # Set total_files once - this represents all files found upfront
        self.stats.stats["total_files"] = total_files_count
        print(f"Found {total_files_count} media file(s) to process...")

        # Process each file
        for idx, file_path in enumerate(all_files, 1):
            self._process_file(file_path, idx, total_files_count, compressed_folder)

        # Set total processing time
        total_processing_time = time.time() - start_time
        self.stats.set_total_processing_time(total_processing_time)

        return self.stats.get_stats()

    def _collect_files(self, compressed_folder: Optional[Path] = None) -> List[Path]:
        """
        Collect files to process based on recursive setting and size filters.

        Args:
            compressed_folder: Path to compressed folder to exclude from collection.
                               If None or overwrite mode, no exclusion is performed.

        Returns:
            List of file paths to process
        """
        files = self._gather_media_files()
        files = self._exclude_compressed_folder_files(files, compressed_folder)
        files = self._apply_size_filters(files)
        return files

    def _gather_media_files(self) -> List[Path]:
        """
        Gather media files from source folder based on recursive setting.

        Returns:
            List of media file paths
        """
        media_exts = self.video_exts + self.image_exts
        if self.config.recursive:
            return [f for f in self.config.source_folder.rglob("*") if f.suffix.lower() in media_exts and f.is_file()]
        return [f for f in self.config.source_folder.iterdir() if f.suffix.lower() in media_exts and f.is_file()]

    def _exclude_compressed_folder_files(self, files: List[Path], compressed_folder: Optional[Path]) -> List[Path]:
        """
        Exclude files that are inside the compressed folder.

        Args:
            files: List of file paths to filter
            compressed_folder: Path to compressed folder to exclude

        Returns:
            Filtered list of file paths
        """
        if compressed_folder is None or self.config.overwrite:
            return files

        try:
            compressed_folder_abs = compressed_folder.resolve()
            return [f for f in files if not self._is_file_in_folder(f, compressed_folder_abs)]
        except (OSError, ValueError):
            # If compressed folder path resolution fails, continue without exclusion
            return files

    def _is_file_in_folder(self, file_path: Path, folder_path: Path) -> bool:
        """
        Check if a file is inside a folder.

        Args:
            file_path: Path to the file
            folder_path: Path to the folder

        Returns:
            True if file is inside folder, False otherwise
        """
        try:
            file_path_abs = file_path.resolve()
            folder_path_abs = folder_path.resolve()

            # Use is_relative_to for Python 3.9+, fallback for older versions
            if hasattr(file_path_abs, "is_relative_to"):
                return file_path_abs.is_relative_to(folder_path_abs)

            # Fallback: check if folder is a parent by using relative_to
            try:
                file_path_abs.relative_to(folder_path_abs)
                return True
            except ValueError:
                return False
        except (ValueError, AttributeError, OSError):
            # If comparison fails, assume file is not in folder to be safe
            return False

    def _apply_size_filters(self, files: List[Path]) -> List[Path]:
        """
        Apply min and max size filters to file list.

        Args:
            files: List of file paths to filter

        Returns:
            Filtered list of file paths
        """
        if self.config.min_size is None and self.config.max_size is None:
            return files

        filtered_files = []
        for f in files:
            try:
                file_size = f.stat().st_size

                # Check min_size
                if self.config.min_size is not None and file_size < self.config.min_size:
                    continue

                # Check max_size
                if self.config.max_size is not None and file_size > self.config.max_size:
                    continue

                filtered_files.append(f)
            except (OSError, FileNotFoundError):
                # Skip files that can't be accessed
                continue

        return filtered_files

    def _get_folder_key(self, file_path: Path) -> str:
        """Get folder key for recursive mode statistics."""
        if not self.config.recursive:
            return "root"

        try:
            folder_path = file_path.parent.relative_to(self.config.source_folder)
            folder_key = str(folder_path) if str(folder_path) != "." else "root"
        except ValueError:
            folder_key = "root"

        return folder_key

    def _process_file(self, file_path: Path, idx: int, total_files: int, compressed_folder: Path) -> None:
        """
        Process a single file.

        Args:
            file_path: Path to the file to process
            idx: Current file index
            total_files: Total number of files
            compressed_folder: Path to compressed folder
        """
        in_path, out_path = self._resolve_paths(file_path, compressed_folder)
        folder_key = self._get_folder_key(file_path)
        original_size = in_path.stat().st_size
        self.stats.add_total_file_size(original_size, folder_key)

        file_start_time = time.time()
        file_type, file_extension = self._identify_file(file_path)
        if file_type is None:
            self._handle_unsupported_type(
                file_path,
                in_path,
                out_path,
                original_size,
                folder_key,
                file_start_time,
            )
            return

        if self._should_skip_existing(
            file_path, out_path, original_size, folder_key, file_type, file_extension, idx, total_files
        ):
            return

        print(f"[{idx}/{total_files}] Processing: {file_path.name} ({format_size(original_size)})")

        try:
            self._compress_by_type(file_type, in_path, out_path)
            if self.config.preserve_timestamps:
                self.file_processor.preserve_timestamps(in_path, out_path)

            compressed_size = out_path.stat().st_size
            file_processing_time = time.time() - file_start_time

            if self._handle_larger_file_if_needed(
                in_path,
                out_path,
                original_size,
                compressed_size,
                file_processing_time,
                folder_key,
                file_type,
                file_extension,
            ):
                return

            self._finalize_success(
                file_path,
                in_path,
                out_path,
                original_size,
                compressed_size,
                file_processing_time,
                folder_key,
                file_type,
                file_extension,
            )

        except subprocess.CalledProcessError as error:
            self._handle_subprocess_error(
                error,
                file_path,
                in_path,
                out_path,
                original_size,
                folder_key,
                file_type,
                file_extension,
                file_start_time,
            )
        except Exception as error:
            self._handle_general_error(
                error,
                file_path,
                in_path,
                out_path,
                original_size,
                folder_key,
                file_type,
                file_extension,
                file_start_time,
            )

    def _resolve_paths(self, file_path: Path, compressed_folder: Path) -> Tuple[Path, Path]:
        in_path = file_path
        out_path = self.file_processor.determine_output_path(
            file_path,
            self.config.source_folder,
            compressed_folder,
            self.config.overwrite,
        )

        if (
            not self.config.preserve_format
            and file_path.suffix.lower() in self.image_exts
            and file_path.suffix.lower() not in [".jpg", ".jpeg"]
        ):
            out_path = out_path.with_suffix(".jpg")

        return in_path, out_path

    def _identify_file(self, file_path: Path) -> (Optional[str], Optional[str]):
        suffix = file_path.suffix.lower()
        if suffix in self.video_exts:
            file_type = "video"
        elif suffix in self.image_exts:
            file_type = "image"
        else:
            file_type = None
        file_extension = suffix.lstrip(".") if suffix else None
        return file_type, file_extension

    def _should_skip_existing(
        self,
        file_path: Path,
        out_path: Path,
        original_size: int,
        folder_key: str,
        file_type: Optional[str],
        file_extension: Optional[str],
        idx: int,
        total_files: int,
    ) -> bool:
        if self.config.overwrite or not out_path.exists():
            return False

        existing_size = out_path.stat().st_size
        self.stats.update_stats(original_size, existing_size, 0, "skipped", folder_key, file_type, file_extension)
        print(f"[{idx}/{total_files}] Skipping (already exists): {file_path.name} ({format_size(existing_size)})")
        return True

    def _compress_by_type(self, file_type: str, in_path: Path, out_path: Path) -> None:
        if file_type == "video":
            self.video_compressor.compress(in_path, out_path)
        elif file_type == "image":
            self.image_compressor.compress(in_path, out_path)
        else:
            raise ValueError(f"Unsupported file type: {in_path.suffix}")

    def _handle_larger_file_if_needed(
        self,
        in_path: Path,
        out_path: Path,
        original_size: int,
        compressed_size: int,
        file_processing_time: float,
        folder_key: str,
        file_type: Optional[str],
        file_extension: Optional[str],
    ) -> bool:
        if compressed_size <= original_size:
            return False

        if self.config.keep_if_larger:
            message = "  ⚠️  Warning: Compressed file is larger than original"
            message += f" ({format_size(compressed_size)} > {format_size(original_size)})"
            print(message)
            return False

        self._handle_larger_replacement(
            in_path,
            out_path,
            original_size,
            compressed_size,
            file_processing_time,
            folder_key,
            file_type,
            file_extension,
        )
        return True

    def _handle_larger_replacement(
        self,
        in_path: Path,
        out_path: Path,
        original_size: int,
        compressed_size: int,
        file_processing_time: float,
        folder_key: str,
        file_type: Optional[str],
        file_extension: Optional[str],
    ) -> None:
        if out_path.exists():
            out_path.unlink()

        if not self.config.overwrite:
            if self.config.preserve_timestamps:
                shutil.copy2(in_path, out_path)
                self.file_processor.preserve_timestamps(in_path, out_path)
            else:
                shutil.copy(in_path, out_path)
            print(f"  ⚠️  Compressed file larger, copying original instead: {format_size(original_size)}")

            file_info = self._build_file_info(
                in_path,
                original_size,
                original_size,
                0,
                0.0,
                file_processing_time,
                "success (copied original)",
                file_type,
                file_extension,
            )
            self.stats.add_file_info(file_info, folder_key)
            self.stats.update_stats(original_size, original_size, 0, "processed", folder_key, file_type, file_extension)
        else:
            message = "  ⚠️  Compressed file is larger"
            message += f" ({format_size(compressed_size)} > {format_size(original_size)}), skipping..."
            print(message)
            self.stats.update_stats(original_size, 0, 0, "skipped", folder_key, file_type, file_extension)

    def _finalize_success(
        self,
        file_path: Path,
        in_path: Path,
        out_path: Path,
        original_size: int,
        compressed_size: int,
        file_processing_time: float,
        folder_key: str,
        file_type: Optional[str],
        file_extension: Optional[str],
    ) -> None:
        space_saved = original_size - compressed_size
        compression_ratio = (space_saved / original_size * 100) if original_size > 0 else 0

        self.stats.update_stats(
            original_size, compressed_size, space_saved, "processed", folder_key, file_type, file_extension
        )

        file_info = self._build_file_info(
            in_path,
            original_size,
            compressed_size,
            space_saved,
            compression_ratio,
            file_processing_time,
            "success",
            file_type,
            file_extension,
        )
        self.stats.add_file_info(file_info, folder_key)

        if self.config.overwrite and out_path.exists():
            self.file_processor.handle_overwrite(in_path, out_path)

        if compression_ratio < 0:
            print(
                f"  ⚠️  Compressed (larger): {format_size(original_size)} → {format_size(compressed_size)} "
                f"({compression_ratio:.1f}% increase)"
            )
        else:
            print(
                f"  ✓ Compressed: {format_size(original_size)} → {format_size(compressed_size)} "
                f"({compression_ratio:.1f}% reduction)"
            )

    def _build_file_info(
        self,
        in_path: Path,
        original_size: int,
        compressed_size: int,
        space_saved: int,
        compression_ratio: float,
        processing_time: float,
        status: str,
        file_type: Optional[str],
        file_extension: Optional[str],
    ) -> Dict:
        return {
            "name": str(in_path.relative_to(self.config.source_folder)),
            "original_size": original_size,
            "compressed_size": compressed_size,
            "space_saved": space_saved,
            "compression_ratio": compression_ratio,
            "processing_time": processing_time,
            "status": status,
            "file_type": file_type,
            "file_extension": file_extension,
        }

    def _handle_subprocess_error(
        self,
        error: subprocess.CalledProcessError,
        file_path: Path,
        in_path: Path,
        out_path: Path,
        original_size: int,
        folder_key: str,
        file_type: Optional[str],
        file_extension: Optional[str],
        file_start_time: float,
    ) -> None:
        print(f"  ✗ Error processing {in_path}: FFmpeg error")
        self._record_failure(
            error,
            file_path,
            original_size,
            folder_key,
            file_type,
            file_extension,
            file_start_time,
        )
        self._cleanup_output(out_path)

    def _handle_general_error(
        self,
        error: Exception,
        file_path: Path,
        in_path: Path,
        out_path: Path,
        original_size: int,
        folder_key: str,
        file_type: Optional[str],
        file_extension: Optional[str],
        file_start_time: float,
    ) -> None:
        print(f"  ✗ Error processing {in_path}: {error}")
        self._record_failure(
            error,
            file_path,
            original_size,
            folder_key,
            file_type,
            file_extension,
            file_start_time,
        )
        self._cleanup_output(out_path)

    def _record_failure(
        self,
        error: Exception,
        file_path: Path,
        original_size: int,
        folder_key: str,
        file_type: Optional[str],
        file_extension: Optional[str],
        file_start_time: float,
    ) -> None:
        file_processing_time = time.time() - file_start_time
        file_info = {
            "name": str(file_path.relative_to(self.config.source_folder)),
            "original_size": original_size,
            "file_type": file_type,
            "file_extension": file_extension,
            "compressed_size": 0,
            "space_saved": 0,
            "compression_ratio": 0,
            "processing_time": file_processing_time,
            "status": f"error: {str(error)}",
        }
        self.stats.add_file_info(file_info, folder_key)
        self.stats.update_stats(original_size, 0, 0, "error", folder_key, file_type, file_extension)

    @staticmethod
    def _cleanup_output(out_path: Path) -> None:
        if out_path.exists():
            out_path.unlink()

    def _handle_unsupported_type(
        self,
        file_path: Path,
        in_path: Path,
        out_path: Path,
        original_size: int,
        folder_key: str,
        file_start_time: float,
    ) -> None:
        error = ValueError(f"Unsupported file type: {file_path.suffix}")
        print(f"  ✗ Error processing {in_path}: {error}")
        file_extension = file_path.suffix.lstrip(".") if file_path.suffix else None
        self._record_failure(error, file_path, original_size, folder_key, None, file_extension, file_start_time)
        self._cleanup_output(out_path)
