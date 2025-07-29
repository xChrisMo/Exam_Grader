"""
Monitoring Service Manager

This module manages the lifecycle of all monitoring services and ensures
they are properly initialized, started, and stopped.
"""

import time
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from src.services.monitoring_dashboard import monitoring_dashboard_service
from src.services.enhanced_alerting_system import enhanced_alerting_system
from src.services.realtime_metrics_collector import realtime_metrics_collector
from src.services.health_monitor import health_monitor
from src.services.performance_monitor import performance_monitor
from src.services.cache_manager import cache_manager
from src.config.processing_config import ProcessingConfigManager
from utils.logger import logger

class ServiceState(Enum):
    """Service states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"

class MonitoringServiceManager:
    """
    Manages all monitoring services with proper initialization order
    and dependency management.
    """
    
    def __init__(self):
        self._config_manager = ProcessingConfigManager()
        self._services: Dict[str, Dict[str, Any]] = {}
        self._startup_order = [
            'health_monitor',
            'performance_monitor', 
            'cache_manager',
            'realtime_metrics_collector',
            'monitoring_dashboard',
            'enhanced_alerting'
        ]
        self._running = False
        self._startup_complete = False
        self._lock = threading.RLock()
        
        # Initialize service registry
        self._initialize_service_registry()
        
        logger.info("Monitoring service manager initialized")
    
    def _initialize_service_registry(self):
        """Initialize the service registry with all monitoring services"""
        self._services = {
            'health_monitor': {
                'instance': health_monitor,
                'state': ServiceState.STOPPED,
                'start_method': 'start_monitoring',
                'stop_method': 'stop_monitoring',
                'health_check': 'get_overall_health',
                'dependencies': [],
                'startup_time': None,
                'error_count': 0,
                'last_error': None
            },
            'performance_monitor': {
                'instance': performance_monitor,
                'state': ServiceState.STOPPED,
                'start_method': 'start_monitoring',
                'stop_method': 'stop_monitoring',
                'health_check': 'get_performance_summary',
                'dependencies': [],
                'startup_time': None,
                'error_count': 0,
                'last_error': None
            },
            'cache_manager': {
                'instance': cache_manager,
                'state': ServiceState.STOPPED,
                'start_method': 'start_cleanup_thread',
                'stop_method': 'stop_cleanup_thread',
                'health_check': 'get_stats',
                'dependencies': [],
                'startup_time': None,
                'error_count': 0,
                'last_error': None
            },
            'realtime_metrics_collector': {
                'instance': realtime_metrics_collector,
                'state': ServiceState.STOPPED,
                'start_method': 'start_collection',
                'stop_method': 'stop_collection',
                'health_check': 'get_all_metrics',
                'dependencies': ['health_monitor', 'performance_monitor', 'cache_manager'],
                'startup_time': None,
                'error_count': 0,
                'last_error': None
            },
            'monitoring_dashboard': {
                'instance': monitoring_dashboard_service,
                'state': ServiceState.STOPPED,
                'start_method': 'start_monitoring',
                'stop_method': 'stop_monitoring',
                'health_check': 'get_monitoring_stats',
                'dependencies': ['realtime_metrics_collector'],
                'startup_time': None,
                'error_count': 0,
                'last_error': None
            },
            'enhanced_alerting': {
                'instance': enhanced_alerting_system,
                'state': ServiceState.STOPPED,
                'start_method': 'start_monitoring',
                'stop_method': 'stop_monitoring',
                'health_check': 'get_alert_statistics',
                'dependencies': ['health_monitor', 'performance_monitor', 'monitoring_dashboard'],
                'startup_time': None,
                'error_count': 0,
                'last_error': None
            }
        }
    
    def start_all_services(self) -> bool:
        """Start all monitoring services in proper order"""
        with self._lock:
            if self._running:
                logger.warning("Monitoring services are already running")
                return True
            
            logger.info("Starting all monitoring services...")
            self._running = True
            success_count = 0
            
            for service_name in self._startup_order:
                if service_name not in self._services:
                    logger.error(f"Service {service_name} not found in registry")
                    continue
                
                try:
                    if self._start_service(service_name):
                        success_count += 1
                        logger.info(f"✓ {service_name} started successfully")
                    else:
                        logger.error(f"✗ {service_name} failed to start")
                        
                except Exception as e:
                    logger.error(f"✗ {service_name} startup error: {e}")
                    self._services[service_name]['state'] = ServiceState.ERROR
                    self._services[service_name]['last_error'] = str(e)
                    self._services[service_name]['error_count'] += 1
            
            self._startup_complete = success_count > 0
            
            if self._startup_complete:
                logger.info(f"Monitoring services startup completed: {success_count}/{len(self._startup_order)} services started")
                
                self._start_health_monitoring()
            else:
                logger.error("Failed to start any monitoring services")
                self._running = False
            
            return self._startup_complete
    
    def stop_all_services(self) -> bool:
        """Stop all monitoring services in reverse order"""
        with self._lock:
            if not self._running:
                logger.warning("Monitoring services are not running")
                return True
            
            logger.info("Stopping all monitoring services...")
            self._running = False
            success_count = 0
            
            # Stop in reverse order
            for service_name in reversed(self._startup_order):
                if service_name not in self._services:
                    continue
                
                try:
                    if self._stop_service(service_name):
                        success_count += 1
                        logger.info(f"✓ {service_name} stopped successfully")
                    else:
                        logger.warning(f"✗ {service_name} failed to stop cleanly")
                        
                except Exception as e:
                    logger.error(f"✗ {service_name} shutdown error: {e}")
                    self._services[service_name]['last_error'] = str(e)
                    self._services[service_name]['error_count'] += 1
            
            self._startup_complete = False
            logger.info(f"Monitoring services shutdown completed: {success_count}/{len(self._startup_order)} services stopped")
            
            return success_count == len(self._startup_order)
    
    def restart_all_services(self) -> bool:
        """Restart all monitoring services"""
        logger.info("Restarting all monitoring services...")
        
        # Stop all services
        stop_success = self.stop_all_services()
        
        time.sleep(2)
        
        # Start all services
        start_success = self.start_all_services()
        
        return stop_success and start_success
    
    def _start_service(self, service_name: str) -> bool:
        """Start a specific service"""
        service_info = self._services[service_name]
        
        # Check dependencies
        for dep_name in service_info['dependencies']:
            if dep_name in self._services:
                dep_state = self._services[dep_name]['state']
                if dep_state != ServiceState.RUNNING:
                    logger.warning(f"Dependency {dep_name} for {service_name} is not running (state: {dep_state.value})")
        
        # Update state
        service_info['state'] = ServiceState.STARTING
        
        try:
            instance = service_info['instance']
            start_method = service_info['start_method']
            
            if hasattr(instance, start_method):
                method = getattr(instance, start_method)
                method()
                
                # Record startup time
                service_info['startup_time'] = datetime.utcnow()
                service_info['state'] = ServiceState.RUNNING
                service_info['last_error'] = None
                
                return True
            else:
                logger.error(f"Service {service_name} does not have method {start_method}")
                service_info['state'] = ServiceState.ERROR
                return False
                
        except Exception as e:
            logger.error(f"Error starting service {service_name}: {e}")
            service_info['state'] = ServiceState.ERROR
            service_info['last_error'] = str(e)
            service_info['error_count'] += 1
            return False
    
    def _stop_service(self, service_name: str) -> bool:
        """Stop a specific service"""
        service_info = self._services[service_name]
        
        if service_info['state'] != ServiceState.RUNNING:
            return True  # Already stopped
        
        # Update state
        service_info['state'] = ServiceState.STOPPING
        
        try:
            instance = service_info['instance']
            stop_method = service_info['stop_method']
            
            if hasattr(instance, stop_method):
                method = getattr(instance, stop_method)
                method()
                
                service_info['state'] = ServiceState.STOPPED
                service_info['startup_time'] = None
                
                return True
            else:
                logger.warning(f"Service {service_name} does not have method {stop_method}")
                service_info['state'] = ServiceState.STOPPED
                return True
                
        except Exception as e:
            logger.error(f"Error stopping service {service_name}: {e}")
            service_info['state'] = ServiceState.ERROR
            service_info['last_error'] = str(e)
            service_info['error_count'] += 1
            return False
    
    def _start_health_monitoring(self):
        """Start health monitoring for the service manager"""
        def health_check_worker():
            while self._running:
                try:
                    self._perform_health_checks()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    logger.error(f"Error in service manager health check: {e}")
                    time.sleep(60)
        
        health_thread = threading.Thread(target=health_check_worker, daemon=True)
        health_thread.start()
        logger.info("Service manager health monitoring started")
    
    def _perform_health_checks(self):
        """Perform health checks on all services"""
        with self._lock:
            for service_name, service_info in self._services.items():
                if service_info['state'] != ServiceState.RUNNING:
                    continue
                
                try:
                    instance = service_info['instance']
                    health_method = service_info['health_check']
                    
                    if hasattr(instance, health_method):
                        method = getattr(instance, health_method)
                        result = method()
                        
                        if result is not None:
                            # Service is healthy, reset error count
                            if service_info['error_count'] > 0:
                                logger.info(f"Service {service_name} recovered from errors")
                                service_info['error_count'] = 0
                                service_info['last_error'] = None
                        else:
                            # Service might be unhealthy
                            service_info['error_count'] += 1
                            if service_info['error_count'] > 3:
                                logger.warning(f"Service {service_name} appears unhealthy (no response from health check)")
                    
                except Exception as e:
                    service_info['error_count'] += 1
                    service_info['last_error'] = str(e)
                    
                    if service_info['error_count'] > 5:
                        logger.error(f"Service {service_name} has persistent health check failures: {e}")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all monitoring services"""
        with self._lock:
            status = {
                'manager_running': self._running,
                'startup_complete': self._startup_complete,
                'services': {}
            }
            
            for service_name, service_info in self._services.items():
                status['services'][service_name] = {
                    'state': service_info['state'].value,
                    'startup_time': service_info['startup_time'].isoformat() if service_info['startup_time'] else None,
                    'error_count': service_info['error_count'],
                    'last_error': service_info['last_error'],
                    'dependencies': service_info['dependencies']
                }
            
            return status
    
    def is_service_running(self, service_name: str) -> bool:
        """Check if a specific service is running"""
        if service_name not in self._services:
            return False
        
        return self._services[service_name]['state'] == ServiceState.RUNNING
    
    def restart_service(self, service_name: str) -> bool:
        """Restart a specific service"""
        if service_name not in self._services:
            logger.error(f"Service {service_name} not found")
            return False
        
        logger.info(f"Restarting service: {service_name}")
        
        # Stop the service
        stop_success = self._stop_service(service_name)
        
        # Wait a moment
        time.sleep(1)
        
        # Start the service
        start_success = self._start_service(service_name)
        
        return stop_success and start_success

# Global instance
monitoring_service_manager = MonitoringServiceManager()