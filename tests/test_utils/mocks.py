"""
Reusable mock objects for testing.
"""

from unittest.mock import MagicMock


def mock_ffmpeg_progress_line(frame: int = 100, fps: float = 25.0, time: str = "00:00:10.00") -> str:
    """Generate a mock FFmpeg progress line."""
    return f"frame=   {frame} fps= {fps} q=28.0 size=    1024kB time={time} bitrate= 800.0kbits/s speed=1.0x"


def mock_ffmpeg_subprocess_success(mocker):
    """Mock subprocess.Popen for successful FFmpeg execution."""
    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Initially running
    mock_process.stderr.readline.side_effect = [
        mock_ffmpeg_progress_line(50, 24.0, "00:00:05.00"),
        mock_ffmpeg_progress_line(100, 25.0, "00:00:10.00"),
        "",  # EOF
    ]
    mock_process.communicate.return_value = (b"", b"")
    mock_process.returncode = 0

    mock_popen = mocker.patch("subprocess.Popen", return_value=mock_process)
    return mock_popen


def mock_ffmpeg_subprocess_error(mocker):
    """Mock subprocess.Popen for FFmpeg execution error."""
    mock_process = MagicMock()
    mock_process.poll.return_value = 1  # Error exit code
    mock_process.stderr.readline.return_value = ""
    mock_process.communicate.return_value = (b"", b"FFmpeg error occurred")
    mock_process.returncode = 1

    mock_popen = mocker.patch("subprocess.Popen", return_value=mock_process)
    return mock_popen


def mock_file_stat(size: int = 1024, mtime: float = 1234567890.0):
    """Create a mock file stat result."""
    mock_stat = MagicMock()
    mock_stat.st_size = size
    mock_stat.st_mtime = mtime
    mock_stat.st_atime = mtime
    return mock_stat
