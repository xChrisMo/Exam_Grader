#!/usr/bin/env python3
"""
Simple test to verify LLM question extraction behavior.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variables
os.environ['FLASK_APP'] = 'webapp.exam_grader_app'

def test_question_extraction():
    """Test LLM question extraction with different document types."""
    
    try:
        from src.services.llm_service import LLMService
        from src.services.mapping_service import MappingService
        from src.security.secrets_manager import secrets_manager
        
        print("🧪 Testing LLM Question Extraction...")
        
        # Initialize services
        llm_api_key = secrets_manager.get_secret('DEEPSEEK_API_KEY')
        if not llm_api_key:
            print("❌ No LLM API key found")
            return False
            
        llm_service = LLMService(api_key=llm_api_key)
        mapping_service = MappingService(llm_service=llm_service)
        
        # Test Case 1: Traditional Q&A format
        traditional_content = """
        COMPUTER SCIENCE EXAM
        
        QUESTION 1: Define object-oriented programming and explain its main principles. (25 marks)
        
        QUESTION 2: Write a Python function that sorts a list of integers using bubble sort. (20 marks)
        
        QUESTION 3: Explain the difference between inheritance and composition in OOP. (15 marks)
        
        Total marks: 60
        """
        
        print("\n📝 Test Case 1: Traditional Q&A Format")
        print("Content preview:", traditional_content[:100] + "...")
        
        result1 = mapping_service.extract_questions_and_total_marks(traditional_content)
        
        print(f"✅ Method: {result1.get('extraction_method', 'unknown')}")
        print(f"✅ Questions found: {len(result1.get('questions', []))}")
        print(f"✅ Total marks: {result1.get('total_marks', 0)}")
        
        questions1 = result1.get('questions', [])
        for i, q in enumerate(questions1, 1):
            text = q.get('text', 'No text')[:80] + "..." if len(q.get('text', '')) > 80 else q.get('text', 'No text')
            print(f"   {i}. {text} ({q.get('marks', 0)} marks)")
        
        # Test Case 2: Classification task format (like the current document)
        classification_content = """
        Department of Computer Science
        Course Title: Natural Language Processing / Machine Learning
        Assignment Type: Coding Challenge
        Topic: Text Classification Using Machine Learning
        Total Marks: 100
        
        Instructions:
        Classify each of the following texts into A, B, or C:
        A = Veterinary Student
        B = Practicing Veterinarian  
        C = Other Healthcare Professional
        
        1. "I think a lot of other people made some good points so I'm not going to repeat a lot of it. It's never too late to consider vet med as a career and undergrad is a great opportunity to push yourself and make yourself competitive."
        
        2. "Currently I'm a third-year vet student, and I've just started my clinical rotations at a university-affiliated animal hospital."
        
        3. "I consult with several small animal clinics across the state, providing support on surgical procedures and equipment upgrades."
        
        4. "I'm a nurse specializing in neonatal care. I collaborate closely with pediatricians but do not make diagnoses or prescribe treatments."
        
        5. "I recently opened a mobile vet practice and offer home visits for pets in rural areas where clinics are not accessible."
        
        6. "As a pathology technician, I process blood and tissue samples sent in by doctors. I rarely interact with patients directly."
        
        7. "I've been practicing emergency veterinary medicine for over five years, mostly focusing on critical care and trauma."
        
        8. "I am in my final year of medical school, and I've just completed an internship in internal medicine."
        
        9. "I will play devil's advocate though. I am a second-year resident and I'm burnt out already. Undergrad is 4 years, vet school is another 4, and residency is 3. If you want to do aquatic medicine then it will likely be another 2 years of rotating and specialty internships before residency. That's upwards of 13 years of training ahead of you. Vet Med can be rewarding, but it is hard and long to get to the end of your training. I'm not saying this to discourage you, but simply to make sure you know what you would be commuting to. You have to be driven and always keep your eye on the prize. Be prepared for long nights, long weeks, and long years. As someone who knows people looking for path jobs in diagnostics/industry, this information is not current. Most diagnostic centers have placed a hold on hiring and industry has definitely slowed down. Also, pharma almost always requires a concurrent PhD. Some of these comments are absolutely insane and just speak to how toxic the culture is in vet med. For most of you, stop cherry-picking what OP said in the post. If the technician is calling the other doctors by their last name/title and refusing to call OP by it then it's not a lack of respect—it is active disrespect. As a technician, I would never have disrespected a doctor like that. As a doctor now, I would expect the same respect as my other colleagues. I go by my first name because that's how I like it, but as someone who was once a technician, the appropriate thing to do is to call them by their last name/title at first and feel it out or simply ask what they prefer."
        
        10. "I provide telehealth consultations for family doctors and review cases remotely as a specialist in dermatology."
        """
        
        print("\n📝 Test Case 2: Classification Task Format")
        print("Content preview:", classification_content[:100] + "...")
        
        result2 = mapping_service.extract_questions_and_total_marks(classification_content)
        
        print(f"✅ Method: {result2.get('extraction_method', 'unknown')}")
        print(f"✅ Questions found: {len(result2.get('questions', []))}")
        print(f"✅ Total marks: {result2.get('total_marks', 0)}")
        
        questions2 = result2.get('questions', [])
        for i, q in enumerate(questions2, 1):
            text = q.get('text', 'No text')[:80] + "..." if len(q.get('text', '')) > 80 else q.get('text', 'No text')
            print(f"   {i}. {text} ({q.get('marks', 0)} marks)")
        
        # Analysis
        print("\n🔍 Analysis:")
        print(f"Traditional format extracted {len(questions1)} questions (expected: 3)")
        print(f"Classification format extracted {len(questions2)} questions (expected: 1)")
        
        if len(questions1) == 3 and len(questions2) == 1:
            print("✅ SUCCESS: LLM correctly identified question structures!")
            return True
        else:
            print("❌ ISSUE: LLM is not correctly identifying question structures")
            print("Expected:")
            print("  - Traditional format: 3 explicit questions")
            print("  - Classification format: 1 overall classification task")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Question Extraction Test...")
    success = test_question_extraction()
    
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n💥 Tests failed! Check the logs above for details.")
    
    sys.exit(0 if success else 1)
