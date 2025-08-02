"""Database schema migration utilities."""
from typing import Dict, List

import logging
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class SchemaMigration:
    """Represents a single database schema migration."""
    
    def __init__(self, version: str, description: str, up_sql: str, down_sql: str = None):
        self.version = version
        self.description = description
        self.up_sql = up_sql
        self.down_sql = down_sql
    
    def __str__(self):
        return f"Migration {self.version}: {self.description}"

class MigrationManager:
    """Enhanced migration manager with schema versioning."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.migrations = self._load_migrations()
    
    def _load_migrations(self):
        """Load all available migrations."""
        migrations = []
        
        # Migration 001: Add performance indexes
        migrations.append(SchemaMigration(
            version="001",
            description="Add performance indexes to existing tables",
            up_sql="""
            CREATE INDEX IF NOT EXISTS idx_user_active_login ON users(is_active, last_login);
            CREATE INDEX IF NOT EXISTS idx_user_created_active ON users(created_at, is_active);
            CREATE INDEX IF NOT EXISTS idx_guide_user_active ON marking_guides(user_id, is_active);
            CREATE INDEX IF NOT EXISTS idx_guide_created_active ON marking_guides(created_at, is_active);
            CREATE INDEX IF NOT EXISTS idx_guide_hash_size ON marking_guides(content_hash, file_size);
            CREATE INDEX IF NOT EXISTS idx_submission_hash_guide ON submissions(content_hash, marking_guide_id);
            CREATE INDEX IF NOT EXISTS idx_mapping_score ON mappings(match_score);
            CREATE INDEX IF NOT EXISTS idx_mapping_method ON mappings(mapping_method);
            CREATE INDEX IF NOT EXISTS idx_grading_progress_id ON grading_results(progress_id);
            CREATE INDEX IF NOT EXISTS idx_session_expires ON sessions(expires_at);
            CREATE INDEX IF NOT EXISTS idx_session_ip ON sessions(ip_address);
            """,
            down_sql="""
            DROP INDEX IF EXISTS idx_user_active_login;
            DROP INDEX IF EXISTS idx_user_created_active;
            DROP INDEX IF EXISTS idx_guide_user_active;
            DROP INDEX IF EXISTS idx_guide_created_active;
            DROP INDEX IF EXISTS idx_guide_hash_size;
            DROP INDEX IF EXISTS idx_submission_hash_guide;
            DROP INDEX IF EXISTS idx_mapping_score;
            DROP INDEX IF EXISTS idx_mapping_method;
            DROP INDEX IF EXISTS idx_grading_progress_id;
            DROP INDEX IF EXISTS idx_session_expires;
            DROP INDEX IF EXISTS idx_session_ip;
            """
        ))
        
        # Migration 002: Add foreign key constraints and validation
        migrations.append(SchemaMigration(
            version="002",
            description="Add foreign key constraints and data validation",
            up_sql="""
            -- Add new columns for enhanced security and validation
            ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at DATETIME DEFAULT CURRENT_TIMESTAMP;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE NOT NULL;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS two_factor_enabled BOOLEAN DEFAULT FALSE NOT NULL;
            
            -- Add check constraints for data validation
            -- Note: SQLite doesn't support adding check constraints to existing tables
            -- These would need to be applied during table recreation
            """,
            down_sql="""
            ALTER TABLE users DROP COLUMN IF EXISTS password_changed_at;
            ALTER TABLE users DROP COLUMN IF EXISTS email_verified;
            ALTER TABLE users DROP COLUMN IF EXISTS two_factor_enabled;
            """
        ))
        
        # Migration 003: Optimize timestamp indexes
        migrations.append(SchemaMigration(
            version="003",
            description="Add timestamp indexes for better query performance",
            up_sql="""
            CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
            CREATE INDEX IF NOT EXISTS idx_users_updated_at ON users(updated_at);
            CREATE INDEX IF NOT EXISTS idx_marking_guides_created_at ON marking_guides(created_at);
            CREATE INDEX IF NOT EXISTS idx_marking_guides_updated_at ON marking_guides(updated_at);
            CREATE INDEX IF NOT EXISTS idx_submissions_created_at ON submissions(created_at);
            CREATE INDEX IF NOT EXISTS idx_submissions_updated_at ON submissions(updated_at);
            CREATE INDEX IF NOT EXISTS idx_mappings_created_at ON mappings(created_at);
            CREATE INDEX IF NOT EXISTS idx_grading_results_created_at ON grading_results(created_at);
            CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);
            CREATE INDEX IF NOT EXISTS idx_grading_sessions_created_at ON grading_sessions(created_at);
            """,
            down_sql="""
            DROP INDEX IF EXISTS idx_users_created_at;
            DROP INDEX IF EXISTS idx_users_updated_at;
            DROP INDEX IF EXISTS idx_marking_guides_created_at;
            DROP INDEX IF EXISTS idx_marking_guides_updated_at;
            DROP INDEX IF EXISTS idx_submissions_created_at;
            DROP INDEX IF EXISTS idx_submissions_updated_at;
            DROP INDEX IF EXISTS idx_mappings_created_at;
            DROP INDEX IF EXISTS idx_grading_results_created_at;
            DROP INDEX IF EXISTS idx_sessions_created_at;
            DROP INDEX IF EXISTS idx_grading_sessions_created_at;
            """
        ))
        
        migrations.append(SchemaMigration(
            version="004",
            description="Add advanced composite indexes for complex query optimization",
            up_sql="""
            -- Advanced user indexes
            CREATE INDEX IF NOT EXISTS idx_user_email_verified_active ON users(email_verified, is_active);
            CREATE INDEX IF NOT EXISTS idx_user_locked_until_active ON users(locked_until, is_active);
            CREATE INDEX IF NOT EXISTS idx_user_password_changed ON users(password_changed_at, is_active);
            
            -- Advanced marking guide indexes
            CREATE INDEX IF NOT EXISTS idx_guide_file_type_size ON marking_guides(file_type, file_size);
            CREATE INDEX IF NOT EXISTS idx_guide_total_marks_active ON marking_guides(total_marks, is_active);
            CREATE INDEX IF NOT EXISTS idx_guide_questions_marks ON marking_guides(max_questions_to_answer, total_marks);
            
            -- Advanced submission indexes
            CREATE INDEX IF NOT EXISTS idx_submission_status_confidence ON submissions(processing_status, ocr_confidence);
            CREATE INDEX IF NOT EXISTS idx_submission_student_guide ON submissions(student_id, marking_guide_id);
            CREATE INDEX IF NOT EXISTS idx_submission_archived_processed ON submissions(archived, processed);
            
            -- Advanced mapping indexes
            CREATE INDEX IF NOT EXISTS idx_mapping_submission_question ON mappings(submission_id, guide_question_id);
            CREATE INDEX IF NOT EXISTS idx_mapping_score_method ON mappings(match_score, mapping_method);
            
            -- Advanced grading result indexes
            CREATE INDEX IF NOT EXISTS idx_grading_score_confidence ON grading_results(score, confidence);
            CREATE INDEX IF NOT EXISTS idx_grading_method_progress ON grading_results(grading_method, progress_id);
            CREATE INDEX IF NOT EXISTS idx_grading_percentage_method ON grading_results(percentage, grading_method);
            
            -- Advanced session indexes
            CREATE INDEX IF NOT EXISTS idx_session_user_active_expires ON sessions(user_id, is_active, expires_at);
            CREATE INDEX IF NOT EXISTS idx_session_ip_user_agent ON sessions(ip_address, user_agent);
            
            -- Advanced grading session indexes
            CREATE INDEX IF NOT EXISTS idx_grading_session_status_step ON grading_sessions(status, current_step);
            CREATE INDEX IF NOT EXISTS idx_grading_session_progress_status ON grading_sessions(progress_id, status);
            CREATE INDEX IF NOT EXISTS idx_grading_session_user_guide ON grading_sessions(user_id, marking_guide_id);
            CREATE INDEX IF NOT EXISTS idx_grading_session_questions_mapped ON grading_sessions(total_questions_mapped, total_questions_graded);
            """,
            down_sql="""
            DROP INDEX IF EXISTS idx_user_email_verified_active;
            DROP INDEX IF EXISTS idx_user_locked_until_active;
            DROP INDEX IF EXISTS idx_user_password_changed;
            DROP INDEX IF EXISTS idx_guide_file_type_size;
            DROP INDEX IF EXISTS idx_guide_total_marks_active;
            DROP INDEX IF EXISTS idx_guide_questions_marks;
            DROP INDEX IF EXISTS idx_submission_status_confidence;
            DROP INDEX IF EXISTS idx_submission_student_guide;
            DROP INDEX IF EXISTS idx_submission_archived_processed;
            DROP INDEX IF EXISTS idx_mapping_submission_question;
            DROP INDEX IF EXISTS idx_mapping_score_method;
            DROP INDEX IF EXISTS idx_grading_score_confidence;
            DROP INDEX IF EXISTS idx_grading_method_progress;
            DROP INDEX IF EXISTS idx_grading_percentage_method;
            DROP INDEX IF EXISTS idx_session_user_active_expires;
            DROP INDEX IF EXISTS idx_session_ip_user_agent;
            DROP INDEX IF EXISTS idx_grading_session_status_step;
            DROP INDEX IF EXISTS idx_grading_session_progress_status;
            DROP INDEX IF EXISTS idx_grading_session_user_guide;
            DROP INDEX IF EXISTS idx_grading_session_questions_mapped;
            """
        ))
        
        # Migration 005: Add data validation triggers and constraints
        migrations.append(SchemaMigration(
            version="005",
            description="Add data validation triggers and enhanced constraints",
            up_sql="""
            -- Create validation triggers for SQLite
            CREATE TRIGGER IF NOT EXISTS validate_user_email_format
            BEFORE INSERT ON users
            FOR EACH ROW
            WHEN NEW.email NOT LIKE '%@%.%'
            BEGIN
                SELECT RAISE(ABORT, 'Invalid email format');
            END;
            
            CREATE TRIGGER IF NOT EXISTS validate_user_email_format_update
            BEFORE UPDATE ON users
            FOR EACH ROW
            WHEN NEW.email NOT LIKE '%@%.%'
            BEGIN
                SELECT RAISE(ABORT, 'Invalid email format');
            END;
            
            CREATE TRIGGER IF NOT EXISTS validate_submission_status
            BEFORE INSERT ON submissions
            FOR EACH ROW
            WHEN NEW.processing_status NOT IN ('pending', 'processing', 'completed', 'failed')
            BEGIN
                SELECT RAISE(ABORT, 'Invalid processing status');
            END;
            
            CREATE TRIGGER IF NOT EXISTS validate_submission_status_update
            BEFORE UPDATE ON submissions
            FOR EACH ROW
            WHEN NEW.processing_status NOT IN ('pending', 'processing', 'completed', 'failed')
            BEGIN
                SELECT RAISE(ABORT, 'Invalid processing status');
            END;
            
            CREATE TRIGGER IF NOT EXISTS validate_grading_session_status
            BEFORE INSERT ON grading_sessions
            FOR EACH ROW
            WHEN NEW.status NOT IN ('not_started', 'in_progress', 'completed', 'failed')
            BEGIN
                SELECT RAISE(ABORT, 'Invalid grading session status');
            END;
            
            CREATE TRIGGER IF NOT EXISTS validate_grading_session_status_update
            BEFORE UPDATE ON grading_sessions
            FOR EACH ROW
            WHEN NEW.status NOT IN ('not_started', 'in_progress', 'completed', 'failed')
            BEGIN
                SELECT RAISE(ABORT, 'Invalid grading session status');
            END;
            
            CREATE TRIGGER IF NOT EXISTS validate_grading_session_step
            BEFORE INSERT ON grading_sessions
            FOR EACH ROW
            WHEN NEW.current_step NOT IN ('text_retrieval', 'mapping', 'grading', 'saving')
            BEGIN
                SELECT RAISE(ABORT, 'Invalid grading session step');
            END;
            
            CREATE TRIGGER IF NOT EXISTS validate_grading_session_step_update
            BEFORE UPDATE ON grading_sessions
            FOR EACH ROW
            WHEN NEW.current_step NOT IN ('text_retrieval', 'mapping', 'grading', 'saving')
            BEGIN
                SELECT RAISE(ABORT, 'Invalid grading session step');
            END;
            """,
            down_sql="""
            DROP TRIGGER IF EXISTS validate_user_email_format;
            DROP TRIGGER IF EXISTS validate_user_email_format_update;
            DROP TRIGGER IF EXISTS validate_submission_status;
            DROP TRIGGER IF EXISTS validate_submission_status_update;
            DROP TRIGGER IF EXISTS validate_grading_session_status;
            DROP TRIGGER IF EXISTS validate_grading_session_status_update;
            DROP TRIGGER IF EXISTS validate_grading_session_step;
            DROP TRIGGER IF EXISTS validate_grading_session_step_update;
            """
        ))
        
        # Migration 006: Add performance monitoring views
        migrations.append(SchemaMigration(
            version="006",
            description="Add performance monitoring views and statistics",
            up_sql="""
            -- Create view for user activity statistics
            CREATE VIEW IF NOT EXISTS user_activity_stats AS
            SELECT 
                u.id,
                u.username,
                u.email,
                u.is_active,
                u.last_login,
                COUNT(DISTINCT mg.id) as total_guides,
                COUNT(DISTINCT s.id) as total_submissions,
                COUNT(DISTINCT gs.id) as total_grading_sessions,
                MAX(mg.created_at) as last_guide_created,
                MAX(s.created_at) as last_submission_created
            FROM users u
            LEFT JOIN marking_guides mg ON u.id = mg.user_id
            LEFT JOIN submissions s ON u.id = s.user_id
            LEFT JOIN grading_sessions gs ON u.id = gs.user_id
            GROUP BY u.id, u.username, u.email, u.is_active, u.last_login;
            
            -- Create view for submission processing statistics
            CREATE VIEW IF NOT EXISTS submission_processing_stats AS
            SELECT 
                s.id,
                s.student_name,
                s.student_id,
                s.processing_status,
                s.ocr_confidence,
                s.created_at,
                mg.title as guide_title,
                COUNT(DISTINCT m.id) as total_mappings,
                COUNT(DISTINCT gr.id) as total_grading_results,
                AVG(gr.score) as average_score,
                AVG(gr.percentage) as average_percentage
            FROM submissions s
            LEFT JOIN marking_guides mg ON s.marking_guide_id = mg.id
            LEFT JOIN mappings m ON s.id = m.submission_id
            LEFT JOIN grading_results gr ON s.id = gr.submission_id
            GROUP BY s.id, s.student_name, s.student_id, s.processing_status, s.ocr_confidence, s.created_at, mg.title;
            
            -- Create view for grading session performance
            CREATE VIEW IF NOT EXISTS grading_session_performance AS
            SELECT 
                gs.id,
                gs.progress_id,
                gs.status,
                gs.current_step,
                gs.total_questions_mapped,
                gs.total_questions_graded,
                gs.processing_start_time,
                gs.processing_end_time,
                CASE 
                    WHEN gs.processing_end_time IS NOT NULL AND gs.processing_start_time IS NOT NULL
                    THEN (julianday(gs.processing_end_time) - julianday(gs.processing_start_time)) * 24 * 60
                    ELSE NULL
                END as processing_duration_minutes,
                u.username,
                mg.title as guide_title,
                s.student_name
            FROM grading_sessions gs
            LEFT JOIN users u ON gs.user_id = u.id
            LEFT JOIN marking_guides mg ON gs.marking_guide_id = mg.id
            LEFT JOIN submissions s ON gs.submission_id = s.id;
            """,
            down_sql="""
            DROP VIEW IF EXISTS user_activity_stats;
             DROP VIEW IF EXISTS submission_processing_stats;
             DROP VIEW IF EXISTS grading_session_performance;
             """
         ))
        
        return migrations
    
    def _ensure_migration_table(self):
        """Ensure the migration tracking table exists."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(10) PRIMARY KEY,
                        description TEXT NOT NULL,
                        applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.commit()
        except SQLAlchemyError as e:
            logger.error(f"Failed to create migration table: {e}")
            raise
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        try:
            self._ensure_migration_table()
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version FROM schema_migrations ORDER BY version"))
                return [row[0] for row in result]
        except SQLAlchemyError as e:
            logger.error(f"Failed to get applied migrations: {e}")
            return []
    
    def apply_migration(self, migration: SchemaMigration) -> bool:
        """Apply a single migration."""
        try:
            logger.info(f"Applying migration {migration.version}: {migration.description}")
            
            with self.engine.connect() as conn:
                with conn.begin():
                    # Execute migration SQL
                    for statement in migration.up_sql.split(';'):
                        statement = statement.strip()
                        if statement:
                            conn.execute(text(statement))
                    
                    # Record migration as applied
                    conn.execute(text("""
                        INSERT INTO schema_migrations (version, description, applied_at)
                        VALUES (:version, :description, :applied_at)
                    """), {
                        'version': migration.version,
                        'description': migration.description,
                        'applied_at': datetime.now(timezone.utc)
                    })
            
            logger.info(f"Successfully applied migration {migration.version}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to apply migration {migration.version}: {e}")
            return False
    
    def rollback_migration(self, migration: SchemaMigration) -> bool:
        """Rollback a single migration."""
        if not migration.down_sql:
            logger.warning(f"No rollback SQL defined for migration {migration.version}")
            return False
            
        try:
            logger.info(f"Rolling back migration {migration.version}: {migration.description}")
            
            with self.engine.connect() as conn:
                with conn.begin():
                    # Execute rollback SQL
                    for statement in migration.down_sql.split(';'):
                        statement = statement.strip()
                        if statement:
                            conn.execute(text(statement))
                    
                    # Remove migration record
                    conn.execute(text("""
                        DELETE FROM schema_migrations WHERE version = :version
                    """), {'version': migration.version})
            
            logger.info(f"Successfully rolled back migration {migration.version}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to rollback migration {migration.version}: {e}")
            return False
    
    def migrate_up(self, target_version: str = None) -> bool:
        """Apply all pending migrations up to target version."""
        try:
            applied_migrations = set(self.get_applied_migrations())
            pending_migrations = [
                m for m in self.migrations 
                if m.version not in applied_migrations and 
                (target_version is None or m.version <= target_version)
            ]
            
            if not pending_migrations:
                logger.info("No pending migrations to apply")
                return True
            
            logger.info(f"Applying {len(pending_migrations)} pending migrations")
            
            for migration in pending_migrations:
                if not self.apply_migration(migration):
                    logger.error(f"Migration failed at version {migration.version}")
                    return False
            
            logger.info("All migrations applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration process failed: {e}")
            return False
    
    def migrate_down(self, target_version: str) -> bool:
        """Rollback migrations down to target version."""
        try:
            applied_migrations = self.get_applied_migrations()
            migrations_to_rollback = [
                m for m in reversed(self.migrations)
                if m.version in applied_migrations and m.version > target_version
            ]
            
            if not migrations_to_rollback:
                logger.info("No migrations to rollback")
                return True
            
            logger.info(f"Rolling back {len(migrations_to_rollback)} migrations")
            
            for migration in migrations_to_rollback:
                if not self.rollback_migration(migration):
                    logger.error(f"Rollback failed at version {migration.version}")
                    return False
            
            logger.info("All rollbacks completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Rollback process failed: {e}")
            return False
    
    def get_migration_status(self) -> Dict[str, Dict]:
        """Get status of all migrations."""
        applied_migrations = set(self.get_applied_migrations())
        status = {}
        
        for migration in self.migrations:
            status[migration.version] = {
                'description': migration.description,
                'applied': migration.version in applied_migrations,
                'has_rollback': migration.down_sql is not None
            }
        
        return status