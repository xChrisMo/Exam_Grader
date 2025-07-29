"""
Test runner for the comprehensive processing system test suite

This script runs all tests including unit tests, integration tests,
performance tests, and error scenario tests.
"""

import sys
import os
import pytest
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def run_test_suite():
    """Run the complete test suite with reporting"""
    
    print("=" * 80)
    print("PROCESSING SYSTEM COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    
    test_categories = [
        {
            'name': 'Unit Tests - Error Handling',
            'path': 'tests/test_error_handling_system.py',
            'description': 'Tests for error handling components'
        },
        {
            'name': 'Unit Tests - File Processing',
            'path': 'tests/test_file_processing_service.py',
            'description': 'Tests for file processing service'
        },
        {
            'name': 'Unit Tests - Enhanced File Processing',
            'path': 'tests/test_enhanced_file_processing.py',
            'description': 'Tests for enhanced file processing components'
        },
        {
            'name': 'Unit Tests - Performance Monitoring',
            'path': 'tests/test_performance_monitoring.py',
            'description': 'Tests for performance monitoring system'
        },
        {
            'name': 'Integration Tests - Processing Pipeline',
            'path': 'tests/integration/test_processing_pipeline.py',
            'description': 'Integration tests for complete processing pipeline'
        },
        {
            'name': 'Performance Tests - System Performance',
            'path': 'tests/performance/test_system_performance.py',
            'description': 'Performance and load tests'
        }
    ]
    
    results = {}
    total_start_time = time.time()
    
    for category in test_categories:
        print(f"\n{'-' * 60}")
        print(f"Running: {category['name']}")
        print(f"Description: {category['description']}")
        print(f"Path: {category['path']}")
        print(f"{'-' * 60}")
        
        start_time = time.time()
        
        # Run tests with pytest
        result = pytest.main([
            category['path'],
            '-v',
            '--tb=short',
            '--no-header',
            '--disable-warnings'
        ])
        
        duration = time.time() - start_time
        
        results[category['name']] = {
            'result': result,
            'duration': duration,
            'status': 'PASSED' if result == 0 else 'FAILED'
        }
        
        print(f"\nResult: {results[category['name']]['status']}")
        print(f"Duration: {duration:.2f} seconds")
    
    total_duration = time.time() - total_start_time
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUITE SUMMARY")
    print("=" * 80)
    
    passed_count = 0
    failed_count = 0
    
    for category_name, result_info in results.items():
        status_symbol = "✅" if result_info['status'] == 'PASSED' else "❌"
        print(f"{status_symbol} {category_name:<40} {result_info['status']:<8} ({result_info['duration']:.2f}s)")
        
        if result_info['status'] == 'PASSED':
            passed_count += 1
        else:
            failed_count += 1
    
    print(f"\n{'-' * 80}")
    print(f"Total Categories: {len(test_categories)}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    print(f"Total Duration: {total_duration:.2f} seconds")
    
    if failed_count == 0:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        return 0
    else:
        print(f"\n⚠️  {failed_count} TEST CATEGORIES FAILED")
        return 1

def run_specific_test_category(category_name):
    """Run a specific test category"""
    
    test_categories = {
        'error': 'tests/test_error_handling_system.py',
        'file': 'tests/test_file_processing_service.py',
        'enhanced': 'tests/test_enhanced_file_processing.py',
        'performance': 'tests/test_performance_monitoring.py',
        'integration': 'tests/integration/test_processing_pipeline.py',
        'load': 'tests/performance/test_system_performance.py'
    }
    
    if category_name not in test_categories:
        print(f"Unknown test category: {category_name}")
        print(f"Available categories: {', '.join(test_categories.keys())}")
        return 1
    
    test_path = test_categories[category_name]
    print(f"Running {category_name} tests from {test_path}")
    
    return pytest.main([
        test_path,
        '-v',
        '--tb=long'
    ])

def run_quick_tests():
    """Run a quick subset of tests for development"""
    
    print("Running quick test subset...")
    
    quick_tests = [
        'tests/test_error_handling_system.py::TestProcessingErrorHandler::test_initialization',
        'tests/test_file_processing_service.py::TestFileProcessingService::test_initialization',
        'tests/test_enhanced_file_processing.py::TestFileProcessorChain::test_chain_initialization',
        'tests/test_performance_monitoring.py::TestPerformanceMonitor::test_initialization'
    ]
    
    return pytest.main([
        *quick_tests,
        '-v',
        '--tb=short'
    ])

if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'quick':
            exit_code = run_quick_tests()
        elif command in ['error', 'file', 'enhanced', 'performance', 'integration', 'load']:
            exit_code = run_specific_test_category(command)
        else:
            print(f"Unknown command: {command}")
            print("Available commands: quick, error, file, enhanced, performance, integration, load")
            exit_code = 1
    else:
        exit_code = run_test_suite()
    
    sys.exit(exit_code)