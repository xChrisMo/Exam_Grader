#!/usr/bin/env python3
"""
Database Initialization Script for Exam Grader
This script ensures the database is properly initialized on deployment platforms like Render.com
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def init_database():
    """Initialize the database with all required tables."""
    try:
        print("🔧 Initializing Exam Grader database...")
        
        # Import required modules
        from webapp.app import app
        from src.database.models import db
        from src.database.utils import DatabaseUtils
        
        with app.app_context():
            # Create all tables
            print("📊 Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Apply SQLite optimizations if using SQLite
            database_url = app.config.get('DATABASE_URL', 'sqlite:///exam_grader.db')
            if database_url.startswith('sqlite:///'):
                print("🔧 Applying SQLite optimizations...")
                from src.database.sqlite_optimizations import initialize_sqlite_optimizations
                if initialize_sqlite_optimizations(database_url):
                    print("✅ SQLite optimizations applied")
                else:
                    print("⚠️  Failed to apply SQLite optimizations")
            
            # Create default admin user
            print("👤 Creating default admin user...")
            if DatabaseUtils.create_default_user():
                print("✅ Default admin user created or already exists")
            else:
                print("⚠️  Failed to create default admin user")
            
            print("🎉 Database initialization completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
