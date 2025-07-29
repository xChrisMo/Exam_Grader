"""
Enhanced Core Service with Dependency Injection and Error Handling

This module provides an enhanced core service with proper dependency injection,
comprehensive error handling, service health monitoring, and graceful degradation.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Type, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod

from utils.logger import logger
from src.services.processing_error_handler import processing_error_handler, ErrorContext, ErrorCategory
from src.services.health_monitor import health_monitor, ServiceStatus, HealthStatus
from src.services.service_shutdown_manager import register_service_for_shutdown, ServicePriority
from src.services.enhanced_logging_service import enhanced_logging_service, LogCategory

class ServiceLifecycle(Enum):
    """Service lifecycle states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"

class DependencyType(Enum):
    """Types of service dependencies"""
    REQUIRED = "required"      # Service cannot function without this dependency
    OPTIONAL = "optional"      # Service can function with degraded capability
    LAZY = "lazy"             # Dependency loaded on first use

@dataclass
class ServiceDependency:
    """Service dependency definition"""
    name: str
    service_type: Type
    dependency_type: DependencyType = DependencyType.REQUIRED
    factory: Optional[Callable[[], Any]] = None
    config: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 3
    retry_delay: float = 1.0

@dataclass
class ServiceInfo:
    """Information about a registered service"""
    name: str
    service: Any
    lifecycle: ServiceLifecycle
    dependencies: List[str] = field(default_factory=list)
    health_status: ServiceStatus = ServiceStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    initialization_time: Optional[float] = None
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class ServiceInterface(ABC):
    """Base interface for all services"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the service"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if service is healthy"""
        pass
    
    @abstractmethod
    def shutdown(self):
        """Shutdown the service"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status information"""
        return {
            'name': getattr(self, 'name', 'unknown'),
            'healthy': self.health_check(),
            'metadata': getattr(self, 'metadata', {})
        }

