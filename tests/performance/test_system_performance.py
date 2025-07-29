"""
Performance tests for the processing system

Tests performance characteristics, load handling, and optimization
of the processing system components.
"""

import pytest
import time
import tempfile
import os
import threading
import concurrent.futures
from statistics import mean, median
from unittest.mock import Mock, patch

from src.services.file_processing_service import FileProcessingService
from src.services.consolidated_llm_service import ConsolidatedLLMService
from src.services.cache_manager import cache_manager
from src.services.performance_monitor import performance_monitor

class TestFileProcessingPerformance:
    """Performance tests for file processing"""
    
    @pytest.fixture
    def large_text_file(self):
        """Create a large text file for performance testing"""
        content = "This is a test sentence. " * 1000  # ~25KB file
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        yield temp_path
        
        try:
            os.unlink(temp_path)
        except OSError:
            pass
    
    @pytest.fixture
    def file_service(self):
        """Create file processing service for testing"""
        return FileProcessingService()
    
    def test_single_file_processing_performance(self, file_service, large_text_file):
        """Test performance of processing a single large file"""
        file_info = {
            'name': 'large_test.txt',
            'size': os.path.getsize(large_text_file),
            'type': 'txt'
        }
        
        start_time = time.time()
        result = file_service.process_file_with_fallback(large_text_file, file_info)
        processing_time = time.time() - start_time
        
        assert result['success'] is True
        assert processing_time < 5.0  # Should process within 5 seconds
        assert result['processing_duration_ms'] < 5000
        
        # Check quality metrics are calculated efficiently
        assert 'quality_metrics' in result
        assert result['content_quality_score'] > 0
    
    def test_batch_file_processing_performance(self, file_service):
        """Test performance of processing multiple files"""
        # Create multiple test files
        test_files = []
        for i in range(10):
            content = f"Test file {i} content. " * 100
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                test_files.append(f.name)
        
        try:
            start_time = time.time()
            results = []
            
            for i, file_path in enumerate(test_files):
                file_info = {
                    'name': f'batch_test_{i}.txt',
                    'size': os.path.getsize(file_path),
                    'type': 'txt'
                }
                
                result = file_service.process_file_with_fallback(file_path, file_info)
                results.append(result)
            
            total_time = time.time() - start_time
            
            # All files should process successfully
            assert all(r['success'] for r in results)
            
            # Average processing time per file should be reasonable
            avg_time_per_file = total_time / len(test_files)
            assert avg_time_per_file < 2.0  # Less than 2 seconds per file
            
            # Check processing times are consistent
            processing_times = [r['processing_duration_ms'] for r in results]
            time_variance = max(processing_times) - min(processing_times)
            assert time_variance < 5000  # Less than 5 second variance
            
        finally:
            # Cleanup
            for file_path in test_files:
                try:
                    os.unlink(file_path)
                except OSError:
                    pass
    
    def test_concurrent_file_processing_performance(self, file_service):
        """Test performance under concurrent load"""
        # Create test files
        test_files = []
        for i in range(20):
            content = f"Concurrent test file {i}. " * 50
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                test_files.append(f.name)
        
        try:
            def process_file(file_path, file_index):
                file_info = {
                    'name': f'concurrent_{file_index}.txt',
                    'size': os.path.getsize(file_path),
                    'type': 'txt'
                }
                
                start_time = time.time()
                result = file_service.process_file_with_fallback(file_path, file_info)
                processing_time = time.time() - start_time
                
                return result, processing_time
            
            # Process files concurrently
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(process_file, file_path, i)
                    for i, file_path in enumerate(test_files)
                ]
                
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            total_time = time.time() - start_time
            
            # All files should process successfully
            assert all(result[0]['success'] for result in results)
            
            # Concurrent processing should be faster than sequential
            assert total_time < 15.0  # Should complete within 15 seconds
            
            # Check individual processing times
            processing_times = [result[1] for result in results]
            avg_processing_time = mean(processing_times)
            assert avg_processing_time < 3.0  # Average under 3 seconds
            
        finally:
            # Cleanup
            for file_path in test_files:
                try:
                    os.unlink(file_path)
                except OSError:
                    pass
    
    def test_memory_usage_during_processing(self, file_service):
        """Test memory usage during file processing"""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Create and process multiple large files
        for i in range(5):
            content = "Large file content. " * 5000  # ~100KB each
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            try:
                file_info = {
                    'name': f'memory_test_{i}.txt',
                    'size': len(content),
                    'type': 'txt'
                }
                
                result = file_service.process_file_with_fallback(temp_path, file_info)
                assert result['success'] is True
                
            finally:
                os.unlink(temp_path)
        
        # Force garbage collection
        gc.collect()
        
        # Check memory usage hasn't grown excessively
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024
    
    def test_quality_assessment_performance(self, file_service):
        """Test performance of quality assessment algorithms"""
        # Create files with different quality characteristics
        test_cases = [
            ("high_quality", "This is a well-structured document with proper grammar. " * 100),
            ("medium_quality", "This document has some issues but is readable. " * 100),
            ("low_quality", "bad grammar no punctuation " * 100),
            ("very_long", "A " * 10000),  # Very long content
        ]
        
        processing_times = []
        
        for test_name, content in test_cases:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            try:
                file_info = {
                    'name': f'{test_name}.txt',
                    'size': len(content),
                    'type': 'txt'
                }
                
                start_time = time.time()
                result = file_service.process_file_with_fallback(temp_path, file_info)
                processing_time = time.time() - start_time
                
                processing_times.append(processing_time)
                
                assert result['success'] is True
                assert 'content_quality_score' in result
                assert 'quality_metrics' in result
                
                # Quality assessment should complete quickly
                assert processing_time < 2.0
                
            finally:
                os.unlink(temp_path)
        
        # Processing times should be consistent
        avg_time = mean(processing_times)
        max_time = max(processing_times)
        assert max_time < avg_time * 3  # No single case should be 3x slower

