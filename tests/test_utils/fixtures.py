"""
Test data and file fixtures.
"""

from pathlib import Path
from typing import List


def create_test_video_file(directory: Path, name: str = "test_video.mp4", size: int = 1024) -> Path:
    """Create a test video file with specified size."""
    video_path = directory / name
    with open(video_path, "wb") as f:
        f.write(b"0" * size)
    return video_path


def create_test_image_file(directory: Path, name: str = "test_image.png", size: int = 512) -> Path:
    """Create a test image file with specified size."""
    image_path = directory / name
    with open(image_path, "wb") as f:
        f.write(b"0" * size)
    return image_path


def create_test_directory_structure(base_dir: Path, structure: List[str]) -> None:
    """Create a directory structure for testing.

    Args:
        base_dir: Base directory to create structure in
        structure: List of relative paths (files or directories)
    """
    for item in structure:
        path = base_dir / item
        if item.endswith("/"):
            # It's a directory
            path.mkdir(parents=True, exist_ok=True)
        else:
            # It's a file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
