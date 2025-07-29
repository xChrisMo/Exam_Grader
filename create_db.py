#!/usr/bin/env python3
"""Simple script to create the database."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

print("Creating database...")

try:
    # Import Flask app to trigger initialization
    from webapp.app import app
    from src.database.models import db
    
    with app.app_context():
        print("Creating all tables...")
        db.create_all()
        print("✅ Database created successfully!")
        
        # Check if tables were created
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Created tables: {tables}")
        
except Exception as e:
    print(f"❌ Error creating database: {e}")
    import traceback
    traceback.print_exc()