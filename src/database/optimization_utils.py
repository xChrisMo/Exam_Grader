"""Database optimization utilities for applying migrations and validating schema."""
from typing import Dict, List, Optional

import logging
from datetime import datetime

from sqlalchemy import create_engine, inspect, text
from flask import current_app

from .schema_migrations import MigrationManager

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """Utility class for database optimization and validation."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize the database optimizer.
        
        Args:
            database_url: Database URL. If None, uses current app config.
        """
        self.database_url = database_url or current_app.config['SQLALCHEMY_DATABASE_URI']
        self.engine = create_engine(self.database_url)
        self.migration_manager = MigrationManager(self.database_url)
    
    def apply_all_migrations(self) -> Dict[str, bool]:
        """Apply all available migrations.
        
        Returns:
            Dictionary mapping migration version to success status.
        """
        results = {}
        
        for migration in self.migration_manager.migrations:
            try:
                logger.info(f"Applying migration {migration.version}: {migration.description}")
                success = self.migration_manager.apply_migration(migration.version)
                results[migration.version] = success
                
                if success:
                    logger.info(f"Successfully applied migration {migration.version}")
                else:
                    logger.error(f"Failed to apply migration {migration.version}")
                    
            except Exception as e:
                logger.error(f"Error applying migration {migration.version}: {str(e)}")
                results[migration.version] = False
        
        return results
    
    def validate_indexes(self) -> Dict[str, List[str]]:
        """Validate that all expected indexes exist.
        
        Returns:
            Dictionary with 'existing' and 'missing' index lists.
        """
        inspector = inspect(self.engine)
        
        expected_indexes = {
            'users': [
                'idx_user_active_login',
                'idx_user_created_active',
                'idx_user_email_verified_active',
                'idx_user_locked_until_active',
                'idx_user_password_changed',
                'idx_users_created_at',
                'idx_users_updated_at'
            ],
            'marking_guides': [
                'idx_guide_user_active',
                'idx_guide_created_active',
                'idx_guide_hash_size',
                'idx_guide_file_type_size',
                'idx_guide_total_marks_active',
                'idx_guide_questions_marks',
                'idx_marking_guides_created_at',
                'idx_marking_guides_updated_at'
            ],
            'submissions': [
                'idx_submission_hash_guide',
                'idx_submission_status_confidence',
                'idx_submission_student_guide',
                'idx_submission_archived_processed',
                'idx_submissions_created_at',
                'idx_submissions_updated_at'
            ],
            'mappings': [
                'idx_mapping_score',
                'idx_mapping_method',
                'idx_mapping_submission_question',
                'idx_mapping_score_method',
                'idx_mappings_created_at'
            ],
            'grading_results': [
                'idx_grading_progress_id',
                'idx_grading_score_confidence',
                'idx_grading_method_progress',
                'idx_grading_percentage_method',
                'idx_grading_results_created_at'
            ],
            'sessions': [
                'idx_session_expires',
                'idx_session_ip',
                'idx_session_user_active_expires',
                'idx_session_ip_user_agent',
                'idx_sessions_created_at'
            ],
            'grading_sessions': [
                'idx_grading_session_status_step',
                'idx_grading_session_progress_status',
                'idx_grading_session_user_guide',
                'idx_grading_session_questions_mapped',
                'idx_grading_sessions_created_at'
            ]
        }
        
        existing_indexes = []
        missing_indexes = []
        
        for table_name, expected in expected_indexes.items():
            try:
                table_indexes = inspector.get_indexes(table_name)
                existing_index_names = [idx['name'] for idx in table_indexes if idx['name']]
                
                for expected_index in expected:
                    if expected_index in existing_index_names:
                        existing_indexes.append(f"{table_name}.{expected_index}")
                    else:
                        missing_indexes.append(f"{table_name}.{expected_index}")
                        
            except Exception as e:
                logger.warning(f"Could not inspect indexes for table {table_name}: {str(e)}")
        
        return {
            'existing': existing_indexes,
            'missing': missing_indexes
        }
    
    def validate_foreign_keys(self) -> Dict[str, List[str]]:
        """Validate that all expected foreign keys exist.
        
        Returns:
            Dictionary with 'existing' and 'missing' foreign key lists.
        """
        inspector = inspect(self.engine)
        
        # Expected foreign keys
        expected_foreign_keys = {
            'marking_guides': ['user_id'],
            'submissions': ['user_id', 'marking_guide_id'],
            'mappings': ['submission_id'],
            'grading_results': ['submission_id', 'mapping_id'],
            'sessions': ['user_id'],
            'grading_sessions': ['submission_id', 'marking_guide_id', 'user_id']
        }
        
        existing_fks = []
        missing_fks = []
        
        for table_name, expected in expected_foreign_keys.items():
            try:
                table_fks = inspector.get_foreign_keys(table_name)
                existing_fk_columns = [fk['constrained_columns'][0] for fk in table_fks if fk['constrained_columns']]
                
                for expected_fk in expected:
                    if expected_fk in existing_fk_columns:
                        existing_fks.append(f"{table_name}.{expected_fk}")
                    else:
                        missing_fks.append(f"{table_name}.{expected_fk}")
                        
            except Exception as e:
                logger.warning(f"Could not inspect foreign keys for table {table_name}: {str(e)}")
        
        return {
            'existing': existing_fks,
            'missing': missing_fks
        }
    
    def validate_constraints(self) -> Dict[str, List[str]]:
        """Validate that all expected constraints exist.
        
        Returns:
            Dictionary with constraint validation results.
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='trigger' AND name LIKE 'validate_%'
                """))
                
                existing_triggers = [row[0] for row in result.fetchall()]
                
                expected_triggers = [
                    'validate_user_email_format',
                    'validate_user_email_format_update',
                    'validate_submission_status',
                    'validate_submission_status_update',
                    'validate_grading_session_status',
                    'validate_grading_session_status_update',
                    'validate_grading_session_step',
                    'validate_grading_session_step_update'
                ]
                
                missing_triggers = [t for t in expected_triggers if t not in existing_triggers]
                
                return {
                    'existing': existing_triggers,
                    'missing': missing_triggers
                }
                
        except Exception as e:
            logger.error(f"Error validating constraints: {str(e)}")
            return {'existing': [], 'missing': []}
    
    def validate_views(self) -> Dict[str, List[str]]:
        """Validate that all expected views exist.
        
        Returns:
            Dictionary with view validation results.
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='view'
                """))
                
                existing_views = [row[0] for row in result.fetchall()]
                
                expected_views = [
                    'user_activity_stats',
                    'submission_processing_stats',
                    'grading_session_performance'
                ]
                
                missing_views = [v for v in expected_views if v not in existing_views]
                
                return {
                    'existing': existing_views,
                    'missing': missing_views
                }
                
        except Exception as e:
            logger.error(f"Error validating views: {str(e)}")
            return {'existing': [], 'missing': []}
    
    def generate_optimization_report(self) -> Dict[str, any]:
        """Generate a comprehensive optimization report.
        
        Returns:
            Dictionary containing optimization status and recommendations.
        """
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'database_url': self.database_url,
            'indexes': self.validate_indexes(),
            'foreign_keys': self.validate_foreign_keys(),
            'constraints': self.validate_constraints(),
            'views': self.validate_views(),
            'recommendations': []
        }
        
        # Generate recommendations
        if report['indexes']['missing']:
            report['recommendations'].append(
                f"Apply missing indexes: {', '.join(report['indexes']['missing'])}"
            )
        
        if report['foreign_keys']['missing']:
            report['recommendations'].append(
                f"Add missing foreign keys: {', '.join(report['foreign_keys']['missing'])}"
            )
        
        if report['constraints']['missing']:
            report['recommendations'].append(
                f"Add missing validation triggers: {', '.join(report['constraints']['missing'])}"
            )
        
        if report['views']['missing']:
            report['recommendations'].append(
                f"Create missing views: {', '.join(report['views']['missing'])}"
            )
        
        if not report['recommendations']:
            report['recommendations'].append("Database is fully optimized!")
        
        return report
    
    def optimize_database(self) -> Dict[str, any]:
        """Apply all optimizations and return a report.
        
        Returns:
            Dictionary containing optimization results.
        """
        logger.info("Starting database optimization...")
        
        # Apply all migrations
        migration_results = self.apply_all_migrations()
        
        # Generate final report
        optimization_report = self.generate_optimization_report()
        
        result = {
            'migration_results': migration_results,
            'optimization_report': optimization_report,
            'success': all(migration_results.values()) and not optimization_report['recommendations']
        }
        
        if result['success']:
            logger.info("Database optimization completed successfully!")
        else:
            logger.warning("Database optimization completed with issues. Check the report for details.")
        
        return result

def create_optimization_script():
    """Create a standalone script for database optimization."""
    script_content = '''
#!/usr/bin/env python3
"""Standalone database optimization script."""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.optimization_utils import DatabaseOptimizer
from src.config.unified_config import Config

def main():
    """Main optimization function."""
    config = Config()
    database_url = config.get_database_url()
    
    optimizer = DatabaseOptimizer(database_url)
    
    print("Starting database optimization...")
    result = optimizer.optimize_database()
    
    print("\nOptimization Results:")
    print(json.dumps(result, indent=2, default=str))
    
    if result['success']:
        print("\n✅ Database optimization completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️  Database optimization completed with issues.")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    return script_content