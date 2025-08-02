"""Base service architecture for unified service management."""
from typing import Any, Dict, List, Optional

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    """Service status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ServiceMetrics:
    """Service metrics data structure."""
    service_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    status: ServiceStatus = ServiceStatus.UNKNOWN
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        return 100.0 - self.success_rate
    
    def add_custom_metric(self, key: str, value: Any) -> None:
        """Add or increment a custom metric.
        
        Args:
            key: Metric key
            value: Value to add (will be incremented if key exists and both are numeric)
        """
        if key in self.custom_metrics and isinstance(self.custom_metrics[key], (int, float)) and isinstance(value, (int, float)):
            self.custom_metrics[key] += value
        else:
            self.custom_metrics[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "service_name": self.service_name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "average_response_time": self.average_response_time,
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "status": self.status.value,
            "custom_metrics": self.custom_metrics
        }

class BaseService(ABC):
    """Base service class providing common functionality for all services."""
    
    def __init__(self, service_name: str, **kwargs):
        """Initialize base service.
        
        Args:
            service_name: Unique name for the service
            **kwargs: Additional service-specific configuration
        """
        self.service_name = service_name
        self.config = kwargs
        self.metrics = ServiceMetrics(service_name=service_name)
        self._lock = threading.RLock()
        self._initialized = False
        self._health_check_interval = kwargs.get('health_check_interval', 60)  # seconds
        self._last_health_check = None
        
        # Register with service registry
        ServiceRegistry.register(self)
        
        logger.info(f"Initialized {self.service_name} service")
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the service. Must be implemented by subclasses.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Perform health check. Must be implemented by subclasses.
        
        Returns:
            bool: True if service is healthy, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup service resources. Must be implemented by subclasses."""
        pass
    
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized
    
    def get_status(self) -> ServiceStatus:
        """Get current service status."""
        return self.metrics.status
    
    def get_metrics(self) -> ServiceMetrics:
        """Get service metrics."""
        with self._lock:
            return self.metrics
    
    def update_custom_metric(self, key: str, value: Any) -> None:
        """Update a custom metric.
        
        Args:
            key: Metric key
            value: Metric value
        """
        with self._lock:
            self.metrics.custom_metrics[key] = value
    
    @contextmanager
    def track_request(self, operation_name=None):
        """Context manager to track request metrics."""
        start_time = time.time()
        request_time = datetime.now(timezone.utc)
        
        try:
            with self._lock:
                self.metrics.total_requests += 1
                self.metrics.last_request_time = request_time
                if operation_name:
                    operation_key = f"operation_{operation_name}"
                    if operation_key not in self.metrics.custom_metrics:
                        self.metrics.custom_metrics[operation_key] = 0
                    self.metrics.custom_metrics[operation_key] += 1
            
            yield
            
            # Success
            end_time = time.time()
            response_time = end_time - start_time
            
            with self._lock:
                self.metrics.successful_requests += 1
                self.metrics.last_success_time = request_time
                self._update_average_response_time(response_time)
                
                # Update status based on recent performance
                if self.metrics.success_rate >= 95:
                    self.metrics.status = ServiceStatus.HEALTHY
                elif self.metrics.success_rate >= 80:
                    self.metrics.status = ServiceStatus.DEGRADED
                else:
                    self.metrics.status = ServiceStatus.UNHEALTHY
                    
        except Exception as e:
            # Failure
            end_time = time.time()
            response_time = end_time - start_time
            
            with self._lock:
                self.metrics.failed_requests += 1
                self.metrics.last_failure_time = request_time
                self._update_average_response_time(response_time)
                
                # Update status
                if self.metrics.success_rate < 80:
                    self.metrics.status = ServiceStatus.UNHEALTHY
                elif self.metrics.success_rate < 95:
                    self.metrics.status = ServiceStatus.DEGRADED
            
            logger.error(f"Request failed in {self.service_name}: {str(e)}")
            raise
    
    def _update_average_response_time(self, response_time: float) -> None:
        """Update average response time using exponential moving average."""
        if self.metrics.average_response_time == 0:
            self.metrics.average_response_time = response_time
        else:
            # Use exponential moving average with alpha = 0.1
            alpha = 0.1
            self.metrics.average_response_time = (
                alpha * response_time + (1 - alpha) * self.metrics.average_response_time
            )
    
    def perform_health_check(self) -> bool:
        """Perform health check with caching.
        
        Returns:
            bool: True if service is healthy, False otherwise
        """
        current_time = time.time()
        
        if (self._last_health_check and 
            current_time - self._last_health_check < self._health_check_interval):
            return self.metrics.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]
        
        try:
            is_healthy = self.health_check()
            with self._lock:
                if is_healthy:
                    if self.metrics.status == ServiceStatus.UNHEALTHY:
                        self.metrics.status = ServiceStatus.DEGRADED
                else:
                    self.metrics.status = ServiceStatus.UNHEALTHY
            
            self._last_health_check = current_time
            return is_healthy
            
        except Exception as e:
            logger.error(f"Health check failed for {self.service_name}: {str(e)}")
            with self._lock:
                self.metrics.status = ServiceStatus.UNHEALTHY
            return False
    
    def reset_metrics(self) -> None:
        """Reset service metrics."""
        with self._lock:
            self.metrics = ServiceMetrics(service_name=self.service_name)
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.service_name})"
    
    def __repr__(self) -> str:
        return self.__str__()

