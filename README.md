# Compressy 🎬📸

A powerful Python command-line tool for compressing videos and images using FFmpeg, with intelligent quality settings, batch processing, and comprehensive statistics tracking.

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![Code Coverage](https://img.shields.io/badge/coverage-100%25-success.svg)](https://github.com/yourusername/Compressy)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


## 📑 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#-usage)
  - [Basic Usage](#basic-usage)
  - [Video Compression](#video-compression)
  - [Image Compression](#image-compression)
  - [Advanced Options](#advanced-options)
  - [Viewing Statistics](#viewing-statistics)
- [Command-Line Arguments](#-command-line-arguments)
- [Output](#-output)
  - [Reports](#reports)
  - [Statistics](#statistics)
- [Examples](#-examples)
- [Project Structure](#️-project-structure)
- [Development](#-development)
  - [Running Tests](#running-tests)
  - [Code Quality](#code-quality)
- [License](#-license)
- [Contributing](#-contributing)
- [Important Notes](#️-important-notes)
- [Troubleshooting](#-troubleshooting)
- [Additional Resources](#-additional-resources)
- [Acknowledgments](#-acknowledgments)

## ✨ Features

- **🎥 Video Compression**: Compress videos using H.264 codec with customizable CRF and encoding presets
- **📐 Video Resolution Control**: Scale videos to target resolutions (720p, 1080p, 4k, or custom dimensions)
- **🖼️ Image Compression**: Compress images (JPEG, PNG, WebP) with quality control and resizing options
- **📁 Batch Processing**: Process entire folders recursively with support for nested directories
- **📏 File Size Filtering**: Filter files by minimum/maximum size before processing
- **📂 Custom Output Directory**: Save compressed files to a custom location instead of the default 'compressed' folder
- **🔄 Format Conversion**: Converts all images to JPEG for maximum compression (unless `--preserve-format` is used)
- **📊 Statistics Tracking**: Track compression statistics across multiple runs with cumulative totals
- **📈 Detailed Reports**: Generate JSON reports with per-file compression details
- **💾 Backup Support**: Automatically create backups before compression
- **⚡ Progress Monitoring**: Real-time progress updates during compression
- **🛡️ Safe Defaults**: Skip files that would increase in size (unless `--keep-if-larger` is used)
- **📅 Timestamp Preservation**: Preservation of original file timestamps via `--preserve-timestamps`

## 🚀 Quick Start

### Prerequisites

- **Python 3.14**
- **FFmpeg** (must be installed and accessible in your PATH, or use `--ffmpeg-path`)

#### Installing FFmpeg

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Compressy.git
cd Compressy
```

2. Install dependencies:
```bash
pip install -r requirements-dev.txt
```

3. Run compressy:
```bash
python compressy.py <source_folder>
```

## 📖 Usage

### Basic Usage

```bash
# Compress all media files in a folder
python compressy.py /path/to/media/folder

# Compress recursively (all subdirectories)
python compressy.py /path/to/media/folder -r  # (--recursive)

# Compress and overwrite original files
python compressy.py /path/to/media/folder -o  # (--overwrite)
```

### Video Compression

```bash
# High quality compression (lower CRF = higher quality)
python compressy.py /path/to/videos -crf 18 -vp slow  # (--video-crf, --video-preset)

# Faster compression with lower quality
python compressy.py /path/to/videos -crf 28 -vp fast

# Custom preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
python compressy.py /path/to/videos --video-preset slow

# Resize videos to 90% of original dimensions
python compressy.py /path/to/videos -vr 90  # (--video-resize)

# Scale videos to specific resolution (720p, 1080p, 1440p, 2160p, 4k, 8k)
python compressy.py /path/to/videos -res 1080p  # (--video-resolution)

# Scale videos to custom resolution (WIDTHxHEIGHT)
python compressy.py /path/to/videos -res 1920x1080

# Combine quality, resolution, and resize for smaller file sizes
python compressy.py /path/to/videos -crf 24 -res 720p
```

**Video CRF Values:**
- `0-18`: Visually lossless (very large files)
- `19-23`: High quality (recommended: 23)
- `24-28`: Good quality with smaller files
- `29-51`: Lower quality (not recommended for most use cases)

### Image Compression

```bash
# Compress images with quality setting (0-100, higher = better quality)
python compressy.py /path/to/images -iq 85  # (--image-quality)

# Resize images to 90% of original dimensions
python compressy.py /path/to/images -ir 90  # (--image-resize)

# Combine quality and resize
python compressy.py /path/to/images -iq 80 -ir 75

# Preserve original image formats (don't convert to JPEG)
python compressy.py /path/to/images -pf  # (--preserve-format)

# Convert all images to JPEG for maximum compression (default)
python compressy.py /path/to/images
```

### Advanced Options

```bash
# Create a backup before compression
python compressy.py /path/to/media --backup-dir /path/to/backups

# Use custom FFmpeg path
python compressy.py /path/to/media --ffmpeg-path /custom/path/to/ffmpeg

# Keep files even if compression makes them larger
python compressy.py /path/to/media -kl  # (--keep-if-larger)

# Preserve original file timestamps
python compressy.py /path/to/media -pt  # (--preserve-timestamps)

# Adjust progress update interval (seconds)
python compressy.py /path/to/media -pi 2.0  # (--progress-interval)

# Output compressed files to custom directory (instead of default 'compressed' folder)
python compressy.py /path/to/media -d /path/to/output  # (--output-dir)

# Process only files within a size range (supports B, KB, MB, GB, TB)
python compressy.py /path/to/media -m 1MB -M 100MB  # (--min-size, --max-size)

# Process only large files (over 10MB)
python compressy.py /path/to/media -m 10MB

# Process only small files (under 50MB)
python compressy.py /path/to/media -M 50MB
```

### Viewing Statistics

```bash
# View cumulative compression statistics
python compressy.py -s  # (--view-stats)

# View run history (all runs)
python compressy.py -h  # (--view-history)

# View last 5 runs
python compressy.py -h 5

# Show help
python compressy.py --help
```

## 📋 Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `source_folder` | Path to folder containing media files | Required |
| `-crf, --video-crf` | Video CRF value (0-51, lower = higher quality) | 23 |
| `-vp, --video-preset` | Video encoding preset | medium |
| `-vr, --video-resize` | Resize videos to % of original (0-100, 0 = no resize) | None |
| `-res, --video-resolution` | Target video resolution (e.g., '1920x1080', '720p', '1080p', '4k') | None |
| `-iq, --image-quality` | Image quality (0-100, higher = better) | 100 |
| `-ir, --image-resize` | Resize images to % of original (1-100) | None |
| `-r, --recursive` | Process files recursively | False |
| `-o, --overwrite` | Overwrite original files | False |
| `-pf, --preserve-format` | Preserve original image formats | False |
| `-pt, --preserve-timestamps` | Preserve original timestamps for output files | False |
| `-m, --min-size` | Minimum file size to process (e.g., '1MB', '500KB', '1.5GB') | None |
| `-M, --max-size` | Maximum file size to process (e.g., '100MB', '1GB', '2.5GB') | None |
| `-d, --output-dir` | Custom output directory for compressed files (cannot be used with --overwrite) | None |
| `--ffmpeg-path` | Custom path to FFmpeg executable | Auto-detect |
| `-pi, --progress-interval` | Seconds between progress updates | 5.0 |
| `-kl, --keep-if-larger` | Keep files even if compression makes them larger | False |
| `--backup-dir` | Directory for backups before compression | None |
| `-s, --view-stats` | View cumulative statistics and exit | False |
| `-h, --view-history` | View run history and exit (optionally limit to N runs) | None |

## 📊 Output

### Reports

Compressy generates detailed JSON reports in the `reports/` directory:

- **Non-recursive mode**: Single report file
- **Recursive mode**: Per-folder reports + aggregated report

Report includes:
- File-by-file compression details
- Original and compressed sizes
- Space saved per file
- Compression ratios
- Processing times
- Command-line arguments used

### Statistics

Statistics are stored in `statistics/` directory:
- `statistics.json`: Cumulative statistics across all runs
- `files.json`: Individual run history with file details

Use `--view-stats` and `--view-history` to view these statistics.

## 🎯 Examples

### Example 1: Compress a photo library

```bash
# Compress all images in a photo library, resize to 90%, quality 85
python compressy.py ~/Pictures/Photos --recursive --image-quality 85 --image-resize 90
```

### Example 2: Compress videos for web

```bash
# Compress videos with good quality for web distribution
python compressy.py ~/Videos --recursive --video-crf 24 --video-preset fast

# Compress and scale videos to 720p for web (smaller file sizes)
python compressy.py ~/Videos --recursive --video-crf 24 --video-resolution 720p

# Alternative: Compress and resize videos to 75% of original dimensions
python compressy.py ~/Videos --recursive --video-crf 24 --video-resize 75
```

### Example 3: Backup and compress

```bash
# Create backup, then compress with overwrite
python compressy.py ~/Media --backup-dir ~/Backups/Media --overwrite --recursive
```

### Example 4: Preserve original formats

```bash
# Compress images but keep original formats (PNG, WebP, etc.)
python compressy.py ~/Images --preserve-format --image-quality 90
```

### Example 5: Scale videos to 720p for web

```bash
# Compress and scale all videos to 720p resolution
python compressy.py ~/Videos --recursive --video-resolution 720p --video-crf 24

# Scale 4K videos down to 1080p with high quality
python compressy.py ~/Videos/4K --video-resolution 1080p --video-crf 20
```

### Example 6: Process only large files

```bash
# Compress only files larger than 50MB
python compressy.py ~/Media --recursive --min-size 50MB

# Compress files between 10MB and 500MB
python compressy.py ~/Media --recursive --min-size 10MB --max-size 500MB
```

### Example 7: Custom output directory

```bash
# Save compressed files to a custom directory instead of 'compressed' folder
python compressy.py ~/Media --recursive --output-dir ~/CompressedMedia

# Combine with other options for complete workflow
python compressy.py ~/Videos --recursive --output-dir ~/Web/Videos --video-resolution 720p --video-crf 24
```

## 🏗️ Project Structure

```
Compressy/
├── compressy/              # Main package
│   ├── core/              # Core compression logic
│   │   ├── config.py      # Configuration and validation
│   │   ├── ffmpeg_executor.py  # FFmpeg execution
│   │   ├── image_compressor.py # Image compression
│   │   ├── media_compressor.py # Main orchestrator
│   │   └── video_compressor.py # Video compression
│   ├── services/          # Supporting services
│   │   ├── backup.py     # Backup management
│   │   ├── reports.py    # Report generation
│   │   └── statistics.py # Statistics tracking
│   └── utils/            # Utilities
│       ├── file_processor.py # File operations
│       └── format.py     # Size formatting
├── tests/                 # Test suite
├── compressy.py          # CLI entry point
└── README.md             # This file
```

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=compressy --cov-report=html

# Run specific test file
pytest tests/test_core/test_media_compressor.py
```

### Code Quality

```bash
# Format code
black compressy tests
isort compressy tests

# Lint code
flake8 compressy tests
pylint compressy
mypy compressy
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## ⚠️ Important Notes

- **Backup your files**: While Compressy is designed to be safe, always backup important files before compression
- **Lossy compression**: Video and image compression is lossy - original quality cannot be perfectly restored
- **File sizes**: Some files may not compress well (already compressed media, very small files)
- **Processing time**: Large videos may take significant time to process
- **FFmpeg required**: This tool requires FFmpeg to be installed and accessible
- **Output directory**: When using `--output-dir`, compressed files are saved to the custom directory. Cannot be combined with `--overwrite`
- **Video resolution**: The `--video-resolution` option scales videos to the specified resolution. Use standard presets (720p, 1080p, 4k) or custom dimensions (WIDTHxHEIGHT)
- **File size filtering**: `--min-size` and `--max-size` filter files before processing. Useful for targeting specific file size ranges

## 🐛 Troubleshooting

### FFmpeg not found

```bash
# Check if FFmpeg is installed
ffmpeg -version

# If not found, install FFmpeg (see Prerequisites)
# Or use --ffmpeg-path to specify custom location
python compressy.py /path/to/media --ffmpeg-path /path/to/ffmpeg
```

### Permission errors

- Ensure you have read/write permissions for source and output directories
- On Windows, run as administrator if needed
- Check that output directory exists and is writable

### Large files not compressing

- Some files may already be highly compressed
- Very large files may take a long time - check progress output
- Use `--keep-if-larger` if you want to keep files even if they don't compress well

## 📚 Additional Resources

- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [H.264 CRF Guide](https://trac.ffmpeg.org/wiki/Encode/H.264)
- [Image Compression Best Practices](https://developers.google.com/speed/webp/docs/compression)

## 🙏 Acknowledgments

- Built with [FFmpeg](https://ffmpeg.org/) for media processing
- Uses [pytest](https://pytest.org/) for testing
- Formatted with [Black](https://black.readthedocs.io/)

---

