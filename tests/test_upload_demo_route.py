#!/usr/bin/env python3
"""
Demo route to test upload submission functionality with hardcoded data
This creates a test endpoint that simulates the upload process
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import tempfile
import json

# Create Flask app for demo
app = Flask(__name__, 
           template_folder='webapp/templates',
           static_folder='webapp/static')
app.secret_key = 'demo-secret-key-for-testing'

# Hardcoded sample data
SAMPLE_MARKING_GUIDE = {
    'filename': 'Department_of_Computer_Science2.docx',
    'questions': [
        {
            'number': '1',
            'text': 'Classify each of the following texts into A, B, or C.',
            'marks': 100,
            'discipline': 'Computer Science',
            'question_type': 'Classification Task',
            'reasoning': 'This is a single classification task where students must categorize each of the ten provided texts into one of three defined categories (A, B, or C). The marks are distributed across all texts, making it one coherent question with multiple parts.'
        }
    ],
    'total_marks': 100,
    'analysis': {
        'document_type': 'Assignment',
        'primary_discipline': 'Computer Science',
        'question_format': 'Classification Task',
        'extraction_confidence': 'High'
    }
}

SAMPLE_SUBMISSION_CONTENT = """
STUDENT SUBMISSION - TEXT CLASSIFICATION ASSIGNMENT
Name: Jane Smith
Student ID: 87654321
Course: Natural Language Processing / Machine Learning

CLASSIFICATION RESULTS:

Text 1: "I think a lot of other people made some good points..."
Classification: C (Other)
Reasoning: General advice, not from a practicing professional.

Text 2: "Currently I'm a third-year vet student..."
Classification: C (Other)
Reasoning: Student, not practicing veterinarian.

Text 3: "I consult with several small animal clinics..."
Classification: B (Veterinarian)
Reasoning: Consulting on surgical procedures indicates practicing vet.

Text 4: "I'm a nurse specializing in neonatal care..."
Classification: C (Other)
Reasoning: Nurse, not doctor.

Text 5: "I recently opened a mobile vet practice..."
Classification: B (Veterinarian)
Reasoning: Owns and operates veterinary practice.

Text 6: "As a pathology technician..."
Classification: C (Other)
Reasoning: Technician, not doctor.

Text 7: "I've been practicing emergency veterinary medicine..."
Classification: B (Veterinarian)
Reasoning: Practicing veterinary medicine.

Text 8: "I am in my final year of medical school..."
Classification: C (Other)
Reasoning: Student, not practicing doctor.

Text 9: "As a doctor now, I would expect the same respect..."
Classification: A (Medical Doctor)
Reasoning: Identifies as practicing doctor.

Text 10: "I provide telehealth consultations for family doctors..."
Classification: A (Medical Doctor)
Reasoning: Specialist providing medical consultations.

