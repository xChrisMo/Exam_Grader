#!/usr/bin/env python3
"""Test script to verify the enhanced grading system with max scores."""

from src.services.consolidated_grading_service import ConsolidatedGradingService
import json

def test_grading_system():
    """Test the grading service with sample data to verify max score functionality."""
    
    # Create test data with different max scores
    test_qa_pairs = [
        {
            'question_id': 'Q1',
            'question_text': 'What is photosynthesis?',
            'student_answer': 'Photosynthesis is the process by which plants make food using sunlight.',
            'max_score': 15.0
        },
        {
            'question_id': 'Q2', 
            'question_text': 'Explain cellular respiration.',
            'student_answer': 'Cellular respiration breaks down glucose to produce energy.',
            'max_score': 25.0
        },
        {
            'question_id': 'Q3',
            'question_text': 'Name three types of rocks.',
            'student_answer': 'Igneous, sedimentary, and metamorphic rocks.',
            'max_score': 10.0
        }
    ]

    # Test the grading service
    service = ConsolidatedGradingService()
    result = service.grade_submission_batch(test_qa_pairs, 'Sample marking guide')

    print('✅ Grading Service Test Results:')
    print(f'Total Score: {result["total_score"]} / {result["max_possible_score"]}')
    print(f'Percentage: {result["percentage"]}%')
    print(f'Letter Grade: {result["letter_grade"]}')
    print(f'Questions Graded: {len(result["detailed_grades"])}')
    print()
    
    print('📊 Individual Question Scores:')
    for grade in result['detailed_grades']:
        print(f'  {grade["question_id"]}: {grade["score"]}/{grade["max_score"]} points - {grade["feedback"]}')
    
    print()
    print('🎯 Summary:')
    print(f'  Average Score per Question: {result["summary"]["average_score"]:.2f}')
    print(f'  Total Questions: {result["summary"]["total_questions"]}')
    
    return result

if __name__ == '__main__':
    test_grading_system()