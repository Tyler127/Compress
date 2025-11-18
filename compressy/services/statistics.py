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
            # Format-level statistics (processed files only)
            "processed_file_format_stats": {},
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
                "processed_file_format_stats": {},
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
        """Initialize processed format statistics for a given extension if not exists."""
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
        if status == "processed":
            self._apply_format_stats(
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
                original_size,
                folder_key,
                file_type,
            )
        elif status == "error":
            self._record_error(folder_key, file_type)

    def _apply_format_stats(
        self,
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
            original_size,
            compressed_size,
            space_saved,
        )

        if self.recursive:
            folder_stat = self._get_folder_stats(folder_key)
            self._update_format_stats_for_container(
                folder_stat,
                file_extension,
                original_size,
                compressed_size,
                space_saved,
            )

    def _update_format_stats_for_container(
        self,
        container: Dict,
        file_extension: str,
        original_size: int,
        compressed_size: int,
        space_saved: int,
    ) -> None:
        self._initialize_format_stats(container["processed_file_format_stats"], file_extension)
        stats = container["processed_file_format_stats"][file_extension]
        stats["count"] += 1
        stats["original_size"] += original_size
        stats["compressed_size"] += compressed_size
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
        self.cumulative_stats_file = self.statistics_dir / "statistics.json"
        self.files_log_file = self.statistics_dir / "files.json"

    def load_cumulative_stats(self) -> Dict:
        """
        Load existing cumulative statistics from JSON file.

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
            # Format statistics (stored as nested dict)
            "processed_file_format_stats": {},
            "last_updated": None,
        }

        if not self.cumulative_stats_file.exists():
            return default_stats

        try:
            with open(self.cumulative_stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)

                # Ensure all required fields exist with defaults
                # Replace None values and missing keys with defaults
                for key, default_value in default_stats.items():
                    if key not in stats or stats[key] is None:
                        stats[key] = default_value

                return stats
        except (json.JSONDecodeError, ValueError) as e:
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

        # Update format statistics (now stored as nested dict)
        run_format_stats = run_stats.get("processed_file_format_stats", {})
        cumulative_format_stats = cumulative.get("processed_file_format_stats", {})

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

        cumulative["processed_file_format_stats"] = cumulative_format_stats
        cumulative["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.save_cumulative_stats(cumulative)

    def save_cumulative_stats(self, stats: Dict) -> None:
        """
        Save cumulative statistics to JSON file.

        Args:
            stats: Dictionary with cumulative statistics
        """
        try:
            with open(self.cumulative_stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
        except PermissionError:
            print(f"Warning: Permission denied when writing to {self.cumulative_stats_file}")
        except Exception as e:
            print(f"Warning: Error saving cumulative statistics ({e})")

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
        # Format-level breakdown (only show formats with count > 0)
        format_stats = stats.get("processed_file_format_stats", {})
        if not format_stats:
            return

        # Sort formats by count (descending)
        sorted_formats = sorted(format_stats.items(), key=lambda x: x[1].get("count", 0), reverse=True)
        # Only show formats with count > 0
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

        print("=" * 60)

    def print_history(self, limit: Optional[int] = None) -> None:
        """
        Print run history in a nice format from files.json.

        Args:
            limit: Maximum number of runs to display (None for all)
        """
        files_log = self.load_files_log()

        if not files_log:
            print("\n" + "=" * 60)
            print("No Run History Available")
            print("=" * 60)
            print("Run history will be created after your first compression run.")
            return

        # Convert to list and sort by timestamp (most recent first)
        runs = []
        for timestamp, entry in files_log.items():
            metadata = entry.get("metadata", {})
            run_data = {
                "timestamp": timestamp,
                "run_id": metadata.get("run_uuid", "N/A"),
                "source_folder": metadata.get("source_folder", "N/A"),
                "command": metadata.get("command"),
                "video_crf": metadata.get("video_crf"),
                "image_quality": metadata.get("image_quality"),
                "recursive": metadata.get("recursive", False),
                "overwrite": metadata.get("overwrite", False),
            }
            # Add stats if available
            stats = entry.get("stats", {})
            run_data.update(
                {
                    "files_processed": stats.get("files_processed", 0),
                    "files_skipped": stats.get("files_skipped", 0),
                    "files_errors": stats.get("files_errors", 0),
                    "space_saved_bytes": stats.get("space_saved_bytes", 0),
                    "processing_time_seconds": stats.get("processing_time_seconds", 0.0),
                }
            )
            runs.append(run_data)

        # Sort by timestamp (most recent first)
        runs.sort(key=lambda x: x["timestamp"], reverse=True)

        if limit:
            runs = runs[:limit]

        print("\n" + "=" * 60)
        print(f"Run History ({len(runs)} of {len(files_log)} runs shown)")
        print("=" * 60)

        for idx, run in enumerate(runs, 1):
            print(f"\nRun #{idx}")
            if "run_id" in run:
                print(f"  Run ID: {run['run_id']}")
            print(f"  Timestamp: {run.get('timestamp', 'N/A')}")
            print(f"  Source Folder: {run.get('source_folder', 'N/A')}")
            print(
                f"  Files: {run.get('files_processed', 0)} processed, "
                f"{run.get('files_skipped', 0)} skipped, "
                f"{run.get('files_errors', 0)} errors"
            )

            space_saved = run.get("space_saved_bytes", 0)
            print(f"  Space Saved: {format_size(space_saved)}")

            time_seconds = run.get("processing_time_seconds", 0)
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
                f"Recursive={run.get('recursive', False)}, "
                f"Overwrite={run.get('overwrite', False)}"
            )

            # Print command if available
            command = run.get("command", None)
            if command and command != "N/A":
                print(f"  Command: {command}")

        print("\n" + "=" * 60)

    def load_files_log(self) -> Dict[str, Dict]:  # noqa: C901
        """
        Load complete file processing history from files.json.

        Returns:
            Dictionary keyed by timestamp, each containing run_uuid and files array
        """
        if not self.files_log_file.exists():
            return {}

        try:
            with open(self.files_log_file, "r", encoding="utf-8") as f:
                files_log = json.load(f)
            # Handle both old format (list) and new format (dict)
            if isinstance(files_log, list):
                # Convert old format (list) to new format (dict)
                converted = {}
                for file_record in files_log:
                    timestamp = file_record.get("timestamp", "")
                    run_id = file_record.get("run_id", "")
                    if timestamp not in converted:
                        converted[timestamp] = {"run_uuid": run_id, "files": []}
                    # Remove timestamp and run_id from file record
                    file_record_copy = {k: v for k, v in file_record.items() if k not in ("timestamp", "run_id")}
                    converted[timestamp]["files"].append(file_record_copy)
                return converted

            # Handle old format with timestamp_run_uuid keys - convert to timestamp-only keys
            if isinstance(files_log, dict):
                converted = {}
                for key, value in files_log.items():
                    # Check if key contains underscore (old format: timestamp_uuid)
                    if "_" in key and isinstance(value, dict) and "run_uuid" in value:
                        # Extract timestamp (everything before the last underscore)
                        # But actually, we want to split on the first underscore after the timestamp
                        # Timestamp format is "YYYY-MM-DD HH:MM:SS", so we split on the first underscore after the space
                        parts = key.split("_", 1)
                        if len(parts) == 2:
                            timestamp = parts[0]
                            # If timestamp already exists, merge files (multiple runs at same timestamp)
                            if timestamp in converted:
                                converted[timestamp]["files"].extend(value.get("files", []))
                            else:
                                converted[timestamp] = value
                        else:
                            # Fallback: use key as-is if we can't parse it
                            # This branch is unreachable: split("_", 1) always returns 2 elements if "_" is in key
                            converted[key] = value  # pragma: no cover
                    else:
                        # Already in new format (timestamp-only key)
                        converted[key] = value
                return converted

            # This return is unreachable: json.load() always returns dict or list (or raises)
            return {}  # pragma: no cover
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Error reading files log ({e})")
            return {}
        except Exception as e:
            print(f"Warning: Error reading files log ({e})")
            return {}

    def append_to_files_log(  # noqa: C901
        self, files_data: List[Dict], run_uuid: str, cmd_args: Dict, run_stats: Dict = None, command: str = None
    ) -> None:
        """
        Append files from current run to files.json.

        Args:
            files_data: List of file info dictionaries from current run
            run_uuid: Unique identifier for this compression run
            cmd_args: Command line arguments used for this run
            run_stats: Statistics dictionary from current compression run (optional)
            command: Exact command string used to run compressy (optional)
        """
        try:
            # Load existing files log
            files_log = self.load_files_log()

            # Process each file and add to log
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Use timestamp as key (if multiple runs happen at same timestamp, they'll be grouped together)
            # Initialize run entry if it doesn't exist
            if timestamp not in files_log:
                files_log[timestamp] = {"metadata": {}, "stats": {}, "files": []}

            # Add run metadata (all command arguments and run info)
            metadata = {
                "run_uuid": run_uuid,
            }
            if command:
                metadata["command"] = command

            # Add all command arguments to metadata
            for key, value in cmd_args.items():
                if value is not None:
                    metadata[key] = value

            files_log[timestamp]["metadata"] = metadata

            # Add stats if provided (only statistical data, no metadata)
            if run_stats is not None:
                stats = {
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
                    "processed_file_format_stats": run_stats.get("processed_file_format_stats", {}),
                    "processing_time_seconds": run_stats.get("total_processing_time", 0.0),
                }
                files_log[timestamp]["stats"] = stats

            # Process all files for this run
            run_files = []
            for file_info in files_data:
                # Extract file type and format from name
                file_name = file_info.get("name", "")
                file_extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

                # Determine file type based on extension
                video_extensions = ["mp4", "avi", "mov", "mkv", "flv", "wmv", "webm", "m4v"]
                image_extensions = ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "svg"]

                if file_extension in video_extensions:
                    file_type = "video"
                elif file_extension in image_extensions:
                    file_type = "image"
                else:
                    file_type = "unknown"

                # Build modifications dict - only include non-null values that were actually applied
                modifications = {}

                # Only include "compressed" if the file was actually compressed
                if file_info.get("status") in ("success"):
                    modifications["compressed"] = True

                # Only include video-related modifications if it's a video and values are not None
                if file_type == "video":
                    if cmd_args.get("video_crf") is not None:
                        modifications["video_crf"] = cmd_args.get("video_crf")
                    if cmd_args.get("video_preset") is not None:
                        modifications["video_preset"] = cmd_args.get("video_preset")
                    if cmd_args.get("video_resize") is not None:
                        modifications["video_resize"] = cmd_args.get("video_resize")
                    if cmd_args.get("video_resolution") is not None:
                        modifications["video_resolution"] = cmd_args.get("video_resolution")

                # Only include image-related modifications if it's an image and values are not None
                if file_type == "image":
                    if cmd_args.get("image_quality") is not None:
                        modifications["image_quality"] = cmd_args.get("image_quality")
                    if cmd_args.get("image_resize") is not None:
                        modifications["image_resize"] = cmd_args.get("image_resize")

                # Create file record (without timestamp and run_id)
                file_record = {
                    "file_name": file_name,
                    "original_path": file_info.get("original_path", "N/A"),
                    "new_path": file_info.get("new_path", "N/A"),
                    "file_type": file_type,
                    "format": file_extension,
                    "modifications": modifications,
                    "size_before_bytes": file_info.get("original_size", 0),
                    "size_after_bytes": file_info.get("compressed_size", 0),
                    "space_saved_bytes": file_info.get("space_saved", 0),
                    "compression_ratio_percent": file_info.get("compression_ratio", 0.0),
                    "processing_time_seconds": file_info.get("processing_time", 0.0),
                    "status": file_info.get("status", "unknown"),
                }

                run_files.append(file_record)

            # Add all files to the run entry
            files_log[timestamp]["files"].extend(run_files)

            # Save updated files log
            with open(self.files_log_file, "w", encoding="utf-8") as f:
                json.dump(files_log, f, indent=2)
        except PermissionError:
            print(f"Warning: Permission denied when writing to {self.files_log_file}")
        except Exception as e:
            print(f"Warning: Error saving files log ({e})")
