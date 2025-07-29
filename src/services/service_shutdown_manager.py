"""
Service Shutdown Manager

This module provides proper service shutdown and resource release management,
ensuring all services are gracefully terminated and resources are properly cleaned up.
"""

import time
import threading
import signal
import sys
import atexit
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from utils.logger import logger

class ShutdownPhase(Enum):
    """Phases of shutdown process"""
    INITIATED = "initiated"
    STOPPING_SERVICES = "stopping_services"
    CLEANING_RESOURCES = "cleaning_resources"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"

class ServicePriority(Enum):
    """Priority levels for service shutdown order"""
    CRITICAL = 1    # Shutdown first (e.g., user-facing services)
    HIGH = 2        # Shutdown second (e.g., processing services)
    MEDIUM = 3      # Shutdown third (e.g., caching services)
    LOW = 4         # Shutdown fourth (e.g., logging services)
    CLEANUP = 5     # Shutdown last (e.g., cleanup services)

@dataclass
class ServiceInfo:
    """Information about a registered service"""
    name: str
    shutdown_callback: Callable[[], None]
    priority: ServicePriority
    timeout: float = 30.0  # seconds
    dependencies: List[str] = field(default_factory=list)
    shutdown_time: Optional[float] = None
    shutdown_success: Optional[bool] = None
    shutdown_error: Optional[str] = None

@dataclass
class ShutdownResult:
    """Result of shutdown process"""
    phase: ShutdownPhase
    total_duration: float
    services_shutdown: int
    services_failed: int
    cleanup_results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'phase': self.phase.value,
            'total_duration': self.total_duration,
            'services_shutdown': self.services_shutdown,
            'services_failed': self.services_failed,
            'cleanup_results': self.cleanup_results,
            'errors': self.errors,
            'timestamp': self.timestamp.isoformat()
        }

