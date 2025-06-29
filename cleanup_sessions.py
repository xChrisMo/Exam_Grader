#!/usr/bin/env python3
"""
Script to clean up existing sessions that might be causing JSON parsing errors.
This will invalidate all existing sessions and allow users to log in fresh.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webapp.exam_grader_app import app
from src.database.models import Session, db
from utils.logger import logger

def cleanup_sessions():
    """Clean up all existing sessions."""
    try:
        with app.app_context():
            # Get all sessions
            sessions = Session.query.all()
            count = len(sessions)
            
            if count == 0:
                print("No sessions found to clean up.")
                return
            
            print(f"Found {count} sessions to clean up...")
            
            # Invalidate all sessions
            for session in sessions:
                session.invalidate()
            
            # Commit the changes
            db.session.commit()
            
            print(f"Successfully invalidated {count} sessions.")
            print("Users will need to log in again.")
            
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {str(e)}")
        print(f"Error: {str(e)}")
        db.session.rollback()

if __name__ == "__main__":
    print("Cleaning up existing sessions...")
    cleanup_sessions()
    print("Session cleanup completed.") 