SUMMARY:
- Medical Doctor (A): 2 texts
- Veterinarian (B): 3 texts
- Other (C): 5 texts
"""

SAMPLE_GRADING_RESULT = {
    'submission_id': 'demo-12345',
    'filename': 'jane_smith_submission.txt',
    'processing_time': 2.5,
    'questions': [
        {
            'number': '1',
            'text': 'Classify each of the following texts into A, B, or C.',
            'total_marks': 100,
            'student_answer': 'Provided classifications for all 10 texts with reasoning',
            'marks_awarded': 85,
            'feedback': 'Excellent understanding of classification criteria. Minor deductions for incomplete reasoning on texts 1 and 6.',
            'detailed_feedback': {
                'strengths': [
                    'Correctly identified all practicing professionals',
                    'Properly classified students as "Other"',
                    'Good reasoning for most classifications'
                ],
                'improvements': [
                    'Text 1: Could provide more detailed reasoning',
                    'Text 6: Consider the distinction between technician and doctor roles'
                ],
                'accuracy': '8/10 classifications fully correct'
            }
        }
    ],
    'total_marks_awarded': 85,
    'total_marks_possible': 100,
    'percentage': 85.0,
    'grade': 'A',
    'overall_feedback': 'Strong performance demonstrating good understanding of the classification task. The student correctly identified the key distinctions between practicing professionals and students/support staff.'
}

@app.route('/')
def demo_home():
    """Demo home page"""
    return """
    <h1>🎓 Upload Submission Demo</h1>
    <p>This is a demo of the upload submission functionality with hardcoded data.</p>
    <ul>
        <li><a href="/demo-upload">📤 Demo Upload Submission Page</a></li>
        <li><a href="/demo-process">⚡ Demo Processing (Instant)</a></li>
        <li><a href="/demo-results">📊 Demo Results</a></li>
    </ul>
    """

@app.route('/demo-upload')
def demo_upload_page():
    """Demo upload submission page"""
    # Set session data to simulate having a marking guide
    session['guide_uploaded'] = True
    session['guide_filename'] = SAMPLE_MARKING_GUIDE['filename']
    
    return render_template('upload_submission.html')

@app.route('/demo-process', methods=['GET', 'POST'])
def demo_process():
    """Demo processing with hardcoded data"""
    if request.method == 'GET':
        return """
        <h2>🚀 Demo Processing</h2>
        <p>Click the button below to simulate processing a submission with hardcoded data.</p>
        <form method="POST">
            <button type="submit" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px;">
                📤 Process Demo Submission
            </button>
        </form>
        """
    
    # Simulate processing
    print("🚀 DEMO: Processing submission with hardcoded data...")
    print(f"📄 Marking Guide: {SAMPLE_MARKING_GUIDE['filename']}")
    print(f"📝 Questions: {len(SAMPLE_MARKING_GUIDE['questions'])}")
    print(f"📊 Total Marks: {SAMPLE_MARKING_GUIDE['total_marks']}")
    print("⏳ Processing submission content...")
    print("✅ Grading completed!")
    
    # Store results in session
    session['demo_results'] = SAMPLE_GRADING_RESULT
    
    return redirect('/demo-results')

@app.route('/demo-results')
def demo_results():
    """Demo results page"""
    results = session.get('demo_results', SAMPLE_GRADING_RESULT)
    
    html = f"""
    <h2>📊 Demo Grading Results</h2>
    <div style="max-width: 800px; margin: 0 auto; font-family: Arial, sans-serif;">
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3>📄 Submission Details</h3>
            <p><strong>File:</strong> {results['filename']}</p>
            <p><strong>Processing Time:</strong> {results['processing_time']} seconds</p>
            <p><strong>Submission ID:</strong> {results['submission_id']}</p>
        </div>
        
        <div style="background: #e8f5e8; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3>🎯 Overall Score</h3>
            <p style="font-size: 24px; margin: 10px 0;">
                <strong>{results['total_marks_awarded']}/{results['total_marks_possible']} 
                ({results['percentage']:.1f}%) - Grade: {results['grade']}</strong>
            </p>
            <p><strong>Overall Feedback:</strong> {results['overall_feedback']}</p>
        </div>
        
        <div style="background: #fff; border: 1px solid #ddd; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3>📝 Question-by-Question Breakdown</h3>
    """
    
    for q in results['questions']:
        html += f"""
            <div style="border-left: 4px solid #007bff; padding-left: 15px; margin-bottom: 20px;">
                <h4>Question {q['number']}: {q['text'][:50]}...</h4>
                <p><strong>Score:</strong> {q['marks_awarded']}/{q['total_marks']} marks</p>
                <p><strong>Student Answer:</strong> {q['student_answer']}</p>
                <p><strong>Feedback:</strong> {q['feedback']}</p>
                
                <div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 10px;">
                    <h5>📈 Detailed Feedback:</h5>
                    <p><strong>Strengths:</strong></p>
                    <ul>
        """
        
        for strength in q['detailed_feedback']['strengths']:
            html += f"<li>{strength}</li>"
        
        html += """
                    </ul>
                    <p><strong>Areas for Improvement:</strong></p>
                    <ul>
        """
        
        for improvement in q['detailed_feedback']['improvements']:
            html += f"<li>{improvement}</li>"
        
        html += f"""
                    </ul>
                    <p><strong>Accuracy:</strong> {q['detailed_feedback']['accuracy']}</p>
                </div>
            </div>
        """
    
    html += """
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="/demo-upload" style="padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">
                📤 Upload Another Submission
            </a>
            <a href="/" style="padding: 10px 20px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">
                🏠 Back to Demo Home
            </a>
        </div>
    </div>
    """
    
    return html

@app.route('/api/demo-upload', methods=['POST'])
def api_demo_upload():
    """API endpoint for demo upload"""
    # Simulate file upload processing
    return jsonify({
        'success': True,
        'message': 'Demo submission processed successfully!',
        'submission_id': 'demo-12345',
        'redirect_url': '/demo-results'
    })

if __name__ == '__main__':
    print("🚀 Starting Upload Submission Demo Server...")
    print("🌐 Demo URLs:")
    print("   📤 Upload Page: http://127.0.0.1:5001/demo-upload")
    print("   ⚡ Process Demo: http://127.0.0.1:5001/demo-process")
    print("   📊 Results: http://127.0.0.1:5001/demo-results")
    print("   🏠 Home: http://127.0.0.1:5001/")
    print("=" * 60)
    
    app.run(debug=True, port=5001)
