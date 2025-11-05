import os
import subprocess
import shutil
import argparse
import csv
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


# ============================================================================
# MARK: Configuration Classes
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
# MARK: Utility Functions
# ============================================================================

def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


# ============================================================================
# MARK: Parameter Validator
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
        valid_presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", 
                         "slow", "slower", "veryslow"]
        if video_preset not in valid_presets:
            raise ValueError(f"video_preset must be one of {valid_presets}, got {video_preset}")
    
    @staticmethod
    def validate_image_resize(image_resize: Optional[int]) -> None:
        """Validate image resize value."""
        if image_resize is not None and not (1 <= image_resize <= 100):
            raise ValueError(f"image_resize must be between 1 and 100, got {image_resize}")


# ============================================================================
# MARK: FFmpeg Executor
# ============================================================================

class FFmpegExecutor:
    """Handles FFmpeg execution and progress tracking."""
    
    def __init__(self, ffmpeg_path: Optional[str] = None):
        """
        Initialize FFmpeg executor.
        
        Args:
            ffmpeg_path: Path to FFmpeg executable. If None, will attempt to find it.
        """
        self.ffmpeg_path = ffmpeg_path or self.find_ffmpeg()
        if self.ffmpeg_path is None:
            raise FileNotFoundError(
                "FFmpeg not found. Please install FFmpeg and add it to PATH, "
                "or specify the path using --ffmpeg-path option."
            )
    
    @staticmethod
    def find_ffmpeg() -> Optional[str]:
        """Find FFmpeg executable in PATH or common locations."""
        # Try finding in PATH first
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return ffmpeg_path
        
        # Try common Windows locations
        common_paths = [
            r"C:\ffmpeg\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return path
        
        return None
    
    @staticmethod
    def parse_progress(line: str) -> Optional[Dict[str, str]]:
        """Parse FFmpeg progress line from stderr."""
        progress = {}
        
        # Extract frame number
        frame_match = re.search(r'frame=\s*(\d+)', line)
        if frame_match:
            progress['frame'] = frame_match.group(1)
        
        # Extract fps
        fps_match = re.search(r'fps=\s*([\d.]+)', line)
        if fps_match:
            progress['fps'] = fps_match.group(1)
        
        # Extract time
        time_match = re.search(r'time=(\d{2}:\d{2}:\d{2}\.\d{2})', line)
        if time_match:
            progress['time'] = time_match.group(1)
        
        # Extract bitrate
        bitrate_match = re.search(r'bitrate=\s*([\d.]+kbits/s|[\d.]+Mbits/s)', line)
        if bitrate_match:
            progress['bitrate'] = bitrate_match.group(1)
        
        # Extract size
        size_match = re.search(r'size=\s*(\d+[kKmMgG]?B)', line)
        if size_match:
            progress['size'] = size_match.group(1)
        
        # Extract speed
        speed_match = re.search(r'speed=\s*([\d.]+x)', line)
        if speed_match:
            progress['speed'] = speed_match.group(1)
        
        return progress if progress else None
    
    def run_with_progress(
        self,
        args: List[str],
        progress_interval: float = 5.0,
        filename: str = ""
    ) -> subprocess.CompletedProcess:
        """
        Run FFmpeg with live progress updates.
        
        Args:
            args: List of FFmpeg arguments
            progress_interval: Seconds between progress updates
            filename: Filename being processed (for display)
        
        Returns:
            CompletedProcess from subprocess
        """
        cmd = [self.ffmpeg_path] + args
        
        # Start FFmpeg process with unbuffered stderr
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=0  # Unbuffered for real-time reading
        )
        
        last_update_time = time.time()
        last_progress = None
        
        # Read stderr while process is running
        stderr_lines = []
        while process.poll() is None:
            line = process.stderr.readline()
            if line:
                stderr_lines.append(line.rstrip())
                # Parse progress information
                progress = self.parse_progress(line)
                
                if progress:
                    last_progress = progress
                    current_time = time.time()
                    
                    # Display progress update if interval has passed
                    if current_time - last_update_time >= progress_interval:
                        progress_str = f"  [Progress] "
                        if 'time' in progress:
                            progress_str += f"Time: {progress['time']} | "
                        if 'frame' in progress:
                            progress_str += f"Frame: {progress['frame']} | "
                        if 'fps' in progress:
                            progress_str += f"FPS: {progress['fps']} | "
                        if 'bitrate' in progress:
                            progress_str += f"Bitrate: {progress['bitrate']} | "
                        if 'size' in progress:
                            progress_str += f"Size: {progress['size']} | "
                        if 'speed' in progress:
                            progress_str += f"Speed: {progress['speed']}"
                        
                        print(progress_str)
                        last_update_time = current_time
            time.sleep(0.1)  # Small sleep to avoid busy waiting
        
        # Get remaining stderr and stdout output
        stdout, remaining_stderr = process.communicate()
        if remaining_stderr:
            for line in remaining_stderr.splitlines():
                if line.strip():
                    stderr_lines.append(line.rstrip())
                    # Check for final progress update
                    progress = self.parse_progress(line)
                    if progress:
                        last_progress = progress
        
        stderr = '\n'.join(stderr_lines)
        
        # Create CompletedProcess-like object
        result = subprocess.CompletedProcess(
            cmd,
            process.returncode,
            stdout,
            stderr
        )
        
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd, stdout, stderr)
        
        return result


