#!/usr/bin/env python3
"""Test script to verify unified database functionality."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variable to force absolute path
os.environ['DATABASE_URL'] = 'sqlite:///c:/Users/mezac/Documents/job/Exam_Grader/exam_grader.db'
os.environ['FORCE_DATABASE_URL'] = '1'

from src.config.unified_config import UnifiedConfig
from sqlalchemy import create_engine, text

def test_database():
    """Test database connectivity and data."""
    try:
        # Load configuration
        config = UnifiedConfig()
        # Force the unified database path
        unified_db_url = 'sqlite:///c:/Users/mezac/Documents/job/Exam_Grader/exam_grader.db'
        print(f"Using unified database URL: {unified_db_url}")
        
        # Create engine and test connection
        engine = create_engine(unified_db_url)
        
        with engine.connect() as conn:
            # Test basic connectivity
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            print(f"Tables found: {tables}")
            
            # Test user count
            if 'users' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                print(f"Users in database: {user_count}")
            
            # Test submissions count
            if 'submissions' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM submissions"))
                submission_count = result.scalar()
                print(f"Submissions in database: {submission_count}")
                
        print("✅ Database test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    test_database()