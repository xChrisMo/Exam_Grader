import os
import sys
import os
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

logging.info("Starting data fix script...")

# Check if the database file exists
db_path = "instance/exam_grader.db"
if not os.path.exists(db_path):
    logging.error(f"Database file not found at {db_path}")
    sys.exit(1)

logging.info(f"Database file found at {db_path}")

try:
    # Connect to the database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()
    logging.info("Connected to database successfully")
    
    # Begin transaction
    conn.execute("BEGIN TRANSACTION")
    
    # 1. Fix submission processing_status: change 'success' to 'completed'
    cursor.execute(
        "UPDATE submissions SET processing_status = 'completed' WHERE processing_status = 'success'"
    )
    rows_updated = cursor.rowcount
    logging.info(f"Updated {rows_updated} submissions from 'success' to 'completed' status")
    
    # 2. Fix percentage values in grading results
    # First, get all grading results with score and max_score
    cursor.execute(
        "SELECT id, score, max_score FROM grading_results WHERE percentage = 0.0 AND max_score > 0"
    )
    results_to_fix = cursor.fetchall()
    
    fixed_count = 0
    for result in results_to_fix:
        result_id = result['id']
        score = result['score']
        max_score = result['max_score']
        
        # Calculate correct percentage
        if max_score > 0:
            percentage = (score / max_score) * 100
            cursor.execute(
                "UPDATE grading_results SET percentage = ? WHERE id = ?",
                (percentage, result_id)
            )
            fixed_count += 1
    
    logging.info(f"Fixed percentage values for {fixed_count} grading results")
    
    # 3. Update the updated_at timestamp for modified records
    current_time = datetime.utcnow().isoformat()
    cursor.execute(
        "UPDATE submissions SET updated_at = ? WHERE processing_status = 'completed'",
        (current_time,)
    )
    
    cursor.execute(
        "UPDATE grading_results SET updated_at = ? WHERE percentage > 0",
        (current_time,)
    )
    
    # Commit the transaction
    conn.commit()
    logging.info("Changes committed to database")
    
    # Verify the changes
    logging.info("\nVerifying changes:")
    
    # Check submission status
    cursor.execute(
        "SELECT processing_status, COUNT(*) as count FROM submissions GROUP BY processing_status"
    )
    status_counts = cursor.fetchall()
    logging.info("Submission processing status counts after fix:")
    for status in status_counts:
        logging.info(f"  - {status['processing_status']}: {status['count']}")
    
    # Check percentage values
    cursor.execute(
        "SELECT COUNT(*) as count FROM grading_results WHERE percentage > 0"
    )
    fixed_percentage_count = cursor.fetchone()["count"]
    logging.info(f"Grading results with percentage > 0: {fixed_percentage_count}")
    
    # Show some sample fixed results
    cursor.execute(
        """
        SELECT gr.id, s.filename, gr.score, gr.max_score, gr.percentage
        FROM grading_results gr
        JOIN submissions s ON gr.submission_id = s.id
        WHERE gr.percentage > 0
        LIMIT 5
        """
    )
    sample_results = cursor.fetchall()
    logging.info("\nSample fixed grading results:")
    for result in sample_results:
        logging.info(f"  - ID: {result['id'][:8]}... | Submission: {result['filename']} | Score: {result['score']}/{result['max_score']} | Percentage: {result['percentage']:.1f}%")

except Exception as e:
    conn.rollback()
    logging.error(f"Error: {str(e)}")
    logging.error("Changes rolled back due to error")
finally:
    if 'conn' in locals():
        conn.close()
        logging.info("Database connection closed")

logging.info("Data fix completed")