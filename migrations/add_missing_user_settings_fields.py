#!/usr/bin/env python3
"""
Add missing fields to user_settings table.

This migration adds the missing fields that are shown in the settings page
but not properly stored in the database.
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
    """Add missing fields to user_settings table."""
    
    try:
        print("🔄 Starting migration: Add missing user settings fields...")
        
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
            # Check existing columns
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('user_settings')]
            print(f"✅ Existing columns: {', '.join(existing_columns)}")
            
            # Fields to add
            fields_to_add = [
                ('notification_level', 'VARCHAR(20) DEFAULT "info"'),
                ('auto_save', 'BOOLEAN DEFAULT 0'),
                ('show_tooltips', 'BOOLEAN DEFAULT 1'),
                ('results_per_page', 'INTEGER DEFAULT 10')
            ]
            
            added_fields = []
            
            for field_name, field_definition in fields_to_add:
                if field_name not in existing_columns:
                    print(f"🔧 Adding {field_name} column...")
                    
                    try:
                        db.session.execute(text(
                            f"ALTER TABLE user_settings ADD COLUMN {field_name} {field_definition}"
                        ))
                        db.session.commit()
                        added_fields.append(field_name)
                        print(f"✅ Added {field_name} column")
                    except Exception as e:
                        print(f"❌ Failed to add {field_name}: {e}")
                        db.session.rollback()
                else:
                    print(f"ℹ️  Column {field_name} already exists")
            
            if added_fields:
                print(f"\n✅ Successfully added {len(added_fields)} fields: {', '.join(added_fields)}")
            else:
                print("\n✅ All fields already exist")
            
            # Verify all fields exist
            inspector = db.inspect(db.engine)
            final_columns = [col['name'] for col in inspector.get_columns('user_settings')]
            
            missing_fields = []
            for field_name, _ in fields_to_add:
                if field_name not in final_columns:
                    missing_fields.append(field_name)
            
            if missing_fields:
                print(f"❌ Still missing fields: {', '.join(missing_fields)}")
                return False
            else:
                print("✅ All required fields are present")
                return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    print("🗄️  EXAM GRADER DATABASE MIGRATION")
    print("=" * 40)
    print("Adding missing user settings fields")
    print("=" * 40)
    
    success = run_migration()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("All user settings fields have been added to the database.")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above.")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()