class ServiceShutdownManager:
    """Manages graceful shutdown of services and resource cleanup"""
    
    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self.shutdown_hooks: List[Callable[[], None]] = []
        self.cleanup_callbacks: List[Callable[[], Dict[str, Any]]] = []
        
        self._shutdown_initiated = False
        self._shutdown_lock = threading.RLock()
        self._shutdown_event = threading.Event()
        self._shutdown_result: Optional[ShutdownResult] = None
        
        # Register signal handlers
        self._register_signal_handlers()
        
        # Register atexit handler
        atexit.register(self._atexit_handler)
    
    def register_service(self, name: str, shutdown_callback: Callable[[], None],
                        priority: ServicePriority = ServicePriority.MEDIUM,
                        timeout: float = 30.0, dependencies: List[str] = None) -> bool:
        """Register a service for managed shutdown"""
        with self._shutdown_lock:
            if self._shutdown_initiated:
                logger.warning(f"Cannot register service {name} - shutdown already initiated")
                return False
            
            if name in self.services:
                logger.warning(f"Service {name} already registered")
                return False
            
            service_info = ServiceInfo(
                name=name,
                shutdown_callback=shutdown_callback,
                priority=priority,
                timeout=timeout,
                dependencies=dependencies or []
            )
            
            self.services[name] = service_info
            logger.info(f"Registered service for shutdown: {name} (priority: {priority.name})")
            return True
    
    def unregister_service(self, name: str) -> bool:
        """Unregister a service"""
        with self._shutdown_lock:
            if name in self.services:
                del self.services[name]
                logger.info(f"Unregistered service: {name}")
                return True
            return False
    
    def register_shutdown_hook(self, hook: Callable[[], None]):
        """Register a shutdown hook to be called during shutdown"""
        self.shutdown_hooks.append(hook)
        logger.debug("Registered shutdown hook")
    
    def register_cleanup_callback(self, callback: Callable[[], Dict[str, Any]]):
        """Register a cleanup callback that returns cleanup results"""
        self.cleanup_callbacks.append(callback)
        logger.debug("Registered cleanup callback")
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info(f"Received signal {signal_name}, initiating graceful shutdown")
            self.shutdown()
        
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    def _atexit_handler(self):
        """Handler called on program exit"""
        if not self._shutdown_initiated:
            logger.info("Program exit detected, initiating cleanup")
            self.shutdown()
    
    def shutdown(self, timeout: float = 60.0) -> ShutdownResult:
        """Initiate graceful shutdown of all services"""
        with self._shutdown_lock:
            if self._shutdown_initiated:
                logger.warning("Shutdown already initiated")
                if self._shutdown_result:
                    return self._shutdown_result
                else:
                    self._shutdown_event.wait(timeout)
                    return self._shutdown_result or ShutdownResult(
                        phase=ShutdownPhase.FAILED,
                        total_duration=0,
                        services_shutdown=0,
                        services_failed=0,
                        errors=["Shutdown timeout"]
                    )
            
            self._shutdown_initiated = True
            start_time = time.time()
            
            logger.info("Initiating graceful shutdown")
            
            result = ShutdownResult(
                phase=ShutdownPhase.INITIATED,
                total_duration=0,
                services_shutdown=0,
                services_failed=0
            )
            
            try:
                # Phase 1: Execute shutdown hooks
                result.phase = ShutdownPhase.STOPPING_SERVICES
                self._execute_shutdown_hooks(result)
                
                # Phase 2: Shutdown services in priority order
                self._shutdown_services(result, timeout)
                
                # Phase 3: Execute cleanup callbacks
                result.phase = ShutdownPhase.CLEANING_RESOURCES
                self._execute_cleanup_callbacks(result)
                
                # Phase 4: Finalize
                result.phase = ShutdownPhase.FINALIZING
                self._finalize_shutdown(result)
                
                result.phase = ShutdownPhase.COMPLETED
                logger.info(f"Graceful shutdown completed in {result.total_duration:.2f}s")
                
            except Exception as e:
                result.phase = ShutdownPhase.FAILED
                result.errors.append(f"Shutdown failed: {str(e)}")
                logger.error(f"Shutdown failed: {e}")
            
            finally:
                result.total_duration = time.time() - start_time
                self._shutdown_result = result
                self._shutdown_event.set()
            
            return result
    
    def _execute_shutdown_hooks(self, result: ShutdownResult):
        """Execute registered shutdown hooks"""
        logger.info(f"Executing {len(self.shutdown_hooks)} shutdown hooks")
        
        for i, hook in enumerate(self.shutdown_hooks):
            try:
                hook()
                logger.debug(f"Executed shutdown hook {i + 1}")
            except Exception as e:
                error_msg = f"Error in shutdown hook {i + 1}: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg)
    
    def _shutdown_services(self, result: ShutdownResult, timeout: float):
        """Shutdown services in priority order"""
        if not self.services:
            logger.info("No services registered for shutdown")
            return
        
        # Group services by priority
        services_by_priority = {}
        for service in self.services.values():
            priority = service.priority
            if priority not in services_by_priority:
                services_by_priority[priority] = []
            services_by_priority[priority].append(service)
        
        # Shutdown services in priority order
        for priority in sorted(services_by_priority.keys(), key=lambda x: x.value):
            services = services_by_priority[priority]
            logger.info(f"Shutting down {len(services)} services with priority {priority.name}")
            
            # Shutdown services in this priority group
            for service in services:
                self._shutdown_service(service, result)
    
    def _shutdown_service(self, service: ServiceInfo, result: ShutdownResult):
        """Shutdown a single service"""
        logger.info(f"Shutting down service: {service.name}")
        start_time = time.time()
        
        try:
            # Create a thread to run the shutdown callback with timeout
            shutdown_thread = threading.Thread(target=service.shutdown_callback)
            shutdown_thread.daemon = True
            shutdown_thread.start()
            
            shutdown_thread.join(timeout=service.timeout)
            
            if shutdown_thread.is_alive():
                # Timeout occurred
                service.shutdown_success = False
                service.shutdown_error = f"Shutdown timeout after {service.timeout}s"
                result.services_failed += 1
                result.errors.append(f"Service {service.name} shutdown timeout")
                logger.error(f"Service {service.name} shutdown timeout")
            else:
                # Shutdown completed
                service.shutdown_success = True
                result.services_shutdown += 1
                logger.info(f"Service {service.name} shutdown completed")
            
        except Exception as e:
            service.shutdown_success = False
            service.shutdown_error = str(e)
            result.services_failed += 1
            result.errors.append(f"Service {service.name} shutdown error: {str(e)}")
            logger.error(f"Error shutting down service {service.name}: {e}")
        
        finally:
            service.shutdown_time = time.time() - start_time
    
    def _execute_cleanup_callbacks(self, result: ShutdownResult):
        """Execute cleanup callbacks"""
        logger.info(f"Executing {len(self.cleanup_callbacks)} cleanup callbacks")
        
        for i, callback in enumerate(self.cleanup_callbacks):
            try:
                cleanup_result = callback()
                result.cleanup_results.append(cleanup_result)
                logger.debug(f"Executed cleanup callback {i + 1}")
            except Exception as e:
                error_msg = f"Error in cleanup callback {i + 1}: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg)
    
    def _finalize_shutdown(self, result: ShutdownResult):
        """Finalize shutdown process"""
        # Log final statistics
        logger.info(f"Shutdown summary: {result.services_shutdown} services shutdown, "
                   f"{result.services_failed} failed, {len(result.cleanup_results)} cleanup operations")
        
        # Force final garbage collection
        try:
            import gc
            collected = gc.collect()
            logger.debug(f"Final garbage collection: {collected} objects collected")
        except Exception as e:
            logger.warning(f"Error in final garbage collection: {e}")
    
    def is_shutdown_initiated(self) -> bool:
        """Check if shutdown has been initiated"""
        return self._shutdown_initiated
    
    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """Wait for shutdown to complete"""
        return self._shutdown_event.wait(timeout)
    
    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered services"""
        with self._shutdown_lock:
            status = {}
            for name, service in self.services.items():
                status[name] = {
                    'name': service.name,
                    'priority': service.priority.name,
                    'timeout': service.timeout,
                    'dependencies': service.dependencies,
                    'shutdown_time': service.shutdown_time,
                    'shutdown_success': service.shutdown_success,
                    'shutdown_error': service.shutdown_error
                }
            return status
    
    def get_shutdown_stats(self) -> Dict[str, Any]:
        """Get shutdown statistics"""
        with self._shutdown_lock:
            return {
                'shutdown_initiated': self._shutdown_initiated,
                'registered_services': len(self.services),
                'shutdown_hooks': len(self.shutdown_hooks),
                'cleanup_callbacks': len(self.cleanup_callbacks),
                'shutdown_result': self._shutdown_result.to_dict() if self._shutdown_result else None,
                'service_status': self.get_service_status()
            }

# Global instance
service_shutdown_manager = ServiceShutdownManager()

# Convenience functions
def register_service_for_shutdown(name: str, shutdown_callback: Callable[[], None],
                                 priority: ServicePriority = ServicePriority.MEDIUM,
                                 timeout: float = 30.0, dependencies: List[str] = None) -> bool:
    """Register a service for managed shutdown"""
    return service_shutdown_manager.register_service(
        name, shutdown_callback, priority, timeout, dependencies
    )

def register_shutdown_hook(hook: Callable[[], None]):
    """Register a shutdown hook"""
    service_shutdown_manager.register_shutdown_hook(hook)

def register_cleanup_callback(callback: Callable[[], Dict[str, Any]]):
    """Register a cleanup callback"""
    service_shutdown_manager.register_cleanup_callback(callback)

def shutdown_services(timeout: float = 60.0) -> ShutdownResult:
    """Initiate graceful shutdown"""
    return service_shutdown_manager.shutdown(timeout)