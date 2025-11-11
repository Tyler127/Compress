"""
Tests for compressy.core.ffmpeg_executor module.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from compressy.core.ffmpeg_executor import FFmpegExecutor


@pytest.mark.unit
class TestFFmpegExecutor:
    """Tests for FFmpegExecutor class."""

    def test_init_with_ffmpeg_path(self):
        """Test initialization with provided ffmpeg path."""
        executor = FFmpegExecutor(ffmpeg_path="/custom/ffmpeg")

        assert executor.ffmpeg_path == "/custom/ffmpeg"

    @patch("compressy.core.ffmpeg_executor.shutil.which")
    @patch("compressy.core.ffmpeg_executor.Path.exists")
    def test_init_finds_ffmpeg_in_path(self, mock_exists, mock_which):
        """Test initialization finds FFmpeg in PATH."""
        mock_which.return_value = "/usr/bin/ffmpeg"

        executor = FFmpegExecutor()

        assert executor.ffmpeg_path == "/usr/bin/ffmpeg"
        mock_which.assert_called_once_with("ffmpeg")

    @patch("compressy.core.ffmpeg_executor.shutil.which")
    def test_init_finds_ffmpeg_in_windows_path(self, mock_which):
        """Test initialization finds FFmpeg in Windows common location."""
        mock_which.return_value = None  # Not in PATH

        # Mock Path.exists for the specific Windows path
        def mock_exists(self):
            return str(self) == r"C:\ffmpeg\ffmpeg.exe"

        with patch.object(Path, "exists", mock_exists):
            executor = FFmpegExecutor()

            assert executor.ffmpeg_path == r"C:\ffmpeg\ffmpeg.exe"

    @patch("compressy.core.ffmpeg_executor.shutil.which")
    @patch("compressy.core.ffmpeg_executor.Path.exists")
    def test_init_raises_when_not_found(self, mock_exists, mock_which):
        """Test initialization raises FileNotFoundError when FFmpeg not found."""
        mock_which.return_value = None
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError, match="FFmpeg not found"):
            FFmpegExecutor()

    def test_parse_progress_frame(self):
        """Test parsing progress line with frame."""
        line = "frame=  100 fps= 25.0"
        result = FFmpegExecutor.parse_progress(line)

        assert result is not None
        assert result["frame"] == "100"

    def test_parse_progress_fps(self):
        """Test parsing progress line with fps."""
        line = "fps= 25.5 q=28.0"
        result = FFmpegExecutor.parse_progress(line)

        assert result is not None
        assert result["fps"] == "25.5"

    def test_parse_progress_time(self):
        """Test parsing progress line with time."""
        line = "time=00:01:23.45 bitrate= 800.0kbits/s"
        result = FFmpegExecutor.parse_progress(line)

        assert result is not None
        assert result["time"] == "00:01:23.45"

    def test_parse_progress_bitrate(self):
        """Test parsing progress line with bitrate."""
        line = "bitrate= 800.0kbits/s speed=1.0x"
        result = FFmpegExecutor.parse_progress(line)

        assert result is not None
        assert "800.0kbits/s" in result["bitrate"]

    def test_parse_progress_size(self):
        """Test parsing progress line with size."""
        line = "size=    1024kB time=00:00:10.00"
        result = FFmpegExecutor.parse_progress(line)

        assert result is not None
        assert "1024kB" in result["size"]

    def test_parse_progress_speed(self):
        """Test parsing progress line with speed."""
        line = "speed=1.5x frame=  200"
        result = FFmpegExecutor.parse_progress(line)

        assert result is not None
        assert result["speed"] == "1.5x"

    def test_parse_progress_complete_line(self):
        """Test parsing complete progress line."""
        line = "frame=  100 fps= 25.0 q=28.0 size=    1024kB time=00:00:10.00 bitrate= 800.0kbits/s speed=1.0x"
        result = FFmpegExecutor.parse_progress(line)

        assert result is not None
        assert result["frame"] == "100"
        assert result["fps"] == "25.0"
        assert result["time"] == "00:00:10.00"
        assert "1024kB" in result["size"]
        assert "800.0kbits/s" in result["bitrate"]
        assert result["speed"] == "1.0x"

    def test_parse_progress_no_match(self):
        """Test parsing progress line with no matchable data."""
        line = "Some random text without progress info"
        result = FFmpegExecutor.parse_progress(line)

        assert result is None

    def test_parse_progress_empty_line(self):
        """Test parsing empty progress line."""
        result = FFmpegExecutor.parse_progress("")

        assert result is None

    @patch("compressy.core.ffmpeg_executor.subprocess.Popen")
    @patch("compressy.core.ffmpeg_executor.time.time")
    @patch("compressy.core.ffmpeg_executor.time.sleep")
    def test_run_with_progress_success(self, mock_sleep, mock_time, mock_popen):
        """Test running FFmpeg with progress tracking (success)."""
        executor = FFmpegExecutor(ffmpeg_path="/fake/ffmpeg")

        # Mock process
        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, None, 0]  # Running, then done
        mock_process.stderr.readline.side_effect = [
            "frame=  50 fps= 24.0 time=00:00:05.00\n",
            "frame= 100 fps= 25.0 time=00:00:10.00\n",
            "",  # EOF
        ]
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock time
        mock_time.side_effect = [0.0, 6.0, 11.0]  # Progress updates at 6s and 11s

        result = executor.run_with_progress(["-i", "input.mp4", "output.mp4"], progress_interval=5.0)

        assert result.returncode == 0
        mock_popen.assert_called_once()
        assert "/fake/ffmpeg" in str(mock_popen.call_args[0][0])

    @patch("compressy.core.ffmpeg_executor.subprocess.Popen")
    @patch("compressy.core.ffmpeg_executor.time.time")
    @patch("compressy.core.ffmpeg_executor.time.sleep")
    def test_run_with_progress_error(self, mock_sleep, mock_time, mock_popen):
        """Test running FFmpeg with error."""
        executor = FFmpegExecutor(ffmpeg_path="/fake/ffmpeg")

        # Mock process with error
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Error exit code
        mock_process.stderr.readline.return_value = ""
        # Return error message as string (not bytes) since universal_newlines=True
        mock_process.communicate.return_value = ("", "FFmpeg error")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        mock_time.return_value = 0.0

        with pytest.raises(subprocess.CalledProcessError):
            executor.run_with_progress(["-i", "input.mp4", "output.mp4"])

    @patch("compressy.core.ffmpeg_executor.subprocess.Popen")
    @patch("compressy.core.ffmpeg_executor.time.time")
    @patch("compressy.core.ffmpeg_executor.time.sleep")
    def test_run_with_progress_displays_updates(self, mock_sleep, mock_time, mock_popen, capsys):
        """Test that progress updates are displayed."""
        executor = FFmpegExecutor(ffmpeg_path="/fake/ffmpeg")

        # Mock process
        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, None, 0]
        mock_process.stderr.readline.side_effect = [
            "frame=  100 fps= 25.0 time=00:00:10.00 bitrate= 800.0kbits/s speed=1.0x\n",
            "",  # EOF
        ]
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock time - progress interval passed
        mock_time.side_effect = [0.0, 6.0, 7.0]  # 6s >= 5s interval

        executor.run_with_progress(["-i", "input.mp4"], progress_interval=5.0)

        output = capsys.readouterr()
        assert "[Progress]" in output.out

    @patch("compressy.core.ffmpeg_executor.shutil.which")
    def test_find_ffmpeg_in_path(self, mock_which):
        """Test finding FFmpeg in PATH."""
        mock_which.return_value = "/usr/bin/ffmpeg"

        result = FFmpegExecutor.find_ffmpeg()

        assert result == "/usr/bin/ffmpeg"
        mock_which.assert_called_once_with("ffmpeg")

    @patch("compressy.core.ffmpeg_executor.shutil.which")
    def test_find_ffmpeg_windows_location(self, mock_which):
        """Test finding FFmpeg in Windows common location."""
        mock_which.return_value = None

        # Mock Path.exists for the specific Windows path
        def mock_exists(self):
            return str(self) == r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"

        with patch.object(Path, "exists", mock_exists):
            result = FFmpegExecutor.find_ffmpeg()

            assert result == r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"

    @patch("compressy.core.ffmpeg_executor.shutil.which")
    @patch("compressy.core.ffmpeg_executor.Path.exists")
    def test_find_ffmpeg_not_found(self, mock_exists, mock_which):
        """Test finding FFmpeg when not found."""
        mock_which.return_value = None
        mock_exists.return_value = False

        result = FFmpegExecutor.find_ffmpeg()

        assert result is None

    @patch("compressy.core.ffmpeg_executor.subprocess.Popen")
    @patch("compressy.core.ffmpeg_executor.time.time")
    @patch("compressy.core.ffmpeg_executor.time.sleep")
    def test_run_with_progress_includes_size(self, mock_sleep, mock_time, mock_popen, capsys):
        """Test that progress updates include size information."""
        executor = FFmpegExecutor(ffmpeg_path="/fake/ffmpeg")

        # Mock process
        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, None, 0]
        mock_process.stderr.readline.side_effect = [
            "frame=  100 fps= 25.0 time=00:00:10.00 bitrate= 800.0kbits/s size=  1024kB speed=1.0x\n",
            "",  # EOF
        ]
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock time - progress interval passed
        mock_time.side_effect = [0.0, 6.0, 7.0]  # 6s >= 5s interval

        executor.run_with_progress(["-i", "input.mp4"], progress_interval=5.0)

        output = capsys.readouterr()
        assert "Size:" in output.out

    @patch("compressy.core.ffmpeg_executor.subprocess.Popen")
    @patch("compressy.core.ffmpeg_executor.time.time")
    @patch("compressy.core.ffmpeg_executor.time.sleep")
    def test_run_with_progress_final_progress_update(self, mock_sleep, mock_time, mock_popen):
        """Test that final progress update is captured from communicate()."""
        executor = FFmpegExecutor(ffmpeg_path="/fake/ffmpeg")

        # Mock process
        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, None, 0]
        mock_process.stderr.readline.side_effect = [
            "frame=  50 fps= 24.0 time=00:00:05.00\n",
            "",  # EOF
        ]
        # Final progress in communicate() stderr (as string since universal_newlines=True)
        mock_process.communicate.return_value = (
            "",
            "frame=  100 fps= 25.0 time=00:00:10.00\n",
        )
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock time
        mock_time.side_effect = [0.0, 6.0, 11.0]

        result = executor.run_with_progress(["-i", "input.mp4", "output.mp4"], progress_interval=5.0)

        assert result.returncode == 0

    def test_maybe_print_progress_without_data(self):
        """Test that _maybe_print_progress returns original timestamp when no progress parsed."""
        executor = FFmpegExecutor(ffmpeg_path="/fake/ffmpeg")

        with patch("builtins.print") as mock_print:
            last_update = executor._maybe_print_progress("no progress info", last_update=1.0, interval=5.0)

        assert last_update == 1.0
        mock_print.assert_not_called()

    def test_maybe_print_progress_throttles_updates(self):
        """Test that _maybe_print_progress throttles updates when interval not reached."""
        executor = FFmpegExecutor(ffmpeg_path="/fake/ffmpeg")

        with patch("compressy.core.ffmpeg_executor.time.time", return_value=2.0), patch("builtins.print") as mock_print:
            last_update = executor._maybe_print_progress(
                "frame=  10 fps=25.0 time=00:00:01.00", last_update=1.5, interval=5.0
            )

        assert last_update == 1.5
        mock_print.assert_not_called()

    def test_format_progress_without_segments(self):
        """Test that _format_progress returns placeholder when no known segments exist."""
        executor = FFmpegExecutor(ffmpeg_path="/fake/ffmpeg")

        formatted = executor._format_progress({})

        assert formatted == "  [Progress]"
