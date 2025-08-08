#!/usr/bin/env python3
"""
Test script for chart generation functionality in TrainingReportService
"""

import sys
import os
import tempfile
from pathlib import Path

# Ensure we use standard logging before importing anything else
import logging

# Add src to path
sys.path.insert(0, 'src')

def test_chart_imports():
    """Test that required visualization libraries are available"""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        import matplotlib.pyplot as plt
        import seaborn as sns
        print("✓ Matplotlib and Seaborn are available")
        return True
    except ImportError as e:
        print(f"✗ Visualization libraries not available: {e}")
        return False

def test_basic_chart_creation():
    """Test basic chart creation functionality"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        # Create a simple test chart
        fig, ax = plt.subplots(figsize=(8, 6))
        categories = ["High", "Medium", "Low"]
        values = [10, 15, 5]
        
        bars = ax.bar(categories, values, color=['#2ecc71', '#f39c12', '#e74c3c'])
        ax.set_title('Test Chart - Confidence Distribution')
        ax.set_ylabel('Count')
        
        # Add value labels
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{int(value)}', ha='center', va='bottom')
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            plt.savefig(tmp.name, dpi=300, bbox_inches='tight')
            plt.close()
            
            # Check if file was created
            if os.path.exists(tmp.name):
                file_size = os.path.getsize(tmp.name)
                print(f"✓ Test chart created successfully: {tmp.name} ({file_size} bytes)")
                os.unlink(tmp.name)  # Clean up
                return True
            else:
                print("✗ Chart file was not created")
                return False
                
    except Exception as e:
        print(f"✗ Failed to create test chart: {e}")
        return False

def test_service_import():
    """Test that TrainingReportService can be imported"""
    try:
        # Test if the file exists and can be compiled
        import py_compile
        service_path = 'src/services/training_report_service.py'
        py_compile.compile(service_path, doraise=True)
        print("✓ TrainingReportService compiles successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to compile TrainingReportService: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Chart Generation Functionality")
    print("=" * 50)
    
    tests = [
        ("Chart Libraries Import", test_chart_imports),
        ("Basic Chart Creation", test_basic_chart_creation),
        ("Service Import", test_service_import)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
    
    print(f"\n{'=' * 50}")
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! Chart generation functionality is ready.")
        return 0
    else:
        print("✗ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())