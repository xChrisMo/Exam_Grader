"""Unit tests for base service architecture."""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

from src.services.base_service import (
    BaseService, ServiceRegistry, ServiceInjector, ServiceMetrics, ServiceStatus
)


class MockService(BaseService):
    """Mock service for testing."""
    
    def __init__(self, service_name: str, should_fail_init: bool = False, should_fail_health: bool = False):
        self.should_fail_init = should_fail_init
        self.should_fail_health = should_fail_health
        self.init_called = False
        self.health_called = False
        self.cleanup_called = False
        super().__init__(service_name)
    
    def initialize(self) -> bool:
        self.init_called = True
        if self.should_fail_init:
            raise Exception("Initialization failed")
        return not self.should_fail_init
    
    def health_check(self) -> bool:
        self.health_called = True
        if self.should_fail_health:
            raise Exception("Health check failed")
        return not self.should_fail_health
    
    def cleanup(self) -> None:
        self.cleanup_called = True


class TestServiceMetrics:
    """Test cases for ServiceMetrics."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = ServiceMetrics("test_service")
        
        assert metrics.service_name == "test_service"
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.average_response_time == 0.0
        assert metrics.status == ServiceStatus.UNKNOWN
        assert metrics.success_rate == 0.0
        assert metrics.failure_rate == 100.0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = ServiceMetrics("test_service")
        metrics.total_requests = 10
        metrics.successful_requests = 8
        
        assert metrics.success_rate == 80.0
        assert metrics.failure_rate == 20.0
    
    def test_to_dict_conversion(self):
        """Test metrics to dictionary conversion."""
        metrics = ServiceMetrics("test_service")
        metrics.total_requests = 5
        metrics.successful_requests = 4
        metrics.custom_metrics["test_metric"] = "test_value"
        
        data = metrics.to_dict()
        
        assert data["service_name"] == "test_service"
        assert data["total_requests"] == 5
        assert data["successful_requests"] == 4
        assert data["success_rate"] == 80.0
        assert data["custom_metrics"]["test_metric"] == "test_value"


class TestBaseService:
    """Test cases for BaseService."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Clear service registry
        ServiceRegistry.cleanup_all()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        ServiceRegistry.cleanup_all()
    
    def test_service_initialization(self):
        """Test service initialization."""
        service = MockService("test_service")
        
        assert service.service_name == "test_service"
        assert not service.is_initialized()
        assert service.get_status() == ServiceStatus.UNKNOWN
        assert isinstance(service.get_metrics(), ServiceMetrics)
    
    def test_service_registration(self):
        """Test automatic service registration."""
        service = MockService("test_service")
        
        registered_service = ServiceRegistry.get_service("test_service")
        assert registered_service is service
    
    def test_track_request_success(self):
        """Test request tracking for successful requests."""
        service = MockService("test_service")
        
        with service.track_request():
            time.sleep(0.01)  # Simulate some work
        
        metrics = service.get_metrics()
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0
        assert metrics.average_response_time > 0
        assert metrics.last_request_time is not None
        assert metrics.last_success_time is not None
        assert metrics.status == ServiceStatus.HEALTHY
    
    def test_track_request_failure(self):
        """Test request tracking for failed requests."""
        service = MockService("test_service")
        
        with pytest.raises(ValueError):
            with service.track_request():
                raise ValueError("Test error")
        
        metrics = service.get_metrics()
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 1
        assert metrics.last_failure_time is not None
    
    def test_health_check_caching(self):
        """Test health check caching."""
        service = MockService("test_service", health_check_interval=1)
        
        # First health check
        result1 = service.perform_health_check()
        assert result1 is True
        assert service.health_called
        
        # Reset flag and check again immediately (should use cache)
        service.health_called = False
        result2 = service.perform_health_check()
        assert result2 is True
        assert not service.health_called  # Should not have called health_check again
    
    def test_custom_metrics(self):
        """Test custom metrics functionality."""
        service = MockService("test_service")
        
        service.update_custom_metric("test_key", "test_value")
        service.update_custom_metric("numeric_key", 42)
        
        metrics = service.get_metrics()
        assert metrics.custom_metrics["test_key"] == "test_value"
        assert metrics.custom_metrics["numeric_key"] == 42
    
    def test_metrics_reset(self):
        """Test metrics reset functionality."""
        service = MockService("test_service")
        
        # Generate some metrics
        with service.track_request():
            pass
        service.update_custom_metric("test", "value")
        
        # Reset metrics
        service.reset_metrics()
        
        metrics = service.get_metrics()
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert len(metrics.custom_metrics) == 0