# ============================================================================
# MARK: File Processor
# ============================================================================

class FileProcessor:
    """Handles file operations like path management and timestamp preservation."""
    
    @staticmethod
    def preserve_timestamps(src: Path, dst: Path) -> None:
        """Preserve file timestamps from source to destination."""
        st = src.stat()
        os.utime(dst, (st.st_atime, st.st_mtime))  # access, modified
        shutil.copystat(src, dst)  # copies creation time on Windows too
    
    @staticmethod
    def determine_output_path(
        source_file: Path,
        source_folder: Path,
        compressed_folder: Path,
        overwrite: bool
    ) -> Path:
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
        if overwrite:
            return source_file.parent / (source_file.stem + "_tmp" + source_file.suffix)
        else:
            relative_path = source_file.relative_to(source_folder)
            out_path = compressed_folder / relative_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            return out_path
    
    @staticmethod
    def handle_overwrite(original_path: Path, temp_path: Path) -> None:
        """Handle file overwrite by replacing original with temp file."""
        if temp_path.exists():
            temp_path.replace(original_path)


# ============================================================================
# MARK: Statistics Tracker
# ============================================================================

class StatisticsTracker:
    """Tracks compression statistics."""
    
    def __init__(self, recursive: bool = False):
        """
        Initialize statistics tracker.
        
        Args:
            recursive: Whether to track per-folder statistics
        """
        self.recursive = recursive
        self.stats = {
            "total_files": 0,
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "space_saved": 0,
            "files": []
        }
        
        if recursive:
            self.stats["folder_stats"] = {}
    
    def initialize_folder_stats(self, folder_key: str) -> None:
        """Initialize statistics for a folder."""
        if self.recursive and folder_key not in self.stats["folder_stats"]:
            self.stats["folder_stats"][folder_key] = {
                "total_files": 0,
                "processed": 0,
                "skipped": 0,
                "errors": 0,
                "total_original_size": 0,
                "total_compressed_size": 0,
                "space_saved": 0,
                "files": []
            }
    
    def add_file_info(
        self,
        file_info: Dict,
        folder_key: str = "root"
    ) -> None:
        """
        Add file information to statistics.
        
        Args:
            file_info: Dictionary with file information
            folder_key: Folder key for recursive mode
        """
        self.stats["files"].append(file_info)
        
        if self.recursive:
            self.initialize_folder_stats(folder_key)
            self.stats["folder_stats"][folder_key]["files"].append(file_info)
    
    def update_stats(
        self,
        original_size: int,
        compressed_size: int,
        space_saved: int,
        status: str,
        folder_key: str = "root"
    ) -> None:
        """
        Update statistics with file processing results.
        
        Args:
            original_size: Original file size
            compressed_size: Compressed file size
            space_saved: Space saved
            status: Processing status ("success", "skipped", "error")
            folder_key: Folder key for recursive mode
        """
        if status == "processed":
            self.stats["processed"] += 1
            self.stats["total_compressed_size"] += compressed_size
            self.stats["space_saved"] += space_saved
            
            if self.recursive:
                self.initialize_folder_stats(folder_key)
                self.stats["folder_stats"][folder_key]["processed"] += 1
                self.stats["folder_stats"][folder_key]["total_compressed_size"] += compressed_size
                self.stats["folder_stats"][folder_key]["space_saved"] += space_saved
        elif status == "skipped":
            self.stats["skipped"] += 1
            self.stats["total_compressed_size"] += compressed_size
            
            if self.recursive:
                self.initialize_folder_stats(folder_key)
                self.stats["folder_stats"][folder_key]["skipped"] += 1
                self.stats["folder_stats"][folder_key]["total_compressed_size"] += compressed_size
        elif status == "error":
            self.stats["errors"] += 1
            
            if self.recursive:
                self.initialize_folder_stats(folder_key)
                self.stats["folder_stats"][folder_key]["errors"] += 1
    
    def add_total_file(self, original_size: int, folder_key: str = "root") -> None:
        """Add a file to total count."""
        self.stats["total_files"] += 1
        self.stats["total_original_size"] += original_size
        
        if self.recursive:
            self.initialize_folder_stats(folder_key)
            self.stats["folder_stats"][folder_key]["total_files"] += 1
            self.stats["folder_stats"][folder_key]["total_original_size"] += original_size
    
    def set_total_processing_time(self, total_time: float) -> None:
        """Set total processing time."""
        self.stats["total_processing_time"] = total_time
    
    def get_stats(self) -> Dict:
        """Get all statistics."""
        return self.stats


