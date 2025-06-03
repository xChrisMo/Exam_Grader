"""
Storage migration system for handling schema changes in file-based storage.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger(__name__)

class StorageMigration:
    """Base class for storage migrations."""
    
    version: str = "0.0.0"
    description: str = "Base migration"
    
    def up(self, storage_dir: Path) -> bool:
        """Apply the migration."""
        raise NotImplementedError("Subclasses must implement up()")
    
    def down(self, storage_dir: Path) -> bool:
        """Rollback the migration."""
        raise NotImplementedError("Subclasses must implement down()")

class Migration_001_InitialSchema(StorageMigration):
    """Initial schema migration."""
    
    version = "1.0.0"
    description = "Initial storage schema"
    
    def up(self, storage_dir: Path) -> bool:
        """Create initial directory structure."""
        try:
            # Create subdirectories for different data types
            (storage_dir / "submissions").mkdir(parents=True, exist_ok=True)
            (storage_dir / "guides").mkdir(parents=True, exist_ok=True)
            (storage_dir / "mappings").mkdir(parents=True, exist_ok=True)
            (storage_dir / "results").mkdir(parents=True, exist_ok=True)
            
            logger.info("Created initial storage directory structure")
            return True
        except Exception as e:
            logger.error(f"Failed to create initial schema: {str(e)}")
            return False
    
    def down(self, storage_dir: Path) -> bool:
        """Remove initial directory structure."""
        try:
            # Note: This is destructive and should be used carefully
            for subdir in ["submissions", "guides", "mappings", "results"]:
                subdir_path = storage_dir / subdir
                if subdir_path.exists():
                    for file in subdir_path.glob("*"):
                        file.unlink()
                    subdir_path.rmdir()
            
            logger.info("Removed initial storage directory structure")
            return True
        except Exception as e:
            logger.error(f"Failed to rollback initial schema: {str(e)}")
            return False

class Migration_002_AddTimestamps(StorageMigration):
    """Add timestamp fields to existing data."""
    
    version = "1.1.0"
    description = "Add timestamp fields to existing storage files"
    
    def up(self, storage_dir: Path) -> bool:
        """Add timestamp fields to existing files."""
        try:
            current_time = datetime.now().isoformat()
            updated_count = 0
            
            # Update all JSON files in storage
            for json_file in storage_dir.rglob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Add timestamps if they don't exist
                    if 'created_at' not in data:
                        data['created_at'] = current_time
                    if 'updated_at' not in data:
                        data['updated_at'] = current_time
                    
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    updated_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to update file {json_file}: {str(e)}")
                    continue
            
            logger.info(f"Added timestamps to {updated_count} storage files")
            return True
        except Exception as e:
            logger.error(f"Failed to add timestamps: {str(e)}")
            return False
    
    def down(self, storage_dir: Path) -> bool:
        """Remove timestamp fields from files."""
        try:
            updated_count = 0
            
            for json_file in storage_dir.rglob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Remove timestamp fields
                    data.pop('created_at', None)
                    data.pop('updated_at', None)
                    
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    updated_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to update file {json_file}: {str(e)}")
                    continue
            
            logger.info(f"Removed timestamps from {updated_count} storage files")
            return True
        except Exception as e:
            logger.error(f"Failed to remove timestamps: {str(e)}")
            return False

class MigrationManager:
    """Manages storage migrations."""
    
    def __init__(self, storage_dir: str = "output"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.migration_file = self.storage_dir / ".migrations.json"
        
        # Register available migrations
        self.migrations = [
            Migration_001_InitialSchema(),
            Migration_002_AddTimestamps(),
        ]
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        if not self.migration_file.exists():
            return []
        
        try:
            with open(self.migration_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('applied_migrations', [])
        except Exception as e:
            logger.error(f"Failed to read migration file: {str(e)}")
            return []
    
    def save_applied_migrations(self, applied_migrations: List[str]) -> bool:
        """Save list of applied migrations."""
        try:
            data = {
                'applied_migrations': applied_migrations,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.migration_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save migration file: {str(e)}")
            return False
    
    def run_migrations(self) -> bool:
        """Run all pending migrations."""
        applied_migrations = self.get_applied_migrations()
        pending_migrations = [
            m for m in self.migrations 
            if m.version not in applied_migrations
        ]
        
        if not pending_migrations:
            logger.info("No pending migrations")
            return True
        
        logger.info(f"Running {len(pending_migrations)} pending migrations")
        
        for migration in pending_migrations:
            logger.info(f"Applying migration {migration.version}: {migration.description}")
            
            try:
                if migration.up(self.storage_dir):
                    applied_migrations.append(migration.version)
                    logger.info(f"Successfully applied migration {migration.version}")
                else:
                    logger.error(f"Failed to apply migration {migration.version}")
                    return False
            except Exception as e:
                logger.error(f"Error applying migration {migration.version}: {str(e)}")
                return False
        
        # Save updated migration list
        return self.save_applied_migrations(applied_migrations)
    
    def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration."""
        applied_migrations = self.get_applied_migrations()
        
        if version not in applied_migrations:
            logger.warning(f"Migration {version} is not applied")
            return False
        
        # Find the migration
        migration = next((m for m in self.migrations if m.version == version), None)
        if not migration:
            logger.error(f"Migration {version} not found")
            return False
        
        logger.info(f"Rolling back migration {version}: {migration.description}")
        
        try:
            if migration.down(self.storage_dir):
                applied_migrations.remove(version)
                self.save_applied_migrations(applied_migrations)
                logger.info(f"Successfully rolled back migration {version}")
                return True
            else:
                logger.error(f"Failed to rollback migration {version}")
                return False
        except Exception as e:
            logger.error(f"Error rolling back migration {version}: {str(e)}")
            return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status."""
        applied_migrations = self.get_applied_migrations()
        
        return {
            'total_migrations': len(self.migrations),
            'applied_count': len(applied_migrations),
            'pending_count': len(self.migrations) - len(applied_migrations),
            'applied_migrations': applied_migrations,
            'pending_migrations': [
                m.version for m in self.migrations 
                if m.version not in applied_migrations
            ]
        }
