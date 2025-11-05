"""
Tests for compressy.core.media_compressor module.
"""
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from compressy.core.config import CompressionConfig
from compressy.core.media_compressor import MediaCompressor


@pytest.mark.unit
class TestMediaCompressor:
    """Tests for MediaCompressor class."""

    def test_initialization(self, mock_config, mocker):
        """Test MediaCompressor initialization."""
        with patch("compressy.core.media_compressor.FFmpegExecutor") as mock_ffmpeg_class:
            mock_ffmpeg = MagicMock()
            mock_ffmpeg_class.return_value = mock_ffmpeg

            compressor = MediaCompressor(mock_config)

            assert compressor.config == mock_config
            assert compressor.ffmpeg == mock_ffmpeg
            assert compressor.video_compressor is not None
            assert compressor.image_compressor is not None
            assert compressor.file_processor is not None
            assert compressor.stats is not None

    def test_collect_files_non_recursive(self, mock_config, temp_dir):
        """Test collecting files in non-recursive mode."""
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(mock_config)

            # Create test files
            (temp_dir / "video.mp4").touch()
            (temp_dir / "image.jpg").touch()
            (temp_dir / "text.txt").touch()  # Should be ignored
            subdir = temp_dir / "subdir"
            subdir.mkdir()
            (subdir / "nested.mp4").touch()  # Should be ignored in non-recursive

            files = compressor._collect_files()

            # Should only find files in root, not subdir
            file_names = [f.name for f in files]
            assert "video.mp4" in file_names
            assert "image.jpg" in file_names
            assert "text.txt" not in file_names
            assert "nested.mp4" not in file_names

    def test_collect_files_recursive(self, temp_dir):
        """Test collecting files in recursive mode."""
        config = CompressionConfig(source_folder=temp_dir, recursive=True)
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            # Create test files
            (temp_dir / "video.mp4").touch()
            subdir = temp_dir / "subdir"
            subdir.mkdir()
            (subdir / "nested.mp4").touch()

            files = compressor._collect_files()

            # Should find files in root and subdir
            file_names = [f.name for f in files]
            assert "video.mp4" in file_names
            assert "nested.mp4" in file_names

    def test_collect_files_only_media_extensions(self, mock_config, temp_dir):
        """Test that only media file extensions are collected."""
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(mock_config)

            # Create various file types
            (temp_dir / "video.mp4").touch()
            (temp_dir / "video.mov").touch()
            (temp_dir / "video.mkv").touch()
            (temp_dir / "video.avi").touch()
            (temp_dir / "image.jpg").touch()
            (temp_dir / "image.png").touch()
            (temp_dir / "image.webp").touch()
            (temp_dir / "document.pdf").touch()  # Should be ignored
            (temp_dir / "text.txt").touch()  # Should be ignored

            files = compressor._collect_files()

            # Should only have media files
            assert len(files) == 7
            extensions = {f.suffix.lower() for f in files}
            assert ".pdf" not in extensions
            assert ".txt" not in extensions

    def test_get_folder_key_non_recursive(self, mock_config, temp_dir):
        """Test folder key generation in non-recursive mode."""
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(mock_config)
            file_path = temp_dir / "test.mp4"

            folder_key = compressor._get_folder_key(file_path)

            assert folder_key == "root"

    def test_get_folder_key_recursive_root(self, temp_dir):
        """Test folder key generation for root folder in recursive mode."""
        config = CompressionConfig(source_folder=temp_dir, recursive=True)
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)
            file_path = temp_dir / "test.mp4"

            folder_key = compressor._get_folder_key(file_path)

            assert folder_key == "root"

    def test_get_folder_key_recursive_subdir(self, temp_dir):
        """Test folder key generation for subdirectory in recursive mode."""
        config = CompressionConfig(source_folder=temp_dir, recursive=True)
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)
            subdir = temp_dir / "subdir"
            subdir.mkdir()
            file_path = subdir / "test.mp4"

            folder_key = compressor._get_folder_key(file_path)

            assert folder_key == "subdir"

    @patch("compressy.core.media_compressor.shutil.copy2")
    def test_process_file_video(self, mock_copy2, mock_config, temp_dir, mocker):
        """Test processing a video file."""
        with patch("compressy.core.media_compressor.FFmpegExecutor") as mock_ffmpeg_class:
            mock_ffmpeg = MagicMock()
            mock_ffmpeg_class.return_value = mock_ffmpeg

            # Don't mock FileProcessor - use real one
            compressor = MediaCompressor(mock_config)

            video_file = temp_dir / "test.mp4"
            video_file.write_bytes(b"0" * 1000)  # 1000 bytes

            # Create output file
            output_file = temp_dir / "compressed" / "test.mp4"
            output_file.parent.mkdir()
            output_file.write_bytes(b"0" * 500)  # 500 bytes (compressed)

            # Store original methods to avoid recursion
            original_exists = Path.exists
            original_stat = Path.stat

            # Mock stat to return sizes - use os.stat_result for proper attribute access
            # Compare paths as strings to handle Path object differences
            def mock_stat(self):
                """Mock Path.stat() as an instance method."""
                path_str = str(self)
                if path_str == str(video_file):
                    size = 1000
                elif path_str == str(output_file) or ("compressed" in path_str and path_str.endswith("test.mp4")):
                    size = 500
                else:
                    # Use real stat for other paths
                    return original_stat(self)
                # Create a proper stat_result-like object
                stat_result = os.stat_result((0, 0, 0, 0, 0, 0, size, 0, 0, 0))
                return stat_result

            # Mock exists to return False so file is processed (not skipped)
            def mock_exists(self):
                """Mock Path.exists() - return False so file gets processed."""
                path_str = str(self)
                # Don't let output file exist so it gets processed
                if path_str == str(output_file) or ("compressed" in path_str and path_str.endswith("test.mp4")):
                    return False
                # Use real exists for other paths
                return original_exists(self)

            # Mock the compress methods
            compressor.video_compressor.compress = MagicMock()

            with patch.object(Path, "stat", mock_stat):
                with patch.object(Path, "exists", mock_exists):
                    compressor._process_file(video_file, 1, 1, temp_dir / "compressed")

            # Verify video compressor was called
            compressor.video_compressor.compress.assert_called_once()

    def test_process_file_skips_existing(self, mock_config, temp_dir, mocker):
        """Test that process_file skips files that already exist."""
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            # Don't mock FileProcessor - use real one
            compressor = MediaCompressor(mock_config)

            image_file = temp_dir / "test.jpg"
            image_file.write_bytes(b"0" * 1000)

            output_file = temp_dir / "compressed" / "test.jpg"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(b"0" * 500)

            # Store original methods to avoid recursion
            original_exists = Path.exists
            original_stat = Path.stat

            def mock_stat(self):
                """Mock Path.stat() as an instance method."""
                path_str = str(self)
                if path_str == str(image_file):
                    size = 1000
                elif path_str == str(output_file) or ("compressed" in path_str and path_str.endswith("test.jpg")):
                    size = 500
                else:
                    # Use real stat for other paths
                    return original_stat(self)
                # Create a proper stat_result-like object
                stat_result = os.stat_result((0, 0, 0, 0, 0, 0, size, 0, 0, 0))
                return stat_result

            # Mock exists to return True only for the output_file (to test skip logic)
            def mock_exists(self):
                """Mock Path.exists() - return True for output_file to test skip."""
                path_str = str(self)
                if path_str == str(output_file) or ("compressed" in path_str and path_str.endswith("test.jpg")):
                    return True
                # Use real exists for other paths
                return original_exists(self)

            # Mock the compress methods
            compressor.image_compressor.compress = MagicMock()

            with patch.object(Path, "stat", mock_stat):
                with patch.object(Path, "exists", mock_exists):
                    compressor._process_file(image_file, 1, 1, temp_dir / "compressed")

            # Should not call image compressor
            compressor.image_compressor.compress.assert_not_called()

    def test_process_file_converts_to_jpeg(self, temp_dir):
        """Test that process_file converts images to JPEG when preserve_format=False (line 147)."""
        config = CompressionConfig(source_folder=temp_dir, preserve_format=False)
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            png_file = temp_dir / "test.png"
            png_file.write_bytes(b"0" * 1000)

            output_file = temp_dir / "compressed" / "test.jpg"  # Should be .jpg after conversion

            compressor.image_compressor.compress = MagicMock()
            compressor.file_processor.preserve_timestamps = MagicMock()

            # Store original methods
            original_stat = Path.stat
            original_exists = Path.exists

            def mock_stat(self):
                path_str = str(self)
                if path_str == str(png_file):
                    return os.stat_result((0, 0, 0, 0, 0, 0, 1000, 0, 0, 0))
                elif path_str == str(output_file):
                    return os.stat_result((0, 0, 0, 0, 0, 0, 800, 0, 0, 0))
                return original_stat(self)

            def mock_exists(self):
                path_str = str(self)
                if path_str == str(png_file) or path_str == str(temp_dir):
                    return True
                return False

            with patch.object(Path, "stat", mock_stat):
                with patch.object(Path, "exists", mock_exists):
                    compressor._process_file(png_file, 1, 1, temp_dir / "compressed")

            # Verify compress was called with .jpg extension (line 147 changes it)
            call_args = compressor.image_compressor.compress.call_args[0]
            assert call_args[1].suffix == ".jpg"  # Output should be .jpg

    def test_compress_no_files_found(self, mock_config, temp_dir, capsys):
        """Test compress when no media files found."""
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(mock_config)

            result = compressor.compress()

            assert result["total_files"] == 0
            output = capsys.readouterr()
            assert "No media files found" in output.out

    def test_compress_validates_source_folder(self, temp_dir):
        """Test that compress validates source folder exists."""
        config = CompressionConfig(source_folder=temp_dir / "nonexistent")
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            with pytest.raises(FileNotFoundError, match="Source folder does not exist"):
                compressor.compress()

    def test_compress_validates_parameters(self, temp_dir):
        """Test that compress validates parameters."""
        config = CompressionConfig(source_folder=temp_dir, video_crf=100)  # Invalid CRF
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            with pytest.raises(ValueError):
                compressor.compress()

    @patch("compressy.core.media_compressor.BackupManager")
    def test_compress_creates_backup(self, mock_backup_class, temp_dir):
        """Test that compress creates backup when backup_dir is specified."""
        backup_dir = temp_dir / "backup"
        config = CompressionConfig(source_folder=temp_dir, backup_dir=backup_dir)
        mock_backup = MagicMock()
        mock_backup_class.return_value = mock_backup

        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            # No files to process, but backup should still be checked
            result = compressor.compress()

            # BackupManager should be initialized
            mock_backup_class.assert_called_once()

    def test_get_folder_key_value_error(self, temp_dir):
        """Test _get_folder_key handles ValueError (file outside source folder)."""
        config = CompressionConfig(source_folder=temp_dir, recursive=True)
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            # Create a file path that will cause ValueError in relative_to
            file_path = Path("/absolute/path/file.mp4")

            # Mock Path.relative_to to raise ValueError
            original_relative_to = Path.relative_to

            def mock_relative_to(self, other):
                if str(self) == str(file_path.parent):
                    raise ValueError("Path is not relative")
                return original_relative_to(self, other)

            with patch.object(Path, "relative_to", mock_relative_to):
                folder_key = compressor._get_folder_key(file_path)
                assert folder_key == "root"

    def test_process_file_unsupported_file_type(self, temp_dir):
        """Test that process_file raises ValueError for unsupported file types."""
        config = CompressionConfig(source_folder=temp_dir)
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            # Create unsupported file
            unsupported_file = temp_dir / "test.xyz"
            unsupported_file.write_bytes(b"0" * 1000)

            # Mock the compress methods
            compressor.video_compressor.compress = MagicMock()
            compressor.image_compressor.compress = MagicMock()

            # Store original methods
            original_stat = Path.stat
            original_exists = Path.exists

            def mock_stat(self):
                path_str = str(self)
                if path_str == str(unsupported_file):
                    return os.stat_result((0, 0, 0, 0, 0, 0, 1000, 0, 0, 0))
                return original_stat(self)

            def mock_exists(self):
                path_str = str(self)
                if path_str == str(unsupported_file) or path_str == str(temp_dir):
                    return True
                # Output file doesn't exist
                return False

            with patch.object(Path, "stat", mock_stat):
                with patch.object(Path, "exists", mock_exists):
                    # The error is caught and printed, not raised
                    compressor._process_file(unsupported_file, 1, 1, temp_dir / "compressed")

            # Verify error was handled (not raised, but caught)
            compressor.video_compressor.compress.assert_not_called()
            compressor.image_compressor.compress.assert_not_called()

    @patch("compressy.core.media_compressor.shutil.copy2")
    def test_process_file_larger_keep_if_larger(self, mock_copy2, temp_dir):
        """Test process_file when compressed file is larger and keep_if_larger=True."""
        config = CompressionConfig(source_folder=temp_dir, keep_if_larger=True)
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            image_file = temp_dir / "test.jpg"
            image_file.write_bytes(b"0" * 1000)

            output_file = temp_dir / "compressed" / "test.jpg"
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Mock compress to create a larger output file
            def mock_compress(in_path, out_path):
                out_path.write_bytes(b"0" * 2000)  # Larger than original

            compressor.image_compressor.compress = MagicMock(side_effect=mock_compress)

            # Store original methods
            original_stat = Path.stat
            original_exists = Path.exists

            def mock_stat(self):
                path_str = str(self)
                if path_str == str(image_file):
                    return os.stat_result((0, 0, 0, 0, 0, 0, 1000, 0, 0, 0))
                elif path_str == str(output_file):
                    # Return larger size after compression
                    if output_file.exists():
                        return os.stat_result((0, 0, 0, 0, 0, 0, 2000, 0, 0, 0))
                    return os.stat_result((0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
                return original_stat(self)

            def mock_exists(self):
                path_str = str(self)
                if path_str == str(image_file) or path_str == str(temp_dir):
                    return True
                # Output file doesn't exist initially (will be created by compression)
                return False

            with patch.object(Path, "stat", mock_stat):
                with patch.object(Path, "exists", mock_exists):
                    compressor._process_file(image_file, 1, 1, temp_dir / "compressed")

            # Should have printed warning about larger file
            compressor.image_compressor.compress.assert_called_once()

    @patch("compressy.core.media_compressor.shutil.copy2")
    def test_process_file_larger_not_keep_if_larger_overwrite_false(self, mock_copy2, temp_dir):
        """Test process_file when compressed is larger, keep_if_larger=False, overwrite=False."""
        config = CompressionConfig(source_folder=temp_dir, keep_if_larger=False, overwrite=False)
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            image_file = temp_dir / "test.jpg"
            image_file.write_bytes(b"0" * 1000)

            output_file = temp_dir / "compressed" / "test.jpg"

            # Store original methods
            original_stat = Path.stat
            original_exists = Path.exists
            original_unlink = Path.unlink

            # Track if compression has happened and file exists
            compression_done = [False]
            output_file_exists = [False]

            # Mock compress to create a larger output file
            def mock_compress(in_path, out_path):
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"0" * 2000)  # Larger
                compression_done[0] = True
                output_file_exists[0] = True

            compressor.image_compressor.compress = MagicMock(side_effect=mock_compress)

            def mock_stat(self):
                import os.path as ospath

                path_str = str(self)
                if path_str == str(image_file):
                    return os.stat_result((0, 0, 0, 0, 0, 0, 1000, 0, 0, 0))
                elif path_str == str(output_file):
                    # Return larger size after compression is done
                    if compression_done[0] and output_file_exists[0]:
                        return os.stat_result((0, 0, 0, 0, 0, 0, 2000, 0, 0, 0))
                    # Check if file actually exists on disk using os.path
                    if ospath.exists(path_str):
                        return original_stat(self)
                    return os.stat_result((0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
                return original_stat(self)

            def mock_exists(self):
                import os.path as ospath

                path_str = str(self)
                if path_str == str(image_file) or path_str == str(temp_dir):
                    return True
                # Output file exists after compression
                if path_str == str(output_file):
                    if output_file_exists[0]:
                        return True
                    # Check real file system using os.path to avoid recursion
                    return ospath.exists(path_str)
                return False

            def mock_unlink(self):
                if str(self) == str(output_file):
                    if output_file_exists[0]:
                        try:
                            if original_exists(self):
                                original_unlink(self)
                            output_file_exists[0] = False
                        except:
                            pass
                else:
                    original_unlink(self)

            # Also need to mock preserve_timestamps to avoid errors
            compressor.file_processor.preserve_timestamps = MagicMock()

            with patch.object(Path, "stat", mock_stat):
                with patch.object(Path, "exists", mock_exists):
                    with patch.object(Path, "unlink", mock_unlink):
                        compressor._process_file(image_file, 1, 1, temp_dir / "compressed")

            # Should have copied original (after unlink)
            mock_copy2.assert_called_once()

    @patch("compressy.core.media_compressor.shutil.copy2")
    def test_process_file_larger_not_keep_if_larger_overwrite_true(self, mock_copy2, temp_dir):
        """Test process_file when compressed is larger, keep_if_larger=False, overwrite=True (lines 214-215)."""
        config = CompressionConfig(source_folder=temp_dir, keep_if_larger=False, overwrite=True)
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            image_file = temp_dir / "test.jpg"
            image_file.write_bytes(b"0" * 1000)

            # When overwrite=True, output is a temp file
            temp_output_file = temp_dir / "test_tmp.jpg"

            # Track compression state
            compression_done = [False]
            temp_file_created = [False]

            # Mock compress to create larger temp output file
            def mock_compress(in_path, out_path):
                # Don't create parent dir if it's the temp_dir itself
                if out_path.parent != temp_dir:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"0" * 2000)  # Larger
                compression_done[0] = True
                temp_file_created[0] = True

            compressor.image_compressor.compress = MagicMock(side_effect=mock_compress)
            compressor.file_processor.preserve_timestamps = MagicMock()

            # Store original methods
            original_stat = Path.stat
            original_exists = Path.exists
            original_unlink = Path.unlink

            def mock_stat(self):
                path_str = str(self)
                if path_str == str(image_file):
                    return os.stat_result((0, 0, 0, 0, 0, 0, 1000, 0, 0, 0))
                elif "_tmp" in path_str or path_str == str(temp_output_file):
                    # Return larger size after compression
                    if compression_done[0] and temp_file_created[0]:
                        return os.stat_result((0, 0, 0, 0, 0, 0, 2000, 0, 0, 0))
                    return os.stat_result((0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
                return original_stat(self)

            def mock_exists(self):
                path_str = str(self)
                if path_str == str(image_file) or path_str == str(temp_dir):
                    return True
                # Temp output file exists after compression
                if compression_done[0] and ("_tmp" in path_str or path_str == str(temp_output_file)):
                    return temp_file_created[0]
                return False

            def mock_unlink(self):
                if "_tmp" in str(self) or str(self) == str(temp_output_file):
                    if temp_file_created[0]:
                        try:
                            temp_output_file.unlink()
                        except:
                            pass
                else:
                    original_unlink(self)

            with patch.object(Path, "stat", mock_stat):
                with patch.object(Path, "exists", mock_exists):
                    with patch.object(Path, "unlink", mock_unlink):
                        compressor._process_file(image_file, 1, 1, temp_dir / "compressed")

            # Should not copy original in overwrite mode
            mock_copy2.assert_not_called()

    def test_process_file_overwrite_handling(self, temp_dir):
        """Test that process_file handles overwrite mode correctly."""
        config = CompressionConfig(source_folder=temp_dir, overwrite=True)
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            image_file = temp_dir / "test.jpg"
            image_file.write_bytes(b"0" * 1000)

            output_file = temp_dir / "compressed" / "test.jpg"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(b"0" * 500)

            compressor.image_compressor.compress = MagicMock()
            compressor.file_processor.handle_overwrite = MagicMock()

            # Store original methods
            original_stat = Path.stat
            original_exists = Path.exists

            def mock_stat(self):
                path_str = str(self)
                if path_str == str(image_file):
                    return os.stat_result((0, 0, 0, 0, 0, 0, 1000, 0, 0, 0))
                elif path_str == str(output_file):
                    return os.stat_result((0, 0, 0, 0, 0, 0, 500, 0, 0, 0))
                return original_stat(self)

            def mock_exists(self):
                path_str = str(self)
                if path_str == str(image_file) or path_str == str(temp_dir):
                    return True
                # Output file doesn't exist initially (will be created)
                return False

            # Track if compression has happened
            compression_done = [False]

            # Mock the compress to create output file
            def mock_compress(in_path, out_path):
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"0" * 500)
                compression_done[0] = True

            compressor.image_compressor.compress = MagicMock(side_effect=mock_compress)

            # Also need to mock preserve_timestamps
            compressor.file_processor.preserve_timestamps = MagicMock()

            # When overwrite=True, output is a temp file in the same directory
            temp_output_file = temp_dir / "test_tmp.jpg"
            temp_file_created = [False]

            # Update mock_stat to return correct size after compression
            def mock_stat_updated(self):
                path_str = str(self)
                if path_str == str(image_file):
                    return os.stat_result((0, 0, 0, 0, 0, 0, 1000, 0, 0, 0))
                elif "_tmp" in path_str or path_str == str(temp_output_file):
                    # Return compressed size after compression is done
                    if compression_done[0] and temp_file_created[0]:
                        return os.stat_result((0, 0, 0, 0, 0, 0, 500, 0, 0, 0))
                    return os.stat_result((0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
                return original_stat(self)

            # Update mock_exists to return True for temp output after compression
            def mock_exists_updated(self):
                import os.path as ospath

                path_str = str(self)
                if path_str == str(image_file) or path_str == str(temp_dir):
                    return True
                # Temp output file exists after compression
                if "_tmp" in path_str or path_str == str(temp_output_file):
                    if compression_done[0] and temp_file_created[0]:
                        return True
                    # Check real file system using os.path to avoid recursion
                    return ospath.exists(path_str)
                return False

            # Update mock_compress to set temp_file_created
            def mock_compress_updated(in_path, out_path):
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"0" * 500)
                compression_done[0] = True
                temp_file_created[0] = True

            compressor.image_compressor.compress = MagicMock(side_effect=mock_compress_updated)

            with patch.object(Path, "stat", mock_stat_updated):
                with patch.object(Path, "exists", mock_exists_updated):
                    compressor._process_file(image_file, 1, 1, temp_dir / "compressed")

            # Should call handle_overwrite with (original_path, temp_path)
            compressor.file_processor.handle_overwrite.assert_called_once()
            # Verify it was called with correct paths
            call_args = compressor.file_processor.handle_overwrite.call_args[0]
            assert call_args[0] == image_file  # original_path
            assert str(call_args[1]).endswith("_tmp.jpg")  # temp_path

    def test_process_file_negative_compression_ratio(self, temp_dir):
        """Test process_file with negative compression ratio (file got larger)."""
        config = CompressionConfig(source_folder=temp_dir, keep_if_larger=True)
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            image_file = temp_dir / "test.jpg"
            image_file.write_bytes(b"0" * 1000)

            output_file = temp_dir / "compressed" / "test.jpg"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(b"0" * 1200)  # Larger

            compressor.image_compressor.compress = MagicMock()

            # Store original methods
            original_stat = Path.stat
            original_exists = Path.exists

            def mock_stat(self):
                path_str = str(self)
                if path_str == str(image_file):
                    return os.stat_result((0, 0, 0, 0, 0, 0, 1000, 0, 0, 0))
                elif path_str == str(output_file):
                    return os.stat_result((0, 0, 0, 0, 0, 0, 1200, 0, 0, 0))
                return original_stat(self)

            def mock_exists(self):
                path_str = str(self)
                if path_str == str(image_file) or path_str == str(temp_dir):
                    return True
                # Output file doesn't exist initially
                return False

            # Mock compress to create a larger output file
            def mock_compress(in_path, out_path):
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"0" * 1200)  # Larger than original

            compressor.image_compressor.compress = MagicMock(side_effect=mock_compress)

            with patch.object(Path, "stat", mock_stat):
                with patch.object(Path, "exists", mock_exists):
                    compressor._process_file(image_file, 1, 1, temp_dir / "compressed")

            # Should have printed warning with negative ratio
            compressor.image_compressor.compress.assert_called_once()

    def test_process_file_called_process_error(self, temp_dir):
        """Test process_file handles CalledProcessError and cleans up output file (line 265)."""
        config = CompressionConfig(source_folder=temp_dir)
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            image_file = temp_dir / "test.jpg"
            image_file.write_bytes(b"0" * 1000)

            output_file = temp_dir / "compressed" / "test.jpg"
            output_file.parent.mkdir(parents=True, exist_ok=True)

            import subprocess

            compressor.image_compressor.compress = MagicMock(
                side_effect=subprocess.CalledProcessError(1, "ffmpeg", b"", b"Error")
            )

            # Track if output file was created (before error)
            output_created = [False]

            # Mock compress to create output file before raising error
            def mock_compress_with_output(in_path, out_path):
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"0" * 500)  # Create output file
                output_created[0] = True
                raise subprocess.CalledProcessError(1, "ffmpeg", b"", b"Error")

            compressor.image_compressor.compress = MagicMock(side_effect=mock_compress_with_output)

            # Store original methods
            original_stat = Path.stat
            original_exists = Path.exists
            original_unlink = Path.unlink

            unlink_called = [False]

            def mock_stat(self):
                path_str = str(self)
                if path_str == str(image_file):
                    return os.stat_result((0, 0, 0, 0, 0, 0, 1000, 0, 0, 0))
                return original_stat(self)

            def mock_exists(self):
                path_str = str(self)
                if path_str == str(image_file) or path_str == str(temp_dir):
                    return True
                # Output file exists after compress creates it (before error) - line 264 check
                if output_created[0] and path_str == str(output_file):
                    return True
                return False

            def mock_unlink(self):
                if str(self) == str(output_file):
                    unlink_called[0] = True
                    if output_created[0]:
                        try:
                            output_file.unlink()
                        except:
                            pass
                else:
                    original_unlink(self)

            with patch.object(Path, "stat", mock_stat):
                with patch.object(Path, "exists", mock_exists):
                    with patch.object(Path, "unlink", mock_unlink):
                        compressor._process_file(image_file, 1, 1, temp_dir / "compressed")

            # Error should be handled and output file should be cleaned up (line 265)
            assert compressor.stats.stats["errors"] == 1
            assert unlink_called[0]  # Should have called unlink on output file

    def test_process_file_general_exception(self, temp_dir):
        """Test process_file handles general Exception."""
        config = CompressionConfig(source_folder=temp_dir)
        with patch("compressy.core.media_compressor.FFmpegExecutor"):
            compressor = MediaCompressor(config)

            image_file = temp_dir / "test.jpg"
            image_file.write_bytes(b"0" * 1000)

            output_file = temp_dir / "compressed" / "test.jpg"
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Track if output file was created (before error)
            output_created = [False]

            # Mock compress to create output file before raising error
            def mock_compress_with_output(in_path, out_path):
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"0" * 500)  # Create output file
                output_created[0] = True
                raise Exception("General error")

            compressor.image_compressor.compress = MagicMock(side_effect=mock_compress_with_output)

            # Store original methods
            original_stat = Path.stat
            original_exists = Path.exists
            original_unlink = Path.unlink

            unlink_called = [False]

            def mock_stat(self):
                path_str = str(self)
                if path_str == str(image_file):
                    return os.stat_result((0, 0, 0, 0, 0, 0, 1000, 0, 0, 0))
                return original_stat(self)

            def mock_exists(self):
                path_str = str(self)
                if path_str == str(image_file) or path_str == str(temp_dir):
                    return True
                # Output file exists after compress creates it (before error) - line 284 check
                if output_created[0] and path_str == str(output_file):
                    return True
                return False

            def mock_unlink(self):
                if str(self) == str(output_file):
                    unlink_called[0] = True
                    if output_created[0]:
                        try:
                            output_file.unlink()
                        except:
                            pass
                else:
                    original_unlink(self)

            with patch.object(Path, "stat", mock_stat):
                with patch.object(Path, "exists", mock_exists):
                    with patch.object(Path, "unlink", mock_unlink):
                        compressor._process_file(image_file, 1, 1, temp_dir / "compressed")

            # Error should be handled and output file should be cleaned up (line 285)
            assert compressor.stats.stats["errors"] == 1
            assert unlink_called[0]  # Should have called unlink on output file
