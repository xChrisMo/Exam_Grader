import os
import sys
import datetime

# Add the current directory to the path so Python can find the modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Create a log file
log_file = os.path.join(os.path.dirname(__file__), 'session_check_log.txt')
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

        # Create a test route to check session variables
        @app.route('/check-session')
        def check_session():
            from flask import session, jsonify
            
            # Get session variables
            last_progress_id = session.get("last_grading_progress_id")
            last_grading_result = session.get('last_grading_result')
            guide_id = session.get('guide_id')
            
            # Return as JSON
            return jsonify({
                'last_grading_progress_id': last_progress_id,
                'last_grading_result': last_grading_result,
                'guide_id': guide_id,
                'all_session_keys': list(session.keys())
            })
        
        f.write("Added check-session route to the app\n")
        f.write("Run the app with: python run_app.py\n")
        f.write("Then visit: http://127.0.0.1:8501/check-session\n")
                
    except Exception as e:
        f.write(f"Error: {str(e)}\n")
        import traceback
        f.write(traceback.format_exc())

print(f"Check completed. Results written to {log_file}")
print("Run the app with: python run_app.py")
print("Then visit: http://127.0.0.1:8501/check-session")