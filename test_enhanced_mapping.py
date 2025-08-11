#!/usr/bin/env python3
"""
Test script for Enhanced Mapping Service
Tests various student exam scenarios to ensure correct mapping
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.consolidated_mapping_service import ConsolidatedMappingService
from src.services.consolidated_llm_service import ConsolidatedLLMService

def test_enhanced_mapping():
    """Test the enhanced mapping functionality with various student exam scenarios."""
    
    print("🧪 Testing Enhanced Mapping Service for Student Exams")
    print("=" * 60)
    
    # Initialize services
    llm_service = ConsolidatedLLMService()
    mapping_service = ConsolidatedMappingService(llm_service)
    
    # Test Case 1: Out-of-order answers
    print("\n📝 Test Case 1: Out-of-order answers")
    guide_content_1 = """
    EXAM QUESTIONS:
    Q1. Explain photosynthesis. [10 marks]
    Q2. What is cellular respiration? [8 marks]  
    Q3. Describe the water cycle. [12 marks]
    """
    
    submission_content_1 = """
    Student Name: John Smith
    
    Q3. The water cycle involves evaporation from oceans and lakes. Water vapor rises and condenses into clouds. Precipitation brings water back to earth as rain or snow.
    
    Q1. Photosynthesis is the process where plants use sunlight, carbon dioxide, and water to make glucose and oxygen. It happens in chloroplasts using chlorophyll.
    
    Q2. Cellular respiration breaks down glucose to release energy (ATP) for cellular processes. It uses oxygen and produces carbon dioxide and water.
    """
    
    result_1, error_1 = mapping_service.map_submission_to_guide(
        guide_content_1, submission_content_1, 3
    )
    
    print(f"✅ Mappings found: {len(result_1.get('mappings', []))}")
    print(f"✅ Quality assessment: {result_1.get('quality_assessment', {}).get('quality_level', 'unknown')}")
    
    # Test Case 2: Multi-part questions with sub-parts
    print("\n📝 Test Case 2: Multi-part questions")
    guide_content_2 = """
    BIOLOGY EXAM:
    1a) Define osmosis. [3 marks]
    1b) Give an example of osmosis in plants. [2 marks]
    2a) What is mitosis? [4 marks]
    2b) List the phases of mitosis. [6 marks]
    """
    
    submission_content_2 = """
    Answer Sheet - Biology Exam
    
    1a) Osmosis is the movement of water molecules through a semi-permeable membrane from high to low concentration.
    
    1b) Water moving into plant roots from soil is an example of osmosis.
    
    2a) Mitosis is cell division that produces two identical diploid cells from one parent cell.
    
    2b) The phases are: prophase, metaphase, anaphase, and telophase.
    """
    
    result_2, error_2 = mapping_service.map_submission_to_guide(
        guide_content_2, submission_content_2, 4
    )
    
    print(f"✅ Mappings found: {len(result_2.get('mappings', []))}")
    print(f"✅ Multi-part handling: {'Yes' if any('1a' in str(m) or '1b' in str(m) for m in result_2.get('mappings', [])) else 'No'}")
    
    # Test Case 3: OCR errors and handwriting issues
    print("\n📝 Test Case 3: OCR errors and handwriting issues")
    guide_content_3 = """
    CHEMISTRY TEST:
    Q1. What is the formula for water? [2 marks]
    Q2. Define pH scale. [5 marks]
    Q3. Name three acids. [3 marks]
    """
    
    submission_content_3 = """
    Student: Mary Johnson
    
    Ql. The formula for water is H20 (should be H2O but OCR read it wrong)
    
    02. pH scale measures how acidic or basic a solution is. It ranges from 0 to l4.
    
    Q3. Three acids are: hydrochloric acid (HCI), sulfuric acid (H2S04), and nitric acid (HN03)
    """
    
    result_3, error_3 = mapping_service.map_submission_to_guide(
        guide_content_3, submission_content_3, 3
    )
    
    print(f"✅ Mappings found: {len(result_3.get('mappings', []))}")
    print(f"✅ OCR error handling: {'Good' if len(result_3.get('mappings', [])) >= 2 else 'Needs improvement'}")
    
    # Test Case 4: Partial and incomplete answers
    print("\n📝 Test Case 4: Partial and incomplete answers")
    guide_content_4 = """
    PHYSICS EXAM:
    1. Explain Newton's First Law of Motion. [8 marks]
    2. Calculate the force when mass=5kg and acceleration=2m/s². [4 marks]
    3. Define kinetic energy and give its formula. [6 marks]
    """
    
    submission_content_4 = """
    Physics Answers:
    
    1. Newton's First Law says an object at rest stays at rest unless... (incomplete due to time)
    
    2. F = ma = 5 × 2 = 10N
    
    3. Kinetic energy is energy of motion. Formula: KE = (didn't finish)
    """
    
    result_4, error_4 = mapping_service.map_submission_to_guide(
        guide_content_4, submission_content_4, 3
    )
    
    print(f"✅ Mappings found: {len(result_4.get('mappings', []))}")
    print(f"✅ Partial answer detection: {'Yes' if any('partial' in str(m).lower() for m in result_4.get('mappings', [])) else 'No'}")
    
    # Test Case 5: Cross-references and complex formatting
    print("\n📝 Test Case 5: Cross-references and complex formatting")
    guide_content_5 = """
    LITERATURE EXAM:
    Part A: Short Answers
    1. Who wrote "Romeo and Juliet"? [2 marks]
    2. What is a metaphor? [3 marks]
    
    Part B: Essay Questions  
    3. Analyze the theme of love in Romeo and Juliet (refer to your answer in Part A). [15 marks]
    """
    
    submission_content_5 = """
    Literature Exam - Student: Alex Brown
    
    Part A:
    1. William Shakespeare wrote Romeo and Juliet.
    
    2. A metaphor is a figure of speech that compares two things without using "like" or "as".
    
    Part B:
    3. The theme of love in Romeo and Juliet (as mentioned in question 1, written by Shakespeare) is complex. The play shows different types of love: romantic love between Romeo and Juliet, familial love, and friendship. The metaphors (see my definition in question 2) used throughout the play enhance this theme...
    """
    
    result_5, error_5 = mapping_service.map_submission_to_guide(
        guide_content_5, submission_content_5, 3
    )
    
    print(f"✅ Mappings found: {len(result_5.get('mappings', []))}")
    print(f"✅ Cross-reference handling: {'Good' if len(result_5.get('mappings', [])) >= 2 else 'Needs improvement'}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 ENHANCED MAPPING TEST SUMMARY")
    print("=" * 60)
    
    total_tests = 5
    successful_tests = 0
    
    test_results = [result_1, result_2, result_3, result_4, result_5]
    for i, result in enumerate(test_results, 1):
        mappings_count = len(result.get('mappings', []))
        quality = result.get('quality_assessment', {}).get('quality_level', 'unknown')
        
        if mappings_count > 0 and quality != 'poor':
            successful_tests += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        print(f"Test {i}: {status} - {mappings_count} mappings, quality: {quality}")
    
    success_rate = (successful_tests / total_tests) * 100
    print(f"\n🎯 Overall Success Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")
    
    if success_rate >= 80:
        print("🎉 Enhanced mapping is working well for student exam scenarios!")
    elif success_rate >= 60:
        print("⚠️  Enhanced mapping shows improvement but needs fine-tuning.")
    else:
        print("🔧 Enhanced mapping needs significant improvements.")
    
    return success_rate >= 60

if __name__ == "__main__":
    try:
        success = test_enhanced_mapping()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)