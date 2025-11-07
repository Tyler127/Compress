"""
Shared pytest fixtures and configuration.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from compressy.core.config import CompressionConfig
from compressy.core.ffmpeg_executor import FFmpegExecutor


# Suppress print statements during tests


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_video(temp_dir):
    """Create a mock video file path."""
    video_path = temp_dir / "test_video.mp4"
    video_path.touch()
    return video_path


@pytest.fixture
def sample_image_png(temp_dir):
    """Create a mock PNG file path."""
    image_path = temp_dir / "test_image.png"
    image_path.touch()
    return image_path


@pytest.fixture
def sample_image_jpg(temp_dir):
    """Create a mock JPEG file path."""
    image_path = temp_dir / "test_image.jpg"
    image_path.touch()
    return image_path


@pytest.fixture
def mock_ffmpeg_executor(mocker):
    """Create a mocked FFmpegExecutor."""
    mock_executor = MagicMock(spec=FFmpegExecutor)
    mock_executor.ffmpeg_path = "/fake/path/to/ffmpeg"
    mock_executor.run_with_progress = MagicMock(return_value=MagicMock(returncode=0))
    mock_executor.find_ffmpeg = MagicMock(return_value="/fake/path/to/ffmpeg")
    mock_executor.parse_progress = MagicMock(return_value={"frame": "100", "fps": "25.0"})
    return mock_executor


@pytest.fixture
def mock_config(temp_dir):
    """Create a sample CompressionConfig."""
    return CompressionConfig(
        source_folder=temp_dir,
        video_crf=23,
        video_preset="medium",
        image_quality=80,
        image_resize=None,
        recursive=False,
        overwrite=False,
        ffmpeg_path="/fake/path/to/ffmpeg",
        progress_interval=1.0,
        keep_if_larger=False,
        backup_dir=None,
        preserve_format=False,
    )


@pytest.fixture
def mock_statistics():
    """Create a sample statistics dictionary."""
    return {
        "total_files": 5,
        "processed": 4,
        "skipped": 1,
        "errors": 0,
        "total_original_size": 1000000,
        "total_compressed_size": 500000,
        "space_saved": 500000,
        "files": [
            {
                "name": "test1.mp4",
                "original_size": 500000,
                "compressed_size": 250000,
                "space_saved": 250000,
                "compression_ratio": 50.0,
                "processing_time": 1.5,
                "status": "success",
            }
        ],
    }


@pytest.fixture
def cleanup_temp_files():
    """Fixture to clean up temporary files after tests."""
    temp_paths = []

    def add_temp_path(path):
        temp_paths.append(path)

    yield add_temp_path

    # Cleanup
    for path in temp_paths:
        if isinstance(path, Path) and path.exists():
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
