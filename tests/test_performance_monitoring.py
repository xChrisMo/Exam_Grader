"""
Tests for performance monitoring and metrics collection

Tests the PerformanceMonitor, CacheManager, and related
performance tracking infrastructure.
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.services.performance_monitor import (
    PerformanceMonitor, OperationTracker, MetricType, AlertLevel, 
    PerformanceMetric, OperationStats, PerformanceAlert, AlertRule
)
from src.services.cache_manager import CacheManager, CacheType, CachePolicy

class TestPerformanceMonitor:
    """Test cases for PerformanceMonitor"""
    
    @pytest.fixture
    def monitor(self):
        """Create PerformanceMonitor instance for testing"""
        return PerformanceMonitor(max_metrics=100, max_alerts=50)
    
    def test_initialization(self, monitor):
        """Test monitor initialization"""
        assert monitor is not None
        assert monitor.max_metrics == 100
        assert monitor.max_alerts == 50
        assert len(monitor._operation_stats) == 0
        assert len(monitor._metrics) == 0
    
    def test_track_operation_success(self, monitor):
        """Test tracking successful operations"""
        monitor.track_operation("test_operation", 1.5, success=True)
        
        stats = monitor.get_operation_stats("test_operation")
        assert stats is not None
        assert stats['total_requests'] == 1
        assert stats['successful_requests'] == 1
        assert stats['failed_requests'] == 0
        assert stats['average_duration'] == 1.5
        assert stats['success_rate'] == 1.0
    
    def test_track_operation_failure(self, monitor):
        """Test tracking failed operations"""
        monitor.track_operation("test_operation", 2.0, success=False)
        
        stats = monitor.get_operation_stats("test_operation")
        assert stats is not None
        assert stats['total_requests'] == 1
        assert stats['successful_requests'] == 0
        assert stats['failed_requests'] == 1
        assert stats['success_rate'] == 0.0
        assert stats['error_rate'] == 1.0
    
    def test_track_multiple_operations(self, monitor):
        """Test tracking multiple operations"""
        # Track multiple successful operations
        for i in range(5):
            monitor.track_operation("test_operation", 1.0 + i * 0.1, success=True)
        
        # Track one failed operation
        monitor.track_operation("test_operation", 3.0, success=False)
        
        stats = monitor.get_operation_stats("test_operation")
        assert stats['total_requests'] == 6
        assert stats['successful_requests'] == 5
        assert stats['failed_requests'] == 1
        assert stats['success_rate'] == 5/6
        assert stats['error_rate'] == 1/6
        assert 1.0 <= stats['average_duration'] <= 2.0
    
    def test_track_custom_metric(self, monitor):
        """Test tracking custom metrics"""
        monitor.track_metric("test_service", MetricType.MEMORY_USAGE, 75.5, 
                           metadata={'unit': 'percent'})
        
        metrics = monitor.get_metrics(operation="test_service", 
                                    metric_type=MetricType.MEMORY_USAGE)
        assert len(metrics) == 1
        assert metrics[0]['metric_type'] == MetricType.MEMORY_USAGE.value
        assert metrics[0]['value'] == 75.5
    
    def test_performance_summary(self, monitor):
        """Test performance summary generation"""
        # Add some test data
        monitor.track_operation("op1", 1.0, success=True)
        monitor.track_operation("op1", 2.0, success=False)
        monitor.track_operation("op2", 0.5, success=True)
        
        summary = monitor.get_performance_summary()
        
        assert summary['total_operations'] == 2  # Two different operations
        assert summary['total_requests'] == 3
        assert summary['total_errors'] == 1
        assert summary['overall_error_rate'] == 1/3
        assert len(summary['slowest_operations']) <= 5
        assert len(summary['error_prone_operations']) <= 5
    
    def test_alert_rule_management(self, monitor):
        """Test alert rule management"""
        # Add alert rule
        monitor.add_alert_rule(
            operation="test_operation",
            metric_type=MetricType.DURATION,
            threshold=5.0,
            level=AlertLevel.WARNING,
            condition="greater_than"
        )
        
        # Trigger alert
        monitor.track_operation("test_operation", 6.0, success=True)
        
        alerts = monitor.get_alerts(level=AlertLevel.WARNING)
        assert len(alerts) >= 1
        
        # Check alert content
        alert = alerts[0]
        assert alert['operation'] == 'test_operation'
        assert alert['level'] == AlertLevel.WARNING.value
        assert alert['value'] == 6.0
        assert alert['threshold'] == 5.0
    
    def test_alert_cooldown(self, monitor):
        """Test alert cooldown mechanism"""
        # Add alert rule with short cooldown
        monitor.add_alert_rule(
            operation="test_operation",
            metric_type=MetricType.DURATION,
            threshold=1.0,
            level=AlertLevel.WARNING,
            condition="greater_than",
            cooldown_seconds=1
        )
        
        # Trigger alert twice quickly
        monitor.track_operation("test_operation", 2.0, success=True)
        monitor.track_operation("test_operation", 2.0, success=True)
        
        alerts = monitor.get_alerts(level=AlertLevel.WARNING)
        # Should only have one alert due to cooldown
        operation_alerts = [a for a in alerts if a['operation'] == 'test_operation']
        assert len(operation_alerts) == 1
    
    def test_metrics_filtering(self, monitor):
        """Test metrics filtering functionality"""
        # Add metrics with different types and operations
        monitor.track_metric("service1", MetricType.DURATION, 1.0)
        monitor.track_metric("service1", MetricType.MEMORY_USAGE, 50.0)
        monitor.track_metric("service2", MetricType.DURATION, 2.0)
        
        # Filter by operation
        service1_metrics = monitor.get_metrics(operation="service1")
        assert len(service1_metrics) == 2
        
        # Filter by metric type
        duration_metrics = monitor.get_metrics(metric_type=MetricType.DURATION)
        assert len(duration_metrics) == 2
        
        # Filter by both
        service1_duration = monitor.get_metrics(operation="service1", 
                                              metric_type=MetricType.DURATION)
        assert len(service1_duration) == 1
        assert service1_duration[0]['value'] == 1.0
    
    def test_metrics_size_limit(self, monitor):
        """Test metrics size limit enforcement"""
        # Fill up metrics to the limit
        for i in range(monitor.max_metrics + 10):
            monitor.track_metric(f"service_{i}", MetricType.DURATION, float(i))
        
        # Should not exceed max_metrics
        all_metrics = monitor.get_metrics()
        assert len(all_metrics) <= monitor.max_metrics
    
    def test_clear_metrics(self, monitor):
        """Test metrics clearing functionality"""
        # Add some metrics
        monitor.track_operation("test_op", 1.0, success=True)
        monitor.track_metric("test_service", MetricType.DURATION, 2.0)
        
        # Clear specific operation
        monitor.clear_metrics(operation="test_op")
        
        # Should not find the operation
        stats = monitor.get_operation_stats("test_op")
        assert stats is None
        
        # But other metrics should remain
        metrics = monitor.get_metrics(operation="test_service")
        assert len(metrics) == 1
        
        # Clear all metrics
        monitor.clear_metrics()
        all_metrics = monitor.get_metrics()
        assert len(all_metrics) == 0

class TestOperationTracker:
    """Test cases for OperationTracker context manager"""
    
    @pytest.fixture
    def monitor(self):
        return PerformanceMonitor()
    
    def test_successful_operation_tracking(self, monitor):
        """Test tracking successful operations with context manager"""
        with OperationTracker(monitor, "test_operation") as tracker:
            time.sleep(0.01)  # Simulate work
            tracker.set_metadata("test_key", "test_value")
        
        stats = monitor.get_operation_stats("test_operation")
        assert stats is not None
        assert stats['successful_requests'] == 1
        assert stats['average_duration'] > 0
    
    def test_failed_operation_tracking(self, monitor):
        """Test tracking failed operations with context manager"""
        try:
            with OperationTracker(monitor, "test_operation") as tracker:
                tracker.mark_failure()
                raise ValueError("Test error")
        except ValueError:
            pass
        
        stats = monitor.get_operation_stats("test_operation")
        assert stats is not None
        assert stats['failed_requests'] == 1
        assert stats['success_rate'] == 0.0
    
    def test_exception_handling(self, monitor):
        """Test that exceptions are properly handled"""
        try:
            with OperationTracker(monitor, "test_operation"):
                raise RuntimeError("Test exception")
        except RuntimeError:
            pass
        
        stats = monitor.get_operation_stats("test_operation")
        assert stats is not None
        assert stats['failed_requests'] == 1

class TestCacheManager:
    """Test cases for CacheManager"""
    
    @pytest.fixture
    def cache_manager(self):
        """Create CacheManager instance for testing"""
        return CacheManager(cache_dir="test_cache")
    
    def test_initialization(self, cache_manager):
        """Test cache manager initialization"""
        assert cache_manager is not None
        assert len(cache_manager._levels) > 0
        
        # Check default cache levels
        assert 'l1_memory' in cache_manager._levels
        assert 'l2_memory' in cache_manager._levels
        assert 'l3_disk' in cache_manager._levels
    
    def test_basic_cache_operations(self, cache_manager):
        """Test basic cache get/set operations"""
        # Test set and get
        success = cache_manager.set("test_key", "test_value")
        assert success is True
        
        value = cache_manager.get("test_key")
        assert value == "test_value"
        
        # Test non-existent key
        value = cache_manager.get("non_existent_key")
        assert value is None
    
    def test_cache_with_ttl(self, cache_manager):
        """Test cache with time-to-live"""
        # Set with short TTL
        cache_manager.set("ttl_key", "ttl_value", ttl=1)
        
        # Should be available immediately
        value = cache_manager.get("ttl_key")
        assert value == "ttl_value"
        
        time.sleep(1.1)
        
        # Should be expired
        value = cache_manager.get("ttl_key")
        assert value is None
    
    def test_cache_level_selection(self, cache_manager):
        """Test automatic cache level selection based on size"""
        # Small value should go to L1
        small_value = "x" * 100
        cache_manager.set("small_key", small_value)
        
        # Large value should go to higher level
        large_value = "x" * 100000
        cache_manager.set("large_key", large_value)
        
        # Both should be retrievable
        assert cache_manager.get("small_key") == small_value
        assert cache_manager.get("large_key") == large_value
    
    def test_specific_cache_level(self, cache_manager):
        """Test setting/getting from specific cache level"""
        # Set in specific level
        success = cache_manager.set("level_key", "level_value", cache_type="l1_memory")
        assert success is True
        
        value = cache_manager.get("level_key", cache_type="l1_memory")
        assert value == "level_value"
        
        # Should not be in other levels
        value = cache_manager.get("level_key", cache_type="l2_memory")
        assert value is None
    
    def test_cache_deletion(self, cache_manager):
        """Test cache deletion"""
        # Set value
        cache_manager.set("delete_key", "delete_value")
        assert cache_manager.get("delete_key") == "delete_value"
        
        deleted_count = cache_manager.delete("delete_key")
        assert deleted_count >= 1
        
        # Should be gone
        assert cache_manager.get("delete_key") is None
    
    def test_cache_clearing(self, cache_manager):
        """Test cache clearing"""
        # Set multiple values
        cache_manager.set("clear_key1", "value1")
        cache_manager.set("clear_key2", "value2")
        
        # Clear all
        cache_manager.clear()
        
        # Should be empty
        assert cache_manager.get("clear_key1") is None
        assert cache_manager.get("clear_key2") is None
    
    def test_expired_cleanup(self, cache_manager):
        """Test expired entry cleanup"""
        # Set entries with short TTL
        cache_manager.set("expire1", "value1", ttl=1)
        cache_manager.set("expire2", "value2", ttl=1)
        
        time.sleep(1.1)
        
        # Run cleanup
        removed_count = cache_manager.clear_expired()
        assert removed_count >= 2
    
    def test_cache_statistics(self, cache_manager):
        """Test cache statistics"""
        # Generate some cache activity
        cache_manager.set("stats_key1", "value1")
        cache_manager.set("stats_key2", "value2")
        cache_manager.get("stats_key1")  # Hit
        cache_manager.get("nonexistent")  # Miss
        
        stats = cache_manager.get_stats()
        
        assert 'levels' in stats
        assert 'total_hits' in stats
        assert 'total_misses' in stats
        assert 'total_entries' in stats
        assert 'overall_hit_rate' in stats
        
        # Should have some hits and misses
        assert stats['total_hits'] >= 1
        assert stats['total_misses'] >= 1
    
    def test_cache_level_management(self, cache_manager):
        """Test adding and removing cache levels"""
        # Add custom cache level
        cache_manager.add_cache_level(
            name="custom_level",
            cache_type=CacheType.MEMORY,
            max_size=100,
            policy=CachePolicy.LRU
        )
        
        assert 'custom_level' in cache_manager._levels
        
        # Use custom level
        cache_manager.set("custom_key", "custom_value", cache_type="custom_level")
        value = cache_manager.get("custom_key", cache_type="custom_level")
        assert value == "custom_value"
        
        # Remove custom level
        removed = cache_manager.remove_cache_level("custom_level")
        assert removed is True
        assert 'custom_level' not in cache_manager._levels

class TestPerformanceIntegration:
    """Integration tests for performance monitoring components"""
    
    @pytest.fixture
    def monitor(self):
        return PerformanceMonitor()
    
    @pytest.fixture
    def cache_manager(self):
        return CacheManager()
    
    def test_cache_performance_monitoring(self, monitor, cache_manager):
        """Test monitoring cache performance"""
        with OperationTracker(monitor, "cache_set"):
            cache_manager.set("perf_key", "perf_value")
        
        with OperationTracker(monitor, "cache_get"):
            value = cache_manager.get("perf_key")
            assert value == "perf_value"
        
        # Check that operations were tracked
        set_stats = monitor.get_operation_stats("cache_set")
        get_stats = monitor.get_operation_stats("cache_get")
        
        assert set_stats is not None
        assert get_stats is not None
        assert set_stats['successful_requests'] == 1
        assert get_stats['successful_requests'] == 1
    
    def test_performance_alerting_integration(self, monitor):
        """Test performance alerting with real operations"""
        monitor.add_alert_rule(
            operation="slow_operation",
            metric_type=MetricType.DURATION,
            threshold=0.1,
            level=AlertLevel.WARNING,
            condition="greater_than"
        )
        
        # Perform slow operation
        with OperationTracker(monitor, "slow_operation"):
            time.sleep(0.15)  # Exceed threshold
        
        # Check that alert was triggered
        alerts = monitor.get_alerts(level=AlertLevel.WARNING)
        slow_alerts = [a for a in alerts if a['operation'] == 'slow_operation']
        assert len(slow_alerts) >= 1
    
    def test_comprehensive_monitoring_scenario(self, monitor, cache_manager):
        """Test comprehensive monitoring scenario"""
        # Set up alerts
        monitor.add_alert_rule(
            operation="cache_miss",
            metric_type=MetricType.ERROR_RATE,
            threshold=0.5,
            level=AlertLevel.ERROR,
            condition="greater_than"
        )
        
        # Simulate mixed cache operations
        for i in range(10):
            key = f"key_{i}"
            
            # Try to get (will miss first time)
            with OperationTracker(monitor, "cache_get") as tracker:
                value = cache_manager.get(key)
                if value is None:
                    tracker.mark_failure()  # Cache miss
            
            # Set the value
            with OperationTracker(monitor, "cache_set"):
                cache_manager.set(key, f"value_{i}")
            
            # Get again (should hit)
            with OperationTracker(monitor, "cache_get"):
                value = cache_manager.get(key)
                assert value == f"value_{i}"
        
        # Check statistics
        get_stats = monitor.get_operation_stats("cache_get")
        set_stats = monitor.get_operation_stats("cache_set")
        
        assert get_stats['total_requests'] == 20  # 10 misses + 10 hits
        assert set_stats['total_requests'] == 10
        assert get_stats['error_rate'] == 0.5  # 50% miss rate
        
        # Check cache statistics
        cache_stats = cache_manager.get_stats()
        assert cache_stats['total_entries'] == 10

if __name__ == '__main__':
    pytest.main([__file__, '-v'])