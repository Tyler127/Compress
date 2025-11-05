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


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def preserve_timestamps(src: Path, dst: Path):
    """Preserve file timestamps from source to destination."""
    st = src.stat()
    os.utime(dst, (st.st_atime, st.st_mtime))  # access, modified
    shutil.copystat(src, dst)  # copies creation time on Windows too


def parse_ffmpeg_progress(line: str) -> Optional[Dict[str, str]]:
    """Parse FFmpeg progress line from stderr."""
    # FFmpeg outputs progress as: frame=  123 fps= 25 q=23.0 size=    1234kB time=00:00:05.00 bitrate=1234.5kbits/s speed=1.2x
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


def run_ffmpeg_with_progress(
    ffmpeg_path: str,
    args: List[str],
    progress_interval: float = 5.0,
    filename: str = ""
) -> subprocess.CompletedProcess:
    """
    Run FFmpeg with live progress updates.
    
    Args:
        ffmpeg_path: Path to FFmpeg executable
        args: List of FFmpeg arguments
        progress_interval: Seconds between progress updates
        filename: Filename being processed (for display)
    
    Returns:
        CompletedProcess from subprocess
    """
    cmd = [ffmpeg_path] + args
    
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
            progress = parse_ffmpeg_progress(line)
            
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
                progress = parse_ffmpeg_progress(line)
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


def validate_parameters(video_crf: int, image_quality: int, video_preset: str, image_resize: Optional[int] = None) -> None:
    """Validate input parameters."""
    if not (0 <= video_crf <= 51):
        raise ValueError(f"video_crf must be between 0 and 51, got {video_crf}")
    
    if not (0 <= image_quality <= 100):
        raise ValueError(f"image_quality must be between 0 and 100, got {image_quality}")
    
    if image_resize is not None and not (1 <= image_resize <= 100):
        raise ValueError(f"image_resize must be between 1 and 100, got {image_resize}")
    
    valid_presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", 
                     "slow", "slower", "veryslow"]
    if video_preset not in valid_presets:
        raise ValueError(f"video_preset must be one of {valid_presets}, got {video_preset}")


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


