#!/usr/bin/env python3
"""
Version Lock System - Prevents Accidental Code Reversions
Creates version locks and validates critical functionality.
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class VersionLock:
    """Creates and validates version locks for critical functionality."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.lock_file = self.project_root / ".version_lock.json"
        self.load_locks()
    
    def load_locks(self):
        """Load existing version locks."""
        try:
            if self.lock_file.exists():
                with open(self.lock_file, 'r') as f:
                    self.locks = json.load(f)
            else:
                self.locks = {"version": "1.0.0", "features": {}, "created": datetime.now().isoformat()}
        except Exception as e:
            logger.warning(f"Could not load version locks: {e}")
            self.locks = {"version": "1.0.0", "features": {}, "created": datetime.now().isoformat()}
    
    def save_locks(self):
        """Save version locks to file."""
        try:
            self.locks["last_updated"] = datetime.now().isoformat()
            with open(self.lock_file, 'w') as f:
                json.dump(self.locks, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save version locks: {e}")
    
    def create_feature_lock(self, feature_name: str, description: str, files: List[str], validation_points: List[str]):
        """Create a lock for a specific feature."""
        feature_lock = {
            "description": description,
            "files": files,
            "validation_points": validation_points,
            "created": datetime.now().isoformat(),
            "file_hashes": {},
            "status": "active"
        }
        
        # Calculate file hashes
        for file_path in files:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'rb') as f:
                        feature_lock["file_hashes"][file_path] = hashlib.sha256(f.read()).hexdigest()
                except Exception as e:
                    logger.warning(f"Could not hash file {file_path}: {e}")
        
        self.locks["features"][feature_name] = feature_lock
        self.save_locks()
        logger.info(f"Created feature lock: {feature_name}")
    
    def validate_feature(self, feature_name: str) -> Dict[str, any]:
        """Validate that a feature is still intact."""
        if feature_name not in self.locks["features"]:
            return {"valid": False, "error": f"Feature lock not found: {feature_name}"}
        
        feature_lock = self.locks["features"][feature_name]
        validation_result = {
            "valid": True,
            "feature": feature_name,
            "description": feature_lock["description"],
            "file_checks": {},
            "validation_checks": [],
            "errors": []
        }
        
        # Check file integrity
        for file_path, expected_hash in feature_lock["file_hashes"].items():
            full_path = self.project_root / file_path
            if not full_path.exists():
                validation_result["file_checks"][file_path] = {"status": "missing", "error": "File not found"}
                validation_result["errors"].append(f"Missing file: {file_path}")
                validation_result["valid"] = False
            else:
                try:
                    with open(full_path, 'rb') as f:
                        current_hash = hashlib.sha256(f.read()).hexdigest()
                    
                    if current_hash == expected_hash:
                        validation_result["file_checks"][file_path] = {"status": "valid", "hash_match": True}
                    else:
                        validation_result["file_checks"][file_path] = {"status": "modified", "hash_match": False}
                        validation_result["errors"].append(f"File modified: {file_path}")
                        validation_result["valid"] = False
                except Exception as e:
                    validation_result["file_checks"][file_path] = {"status": "error", "error": str(e)}
                    validation_result["errors"].append(f"Error checking {file_path}: {e}")
                    validation_result["valid"] = False
        
        # Check validation points
        for validation_point in feature_lock["validation_points"]:
            try:
                check_result = self._check_validation_point(validation_point)
                validation_result["validation_checks"].append({
                    "point": validation_point,
                    "status": "valid" if check_result else "failed",
                    "result": check_result
                })
                if not check_result:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Validation failed: {validation_point}")
            except Exception as e:
                validation_result["validation_checks"].append({
                    "point": validation_point,
                    "status": "error",
                    "error": str(e)
                })
                validation_result["errors"].append(f"Validation error for {validation_point}: {e}")
                validation_result["valid"] = False
        
        return validation_result
    
    def _check_validation_point(self, validation_point: str) -> bool:
        """Check a specific validation point."""
        if validation_point == "batch_processing_route_exists":
            app_file = self.project_root / "webapp/exam_grader_app.py"
            if app_file.exists():
                content = app_file.read_text()
                return "process_batch_submission" in content and "process_single_submission" in content
        
        elif validation_point == "multiple_upload_template_active":
            app_file = self.project_root / "webapp/exam_grader_app.py"
            if app_file.exists():
                content = app_file.read_text()
                return "upload_submission_multiple.html" in content
        
        elif validation_point == "batch_service_integrated":
            app_file = self.project_root / "webapp/exam_grader_app.py"
            if app_file.exists():
                content = app_file.read_text()
                return "BatchProcessingService" in content
        
        elif validation_point == "parse_function_imported":
            app_file = self.project_root / "webapp/exam_grader_app.py"
            if app_file.exists():
                content = app_file.read_text()
                return "parse_student_submission" in content
        
        return False
    
    def update_feature_lock(self, feature_name: str):
        """Update a feature lock after intentional changes."""
        if feature_name not in self.locks["features"]:
            logger.warning(f"Feature lock not found: {feature_name}")
            return False
        
        feature_lock = self.locks["features"][feature_name]
        
        # Recalculate file hashes
        for file_path in feature_lock["files"]:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'rb') as f:
                        feature_lock["file_hashes"][file_path] = hashlib.sha256(f.read()).hexdigest()
                except Exception as e:
                    logger.warning(f"Could not hash file {file_path}: {e}")
        
        feature_lock["last_updated"] = datetime.now().isoformat()
        self.save_locks()
        logger.info(f"Updated feature lock: {feature_name}")
        return True
    
    def get_all_feature_status(self) -> Dict[str, any]:
        """Get status of all feature locks."""
        status = {
            "total_features": len(self.locks["features"]),
            "features": {},
            "overall_valid": True
        }
        
        for feature_name in self.locks["features"]:
            validation = self.validate_feature(feature_name)
            status["features"][feature_name] = validation
            if not validation["valid"]:
                status["overall_valid"] = False
        
        return status


def create_batch_processing_lock(project_root: str = None) -> VersionLock:
    """Create version lock for batch processing functionality."""
    if project_root is None:
        project_root = Path(__file__).parent.parent
    
    version_lock = VersionLock(project_root)
    
    # Create lock for batch processing feature
    version_lock.create_feature_lock(
        feature_name="batch_processing",
        description="Multiple file upload and batch processing functionality",
        files=[
            "webapp/exam_grader_app.py",
            "webapp/templates/upload_submission_multiple.html",
            "src/services/batch_processing_service.py",
            "src/parsing/parse_submission.py"
        ],
        validation_points=[
            "batch_processing_route_exists",
            "multiple_upload_template_active",
            "batch_service_integrated",
            "parse_function_imported"
        ]
    )
    
    logger.info("Created batch processing version lock")
    return version_lock


if __name__ == "__main__":
    # Create locks when run directly
    lock = create_batch_processing_lock()
    status = lock.get_all_feature_status()
    print(f"Feature Status: {json.dumps(status, indent=2)}")
