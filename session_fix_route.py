
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
            session['guide_id'] = 'ed833574-d3fb-4fe3-84c4-b805ee5b8a64'
            session['guide_filename'] = 'Department_of_Computer_Science2.docx'
            session['guide_uploaded'] = True
            session['last_grading_result'] = True
            
            # Set progress_id if available
            progress_id = '9f964c25-e4ac-4577-9ef3-f72c0a45e455' if '9f964c25-e4ac-4577-9ef3-f72c0a45e455' != 'None' else None
            if progress_id:
                session['last_grading_progress_id'] = progress_id
            
            session.modified = True
            
            logger.info(f"Session fixed with guide_id: {session.get('guide_id')}")
            logger.info(f"Progress ID set to: {session.get('last_grading_progress_id')}")
            
            flash('Session variables have been fixed. You can now access the results page.', 'success')
            return redirect(url_for('view_results'))
            
        except Exception as e:
            logger.error(f"Error fixing session: {str(e)}")
            flash(f'Error fixing session: {str(e)}', 'error')
            return redirect(url_for('dashboard'))
    
    @app.route("/check-session-status")
    def check_session_status():
        """Check current session status."""
        session_info = {
            'guide_id': session.get('guide_id'),
            'guide_filename': session.get('guide_filename'),
            'guide_uploaded': session.get('guide_uploaded'),
            'last_grading_result': session.get('last_grading_result'),
            'last_grading_progress_id': session.get('last_grading_progress_id'),
        }
        
        return jsonify({
            'session_variables': session_info,
            'session_valid': bool(session.get('guide_id')),
            'can_access_results': bool(session.get('guide_id') and session.get('last_grading_result'))
        })

if __name__ == "__main__":
    print("This is a module to be imported, not run directly.")
    print("Add this to your main app:")
    print("")
    print("from fix_results_session import add_session_fix_route")
    print("add_session_fix_route(app)")
    print("")
    print("Then visit: http://127.0.0.1:8501/fix-session")
