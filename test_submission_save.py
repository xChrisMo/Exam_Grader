#!/usr/bin/env python3
"""
Test script to check if submissions can be saved to the database.
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
from flask import Flask

def test_submission_save():
    """Test saving a submission to the database."""
    
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
            
            # Check if we have any users
            user_count = User.query.count()
            print(f"✓ Found {user_count} users in database")
            
            if user_count == 0:
                print("⚠ No users found - creating test user")
                test_user = User(username="testuser", email="test@example.com")
                test_user.set_password("password123")
                db.session.add(test_user)
                db.session.commit()
                print("✓ Test user created")
            
            # Get the first user
            user = User.query.first()
            print(f"✓ Using user: {user.username} (ID: {user.id})")
            
            # Try to create a test submission
            test_submission = Submission(
                user_id=user.id,
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
            
            print("✓ Test submission object created")
            
            # Try to save to database
            db.session.add(test_submission)
            db.session.commit()
            
            print(f"✓ Test submission saved successfully with ID: {test_submission.id}")
            
            # Verify it was saved
            saved_submission = Submission.query.filter_by(id=test_submission.id).first()
            if saved_submission:
                print(f"✓ Submission verified in database: {saved_submission.filename}")
            else:
                print("✗ Submission not found after save")
                
            # Clean up - delete the test submission
            db.session.delete(test_submission)
            db.session.commit()
            print("✓ Test submission cleaned up")
            
        except Exception as e:
            print(f"✗ Error during submission save test: {str(e)}")
            import traceback
            traceback.print_exc()
            try:
                db.session.rollback()
            except:
                pass

if __name__ == "__main__":
    print("Testing submission save to database...")
    test_submission_save()
    print("Test completed.")