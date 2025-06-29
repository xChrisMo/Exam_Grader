#!/usr/bin/env python3
"""
Direct database cleanup script to remove all sessions.
This bypasses the Flask app to avoid session-related issues.
"""

import sys
import os
from sqlalchemy import create_engine, text

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def cleanup_sessions_direct():
    """Clean up all sessions directly from the database."""
    try:
        # Get database URL from environment or use default
        database_url = os.getenv('DATABASE_URL', 'sqlite:///instance/exam_grader.db')
        
        print(f"Connecting to database: {database_url}")
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if sessions table exists
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"))
            if not result.fetchone():
                print("Sessions table does not exist. Nothing to clean up.")
                return
            
            # Count existing sessions
            result = conn.execute(text("SELECT COUNT(*) FROM sessions"))
            count = result.fetchone()[0]
            
            if count == 0:
                print("No sessions found to clean up.")
                return
            
            print(f"Found {count} sessions to clean up...")
            
            # Delete all sessions
            conn.execute(text("DELETE FROM sessions"))
            conn.commit()
            
            print(f"Successfully deleted {count} sessions.")
            print("Users will need to log in again.")
            
    except Exception as e:
        print(f"Error cleaning up sessions: {str(e)}")

if __name__ == "__main__":
    print("Cleaning up existing sessions directly from database...")
    cleanup_sessions_direct()
    print("Session cleanup completed.") 