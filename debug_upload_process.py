#!/usr/bin/env python3
"""
Debug script to trace the exact upload process and identify where it fails.
"""

import os
import sys
import uuid
from pathlib import Path
from werkzeug.datastructures import FileStorage
from io import BytesIO

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
from src.utils.validation_utils import ValidationUtils
from src.services.content_validation_service import ContentValidationService

def create_test_file():
    """Create a test PDF file in memory."""
    # Simple PDF content
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
    
    file_obj = BytesIO(pdf_content)
    file_storage = FileStorage(
        stream=file_obj,
        filename="test_submission.pdf",
        content_type="application/pdf"
    )
    return file_storage

def debug_upload_process():
    """Debug the complete upload process step by step."""
    
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
            
            with app.test_request_context():
                # Simulate a logged-in session
                session['user_id'] = str(user.id)
                current_user = get_current_user()
                print(f"✓ Current user authenticated: {current_user.username if current_user else None}")
                
                if not current_user:
                    print("✗ Authentication failed")
                    return
                
                # Step 1: Create test file with text content
                print("\n--- Step 1: Create Test File ---")
                try:
                    temp_dir = str(config.files.temp_dir)
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    # Use the test PDF with actual text content
                    test_filename = "test_submission_with_text.pdf"
                    source_path = os.path.join(temp_dir, "test_submission_with_text.pdf")
                    filename = f"submission_{uuid.uuid4().hex}_{test_filename}"
                    file_path = os.path.join(temp_dir, filename)
                    
                    # Copy the test file with text content
                    import shutil
                    shutil.copy2(source_path, file_path)
                    print(f"✓ Test file created: {file_path}")
                except Exception as e:
                    print(f"✗ Test file creation error: {str(e)}")
                    return
                
                # Step 2: Content validation
                print("\n--- Step 2: Content Validation ---")
                try:
                    content_validation_service = ContentValidationService()
                    file_extension = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
                    
                    validation_result = content_validation_service.validate_and_check_duplicates(
                        file_path, 
                        file_extension,
                        user_id=current_user.id,
                        check_type='submission',
                        marking_guide_id=None
                    )
                    
                    print(f"Content validation result: {validation_result}")
                    if not validation_result['success']:
                        print(f"✗ Content validation failed: {validation_result['error']}")
                        return
                    print("✓ Content validation passed")
                except Exception as e:
                    print(f"✗ Content validation error: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return
                
                # Step 3: Create submission object
                print("\n--- Step 3: Create Submission Object ---")
                try:
                    submission = Submission(
                        user_id=current_user.id,
                        student_name="Debug Test Student",
                        student_id="DEBUG001",
                        marking_guide_id=None,
                        filename=test_filename,
                        file_path=file_path,
                        file_size=validation_result['file_size'],
                        file_type=validation_result['file_type'],
                        content_text=validation_result['text_content'],
                        content_hash=validation_result['content_hash'],
                        answers={},
                        ocr_confidence=validation_result.get('confidence', 1.0),
                        processing_status="completed",
                        archived=False,
                    )
                    print("✓ Submission object created")
                except Exception as e:
                    print(f"✗ Submission object creation error: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return
                
                # Step 4: Save to database
                print("\n--- Step 4: Save to Database ---")
                try:
                    db.session.add(submission)
                    db.session.commit()
                    print(f"✓ Submission saved to database with ID: {submission.id}")
                    
                    # Verify it was saved
                    saved_submission = Submission.query.filter_by(id=submission.id).first()
                    if saved_submission:
                        print(f"✓ Submission verified in database: {saved_submission.filename}")
                        
                        # Clean up
                        db.session.delete(saved_submission)
                        db.session.commit()
                        print("✓ Test submission cleaned up")
                    else:
                        print("✗ Submission not found after save")
                        
                except Exception as e:
                    print(f"✗ Database save error: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    try:
                        db.session.rollback()
                    except:
                        pass
                    return
                
                # Clean up temp file
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print("✓ Temp file cleaned up")
                except Exception as e:
                    print(f"⚠ Temp file cleanup warning: {str(e)}")
                    
        except Exception as e:
            print(f"✗ Error during debug process: {str(e)}")
            import traceback
            traceback.print_exc()
            try:
                db.session.rollback()
            except:
                pass

if __name__ == "__main__":
    print("Debugging upload process step by step...")
    debug_upload_process()
    print("Debug completed.")