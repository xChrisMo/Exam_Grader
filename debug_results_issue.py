#!/usr/bin/env python3
"""
Debug script to investigate the results page issue.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sqlite3
from datetime import datetime

def debug_results_issue():
    """Debug the results page issue by examining the database directly."""
    db_path = "instance/exam_grader.db"
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get the guide_id from the logs
        guide_id = "ccb78f40-a816-4990-b13c-8f1b18825b76"
        
        print(f"\n=== DEBUGGING RESULTS ISSUE ===")
        print(f"Guide ID: {guide_id}")
        
        # Count total grading results for this guide
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM grading_results 
            WHERE marking_guide_id = ?
        """, (guide_id,))
        total_results = cursor.fetchone()['count']
        print(f"Total grading results for guide: {total_results}")
        
        # Check how many have valid submissions
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM grading_results gr
            INNER JOIN submissions s ON gr.submission_id = s.id
            WHERE gr.marking_guide_id = ?
        """, (guide_id,))
        valid_submissions = cursor.fetchone()['count']
        print(f"Results with valid submissions: {valid_submissions}")
        
        # Check for orphaned results
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM grading_results gr
            LEFT JOIN submissions s ON gr.submission_id = s.id
            WHERE gr.marking_guide_id = ? AND s.id IS NULL
        """, (guide_id,))
        orphaned_results = cursor.fetchone()['count']
        print(f"Orphaned results (no submission): {orphaned_results}")
        
        # Get sample of results with submission details
        cursor.execute("""
            SELECT 
                gr.id as result_id,
                gr.submission_id,
                gr.score,
                gr.percentage,
                gr.created_at,
                s.filename,
                s.id as sub_id
            FROM grading_results gr
            LEFT JOIN submissions s ON gr.submission_id = s.id
            WHERE gr.marking_guide_id = ?
            ORDER BY gr.created_at DESC
            LIMIT 10
        """, (guide_id,))
        
        sample_results = cursor.fetchall()
        print(f"\nSample results (first 10):")
        for i, result in enumerate(sample_results, 1):
            print(f"  {i}. Result ID: {result['result_id']}")
            print(f"     Submission ID: {result['submission_id']}")
            print(f"     Submission exists: {'Yes' if result['sub_id'] else 'No'}")
            print(f"     Filename: {result['filename'] or 'N/A'}")
            print(f"     Score: {result['score']}%")
            print(f"     Created: {result['created_at']}")
            print()
        
        # Check if there are duplicate submission_ids
        cursor.execute("""
            SELECT submission_id, COUNT(*) as count
            FROM grading_results 
            WHERE marking_guide_id = ?
            GROUP BY submission_id
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 5
        """, (guide_id,))
        
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"Duplicate submission_ids found:")
            for dup in duplicates:
                print(f"  Submission ID: {dup['submission_id']} - {dup['count']} results")
        else:
            print("No duplicate submission_ids found")
        
        # Check unique submission_ids
        cursor.execute("""
            SELECT COUNT(DISTINCT submission_id) as unique_count
            FROM grading_results 
            WHERE marking_guide_id = ?
        """, (guide_id,))
        unique_submissions = cursor.fetchone()['unique_count']
        print(f"\nUnique submission_ids: {unique_submissions}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error debugging results: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_results_issue()