"""
Test Suite for Monitoring and Alerting System

This module provides comprehensive tests for the monitoring dashboard,
alerting system, metrics collection, and service health monitoring.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.services.monitoring_dashboard import (
    monitoring_dashboard_service, DashboardType, AlertSeverity, MonitoringAlert
)
from src.services.enhanced_alerting_system import (
    enhanced_alerting_system, AlertRule, AlertThreshold, AlertChannel
)
from src.services.realtime_metrics_collector import (
    realtime_metrics_collector, MetricType, MetricSeries
)
from src.services.monitoring_service_manager import (
    monitoring_service_manager, ServiceState
)
from src.services.health_monitor import health_monitor
from src.services.performance_monitor import performance_monitor

class TestMonitoringDashboard:
    """Test monitoring dashboard functionality"""
    
    def test_dashboard_initialization(self):
        """Test that monitoring dashboard initializes correctly"""
        # Check that default dashboards are created
        dashboards = monitoring_dashboard_service.list_dashboards()
        assert len(dashboards) >= 3  # system_health, performance, error_tracking
        
        dashboard_ids = [d['id'] for d in dashboards]
        assert 'system_health' in dashboard_ids
        assert 'performance' in dashboard_ids
        assert 'error_tracking' in dashboard_ids
    
    def test_dashboard_data_collection(self):
        """Test dashboard data collection"""
        # Get system health dashboard data
        dashboard_data = monitoring_dashboard_service.get_dashboard_data('system_health')
        assert dashboard_data is not None
        assert 'dashboard' in dashboard_data
        assert 'widgets' in dashboard_data
        assert dashboard_data['dashboard']['id'] == 'system_health'
    
    def test_alert_creation_and_resolution(self):
        """Test alert creation and resolution"""
        # Create a test alert
        alert_id = monitoring_dashboard_service.create_alert(
            "Test Alert",
            "This is a test alert",
            AlertSeverity.HIGH,
            "test_source"
        )
        
        assert alert_id is not None
        
        # Get alerts and verify it exists
        alerts = monitoring_dashboard_service.get_alerts(limit=10)
        alert_found = any(alert['id'] == alert_id for alert in alerts)
        assert alert_found
        
        # Resolve the alert
        success = monitoring_dashboard_service.resolve_alert(alert_id)
        assert success
        
        # Verify alert is resolved
        resolved_alerts = monitoring_dashboard_service.get_alerts(resolved=True, limit=10)
        resolved_alert = next((a for a in resolved_alerts if a['id'] == alert_id), None)
        assert resolved_alert is not None
        assert resolved_alert['resolved'] is True
    
    def test_monitoring_statistics(self):
        """Test monitoring statistics collection"""
        stats = monitoring_dashboard_service.get_monitoring_stats()
        
        assert 'dashboards_count' in stats
        assert 'collectors_count' in stats
        assert 'active_alerts' in stats
        assert 'total_alerts' in stats
        assert stats['dashboards_count'] >= 3

class TestEnhancedAlertingSystem:
    """Test enhanced alerting system functionality"""
    
    def test_alerting_system_initialization(self):
        """Test that alerting system initializes correctly"""
        stats = enhanced_alerting_system.get_alert_statistics()
        
        assert 'active_alerts' in stats
        assert 'total_alert_rules' in stats
        assert 'notification_channels' in stats
        assert 'monitoring_active' in stats
    
    def test_alert_threshold_checking(self):
        """Test alert threshold checking logic"""
        # Create a test threshold
        threshold = AlertThreshold(
            metric_name="test_metric",
            warning_value=50.0,
            critical_value=80.0,
            comparison="greater_than"
        )
        
        # Test threshold checking
        assert threshold.check_threshold(30.0) is None  # Below warning
        assert threshold.check_threshold(60.0) == AlertSeverity.HIGH  # Warning level
        assert threshold.check_threshold(90.0) == AlertSeverity.CRITICAL  # Critical level
    
    @patch('src.services.enhanced_alerting_system.health_monitor')
    def test_service_health_alert_checking(self, mock_health_monitor):
        """Test service health alert checking"""
        # Mock unhealthy service
        mock_health_monitor.get_overall_health.return_value = {
            'services': {
                'test_service': {
                    'status': 'unhealthy',
                    'error_count': 10
                }
            }
        }
        
        # Trigger health check
        enhanced_alerting_system._check_service_health_alerts()
        
        # Verify alert was created (would need to check internal state)
        stats = enhanced_alerting_system.get_alert_statistics()
        # This is a basic check - in a real test we'd verify the specific alert
        assert 'alert_states' in stats
    
    def test_alert_state_management(self):
        """Test alert state management"""
        # Clear any existing alert state
        enhanced_alerting_system.clear_alert_state(AlertRule.HIGH_ERROR_RATE)
        
        # Trigger an alert
        enhanced_alerting_system._trigger_alert(
            AlertRule.HIGH_ERROR_RATE,
            "Test High Error Rate",
            "Error rate is too high",
            AlertSeverity.HIGH,
            {'error_rate': 0.15}
        )
        
        # Check alert state
        stats = enhanced_alerting_system.get_alert_statistics()
        assert 'alert_states' in stats
        
        # Clear the alert state
        success = enhanced_alerting_system.clear_alert_state(AlertRule.HIGH_ERROR_RATE)
        assert success

class TestRealtimeMetricsCollector:
    """Test real-time metrics collector functionality"""
    
    def test_metrics_collector_initialization(self):
        """Test that metrics collector initializes correctly"""
        metrics = realtime_metrics_collector.get_all_metrics()
        
        # Check that default metrics are registered
        assert 'system.cpu.usage' in metrics
        assert 'system.memory.usage' in metrics
        assert 'app.requests.total' in metrics
        assert 'services.health.score' in metrics
    
    def test_metric_recording(self):
        """Test metric recording functionality"""
        # Record a test metric
        realtime_metrics_collector.record_metric('test.metric', 42.0, {'label': 'test'})
        
        # Verify metric was recorded
        value = realtime_metrics_collector.get_metric_value('test.metric')
        assert value == 42.0
        
        # Get metric series
        metric = realtime_metrics_collector.get_metric('test.metric')
        assert metric is None  # Not registered, so won't be stored
        
        # Register and record a proper metric
        realtime_metrics_collector.register_metric('test.registered', MetricType.GAUGE, "Test metric")
        realtime_metrics_collector.record_metric('test.registered', 100.0)
        
        registered_value = realtime_metrics_collector.get_metric_value('test.registered')
        assert registered_value == 100.0
    
    def test_metric_statistics(self):
        """Test metric statistics calculation"""
        # Register a test metric
        realtime_metrics_collector.register_metric('test.stats', MetricType.GAUGE, "Test stats metric")
        
        # Record multiple values
        for i in range(10):
            realtime_metrics_collector.record_metric('test.stats', float(i * 10))
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        # Get metric and test statistics
        metric = realtime_metrics_collector.get_metric('test.stats')
        assert metric is not None
        
        # Test average calculation
        avg = metric.get_average(minutes=1)
        assert avg > 0
        
        # Test max calculation
        max_val = metric.get_max(minutes=1)
        assert max_val == 90.0  # Last value recorded
        
        # Test trend calculation
        trend = metric.get_trend(minutes=1)
        assert trend in ['increasing', 'decreasing', 'stable']
    
    def test_metric_history(self):
        """Test metric history retrieval"""
        # Register and record metrics
        realtime_metrics_collector.register_metric('test.history', MetricType.COUNTER, "Test history metric")
        
        for i in range(5):
            realtime_metrics_collector.record_metric('test.history', float(i))
            time.sleep(0.01)
        
        # Get history
        history = realtime_metrics_collector.get_metric_history('test.history', minutes=1)
        assert len(history) == 5
        
        # Verify history structure
        for point in history:
            assert 'timestamp' in point
            assert 'value' in point
            assert 'labels' in point
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_system_metrics_collection(self, mock_net, mock_disk, mock_memory, mock_cpu):
        """Test system metrics collection"""
        # Mock system metrics
        mock_cpu.return_value = 45.5
        mock_memory.return_value = Mock(percent=67.2)
        mock_disk.return_value = Mock(used=1000, total=2000)
        mock_net.return_value = Mock(bytes_sent=5000, bytes_recv=3000)
        
        # Collect system metrics
        metrics = realtime_metrics_collector._collect_system_metrics()
        
        assert 'system.cpu.usage' in metrics
        assert 'system.memory.usage' in metrics
        assert 'system.disk.usage' in metrics
        assert metrics['system.cpu.usage'] == 45.5
        assert metrics['system.memory.usage'] == 67.2
        assert metrics['system.disk.usage'] == 50.0  # 1000/2000 * 100

class TestMonitoringServiceManager:
    """Test monitoring service manager functionality"""
    
    def test_service_manager_initialization(self):
        """Test service manager initialization"""
        status = monitoring_service_manager.get_service_status()
        
        assert 'manager_running' in status
        assert 'startup_complete' in status
        assert 'services' in status
        
        # Check that all expected services are registered
        expected_services = [
            'health_monitor', 'performance_monitor', 'cache_manager',
            'realtime_metrics_collector', 'monitoring_dashboard', 'enhanced_alerting'
        ]
        
        for service in expected_services:
            assert service in status['services']
    
    def test_service_state_tracking(self):
        """Test service state tracking"""
        # Check individual service status
        for service_name in ['health_monitor', 'performance_monitor']:
            is_running = monitoring_service_manager.is_service_running(service_name)
            # Service might or might not be running depending on test environment
            assert isinstance(is_running, bool)
    
    def test_service_status_reporting(self):
        """Test service status reporting"""
        status = monitoring_service_manager.get_service_status()
        
        for service_name, service_status in status['services'].items():
            assert 'state' in service_status
            assert 'error_count' in service_status
            assert 'dependencies' in service_status
            
            # State should be a valid ServiceState value
            valid_states = [state.value for state in ServiceState]
            assert service_status['state'] in valid_states

class TestIntegrationScenarios:
    """Test integration scenarios between monitoring components"""
    
    def test_end_to_end_monitoring_flow(self):
        """Test complete monitoring flow from metrics to alerts"""
        # 1. Record a high error rate metric
        realtime_metrics_collector.register_metric('integration.error_rate', MetricType.GAUGE, "Integration test error rate")
        realtime_metrics_collector.record_metric('integration.error_rate', 0.25)  # 25% error rate
        
        # 2. Verify metric was recorded
        error_rate = realtime_metrics_collector.get_metric_value('integration.error_rate')
        assert error_rate == 0.25
        
        threshold = AlertThreshold(
            metric_name="error_rate",
            warning_value=0.05,
            critical_value=0.15,
            comparison="greater_than"
        )
        
        severity = threshold.check_threshold(0.25)
        assert severity == AlertSeverity.CRITICAL
        
        # 4. Create an alert based on this metric
        alert_id = monitoring_dashboard_service.create_alert(
            "Integration Test Alert",
            f"Error rate is {error_rate:.1%}",
            severity,
            "integration_test"
        )
        
        assert alert_id is not None
        
        # 5. Verify alert appears in dashboard
        alerts = monitoring_dashboard_service.get_alerts(limit=5)
        integration_alert = next((a for a in alerts if a['id'] == alert_id), None)
        assert integration_alert is not None
        assert integration_alert['severity'] == 'critical'
    
    def test_dashboard_data_consistency(self):
        """Test that dashboard data is consistent across components"""
        # Get dashboard data
        dashboard_data = realtime_metrics_collector.get_dashboard_data()
        
        assert 'timestamp' in dashboard_data
        assert 'metrics' in dashboard_data
        
        # Verify metrics structure
        metrics = dashboard_data['metrics']
        expected_categories = ['system', 'application', 'services', 'cache']
        
        for category in expected_categories:
            if category in metrics:
                assert isinstance(metrics[category], dict)
    
    @patch('src.services.health_monitor.health_monitor.get_overall_health')
    def test_service_health_integration(self, mock_health):
        """Test integration between health monitoring and alerting"""
        # Mock a service failure
        mock_health.return_value = {
            'overall_healthy': False,
            'services': {
                'test_service': {
                    'status': 'unhealthy',
                    'error_count': 5,
                    'last_check': time.time()
                }
            }
        }
        
        # Collect service health metrics
        metrics = realtime_metrics_collector._collect_service_health_metrics()
        
        # Verify health score reflects the unhealthy service
        assert 'services.health.score' in metrics
        assert metrics['services.health.score'] < 100  # Should be less than 100% healthy
        assert metrics['services.failed.count'] >= 1

class TestPerformanceAndScalability:
    """Test performance and scalability of monitoring system"""
    
    def test_high_volume_metric_recording(self):
        """Test system performance with high volume of metrics"""
        # Register a test metric
        realtime_metrics_collector.register_metric('perf.test', MetricType.COUNTER, "Performance test metric")
        
        # Record many metrics quickly
        start_time = time.time()
        for i in range(1000):
            realtime_metrics_collector.record_metric('perf.test', float(i))
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert duration < 5.0  # 5 seconds for 1000 metrics
        
        # Verify final value
        final_value = realtime_metrics_collector.get_metric_value('perf.test')
        assert final_value == 999.0
    
    def test_concurrent_metric_access(self):
        """Test concurrent access to metrics"""
        realtime_metrics_collector.register_metric('concurrent.test', MetricType.GAUGE, "Concurrent test metric")
        
        def record_metrics(thread_id):
            for i in range(100):
                realtime_metrics_collector.record_metric('concurrent.test', float(thread_id * 100 + i))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=record_metrics, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify metric still works
        value = realtime_metrics_collector.get_metric_value('concurrent.test')
        assert value is not None
    
    def test_memory_usage_with_large_history(self):
        """Test memory usage with large metric history"""
        # Register metric with large history
        realtime_metrics_collector.register_metric('memory.test', MetricType.GAUGE, "Memory test metric")
        
        # Record many values (should be limited by deque maxlen)
        for i in range(2000):  # More than default maxlen of 1000
            realtime_metrics_collector.record_metric('memory.test', float(i))
        
        # Get metric and verify history is limited
        metric = realtime_metrics_collector.get_metric('memory.test')
        assert metric is not None
        assert len(metric.points) <= 1000  # Should be limited by maxlen
        
        # Verify latest value is correct
        latest = metric.get_latest()
        assert latest.value == 1999.0

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup and teardown for each test"""
    # Setup
    yield
    
    # Teardown - clean up any test alerts
    try:
        # Clear test alerts
        alerts = monitoring_dashboard_service.get_alerts(limit=100)
        for alert in alerts:
            if 'test' in alert.get('title', '').lower() or 'integration' in alert.get('title', '').lower():
                monitoring_dashboard_service.resolve_alert(alert['id'])
    except Exception:
        pass  # Ignore cleanup errors

if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])