#!/usr/bin/env python
"""Fix script for results page session issues."""

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

def get_latest_guide_and_results():
    """Get the latest marking guide and its associated results."""
    db_path = "instance/exam_grader.db"
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get the most recent marking guide that has grading results
        cursor.execute("""
            SELECT DISTINCT 
                mg.id as guide_id,
                mg.title as guide_title,
                mg.filename as guide_filename,
                COUNT(gr.id) as result_count,
                MAX(gr.created_at) as latest_grading
            FROM marking_guides mg
            INNER JOIN grading_results gr ON mg.id = gr.marking_guide_id
            GROUP BY mg.id, mg.title, mg.filename
            ORDER BY latest_grading DESC
            LIMIT 1
        """)
        
        guide_info = cursor.fetchone()
        
        if not guide_info:
            logger.error("No marking guide with grading results found")
            return None, None
        
        logger.info(f"Found latest guide: {guide_info['guide_title']} (ID: {guide_info['guide_id']})")
        logger.info(f"Results count: {guide_info['result_count']}")
        logger.info(f"Latest grading: {guide_info['latest_grading']}")
        
        # Get the latest progress_id for this guide
        cursor.execute("""
            SELECT DISTINCT progress_id
            FROM grading_results
            WHERE marking_guide_id = ?
            AND progress_id IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
        """, (guide_info['guide_id'],))
        
        progress_result = cursor.fetchone()
        progress_id = progress_result['progress_id'] if progress_result else None
        
        logger.info(f"Latest progress_id: {progress_id}")
        
        conn.close()
        return guide_info, progress_id
        
    except Exception as e:
        logger.error(f"Error getting guide and results: {e}")
        return None, None

def create_session_fix_route():
    """Create a temporary route to fix session variables."""
    guide_info, progress_id = get_latest_guide_and_results()
    
    if not guide_info:
        logger.error("Cannot create session fix - no valid guide/results found")
        return False
    
    # Create a simple Flask route file
    fix_route_content = f'''
#!/usr/bin/env python
"""Temporary session fix route."""

from flask import Flask, session, redirect, url_for, flash, jsonify
import logging

logger = logging.getLogger(__name__)

def add_session_fix_route(app):
    """Add a temporary route to fix session variables."""
    
    @app.route("/fix-session")
    def fix_session():
        """Fix session variables for results page."""
        try:
            # Set the required session variables
            session['guide_id'] = '{guide_info['guide_id']}'
            session['guide_filename'] = '{guide_info['guide_filename']}'
            session['guide_uploaded'] = True
            session['last_grading_result'] = True
            
            # Set progress_id if available
            progress_id = '{progress_id}' if '{progress_id}' != 'None' else None
            if progress_id:
                session['last_grading_progress_id'] = progress_id
            
            session.modified = True
            
            logger.info(f"Session fixed with guide_id: {{session.get('guide_id')}}")
            logger.info(f"Progress ID set to: {{session.get('last_grading_progress_id')}}")
            
            flash('Session variables have been fixed. You can now access the results page.', 'success')
            return redirect(url_for('view_results'))
            
        except Exception as e:
            logger.error(f"Error fixing session: {{str(e)}}")
            flash(f'Error fixing session: {{str(e)}}', 'error')
            return redirect(url_for('dashboard'))
    
    @app.route("/check-session-status")
    def check_session_status():
        """Check current session status."""
        session_info = {{
            'guide_id': session.get('guide_id'),
            'guide_filename': session.get('guide_filename'),
            'guide_uploaded': session.get('guide_uploaded'),
            'last_grading_result': session.get('last_grading_result'),
            'last_grading_progress_id': session.get('last_grading_progress_id'),
        }}
        
        return jsonify({{
            'session_variables': session_info,
            'session_valid': bool(session.get('guide_id')),
            'can_access_results': bool(session.get('guide_id') and session.get('last_grading_result'))
        }})

if __name__ == "__main__":
    print("This is a module to be imported, not run directly.")
    print("Add this to your main app:")
    print("")
    print("from fix_results_session import add_session_fix_route")
    print("add_session_fix_route(app)")
    print("")
    print("Then visit: http://127.0.0.1:8501/fix-session")
'''
    
    with open('session_fix_route.py', 'w') as f:
        f.write(fix_route_content)
    
    logger.info("Created session_fix_route.py")
    return True

def create_manual_fix_instructions():
    """Create manual instructions for fixing the session."""
    guide_info, progress_id = get_latest_guide_and_results()
    
    if not guide_info:
        logger.error("Cannot create instructions - no valid guide/results found")
        return
    
    instructions = f'''
=== MANUAL SESSION FIX INSTRUCTIONS ===

1. Open your browser and go to: http://127.0.0.1:8501

2. Open browser developer tools (F12)

3. Go to the Console tab

4. Run this JavaScript code to fix the session:

fetch('/fix-session', {{
    method: 'GET',
    credentials: 'same-origin'
}})
.then(response => {{
    if (response.ok) {{
        console.log('Session fixed successfully');
        window.location.href = '/results';
    }} else {{
        console.error('Failed to fix session');
    }}
}})
.catch(error => {{
    console.error('Error:', error);
}});

5. Alternatively, you can:
   - Visit: http://127.0.0.1:8501/clear-session-guide
   - Re-upload your marking guide: {guide_info['guide_filename']}
   - Re-run the grading process

=== SESSION VARIABLES NEEDED ===
guide_id: {guide_info['guide_id']}
guide_filename: {guide_info['guide_filename']}
progress_id: {progress_id}

=== QUICK FIX URL ===
If the session fix route is added, visit:
http://127.0.0.1:8501/fix-session
'''
    
    with open('session_fix_instructions.txt', 'w') as f:
        f.write(instructions)
    
    logger.info("Created session_fix_instructions.txt")
    print(instructions)

def main():
    """Main function to fix session issues."""
    logger.info("Starting Session Fix for Results Page...")
    
    # Create the session fix route
    if create_session_fix_route():
        logger.info("✅ Session fix route created successfully")
    
    # Create manual instructions
    create_manual_fix_instructions()
    
    logger.info("\n=== NEXT STEPS ===")
    logger.info("1. The session fix route has been created")
    logger.info("2. Restart your Flask application")
    logger.info("3. Visit: http://127.0.0.1:8501/fix-session")
    logger.info("4. This should fix your session and redirect to results")
    
    logger.info("\nAlternatively, follow the manual instructions in session_fix_instructions.txt")

if __name__ == "__main__":
    main()