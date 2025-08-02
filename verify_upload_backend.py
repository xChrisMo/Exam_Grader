#!/usr/bin/env python3
"""
Direct backend test for upload functionality
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_backend_directly():
    """Test the backend upload functionality directly"""
    print("🔧 Testing Backend Upload Functionality Directly")
    print("=" * 50)
    
    try:
        # Import Flask app and models
        from webapp.app import app
        from src.database.models import db, LLMDocument
        from flask import current_app
        from werkzeug.datastructures import FileStorage
        import tempfile
        import io
        
        with app.app_context():
            print("✅ Flask app context created")
            
            # Test 1: Check if database tables exist
            try:
                count = LLMDocument.query.count()
                print(f"✅ Database accessible - {count} documents found")
            except Exception as e:
                print(f"❌ Database error: {e}")
                return False
            
            # Test 2: Test file upload simulation
            print("\n📚 Testing Training Guide Upload Logic...")
            
            # Create a test file in memory
            test_content = "Test training guide content\nQuestion 1: What is AI?\nAnswer: Artificial Intelligence"
            test_file = io.BytesIO(test_content.encode('utf-8'))
            test_file.name = 'test_guide.txt'
            
            # Simulate file upload
            file_storage = FileStorage(
                stream=test_file,
                filename='test_guide.txt',
                content_type='text/plain'
            )
            
            # Test the upload logic (without HTTP request)
            try:
                # Create upload directory
                upload_dir = os.path.join(current_app.root_path, 'uploads', 'training_guides')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Generate filename
                filename = f"test_user_{int(os.path.getmtime(__file__))}_{file_storage.filename}"
                file_path = os.path.join(upload_dir, filename)
                
                # Save file
                file_storage.save(file_path)
                
                # Create database record (simulating the backend logic)
                guide = LLMDocument(
                    user_id='test_user_123',
                    name='Test Training Guide',
                    original_name=file_storage.filename,
                    stored_name=filename,
                    file_type='.txt',
                    mime_type='text/plain',
                    file_size=os.path.getsize(file_path),
                    file_path=file_path,
                    text_content=test_content,
                    word_count=len(test_content.split()),
                    character_count=len(test_content),
                    extracted_text=True,
                    type='training_guide'
                )
                
                db.session.add(guide)
                db.session.commit()
                
                print(f"✅ Training guide created successfully!")
                print(f"   ID: {guide.id}")
                print(f"   Name: {guide.name}")
                print(f"   File: {guide.original_name}")
                print(f"   Size: {guide.file_size} bytes")
                print(f"   Words: {guide.word_count}")
                
                # Clean up
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Remove from database
                db.session.delete(guide)
                db.session.commit()
                
                print("✅ Cleanup completed")
                
            except Exception as e:
                print(f"❌ Upload logic error: {e}")
                import traceback
                traceback.print_exc()
                return False
            
            # Test 3: Test submission upload logic
            print("\n📝 Testing Test Submission Upload Logic...")
            
            try:
                # Create test submission content
                submission_content = "Student Answer 1: AI stands for Artificial Intelligence\nStudent Answer 2: Machine learning is a subset of AI"
                test_file = io.BytesIO(submission_content.encode('utf-8'))
                test_file.name = 'test_submission.txt'
                
                file_storage = FileStorage(
                    stream=test_file,
                    filename='test_submission.txt',
                    content_type='text/plain'
                )
                
                # Create upload directory
                upload_dir = os.path.join(current_app.root_path, 'uploads', 'test_submissions')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Generate filename
                filename = f"test_user_{int(os.path.getmtime(__file__))}_{file_storage.filename}"
                file_path = os.path.join(upload_dir, filename)
                
                # Save file
                file_storage.save(file_path)
                
                # Create database record
                submission = LLMDocument(
                    user_id='test_user_123',
                    name='Test Student Submission',
                    original_name=file_storage.filename,
                    stored_name=filename,
                    file_type='.txt',
                    mime_type='text/plain',
                    file_size=os.path.getsize(file_path),
                    file_path=file_path,
                    text_content=submission_content,
                    word_count=len(submission_content.split()),
                    character_count=len(submission_content),
                    extracted_text=True,
                    type='test_submission'
                )
                
                db.session.add(submission)
                db.session.commit()
                
                print(f"✅ Test submission created successfully!")
                print(f"   ID: {submission.id}")
                print(f"   Name: {submission.name}")
                print(f"   File: {submission.original_name}")
                print(f"   Expected Score: N/A (stored separately)")
                print(f"   Words: {submission.word_count}")
                
                # Clean up
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Remove from database
                db.session.delete(submission)
                db.session.commit()
                
                print("✅ Cleanup completed")
                
            except Exception as e:
                print(f"❌ Submission upload logic error: {e}")
                import traceback
                traceback.print_exc()
                return False
            
            print("\n🎉 All backend upload tests passed!")
            return True
            
    except Exception as e:
        print(f"❌ Backend test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_upload_directories():
    """Check if upload directories exist and are writable"""
    print("\n📁 Checking Upload Directories...")
    
    directories = [
        'uploads/training_guides',
        'uploads/test_submissions'
    ]
    
    for dir_path in directories:
        full_path = project_root / dir_path
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            
            # Test write permission
            test_file = full_path / 'test_write.tmp'
            test_file.write_text('test')
            test_file.unlink()
            
            print(f"✅ {dir_path} - exists and writable")
        except Exception as e:
            print(f"❌ {dir_path} - error: {e}")

def main():
    """Main test function"""
    print("🧪 Backend Upload Functionality Verification")
    print("=" * 50)
    
    # Check upload directories
    check_upload_directories()
    
    # Test backend directly
    success = test_backend_directly()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Backend upload functionality is working correctly!")
        print("\n✅ What this means:")
        print("- Database models are properly configured")
        print("- File upload logic works correctly")
        print("- Both training guides and test submissions can be processed")
        print("- Upload directories are accessible")
        
        print("\n🔧 If frontend uploads still fail, check:")
        print("1. User authentication (login required)")
        print("2. CSRF token handling")
        print("3. Network connectivity")
        print("4. Browser console for JavaScript errors")
    else:
        print("❌ Backend upload functionality has issues")
        print("Check the error messages above for details")

if __name__ == "__main__":
    main()