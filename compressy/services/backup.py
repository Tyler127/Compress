import shutil
from datetime import datetime
from pathlib import Path

# ============================================================================
# Backup Manager
# ============================================================================


class BackupManager:
    """Handles backup operations."""

    @staticmethod
    def create_backup(source_folder: Path, backup_dir: Path) -> Path:
        """
        Create a backup of the source folder in the backup directory.

        Args:
            source_folder: Path to the source folder to backup
            backup_dir: Path to the backup directory

        Returns:
            Path to the created backup folder
        """
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Create backup folder with the same name as source folder
        backup_folder_name = source_folder.name
        backup_path = backup_dir / backup_folder_name

        # If backup already exists, add a timestamp to make it unique
        if backup_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{backup_folder_name}_{timestamp}"

        print(f"Creating backup to: {backup_path}")
        print("This may take a while for large folders...")

        # Copy entire directory tree
        shutil.copytree(source_folder, backup_path, dirs_exist_ok=False)

        print(f"✓ Backup created successfully: {backup_path}")
        return backup_path
