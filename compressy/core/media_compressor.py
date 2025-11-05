import shutil
import time
import subprocess
from pathlib import Path
from typing import Dict, List
from compressy.core.config import CompressionConfig, ParameterValidator
from compressy.core.ffmpeg_executor import FFmpegExecutor
from compressy.core.video_compressor import VideoCompressor
from compressy.core.image_compressor import ImageCompressor
from compressy.utils.file_processor import FileProcessor
from compressy.services.statistics import StatisticsTracker
from compressy.services.backup import BackupManager
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
        
        # Collect files
        all_files = self._collect_files()
        
        if not all_files:
            print("No media files found to compress.")
            result = self.stats.get_stats()
            if not self.config.recursive:
                result.pop("folder_stats", None)
            return result
        
        # Setup compressed folder
        compressed_folder = self.config.source_folder / "compressed"
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
    
    def _collect_files(self) -> List[Path]:
        """Collect files to process based on recursive setting."""
        if self.config.recursive:
            return [
                f for f in self.config.source_folder.rglob("*")
                if f.suffix.lower() in self.video_exts + self.image_exts and f.is_file()
            ]
        else:
            return [
                f for f in self.config.source_folder.iterdir()
                if f.suffix.lower() in self.video_exts + self.image_exts and f.is_file()
            ]
    
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
    
    def _process_file(
        self,
        file_path: Path,
        idx: int,
        total_files: int,
        compressed_folder: Path
    ) -> None:
        """
        Process a single file.
        
        Args:
            file_path: Path to the file to process
            idx: Current file index
            total_files: Total number of files
            compressed_folder: Path to compressed folder
        """
        in_path = file_path
        out_path = self.file_processor.determine_output_path(
            file_path,
            self.config.source_folder,
            compressed_folder,
            self.config.overwrite
        )
        
        # If not preserving format and this is an image (not already JPEG), convert to JPEG
        if not self.config.preserve_format and file_path.suffix.lower() in self.image_exts:
            if file_path.suffix.lower() not in ['.jpg', '.jpeg']:
                # Change output extension to .jpg
                out_path = out_path.with_suffix('.jpg')
        
        folder_key = self._get_folder_key(file_path)
        original_size = in_path.stat().st_size
        
        # Add to total original size (but not total_files count - that's set once upfront)
        self.stats.add_total_file_size(original_size, folder_key)
        
        # Skip if already compressed and not overwriting
        if not self.config.overwrite and out_path.exists():
            existing_size = out_path.stat().st_size
            self.stats.update_stats(original_size, existing_size, 0, "skipped", folder_key)
            print(f"[{idx}/{total_files}] Skipping (already exists): {file_path.name} ({format_size(existing_size)})")
            return
        
        print(f"[{idx}/{total_files}] Processing: {file_path.name} ({format_size(original_size)})")
        
        # Track processing time
        file_start_time = time.time()
        
        try:
            # Compress based on file type
            if file_path.suffix.lower() in self.video_exts:
                self.video_compressor.compress(in_path, out_path)
            elif file_path.suffix.lower() in self.image_exts:
                self.image_compressor.compress(in_path, out_path)
            else:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")
            
            # Preserve timestamps
            self.file_processor.preserve_timestamps(in_path, out_path)
            
            # Get compressed size
            compressed_size = out_path.stat().st_size
            space_saved = original_size - compressed_size
            compression_ratio = (space_saved / original_size * 100) if original_size > 0 else 0
            
            # Check if compressed file is larger than original
            if compressed_size > original_size:
                if self.config.keep_if_larger:
                    print(f"  ⚠️  Warning: Compressed file is larger than original ({format_size(compressed_size)} > {format_size(original_size)})")
                else:
                    # Skip compressed version
                    if out_path.exists():
                        out_path.unlink()
                    
                    if not self.config.overwrite:
                        # Copy original to compressed folder
                        shutil.copy2(in_path, out_path)
                        self.file_processor.preserve_timestamps(in_path, out_path)
                        print(f"  ⚠️  Compressed file larger, copying original instead: {format_size(original_size)}")
                        
                        # Track as processed with no compression
                        file_processing_time = time.time() - file_start_time
                        file_info = {
                            "name": str(file_path.relative_to(self.config.source_folder)),
                            "original_size": original_size,
                            "compressed_size": original_size,
                            "space_saved": 0,
                            "compression_ratio": 0.0,
                            "processing_time": file_processing_time,
                            "status": "success (copied original)"
                        }
                        self.stats.add_file_info(file_info, folder_key)
                        self.stats.update_stats(original_size, original_size, 0, "processed", folder_key)
                    else:
                        # In overwrite mode, just skip
                        print(f"  ⚠️  Compressed file is larger ({format_size(compressed_size)} > {format_size(original_size)}), skipping...")
                        self.stats.update_stats(original_size, 0, 0, "skipped", folder_key)
                    return
            
            # Calculate processing time
            file_processing_time = time.time() - file_start_time
            
            # Update statistics
            self.stats.update_stats(original_size, compressed_size, space_saved, "processed", folder_key)
            
            file_info = {
                "name": str(file_path.relative_to(self.config.source_folder)),
                "original_size": original_size,
                "compressed_size": compressed_size,
                "space_saved": space_saved,
                "compression_ratio": compression_ratio,
                "processing_time": file_processing_time,
                "status": "success"
            }
            self.stats.add_file_info(file_info, folder_key)
            
            # Handle overwrite
            if self.config.overwrite and out_path.exists():
                self.file_processor.handle_overwrite(in_path, out_path)
            
            # Print result
            if compression_ratio < 0:
                print(f"  ⚠️  Compressed (larger): {format_size(original_size)} → {format_size(compressed_size)} "
                      f"({compression_ratio:.1f}% increase)")
            else:
                print(f"  ✓ Compressed: {format_size(original_size)} → {format_size(compressed_size)} "
                      f"({compression_ratio:.1f}% reduction)")
        
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Error processing {in_path}: FFmpeg error")
            file_processing_time = time.time() - file_start_time
            
            file_info = {
                "name": str(file_path.relative_to(self.config.source_folder)),
                "original_size": original_size,
                "compressed_size": 0,
                "space_saved": 0,
                "compression_ratio": 0,
                "processing_time": file_processing_time,
                "status": f"error: {str(e)}"
            }
            self.stats.add_file_info(file_info, folder_key)
            self.stats.update_stats(original_size, 0, 0, "error", folder_key)
            
            # Clean up failed output file
            if out_path.exists():
                out_path.unlink()
        
        except Exception as e:
            print(f"  ✗ Error processing {in_path}: {e}")
            file_processing_time = time.time() - file_start_time
            
            file_info = {
                "name": str(file_path.relative_to(self.config.source_folder)),
                "original_size": original_size,
                "compressed_size": 0,
                "space_saved": 0,
                "compression_ratio": 0,
                "processing_time": file_processing_time,
                "status": f"error: {str(e)}"
            }
            self.stats.add_file_info(file_info, folder_key)
            self.stats.update_stats(original_size, 0, 0, "error", folder_key)
            
            # Clean up failed output file
            if out_path.exists():
                out_path.unlink()

