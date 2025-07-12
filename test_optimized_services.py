#!/usr/bin/env python3
"""
Test script for optimized AI processing services.
This script verifies that all optimized services can be imported and initialized correctly.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_imports():
    """Test that all optimized services can be imported."""
    print("Testing imports...")
    
    try:
        from src.services.optimized_ocr_service import OptimizedOCRService
        print("✓ OptimizedOCRService imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import OptimizedOCRService: {e}")
        return False
    
    try:
        from src.services.optimized_mapping_service import OptimizedMappingService
        print("✓ OptimizedMappingService imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import OptimizedMappingService: {e}")
        return False
    
    try:
        from src.services.optimized_grading_service import OptimizedGradingService
        print("✓ OptimizedGradingService imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import OptimizedGradingService: {e}")
        return False
    
    try:
        from src.services.optimized_background_tasks import (
            ProcessingProgress,
            process_optimized_ocr_task,
            process_optimized_full_pipeline,
            process_batch_submissions_optimized
        )
        print("✓ Optimized background tasks imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import optimized background tasks: {e}")
        return False
    
    try:
        from webapp.optimized_routes import optimized_bp
        print("✓ Optimized routes blueprint imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import optimized routes: {e}")
        return False
    
    return True

def test_in_memory_cache():
    """Test in-memory caching functionality."""
    print("\nTesting in-memory cache...")
    
    try:
        from src.services.optimized_ocr_service import OptimizedOCRService
        ocr_service = OptimizedOCRService(api_key="test_key")
        
        # Test cache stats
        stats = ocr_service.get_cache_stats()
        if 'cache_enabled' in stats and stats['cache_enabled']:
            print("✓ In-memory cache is enabled and functional")
            print(f"  Cache entries: {stats.get('total_entries', 0)}")
            print(f"  Memory usage: {stats.get('memory_usage_mb', 0)} MB")
            return True
        else:
            print("✗ In-memory cache not properly configured")
            return False
    except Exception as e:
        print(f"✗ In-memory cache test failed: {e}")
        return False

def test_service_initialization():
    """Test that services can be initialized."""
    print("\nTesting service initialization...")
    
    try:
        # Test OptimizedOCRService
        from src.services.optimized_ocr_service import OptimizedOCRService
        ocr_service = OptimizedOCRService(api_key="test_key")
        print("✓ OptimizedOCRService initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize OptimizedOCRService: {e}")
        return False
    
    try:
        # Test OptimizedMappingService
        from src.services.optimized_mapping_service import OptimizedMappingService
        from src.services.llm_service import LLMService
        
        llm_service = LLMService(api_key="test_key")
        mapping_service = OptimizedMappingService(llm_service=llm_service)
        print("✓ OptimizedMappingService initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize OptimizedMappingService: {e}")
        return False
    
    try:
        # Test OptimizedGradingService
        from src.services.optimized_grading_service import OptimizedGradingService
        from src.services.llm_service import LLMService
        from src.services.optimized_mapping_service import OptimizedMappingService
        
        llm_service = LLMService(api_key="test_key")
        mapping_service = OptimizedMappingService(llm_service=llm_service)
        grading_service = OptimizedGradingService(
            llm_service=llm_service,
            mapping_service=mapping_service
        )
        print("✓ OptimizedGradingService initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize OptimizedGradingService: {e}")
        return False
    
    return True

def test_celery_configuration():
    """Test Celery configuration for background tasks."""
    print("\nTesting Celery configuration...")
    
    try:
        from src.services.optimized_background_tasks import celery_app
        
        # Test basic Celery configuration
        if celery_app.conf.broker_url:
            print(f"✓ Celery broker configured: {celery_app.conf.broker_url}")
        else:
            print("✗ Celery broker not configured")
            return False
        
        # Test task registration
        registered_tasks = list(celery_app.tasks.keys())
        optimized_tasks = [task for task in registered_tasks if 'optimized' in task]
        
        if optimized_tasks:
            print(f"✓ Optimized tasks registered: {len(optimized_tasks)}")
            for task in optimized_tasks:
                print(f"  - {task}")
        else:
            print("✗ No optimized tasks found")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Celery configuration test failed: {e}")
        return False

def test_dependencies():
    """Test that required dependencies are available."""
    print("\nTesting dependencies...")
    
    required_packages = [
        'celery',
        'concurrent.futures',
        'hashlib',
        'asyncio',
        'PIL',
        'numpy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} available")
        except ImportError:
            print(f"✗ {package} missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("OPTIMIZED AI PROCESSING SERVICES TEST")
    print("=" * 60)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Imports", test_imports),
        ("In-Memory Cache", test_in_memory_cache),
        ("Service Initialization", test_service_initialization),
        ("Celery Configuration", test_celery_configuration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        icon = "✓" if result else "✗"
        print(f"{icon} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Optimized services are ready to use.")
        print("\nNext steps:")
        print("1. Start Celery worker: celery -A src.services.optimized_background_tasks worker --loglevel=info")
        print("2. Access optimized dashboard: /optimized-dashboard")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix the issues before using optimized services.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())