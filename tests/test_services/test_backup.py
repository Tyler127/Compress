"""
Tests for compressy.services.backup module.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from compressy.services.backup import BackupManager


@pytest.mark.unit
class TestBackupManager:
    """Tests for BackupManager class."""

    def test_create_backup_new_directory(self, temp_dir):
        """Test creating backup in new directory."""
        source_folder = temp_dir / "source"
        source_folder.mkdir()
        (source_folder / "file1.txt").write_text("content1")
        (source_folder / "file2.txt").write_text("content2")

        backup_dir = temp_dir / "backups"

        with patch("compressy.services.backup.shutil.copytree") as mock_copytree:
            backup_path = BackupManager.create_backup(source_folder, backup_dir)

            assert backup_dir.exists()
            assert backup_path == backup_dir / source_folder.name
            mock_copytree.assert_called_once_with(source_folder, backup_path, dirs_exist_ok=False)

    def test_create_backup_existing_backup(self, temp_dir):
        """Test creating backup when backup already exists (adds timestamp)."""
        source_folder = temp_dir / "source"
        source_folder.mkdir()

        backup_dir = temp_dir / "backups"
        backup_dir.mkdir()
        existing_backup = backup_dir / source_folder.name
        existing_backup.mkdir()

        with patch("compressy.services.backup.shutil.copytree") as mock_copytree:
            with patch("compressy.services.backup.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20240101_120000"

                backup_path = BackupManager.create_backup(source_folder, backup_dir)

                # Should have timestamp appended
                expected_name = f"{source_folder.name}_20240101_120000"
                assert backup_path.name == expected_name
                mock_copytree.assert_called_once()

    def test_create_backup_creates_directory(self, temp_dir):
        """Test that backup directory is created if it doesn't exist."""
        source_folder = temp_dir / "source"
        source_folder.mkdir()

        backup_dir = temp_dir / "backups" / "nested"

        assert not backup_dir.exists()

        with patch("compressy.services.backup.shutil.copytree"):
            BackupManager.create_backup(source_folder, backup_dir)

            assert backup_dir.exists()

    def test_create_backup_calls_copytree(self, temp_dir):
        """Test that shutil.copytree is called with correct arguments."""
        source_folder = temp_dir / "source"
        source_folder.mkdir()
        backup_dir = temp_dir / "backups"

        with patch("compressy.services.backup.shutil.copytree") as mock_copytree:
            backup_path = BackupManager.create_backup(source_folder, backup_dir)

            mock_copytree.assert_called_once_with(source_folder, backup_path, dirs_exist_ok=False)

    def test_create_backup_returns_path(self, temp_dir):
        """Test that create_backup returns the backup path."""
        source_folder = temp_dir / "source"
        source_folder.mkdir()
        backup_dir = temp_dir / "backups"

        with patch("compressy.services.backup.shutil.copytree"):
            backup_path = BackupManager.create_backup(source_folder, backup_dir)

            assert isinstance(backup_path, Path)
            assert backup_path.parent == backup_dir
            assert backup_path.name == source_folder.name or backup_path.name.startswith(source_folder.name + "_")
