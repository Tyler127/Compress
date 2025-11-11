import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from compressy.utils.format import format_size


# ============================================================================
# Report Generator
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
        cmd_args: Optional[Dict] = None,
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

                report_path = main_reports_dir / f"{folder_safe_name}_report.csv"
                folder_display_name = folder_key if folder_key != "." else "root"
                unique_path = self._get_unique_path(report_path)
                self._write_csv_report(
                    unique_path,
                    folder_stat,
                    folder_display_name,
                    compressed_folder_name,
                    cmd_args,
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
            aggregated_report_path = main_reports_dir / "aggregated_report.csv"
            unique_aggregated_path = self._get_unique_path(aggregated_report_path)
            self._write_csv_report(
                unique_aggregated_path,
                aggregated_stats,
                f"{compressed_folder_name} (All Folders)",
                None,
                cmd_args,
            )
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

    def _write_csv_report(
        self,
        file_path: Path,
        report_stats: Dict,
        report_title: str,
        parent_folder: Optional[str] = None,
        cmd_args: Optional[Dict] = None,
    ) -> None:
        """Write a CSV report with summary/stats as header comments and CSV data."""
        # Get unique file path if report already exists
        unique_path = self._get_unique_path(file_path)
        if unique_path != file_path:
            print(f"  Report already exists, creating: {unique_path.name}")

        with open(unique_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            self._write_report_header(writer, report_title, parent_folder)
            self._write_summary_section(writer, report_stats)
            self._write_size_statistics(writer, report_stats)
            self._write_processing_time(writer, report_stats)
            self._write_file_details(writer, report_stats)
            self._write_arguments_section(writer, cmd_args)

    def _write_report_header(self, writer: csv.writer, report_title: str, parent_folder: Optional[str]) -> None:
        writer.writerow([f"# Compression Report: {report_title}"])
        if parent_folder:
            writer.writerow([f"# Parent Folder: {parent_folder}"])
        writer.writerow([f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
        writer.writerow([])

    def _write_summary_section(self, writer: csv.writer, report_stats: Dict) -> None:
        writer.writerow(["# Summary"])
        writer.writerow(["# Total Files Found", report_stats["total_files"]])
        writer.writerow(["# Files Processed", report_stats["processed"]])
        writer.writerow(["# Files Skipped", report_stats["skipped"]])
        writer.writerow(["# Errors", report_stats["errors"]])
        writer.writerow([])

    def _write_size_statistics(self, writer: csv.writer, report_stats: Dict) -> None:
        total_compression_ratio = (
            (report_stats["space_saved"] / report_stats["total_original_size"] * 100)
            if report_stats["total_original_size"] > 0
            else 0
        )
        writer.writerow(["# Size Statistics"])
        writer.writerow(["# Total Original Size", format_size(report_stats["total_original_size"])])
        writer.writerow(["# Total Compressed Size", format_size(report_stats["total_compressed_size"])])
        writer.writerow(["# Total Space Saved", format_size(report_stats["space_saved"])])
        writer.writerow(["# Overall Compression Ratio", f"{total_compression_ratio:.2f}%"])

    def _write_processing_time(self, writer: csv.writer, report_stats: Dict) -> None:
        total_time = report_stats.get("total_processing_time", 0)
        if total_time > 0:
            writer.writerow(["# Total Processing Time", self._format_processing_time(total_time)])
        writer.writerow([])

    @staticmethod
    def _format_processing_time(total_time: float) -> str:
        hours = int(total_time // 3600)
        minutes = int((total_time % 3600) // 60)
        seconds = total_time % 60
        if hours > 0:
            return f"{hours}h {minutes}m {seconds:.1f}s"
        if minutes > 0:
            return f"{minutes}m {seconds:.1f}s"
        return f"{seconds:.1f}s"

    def _write_file_details(self, writer: csv.writer, report_stats: Dict) -> None:
        if not report_stats["files"]:
            return

        writer.writerow(["# File Details"])
        writer.writerow(
            [
                "Filename",
                "Original Size",
                "Compressed Size",
                "Space Saved",
                "Compression Ratio (%)",
                "Processing Time (s)",
                "Status",
            ]
        )

        for file_info in report_stats["files"]:
            processing_time = file_info.get("processing_time", 0)
            writer.writerow(
                [
                    file_info["name"],
                    format_size(file_info["original_size"]),
                    format_size(file_info["compressed_size"]),
                    format_size(file_info["space_saved"]),
                    f"{file_info['compression_ratio']:.2f}",
                    f"{processing_time:.2f}",
                    file_info["status"],
                ]
            )
        writer.writerow([])

    def _write_arguments_section(self, writer: csv.writer, cmd_args: Optional[Dict]) -> None:
        if not cmd_args:
            return

        writer.writerow(["# Arguments"])
        writer.writerow(["# Source Folder", cmd_args.get("source_folder", "N/A")])
        writer.writerow(["# Video CRF", cmd_args.get("video_crf", "N/A")])
        writer.writerow(["# Video Preset", cmd_args.get("video_preset", "N/A")])
        writer.writerow(["# Image Quality", cmd_args.get("image_quality", "N/A")])
        if cmd_args.get("image_resize"):
            writer.writerow(["# Image Resize", f"{cmd_args.get('image_resize')}%"])
        writer.writerow(["# Recursive", cmd_args.get("recursive", "N/A")])
        writer.writerow(["# Overwrite", cmd_args.get("overwrite", "N/A")])
        writer.writerow(["# Keep If Larger", cmd_args.get("keep_if_larger", "N/A")])
        writer.writerow(["# Progress Interval", cmd_args.get("progress_interval", "N/A")])
        if cmd_args.get("ffmpeg_path"):
            writer.writerow(["# FFmpeg Path", cmd_args.get("ffmpeg_path")])
        if cmd_args.get("backup_dir"):
            writer.writerow(["# Backup Directory", cmd_args.get("backup_dir")])
