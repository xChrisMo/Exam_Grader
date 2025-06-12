#!/usr/bin/env python3
"""
File Protection System - Prevents Code Reversions
Monitors critical files and prevents accidental overwrites or reversions.
"""

import os
import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class FileProtectionSystem:
    """Protects critical files from accidental reversions."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.protection_dir = self.project_root / ".file_protection"
        self.state_file = self.protection_dir / "protection_state.json"
        self.backup_dir = self.protection_dir / "backups"
        
        # Critical files that should be protected
        self.protected_files = [
            "webapp/exam_grader_app.py",
            "webapp/templates/upload_submission_multiple.html",
            "src/services/batch_processing_service.py",
            "src/parsing/parse_submission.py",
            "utils/file_protection.py"
        ]
        
        self._ensure_directories()
        self._load_state()
    
    def _ensure_directories(self):
        """Create protection directories if they don't exist."""
        self.protection_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
    
    def _load_state(self):
        """Load protection state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
            else:
                self.state = {"protected_files": {}, "last_check": None}
        except Exception as e:
            logger.warning(f"Could not load protection state: {e}")
            self.state = {"protected_files": {}, "last_check": None}
    
    def _save_state(self):
        """Save protection state to file."""
        try:
            self.state["last_check"] = datetime.now().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save protection state: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Could not calculate hash for {file_path}: {e}")
            return ""
    
    def protect_file(self, relative_path: str) -> bool:
        """Add a file to protection and create backup."""
        try:
            file_path = self.project_root / relative_path
            if not file_path.exists():
                logger.warning(f"File does not exist: {file_path}")
                return False
            
            # Calculate current hash
            current_hash = self._calculate_file_hash(file_path)
            
            # Create backup
            backup_name = f"{relative_path.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup"
            backup_path = self.backup_dir / backup_name
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
            
            # Update state
            self.state["protected_files"][relative_path] = {
                "hash": current_hash,
                "protected_at": datetime.now().isoformat(),
                "backup_path": str(backup_path),
                "size": file_path.stat().st_size
            }
            
            self._save_state()
            logger.info(f"Protected file: {relative_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error protecting file {relative_path}: {e}")
            return False
    
    def check_file_integrity(self, relative_path: str) -> Tuple[bool, Optional[str]]:
        """Check if a protected file has been modified unexpectedly."""
        try:
            if relative_path not in self.state["protected_files"]:
                return True, None  # Not protected, so no issue
            
            file_path = self.project_root / relative_path
            if not file_path.exists():
                return False, f"Protected file missing: {relative_path}"
            
            current_hash = self._calculate_file_hash(file_path)
            expected_hash = self.state["protected_files"][relative_path]["hash"]
            
            if current_hash != expected_hash:
                return False, f"File modified unexpectedly: {relative_path}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error checking integrity for {relative_path}: {e}")
            return False, f"Error checking file: {str(e)}"
    
    def update_protection(self, relative_path: str) -> bool:
        """Update protection for a file after intentional modification."""
        try:
            file_path = self.project_root / relative_path
            if not file_path.exists():
                return False
            
            # Create new backup
            current_hash = self._calculate_file_hash(file_path)
            backup_name = f"{relative_path.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup"
            backup_path = self.backup_dir / backup_name
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
            
            # Update state
            if relative_path in self.state["protected_files"]:
                self.state["protected_files"][relative_path].update({
                    "hash": current_hash,
                    "updated_at": datetime.now().isoformat(),
                    "backup_path": str(backup_path),
                    "size": file_path.stat().st_size
                })
            else:
                self.state["protected_files"][relative_path] = {
                    "hash": current_hash,
                    "protected_at": datetime.now().isoformat(),
                    "backup_path": str(backup_path),
                    "size": file_path.stat().st_size
                }
            
            self._save_state()
            logger.info(f"Updated protection for: {relative_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating protection for {relative_path}: {e}")
            return False
    
    def protect_all_critical_files(self) -> Dict[str, bool]:
        """Protect all critical files."""
        results = {}
        for file_path in self.protected_files:
            results[file_path] = self.protect_file(file_path)
        return results
    
    def check_all_integrity(self) -> Dict[str, Tuple[bool, Optional[str]]]:
        """Check integrity of all protected files."""
        results = {}
        for file_path in self.state["protected_files"]:
            results[file_path] = self.check_file_integrity(file_path)
        return results
    
    def restore_file(self, relative_path: str) -> bool:
        """Restore a file from its latest backup."""
        try:
            if relative_path not in self.state["protected_files"]:
                logger.warning(f"File not protected: {relative_path}")
                return False
            
            backup_path = Path(self.state["protected_files"][relative_path]["backup_path"])
            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_path}")
                return False
            
            file_path = self.project_root / relative_path
            shutil.copy2(backup_path, file_path)
            
            logger.info(f"Restored file: {relative_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring file {relative_path}: {e}")
            return False
    
    def get_protection_status(self) -> Dict[str, any]:
        """Get current protection status."""
        return {
            "protected_files_count": len(self.state["protected_files"]),
            "protected_files": list(self.state["protected_files"].keys()),
            "last_check": self.state.get("last_check"),
            "backup_directory": str(self.backup_dir),
            "total_backups": len(list(self.backup_dir.glob("*.backup"))) if self.backup_dir.exists() else 0
        }


def initialize_file_protection(project_root: str = None) -> FileProtectionSystem:
    """Initialize file protection system."""
    if project_root is None:
        project_root = Path(__file__).parent.parent
    
    protection = FileProtectionSystem(project_root)
    
    # Protect all critical files
    results = protection.protect_all_critical_files()
    
    logger.info("File protection system initialized")
    logger.info(f"Protected {sum(results.values())} out of {len(results)} critical files")
    
    return protection


if __name__ == "__main__":
    # Initialize protection when run directly
    protection = initialize_file_protection()
    status = protection.get_protection_status()
    print(f"File Protection Status: {json.dumps(status, indent=2)}")
