"""Database migration manager for the Exam Grader application."""

import logging
from pathlib import Path
from typing import Dict

from sqlalchemy import create_engine, inspect

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database migrations and schema updates."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)

    def migrate(self) -> bool:
        """Run all pending migrations."""
        try:
            logger.info("Starting database migration...")

            if isinstance(self.database_url, str) and self.database_url.startswith(
                "sqlite:///"
            ):
                db_path = self.database_url.replace("sqlite:///", "")
                db_dir = Path(db_path).parent
                db_dir.mkdir(parents=True, exist_ok=True)

                if not Path(db_path).exists():
                    Path(db_path).touch()
                    logger.info(f"Created database file: {db_path}")

            if self._is_migration_needed():
                logger.info("Migration needed, creating tables...")
                self._create_tables()
                logger.info("Migration completed successfully")
            else:
                logger.info("Database is up-to-date")

            return True

        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            return False

    def _is_migration_needed(self) -> bool:
        """Check if database migration is needed."""
        try:
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()

            required_tables = {
                "users",
                "marking_guides",
                "submissions",
                "mappings",
                "grading_results",
                "sessions",
            }

            missing_tables = required_tables - set(existing_tables)
            return len(missing_tables) > 0

        except Exception:
            return True

    def _create_tables(self):
        """Create all database tables."""
        try:
            # Import models to ensure they are registered with SQLAlchemy
            from .models import db

            inspector = inspect(self.engine)

            if self.engine.dialect.has_table(self.engine.connect(), "sessions"):
                db.metadata.tables["sessions"].drop(self.engine)
                logger.info("Dropped 'sessions' table to apply schema changes.")

            # Handle 'submissions' table migration more carefully
            if self.engine.dialect.has_table(self.engine.connect(), "submissions"):
                columns = inspector.get_columns("submissions")
                column_names = [col["name"] for col in columns]
                if "processed" not in column_names:
                    with self.engine.connect() as connection:
                        with connection.begin():
                            if self.engine.dialect.name == "sqlite":
                                connection.execute(
                                    db.text(
                                        "ALTER TABLE submissions ADD COLUMN processed BOOLEAN DEFAULT FALSE NOT NULL"
                                    )
                                )
                            elif self.engine.dialect.name == "postgresql":
                                connection.execute(
                                    db.text(
                                        "ALTER TABLE submissions ADD COLUMN processed BOOLEAN DEFAULT FALSE NOT NULL"
                                    )
                                )
                            logger.info(
                                "Added 'processed' column to 'submissions' table."
                            )
                else:
                    logger.info(
                        "'processed' column already exists in 'submissions' table. No alteration needed."
                    )
            else:
                logger.info("'submissions' table does not exist. It will be created.")

            # Create all tables that do not exist
            db.metadata.create_all(self.engine)

            # Verify tables were created
            created_tables = inspector.get_table_names()
            logger.info(f"Database tables created successfully: {created_tables}")

            return True

        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise

    def get_migration_status(self) -> Dict[str, any]:
        """Get current migration status."""
        try:
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()

            return {
                "database_url": self.database_url,
                "existing_tables": existing_tables,
                "migration_needed": self._is_migration_needed(),
                "engine_connected": True,
            }

        except Exception as e:
            return {
                "database_url": self.database_url,
                "existing_tables": [],
                "migration_needed": True,
                "engine_connected": False,
                "error": str(e),
            }
