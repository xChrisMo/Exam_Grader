#!/usr/bin/env python
"""Diagnostic script to identify and fix results page issues."""

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

logger = logging.getLogger(__name__)

def check_database_connection():
    """Check if database is accessible and has required tables."""
    db_path = "instance/exam_grader.db"
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check required tables
        required_tables = ['grading_results', 'marking_guides', 'submissions', 'users']
        for table in required_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                logger.error(f"Required table '{table}' not found")
                return False
            else:
                logger.info(f"Table '{table}' exists")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return False

def check_grading_results():
    """Check if there are grading results and their associated data."""
    db_path = "instance/exam_grader.db"
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Count grading results
        cursor.execute("SELECT COUNT(*) as count FROM grading_results")
        total_results = cursor.fetchone()['count']
        logger.info(f"Total grading results: {total_results}")
        
        if total_results == 0:
            logger.warning("No grading results found in database")
            return False
        
        # Check for orphaned results (results without valid submissions or guides)
        cursor.execute("""
            SELECT COUNT(*) as count FROM grading_results gr
            LEFT JOIN submissions s ON gr.submission_id = s.id
            LEFT JOIN marking_guides mg ON gr.marking_guide_id = mg.id
            WHERE s.id IS NULL OR mg.id IS NULL
        """)
        orphaned_count = cursor.fetchone()['count']
        
        if orphaned_count > 0:
            logger.warning(f"Found {orphaned_count} orphaned grading results")
        
        # Get sample of recent results with details
        cursor.execute("""
            SELECT 
                gr.id,
                gr.submission_id,
                gr.marking_guide_id,
                gr.score,
                gr.percentage,
                gr.created_at,
                s.filename as submission_filename,
                mg.title as guide_title
            FROM grading_results gr
            LEFT JOIN submissions s ON gr.submission_id = s.id
            LEFT JOIN marking_guides mg ON gr.marking_guide_id = mg.id
            ORDER BY gr.created_at DESC
            LIMIT 3
        """)
        
        recent_results = cursor.fetchall()
        logger.info("Recent grading results:")
        for result in recent_results:
            logger.info(f"  ID: {result['id']}")
            logger.info(f"  Submission: {result['submission_filename']}")
            logger.info(f"  Guide: {result['guide_title']}")
            logger.info(f"  Score: {result['score']}/{result['percentage']}%")
            logger.info(f"  Created: {result['created_at']}")
            logger.info("  ---")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error checking grading results: {e}")
        return False

def check_marking_guides():
    """Check available marking guides."""
    db_path = "instance/exam_grader.db"
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM marking_guides")
        total_guides = cursor.fetchone()['count']
        logger.info(f"Total marking guides: {total_guides}")
        
        if total_guides == 0:
            logger.warning("No marking guides found")
            return False
        
        # Get recent guides
        cursor.execute("""
            SELECT id, title, filename, created_at
            FROM marking_guides
            ORDER BY created_at DESC
            LIMIT 3
        """)
        
        recent_guides = cursor.fetchall()
        logger.info("Recent marking guides:")
        for guide in recent_guides:
            logger.info(f"  ID: {guide['id']}")
            logger.info(f"  Title: {guide['title']}")
            logger.info(f"  Filename: {guide['filename']}")
            logger.info(f"  Created: {guide['created_at']}")
            logger.info("  ---")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error checking marking guides: {e}")
        return False

def suggest_fixes():
    """Suggest potential fixes for the results page issue."""
    logger.info("\n=== SUGGESTED FIXES ===")
    
    logger.info("1. If you're getting 'Error loading results' message:")
    logger.info("   - Check if you have a valid session with guide_id set")
    logger.info("   - Try logging out and logging back in")
    logger.info("   - Clear browser cache and cookies")
    
    logger.info("\n2. If no results are showing but grading was completed:")
    logger.info("   - Check if the session variables are properly set")
    logger.info("   - Verify the guide_id in session matches a guide in database")
    logger.info("   - Check if last_grading_progress_id is set in session")
    
    logger.info("\n3. Database issues:")
    logger.info("   - Run: python migrate_db.py")
    logger.info("   - Check database permissions")
    logger.info("   - Verify database file is not corrupted")
    
    logger.info("\n4. Session issues:")
    logger.info("   - Visit /clear-session-guide to reset session")
    logger.info("   - Re-upload marking guide")
    logger.info("   - Re-run grading process")

def main():
    """Main diagnostic function."""
    logger.info("Starting Results Page Diagnostic...")
    logger.info(f"Current directory: {os.getcwd()}")
    
    # Check database connection
    logger.info("\n=== CHECKING DATABASE ===")
    db_ok = check_database_connection()
    
    if not db_ok:
        logger.error("Database issues detected. Fix database first.")
        return
    
    # Check grading results
    logger.info("\n=== CHECKING GRADING RESULTS ===")
    results_ok = check_grading_results()
    
    # Check marking guides
    logger.info("\n=== CHECKING MARKING GUIDES ===")
    guides_ok = check_marking_guides()
    
    # Provide suggestions
    suggest_fixes()
    
    # Summary
    logger.info("\n=== DIAGNOSTIC SUMMARY ===")
    logger.info(f"Database: {'✅ OK' if db_ok else '❌ ISSUES'}")
    logger.info(f"Grading Results: {'✅ OK' if results_ok else '❌ ISSUES'}")
    logger.info(f"Marking Guides: {'✅ OK' if guides_ok else '❌ ISSUES'}")
    
    if db_ok and results_ok and guides_ok:
        logger.info("\n✅ Database appears healthy. Issue is likely session-related.")
        logger.info("Try accessing: http://127.0.0.1:8501/clear-session-guide")
        logger.info("Then re-upload your guide and run grading again.")
    else:
        logger.info("\n❌ Issues detected. Address the problems above.")

if __name__ == "__main__":
    main()