def compress_media(
    source_folder: str,
    video_crf: int = 23,
    video_preset: str = "medium",
    image_quality: int = 85,
    image_resize: Optional[int] = None,
    recursive: bool = False,
    overwrite: bool = False,
    ffmpeg_path: Optional[str] = None,
    progress_interval: float = 5.0,
    keep_if_larger: bool = False,
    backup_dir: Optional[str] = None
) -> Dict:
    """
    Compress media files (videos and images).
    
    Returns:
        Dictionary with statistics about the compression process.
        If recursive=True, includes per-folder stats in 'folder_stats' key.
    """
    # Validate parameters
    validate_parameters(video_crf, image_quality, video_preset, image_resize)
    
    # Find FFmpeg if not provided
    if ffmpeg_path is None:
        ffmpeg_path = find_ffmpeg()
        if ffmpeg_path is None:
            raise FileNotFoundError(
                "FFmpeg not found. Please install FFmpeg and add it to PATH, "
                "or specify the path using --ffmpeg-path option."
            )
    
    source_folder = Path(source_folder)
    if not source_folder.exists():
        raise FileNotFoundError(f"Source folder does not exist: {source_folder}")
    
    # Create backup if backup directory is provided
    backup_path = None
    if backup_dir:
        backup_dir_path = Path(backup_dir)
        backup_path = create_backup(source_folder, backup_dir_path)
    
    # Track total processing time
    start_time = time.time()
    
    video_exts = [".mp4", ".mov", ".mkv", ".avi"]
    image_exts = [".jpg", ".jpeg", ".png", ".webp"]
    
    # Collect files
    if recursive:
        all_files = [f for f in source_folder.rglob("*") if f.suffix.lower() in video_exts + image_exts and f.is_file()]
    else:
        all_files = [f for f in source_folder.iterdir() if f.suffix.lower() in video_exts + image_exts and f.is_file()]
    
    if not all_files:
        print("No media files found to compress.")
        result = {
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
            result["folder_stats"] = {}
        return result
    
    compressed_folder = source_folder / "compressed"
    if not overwrite:
        compressed_folder.mkdir(parents=True, exist_ok=True)
    
    # Statistics tracking
    stats = {
        "total_files": len(all_files),
        "processed": 0,
        "skipped": 0,
        "errors": 0,
        "total_original_size": 0,
        "total_compressed_size": 0,
        "space_saved": 0,
        "files": []
    }
    
    # Per-folder stats for recursive mode
    if recursive:
        stats["folder_stats"] = {}
    
    print(f"Found {len(all_files)} media file(s) to process...")
    
    for idx, f in enumerate(all_files, 1):
        in_path = f
        if overwrite:
            out_path = f.parent / (f.stem + "_tmp" + f.suffix)
        else:
            relative_path = f.relative_to(source_folder)
            out_path = compressed_folder / relative_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get folder path for recursive mode tracking
        if recursive:
            try:
                folder_path = f.parent.relative_to(source_folder)
                folder_key = str(folder_path) if str(folder_path) != "." else "root"
            except ValueError:
                # File is outside source_folder (shouldn't happen, but handle gracefully)
                folder_key = "root"
        else:
            folder_key = "root"
        
        # Initialize folder stats if needed
        if recursive and folder_key not in stats["folder_stats"]:
            stats["folder_stats"][folder_key] = {
                "total_files": 0,
                "processed": 0,
                "skipped": 0,
                "errors": 0,
                "total_original_size": 0,
                "total_compressed_size": 0,
                "space_saved": 0,
                "files": []
            }
        
        original_size = in_path.stat().st_size
        
        # Track total files per folder (before skipping)
        if recursive:
            stats["folder_stats"][folder_key]["total_files"] += 1
            stats["folder_stats"][folder_key]["total_original_size"] += original_size
        
        stats["total_original_size"] += original_size
        
        # Skip if already compressed and not overwriting
        if not overwrite and out_path.exists():
            # File already exists - count its size in compressed folder total
            existing_size = out_path.stat().st_size
            stats["total_compressed_size"] += existing_size
            stats["skipped"] += 1
            if recursive:
                stats["folder_stats"][folder_key]["skipped"] += 1
                stats["folder_stats"][folder_key]["total_compressed_size"] += existing_size
            print(f"[{idx}/{len(all_files)}] Skipping (already exists): {f.name} ({format_size(existing_size)})")
            continue
        
        print(f"[{idx}/{len(all_files)}] Processing: {f.name} ({format_size(original_size)})")
        
        # Track processing time for this file
        file_start_time = time.time()
        
        try:
            if f.suffix.lower() in video_exts:
                # Compress video using FFmpeg with progress updates
                ffmpeg_args = [
                    "-i", str(in_path),
                    "-vcodec", "libx264",
                    "-crf", str(video_crf),
                    "-preset", video_preset,
                    "-acodec", "aac",
                    "-b:a", "128k",
                    "-map_metadata", "0",
                    "-y",  # Overwrite output file if it exists
                    str(out_path)
                ]
                run_ffmpeg_with_progress(
                    ffmpeg_path,
                    ffmpeg_args,
                    progress_interval=progress_interval,
                    filename=f.name
                )
                # Track if timestamps were already preserved
                preserve_timestamps_called = False
            elif f.suffix.lower() in image_exts:
                # Use FFmpeg to compress images
                # Preserve original format
                
                # Track if timestamps were already preserved
                preserve_timestamps_called = False
                
                # Determine output format based on input format
                input_ext = f.suffix.lower()
                if input_ext in ['.jpg', '.jpeg']:
                    # JPEG quality mapping
                    # Map image_quality (0-100) to JPEG quality (0-100)
                    # JPEG quality 100 is essentially uncompressed and produces huge files
                    # Map quality 100 to JPEG quality 95 (excellent quality, much smaller files)
                    if image_quality >= 100:
                        jpeg_quality = 95
                    elif image_quality >= 95:
                        jpeg_quality = image_quality - 5
                    else:
                        jpeg_quality = int((image_quality / 94) * 90)
                        jpeg_quality = max(1, min(90, jpeg_quality))
                    
                    # FFmpeg uses q:v scale: 2=best quality, 31=worst quality
                    ffmpeg_q = int(2 + (31 - 2) * (100 - jpeg_quality) / 100)
                    ffmpeg_q = max(2, min(31, ffmpeg_q))
                    
                    # Build FFmpeg arguments for JPEG compression
                    ffmpeg_args = [
                        "-i", str(in_path),
                        "-q:v", str(ffmpeg_q),
                    ]
                elif input_ext == '.png':
                    # PNG compression - use compress_level (0-9)
                    # Map image_quality (0-100) to compress_level (0-9)
                    # Higher quality = lower compression level (better quality, larger file)
                    compress_level = int(9 - (image_quality / 100) * 9)
                    compress_level = max(0, min(9, compress_level))
                    
                    # Build FFmpeg arguments for PNG compression
                    ffmpeg_args = [
                        "-i", str(in_path),
                        "-compression_level", str(compress_level),
                    ]
                elif input_ext == '.webp':
                    # WebP quality mapping
                    # Map image_quality (0-100) to WebP quality (0-100)
                    if image_quality >= 100:
                        webp_quality = 95
                    elif image_quality >= 95:
                        webp_quality = image_quality - 5
                    else:
                        webp_quality = int((image_quality / 94) * 90)
                        webp_quality = max(1, min(90, webp_quality))
                    
                    # Build FFmpeg arguments for WebP compression
                    ffmpeg_args = [
                        "-i", str(in_path),
                        "-quality", str(webp_quality),
                    ]
                else:
                    # Default: use quality parameter for other formats
                    ffmpeg_args = [
                        "-i", str(in_path),
                        "-q:v", str(int(2 + (31 - 2) * (100 - image_quality) / 100)) if image_quality <= 100 else "2",
                    ]
                
                # Add resize filter if specified
                if image_resize is not None and image_resize < 100:
                    # Resize image: resize percentage (e.g., 90 = 90% of original dimensions)
                    resize_factor = image_resize / 100
                    ffmpeg_args.extend([
                        "-vf", f"scale=iw*{resize_factor}:ih*{resize_factor}:flags=lanczos"
                    ])
                
                # Add output arguments (preserve original format)
                ffmpeg_args.extend([
                    "-y",  # Overwrite output file if it exists
                    str(out_path)
                ])
                
                # Run FFmpeg for image compression
                run_ffmpeg_with_progress(
                    ffmpeg_path,
                    ffmpeg_args,
                    progress_interval=progress_interval,
                    filename=f.name
                )
            
            # Preserve timestamps (unless already done by shutil.copy2 for quality 100)
            if not preserve_timestamps_called:
                preserve_timestamps(in_path, out_path)
            
            # Get compressed size
            compressed_size = out_path.stat().st_size
            space_saved = original_size - compressed_size
            compression_ratio = (space_saved / original_size * 100) if original_size > 0 else 0
            
            # Check if compressed file is larger than original
            if compressed_size > original_size:
                if keep_if_larger:
                    # Keep it but warn
                    print(f"  ⚠️  Warning: Compressed file is larger than original ({format_size(compressed_size)} > {format_size(original_size)})")
                else:
                    # Skip compressed version - delete it and copy original to compressed folder (non-overwrite mode)
                    if out_path.exists():
                        out_path.unlink()
                    
                    if not overwrite:
                        # In non-overwrite mode, copy original to compressed folder
                        shutil.copy2(in_path, out_path)
                        preserve_timestamps(in_path, out_path)
                        print(f"  ⚠️  Compressed file larger, copying original instead: {format_size(original_size)}")
                        
                        # Track as if we processed it (but with no compression)
                        stats["total_compressed_size"] += original_size
                        stats["space_saved"] += 0  # No space saved
                        
                        # Calculate processing time for this file
                        file_processing_time = time.time() - file_start_time
                        
                        file_info = {
                            "name": str(f.relative_to(source_folder)),
                            "original_size": original_size,
                            "compressed_size": original_size,
                            "space_saved": 0,
                            "compression_ratio": 0.0,
                            "processing_time": file_processing_time,
                            "status": "success (copied original)"
                        }
                        
                        stats["files"].append(file_info)
                        stats["processed"] += 1
                        
                        if recursive:
                            stats["folder_stats"][folder_key]["files"].append(file_info)
                            stats["folder_stats"][folder_key]["processed"] += 1
                            stats["folder_stats"][folder_key]["total_compressed_size"] += original_size
                            stats["folder_stats"][folder_key]["space_saved"] += 0
                    else:
                        # In overwrite mode, just skip
                        print(f"  ⚠️  Compressed file is larger ({format_size(compressed_size)} > {format_size(original_size)}), skipping...")
                        stats["skipped"] += 1
                        if recursive:
                            stats["folder_stats"][folder_key]["skipped"] += 1
                    continue
            
            # Calculate processing time for this file
            file_processing_time = time.time() - file_start_time
            
            stats["total_compressed_size"] += compressed_size
            stats["space_saved"] += space_saved
            
            file_info = {
                "name": str(f.relative_to(source_folder)),
                "original_size": original_size,
                "compressed_size": compressed_size,
                "space_saved": space_saved,
                "compression_ratio": compression_ratio,
                "processing_time": file_processing_time,
                "status": "success"
            }
            
            stats["files"].append(file_info)
            stats["processed"] += 1
            
            if recursive:
                stats["folder_stats"][folder_key]["files"].append(file_info)
                stats["folder_stats"][folder_key]["processed"] += 1
                stats["folder_stats"][folder_key]["total_compressed_size"] += compressed_size
                stats["folder_stats"][folder_key]["space_saved"] += space_saved
            
            # Overwrite safely
            if overwrite and out_path.exists():
                out_path.replace(in_path)
                if compression_ratio < 0:
                    print(f"  ⚠️  Compressed (larger): {format_size(original_size)} → {format_size(compressed_size)} "
                          f"({compression_ratio:.1f}% increase)")
                else:
                    print(f"  ✓ Compressed: {format_size(original_size)} → {format_size(compressed_size)} "
                          f"({compression_ratio:.1f}% reduction)")
            else:
                if compression_ratio < 0:
                    print(f"  ⚠️  Compressed (larger): {format_size(original_size)} → {format_size(compressed_size)} "
                          f"({compression_ratio:.1f}% increase)")
                else:
                    print(f"  ✓ Compressed: {format_size(original_size)} → {format_size(compressed_size)} "
                          f"({compression_ratio:.1f}% reduction)")
                
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Error processing {in_path}: FFmpeg error")
            stats["errors"] += 1
            # Calculate processing time even for errors
            file_processing_time = time.time() - file_start_time
            
            file_info = {
                "name": str(f.relative_to(source_folder)),
                "original_size": original_size,
                "compressed_size": 0,
                "space_saved": 0,
                "compression_ratio": 0,
                "processing_time": file_processing_time,
                "status": f"error: {str(e)}"
            }
            stats["files"].append(file_info)
            if recursive:
                stats["folder_stats"][folder_key]["files"].append(file_info)
                stats["folder_stats"][folder_key]["errors"] += 1
            # Clean up failed output file
            if out_path.exists():
                out_path.unlink()
            continue
        except Exception as e:
            print(f"  ✗ Error processing {in_path}: {e}")
            stats["errors"] += 1
            # Calculate processing time even for errors
            file_processing_time = time.time() - file_start_time
            
            file_info = {
                "name": str(f.relative_to(source_folder)),
                "original_size": original_size,
                "compressed_size": 0,
                "space_saved": 0,
                "compression_ratio": 0,
                "processing_time": file_processing_time,
                "status": f"error: {str(e)}"
            }
            stats["files"].append(file_info)
            if recursive:
                stats["folder_stats"][folder_key]["files"].append(file_info)
                stats["folder_stats"][folder_key]["errors"] += 1
            # Clean up failed output file
            if out_path.exists():
                out_path.unlink()
            continue
    
    # Calculate total processing time
    total_processing_time = time.time() - start_time
    stats["total_processing_time"] = total_processing_time
    
    return stats


def generate_report(stats: Dict, compressed_folder_name: str, output_dir: Path, recursive: bool = False, args: Optional[Dict] = None) -> List[Path]:
    """
    Generate CSV report(s) with compression statistics.
    
    If recursive=True and folder_stats exist, generates one report per subfolder.
    Otherwise, generates a single report.
    
    Returns:
        List of report file paths.
    """
    reports_dir = output_dir / "reports"
    
    # Sanitize folder name for directory/filename
    safe_name = "".join(c for c in compressed_folder_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')
    
    report_paths = []
    
    def get_unique_report_path(base_path: Path) -> Path:
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
    
    def write_csv_report(file_path: Path, report_stats: Dict, report_title: str, parent_folder: str = None, cmd_args: Optional[Dict] = None):
        """Write a CSV report with summary/stats as header comments and CSV data."""
        # Get unique file path if report already exists
        unique_path = get_unique_report_path(file_path)
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
            unique_path = get_unique_report_path(report_path)
            write_csv_report(unique_path, folder_stat, folder_display_name, compressed_folder_name, args)
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
        unique_aggregated_path = get_unique_report_path(aggregated_report_path)
        write_csv_report(unique_aggregated_path, aggregated_stats, f"{compressed_folder_name} (All Folders)", None, args)
        report_paths.append(unique_aggregated_path)
        print(f"✓ Aggregated report generated: {unique_aggregated_path}")
    
    else:
        # Generate single report (non-recursive or no folder_stats)
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"{safe_name}_report.csv"
        unique_path = get_unique_report_path(report_path)
        write_csv_report(unique_path, stats, compressed_folder_name, None, args)
        report_paths.append(unique_path)
        print(f"\n✓ Report generated: {unique_path}")
    
    return report_paths


def main():
    parser = argparse.ArgumentParser(
        description="Compress media files (videos and images) while preserving timestamps."
    )
    parser.add_argument(
        "source_folder",
        type=str,
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
    
    args = parser.parse_args()
    
    try:
        stats = compress_media(
            source_folder=args.source_folder,
            video_crf=args.video_crf,
            video_preset=args.video_preset,
            image_quality=args.image_quality,
            image_resize=args.image_resize,
            recursive=args.recursive,
            overwrite=args.overwrite,
            ffmpeg_path=args.ffmpeg_path,
            progress_interval=args.progress_interval,
            keep_if_larger=args.keep_if_larger,
            backup_dir=args.backup_dir
        )
        
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
        
        report_paths = generate_report(stats, compressed_folder_name, Path.cwd(), recursive=args.recursive, args=cmd_args)
        
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