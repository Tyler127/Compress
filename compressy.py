import argparse
import shlex
import sys
import uuid
from pathlib import Path
from compressy.core.config import CompressionConfig
from compressy.core.media_compressor import MediaCompressor
from compressy.services.reports import ReportGenerator
from compressy.services.statistics import StatisticsManager
from compressy.utils.format import format_size, parse_size


# ============================================================================
#  Main Function
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Compress media files (videos and images).",
        add_help=False,
    )
    parser.add_argument(
        "--help",
        action="help",
        help="Show this help message and exit",
    )
    parser.add_argument(
        "source_folder",
        type=str,
        nargs='?',
        help="Path to the source folder containing media files"
    )
    parser.add_argument(
        "-crf", "--video-crf",
        type=int,
        default=23,
        help="Video CRF value (0-51, lower = higher quality, default: 23)"
    )
    parser.add_argument(
        "-vp", "--video-preset",
        type=str,
        default="medium",
        choices=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", 
                 "slow", "slower", "veryslow"],
        help="Video encoding preset (default: medium)"
    )
    parser.add_argument(
        "-vr", "--video-resize",
        type=int,
        default=None,
        help="Resize videos to percentage of original dimensions (0-100, e.g., 90 = 90%% of original size, 0 = no resize, default: no resize)"
    )
    parser.add_argument(
        "-iq", "--image-quality",
        type=int,
        default=100,
        help="Image quality (0-100, higher = better quality, default: 100)"
    )
    parser.add_argument(
        "-ir", "--image-resize",
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
        "-o", "--overwrite",
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
        "-pi", "--progress-interval",
        type=float,
        default=5.0,
        help="Seconds between FFmpeg progress updates (default: 5.0)"
    )
    parser.add_argument(
        "-kl", "--keep-if-larger",
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
        "-pf", "--preserve-format",
        action="store_true",
        help="Preserve original image formats (default: convert all images to JPEG)"
    )
    parser.add_argument(
        "-pt", "--preserve-timestamps",
        action="store_true",
        help="Preserve original timestamps for output files (default: disabled)"
    )
    parser.add_argument(
        "-s", "--view-stats",
        action="store_true",
        help="View cumulative compression statistics and exit"
    )
    parser.add_argument(
        "-h", "--view-history",
        type=int,
        nargs='?',
        const=-1,
        metavar="N",
        help="View run history and exit (optionally limit to N most recent runs, default: all)"
    )
    parser.add_argument(
        "-m", "--min-size",
        type=str,
        default=None,
        help="Minimum file size to process (e.g., '1MB', '500KB', '1.5GB')"
    )
    parser.add_argument(
        "-M", "--max-size",
        type=str,
        default=None,
        help="Maximum file size to process (e.g., '100MB', '1GB', '2.5GB')"
    )
    parser.add_argument(
        "-d", "--output-dir",
        type=str,
        default=None,
        help="Custom output directory for compressed files (cannot be used with --overwrite)"
    )
    parser.add_argument(
        "-res", "--video-resolution",
        type=str,
        default=None,
        help="Target video resolution (e.g., '1920x1080', '720p', '1080p', '4k')"
    )
    
    args = parser.parse_args()
    
    # Build command string from sys.argv for logging (only for compression runs, not view commands)
    def build_command_string():
        """Reconstruct the command string from sys.argv."""        
        # Use sys.argv but replace the script name with the actual script name
        cmd_parts = list(sys.argv)
        # Replace first argument (script path) with just the script name for cleaner output
        if cmd_parts:
            cmd_parts[0] = Path(__file__).name
        
        return " ".join(shlex.quote(arg) if " " in arg or any(c in arg for c in "&|<>()") else arg for arg in cmd_parts)
    
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
        # Generate unique UUID for this compression run
        run_uuid = str(uuid.uuid4())
        
        # Parse size arguments if provided
        min_size = parse_size(args.min_size) if args.min_size else None
        max_size = parse_size(args.max_size) if args.max_size else None
        
        # Create configuration
        config = CompressionConfig(
            source_folder=Path(args.source_folder),
            video_crf=args.video_crf,
            video_preset=args.video_preset,
            video_resize=args.video_resize,
            image_quality=args.image_quality,
            image_resize=args.image_resize,
            recursive=args.recursive,
            overwrite=args.overwrite,
            ffmpeg_path=args.ffmpeg_path,
            progress_interval=args.progress_interval,
            keep_if_larger=args.keep_if_larger,
            backup_dir=Path(args.backup_dir) if args.backup_dir else None,
            preserve_format=args.preserve_format,
            preserve_timestamps=args.preserve_timestamps,
            min_size=min_size,
            max_size=max_size,
            output_dir=Path(args.output_dir) if args.output_dir else None,
            video_resolution=args.video_resolution
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
            'video_resize': args.video_resize,
            'image_quality': args.image_quality,
            'image_resize': args.image_resize,
            'recursive': args.recursive,
            'overwrite': args.overwrite,
            'keep_if_larger': args.keep_if_larger,
            'progress_interval': args.progress_interval,
            'preserve_format': args.preserve_format,
            'preserve_timestamps': args.preserve_timestamps,
        }
        if args.ffmpeg_path:
            cmd_args['ffmpeg_path'] = args.ffmpeg_path
        if args.backup_dir:
            cmd_args['backup_dir'] = args.backup_dir
        if args.min_size:
            cmd_args['min_size'] = args.min_size
        if args.max_size:
            cmd_args['max_size'] = args.max_size
        if args.output_dir:
            cmd_args['output_dir'] = args.output_dir
        if args.video_resolution:
            cmd_args['video_resolution'] = args.video_resolution
        
        report_generator = ReportGenerator(Path.cwd())
        report_paths = report_generator.generate(stats, compressed_folder_name, recursive=args.recursive, cmd_args=cmd_args, run_uuid=run_uuid)
        
        # Update cumulative statistics
        try:
            # Use absolute path to ensure correct resolution
            script_dir = Path(__file__).resolve().parent
            statistics_dir = script_dir / "statistics"
            stats_manager = StatisticsManager(statistics_dir)
            stats_manager.update_cumulative_stats(stats)
            # Build command string for logging
            command_string = build_command_string()
            stats_manager.append_to_files_log(stats.get('files', []), run_uuid, cmd_args, stats, command_string)
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
        
        # Calculate and display size reduction
        original_size = stats.get('total_original_size', 0)
        compressed_size = stats.get('total_compressed_size', 0)
        space_saved = stats.get('space_saved', 0)
        
        if original_size > 0:
            reduction_percent = (space_saved / original_size) * 100
            print(f"Size: {format_size(original_size)} → {format_size(compressed_size)} ({reduction_percent:.1f}% reduction)")
            print(f"Space saved: {format_size(space_saved)}")
        else:
            print(f"Space saved: {format_size(space_saved)}")
        
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
