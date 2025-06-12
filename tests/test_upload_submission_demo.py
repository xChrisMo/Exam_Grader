#!/usr/bin/env python3
"""
Demo script to test upload submission functionality with hardcoded data
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_sample_submission_file():
    """Create a sample submission file with hardcoded content"""
    
    # Sample student submission content
    submission_content = """
STUDENT SUBMISSION - TEXT CLASSIFICATION ASSIGNMENT
Name: John Doe
Student ID: 12345678
Course: Natural Language Processing / Machine Learning

CLASSIFICATION RESULTS:

Text 1: "I think a lot of other people made some good points so I'm not going to repeat a lot of it. It's never too late to consider vet med as a career and undergrad is a great opportunity to push yourself and make yourself competitive."
Classification: C (Other)
Reasoning: This appears to be general advice about veterinary medicine career, but the speaker doesn't identify as a practicing veterinarian or doctor.

Text 2: "Currently I'm a third-year vet student, and I've just started my clinical rotations at a university-affiliated animal hospital."
Classification: C (Other)
Reasoning: This is a veterinary student, not a practicing veterinarian, so should be classified as "Other" according to the instructions.

Text 3: "I consult with several small animal clinics across the state, providing support on surgical procedures and equipment upgrades."
Classification: B (Veterinarian)
Reasoning: This person is consulting with veterinary clinics on surgical procedures, indicating they are a practicing veterinarian.

Text 4: "I'm a nurse specializing in neonatal care. I collaborate closely with pediatricians but do not make diagnoses or prescribe treatments."
Classification: C (Other)
Reasoning: This is a nurse, not a doctor, so should be classified as "Other" according to the instructions.

Text 5: "I recently opened a mobile vet practice and offer home visits for pets in rural areas where clinics are not accessible."
Classification: B (Veterinarian)
Reasoning: This person owns and operates a veterinary practice, clearly indicating they are a practicing veterinarian.

Text 6: "As a pathology technician, I process blood and tissue samples sent in by doctors. I rarely interact with patients directly."
Classification: C (Other)
Reasoning: This is a technician, not a doctor, so should be classified as "Other".

Text 7: "I've been practicing emergency veterinary medicine for over five years, mostly focusing on critical care and trauma."
Classification: B (Veterinarian)
Reasoning: This person is practicing veterinary medicine, clearly indicating they are a veterinarian.

Text 8: "I am in my final year of medical school, and I've just completed an internship in internal medicine."
Classification: C (Other)
Reasoning: This is a medical student, not a practicing doctor, so should be classified as "Other".

Text 9: [Long text about veterinary career advice]
Classification: A (Medical Doctor)
Reasoning: The speaker mentions "As a doctor now, I would expect the same respect as my other colleagues" indicating they are a practicing doctor.

Text 10: "I provide telehealth consultations for family doctors and review cases remotely as a specialist in dermatology."
Classification: A (Medical Doctor)
Reasoning: This person is a specialist in dermatology providing consultations, clearly indicating they are a practicing medical doctor.

SUMMARY:
- Medical Doctor (A): 2 texts
- Veterinarian (B): 3 texts  
- Other (C): 5 texts

Total: 10 texts classified
"""
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(submission_content)
    temp_file.close()
    
    return temp_file.name

def simulate_upload_process():
    """Simulate the upload submission process"""
    
    print("🚀 UPLOAD SUBMISSION DEMO")
    print("=" * 50)
    
    # Create sample submission file
    print("📄 Creating sample submission file...")
    submission_file = create_sample_submission_file()
    file_size = os.path.getsize(submission_file)
    
    print(f"✅ Sample submission created:")
    print(f"   📁 File: {submission_file}")
    print(f"   📊 Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    # Simulate file validation
    print("\n🔍 VALIDATING FILE...")
    print("✅ File format: .txt (supported)")
    print("✅ File size: Within limits")
    print("✅ File readable: Yes")
    
    # Simulate upload process
    print("\n📤 SIMULATING UPLOAD PROCESS...")
    print("⏳ Step 1: Uploading file...")
    print("⏳ Step 2: Processing content...")
    print("⏳ Step 3: Extracting text...")
    print("⏳ Step 4: Analyzing submission...")
    
    # Read and display content preview
    print("\n📋 SUBMISSION CONTENT PREVIEW:")
    print("-" * 40)
    with open(submission_file, 'r', encoding='utf-8') as f:
        content = f.read()
        preview = content[:500] + "..." if len(content) > 500 else content
        print(preview)
    
    # Simulate grading process
    print("\n🎯 SIMULATING GRADING PROCESS...")
    print("✅ Marking guide loaded: Department_of_Computer_Science2.docx")
    print("✅ Question identified: 'Classify each of the following texts into A, B, or C.'")
    print("✅ Total marks available: 100")
    print("✅ Submission format: Text classification results")
    
    # Simulate grading results
    print("\n📊 SIMULATED GRADING RESULTS:")
    print("-" * 40)
    print("🎯 Question 1: Text Classification (100 marks)")
    print("   📝 Student provided classifications for all 10 texts")
    print("   ✅ Correct format: Yes")
    print("   ✅ All texts classified: Yes")
    print("   ✅ Reasoning provided: Yes")
    print("   📊 Estimated score: 85/100")
    print("   💬 Feedback: Good understanding of classification criteria")
    
    # Cleanup
    print(f"\n🧹 Cleaning up temporary file: {submission_file}")
    os.unlink(submission_file)
    
    print("\n✅ UPLOAD SUBMISSION DEMO COMPLETED!")
    print("🌐 In the real application, visit: http://127.0.0.1:5000/upload-submission")

def demonstrate_file_types():
    """Demonstrate different supported file types"""
    
    print("\n📁 SUPPORTED FILE TYPES DEMO:")
    print("=" * 40)
    
    supported_types = [
        (".pdf", "PDF documents", "Best for scanned submissions"),
        (".docx", "Word documents", "Best for typed submissions"),
        (".doc", "Legacy Word documents", "Older Word format"),
        (".txt", "Plain text files", "Simple text submissions"),
        (".jpg", "JPEG images", "Scanned handwritten work"),
        (".png", "PNG images", "High quality scans"),
        (".tiff", "TIFF images", "Professional scanning format"),
        (".bmp", "Bitmap images", "Uncompressed image format"),
        (".gif", "GIF images", "Basic image format")
    ]
    
    for ext, name, description in supported_types:
        print(f"✅ {ext:<6} - {name:<20} - {description}")
    
    print(f"\n📊 Maximum file size: 16MB")
    print(f"🔧 Processing: OCR + LLM analysis")

if __name__ == "__main__":
    try:
        simulate_upload_process()
        demonstrate_file_types()
        
        print("\n" + "=" * 60)
        print("🎓 EXAM GRADER - UPLOAD SUBMISSION DEMO COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error during demo: {str(e)}")
        import traceback
        traceback.print_exc()
