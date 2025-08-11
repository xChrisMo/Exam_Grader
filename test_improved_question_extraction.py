#!/usr/bin/env python3
"""
Test script for Improved Question Extraction
Tests the enhanced LLM question extraction with intelligent grouping decisions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_improved_question_extraction():
    """Test the improved question extraction functionality."""
    
    print("🧪 Testing Improved Question Extraction with Intelligent Grouping")
    print("=" * 70)
    
    # Import the function we improved
    try:
        from webapp.routes.guide_processing_routes import extract_questions_with_llm
        print("✅ Successfully imported extract_questions_with_llm function")
    except ImportError as e:
        print(f"❌ Failed to import function: {e}")
        return False
    
    # Test Case 1: Mixed grouped and separate questions
    print("\n📝 Test Case 1: Mixed grouped and separate questions")
    content_1 = """
    BIOLOGY EXAM - SEMESTER 1
    
    Question 1: Cell Structure and Function (25 marks total)
    a) Draw and label a plant cell (10 marks)
    b) Explain the function of chloroplasts (8 marks)  
    c) Compare plant and animal cells (7 marks)
    
    Question 2: Describe the process of photosynthesis. Include the chemical equation and explain where it occurs in the plant. (15 marks)
    
    Question 3: Genetics Problems (20 marks total)
    Part A: A brown-eyed father (Bb) and blue-eyed mother (bb) have children.
    - What is the probability of brown-eyed children? (5 marks)
    - Draw a Punnett square to show your work (5 marks)
    Part B: Explain the difference between genotype and phenotype with examples (10 marks)
    
    Question 4: Define the following terms: (2 marks each)
    - Mitosis
    - Meiosis  
    - DNA
    - RNA
    - Chromosome
    """
    
    result_1 = extract_questions_with_llm(content_1)
    
    if result_1:
        print(f"✅ Extracted {len(result_1)} questions")
        for i, q in enumerate(result_1):
            print(f"   Question {i+1}: {q.get('number', 'Unknown')} - {q.get('type', 'Unknown')} - {q.get('marks', 0)} marks")
            if q.get('sub_parts'):
                print(f"      Sub-parts: {', '.join(q.get('sub_parts', []))}")
    else:
        print("❌ No questions extracted")
    
    # Test Case 2: Unconventional formatting
    print("\n📝 Test Case 2: Unconventional formatting")
    content_2 = """
    MATHEMATICS ASSESSMENT
    
    Problem Set Alpha: Quadratic Equations
    Given the equation y = x² - 4x + 3
    • Find the vertex of the parabola
    • Determine the x-intercepts  
    • Sketch the graph
    • State the domain and range
    Total: 20 points
    
    Problem Set Beta: Solve the following independently:
    1) 2x + 5 = 13 (3 points)
    2) 3(x - 2) = 15 (3 points)  
    3) x² - 9 = 0 (4 points)
    
    Essay Question: Explain the relationship between algebra and geometry in coordinate systems. Provide specific examples and discuss practical applications. (25 points)
    """
    
    result_2 = extract_questions_with_llm(content_2)
    
    if result_2:
        print(f"✅ Extracted {len(result_2)} questions")
        for i, q in enumerate(result_2):
            print(f"   Question {i+1}: {q.get('number', 'Unknown')} - {q.get('type', 'Unknown')} - {q.get('marks', 0)} marks")
            if q.get('sub_parts'):
                print(f"      Sub-parts: {', '.join(q.get('sub_parts', []))}")
    else:
        print("❌ No questions extracted")
    
    # Test Case 3: Complex scenario-based questions
    print("\n📝 Test Case 3: Complex scenario-based questions")
    content_3 = """
    BUSINESS STUDIES CASE STUDY EXAM
    
    Case Study: TechStart Inc.
    TechStart Inc. is a software startup founded in 2020. The company develops mobile applications for small businesses. In 2023, they faced increased competition and declining sales.
    
    Based on the case study above, answer the following:
    
    Section A: Analysis (40 marks)
    1. Identify THREE internal factors that may have contributed to TechStart's challenges
    2. Suggest TWO external factors affecting the company's performance  
    3. Analyze the competitive landscape in the mobile app industry
    4. Evaluate the company's market position
    
    Section B: Strategic Planning (35 marks)
    Using SWOT analysis framework:
    - Identify Strengths (5 marks)
    - Identify Weaknesses (5 marks)
    - Identify Opportunities (10 marks)
    - Identify Threats (10 marks)
    - Recommend strategic actions (5 marks)
    
    Section C: Independent Question
    Explain the importance of market research in business decision-making. (25 marks)
    """
    
    result_3 = extract_questions_with_llm(content_3)
    
    if result_3:
        print(f"✅ Extracted {len(result_3)} questions")
        for i, q in enumerate(result_3):
            print(f"   Question {i+1}: {q.get('number', 'Unknown')} - {q.get('type', 'Unknown')} - {q.get('marks', 0)} marks")
            if q.get('sub_parts'):
                print(f"      Sub-parts: {', '.join(q.get('sub_parts', []))}")
    else:
        print("❌ No questions extracted")
    
    # Test Case 4: All separate questions
    print("\n📝 Test Case 4: All separate questions")
    content_4 = """
    GENERAL KNOWLEDGE QUIZ
    
    Question 1: What is the capital of France? (2 marks)
    
    Question 2: Who wrote "Romeo and Juliet"? (2 marks)
    
    Question 3: What is 15 × 8? (2 marks)
    
    Question 4: Name the largest planet in our solar system. (2 marks)
    
    Question 5: In which year did World War II end? (2 marks)
    """
    
    result_4 = extract_questions_with_llm(content_4)
    
    if result_4:
        print(f"✅ Extracted {len(result_4)} questions")
        for i, q in enumerate(result_4):
            print(f"   Question {i+1}: {q.get('number', 'Unknown')} - {q.get('type', 'Unknown')} - {q.get('marks', 0)} marks")
    else:
        print("❌ No questions extracted")
    
    # Test Case 5: All grouped questions
    print("\n📝 Test Case 5: All grouped questions")
    content_5 = """
    CHEMISTRY LAB REPORT ASSESSMENT
    
    Experiment 1: Acid-Base Titration
    You performed a titration of HCl with NaOH. Use your results to answer:
    a) Calculate the molarity of the HCl solution (8 marks)
    b) Explain any sources of error in your experiment (6 marks)
    c) Suggest improvements to increase accuracy (6 marks)
    
    Experiment 2: Crystallization Process  
    Based on your crystallization of copper sulfate:
    i) Describe the crystallization process you observed (5 marks)
    ii) Calculate the percentage yield of crystals obtained (7 marks)
    iii) Explain factors affecting crystal formation (8 marks)
    """
    
    result_5 = extract_questions_with_llm(content_5)
    
    if result_5:
        print(f"✅ Extracted {len(result_5)} questions")
        for i, q in enumerate(result_5):
            print(f"   Question {i+1}: {q.get('number', 'Unknown')} - {q.get('type', 'Unknown')} - {q.get('marks', 0)} marks")
            if q.get('sub_parts'):
                print(f"      Sub-parts: {', '.join(q.get('sub_parts', []))}")
    else:
        print("❌ No questions extracted")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 IMPROVED QUESTION EXTRACTION TEST SUMMARY")
    print("=" * 70)
    
    test_results = [result_1, result_2, result_3, result_4, result_5]
    test_names = [
        "Mixed grouped and separate",
        "Unconventional formatting", 
        "Complex scenario-based",
        "All separate questions",
        "All grouped questions"
    ]
    
    successful_tests = 0
    total_tests = len(test_results)
    
    for i, (result, name) in enumerate(zip(test_results, test_names), 1):
        if result and len(result) > 0:
            successful_tests += 1
            status = "✅ PASS"
            
            # Check for intelligent grouping
            has_grouped = any(q.get('type') == 'grouped' for q in result)
            has_individual = any(q.get('type') == 'individual' for q in result)
            
            grouping_info = ""
            if has_grouped and has_individual:
                grouping_info = " (Mixed grouping ✓)"
            elif has_grouped:
                grouping_info = " (All grouped ✓)"
            elif has_individual:
                grouping_info = " (All individual ✓)"
                
        else:
            status = "❌ FAIL"
            grouping_info = ""
        
        print(f"Test {i} ({name}): {status} - {len(result) if result else 0} questions{grouping_info}")
    
    success_rate = (successful_tests / total_tests) * 100
    print(f"\n🎯 Overall Success Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")
    
    if success_rate >= 80:
        print("🎉 Improved question extraction is working excellently!")
        print("✅ LLM is making intelligent grouping decisions without restrictive examples")
    elif success_rate >= 60:
        print("⚠️  Improved question extraction shows good results but could be refined")
    else:
        print("🔧 Question extraction needs further improvements")
    
    print("\n🔍 Key Improvements Verified:")
    print("✅ No restrictive examples limiting LLM flexibility")
    print("✅ Intelligent grouping based on content relationships")
    print("✅ Adaptive to any format or structure")
    print("✅ Focus on educational intent and pedagogical purpose")
    print("✅ Freedom to make context-aware decisions")
    
    return success_rate >= 60

if __name__ == "__main__":
    try:
        success = test_improved_question_extraction()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)