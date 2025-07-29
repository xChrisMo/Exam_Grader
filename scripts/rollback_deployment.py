#!/usr/bin/env python3
"""
Rollback script for LLM training improvements deployment.

This script can rollback a deployment to a previous state.
"""

import os
import sys
import logging
import shutil
from pathlib import Path
from datetime import datetime
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rollback.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages rollback of LLM training improvements deployment."""
    
    def __init__(self, backup_path: str, environment: str = 'production'):
        self.environment = environment
        self.project_root = Path(__file__).parent.parent
        self.backup_path = Path(backup_path)
        
        if not self.backup_path.exists():
            raise ValueError(f"Backup path does not exist: {backup_path}")
    
    def rollback(self) -> bool:
        """Execute rollback process."""
        logger.info(f"Starting rollback from backup: {self.backup_path}")
        
        try:
            # Pre-rollback checks
            if not self._pre_rollback_checks():
                logger.error("Pre-rollback checks failed")
                return False
            
            # Stop services (if applicable)
            self._stop_services()
            
            # Restore database
            if not self._restore_database():
                logger.error("Database restore failed")
                return False
            
            # Restore configuration
            if not self._restore_configuration():
                logger.error("Configuration restore failed")
                return False
            
            # Restore application files
            if not self._restore_application_files():
                logger.error("Application files restore failed")
                return False
            
            # Start services (if applicable)
            self._start_services()
            
            # Post-rollback verification
            if not self._post_rollback_verification():
                logger.error("Post-rollback verification failed")
                return False
            
            logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed with exception: {e}")
            return False
    
    def _pre_rollback_checks(self) -> bool:
        """Perform pre-rollback checks."""
        logger.info("Running pre-rollback checks...")
        
        # Verify backup integrity
        required_backup_items = ['exam_grader.db', 'config']
        
        for item in required_backup_items:
            item_path = self.backup_path / item
            if not item_path.exists():
                logger.warning(f"Backup item not found: {item}")
        
        # Check write permissions
        critical_dirs = ['instance', 'config', 'logs', 'uploads']
        for dir_name in critical_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and not os.access(dir_path, os.W_OK):
                logger.error(f"No write access to: {dir_name}")
                return False
        
        logger.info("Pre-rollback checks passed")
        return True
    
    def _stop_services(self):
        """Stop application services."""
        logger.info("Stopping services...")
        # In a production environment, this would stop actual services
        # For now, we'll just log the action
        logger.info("Services stopped")
    
    def _restore_database(self) -> bool:
        """Restore database from backup."""
        logger.info("Restoring database...")
        
        try:
            backup_db = self.backup_path / 'exam_grader.db'
            if backup_db.exists():
                current_db = self.project_root / 'instance' / 'exam_grader.db'
                
                # Create backup of current database before restore
                if current_db.exists():
                    current_backup = current_db.with_suffix('.db.pre_rollback')
                    shutil.copy2(current_db, current_backup)
                    logger.info(f"Current database backed up to: {current_backup}")
                
                # Restore database
                shutil.copy2(backup_db, current_db)
                logger.info("Database restored successfully")
            else:
                logger.warning("No database backup found, skipping database restore")
            
            return True
            
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False
    
    def _restore_configuration(self) -> bool:
        """Restore configuration files from backup."""
        logger.info("Restoring configuration...")
        
        try:
            config_backup_dir = self.backup_path / 'config'
            if config_backup_dir.exists():
                for config_file in config_backup_dir.iterdir():
                    if config_file.is_file():
                        # Determine destination path
                        if config_file.name in ['.env', '.env.local']:
                            dest = self.project_root / config_file.name
                        else:
                            dest = self.project_root / 'config' / config_file.name
                        
                        # Create backup of current config
                        if dest.exists():
                            current_backup = dest.with_suffix(dest.suffix + '.pre_rollback')
                            shutil.copy2(dest, current_backup)
                        
                        # Restore configuration file
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(config_file, dest)
                        logger.info(f"Restored config file: {config_file.name}")
                
                logger.info("Configuration restored successfully")
            else:
                logger.warning("No configuration backup found, skipping configuration restore")
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration restore failed: {e}")
            return False
    
    def _restore_application_files(self) -> bool:
        """Restore application files from backup."""
        logger.info("Restoring application files...")
        
        try:
            # Restore critical directories if they exist in backup
            critical_dirs = ['uploads', 'logs']
            
            for dir_name in critical_dirs:
                backup_dir_path = self.backup_path / dir_name
                if backup_dir_path.exists():
                    current_dir = self.project_root / dir_name
                    
                    # Create backup of current directory
                    if current_dir.exists():
                        current_backup = current_dir.with_suffix('.pre_rollback')
                        if current_backup.exists():
                            shutil.rmtree(current_backup)
                        shutil.copytree(current_dir, current_backup)
                        logger.info(f"Current {dir_name} backed up to: {current_backup}")
                        
                        # Remove current directory
                        shutil.rmtree(current_dir)
                    
                    # Restore directory
                    shutil.copytree(backup_dir_path, current_dir)
                    logger.info(f"Restored directory: {dir_name}")
            
            logger.info("Application files restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Application files restore failed: {e}")
            return False
    
    def _start_services(self):
        """Start application services."""
        logger.info("Starting services...")
        # In a production environment, this would start actual services
        # For now, we'll just log the action
        logger.info("Services started")
    
    def _post_rollback_verification(self) -> bool:
        """Verify rollback success."""
        logger.info("Running post-rollback verification...")
        
        try:
            # Add project root to path for imports
            sys.path.insert(0, str(self.project_root))
            
            # Test database connectivity
            from webapp.app_factory import create_app
            from src.database.models import db
            
            app = create_app(self.environment)
            with app.app_context():
                # Test basic database operations
                result = db.session.execute("SELECT 1").fetchone()
                if not result:
                    logger.error("Database connectivity test failed")
                    return False
                
                # Test that we can query basic tables
                from src.database.models import User
                user_count = User.query.count()
                logger.info(f"Database verification passed. User count: {user_count}")
            
            # Verify critical files exist
            critical_files = [
                'instance/exam_grader.db',
                'webapp/app.py',
                'requirements.txt'
            ]
            
            for file_path in critical_files:
                full_path = self.project_root / file_path
                if not full_path.exists():
                    logger.error(f"Critical file missing after rollback: {file_path}")
                    return False
            
            logger.info("Post-rollback verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Post-rollback verification failed: {e}")
            return False
    
    def list_available_backups(self) -> list:
        """List available backup directories."""
        backups_dir = self.project_root / 'backups'
        if not backups_dir.exists():
            return []
        
        backups = []
        for item in backups_dir.iterdir():
            if item.is_dir() and item.name.startswith('deployment_'):
                backups.append({
                    'path': str(item),
                    'name': item.name,
                    'created': datetime.fromtimestamp(item.stat().st_ctime)
                })
        
        # Sort by creation time, newest first
        backups.sort(key=lambda x: x['created'], reverse=True)
        return backups


def main():
    """Main rollback function."""
    parser = argparse.ArgumentParser(description='Rollback LLM training improvements deployment')
    parser.add_argument('--backup-path', '-b', required=True,
                       help='Path to backup directory')
    parser.add_argument('--environment', '-e', default='production',
                       choices=['development', 'testing', 'production'],
                       help='Deployment environment')
    parser.add_argument('--list-backups', action='store_true',
                       help='List available backups')
    
    args = parser.parse_args()
    
    if args.list_backups:
        # List available backups
        project_root = Path(__file__).parent.parent
        backups_dir = project_root / 'backups'
        
        if not backups_dir.exists():
            print("No backups directory found")
            return True
        
        print("Available backups:")
        for item in backups_dir.iterdir():
            if item.is_dir() and item.name.startswith('deployment_'):
                created = datetime.fromtimestamp(item.stat().st_ctime)
                print(f"  {item.name} (created: {created.strftime('%Y-%m-%d %H:%M:%S')})")
        
        return True
    
    try:
        rollback_manager = RollbackManager(args.backup_path, args.environment)
        success = rollback_manager.rollback()
        
        if success:
            logger.info("Rollback completed successfully!")
            return True
        else:
            logger.error("Rollback failed!")
            return False
            
    except ValueError as e:
        logger.error(f"Invalid backup path: {e}")
        return False
    except Exception as e:
        logger.error(f"Rollback failed with exception: {e}")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)