class DependencyInjector:
    """Dependency injection container"""
    
    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
        self._dependencies: Dict[str, ServiceDependency] = {}
        self._initialization_order: List[str] = []
        self._lock = threading.RLock()
    
    def register_dependency(self, dependency: ServiceDependency):
        """Register a service dependency"""
        with self._lock:
            self._dependencies[dependency.name] = dependency
            logger.debug(f"Registered dependency: {dependency.name} ({dependency.dependency_type.value})")
    
    def register_service(self, name: str, service: Any, dependencies: List[str] = None):
        """Register a service instance"""
        with self._lock:
            service_info = ServiceInfo(
                name=name,
                service=service,
                lifecycle=ServiceLifecycle.UNINITIALIZED,
                dependencies=dependencies or []
            )
            self._services[name] = service_info
            logger.info(f"Registered service: {name}")
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get a service instance"""
        with self._lock:
            service_info = self._services.get(name)
            if service_info and service_info.lifecycle == ServiceLifecycle.RUNNING:
                return service_info.service
            return None
    
    def initialize_services(self) -> Dict[str, bool]:
        """Initialize all services in dependency order"""
        with self._lock:
            results = {}
            
            # Calculate initialization order
            self._calculate_initialization_order()
            
            # Initialize services in order
            for service_name in self._initialization_order:
                results[service_name] = self._initialize_service(service_name)
            
            return results
    
    def _calculate_initialization_order(self):
        """Calculate service initialization order based on dependencies"""
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(service_name: str):
            if service_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {service_name}")
            if service_name in visited:
                return
            
            temp_visited.add(service_name)
            
            service_info = self._services.get(service_name)
            if service_info:
                for dep_name in service_info.dependencies:
                    if dep_name in self._services:
                        visit(dep_name)
            
            temp_visited.remove(service_name)
            visited.add(service_name)
            order.append(service_name)
        
        for service_name in self._services.keys():
            if service_name not in visited:
                visit(service_name)
        
        self._initialization_order = order
        logger.info(f"Service initialization order: {' -> '.join(order)}")
    
    def _initialize_service(self, service_name: str) -> bool:
        """Initialize a single service"""
        service_info = self._services.get(service_name)
        if not service_info:
            return False
        
        if service_info.lifecycle != ServiceLifecycle.UNINITIALIZED:
            return service_info.lifecycle == ServiceLifecycle.RUNNING
        
        logger.info(f"Initializing service: {service_name}")
        service_info.lifecycle = ServiceLifecycle.INITIALIZING
        
        start_time = time.time()
        
        try:
            # Check dependencies
            for dep_name in service_info.dependencies:
                if not self._check_dependency(service_name, dep_name):
                    dependency = self._dependencies.get(dep_name)
                    if dependency and dependency.dependency_type == DependencyType.REQUIRED:
                        raise Exception(f"Required dependency {dep_name} not available")
                    else:
                        logger.warning(f"Optional dependency {dep_name} not available for {service_name}")
            
            # Initialize the service
            if hasattr(service_info.service, 'initialize'):
                success = service_info.service.initialize()
            else:
                success = True
            
            if success:
                service_info.lifecycle = ServiceLifecycle.RUNNING
                service_info.initialization_time = time.time() - start_time
                service_info.health_status = ServiceStatus.HEALTHY
                service_info.last_health_check = datetime.utcnow()
                
                logger.info(f"Service {service_name} initialized successfully in {service_info.initialization_time:.3f}s")
                return True
            else:
                service_info.lifecycle = ServiceLifecycle.FAILED
                service_info.error_count += 1
                logger.error(f"Service {service_name} initialization failed")
                return False
                
        except Exception as e:
            service_info.lifecycle = ServiceLifecycle.FAILED
            service_info.error_count += 1
            
            error_context = ErrorContext(
                operation="service_initialization",
                service="dependency_injector",
                timestamp=datetime.utcnow(),
                additional_data={
                    'service_name': service_name,
                    'error': str(e)
                }
            )
            
            processing_error_handler.handle_error(e, error_context)
            logger.error(f"Error initializing service {service_name}: {e}")
            return False
    
    def _check_dependency(self, service_name: str, dep_name: str) -> bool:
        """Check if a dependency is available"""
        dep_service_info = self._services.get(dep_name)
        if dep_service_info:
            return dep_service_info.lifecycle == ServiceLifecycle.RUNNING
        
        dependency = self._dependencies.get(dep_name)
        if dependency and dependency.factory:
            try:
                service_instance = dependency.factory()
                self.register_service(dep_name, service_instance)
                return self._initialize_service(dep_name)
            except Exception as e:
                logger.error(f"Failed to create dependency {dep_name}: {e}")
                return False
        
        return False
    
    def health_check_all(self) -> Dict[str, bool]:
        """Perform health checks on all services"""
        with self._lock:
            results = {}
            
            for service_name, service_info in self._services.items():
                if service_info.lifecycle == ServiceLifecycle.RUNNING:
                    try:
                        if hasattr(service_info.service, 'health_check'):
                            is_healthy = service_info.service.health_check()
                        else:
                            is_healthy = True
                        
                        service_info.health_status = ServiceStatus.HEALTHY if is_healthy else ServiceStatus.UNHEALTHY
                        service_info.last_health_check = datetime.utcnow()
                        results[service_name] = is_healthy
                        
                        if not is_healthy:
                            service_info.error_count += 1
                        else:
                            service_info.error_count = 0
                            
                    except Exception as e:
                        service_info.health_status = ServiceStatus.UNHEALTHY
                        service_info.error_count += 1
                        results[service_name] = False
                        logger.error(f"Health check failed for {service_name}: {e}")
                else:
                    results[service_name] = False
            
            return results
    
    def shutdown_all(self):
        """Shutdown all services in reverse order"""
        with self._lock:
            # Shutdown in reverse order
            for service_name in reversed(self._initialization_order):
                service_info = self._services.get(service_name)
                if service_info and service_info.lifecycle == ServiceLifecycle.RUNNING:
                    self._shutdown_service(service_name)
    
    def _shutdown_service(self, service_name: str):
        """Shutdown a single service"""
        service_info = self._services.get(service_name)
        if not service_info:
            return
        
        logger.info(f"Shutting down service: {service_name}")
        service_info.lifecycle = ServiceLifecycle.STOPPING
        
        try:
            if hasattr(service_info.service, 'shutdown'):
                service_info.service.shutdown()
            
            service_info.lifecycle = ServiceLifecycle.STOPPED
            logger.info(f"Service {service_name} shutdown completed")
            
        except Exception as e:
            service_info.lifecycle = ServiceLifecycle.FAILED
            logger.error(f"Error shutting down service {service_name}: {e}")
    
    def get_service_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all services"""
        with self._lock:
            return {
                name: {
                    'name': info.name,
                    'lifecycle': info.lifecycle.value,
                    'health_status': info.health_status.value,
                    'dependencies': info.dependencies,
                    'initialization_time': info.initialization_time,
                    'error_count': info.error_count,
                    'last_health_check': info.last_health_check.isoformat() if info.last_health_check else None
                }
                for name, info in self._services.items()
            }

