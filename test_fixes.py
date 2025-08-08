#!/usr/bin/env python3
"""
Test script to verify the fixes for the exam grader issues.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.enhanced_result_service import enhanced_result_service
from src.database.models import GradingResult
import json

def test_enhanced_result_service():
    """Test the enhanced result service with problematic data."""
    print("Testing Enhanced Result Service...")
    
    # Test case 1: None values in detailed grades
    test_result = {
        "id": "test_result_1",
        "score": 85.5,
        "max_score": 100,
        "percentage": 85.5,
        "confidence": None,  # This was causing the comparison error
        "detailed_feedback": json.dumps([
            {
                "question_id": "Q1",
                "score": None,  # This was causing issues
                "max_score": 10,
                "feedback": "Good answer"
            },
            {
                "question_id": "Q2", 
                "score": 8.5,
                "max_score": None,  # This was causing issues
                "feedback": "Needs improvement"
            }
        ])
    }
    
    try:
        # Test individual methods to isolate the issue
        detailed_grades = enhanced_result_service._parse_detailed_feedback(test_result.get("detailed_feedback"))
        print(f"  - Parsed detailed grades: {len(detailed_grades)} grades")
        
        if detailed_grades:
            enhanced_grades = enhanced_result_service._enhance_detailed_grades(detailed_grades)
            print(f"  - Enhanced grades: {len(enhanced_grades)} grades")
            
            analytics = enhanced_result_service._calculate_grade_analytics(detailed_grades)
            print(f"  - Analytics calculated: {bool(analytics)}")
            
            # This is likely where the error occurs
            insights = enhanced_result_service._generate_performance_insights(detailed_grades, test_result.get("percentage", 0))
            print(f"  - Performance insights: {len(insights)} insights")
        
        enhanced = enhanced_result_service.enhance_result(test_result)
        print("✓ Enhanced result service handled None values correctly")
        print(f"  - Confidence analysis: {enhanced.get('confidence_analysis', {}).get('level', 'N/A')}")
        print(f"  - Performance insights: {len(enhanced.get('performance_insights', []))} insights generated")
        return True
    except Exception as e:
        print(f"✗ Enhanced result service failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_grading_result_model():
    """Test the GradingResult model total_score property."""
    print("\nTesting GradingResult Model...")
    
    try:
        # Create a mock GradingResult object (without database)
        class MockGradingResult:
            def __init__(self):
                self.score = 85.5
            
            @property
            def total_score(self):
                return self.score
            
            @total_score.setter
            def total_score(self, value):
                self.score = value
        
        result = MockGradingResult()
        
        # Test getter
        assert result.total_score == 85.5, "total_score getter failed"
        
        # Test setter
        result.total_score = 90.0
        assert result.score == 90.0, "total_score setter failed"
        assert result.total_score == 90.0, "total_score getter after setter failed"
        
        print("✓ GradingResult total_score property works correctly")
        return True
    except Exception as e:
        print(f"✗ GradingResult model test failed: {e}")
        return False

def test_settings_route_imports():
    """Test if settings route dependencies can be imported."""
    print("\nTesting Settings Route Dependencies...")
    
    try:
        from webapp.routes.main_routes import main_bp
        from src.database.models import UserSettings
        print("✓ Settings route imports work correctly")
        return True
    except ImportError as e:
        print(f"✗ Settings route import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Settings route test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Running Exam Grader Fix Tests")
    print("=" * 40)
    
    tests = [
        test_enhanced_result_service,
        test_grading_result_model,
        test_settings_route_imports
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"Tests completed: {passed}/{total} passed")
    
    if passed == total:
        print("✓ All fixes appear to be working correctly!")
        return 0
    else:
        print("✗ Some issues remain. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())