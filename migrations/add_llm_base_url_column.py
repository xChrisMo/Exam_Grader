#!/usr/bin/env python3
"""
Add llm_base_url column to user_settings table.

This migration adds the llm_base_url column to the user_settings table
to support custom LLM API endpoints.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from sqlalchemy import text

# Load environment variables
load_dotenv("instance/.env", override=True)


def run_migration():
    """Add llm_base_url column to user_settings table."""
    
    try:
        print("🔄 Starting migration: Add llm_base_url column...")
        
        # Import Flask app and database
        from flask import Flask
        from src.config.unified_config import config
        from src.database import db
        
        # Create minimal Flask app
        app = Flask(__name__)
        app.config.update(config.get_flask_config())
        
        # Initialize database
        db.init_app(app)
        
        with app.app_context():
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user_settings')]
            
            if 'llm_base_url' in columns:
                print("✅ Column llm_base_url already exists in user_settings table")
                return True
            
            # Add the column
            print("🔧 Adding llm_base_url column to user_settings table...")
            
            # Use raw SQL to add the column
            db.session.execute(text(
                "ALTER TABLE user_settings ADD COLUMN llm_base_url VARCHAR(500)"
            ))
            db.session.commit()
            
            print("✅ Successfully added llm_base_url column")
            
            # Verify the column was added
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user_settings')]
            
            if 'llm_base_url' in columns:
                print("✅ Migration completed successfully")
                return True
            else:
                print("❌ Migration failed: Column not found after addition")
                return False
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    print("🗄️  EXAM GRADER DATABASE MIGRATION")
    print("=" * 40)
    print("Adding llm_base_url column to user_settings table")
    print("=" * 40)
    
    success = run_migration()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("The llm_base_url column has been added to the user_settings table.")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above.")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()