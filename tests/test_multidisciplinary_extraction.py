#!/usr/bin/env python3
"""
Comprehensive test for multi-disciplinary question extraction system.
Tests the LLM's ability to intelligently identify questions across various academic disciplines.
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
    """Test multi-disciplinary question extraction capabilities."""
    
    try:
        from src.services.llm_service import LLMService
        from src.services.mapping_service import MappingService
        from src.security.secrets_manager import secrets_manager
        
        print("🚀 Starting Multi-Disciplinary Question Extraction Test...")
        
        # Initialize services
        llm_api_key = secrets_manager.get_secret('DEEPSEEK_API_KEY')
        if not llm_api_key:
            print("❌ No LLM API key found")
            return False
            
        llm_service = LLMService(api_key=llm_api_key)
        mapping_service = MappingService(llm_service=llm_service)
        
        print("✅ Services initialized successfully")
        
        # Test cases for different disciplines
        test_cases = [
            {
                "name": "Computer Science - Programming Assignment",
                "content": """
                Computer Science 101 - Programming Assignment
                Total Marks: 100
                
                QUESTION 1: Write a Python function called 'binary_search' that takes a sorted list and a target value as parameters. The function should return the index of the target if found, or -1 if not found. (40 marks)
                
                QUESTION 2: Analyze the time complexity of the following algorithm and explain your reasoning:
                
                def bubble_sort(arr):
                    n = len(arr)
                    for i in range(n):
                        for j in range(0, n-i-1):
                            if arr[j] > arr[j+1]:
                                arr[j], arr[j+1] = arr[j+1], arr[j]
                    return arr
                
                (30 marks)
                
                QUESTION 3: Design a simple database schema for a library management system. Include tables for books, authors, and borrowers. Specify primary keys, foreign keys, and relationships. (30 marks)
                """,
                "expected_questions": 3,
                "expected_discipline": "Computer Science"
            },
            
            {
                "name": "Mathematics - Calculus Exam",
                "content": """
                Mathematics 201 - Calculus Midterm Exam
                Total Marks: 80
                
                1. Find the derivative of f(x) = 3x³ - 2x² + 5x - 1 (10 marks)
                
                2. Use the chain rule to find dy/dx for y = sin(2x³ + 1) (15 marks)
                
                3. Evaluate the definite integral: ∫[0 to π] sin(x)cos(x) dx (20 marks)
                
                4. A ball is thrown upward with an initial velocity of 64 ft/s from a height of 80 ft. The height function is h(t) = -16t² + 64t + 80. Find:
                   a) The maximum height reached (10 marks)
                   b) The time when the ball hits the ground (15 marks)
                   c) The velocity when the ball hits the ground (10 marks)
                """,
                "expected_questions": 4,
                "expected_discipline": "Mathematics"
            },
            
            {
                "name": "Literature - Text Analysis",
                "content": """
                English Literature 301 - Shakespeare Analysis
                Total Marks: 100
                
                Read the following passage from Hamlet, Act 3, Scene 1:
                
                "To be or not to be, that is the question:
                Whether 'tis nobler in the mind to suffer
                The slings and arrows of outrageous fortune,
                Or to take arms against a sea of troubles
                And, by opposing, end them."
                
                QUESTION 1: Analyze the use of metaphor in this soliloquy. How do the metaphors contribute to the overall meaning and emotional impact? (40 marks)
                
                QUESTION 2: Discuss the philosophical themes present in this passage. How does Hamlet's internal conflict reflect broader existential questions? (35 marks)
                
                QUESTION 3: Compare this soliloquy to another famous soliloquy from Shakespeare's works. Analyze similarities and differences in style, theme, and dramatic function. (25 marks)
                """,
                "expected_questions": 3,
                "expected_discipline": "Literature"
            },
            
            {
                "name": "Business - Case Study Analysis",
                "content": """
                Business Strategy 401 - Case Study Analysis
                Total Marks: 100
                
                Case Study: Netflix's Transformation from DVD-by-Mail to Streaming Giant
                
                Background: Netflix was founded in 1997 as a DVD-by-mail service. In 2007, they launched their streaming service, and by 2013, they had transitioned to become primarily a streaming platform while also investing heavily in original content production.
                
                Financial Data:
                - 2007 Revenue: $1.2 billion (primarily DVD)
                - 2020 Revenue: $25 billion (primarily streaming)
                - Current subscribers: 230+ million globally
                - Content investment: $15+ billion annually
                
                Questions for Analysis:
                
                1. Analyze Netflix's strategic transformation from a traditional DVD rental business to a streaming platform. What were the key factors that enabled this successful pivot? (30 marks)
                
                2. Evaluate Netflix's decision to invest heavily in original content production. Calculate the ROI implications and assess the strategic benefits beyond financial returns. (35 marks)
                
                3. Develop a strategic recommendation for Netflix's next phase of growth. Consider emerging technologies, market saturation, and competitive pressures. (35 marks)
                """,
                "expected_questions": 3,
                "expected_discipline": "Business"
            },
            
            {
                "name": "Text Classification Task",
                "content": """
                Department of Computer Science
                Course Title: Natural Language Processing / Machine Learning
                Assignment Type: Coding Challenge
                Topic: Text Classification Using Machine Learning
                Total Marks: 100
                
                Instructions:
                Classify each of the following texts into A, B, or C.
                
                1. I think a lot of other people made some good points so I'm not going to repeat a lot of it. It's never too late to consider vet med as a career and undergrad is a great opportunity to push yourself and make yourself competitive.
                
                2. "Currently I'm a third-year vet student, and I've just started my clinical rotations at a university-affiliated animal hospital."
                
                3. "I consult with several small animal clinics across the state, providing support on surgical procedures and equipment upgrades."
                
                4. "I'm a nurse specializing in neonatal care. I collaborate closely with pediatricians but do not make diagnoses or prescribe treatments."
                
                5. "I recently opened a mobile vet practice and offer home visits for pets in rural areas where clinics are not accessible."
                
                [Additional text items 6-10 continue...]
                """,
                "expected_questions": 1,
                "expected_discipline": "Computer Science"
            }
        ]
        
        # Run tests
        all_passed = True
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test {i}: {test_case['name']}")
            print("=" * 60)
            
            try:
                result = mapping_service.extract_questions_and_total_marks(test_case['content'])
                
                questions = result.get('questions', [])
                total_marks = result.get('total_marks', 0)
                analysis = result.get('analysis', {})
                
                print(f"📊 Results:")
                print(f"   Questions extracted: {len(questions)}")
                print(f"   Total marks: {total_marks}")
                print(f"   Extraction method: {result.get('extraction_method', 'unknown')}")
                
                if analysis:
                    print(f"   Document type: {analysis.get('document_type', 'Unknown')}")
                    print(f"   Primary discipline: {analysis.get('primary_discipline', 'Unknown')}")
                    print(f"   Question format: {analysis.get('question_format', 'Unknown')}")
                    print(f"   Confidence: {analysis.get('extraction_confidence', 'Unknown')}")
                
                print(f"\n📝 Extracted Questions:")
                for j, q in enumerate(questions, 1):
                    print(f"   {j}. {q.get('text', 'No text')[:80]}...")
                    print(f"      Marks: {q.get('marks', 0)}")
                    print(f"      Discipline: {q.get('discipline', 'Unknown')}")
                    print(f"      Type: {q.get('question_type', 'Unknown')}")
                    if q.get('reasoning'):
                        print(f"      Reasoning: {q.get('reasoning', '')[:100]}...")
                
                # Validate results
                expected_questions = test_case['expected_questions']
                if len(questions) == expected_questions:
                    print(f"✅ PASS: Correct number of questions ({len(questions)})")
                else:
                    print(f"❌ FAIL: Expected {expected_questions} questions, got {len(questions)}")
                    all_passed = False
                
                # Check if discipline was identified correctly (if analysis is available)
                if analysis and analysis.get('primary_discipline'):
                    identified_discipline = analysis.get('primary_discipline', '')
                    expected_discipline = test_case['expected_discipline']
                    if expected_discipline.lower() in identified_discipline.lower():
                        print(f"✅ PASS: Correct discipline identified ({identified_discipline})")
                    else:
                        print(f"⚠️  WARNING: Expected {expected_discipline}, identified {identified_discipline}")
                
            except Exception as e:
                print(f"❌ ERROR: {str(e)}")
                all_passed = False
        
        print("\n" + "=" * 80)
        if all_passed:
            print("🎉 ALL TESTS PASSED! Multi-disciplinary question extraction is working correctly.")
        else:
            print("⚠️  SOME TESTS FAILED. Review the results above for details.")
        
        return all_passed
        
    except Exception as e:
        print(f"💥 Test setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_question_extraction()
    sys.exit(0 if success else 1)
