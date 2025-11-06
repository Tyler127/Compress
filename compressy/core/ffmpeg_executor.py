import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

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
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=0,  # Unbuffered for real-time reading
        )

        last_update_time = time.time()

        # Read stderr while process is running
        stderr_lines = []
        while process.poll() is None:
            line = process.stderr.readline()
            if line:
                stderr_lines.append(line.rstrip())
                # Parse progress information
                progress = self.parse_progress(line)

                if progress:
                    current_time = time.time()

                    # Display progress update if interval has passed
                    if current_time - last_update_time >= progress_interval:
                        progress_str = "  [Progress] "
                        if "time" in progress:
                            progress_str += f"Time: {progress['time']} | "
                        if "frame" in progress:
                            progress_str += f"Frame: {progress['frame']} | "
                        if "fps" in progress:
                            progress_str += f"FPS: {progress['fps']} | "
                        if "bitrate" in progress:
                            progress_str += f"Bitrate: {progress['bitrate']} | "
                        if "size" in progress:
                            progress_str += f"Size: {progress['size']} | "
                        if "speed" in progress:
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

        stderr = "\n".join(stderr_lines)

        # Create CompletedProcess-like object
        result = subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)

        if result.returncode != 0:
            self.logger.error(
                f"FFmpeg command failed for {filename} with return code {result.returncode}",
                extra={"return_code": result.returncode, "stderr": stderr[:500]},  # Log first 500 chars of stderr
            )
            raise subprocess.CalledProcessError(result.returncode, cmd, stdout, stderr)

        self.logger.debug(f"FFmpeg command completed successfully for {filename}")
        return result
