import shutil
from datetime import datetime
from pathlib import Path

from compressy.utils.logger import get_logger


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
        logger = get_logger()
        logger.info(f"Starting backup creation for: {source_folder}")

        backup_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Backup directory created/verified: {backup_dir}")

        # Create backup folder with the same name as source folder
        backup_folder_name = source_folder.name
        backup_path = backup_dir / backup_folder_name

        # If backup already exists, add a timestamp to make it unique
        if backup_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{backup_folder_name}_{timestamp}"
            logger.debug(f"Backup path already exists, using timestamped name: {backup_path}")

        print(f"Creating backup to: {backup_path}")
        print("This may take a while for large folders...")

        try:
            # Copy entire directory tree
            shutil.copytree(source_folder, backup_path, dirs_exist_ok=False)
            logger.info(f"Backup created successfully: {backup_path}")
            print(f"✓ Backup created successfully: {backup_path}")
            return backup_path
        except Exception:
            logger.error(
                "Failed to create backup",
                exc_info=True,
                extra={"source": str(source_folder), "backup_path": str(backup_path)},
            )
            raise
