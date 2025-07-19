#!/usr/bin/env python3
"""
Test script to check authentication during upload process.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.config.unified_config import UnifiedConfig
from src.database import db, Submission, User
from flask import Flask, session
from webapp.auth import get_current_user

def test_upload_authentication():
    """Test authentication during upload process."""
    
    # Initialize Flask app
    app = Flask(__name__)
    
    # Load configuration
    config = UnifiedConfig()
    app.config.update(config.get_flask_config())
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "dev-key-123"
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        try:
            # Create tables if they don't exist
            db.create_all()
            print("✓ Database tables created/verified")
            
            # Get a user from database
            user = User.query.first()
            if not user:
                print("✗ No users found in database")
                return
                
            print(f"✓ Found user: {user.username} (ID: {user.id})")
            
            # Test without session (should fail)
            with app.test_request_context():
                current_user = get_current_user()
                print(f"✓ Current user without session: {current_user}")
                
            # Test with session (should work)
            with app.test_request_context():
                # Simulate a logged-in session
                session['user_id'] = str(user.id)
                current_user = get_current_user()
                print(f"✓ Current user with session: {current_user.username if current_user else None}")
                
                if current_user:
                    print(f"✓ Authentication working - User ID: {current_user.id}")
                    
                    # Test submission creation with authenticated user
                    test_submission = Submission(
                        user_id=current_user.id,
                        student_name="Test Student",
                        student_id="TEST001",
                        filename="test_file.pdf",
                        file_path="/temp/test_file.pdf",
                        file_size=1024,
                        file_type="application/pdf",
                        content_text="This is test content",
                        content_hash="test_hash_123",
                        answers={"question1": "answer1"},
                        ocr_confidence=0.95,
                        processing_status="completed",
                        archived=False
                    )
                    
                    db.session.add(test_submission)
                    db.session.commit()
                    print(f"✓ Test submission saved with authenticated user: {test_submission.id}")
                    
                    # Clean up
                    db.session.delete(test_submission)
                    db.session.commit()
                    print("✓ Test submission cleaned up")
                else:
                    print("✗ Authentication failed - no current user found")
                    
        except Exception as e:
            print(f"✗ Error during authentication test: {str(e)}")
            import traceback
            traceback.print_exc()
            try:
                db.session.rollback()
            except:
                pass

if __name__ == "__main__":
    print("Testing upload authentication...")
    test_upload_authentication()
    print("Test completed.")