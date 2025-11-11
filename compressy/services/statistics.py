import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from compressy.utils.format import format_size


# ============================================================================
# Statistics Tracker
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
            "files": [],
            # Type-level statistics
            "videos_processed": 0,
            "images_processed": 0,
            "videos_skipped": 0,
            "images_skipped": 0,
            "videos_errors": 0,
            "images_errors": 0,
            "videos_original_size": 0,
            "videos_compressed_size": 0,
            "videos_space_saved": 0,
            "images_original_size": 0,
            "images_compressed_size": 0,
            "images_space_saved": 0,
            # Format-level statistics
            "format_stats": {},
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
                "files": [],
                # Type-level statistics
                "videos_processed": 0,
                "images_processed": 0,
                "videos_skipped": 0,
                "images_skipped": 0,
                "videos_errors": 0,
                "images_errors": 0,
                "videos_original_size": 0,
                "videos_compressed_size": 0,
                "videos_space_saved": 0,
                "images_original_size": 0,
                "images_compressed_size": 0,
                "images_space_saved": 0,
                # Format-level statistics
                "format_stats": {},
            }

    def add_file_info(self, file_info: Dict, folder_key: str = "root") -> None:
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

    def _initialize_format_stats(self, format_stats: Dict, extension: str) -> None:
        """Initialize format statistics for a given extension if not exists."""
        if extension not in format_stats:
            format_stats[extension] = {
                "count": 0,
                "original_size": 0,
                "compressed_size": 0,
                "space_saved": 0,
            }

    def update_stats(
        self,
        original_size: int,
        compressed_size: int,
        space_saved: int,
        status: str,
        folder_key: str = "root",
        file_type: Optional[str] = None,
        file_extension: Optional[str] = None,
    ) -> None:
        """
        Update statistics with file processing results.

        Args:
            original_size: Original file size
            compressed_size: Compressed file size
            space_saved: Space saved
            status: Processing status ("processed", "skipped", "error")
            folder_key: Folder key for recursive mode
            file_type: File type ("video" or "image")
            file_extension: File extension without dot (e.g., "mp4", "jpg")
        """
        if status in {"processed", "skipped"}:
            self._apply_format_stats(
                status,
                file_extension,
                original_size,
                compressed_size,
                space_saved,
                folder_key,
            )

        if status == "processed":
            self._record_processed(
                original_size,
                compressed_size,
                space_saved,
                folder_key,
                file_type,
                file_extension,
            )
        elif status == "skipped":
            self._record_skipped(
                original_size,
                compressed_size,
                folder_key,
                file_type,
            )
        elif status == "error":
            self._record_error(folder_key, file_type)

    def _apply_format_stats(
        self,
        status: str,
        file_extension: Optional[str],
        original_size: int,
        compressed_size: int,
        space_saved: int,
        folder_key: str,
    ) -> None:
        if not file_extension:
            return

        self._update_format_stats_for_container(
            self.stats,
            file_extension,
            status,
            original_size,
            compressed_size,
            space_saved,
        )

        if self.recursive:
            folder_stat = self._get_folder_stats(folder_key)
            self._update_format_stats_for_container(
                folder_stat,
                file_extension,
                status,
                original_size,
                compressed_size,
                space_saved,
            )

    def _update_format_stats_for_container(
        self,
        container: Dict,
        file_extension: str,
        status: str,
        original_size: int,
        compressed_size: int,
        space_saved: int,
    ) -> None:
        self._initialize_format_stats(container["format_stats"], file_extension)
        stats = container["format_stats"][file_extension]
        stats["count"] += 1
        stats["original_size"] += original_size
        stats["compressed_size"] += compressed_size
        if status == "processed":
            stats["space_saved"] += space_saved

    def _record_processed(
        self,
        original_size: int,
        compressed_size: int,
        space_saved: int,
        folder_key: str,
        file_type: Optional[str],
        file_extension: Optional[str],
    ) -> None:
        self.stats["processed"] += 1
        self.stats["total_compressed_size"] += compressed_size
        self.stats["space_saved"] += space_saved
        self._update_type_totals(self.stats, file_type, "processed", original_size, compressed_size, space_saved)

        if self.recursive:
            folder_stat = self._get_folder_stats(folder_key)
            folder_stat["processed"] += 1
            folder_stat["total_compressed_size"] += compressed_size
            folder_stat["space_saved"] += space_saved
            self._update_type_totals(folder_stat, file_type, "processed", original_size, compressed_size, space_saved)

    def _record_skipped(
        self,
        original_size: int,
        compressed_size: int,
        folder_key: str,
        file_type: Optional[str],
    ) -> None:
        self.stats["skipped"] += 1
        self.stats["total_compressed_size"] += compressed_size
        self._update_type_totals(self.stats, file_type, "skipped", original_size, compressed_size, 0)

        if self.recursive:
            folder_stat = self._get_folder_stats(folder_key)
            folder_stat["skipped"] += 1
            folder_stat["total_compressed_size"] += compressed_size
            self._update_type_totals(folder_stat, file_type, "skipped", original_size, compressed_size, 0)

    def _record_error(self, folder_key: str, file_type: Optional[str]) -> None:
        self.stats["errors"] += 1
        self._update_type_totals(self.stats, file_type, "error", 0, 0, 0)

        if self.recursive:
            folder_stat = self._get_folder_stats(folder_key)
            folder_stat["errors"] += 1
            self._update_type_totals(folder_stat, file_type, "error", 0, 0, 0)

    def _update_type_totals(
        self,
        container: Dict,
        file_type: Optional[str],
        status: str,
        original_size: int,
        compressed_size: int,
        space_saved: int,
    ) -> None:
        if file_type not in {"video", "image"}:
            return

        prefix = "videos" if file_type == "video" else "images"

        if status == "processed":
            container[f"{prefix}_processed"] += 1
            container[f"{prefix}_original_size"] += original_size
            container[f"{prefix}_compressed_size"] += compressed_size
            container[f"{prefix}_space_saved"] += space_saved
        elif status == "skipped":
            container[f"{prefix}_skipped"] += 1
            container[f"{prefix}_original_size"] += original_size
            container[f"{prefix}_compressed_size"] += compressed_size
        elif status == "error":
            container[f"{prefix}_errors"] += 1

    def _get_folder_stats(self, folder_key: str) -> Dict:
        self.initialize_folder_stats(folder_key)
        return self.stats["folder_stats"][folder_key]

    def add_total_file(self, original_size: int, folder_key: str = "root") -> None:
        """Add a file to total count."""
        self.stats["total_files"] += 1
        self.stats["total_original_size"] += original_size

        if self.recursive:
            self.initialize_folder_stats(folder_key)
            self.stats["folder_stats"][folder_key]["total_files"] += 1
            self.stats["folder_stats"][folder_key]["total_original_size"] += original_size

    def add_total_file_size(self, original_size: int, folder_key: str = "root") -> None:
        """Add file size to total (but don't increment global total_files counter).

        Note: In recursive mode, this DOES increment folder-level total_files
        to ensure per-folder reports are generated correctly.
        """
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
# Statistics Manager
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
            # Type-level statistics
            "total_videos_processed": 0,
            "total_images_processed": 0,
            "total_videos_skipped": 0,
            "total_images_skipped": 0,
            "total_videos_errors": 0,
            "total_images_errors": 0,
            "total_videos_original_size_bytes": 0,
            "total_videos_compressed_size_bytes": 0,
            "total_videos_space_saved_bytes": 0,
            "total_images_original_size_bytes": 0,
            "total_images_compressed_size_bytes": 0,
            "total_images_space_saved_bytes": 0,
            # Format statistics (stored as JSON string)
            "format_stats_json": "{}",
            "last_updated": None,
        }

        if not self.cumulative_stats_file.exists():
            return default_stats

        try:
            with open(self.cumulative_stats_file, "r", newline="", encoding="utf-8") as f:
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
                    # Type-level statistics (with backward compatibility)
                    "total_videos_processed": safe_int(row.get("total_videos_processed")),
                    "total_images_processed": safe_int(row.get("total_images_processed")),
                    "total_videos_skipped": safe_int(row.get("total_videos_skipped")),
                    "total_images_skipped": safe_int(row.get("total_images_skipped")),
                    "total_videos_errors": safe_int(row.get("total_videos_errors")),
                    "total_images_errors": safe_int(row.get("total_images_errors")),
                    "total_videos_original_size_bytes": safe_int(row.get("total_videos_original_size_bytes")),
                    "total_videos_compressed_size_bytes": safe_int(row.get("total_videos_compressed_size_bytes")),
                    "total_videos_space_saved_bytes": safe_int(row.get("total_videos_space_saved_bytes")),
                    "total_images_original_size_bytes": safe_int(row.get("total_images_original_size_bytes")),
                    "total_images_compressed_size_bytes": safe_int(row.get("total_images_compressed_size_bytes")),
                    "total_images_space_saved_bytes": safe_int(row.get("total_images_space_saved_bytes")),
                    # Format statistics
                    "format_stats_json": row.get("format_stats_json", "{}"),
                    "last_updated": row.get("last_updated") or None,
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

        # Update type-level statistics
        cumulative["total_videos_processed"] += run_stats.get("videos_processed", 0)
        cumulative["total_images_processed"] += run_stats.get("images_processed", 0)
        cumulative["total_videos_skipped"] += run_stats.get("videos_skipped", 0)
        cumulative["total_images_skipped"] += run_stats.get("images_skipped", 0)
        cumulative["total_videos_errors"] += run_stats.get("videos_errors", 0)
        cumulative["total_images_errors"] += run_stats.get("images_errors", 0)
        cumulative["total_videos_original_size_bytes"] += run_stats.get("videos_original_size", 0)
        cumulative["total_videos_compressed_size_bytes"] += run_stats.get("videos_compressed_size", 0)
        cumulative["total_videos_space_saved_bytes"] += run_stats.get("videos_space_saved", 0)
        cumulative["total_images_original_size_bytes"] += run_stats.get("images_original_size", 0)
        cumulative["total_images_compressed_size_bytes"] += run_stats.get("images_compressed_size", 0)
        cumulative["total_images_space_saved_bytes"] += run_stats.get("images_space_saved", 0)

        # Update format statistics
        run_format_stats = run_stats.get("format_stats", {})
        cumulative_format_stats = json.loads(cumulative.get("format_stats_json", "{}"))

        for format_ext, format_data in run_format_stats.items():
            if format_ext not in cumulative_format_stats:
                cumulative_format_stats[format_ext] = {
                    "count": 0,
                    "original_size": 0,
                    "compressed_size": 0,
                    "space_saved": 0,
                }
            cumulative_format_stats[format_ext]["count"] += format_data.get("count", 0)
            cumulative_format_stats[format_ext]["original_size"] += format_data.get("original_size", 0)
            cumulative_format_stats[format_ext]["compressed_size"] += format_data.get("compressed_size", 0)
            cumulative_format_stats[format_ext]["space_saved"] += format_data.get("space_saved", 0)

        cumulative["format_stats_json"] = json.dumps(cumulative_format_stats)
        cumulative["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.save_cumulative_stats(cumulative)

    def save_cumulative_stats(self, stats: Dict) -> None:
        """
        Save cumulative statistics to CSV file.

        Args:
            stats: Dictionary with cumulative statistics
        """
        try:
            with open(self.cumulative_stats_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "total_runs",
                        "total_files_processed",
                        "total_files_skipped",
                        "total_files_errors",
                        "total_original_size_bytes",
                        "total_compressed_size_bytes",
                        "total_space_saved_bytes",
                        "total_videos_processed",
                        "total_images_processed",
                        "total_videos_skipped",
                        "total_images_skipped",
                        "total_videos_errors",
                        "total_images_errors",
                        "total_videos_original_size_bytes",
                        "total_videos_compressed_size_bytes",
                        "total_videos_space_saved_bytes",
                        "total_images_original_size_bytes",
                        "total_images_compressed_size_bytes",
                        "total_images_space_saved_bytes",
                        "format_stats_json",
                        "last_updated",
                    ],
                )
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

            with open(self.run_history_file, "a", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "timestamp",
                    "source_folder",
                    "files_processed",
                    "files_skipped",
                    "files_errors",
                    "space_saved_bytes",
                    "videos_processed",
                    "images_processed",
                    "videos_original_size_bytes",
                    "videos_compressed_size_bytes",
                    "videos_space_saved_bytes",
                    "images_original_size_bytes",
                    "images_compressed_size_bytes",
                    "images_space_saved_bytes",
                    "format_stats_json",
                    "processing_time_seconds",
                    "video_crf",
                    "image_quality",
                    "recursive",
                    "overwrite",
                ]

                writer = csv.DictWriter(f, fieldnames=fieldnames)

                # Write header if file is new
                if not file_exists:
                    writer.writeheader()

                # Prepare run record
                format_stats_json = json.dumps(run_stats.get("format_stats", {}))
                run_record = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source_folder": cmd_args.get("source_folder", "N/A"),
                    "files_processed": run_stats.get("processed", 0),
                    "files_skipped": run_stats.get("skipped", 0),
                    "files_errors": run_stats.get("errors", 0),
                    "space_saved_bytes": run_stats.get("space_saved", 0),
                    "videos_processed": run_stats.get("videos_processed", 0),
                    "images_processed": run_stats.get("images_processed", 0),
                    "videos_original_size_bytes": run_stats.get("videos_original_size", 0),
                    "videos_compressed_size_bytes": run_stats.get("videos_compressed_size", 0),
                    "videos_space_saved_bytes": run_stats.get("videos_space_saved", 0),
                    "images_original_size_bytes": run_stats.get("images_original_size", 0),
                    "images_compressed_size_bytes": run_stats.get("images_compressed_size", 0),
                    "images_space_saved_bytes": run_stats.get("images_space_saved", 0),
                    "format_stats_json": format_stats_json,
                    "processing_time_seconds": run_stats.get("total_processing_time", 0.0),
                    "video_crf": cmd_args.get("video_crf", "N/A"),
                    "image_quality": cmd_args.get("image_quality", "N/A"),
                    "recursive": cmd_args.get("recursive", False),
                    "overwrite": cmd_args.get("overwrite", False),
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
            print("\n" + "=" * 60)
            print("No Statistics Available")
            print("=" * 60)
            print("Statistics will be created after your first compression run.")
            return

        print("\n" + "=" * 60)
        print("Cumulative Compression Statistics")
        print("=" * 60)
        print(f"Total Runs: {stats['total_runs']}")
        print(f"Last Updated: {stats['last_updated'] or 'N/A'}")

        self._print_file_statistics(stats)
        self._print_type_breakdown(stats)
        self._print_size_statistics(stats)
        self._print_size_by_type(stats)
        self._print_format_breakdown(stats)

        print("=" * 60)

    def _print_file_statistics(self, stats: Dict) -> None:
        print()
        print("File Statistics:")
        print(f"  Processed: {stats['total_files_processed']:,} files")
        print(f"  Skipped: {stats['total_files_skipped']:,} files")
        print(f"  Errors: {stats['total_files_errors']:,} files")

    def _print_type_breakdown(self, stats: Dict) -> None:
        videos_processed = stats.get("total_videos_processed", 0)
        images_processed = stats.get("total_images_processed", 0)
        videos_skipped = stats.get("total_videos_skipped", 0)
        images_skipped = stats.get("total_images_skipped", 0)
        videos_errors = stats.get("total_videos_errors", 0)
        images_errors = stats.get("total_images_errors", 0)

        if videos_processed == 0 and images_processed == 0:
            return

        print()
        print("By Type:")
        if videos_processed > 0 or videos_skipped > 0 or videos_errors > 0:
            print(f"  Videos: {videos_processed:,} processed, {videos_skipped:,} skipped, {videos_errors:,} errors")
        if images_processed > 0 or images_skipped > 0 or images_errors > 0:
            print(f"  Images: {images_processed:,} processed, {images_skipped:,} skipped, {images_errors:,} errors")

    def _print_size_statistics(self, stats: Dict) -> None:
        print()
        print("Size Statistics:")
        original_size = stats["total_original_size_bytes"]
        compressed_size = stats["total_compressed_size_bytes"]
        space_saved = stats["total_space_saved_bytes"]

        print(f"  Original Size: {format_size(original_size)}")
        print(f"  Compressed Size: {format_size(compressed_size)}")
        print(f"  Space Saved: {format_size(space_saved)}")

        if original_size > 0:
            compression_ratio = (space_saved / original_size) * 100
            print(f"  Overall Compression: {compression_ratio:.2f}%")

    def _print_size_by_type(self, stats: Dict) -> None:
        videos_original = stats.get("total_videos_original_size_bytes", 0)
        videos_compressed = stats.get("total_videos_compressed_size_bytes", 0)
        videos_space_saved = stats.get("total_videos_space_saved_bytes", 0)
        images_original = stats.get("total_images_original_size_bytes", 0)
        images_compressed = stats.get("total_images_compressed_size_bytes", 0)
        images_space_saved = stats.get("total_images_space_saved_bytes", 0)

        if videos_original == 0 and images_original == 0:
            return

        print()
        print("Size by Type:")
        if videos_original > 0:
            print(
                f"  Videos: {format_size(videos_original)} → {format_size(videos_compressed)} "
                f"({format_size(videos_space_saved)} saved)"
            )
            if videos_original > 0:
                video_ratio = (videos_space_saved / videos_original) * 100
                print(f"    Compression: {video_ratio:.2f}%")
        if images_original > 0:
            print(
                f"  Images: {format_size(images_original)} → {format_size(images_compressed)} "
                f"({format_size(images_space_saved)} saved)"
            )
            if images_original > 0:
                image_ratio = (images_space_saved / images_original) * 100
                print(f"    Compression: {image_ratio:.2f}%")

    def _print_format_breakdown(self, stats: Dict) -> None:
        format_stats = self._load_format_stats(stats.get("format_stats_json", "{}"))
        if not format_stats:
            return

        sorted_formats = sorted(format_stats.items(), key=lambda x: x[1].get("count", 0), reverse=True)
        formats_to_show = [(ext, data) for ext, data in sorted_formats if data.get("count", 0) > 0]

        if not formats_to_show:
            return

        print()
        print("By Format:")
        for format_ext, format_data in formats_to_show:
            count = format_data.get("count", 0)
            orig_size = format_data.get("original_size", 0)
            comp_size = format_data.get("compressed_size", 0)
            saved = format_data.get("space_saved", 0)
            print(
                f"  .{format_ext.upper()}: {count:,} files, "
                f"{format_size(orig_size)} → {format_size(comp_size)} "
                f"({format_size(saved)} saved)"
            )
            if orig_size > 0:
                format_ratio = (saved / orig_size) * 100
                print(f"    Compression: {format_ratio:.2f}%")

    @staticmethod
    def _load_format_stats(format_stats_json: str) -> Dict[str, Dict]:
        try:
            return json.loads(format_stats_json) if format_stats_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

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
            with open(self.run_history_file, "r", newline="", encoding="utf-8") as f:
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
            print("\n" + "=" * 60)
            print("No Run History Available")
            print("=" * 60)
            print("Run history will be created after your first compression run.")
            return

        # Reverse to show most recent first
        runs.reverse()

        if limit:
            runs = runs[:limit]

        print("\n" + "=" * 60)
        print(f"Run History ({len(runs)} of {len(self.load_run_history())} runs shown)")
        print("=" * 60)

        for idx, run in enumerate(runs, 1):
            print(f"\nRun #{idx}")
            print(f"  Timestamp: {run.get('timestamp', 'N/A')}")
            print(f"  Source Folder: {run.get('source_folder', 'N/A')}")
            print(
                f"  Files: {run.get('files_processed', 0)} processed, "
                f"{run.get('files_skipped', 0)} skipped, "
                f"{run.get('files_errors', 0)} errors"
            )

            space_saved = int(run.get("space_saved_bytes", 0))
            print(f"  Space Saved: {format_size(space_saved)}")

            time_seconds = float(run.get("processing_time_seconds", 0))
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

            print(
                f"  Settings: CRF={run.get('video_crf', 'N/A')}, "
                f"Quality={run.get('image_quality', 'N/A')}, "
                f"Recursive={run.get('recursive', 'False')}, "
                f"Overwrite={run.get('overwrite', 'False')}"
            )

        print("\n" + "=" * 60)
