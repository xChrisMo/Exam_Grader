#!/usr/bin/env python3
"""
Script to create a test marking guide for testing the API endpoint.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from webapp.exam_grader_app import app
from src.database.models import MarkingGuide, User, db
import uuid

def create_test_guide():
    """Create a test marking guide."""
    with app.app_context():
        # Get the first user
        user = User.query.first()
        if not user:
            print("No users found in database. Please create a user first.")
            return
        
        # Check if test guide already exists
        existing_guide = MarkingGuide.query.filter_by(title="Test Marking Guide").first()
        if existing_guide:
            print(f"Test guide already exists with ID: {existing_guide.id}")
            return existing_guide.id
        
        # Create test marking guide
        guide_id = str(uuid.uuid4())
        test_guide = MarkingGuide(
            id=guide_id,
            user_id=user.id,
            title="Test Marking Guide",
            description="A test marking guide for API testing",
            filename="test_guide.pdf",
            file_path="/uploads/test_guide.pdf",
            file_size=1024,
            file_type="application/pdf",
            content_text="Question 1: What is 2+2?\nAnswer: 4\n\nQuestion 2: What is the capital of France?\nAnswer: Paris",
            total_marks=100.0,
            max_questions_to_answer=2
        )
        
        db.session.add(test_guide)
        db.session.commit()
        
        print(f"Test marking guide created successfully with ID: {guide_id}")
        return guide_id

if __name__ == "__main__":
    guide_id = create_test_guide()
    print(f"\nYou can now test the API with: /api/marking-guides/{guide_id}")