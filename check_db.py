import os
import sys
import datetime

# Add the current directory to the path so Python can find the modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Create a log file
log_file = os.path.join(os.path.dirname(__file__), 'db_check_log.txt')
with open(log_file, 'w') as f:
    f.write(f"Check started at: {datetime.datetime.now()}\n")
    f.write(f"Python version: {sys.version}\n")
    f.write(f"Current directory: {os.getcwd()}\n")
    f.write("Importing modules...\n")

    try:
        # Import the app from exam_grader_app.py
        f.write("Importing app from webapp.exam_grader_app...\n")
        from webapp.exam_grader_app import app
        f.write("Successfully imported app\n")
        
        # Import the database models
        f.write("Importing database models...\n")
        from src.database.models import GradingResult, Submission
        f.write("Successfully imported models\n")

        # Use the app context to query the database
        with app.app_context():
            f.write("Inside app context\n")
            
            # Check for grading results
            try:
                results = GradingResult.query.all()
                f.write(f'Total grading results: {len(results)}\n')
                
                if results:
                    f.write("\nSample result:\n")
                    sample = results[0]
                    f.write(f"ID: {sample.id}\n")
                    f.write(f"Submission ID: {sample.submission_id}\n")
                    f.write(f"Progress ID: {sample.progress_id}\n")
                    f.write(f"Created at: {sample.created_at}\n")
                else:
                    f.write("\nNo grading results found in database.\n")
            except Exception as e:
                f.write(f"Error querying GradingResult: {str(e)}\n")
            
            # Check for submissions
            try:
                submissions = Submission.query.all()
                f.write(f'Total submissions: {len(submissions)}\n')
                
                if submissions:
                    f.write("\nSample submission:\n")
                    sample = submissions[0]
                    f.write(f"ID: {sample.id}\n")
                    f.write(f"Filename: {sample.filename}\n")
                    f.write(f"Processing status: {sample.processing_status}\n")
                else:
                    f.write("\nNo submissions found in database.\n")
            except Exception as e:
                f.write(f"Error querying Submission: {str(e)}\n")
                
    except Exception as e:
        f.write(f"Error: {str(e)}\n")
        import traceback
        f.write(traceback.format_exc())

print(f"Check completed. Results written to {log_file}")