class TestServiceRegistry:
    """Test cases for ServiceRegistry."""
    
    def setup_method(self):
        """Setup for each test method."""
        ServiceRegistry.cleanup_all()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        ServiceRegistry.cleanup_all()
    
    def test_service_registration_and_retrieval(self):
        """Test service registration and retrieval."""
        service = MockService("test_service")
        
        # Service should be automatically registered
        retrieved = ServiceRegistry.get_service("test_service")
        assert retrieved is service
        
        # Test get_all_services
        all_services = ServiceRegistry.get_all_services()
        assert "test_service" in all_services
        assert all_services["test_service"] is service
    
    def test_service_unregistration(self):
        """Test service unregistration."""
        service = MockService("test_service")
        
        # Unregister service
        ServiceRegistry.unregister("test_service")
        
        # Service should no longer be available
        retrieved = ServiceRegistry.get_service("test_service")
        assert retrieved is None
        assert service.cleanup_called
    
    def test_dependency_management(self):
        """Test dependency relationship management."""
        service1 = MockService("service1")
        service2 = MockService("service2")
        
        # Add dependency
        ServiceRegistry.add_dependency("service1", "service2")
        
        # Check dependencies
        deps = ServiceRegistry.get_dependencies("service1")
        assert "service2" in deps
        
        # Service without dependencies
        deps_empty = ServiceRegistry.get_dependencies("service2")
        assert len(deps_empty) == 0
    
    def test_health_status_all_services(self):
        """Test getting health status of all services."""
        healthy_service = MockService("healthy_service")
        unhealthy_service = MockService("unhealthy_service", should_fail_health=True)
        
        status = ServiceRegistry.get_health_status()
        
        assert "healthy_service" in status
        assert "unhealthy_service" in status
        assert status["healthy_service"]["healthy"] is True
        assert status["unhealthy_service"]["healthy"] is False
    
    def test_initialize_all_services(self):
        """Test initializing all services."""
        good_service = MockService("good_service")
        bad_service = MockService("bad_service", should_fail_init=True)
        
        results = ServiceRegistry.initialize_all()
        
        assert results["good_service"] is True
        assert results["bad_service"] is False
        assert good_service.is_initialized() is True
        assert bad_service.is_initialized() is False
    
    def test_cleanup_all_services(self):
        """Test cleanup of all services."""
        service1 = MockService("service1")
        service2 = MockService("service2")
        
        # Add some dependencies
        ServiceRegistry.add_dependency("service1", "service2")
        
        # Cleanup all
        ServiceRegistry.cleanup_all()
        
        # All services should be unregistered
        assert ServiceRegistry.get_service("service1") is None
        assert ServiceRegistry.get_service("service2") is None
        assert len(ServiceRegistry.get_all_services()) == 0
        
        # Cleanup should have been called
        assert service1.cleanup_called
        assert service2.cleanup_called


class TestServiceInjector:
    """Test cases for ServiceInjector."""
    
    def setup_method(self):
        """Setup for each test method."""
        ServiceRegistry.cleanup_all()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        ServiceRegistry.cleanup_all()
    
    def test_dependency_injection(self):
        """Test manual dependency injection."""
        target_service = MockService("target")
        dependency_service = MockService("dependency")
        
        # Inject dependency
        ServiceInjector.inject_dependencies(
            target_service,
            dep_service=dependency_service,
            config_value="test_config"
        )
        
        # Check injection
        assert hasattr(target_service, "dep_service")
        assert target_service.dep_service is dependency_service
        assert hasattr(target_service, "config_value")
        assert target_service.config_value == "test_config"
        
        # Check dependency relationship
        deps = ServiceRegistry.get_dependencies("target")
        assert "dependency" in deps
    
    def test_auto_injection(self):
        """Test automatic dependency injection."""
        dependency_service = MockService("dependency_service")
        target_service = MockService("target_service")
        
        # Add dependency relationship
        ServiceRegistry.add_dependency("target_service", "dependency_service")
        
        # Auto-inject
        ServiceInjector.auto_inject(target_service)
        
        # Check injection
        assert hasattr(target_service, "dependency_service")
        assert target_service.dependency_service is dependency_service


class TestServiceIntegration:
    """Integration tests for service architecture."""
    
    def setup_method(self):
        """Setup for each test method."""
        ServiceRegistry.cleanup_all()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        ServiceRegistry.cleanup_all()
    
    def test_full_service_lifecycle(self):
        """Test complete service lifecycle."""
        # Create services
        service1 = MockService("service1")
        service2 = MockService("service2")
        
        # Set up dependencies
        ServiceRegistry.add_dependency("service1", "service2")
        ServiceInjector.auto_inject(service1)
        
        # Initialize all services
        init_results = ServiceRegistry.initialize_all()
        assert all(init_results.values())
        
        # Check health status
        health_status = ServiceRegistry.get_health_status()
        assert all(status["healthy"] for status in health_status.values())
        
        # Simulate some work
        with service1.track_request():
            with service2.track_request():
                pass
        
        # Check metrics
        metrics1 = service1.get_metrics()
        metrics2 = service2.get_metrics()
        assert metrics1.total_requests == 1
        assert metrics2.total_requests == 1
        
        # Cleanup
        ServiceRegistry.cleanup_all()
        assert service1.cleanup_called
        assert service2.cleanup_called
    
    def test_service_failure_handling(self):
        """Test handling of service failures."""
        # Create a service that fails health checks
        failing_service = MockService("failing_service", should_fail_health=True)
        healthy_service = MockService("healthy_service")
        
        # Check health status
        health_status = ServiceRegistry.get_health_status()
        
        assert health_status["failing_service"]["healthy"] is False
        assert health_status["healthy_service"]["healthy"] is True
        
        # Test failed request tracking
        with pytest.raises(Exception):
            with failing_service.track_request():
                raise Exception("Simulated failure")
        
        metrics = failing_service.get_metrics()
        assert metrics.failed_requests == 1
        assert metrics.status == ServiceStatus.UNHEALTHY