class TestCachePerformance:
    """Performance tests for caching system"""
    
    def test_cache_hit_performance(self):
        """Test cache hit performance"""
        # Warm up cache
        for i in range(100):
            cache_manager.set(f"key_{i}", f"value_{i}")
        
        # Measure cache hit performance
        start_time = time.time()
        for i in range(100):
            value = cache_manager.get(f"key_{i}")
            assert value == f"value_{i}"
        
        hit_time = time.time() - start_time
        
        # Cache hits should be very fast
        assert hit_time < 0.1  # Less than 100ms for 100 hits
        avg_hit_time = hit_time / 100
        assert avg_hit_time < 0.001  # Less than 1ms per hit
    
    def test_cache_miss_performance(self):
        """Test cache miss performance"""
        # Clear cache
        cache_manager.clear()
        
        # Measure cache miss performance
        start_time = time.time()
        for i in range(100):
            value = cache_manager.get(f"nonexistent_key_{i}")
            assert value is None
        
        miss_time = time.time() - start_time
        
        # Cache misses should still be fast
        assert miss_time < 0.5  # Less than 500ms for 100 misses
        avg_miss_time = miss_time / 100
        assert avg_miss_time < 0.005  # Less than 5ms per miss
    
    def test_cache_set_performance(self):
        """Test cache set performance"""
        # Clear cache
        cache_manager.clear()
        
        # Measure cache set performance
        start_time = time.time()
        for i in range(1000):
            success = cache_manager.set(f"perf_key_{i}", f"perf_value_{i}")
            assert success is True
        
        set_time = time.time() - start_time
        
        # Cache sets should be reasonably fast
        assert set_time < 2.0  # Less than 2 seconds for 1000 sets
        avg_set_time = set_time / 1000
        assert avg_set_time < 0.002  # Less than 2ms per set
    
    def test_cache_concurrent_access(self):
        """Test cache performance under concurrent access"""
        cache_manager.clear()
        
        def cache_worker(worker_id, operations=100):
            for i in range(operations):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                
                # Set value
                cache_manager.set(key, value)
                
                # Get value
                retrieved = cache_manager.get(key)
                assert retrieved == value
        
        # Run concurrent cache operations
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(cache_worker, worker_id)
                for worker_id in range(10)
            ]
            
            for future in concurrent.futures.as_completed(futures):
                future.result()
        
        concurrent_time = time.time() - start_time
        
        # Concurrent operations should complete reasonably quickly
        assert concurrent_time < 5.0  # Less than 5 seconds for all operations
    
    def test_cache_memory_efficiency(self):
        """Test cache memory efficiency"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Fill cache with data
        for i in range(10000):
            large_value = "x" * 1000  # 1KB per entry
            cache_manager.set(f"memory_key_{i}", large_value)
        
        # Check memory usage
        filled_memory = process.memory_info().rss
        memory_used = filled_memory - initial_memory
        
        # Clear cache
        cache_manager.clear()
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_freed = filled_memory - final_memory
        
        # Memory should be efficiently managed
        # 10MB of data should not use more than 50MB of memory
        assert memory_used < 50 * 1024 * 1024
        
        # Most memory should be freed after clearing
        assert memory_freed > memory_used * 0.5

class TestPerformanceMonitoringOverhead:
    """Test performance monitoring overhead"""
    
    def test_monitoring_overhead(self):
        """Test that performance monitoring has minimal overhead"""
        # Clear previous metrics
        performance_monitor.clear_metrics()
        
        def test_operation():
            time.sleep(0.001)  # Simulate 1ms operation
            return "result"
        
        # Measure operation without monitoring
        start_time = time.time()
        for _ in range(100):
            test_operation()
        unmonitored_time = time.time() - start_time
        
        # Measure operation with monitoring
        start_time = time.time()
        for i in range(100):
            performance_monitor.track_operation(f"test_op_{i}", 0.001, success=True)
        monitored_time = time.time() - start_time
        
        # Monitoring overhead should be minimal
        overhead = monitored_time - unmonitored_time
        overhead_percentage = (overhead / unmonitored_time) * 100
        
        assert overhead_percentage < 50  # Less than 50% overhead
        assert overhead < 0.5  # Less than 500ms total overhead
    
    def test_metrics_collection_performance(self):
        """Test performance of metrics collection"""
        # Generate metrics
        for i in range(1000):
            performance_monitor.track_operation(f"perf_test_{i % 10}", 0.001, success=True)
        
        # Measure metrics retrieval performance
        start_time = time.time()
        summary = performance_monitor.get_performance_summary()
        retrieval_time = time.time() - start_time
        
        assert retrieval_time < 0.1  # Less than 100ms
        assert summary['total_operations'] > 0
        
        # Measure specific metrics retrieval
        start_time = time.time()
        stats = performance_monitor.get_operation_stats("perf_test_0")
        specific_retrieval_time = time.time() - start_time
        
        assert specific_retrieval_time < 0.01  # Less than 10ms
        assert stats is not None

class TestSystemLoadPerformance:
    """Test system performance under various load conditions"""
    
    def test_sustained_load_performance(self):
        """Test performance under sustained load"""
        file_service = FileProcessingService()
        
        # Create test content
        test_content = "Sustained load test content. " * 100
        
        processing_times = []
        success_count = 0
        
        start_time = time.time()
        while time.time() - start_time < 10:  # Run for 10 seconds
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(test_content)
                temp_path = f.name
            
            try:
                file_info = {
                    'name': 'sustained_load.txt',
                    'size': len(test_content),
                    'type': 'txt'
                }
                
                op_start = time.time()
                result = file_service.process_file_with_fallback(temp_path, file_info)
                op_time = time.time() - op_start
                
                processing_times.append(op_time)
                if result['success']:
                    success_count += 1
                    
            finally:
                os.unlink(temp_path)
        
        # Analyze performance under sustained load
        total_operations = len(processing_times)
        success_rate = success_count / total_operations
        avg_processing_time = mean(processing_times)
        median_processing_time = median(processing_times)
        
        assert total_operations > 10  # Should process multiple files
        assert success_rate > 0.95  # 95% success rate
        assert avg_processing_time < 2.0  # Average under 2 seconds
        assert median_processing_time < 1.5  # Median under 1.5 seconds
    
    def test_resource_cleanup_performance(self):
        """Test that resources are cleaned up efficiently"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        initial_handles = process.num_handles() if hasattr(process, 'num_handles') else 0
        
        file_service = FileProcessingService()
        
        # Process many files to test resource cleanup
        for i in range(50):
            content = f"Resource cleanup test {i}. " * 100
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            try:
                file_info = {
                    'name': f'cleanup_test_{i}.txt',
                    'size': len(content),
                    'type': 'txt'
                }
                
                result = file_service.process_file_with_fallback(temp_path, file_info)
                assert result['success'] is True
                
            finally:
                os.unlink(temp_path)
        
        # Force cleanup
        gc.collect()
        
        # Check resource usage
        final_memory = process.memory_info().rss
        final_handles = process.num_handles() if hasattr(process, 'num_handles') else 0
        
        memory_increase = final_memory - initial_memory
        handle_increase = final_handles - initial_handles
        
        # Resource usage should not grow excessively
        assert memory_increase < 100 * 1024 * 1024  # Less than 100MB increase
        assert handle_increase < 100  # Less than 100 additional handles

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])