# ============================================================================
# MARK: Backup Manager
# ============================================================================

class BackupManager:
    """Handles backup operations."""
    
    @staticmethod
    def create_backup(source_folder: Path, backup_dir: Path) -> Path:
        """
        Create a backup of the source folder in the backup directory.
        
        Args:
            source_folder: Path to the source folder to backup
            backup_dir: Path to the backup directory
        
        Returns:
            Path to the created backup folder
        """
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create backup folder with the same name as source folder
        backup_folder_name = source_folder.name
        backup_path = backup_dir / backup_folder_name
        
        # If backup already exists, add a timestamp to make it unique
        if backup_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{backup_folder_name}_{timestamp}"
        
        print(f"Creating backup to: {backup_path}")
        print("This may take a while for large folders...")
        
        # Copy entire directory tree
        shutil.copytree(source_folder, backup_path, dirs_exist_ok=False)
        
        print(f"✓ Backup created successfully: {backup_path}")
        return backup_path


# ============================================================================
# MARK: Video Compressor
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
            filename=in_path.name
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
            "-i", str(in_path),
            "-vcodec", "libx264",
            "-crf", str(self.config.video_crf),
            "-preset", self.config.video_preset,
            "-acodec", "aac",
            "-b:a", "128k",
            "-map_metadata", "0",
            "-y",  # Overwrite output file if it exists
            str(out_path)
        ]


# ============================================================================
# MARK: Image Compressor
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
            filename=in_path.name
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
        converting_to_jpeg = not self.config.preserve_format and output_ext in ['.jpg', '.jpeg']
        
        if converting_to_jpeg:
            # Convert all images to JPEG format
            # Handle transparency/alpha channel for PNG/WebP
            if input_ext in ['.png', '.webp']:
                # Remove alpha channel and convert to RGB for JPEG
                # JPEG doesn't support transparency
                if self.config.image_resize is not None and self.config.image_resize < 100:
                    resize_factor = self.config.image_resize / 100
                    ffmpeg_args.extend([
                        "-vf", f"format=rgb24,scale=iw*{resize_factor}:ih*{resize_factor}:flags=lanczos"
                    ])
                else:
                    ffmpeg_args.extend([
                        "-vf", "format=rgb24"
                    ])
            elif self.config.image_resize is not None and self.config.image_resize < 100:
                # JPEG input with resize
                resize_factor = self.config.image_resize / 100
                ffmpeg_args.extend([
                    "-vf", f"scale=iw*{resize_factor}:ih*{resize_factor}:flags=lanczos"
                ])
            
            # JPEG quality mapping
            jpeg_quality = self._map_jpeg_quality()
            ffmpeg_q = int(2 + (31 - 2) * (100 - jpeg_quality) / 100)
            ffmpeg_q = max(2, min(31, ffmpeg_q))
            ffmpeg_args.extend(["-q:v", str(ffmpeg_q)])
            
        elif self.config.preserve_format:
            # Preserve original format - use format-specific compression
            if input_ext in ['.jpg', '.jpeg']:
                # JPEG quality mapping
                jpeg_quality = self._map_jpeg_quality()
                ffmpeg_q = int(2 + (31 - 2) * (100 - jpeg_quality) / 100)
                ffmpeg_q = max(2, min(31, ffmpeg_q))
                ffmpeg_args.extend(["-q:v", str(ffmpeg_q)])
            elif input_ext == '.png':
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
                ffmpeg_args.extend([
                    "-compression_level", str(compress_level)
                ])
            elif input_ext == '.webp':
                # WebP quality mapping
                webp_quality = self._map_webp_quality()
                ffmpeg_args.extend(["-quality", str(webp_quality)])
            else:
                # Default: use quality parameter for other formats
                ffmpeg_q = int(2 + (31 - 2) * (100 - self.config.image_quality) / 100) if self.config.image_quality <= 100 else 2
                ffmpeg_args.extend(["-q:v", str(ffmpeg_q)])
            
            # Add resize filter if specified (only if not already added for JPEG conversion)
            if self.config.image_resize is not None and self.config.image_resize < 100:
                resize_factor = self.config.image_resize / 100
                ffmpeg_args.extend([
                    "-vf", f"scale=iw*{resize_factor}:ih*{resize_factor}:flags=lanczos"
                ])
        
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


# ============================================================================
# MARK: Report Generator
# ============================================================================

