#!/usr/bin/env python3
"""
Database Reset Utility for Exam Grader Application.

This script completely resets the database by:
1. Removing the existing database file
2. Creating a new database with all tables
3. Creating the default admin user

Usage:
    python reset_database.py
    python reset_database.py --confirm
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv("instance/.env", override=True)

def reset_database(confirm: bool = False):
    """Reset the database completely."""
    
    if not confirm:
        print("⚠️  WARNING: This will completely delete the existing database!")
        print("   All users, submissions, and grading data will be lost.")
        response = input("   Are you sure you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Database reset cancelled.")
            return False
    
    try:
        print("🔄 Starting database reset...")
        
        # Get database URL from config
        database_url = os.getenv("DATABASE_URL", "sqlite:///exam_grader.db")
        
        # Handle SQLite database file
        if database_url.startswith('sqlite:///'):
            db_path = database_url.replace('sqlite:///', '')
            db_file = Path(db_path)
            
            if db_file.exists():
                db_file.unlink()
                print(f"✅ Removed existing database: {db_path}")
            else:
                print(f"ℹ️  Database file doesn't exist: {db_path}")
        
        # Import Flask app to trigger database initialization
        print("🔧 Creating new database...")
        
        # Set up minimal Flask app context for database operations
        from flask import Flask
        from src.config.unified_config import config
        from src.database import db, MigrationManager, DatabaseUtils
        
        # Create minimal Flask app
        app = Flask(__name__)
        app.config.update(config.get_flask_config())
        
        # Initialize database
        db.init_app(app)
        
        with app.app_context():
            # Drop all tables and indexes before creating to ensure a clean slate
            try:
                # First, try to drop all tables which should also drop associated indexes
                db.drop_all()
                print("✅ Dropped existing database tables and indexes (if any)")
            except Exception as e:
                print(f"⚠️  Warning during drop_all: {e}")
                # If drop_all fails, try to manually drop problematic indexes
                try:
                    from sqlalchemy import text
                    # Drop specific indexes that might cause conflicts
                    problematic_indexes = [
                        'idx_user_status',
                        'idx_submission_user_status',
                        'idx_grading_session_user_status',
                        'idx_submission_guide', 
                        'idx_progress_status',
                        'idx_user_created',
                        'idx_status_created',
                        'idx_guide_status'
                    ]
                    for index_name in problematic_indexes:
                        try:
                            db.session.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
                            print(f"✅ Dropped index: {index_name}")
                        except Exception as idx_e:
                            print(f"⚠️  Could not drop index {index_name}: {idx_e}")
                    db.session.commit()
                except Exception as cleanup_e:
                    print(f"⚠️  Warning during index cleanup: {cleanup_e}")
            
            # Create all tables with proper error handling
            try:
                db.create_all()
                print("✅ Database tables created")
            except Exception as create_e:
                print(f"❌ Error creating tables: {create_e}")
                # If creation fails due to existing indexes, try to handle it
                if "already exists" in str(create_e):
                    print("⚠️  Some indexes already exist, attempting to continue...")
                    # Try to create tables individually to isolate the problem
                    from src.database.models import User, MarkingGuide, Submission, Mapping, GradingResult, Session, GradingSession
                    models = [User, MarkingGuide, Submission, Mapping, GradingResult, Session, GradingSession]
                    for model in models:
                        try:
                            model.__table__.create(db.engine, checkfirst=True)
                            print(f"✅ Created table: {model.__tablename__}")
                        except Exception as model_e:
                            if "already exists" not in str(model_e):
                                print(f"❌ Error creating {model.__tablename__}: {model_e}")
                            else:
                                print(f"ℹ️  Table {model.__tablename__} already exists")
                else:
                    raise create_e
            
            # Verify tables exist
            from sqlalchemy import inspect
            engine = db.engine
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"✅ Tables created: {', '.join(tables)}")
            
            # Create default user
            if DatabaseUtils.create_default_user():
                print("✅ Default admin user created")
            else:
                print("⚠️  Warning: Failed to create default user")
        
        print("\n🎉 Database reset completed successfully!")
        print("\n" + "=" * 60)
        print("DATABASE RESET COMPLETE")
        print("=" * 60)
        print("The database has been completely reset.")
        print("You can now start the application with:")
        print("  python run_app.py")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Database reset failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def check_database_status():
    """Check current database status."""
    try:
        print("🔍 Checking database status...")
        
        database_url = os.getenv("DATABASE_URL", "sqlite:///exam_grader.db")
        print(f"Database URL: {database_url}")
        
        if database_url.startswith('sqlite:///'):
            db_path = database_url.replace('sqlite:///', '')
            db_file = Path(db_path)
            
            if db_file.exists():
                size_mb = db_file.stat().st_size / (1024 * 1024)
                print(f"✅ Database file exists: {db_path} ({size_mb:.2f} MB)")
                
                # Try to connect and check tables
                from sqlalchemy import create_engine, inspect
                engine = create_engine(database_url)
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                if tables:
                    print(f"✅ Tables found: {', '.join(tables)}")
                else:
                    print("⚠️  No tables found in database")
                    
            else:
                print(f"❌ Database file doesn't exist: {db_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking database: {str(e)}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Reset the Exam Grader database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python reset_database.py --status     # Check database status
  python reset_database.py             # Interactive reset
  python reset_database.py --confirm   # Reset without confirmation
        """
    )
    
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check database status only"
    )
    
    args = parser.parse_args()
    
    print("🗄️  EXAM GRADER DATABASE UTILITY")
    print("=" * 40)
    
    if args.status:
        success = check_database_status()
        sys.exit(0 if success else 1)
    else:
        success = reset_database(args.confirm)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
