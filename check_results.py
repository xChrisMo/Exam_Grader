#!/usr/bin/env python
"""Simple script to check if there are any grading results in the database."""

import os
import sys
import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Path to the database file
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'exam_grader.db')
logging.info(f"Looking for database at: {db_path}")

# Check if the database file exists
if not os.path.exists(db_path):
    logging.error(f"Database file not found at: {db_path}")
    sys.exit(1)

logging.info(f"Database file found at: {db_path}")

# Main function to check for results using direct SQLite connection
def check_results():
    try:
        # Connect to the SQLite database
        logging.info("Connecting to database...")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        
        # Check if grading_results table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='grading_results'")
        if not cursor.fetchone():
            logging.warning("The grading_results table does not exist in the database.")
            return
        
        # Count total grading results
        cursor.execute("SELECT COUNT(*) FROM grading_results")
        total_results = cursor.fetchone()[0]
        logging.info(f"Total grading results in database: {total_results}")
        
        if total_results > 0:
            # Get the most recent results
            cursor.execute("""
                SELECT gr.*, s.filename as submission_filename, mg.title as guide_title 
                FROM grading_results gr
                LEFT JOIN submissions s ON gr.submission_id = s.id
                LEFT JOIN marking_guides mg ON gr.marking_guide_id = mg.id
                ORDER BY gr.created_at DESC LIMIT 5
            """)
            recent_results = cursor.fetchall()
            
            logging.info("\nMost recent grading results:")
            
            for result in recent_results:
                logging.info(f"\nID: {result['id']}")
                logging.info(f"Submission: {result['submission_filename'] if result['submission_filename'] else 'Unknown'}")
                logging.info(f"Guide: {result['guide_title'] if result['guide_title'] else 'Unknown'}")
                logging.info(f"Score: {result['score']}/{result['max_score']} ({result['percentage']:.1f}%)")
                logging.info(f"Created: {result['created_at']}")
        else:
            logging.info("No grading results found in the database.")
            
    except Exception as e:
        logging.error(f"Error checking results: {e}")
        import traceback
        logging.error(traceback.format_exc())
    finally:
        if 'conn' in locals():
            conn.close()

# Run the script
if __name__ == '__main__':
    check_results()