class ReportGenerator:
    """Generates CSV reports with compression statistics."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize report generator.
        
        Args:
            output_dir: Directory where reports will be saved
        """
        self.output_dir = output_dir
    
    def generate(
        self,
        stats: Dict,
        compressed_folder_name: str,
        recursive: bool = False,
        cmd_args: Optional[Dict] = None
    ) -> List[Path]:
        """
        Generate CSV report(s) with compression statistics.
        
        If recursive=True and folder_stats exist, generates one report per subfolder.
        Otherwise, generates a single report.
        
        Args:
            stats: Statistics dictionary from compression
            compressed_folder_name: Name of the compressed folder
            recursive: Whether to generate per-folder reports
            cmd_args: Command line arguments for report
        
        Returns:
            List of report file paths.
        """
        reports_dir = self.output_dir / "reports"
        
        # Sanitize folder name for directory/filename
        safe_name = "".join(c for c in compressed_folder_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        
        report_paths = []
        
        # If recursive mode and folder_stats exist, generate per-folder reports
        if recursive and "folder_stats" in stats and stats["folder_stats"]:
            # Create main folder for reports
            main_reports_dir = reports_dir / safe_name
            main_reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate report for each subfolder
            for folder_key, folder_stat in stats["folder_stats"].items():
                # Skip empty folders
                if folder_stat["total_files"] == 0:
                    continue
                
                # Sanitize folder name for filename
                folder_safe_name = "".join(c for c in folder_key if c.isalnum() or c in (' ', '-', '_', '\\', '/')).strip()
                folder_safe_name = folder_safe_name.replace(' ', '_').replace('\\', '_').replace('/', '_')
                if not folder_safe_name or folder_safe_name == ".":
                    folder_safe_name = "root"
                
                report_path = main_reports_dir / f"{folder_safe_name}_report.csv"
                folder_display_name = folder_key if folder_key != "." else "root"
                unique_path = self._get_unique_path(report_path)
                self._write_csv_report(unique_path, folder_stat, folder_display_name, compressed_folder_name, cmd_args)
                report_paths.append(unique_path)
                print(f"✓ Report generated: {unique_path}")
            
            # Generate aggregated report combining all subfolder reports
            aggregated_stats = {
                "total_files": 0,
                "processed": 0,
                "skipped": 0,
                "errors": 0,
                "total_original_size": 0,
                "total_compressed_size": 0,
                "space_saved": 0,
                "total_processing_time": stats.get("total_processing_time", 0),
                "files": []
            }
            
            # Aggregate all folder stats
            for folder_stat in stats["folder_stats"].values():
                aggregated_stats["total_files"] += folder_stat["total_files"]
                aggregated_stats["processed"] += folder_stat["processed"]
                aggregated_stats["skipped"] += folder_stat["skipped"]
                aggregated_stats["errors"] += folder_stat["errors"]
                aggregated_stats["total_original_size"] += folder_stat["total_original_size"]
                aggregated_stats["total_compressed_size"] += folder_stat["total_compressed_size"]
                aggregated_stats["space_saved"] += folder_stat["space_saved"]
                aggregated_stats["files"].extend(folder_stat["files"])
            
            # Generate aggregated report
            aggregated_report_path = main_reports_dir / "aggregated_report.csv"
            unique_aggregated_path = self._get_unique_path(aggregated_report_path)
            self._write_csv_report(unique_aggregated_path, aggregated_stats, f"{compressed_folder_name} (All Folders)", None, cmd_args)
            report_paths.append(unique_aggregated_path)
            print(f"✓ Aggregated report generated: {unique_aggregated_path}")
        
        else:
            # Generate single report (non-recursive or no folder_stats)
            reports_dir.mkdir(parents=True, exist_ok=True)
            report_path = reports_dir / f"{safe_name}_report.csv"
            unique_path = self._get_unique_path(report_path)
            self._write_csv_report(unique_path, stats, compressed_folder_name, None, cmd_args)
            report_paths.append(unique_path)
            print(f"\n✓ Report generated: {unique_path}")
        
        return report_paths
    
    def _get_unique_path(self, base_path: Path) -> Path:
        """Get a unique report path by incrementing number if file exists."""
        if not base_path.exists():
            return base_path
        
        # File exists, try incrementing numbers
        base_name = base_path.stem
        suffix = base_path.suffix
        parent_dir = base_path.parent
        
        # Extract base name without existing numbers in parentheses
        match = re.match(r'^(.+?)(\s*\(\d+\))?$', base_name)
        if match:
            base_name_only = match.group(1).strip()
        else:
            base_name_only = base_name
        
        # Find the highest existing number
        existing_numbers = []
        pattern = re.compile(re.escape(base_name_only) + r'\s*\((\d+)\)' + re.escape(suffix))
        for file in parent_dir.glob(f"{base_name_only}*{suffix}"):
            match = pattern.match(file.name)
            if match:
                existing_numbers.append(int(match.group(1)))
        
        # Start from the next number after the highest, or 1 if none exist
        counter = (max(existing_numbers) + 1) if existing_numbers else 1
        
        new_name = f"{base_name_only} ({counter}){suffix}"
        return parent_dir / new_name
    
    def _write_csv_report(
        self,
        file_path: Path,
        report_stats: Dict,
        report_title: str,
        parent_folder: Optional[str] = None,
        cmd_args: Optional[Dict] = None
    ) -> None:
        """Write a CSV report with summary/stats as header comments and CSV data."""
        # Get unique file path if report already exists
        unique_path = self._get_unique_path(file_path)
        if unique_path != file_path:
            print(f"  Report already exists, creating: {unique_path.name}")
        
        with open(unique_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write summary and statistics as comment rows
            writer.writerow([f"# Compression Report: {report_title}"])
            if parent_folder:
                writer.writerow([f"# Parent Folder: {parent_folder}"])
            writer.writerow([f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
            writer.writerow([])
            
            # Summary section
            writer.writerow(["# Summary"])
            writer.writerow(["# Total Files Found", report_stats['total_files']])
            writer.writerow(["# Files Processed", report_stats['processed']])
            writer.writerow(["# Files Skipped", report_stats['skipped']])
            writer.writerow(["# Errors", report_stats['errors']])
            writer.writerow([])
            
            # Size Statistics section
            total_compression_ratio = (report_stats["space_saved"] / report_stats["total_original_size"] * 100) if report_stats["total_original_size"] > 0 else 0
            writer.writerow(["# Size Statistics"])
            writer.writerow(["# Total Original Size", format_size(report_stats['total_original_size'])])
            writer.writerow(["# Total Compressed Size", format_size(report_stats['total_compressed_size'])])
            writer.writerow(["# Total Space Saved", format_size(report_stats['space_saved'])])
            writer.writerow(["# Overall Compression Ratio", f"{total_compression_ratio:.2f}%"])
            
            # Processing Time Statistics
            total_time = report_stats.get('total_processing_time', 0)
            if total_time > 0:
                hours = int(total_time // 3600)
                minutes = int((total_time % 3600) // 60)
                seconds = total_time % 60
                if hours > 0:
                    time_str = f"{hours}h {minutes}m {seconds:.1f}s"
                elif minutes > 0:
                    time_str = f"{minutes}m {seconds:.1f}s"
                else:
                    time_str = f"{seconds:.1f}s"
                writer.writerow(["# Total Processing Time", time_str])
            writer.writerow([])
            
            # File Details CSV section
            if report_stats['files']:
                writer.writerow(["# File Details"])
                writer.writerow(["Filename", "Original Size", "Compressed Size", "Space Saved", "Compression Ratio (%)", "Processing Time (s)", "Status"])
                
                for file_info in report_stats['files']:
                    processing_time = file_info.get('processing_time', 0)
                    writer.writerow([
                        file_info['name'],
                        format_size(file_info['original_size']),
                        format_size(file_info['compressed_size']),
                        format_size(file_info['space_saved']),
                        f"{file_info['compression_ratio']:.2f}",
                        f"{processing_time:.2f}",
                        file_info['status']
                    ])
                writer.writerow([])
            
            # Arguments section
            if cmd_args:
                writer.writerow(["# Arguments"])
                writer.writerow(["# Source Folder", cmd_args.get('source_folder', 'N/A')])
                writer.writerow(["# Video CRF", cmd_args.get('video_crf', 'N/A')])
                writer.writerow(["# Video Preset", cmd_args.get('video_preset', 'N/A')])
                writer.writerow(["# Image Quality", cmd_args.get('image_quality', 'N/A')])
                if cmd_args.get('image_resize'):
                    writer.writerow(["# Image Resize", f"{cmd_args.get('image_resize')}%"])
                writer.writerow(["# Recursive", cmd_args.get('recursive', 'N/A')])
                writer.writerow(["# Overwrite", cmd_args.get('overwrite', 'N/A')])
                writer.writerow(["# Keep If Larger", cmd_args.get('keep_if_larger', 'N/A')])
                writer.writerow(["# Progress Interval", cmd_args.get('progress_interval', 'N/A')])
                if cmd_args.get('ffmpeg_path'):
                    writer.writerow(["# FFmpeg Path", cmd_args.get('ffmpeg_path')])
                if cmd_args.get('backup_dir'):
                    writer.writerow(["# Backup Directory", cmd_args.get('backup_dir')])


# ============================================================================
# MARK: Statistics Manager
# ============================================================================

class StatisticsManager:
    """Manages cumulative compression statistics and run history."""
    
    def __init__(self, statistics_dir: Path):
        """
        Initialize statistics manager.
        
        Args:
            statistics_dir: Path to the statistics directory
        """
        self.statistics_dir = statistics_dir
        self.statistics_dir.mkdir(parents=True, exist_ok=True)
        self.cumulative_stats_file = self.statistics_dir / "statistics.csv"
        self.run_history_file = self.statistics_dir / "run_history.csv"
    
    def load_cumulative_stats(self) -> Dict:
        """
        Load existing cumulative statistics from CSV file.
        
        Returns:
            Dictionary with cumulative statistics, or defaults if file doesn't exist
        """
        default_stats = {
            "total_runs": 0,
            "total_files_processed": 0,
            "total_files_skipped": 0,
            "total_files_errors": 0,
            "total_original_size_bytes": 0,
            "total_compressed_size_bytes": 0,
            "total_space_saved_bytes": 0,
            "last_updated": None
        }
        
        if not self.cumulative_stats_file.exists():
            return default_stats
        
        try:
            with open(self.cumulative_stats_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                row = next(reader, None)
                
                if row is None:
                    return default_stats
                
                # Convert string values to appropriate types, handling empty strings
                def safe_int(value, default=0):
                    """Safely convert value to int, handling None and empty strings."""
                    if value is None or value == "":
                        return default
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return default
                
                stats = {
                    "total_runs": safe_int(row.get("total_runs")),
                    "total_files_processed": safe_int(row.get("total_files_processed")),
                    "total_files_skipped": safe_int(row.get("total_files_skipped")),
                    "total_files_errors": safe_int(row.get("total_files_errors")),
                    "total_original_size_bytes": safe_int(row.get("total_original_size_bytes")),
                    "total_compressed_size_bytes": safe_int(row.get("total_compressed_size_bytes")),
                    "total_space_saved_bytes": safe_int(row.get("total_space_saved_bytes")),
                    "last_updated": row.get("last_updated") or None
                }
                
                return stats
        except (ValueError, KeyError, csv.Error) as e:
            print(f"Warning: Error reading statistics file ({e}). Creating new file.")
            return default_stats
        except Exception as e:
            print(f"Warning: Unexpected error reading statistics file ({e}). Creating new file.")
            return default_stats
    
    def update_cumulative_stats(self, run_stats: Dict) -> None:
        """
        Update cumulative statistics with current run results.
        
        Args:
            run_stats: Statistics dictionary from current compression run
        """
        cumulative = self.load_cumulative_stats()
        
        # Update cumulative totals
        cumulative["total_runs"] += 1
        cumulative["total_files_processed"] += run_stats.get("processed", 0)
        cumulative["total_files_skipped"] += run_stats.get("skipped", 0)
        cumulative["total_files_errors"] += run_stats.get("errors", 0)
        cumulative["total_original_size_bytes"] += run_stats.get("total_original_size", 0)
        cumulative["total_compressed_size_bytes"] += run_stats.get("total_compressed_size", 0)
        cumulative["total_space_saved_bytes"] += run_stats.get("space_saved", 0)
        cumulative["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.save_cumulative_stats(cumulative)
    
    def save_cumulative_stats(self, stats: Dict) -> None:
        """
        Save cumulative statistics to CSV file.
        
        Args:
            stats: Dictionary with cumulative statistics
        """
        try:
            with open(self.cumulative_stats_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "total_runs",
                    "total_files_processed",
                    "total_files_skipped",
                    "total_files_errors",
                    "total_original_size_bytes",
                    "total_compressed_size_bytes",
                    "total_space_saved_bytes",
                    "last_updated"
                ])
                writer.writeheader()
                writer.writerow(stats)
        except PermissionError:
            print(f"Warning: Permission denied when writing to {self.cumulative_stats_file}")
        except Exception as e:
            print(f"Warning: Error saving cumulative statistics ({e})")
    
    def append_run_history(self, run_stats: Dict, cmd_args: Dict) -> None:
        """
        Append current run to run history CSV file.
        
        Args:
            run_stats: Statistics dictionary from current compression run
            cmd_args: Command line arguments used for this run
        """
        try:
            file_exists = self.run_history_file.exists()
            
            with open(self.run_history_file, 'a', newline='', encoding='utf-8') as f:
                fieldnames = [
                    "timestamp",
                    "source_folder",
                    "files_processed",
                    "files_skipped",
                    "files_errors",
                    "space_saved_bytes",
                    "processing_time_seconds",
                    "video_crf",
                    "image_quality",
                    "recursive",
                    "overwrite"
                ]
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # Write header if file is new
                if not file_exists:
                    writer.writeheader()
                
                # Prepare run record
                run_record = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source_folder": cmd_args.get("source_folder", "N/A"),
                    "files_processed": run_stats.get("processed", 0),
                    "files_skipped": run_stats.get("skipped", 0),
                    "files_errors": run_stats.get("errors", 0),
                    "space_saved_bytes": run_stats.get("space_saved", 0),
                    "processing_time_seconds": run_stats.get("total_processing_time", 0.0),
                    "video_crf": cmd_args.get("video_crf", "N/A"),
                    "image_quality": cmd_args.get("image_quality", "N/A"),
                    "recursive": cmd_args.get("recursive", False),
                    "overwrite": cmd_args.get("overwrite", False)
                }
                
                writer.writerow(run_record)
        except PermissionError:
            print(f"Warning: Permission denied when writing to {self.run_history_file}")
        except Exception as e:
            print(f"Warning: Error saving run history ({e})")
    
    def print_stats(self) -> None:
        """Print cumulative statistics in a nice format."""
        stats = self.load_cumulative_stats()
        
        if stats["total_runs"] == 0:
            print("\n" + "="*60)
            print("No Statistics Available")
            print("="*60)
            print("Statistics will be created after your first compression run.")
            return
        
        print("\n" + "="*60)
        print("Cumulative Compression Statistics")
        print("="*60)
        print(f"Total Runs: {stats['total_runs']}")
        print(f"Last Updated: {stats['last_updated'] or 'N/A'}")
        print()
        print("File Statistics:")
        print(f"  Processed: {stats['total_files_processed']:,} files")
        print(f"  Skipped: {stats['total_files_skipped']:,} files")
        print(f"  Errors: {stats['total_files_errors']:,} files")
        print()
        print("Size Statistics:")
        original_size = stats['total_original_size_bytes']
        compressed_size = stats['total_compressed_size_bytes']
        space_saved = stats['total_space_saved_bytes']
        
        print(f"  Original Size: {format_size(original_size)}")
        print(f"  Compressed Size: {format_size(compressed_size)}")
        print(f"  Space Saved: {format_size(space_saved)}")
        
        if original_size > 0:
            compression_ratio = (space_saved / original_size) * 100
            print(f"  Overall Compression: {compression_ratio:.2f}%")
        
        print("="*60)
    
    def load_run_history(self) -> List[Dict]:
        """
        Load run history from CSV file.
        
        Returns:
            List of dictionaries containing run history records
        """
        if not self.run_history_file.exists():
            return []
        
        try:
            runs = []
            with open(self.run_history_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    runs.append(row)
            return runs
        except Exception as e:
            print(f"Warning: Error reading run history ({e})")
            return []
    
    def print_history(self, limit: Optional[int] = None) -> None:
        """
        Print run history in a nice format.
        
        Args:
            limit: Maximum number of runs to display (None for all)
        """
        runs = self.load_run_history()
        
        if not runs:
            print("\n" + "="*60)
            print("No Run History Available")
            print("="*60)
            print("Run history will be created after your first compression run.")
            return
        
        # Reverse to show most recent first
        runs.reverse()
        
        if limit:
            runs = runs[:limit]
        
        print("\n" + "="*60)
        print(f"Run History ({len(runs)} of {len(self.load_run_history())} runs shown)")
        print("="*60)
        
        for idx, run in enumerate(runs, 1):
            print(f"\nRun #{idx}")
            print(f"  Timestamp: {run.get('timestamp', 'N/A')}")
            print(f"  Source Folder: {run.get('source_folder', 'N/A')}")
            print(f"  Files: {run.get('files_processed', 0)} processed, "
                  f"{run.get('files_skipped', 0)} skipped, "
                  f"{run.get('files_errors', 0)} errors")
            
            space_saved = int(run.get('space_saved_bytes', 0))
            print(f"  Space Saved: {format_size(space_saved)}")
            
            time_seconds = float(run.get('processing_time_seconds', 0))
            if time_seconds > 0:
                hours = int(time_seconds // 3600)
                minutes = int((time_seconds % 3600) // 60)
                seconds = time_seconds % 60
                if hours > 0:
                    time_str = f"{hours}h {minutes}m {seconds:.1f}s"
                elif minutes > 0:
                    time_str = f"{minutes}m {seconds:.1f}s"
                else:
                    time_str = f"{seconds:.1f}s"
                print(f"  Processing Time: {time_str}")
            
            print(f"  Settings: CRF={run.get('video_crf', 'N/A')}, "
                  f"Quality={run.get('image_quality', 'N/A')}, "
                  f"Recursive={run.get('recursive', 'False')}, "
                  f"Overwrite={run.get('overwrite', 'False')}")
        
        print("\n" + "="*60)


# ============================================================================
# MARK: Media Compressor
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
        
        self.stats.stats["total_files"] = len(all_files)
        print(f"Found {len(all_files)} media file(s) to process...")
        
        # Process each file
        for idx, file_path in enumerate(all_files, 1):
            self._process_file(file_path, idx, len(all_files), compressed_folder)
        
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
        
        # Add to total files
        self.stats.add_total_file(original_size, folder_key)
        
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


# ============================================================================
# MARK: Main Function
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Compress media files (videos and images) while preserving timestamps."
    )
    parser.add_argument(
        "source_folder",
        type=str,
        nargs='?',
        help="Path to the source folder containing media files"
    )
    parser.add_argument(
        "--video-crf",
        type=int,
        default=23,
        help="Video CRF value (0-51, lower = higher quality, default: 23)"
    )
    parser.add_argument(
        "--video-preset",
        type=str,
        default="medium",
        choices=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", 
                 "slow", "slower", "veryslow"],
        help="Video encoding preset (default: medium)"
    )
    parser.add_argument(
        "--image-quality",
        type=int,
        default=100,
        help="Image quality (0-100, higher = better quality, default: 100)"
    )
    parser.add_argument(
        "--image-resize",
        type=int,
        default=None,
        help="Resize images to percentage of original dimensions (1-100, e.g., 90 = 90%% of original size, default: no resize)"
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Process files recursively in subdirectories"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite original files instead of creating a 'compressed' folder"
    )
    parser.add_argument(
        "--ffmpeg-path",
        type=str,
        default=None,
        help="Path to FFmpeg executable (default: auto-detect)"
    )
    parser.add_argument(
        "--progress-interval",
        type=float,
        default=5.0,
        help="Seconds between FFmpeg progress updates (default: 5.0)"
    )
    parser.add_argument(
        "--keep-if-larger",
        action="store_true",
        help="Keep compressed files even if they are larger than the original (default: skip larger files)"
    )
    parser.add_argument(
        "--backup-dir",
        type=str,
        default=None,
        help="Directory to create a backup of the source folder before compression"
    )
    parser.add_argument(
        "--preserve-format",
        action="store_true",
        help="Preserve original image formats (default: convert all images to JPEG)"
    )
    parser.add_argument(
        "--view-stats",
        action="store_true",
        help="View cumulative compression statistics and exit"
    )
    parser.add_argument(
        "--view-history",
        type=int,
        nargs='?',
        const=-1,
        metavar="N",
        help="View run history and exit (optionally limit to N most recent runs, default: all)"
    )
    
    args = parser.parse_args()
    
    # Handle view commands early (don't require source_folder)
    if args.view_stats or args.view_history is not None:
        script_dir = Path(__file__).resolve().parent
        statistics_dir = script_dir / "statistics"
        stats_manager = StatisticsManager(statistics_dir)
        
        if args.view_stats:
            stats_manager.print_stats()
        
        if args.view_history is not None:
            # const=-1 means --view-history without number shows all
            # A number means limit to that many
            limit = None if args.view_history == -1 else (args.view_history if args.view_history > 0 else None)
            stats_manager.print_history(limit=limit)
        
        return 0
    
    # Require source_folder for compression
    if not args.source_folder:
        parser.error("source_folder is required for compression (or use --view-stats/--view-history)")
    
    try:
        # Create configuration
        config = CompressionConfig(
            source_folder=Path(args.source_folder),
            video_crf=args.video_crf,
            video_preset=args.video_preset,
            image_quality=args.image_quality,
            image_resize=args.image_resize,
            recursive=args.recursive,
            overwrite=args.overwrite,
            ffmpeg_path=args.ffmpeg_path,
            progress_interval=args.progress_interval,
            keep_if_larger=args.keep_if_larger,
            backup_dir=Path(args.backup_dir) if args.backup_dir else None,
            preserve_format=args.preserve_format
        )
        
        # Compress media
        compressor = MediaCompressor(config)
        stats = compressor.compress()
        
        # Generate report(s)
        source_path = Path(args.source_folder)
        compressed_folder_name = source_path.name
        
        # Prepare command line arguments for report
        cmd_args = {
            'source_folder': args.source_folder,
            'video_crf': args.video_crf,
            'video_preset': args.video_preset,
            'image_quality': args.image_quality,
            'image_resize': args.image_resize,
            'recursive': args.recursive,
            'overwrite': args.overwrite,
            'keep_if_larger': args.keep_if_larger,
            'progress_interval': args.progress_interval,
        }
        if args.ffmpeg_path:
            cmd_args['ffmpeg_path'] = args.ffmpeg_path
        if args.backup_dir:
            cmd_args['backup_dir'] = args.backup_dir
        
        report_generator = ReportGenerator(Path.cwd())
        report_paths = report_generator.generate(stats, compressed_folder_name, recursive=args.recursive, cmd_args=cmd_args)
        
        # Update cumulative statistics
        try:
            # Use absolute path to ensure correct resolution
            script_dir = Path(__file__).resolve().parent
            statistics_dir = script_dir / "statistics"
            stats_manager = StatisticsManager(statistics_dir)
            stats_manager.update_cumulative_stats(stats)
            stats_manager.append_run_history(stats, cmd_args)
            print(f"Statistics updated: {statistics_dir}")
        except Exception as e:
            import traceback
            print(f"Warning: Could not update statistics ({e})")
            print(f"Traceback: {traceback.format_exc()}")
        
        # Print summary
        print("\n" + "="*60)
        print("Compression Complete!")
        print("="*60)
        print(f"Processed: {stats['processed']} files")
        print(f"Skipped: {stats['skipped']} files")
        print(f"Errors: {stats['errors']} files")
        print(f"Total space saved: {format_size(stats['space_saved'])}")
        if args.recursive and len(report_paths) > 1:
            print(f"Reports generated: {len(report_paths)} reports in reports/{compressed_folder_name}/")
        else:
            print(f"Report: {report_paths[0] if report_paths else 'N/A'}")
        print("="*60)
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())