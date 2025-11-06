# ============================================================================
# Utility Functions
# ============================================================================

import re


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def parse_size(size_str: str) -> int:
    """
    Parse a size string to bytes.

    Supports formats like:
    - "1MB", "500MB", "1.5GB", "2TB"
    - "1024B", "1.5K"
    - Case insensitive (kb, KB, Kb all work)

    Args:
        size_str: Size string to parse (e.g., "10MB", "1.5GB")

    Returns:
        Size in bytes as integer

    Raises:
        ValueError: If size string format is invalid or size is negative
    """
    if not size_str or not isinstance(size_str, str):
        raise ValueError(f"Invalid size string: {size_str}")

    # Remove whitespace and convert to uppercase
    size_str = size_str.strip().upper()

    # Match pattern: number (int or float) + unit (optional)
    match = re.match(r"^([\d.]+)\s*([KMGT]?B?)$", size_str)

    if not match:
        raise ValueError(f"Invalid size format: {size_str}. Expected format like '10MB', '1.5GB', '500KB'")

    try:
        value = float(match.group(1))
    except ValueError:
        raise ValueError(f"Invalid numeric value in size string: {size_str}")

    if value < 0:
        raise ValueError(f"Size cannot be negative: {size_str}")

    unit = match.group(2) or "B"

    # Define unit multipliers (in bytes)
    units = {
        "B": 1,
        "K": 1024,
        "KB": 1024,
        "M": 1024**2,
        "MB": 1024**2,
        "G": 1024**3,
        "GB": 1024**3,
        "T": 1024**4,
        "TB": 1024**4,
    }

    if unit not in units:
        raise ValueError(f"Invalid size unit: {unit}. Supported units: B, K, KB, M, MB, G, GB, T, TB")

    # Calculate size in bytes
    size_bytes = int(value * units[unit])

    return size_bytes


def parse_resolution(resolution_str: str) -> tuple:
    """
    Parse a resolution string to (width, height) tuple.

    Supports formats like:
    - "1920x1080", "1280x720" (explicit width x height)
    - "720p", "1080p", "1440p", "2160p" (standard resolutions)
    - "2k", "4k", "8k" (standard resolutions)
    - Case insensitive

    Args:
        resolution_str: Resolution string to parse (e.g., "1920x1080", "1080p", "4k")

    Returns:
        Tuple of (width, height) as integers

    Raises:
        ValueError: If resolution string format is invalid
    """
    if not resolution_str or not isinstance(resolution_str, str):
        raise ValueError(f"Invalid resolution string: {resolution_str}")

    # Remove whitespace and convert to lowercase
    resolution_str = resolution_str.strip().lower()

    # Named resolution mappings
    named_resolutions = {
        "480p": (854, 480),
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "1440p": (2560, 1440),
        "2160p": (3840, 2160),
        "2k": (2048, 1080),
        "4k": (3840, 2160),
        "8k": (7680, 4320),
    }

    # Check if it's a named resolution
    if resolution_str in named_resolutions:
        return named_resolutions[resolution_str]

    # Try to parse as WIDTHxHEIGHT format
    match = re.match(r"^(\d+)x(\d+)$", resolution_str)
    if match:
        width = int(match.group(1))
        height = int(match.group(2))

        if width <= 0 or height <= 0:
            raise ValueError(f"Resolution dimensions must be positive: {resolution_str}")

        return (width, height)

    # If nothing matched, raise an error
    raise ValueError(
        f"Invalid resolution format: {resolution_str}. "
        f"Expected formats: '1920x1080', '720p', '1080p', '1440p', '2160p', '2k', '4k', '8k'"
    )
