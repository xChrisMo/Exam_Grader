#!/usr/bin/env python3
"""
Database Migration Utility for Exam Grader Application.

This script runs database migrations without resetting the database,
specifically to add the 'processed' column to the submissions table.

Usage:
    python migrate_db.py
"""

import os
import sys
import sqlite3
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv("instance/.env", override=True)
load_dotenv(".env", override=True)

def run_migration():
    """Run database migrations without resetting."""
    try:
        print("🔄 Starting database migration...")
        
        # Import Flask app to set up context
        from flask import Flask
        from src.config.unified_config import UnifiedConfig
        from src.database.models import db, Submission
        from src.database.migrations import MigrationManager
        
        # Create minimal Flask app
        app = Flask(__name__)
        config = UnifiedConfig()
        app.config.update(config.get_flask_config())
        
        # Initialize database
        db.init_app(app)
        
        with app.app_context():
            # Run the regular migration first to ensure tables exist
            # Convert SQLAlchemy URL object to string
            db_url = str(db.engine.url)
            migration_manager = MigrationManager(db_url)
            success = migration_manager.migrate()
            
            if success:
                print("✅ Initial database migration completed successfully!")
                
                # Now check if the processed column exists
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                
                # Make sure the submissions table exists
                if 'submissions' in inspector.get_table_names():
                    columns = inspector.get_columns('submissions')
                    column_names = [col['name'] for col in columns]
                    
                    if 'processed' not in column_names:
                        print("'processed' column not found. Adding it directly...")
                        # Connect to the database directly
                        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        
                        # Add the processed column
                        try:
                            cursor.execute("ALTER TABLE submissions ADD COLUMN processed BOOLEAN DEFAULT 0 NOT NULL")
                            conn.commit()
                            print("✅ Added 'processed' column to submissions table.")
                        except Exception as e:
                            print(f"❌ Error adding column: {str(e)}")
                            conn.rollback()
                        finally:
                            conn.close()
                    else:
                        print("'processed' column already exists.")
                else:
                    print("❌ The 'submissions' table does not exist. Creating it...")
                    # Create the submissions table
                    Submission.__table__.create(db.engine)
                    print("✅ Created 'submissions' table.")
                
                # Verify the processed column exists
                inspector = inspect(db.engine)
                if 'submissions' in inspector.get_table_names():
                    columns = inspector.get_columns('submissions')
                    column_names = [col['name'] for col in columns]
                    
                    if 'processed' in column_names:
                        print("✅ The 'processed' column has been added to the submissions table.")
                    else:
                        print("❌ The 'processed' column is still missing from the submissions table.")
                else:
                    print("❌ The 'submissions' table does not exist.")
            else:
                print("❌ Database migration failed.")
        
        return success
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point."""
    print("🗄️  EXAM GRADER DATABASE MIGRATION UTILITY")
    print("=" * 40)
    
    success = run_migration()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()