class EnhancedCoreService:
    """Enhanced core service with dependency injection and error handling"""
    
    def __init__(self):
        self.name = "enhanced_core_service"
        self.injector = DependencyInjector()
        self.lifecycle = ServiceLifecycle.UNINITIALIZED
        self.initialization_start_time = None
        self.initialization_results = {}
        
        register_service_for_shutdown(
            self.name,
            self.shutdown,
            ServicePriority.HIGH,
            timeout=30.0
        )
        
        # Setup default dependencies
        self._setup_default_dependencies()
    
    def _setup_default_dependencies(self):
        """Setup default service dependencies"""
        
        # OCR Service dependency
        def create_ocr_service():
            try:
                from src.services.consolidated_ocr_service import ConsolidatedOCRService
                return ConsolidatedOCRService(allow_no_key=True)
            except ImportError as e:
                logger.warning(f"OCR service not available: {e}")
                return None
        
        self.injector.register_dependency(ServiceDependency(
            name="ocr_service",
            service_type=object,  # We'll use duck typing
            dependency_type=DependencyType.OPTIONAL,
            factory=create_ocr_service
        ))
        
        # LLM Service dependency
        def create_llm_service():
            try:
                from src.services.consolidated_llm_service import ConsolidatedLLMService
                return ConsolidatedLLMService()
            except ImportError as e:
                logger.warning(f"LLM service not available: {e}")
                return None
        
        self.injector.register_dependency(ServiceDependency(
            name="llm_service",
            service_type=object,
            dependency_type=DependencyType.OPTIONAL,
            factory=create_llm_service
        ))
        
        # File Processing Service dependency
        def create_file_processing_service():
            try:
                from src.services.file_processing_service import FileProcessingService
                return FileProcessingService()
            except ImportError as e:
                logger.warning(f"File processing service not available: {e}")
                return None
        
        self.injector.register_dependency(ServiceDependency(
            name="file_processing_service",
            service_type=object,
            dependency_type=DependencyType.OPTIONAL,
            factory=create_file_processing_service
        ))
        
        # Cache Manager dependency
        def create_cache_manager():
            try:
                from src.services.cache_manager import cache_manager
                return cache_manager
            except ImportError as e:
                logger.warning(f"Cache manager not available: {e}")
                return None
        
        self.injector.register_dependency(ServiceDependency(
            name="cache_manager",
            service_type=object,
            dependency_type=DependencyType.OPTIONAL,
            factory=create_cache_manager
        ))
        
        # Performance Monitor dependency
        def create_performance_monitor():
            try:
                from src.services.performance_monitor import performance_monitor
                return performance_monitor
            except ImportError as e:
                logger.warning(f"Performance monitor not available: {e}")
                return None
        
        self.injector.register_dependency(ServiceDependency(
            name="performance_monitor",
            service_type=object,
            dependency_type=DependencyType.OPTIONAL,
            factory=create_performance_monitor
        ))
    
    def initialize(self) -> bool:
        """Initialize the core service and all dependencies"""
        if self.lifecycle != ServiceLifecycle.UNINITIALIZED:
            logger.warning("Core service already initialized")
            return self.lifecycle == ServiceLifecycle.RUNNING
        
        self.lifecycle = ServiceLifecycle.INITIALIZING
        self.initialization_start_time = time.time()
        
        logger.info("Starting enhanced core service initialization")
        
        try:
            # Log initialization start
            enhanced_logging_service.log_info(
                LogCategory.SYSTEM, self.name, "initialize",
                "Starting core service initialization"
            )
            
            # Initialize all services
            self.initialization_results = self.injector.initialize_services()
            
            # Check initialization results
            successful_services = sum(1 for success in self.initialization_results.values() if success)
            total_services = len(self.initialization_results)
            
            if successful_services == 0:
                self.lifecycle = ServiceLifecycle.FAILED
                logger.error("No services initialized successfully")
                return False
            
            # Register with health monitor
            try:
                health_monitor.register_service(self.name, self.health_check)
            except Exception as e:
                logger.warning(f"Failed to register with health monitor: {e}")
            
            self.lifecycle = ServiceLifecycle.RUNNING
            initialization_time = time.time() - self.initialization_start_time
            
            logger.info(f"Core service initialization completed in {initialization_time:.3f}s")
            logger.info(f"Services initialized: {successful_services}/{total_services}")
            
            # Log successful initialization
            enhanced_logging_service.log_info(
                LogCategory.SYSTEM, self.name, "initialize",
                f"Core service initialized successfully ({successful_services}/{total_services} services)",
                duration_ms=initialization_time * 1000,
                metadata={
                    'successful_services': successful_services,
                    'total_services': total_services,
                    'initialization_results': self.initialization_results
                }
            )
            
            return True
            
        except Exception as e:
            self.lifecycle = ServiceLifecycle.FAILED
            
            error_context = ErrorContext(
                operation="core_service_initialization",
                service=self.name,
                timestamp=datetime.utcnow(),
                additional_data={
                    'error': str(e),
                    'initialization_results': self.initialization_results
                }
            )
            
            processing_error_handler.handle_error(e, error_context)
            
            enhanced_logging_service.log_error(
                LogCategory.ERROR, self.name, "initialize",
                f"Core service initialization failed: {str(e)}",
                stack_trace=str(e)
            )
            
            logger.error(f"Core service initialization failed: {e}")
            return False
    
    def health_check(self) -> bool:
        """Perform health check on core service and all dependencies"""
        if self.lifecycle != ServiceLifecycle.RUNNING:
            return False
        
        try:
            # Check all service health
            health_results = self.injector.health_check_all()
            
            healthy_services = sum(1 for healthy in health_results.values() if healthy)
            total_services = len(health_results)
            
            is_healthy = healthy_services > (total_services / 2) if total_services > 0 else False
            
            if not is_healthy:
                logger.warning(f"Core service health check failed: {healthy_services}/{total_services} services healthy")
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """Get a service instance"""
        return self.injector.get_service(service_name)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status information"""
        initialization_time = None
        if self.initialization_start_time:
            if self.lifecycle == ServiceLifecycle.RUNNING:
                initialization_time = time.time() - self.initialization_start_time
            elif self.lifecycle in [ServiceLifecycle.FAILED, ServiceLifecycle.STOPPED]:
                # Use the time when initialization completed/failed
                initialization_time = getattr(self, '_final_initialization_time', None)
        
        return {
            'name': self.name,
            'lifecycle': self.lifecycle.value,
            'healthy': self.health_check() if self.lifecycle == ServiceLifecycle.RUNNING else False,
            'initialization_time': initialization_time,
            'initialization_results': self.initialization_results,
            'services': self.injector.get_service_info(),
            'service_count': len(self.injector._services),
            'healthy_service_count': sum(
                1 for info in self.injector._services.values() 
                if info.health_status == ServiceStatus.HEALTHY
            )
        }
    
    def shutdown(self):
        """Shutdown the core service and all dependencies"""
        if self.lifecycle in [ServiceLifecycle.STOPPED, ServiceLifecycle.STOPPING]:
            return
        
        logger.info("Shutting down enhanced core service")
        self.lifecycle = ServiceLifecycle.STOPPING
        
        try:
            # Shutdown all services
            self.injector.shutdown_all()
            
            self.lifecycle = ServiceLifecycle.STOPPED
            logger.info("Enhanced core service shutdown completed")
            
        except Exception as e:
            self.lifecycle = ServiceLifecycle.FAILED
            logger.error(f"Error during core service shutdown: {e}")

# Global instance
enhanced_core_service = EnhancedCoreService()