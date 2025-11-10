import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from compressy.utils.logger import get_logger


# ============================================================================
# FFmpeg Executor
# ============================================================================


class FFmpegExecutor:
    """Handles FFmpeg execution and progress tracking."""

    def __init__(self, ffmpeg_path: Optional[str] = None):
        """
        Initialize FFmpeg executor.

        Args:
            ffmpeg_path: Path to FFmpeg executable. If None, will attempt to find it.
        """
        self.logger = get_logger()
        self.ffmpeg_path = ffmpeg_path or self.find_ffmpeg()
        if self.ffmpeg_path is None:
            self.logger.critical("FFmpeg not found in PATH or common locations")
            raise FileNotFoundError(
                "FFmpeg not found. Please install FFmpeg and add it to PATH, "
                "or specify the path using --ffmpeg-path option."
            )
        self.logger.debug(f"FFmpeg executor initialized with path: {self.ffmpeg_path}")

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
        frame_match = re.search(r"frame=\s*(\d+)", line)
        if frame_match:
            progress["frame"] = frame_match.group(1)

        # Extract fps
        fps_match = re.search(r"fps=\s*([\d.]+)", line)
        if fps_match:
            progress["fps"] = fps_match.group(1)

        # Extract time
        time_match = re.search(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})", line)
        if time_match:
            progress["time"] = time_match.group(1)

        # Extract bitrate
        bitrate_match = re.search(r"bitrate=\s*([\d.]+kbits/s|[\d.]+Mbits/s)", line)
        if bitrate_match:
            progress["bitrate"] = bitrate_match.group(1)

        # Extract size
        size_match = re.search(r"size=\s*(\d+[kKmMgG]?B)", line)
        if size_match:
            progress["size"] = size_match.group(1)

        # Extract speed
        speed_match = re.search(r"speed=\s*([\d.]+x)", line)
        if speed_match:
            progress["speed"] = speed_match.group(1)

        return progress if progress else None

    def run_with_progress(
        self, args: List[str], progress_interval: float = 5.0, filename: str = ""
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
        self.logger.debug(f"Executing FFmpeg command for {filename}: {' '.join(cmd)}")

        # Start FFmpeg process with unbuffered stderr
        process = self._launch_process(cmd)

        stderr_lines = self._collect_progress(process, progress_interval)
        stdout, stderr_lines = self._finalize_process(process, stderr_lines)
        result = subprocess.CompletedProcess(cmd, process.returncode, stdout, "\n".join(stderr_lines))

        self._raise_on_error(result, cmd)
        return result

    def _launch_process(self, cmd: List[str]) -> subprocess.Popen:
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=0,
        )

    def _collect_progress(self, process: subprocess.Popen, progress_interval: float) -> List[str]:
        stderr_lines: List[str] = []
        last_update_time = time.time()

        while process.poll() is None:
            line = process.stderr.readline()
            if line:
                stripped = line.rstrip()
                stderr_lines.append(stripped)
                last_update_time = self._maybe_print_progress(stripped, last_update_time, progress_interval)
            time.sleep(0.1)

        return stderr_lines

    def _maybe_print_progress(self, line: str, last_update: float, interval: float) -> float:
        progress = self.parse_progress(line)
        if not progress:
            return last_update

        current_time = time.time()
        if current_time - last_update < interval:
            return last_update

        print(self._format_progress(progress))
        return current_time

    def _format_progress(self, progress: Dict[str, str]) -> str:
        segments: List[str] = []
        for key in ("time", "frame", "fps", "bitrate", "size", "speed"):
            if key in progress:
                label = key.capitalize() if key != "fps" else "FPS"
                segments.append(f"{label}: {progress[key]}")
        if not segments:
            return "  [Progress]"
        return "  [Progress] " + " | ".join(segments)

    def _finalize_process(self, process: subprocess.Popen, stderr_lines: List[str]) -> Tuple[str, List[str]]:
        stdout, remaining_stderr = process.communicate()
        if remaining_stderr:
            stderr_lines.extend(line.rstrip() for line in remaining_stderr.splitlines() if line.strip())
        return stdout, stderr_lines

    @staticmethod
    def _raise_on_error(result: subprocess.CompletedProcess, cmd: List[str]) -> None:
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