class ServiceRegistry:
    """Registry for managing service instances and dependencies."""
    
    _services: Dict[str, BaseService] = {}
    _dependencies: Dict[str, List[str]] = {}
    _lock = threading.RLock()
    
    @classmethod
    def register(cls, service: BaseService) -> None:
        """Register a service instance.
        
        Args:
            service: Service instance to register
        """
        with cls._lock:
            cls._services[service.service_name] = service
            logger.info(f"Registered service: {service.service_name}")
    
    @classmethod
    def unregister(cls, service_name: str) -> None:
        """Unregister a service.
        
        Args:
            service_name: Name of service to unregister
        """
        with cls._lock:
            if service_name in cls._services:
                service = cls._services.pop(service_name)
                try:
                    service.cleanup()
                except Exception as e:
                    logger.error(f"Error during cleanup of {service_name}: {str(e)}")
                logger.info(f"Unregistered service: {service_name}")
    
    @classmethod
    def get_service(cls, service_name: str) -> Optional[BaseService]:
        """Get a service by name.
        
        Args:
            service_name: Name of service to retrieve
            
        Returns:
            Service instance or None if not found
        """
        with cls._lock:
            return cls._services.get(service_name)
    
    @classmethod
    def get_all_services(cls) -> Dict[str, BaseService]:
        """Get all registered services.
        
        Returns:
            Dictionary of service name to service instance
        """
        with cls._lock:
            return cls._services.copy()
    
    @classmethod
    def add_dependency(cls, service_name: str, dependency_name: str) -> None:
        """Add a dependency relationship.
        
        Args:
            service_name: Name of service that depends on dependency
            dependency_name: Name of service that is depended upon
        """
        with cls._lock:
            if service_name not in cls._dependencies:
                cls._dependencies[service_name] = []
            if dependency_name not in cls._dependencies[service_name]:
                cls._dependencies[service_name].append(dependency_name)
    
    @classmethod
    def get_dependencies(cls, service_name: str) -> List[str]:
        """Get dependencies for a service.
        
        Args:
            service_name: Name of service
            
        Returns:
            List of dependency service names
        """
        with cls._lock:
            return cls._dependencies.get(service_name, []).copy()
    
    @classmethod
    def get_health_status(cls) -> Dict[str, Dict[str, Any]]:
        """Get health status of all services.
        
        Returns:
            Dictionary of service health information
        """
        status = {}
        with cls._lock:
            for name, service in cls._services.items():
                try:
                    is_healthy = service.perform_health_check()
                    metrics = service.get_metrics()
                    status[name] = {
                        "healthy": is_healthy,
                        "status": metrics.status.value,
                        "metrics": metrics.to_dict()
                    }
                except Exception as e:
                    status[name] = {
                        "healthy": False,
                        "status": ServiceStatus.UNHEALTHY.value,
                        "error": str(e)
                    }
        return status
    
    @classmethod
    def initialize_all(cls) -> Dict[str, bool]:
        """Initialize all registered services.
        
        Returns:
            Dictionary of service name to initialization success
        """
        results = {}
        with cls._lock:
            for name, service in cls._services.items():
                try:
                    success = service.initialize()
                    service._initialized = success
                    results[name] = success
                    logger.info(f"Service {name} initialization: {'success' if success else 'failed'}")
                except Exception as e:
                    results[name] = False
                    logger.error(f"Failed to initialize service {name}: {str(e)}")
        return results
    
    @classmethod
    def cleanup_all(cls) -> None:
        """Cleanup all registered services."""
        with cls._lock:
            for name in list(cls._services.keys()):
                cls.unregister(name)
            cls._dependencies.clear()

class ServiceInjector:
    """Dependency injection for services."""
    
    @staticmethod
    def inject_dependencies(target_service: BaseService, **dependencies) -> None:
        """Inject dependencies into a service.
        
        Args:
            target_service: Service to inject dependencies into
            **dependencies: Named dependencies to inject
        """
        for name, dependency in dependencies.items():
            if isinstance(dependency, BaseService):
                setattr(target_service, name, dependency)
                ServiceRegistry.add_dependency(target_service.service_name, dependency.service_name)
                logger.debug(f"Injected {dependency.service_name} into {target_service.service_name} as {name}")
            else:
                setattr(target_service, name, dependency)
                logger.debug(f"Injected {type(dependency).__name__} into {target_service.service_name} as {name}")
    
    @staticmethod
    def auto_inject(target_service: BaseService) -> None:
        """Automatically inject dependencies based on service registry.
        
        Args:
            target_service: Service to auto-inject dependencies into
        """
        dependencies = ServiceRegistry.get_dependencies(target_service.service_name)
        for dep_name in dependencies:
            dep_service = ServiceRegistry.get_service(dep_name)
            if dep_service:
                # Convert service name to attribute name (e.g., "llm_service" -> "llm_service")
                attr_name = dep_name.lower().replace('-', '_')
                setattr(target_service, attr_name, dep_service)
                logger.debug(f"Auto-injected {dep_name} into {target_service.service_name}")