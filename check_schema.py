#!/usr/bin/env python3

import os
import sys
import sqlite3
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Database path
db_path = 'instance/exam_grader.db'

def check_schema():
    """Check the database schema for the submissions table."""
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table info for submissions table
        cursor.execute('PRAGMA table_info(submissions)')
        columns = cursor.fetchall()
        
        print(f"\nSubmissions table columns in {db_path}:\n")
        for col in columns:
            print(col)
            
        # Check if 'archived' column exists
        archived_column = next((col for col in columns if col[1] == 'archived'), None)
        if archived_column:
            print(f"\nARCHIVED column found: {archived_column}")
            print(f"Column index: {archived_column[0]}")
            print(f"Column name: {archived_column[1]}")
            print(f"Data type: {archived_column[2]}")
            print(f"Nullable: {archived_column[3]}")
            print(f"Default value: {archived_column[4]}")
            print(f"Primary key: {archived_column[5]}")
        else:
            print("\nARCHIVED column NOT found in submissions table")
        
        conn.close()
        return True
    except Exception as e:
        print(f"Error checking schema: {str(e)}")
        return False

if __name__ == "__main__":
    check_schema()