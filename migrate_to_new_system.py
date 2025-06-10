#!/usr/bin/env python3
"""
Migration Script for Exam Grader Application.

This script migrates the application from the old session-based storage
system to the new database-backed system with enhanced security features.
"""

import argparse
import json
import os
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from flask import Flask

    from src.config.unified_config import config
    from src.database import DatabaseUtils, MigrationManager, db
    from src.security.secrets_manager import initialize_secrets, secrets_manager
    from utils.logger import logger
except ImportError as e:
    print(f"❌ Failed to import required modules: {e}")
    print("   Make sure all dependencies are installed")
    sys.exit(1)


class MigrationTool:
    """Tool for migrating from old system to new system."""

    def __init__(self):
        """Initialize migration tool."""
        self.app = None
        self.backup_dir = Path("migration_backup")
        self.backup_dir.mkdir(exist_ok=True)

    def setup_flask_app(self):
        """Setup Flask application for database operations."""
        self.app = Flask(__name__)
        self.app.config.update(config.get_flask_config())

        with self.app.app_context():
            db.init_app(self.app)

            # Create all database tables directly
            db.create_all()

            # Create default user
            DatabaseUtils.create_default_user()

    def backup_old_config(self):
        """Backup old configuration files."""
        print("📦 Backing up old configuration files...")

        old_config_files = ["config.py", "src/config/config_manager.py"]

        for config_file in old_config_files:
            if Path(config_file).exists():
                backup_path = self.backup_dir / f"{Path(config_file).name}.backup"
                import shutil

                shutil.copy2(config_file, backup_path)
                print(f"   ✅ Backed up {config_file} to {backup_path}")

    def migrate_environment_variables(self):
        """Migrate environment variables to secrets manager."""
        print("🔐 Migrating environment variables to secure storage...")

        # Common environment variables to migrate
        env_vars_to_migrate = [
            "HANDWRITING_OCR_API_KEY",
            "DEEPSEEK_API_KEY",
            "SECRET_KEY",
            "DATABASE_URL",
        ]

        migrated_count = 0
        for var_name in env_vars_to_migrate:
            value = os.getenv(var_name)
            if value:
                if secrets_manager.set_secret(
                    var_name, value, f"Migrated from environment variable"
                ):
                    print(f"   ✅ Migrated {var_name}")
                    migrated_count += 1
                else:
                    print(f"   ❌ Failed to migrate {var_name}")

        print(f"   📊 Migrated {migrated_count} environment variables")
        return migrated_count

    def migrate_session_files(self, session_dir: str = "flask_session"):
        """Migrate Flask session files to database."""
        print("💾 Migrating session data to database...")

        session_path = Path(session_dir)
        if not session_path.exists():
            print(f"   ℹ️  No session directory found at {session_path}")
            return 0

        migrated_count = 0

        # Get default user for migration
        with self.app.app_context():
            from src.database.models import User

            default_user = User.query.filter_by(username="admin").first()
            if not default_user:
                print("   ❌ No default user found for migration")
                return 0

            # Process session files
            for session_file in session_path.glob("*"):
                if session_file.is_file():
                    try:
                        # Try to load session data
                        session_data = self._load_session_file(session_file)
                        if session_data:
                            # Migrate to database
                            if DatabaseUtils.migrate_session_data_to_db(
                                session_data, default_user.id
                            ):
                                migrated_count += 1
                                print(
                                    f"   ✅ Migrated session file: {session_file.name}"
                                )
                            else:
                                print(
                                    f"   ❌ Failed to migrate session file: {session_file.name}"
                                )

                    except Exception as e:
                        print(
                            f"   ⚠️  Error processing session file {session_file.name}: {str(e)}"
                        )

        print(f"   📊 Migrated {migrated_count} session files")
        return migrated_count

    def _load_session_file(self, session_file: Path) -> Optional[Dict[str, Any]]:
        """Load session data from file."""
        try:
            # Try different session formats
            with open(session_file, "rb") as f:
                # Try pickle format first
                try:
                    return pickle.load(f)
                except:
                    pass

                # Try JSON format
                f.seek(0)
                try:
                    content = f.read().decode("utf-8")
                    return json.loads(content)
                except:
                    pass

            return None

        except Exception as e:
            logger.warning(f"Failed to load session file {session_file}: {str(e)}")
            return None

    def migrate_storage_files(self):
        """Migrate old storage files to new system."""
        print("📁 Migrating storage files...")

        # Old storage directories
        old_storage_dirs = ["temp", "output", "uploads", "storage"]

        migrated_files = 0

        for storage_dir in old_storage_dirs:
            storage_path = Path(storage_dir)
            if storage_path.exists():
                # Create backup
                backup_path = self.backup_dir / f"{storage_dir}_backup"
                if not backup_path.exists():
                    import shutil

                    shutil.copytree(storage_path, backup_path)
                    print(f"   ✅ Backed up {storage_dir} to {backup_path}")

                # Count files for reporting
                file_count = len(list(storage_path.rglob("*")))
                migrated_files += file_count

        print(f"   📊 Backed up {migrated_files} storage files")
        return migrated_files

    def update_configuration_files(self):
        """Update configuration files to use new system."""
        print("⚙️  Updating configuration files...")

        # Create new environment file template
        env_template = """# Exam Grader Environment Configuration
# Generated by migration script

# Database Configuration
DATABASE_URL=sqlite:///exam_grader.db

# Security Configuration
SECRET_KEY=your-secret-key-here
SESSION_TIMEOUT=3600

# API Keys (will be migrated to secure storage)
HANDWRITING_OCR_API_KEY=your-ocr-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key

# File Configuration
MAX_FILE_SIZE_MB=20
TEMP_DIR=temp
OUTPUT_DIR=output
UPLOAD_DIR=uploads

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=exam_grader.log

# Cache Configuration
CACHE_TYPE=simple
CACHE_DEFAULT_TIMEOUT=3600

# Environment
FLASK_ENV=production
"""

        env_file = Path(".env.example.new")
        with open(env_file, "w") as f:
            f.write(env_template)

        print(f"   ✅ Created new environment template: {env_file}")

        # Create migration completion marker
        marker_file = Path(".migration_completed")
        with open(marker_file, "w") as f:
            json.dump(
                {
                    "migration_date": datetime.now().isoformat(),
                    "migration_version": "2.0.0",
                    "migrated_by": "migration_script",
                },
                f,
                indent=2,
            )

        print(f"   ✅ Created migration marker: {marker_file}")

    def verify_migration(self):
        """Verify that migration was successful."""
        print("🔍 Verifying migration...")

        verification_results = {
            "database_tables": False,
            "default_user": False,
            "secrets_manager": False,
            "configuration": False,
        }

        try:
            with self.app.app_context():
                # Check database tables
                from sqlalchemy import inspect

                inspector = inspect(db.engine)
                expected_tables = {
                    "users",
                    "marking_guides",
                    "submissions",
                    "mappings",
                    "grading_results",
                    "sessions",
                }
                actual_tables = set(inspector.get_table_names())
                verification_results["database_tables"] = expected_tables.issubset(
                    actual_tables
                )

                # Check default user
                from src.database.models import User

                default_user = User.query.filter_by(username="admin").first()
                verification_results["default_user"] = default_user is not None

                # Check secrets manager
                verification_results["secrets_manager"] = (
                    len(secrets_manager.list_secrets()) > 0
                )

                # Check configuration
                verification_results["configuration"] = config.environment is not None

        except Exception as e:
            print(f"   ❌ Verification error: {str(e)}")

        # Report results
        all_passed = all(verification_results.values())

        for check, passed in verification_results.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check.replace('_', ' ').title()}")

        if all_passed:
            print("   🎉 Migration verification passed!")
        else:
            print("   ⚠️  Some verification checks failed")

        return all_passed

    def run_migration(
        self, migrate_sessions: bool = True, migrate_env_vars: bool = True
    ):
        """Run complete migration process."""
        print("🚀 Starting Exam Grader migration to new system...")
        print("=" * 60)

        try:
            # Setup Flask app
            self.setup_flask_app()

            # Initialize secrets manager
            initialize_secrets()

            # Backup old files
            self.backup_old_config()

            # Migrate environment variables
            if migrate_env_vars:
                self.migrate_environment_variables()

            # Migrate session data
            if migrate_sessions:
                self.migrate_session_files()

            # Migrate storage files
            self.migrate_storage_files()

            # Update configuration
            self.update_configuration_files()

            # Verify migration
            success = self.verify_migration()

            print("=" * 60)
            if success:
                print("🎉 Migration completed successfully!")
                print("\nNext steps:")
                print("1. Review the new .env.example.new file")
                print("2. Update your environment variables")
                print("3. Test the application with the new system")
                print("4. Remove old configuration files if everything works")
            else:
                print("⚠️  Migration completed with warnings")
                print("Please review the verification results above")

            return success

        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            logger.error(f"Migration failed: {str(e)}")
            return False


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(
        description="Migrate Exam Grader to new database-backed system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_to_new_system.py                    # Full migration
  python migrate_to_new_system.py --no-sessions     # Skip session migration
  python migrate_to_new_system.py --no-env-vars     # Skip environment variable migration
        """,
    )

    parser.add_argument(
        "--no-sessions", action="store_true", help="Skip session data migration"
    )

    parser.add_argument(
        "--no-env-vars", action="store_true", help="Skip environment variable migration"
    )

    parser.add_argument(
        "--backup-dir", default="migration_backup", help="Directory for backup files"
    )

    args = parser.parse_args()

    # Create migration tool
    migration_tool = MigrationTool()
    migration_tool.backup_dir = Path(args.backup_dir)
    migration_tool.backup_dir.mkdir(exist_ok=True)

    # Run migration
    success = migration_tool.run_migration(
        migrate_sessions=not args.no_sessions, migrate_env_vars=not args.no_env_vars
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
