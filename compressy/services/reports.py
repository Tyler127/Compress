import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# ============================================================================
# Report Generator
# ============================================================================


class ReportGenerator:
    """Generates JSON reports with compression statistics."""

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
        cmd_args: Optional[Dict] = None,
        run_uuid: Optional[str] = None,
    ) -> List[Path]:
        """
        Generate JSON report(s) with compression statistics.

        If recursive=True and folder_stats exist, generates one report per subfolder.
        Otherwise, generates a single report.

        Args:
            stats: Statistics dictionary from compression
            compressed_folder_name: Name of the compressed folder
            recursive: Whether to generate per-folder reports
            cmd_args: Command line arguments for report
            run_uuid: Unique identifier for this compression run

        Returns:
            List of report file paths.
        """
        reports_dir = self.output_dir / "reports"

        # Sanitize folder name for directory/filename
        safe_name = "".join(c for c in compressed_folder_name if c.isalnum() or c in (" ", "-", "_")).strip()
        safe_name = safe_name.replace(" ", "_")

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
                folder_safe_name = "".join(
                    c for c in folder_key if c.isalnum() or c in (" ", "-", "_", "\\", "/")
                ).strip()
                folder_safe_name = folder_safe_name.replace(" ", "_").replace("\\", "_").replace("/", "_")
                if not folder_safe_name or folder_safe_name == ".":
                    folder_safe_name = "root"

                report_path = main_reports_dir / f"{folder_safe_name}_report.json"
                folder_display_name = folder_key if folder_key != "." else "root"
                unique_path = self._get_unique_path(report_path)
                self._write_json_report(
                    unique_path,
                    folder_stat,
                    folder_display_name,
                    compressed_folder_name,
                    cmd_args,
                    run_uuid,
                )
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
                "files": [],
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
            aggregated_report_path = main_reports_dir / "aggregated_report.json"
            unique_aggregated_path = self._get_unique_path(aggregated_report_path)
            self._write_json_report(
                unique_aggregated_path,
                aggregated_stats,
                f"{compressed_folder_name} (All Folders)",
                None,
                cmd_args,
                run_uuid,
            )
            report_paths.append(unique_aggregated_path)
            print(f"✓ Aggregated report generated: {unique_aggregated_path}")

        else:
            # Generate single report (non-recursive or no folder_stats)
            reports_dir.mkdir(parents=True, exist_ok=True)
            report_path = reports_dir / f"{safe_name}_report.json"
            unique_path = self._get_unique_path(report_path)
            self._write_json_report(unique_path, stats, compressed_folder_name, None, cmd_args, run_uuid)
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
        match = re.match(r"^(.+?)(\s*\(\d+\))?$", base_name)
        if match:
            base_name_only = match.group(1).strip()
        else:
            base_name_only = base_name

        # Find the highest existing number
        existing_numbers = []
        pattern = re.compile(re.escape(base_name_only) + r"\s*\((\d+)\)" + re.escape(suffix))
        for file in parent_dir.glob(f"{base_name_only}*{suffix}"):
            match = pattern.match(file.name)
            if match:
                existing_numbers.append(int(match.group(1)))

        # Start from the next number after the highest, or 1 if none exist
        counter = (max(existing_numbers) + 1) if existing_numbers else 1

        new_name = f"{base_name_only} ({counter}){suffix}"
        return parent_dir / new_name

    def _write_json_report(
        self,
        file_path: Path,
        report_stats: Dict,
        report_title: str,
        parent_folder: Optional[str] = None,
        cmd_args: Optional[Dict] = None,
        run_uuid: Optional[str] = None,
    ) -> None:
        """Write a JSON report with structured compression statistics."""
        # Get unique file path if report already exists
        unique_path = self._get_unique_path(file_path)
        if unique_path != file_path:
            print(f"  Report already exists, creating: {unique_path.name}")

        # Build metadata section
        metadata = {
            "title": f"Compression Report: {report_title}",
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if parent_folder:
            metadata["parent_folder"] = parent_folder
        if run_uuid:
            metadata["run_id"] = run_uuid

        # Build summary section
        summary = {
            "total_files": report_stats["total_files"],
            "processed": report_stats["processed"],
            "skipped": report_stats["skipped"],
            "errors": report_stats["errors"],
        }

        # Build size statistics section
        total_compression_ratio = (
            (report_stats["space_saved"] / report_stats["total_original_size"] * 100)
            if report_stats["total_original_size"] > 0
            else 0
        )
        size_statistics = {
            "total_original_size_bytes": report_stats["total_original_size"],
            "total_compressed_size_bytes": report_stats["total_compressed_size"],
            "space_saved_bytes": report_stats["space_saved"],
            "compression_ratio_percent": round(total_compression_ratio, 2),
        }

        # Build processing time section
        total_time = report_stats.get("total_processing_time", 0)
        time_str = ""
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

        processing_time = {
            "total_seconds": total_time,
            "formatted": time_str,
        }

        # Build file details section
        file_details = []
        for file_info in report_stats.get("files", []):
            file_details.append(
                {
                    "name": file_info["name"],
                    "original_size_bytes": file_info["original_size"],
                    "compressed_size_bytes": file_info["compressed_size"],
                    "space_saved_bytes": file_info["space_saved"],
                    "compression_ratio_percent": round(file_info["compression_ratio"], 2),
                    "processing_time_seconds": round(file_info.get("processing_time", 0), 2),
                    "status": file_info["status"],
                }
            )

        # Build arguments section
        arguments = {}
        if cmd_args:
            arguments = {
                "source_folder": cmd_args.get("source_folder"),
                "video_crf": cmd_args.get("video_crf"),
                "video_preset": cmd_args.get("video_preset"),
                "video_resize": cmd_args.get("video_resize"),
                "image_quality": cmd_args.get("image_quality"),
                "image_resize": cmd_args.get("image_resize"),
                "recursive": cmd_args.get("recursive", False),
                "overwrite": cmd_args.get("overwrite", False),
                "keep_if_larger": cmd_args.get("keep_if_larger", False),
                "progress_interval": cmd_args.get("progress_interval"),
                "ffmpeg_path": cmd_args.get("ffmpeg_path"),
                "backup_dir": cmd_args.get("backup_dir"),
            }

        # Build complete report structure
        report = {
            "metadata": metadata,
            "summary": summary,
            "size_statistics": size_statistics,
            "processing_time": processing_time,
            "file_details": file_details,
            "arguments": arguments,
        }

        # Write JSON report
        with open(unique_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
