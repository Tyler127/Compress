# Compressy 🎬📸

A powerful Python command-line tool for compressing videos and images using FFmpeg, with intelligent quality settings, batch processing, and comprehensive statistics tracking.

[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
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
- **🖼️ Image Compression**: Compress images (JPEG, PNG, WebP) with quality control and resizing options
- **📁 Batch Processing**: Process entire folders recursively with support for nested directories
- **🔄 Format Conversion**: Converts all images to JPEG for maximum compression (unless `--preserve-format` is used)
- **📊 Statistics Tracking**: Track compression statistics across multiple runs with cumulative totals
- **📈 Detailed Reports**: Generate CSV reports with per-file compression details
- **💾 Backup Support**: Automatically create backups before compression
- **⚡ Progress Monitoring**: Real-time progress updates during compression
- **🛡️ Safe Defaults**: Skip files that would increase in size (unless `--keep-if-larger` is used)
- **📅 Timestamp Preservation**: Preserve original file timestamps

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
python compressy.py /path/to/media/folder --recursive

# Compress and overwrite original files
python compressy.py /path/to/media/folder --overwrite
```

### Video Compression

```bash
# High quality compression (lower CRF = higher quality)
python compressy.py /path/to/videos --video-crf 18 --video-preset slow

# Faster compression with lower quality
python compressy.py /path/to/videos --video-crf 28 --video-preset fast

# Custom preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
python compressy.py /path/to/videos --video-preset slow
```

**Video CRF Values:**
- `0-18`: Visually lossless (very large files)
- `19-23`: High quality (recommended: 23)
- `24-28`: Good quality with smaller files
- `29-51`: Lower quality (not recommended for most use cases)

### Image Compression

```bash
# Compress images with quality setting (0-100, higher = better quality)
python compressy.py /path/to/images --image-quality 85

# Resize images to 90% of original dimensions
python compressy.py /path/to/images --image-resize 90

# Combine quality and resize
python compressy.py /path/to/images --image-quality 80 --image-resize 75

# Preserve original image formats (don't convert to JPEG)
python compressy.py /path/to/images --preserve-format

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
python compressy.py /path/to/media --keep-if-larger

# Adjust progress update interval (seconds)
python compressy.py /path/to/media --progress-interval 2.0
```

### Viewing Statistics

```bash
# View cumulative compression statistics
python compressy.py --view-stats

# View run history (all runs)
python compressy.py --view-history

# View last 5 runs
python compressy.py --view-history 5
```

## 📋 Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `source_folder` | Path to folder containing media files | Required |
| `--video-crf` | Video CRF value (0-51, lower = higher quality) | 23 |
| `--video-preset` | Video encoding preset | medium |
| `--image-quality` | Image quality (0-100, higher = better) | 100 |
| `--image-resize` | Resize images to % of original (1-100) | None |
| `-r, --recursive` | Process files recursively | False |
| `--overwrite` | Overwrite original files | False |
| `--preserve-format` | Preserve original image formats | False |
| `--ffmpeg-path` | Custom path to FFmpeg executable | Auto-detect |
| `--progress-interval` | Seconds between progress updates | 5.0 |
| `--keep-if-larger` | Keep files even if compression makes them larger | False |
| `--backup-dir` | Directory for backups before compression | None |
| `--view-stats` | View cumulative statistics and exit | False |
| `--view-history` | View run history and exit (optionally limit to N runs) | None |

## 📊 Output

### Reports

Compressy generates detailed CSV reports in the `reports/` directory:

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
- `statistics.csv`: Cumulative statistics across all runs
- `run_history.csv`: Individual run history

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

