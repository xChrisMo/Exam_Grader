"""
Health Monitoring System - Unified system for service health monitoring and diagnostics.

This module integrates HealthMonitor, ServiceRegistry, and DiagnosticCollector
to provide comprehensive health monitoring and diagnostic capabilities.
"""

import threading
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone, timedelta

from src.services.health_monitor import health_monitor, HealthStatus, HealthAlert
from src.services.service_registry import service_registry, ServiceState
from src.services.diagnostic_collector import diagnostic_collector
from utils.logger import logger

class HealthMonitoringSystem:
    """
    Unified health monitoring system that coordinates all health monitoring components.
    """
    
    def __init__(self):
        self.health_monitor = health_monitor
        self.service_registry = service_registry
        self.diagnostic_collector = diagnostic_collector
        
        # System state
        self.system_initialized = False
        self.monitoring_active = False
        self.diagnostic_interval = 300  # 5 minutes
        self.last_diagnostic_collection = None
        
        # Event handlers
        self.alert_handlers: List[Callable] = []
        self.status_change_handlers: List[Callable] = []
        
        # Initialize system
        self._initialize_system()
        
        logger.info("HealthMonitoringSystem initialized")
    
    def _initialize_system(self):
        """Initialize the health monitoring system."""
        try:
            self._register_core_services()
            
            # Set up event handlers
            self._setup_event_handlers()
            
            # Register alert handlers
            self.health_monitor.register_alert_handler(self._handle_health_alert)
            
            self.system_initialized = True
            logger.info("Health monitoring system initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize health monitoring system: {e}")
    
    def _register_core_services(self):
        """Register core processing services for health monitoring."""
        
        # Register core service
        try:
            from src.services.core_service import core_service
            self.register_service_for_monitoring(
                'core_service',
                core_service,
                dependencies=[]
            )
        except ImportError:
            logger.warning("Core service not available for health monitoring")
        
        # Register LLM service
        try:
            from src.services.consolidated_llm_service import ConsolidatedLLMService
            # Would need to get the actual instance
            logger.debug("LLM service registration would be handled by service initialization")
        except ImportError:
            logger.warning("LLM service not available for health monitoring")
        
        # Register file processing service
        try:
            from src.services.file_processing_service import FileProcessingService
            # Would need to get the actual instance
            logger.debug("File processing service registration would be handled by service initialization")
        except ImportError:
            logger.warning("File processing service not available for health monitoring")
        
        # Register template system
        try:
            from src.services.template_resource_system import template_resource_system
            self.register_service_for_monitoring(
                'template_resource_system',
                template_resource_system,
                dependencies=[]
            )
        except ImportError:
            logger.warning("Template resource system not available for health monitoring")
    
    def _setup_event_handlers(self):
        """Set up event handlers for service registry events."""
        
        def on_service_started(service_info):
            logger.info(f"Service started: {service_info.name}")
            self._trigger_status_change_handlers('service_started', service_info.name)
        
        def on_service_failed(service_info):
            logger.error(f"Service failed: {service_info.name}")
            self._trigger_status_change_handlers('service_failed', service_info.name)
        
        def on_service_stopped(service_info):
            logger.info(f"Service stopped: {service_info.name}")
            self._trigger_status_change_handlers('service_stopped', service_info.name)
        
        # Register event handlers
        self.service_registry.add_event_handler('service_started', on_service_started)
        self.service_registry.add_event_handler('service_failed', on_service_failed)
        self.service_registry.add_event_handler('service_stopped', on_service_stopped)
    
    def register_service_for_monitoring(
        self,
        service_name: str,
        service_instance: Any,
        dependencies: List[str] = None,
        group: str = None
    ) -> bool:
        """
        Register a service for both service registry and health monitoring.
        
        Args:
            service_name: Name of the service
            service_instance: Service instance
            dependencies: Service dependencies
            group: Service group
            
        Returns:
            True if registration successful
        """
        try:
            # Register with service registry
            registry_success = self.service_registry.register_service(
                name=service_name,
                service=service_instance,
                dependencies=dependencies,
                group=group
            )
            
            if not registry_success:
                return False
            
            # Create health check function
            def health_check_func():
                try:
                    if hasattr(service_instance, 'health_check'):
                        return service_instance.health_check()
                    elif hasattr(service_instance, 'get_health_status'):
                        status = service_instance.get_health_status()
                        return status.get('status') == 'healthy' if isinstance(status, dict) else False
                    else:
                        return True
                except Exception as e:
                    logger.error(f"Health check failed for {service_name}: {e}")
                    return False
            
            # Register with health monitor
            self.health_monitor.register_service(
                service_name=service_name,
                health_check_func=health_check_func,
                dependencies=dependencies
            )
            
            logger.info(f"Successfully registered service for monitoring: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service for monitoring '{service_name}': {e}")
            return False
    
    def start_monitoring(self):
        """Start comprehensive health monitoring."""
        if not self.system_initialized:
            logger.error("Health monitoring system not initialized")
            return False
        
        if self.monitoring_active:
            logger.warning("Health monitoring is already active")
            return True
        
        try:
            # Start health monitor
            self.health_monitor.start_monitoring()
            
            # Start diagnostic collection
            self._start_diagnostic_collection()
            
            self.monitoring_active = True
            logger.info("Health monitoring system started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start health monitoring: {e}")
            return False
    
    def stop_monitoring(self):
        """Stop health monitoring."""
        try:
            # Stop health monitor
            self.health_monitor.stop_monitoring()
            
            self.monitoring_active = False
            logger.info("Health monitoring system stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop health monitoring: {e}")
    
    def _start_diagnostic_collection(self):
        """Start periodic diagnostic collection."""
        def diagnostic_worker():
            while self.monitoring_active:
                try:
                    # Collect diagnostics periodically
                    if (self.last_diagnostic_collection is None or 
                        datetime.now(timezone.utc) - self.last_diagnostic_collection > timedelta(seconds=self.diagnostic_interval)):
                        
                        self.diagnostic_collector.collect_full_diagnostic()
                        self.last_diagnostic_collection = datetime.now(timezone.utc)
                    
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"Error in diagnostic collection: {e}")
                    time.sleep(60)
        
        diagnostic_thread = threading.Thread(target=diagnostic_worker, daemon=True)
        diagnostic_thread.start()
    
    def get_system_health_status(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        try:
            overall_health = self.health_monitor.get_overall_health()
            
            # Get service registry status
            registry_status = self.service_registry.get_registry_status()
            
            # Get recent diagnostic data
            recent_diagnostics = self.diagnostic_collector.get_diagnostic_history(limit=1)
            latest_diagnostic = recent_diagnostics[0] if recent_diagnostics else None
            
            # Get active alerts
            active_alerts = self.health_monitor.get_alerts(resolved=False, limit=10)
            
            # Determine overall system status
            system_status = self._calculate_overall_system_status(
                overall_health, registry_status, active_alerts
            )
            
            return {
                'system_status': system_status,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'monitoring_active': self.monitoring_active,
                'health_summary': overall_health,
                'service_registry': registry_status,
                'active_alerts': len(active_alerts),
                'recent_alerts': [
                    {
                        'service': alert.service_name,
                        'severity': alert.severity,
                        'message': alert.message,
                        'timestamp': alert.timestamp.isoformat()
                    }
                    for alert in active_alerts[:5]
                ],
                'latest_diagnostic': {
                    'timestamp': latest_diagnostic.timestamp.isoformat(),
                    'recommendations_count': len(latest_diagnostic.recommendations),
                    'system_uptime': latest_diagnostic.system_info.uptime_seconds,
                    'memory_usage_percent': latest_diagnostic.resource_usage.get('memory', {}).get('percent', 0),
                    'cpu_usage_percent': latest_diagnostic.resource_usage.get('cpu', {}).get('overall_percent', 0)
                } if latest_diagnostic else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health status: {e}")
            return {
                'system_status': 'error',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'monitoring_active': self.monitoring_active,
                'error': str(e)
            }
    
    def _calculate_overall_system_status(
        self,
        health_status: Dict[str, Any],
        registry_status: Dict[str, Any],
        active_alerts: List[HealthAlert]
    ) -> str:
        """Calculate overall system status based on various factors."""
        
        # Check health monitor status
        health_status_value = health_status.get('status', 'unknown')
        
        critical_alerts = [a for a in active_alerts if a.severity == 'critical']
        
        # Check service registry health
        failed_services = registry_status.get('service_states', {}).get('failed', 0)
        
        if health_status_value == 'unhealthy' or critical_alerts or failed_services > 0:
            return 'critical'
        elif health_status_value == 'degraded' or len(active_alerts) > 5:
            return 'degraded'
        elif health_status_value == 'healthy':
            return 'healthy'
        else:
            return 'unknown'
    
    def get_service_health_details(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed health information for a specific service."""
        try:
            service_info = self.service_registry.get_service_info(service_name)
            if not service_info:
                return None
            
            health_info = self.health_monitor.get_service_health(service_name)
            
            # Get service metrics
            metrics = self.health_monitor.get_service_metrics(service_name)
            
            # Get service alerts
            service_alerts = self.health_monitor.get_alerts(service_name=service_name, limit=5)
            
            return {
                'service_name': service_name,
                'registry_info': {
                    'state': service_info.state.value,
                    'dependencies': service_info.dependencies,
                    'dependents': service_info.dependents,
                    'registration_time': service_info.registration_time.isoformat(),
                    'initialization_attempts': service_info.initialization_attempts,
                    'metadata': service_info.metadata
                },
                'health_info': {
                    'status': health_info.status.value,
                    'last_check': health_info.last_check.isoformat(),
                    'response_time_ms': health_info.response_time_ms,
                    'error_count': health_info.error_count,
                    'success_count': health_info.success_count,
                    'uptime_seconds': health_info.uptime_seconds,
                    'details': health_info.details
                } if health_info else None,
                'recent_metrics': [
                    {
                        'name': m.name,
                        'value': m.value,
                        'unit': m.unit,
                        'timestamp': m.timestamp.isoformat()
                    }
                    for m in metrics[-10:]  # Last 10 metrics
                ],
                'recent_alerts': [
                    {
                        'severity': alert.severity,
                        'message': alert.message,
                        'timestamp': alert.timestamp.isoformat(),
                        'resolved': alert.resolved
                    }
                    for alert in service_alerts
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get service health details for '{service_name}': {e}")
            return None
    
    def trigger_diagnostic_collection(self) -> bool:
        """Manually trigger diagnostic collection."""
        try:
            report = self.diagnostic_collector.collect_full_diagnostic()
            self.last_diagnostic_collection = datetime.now(timezone.utc)
            
            logger.info("Manual diagnostic collection completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to trigger diagnostic collection: {e}")
            return False
    
    def export_health_report(self, output_file: str) -> bool:
        """Export comprehensive health report."""
        try:
            # Collect current system status
            system_status = self.get_system_health_status()
            
            # Get latest diagnostic report
            diagnostic_report = self.diagnostic_collector.collect_full_diagnostic()
            
            # Combine into comprehensive report
            health_report = {
                'report_type': 'comprehensive_health_report',
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'system_status': system_status,
                'diagnostic_report': diagnostic_report,
                'service_details': {}
            }
            
            # Add detailed service information
            for service_name in self.service_registry.list_services():
                service_details = self.get_service_health_details(service_name)
                if service_details:
                    health_report['service_details'][service_name] = service_details
            
            # Export diagnostic report (which handles the file writing)
            return self.diagnostic_collector.export_diagnostic_report(output_file, diagnostic_report)
            
        except Exception as e:
            logger.error(f"Failed to export health report: {e}")
            return False
    
    def register_alert_handler(self, handler: Callable[[HealthAlert], None]):
        """Register a custom alert handler."""
        self.alert_handlers.append(handler)
        logger.info("Registered custom alert handler")
    
    def register_status_change_handler(self, handler: Callable[[str, str], None]):
        """Register a status change handler."""
        self.status_change_handlers.append(handler)
        logger.info("Registered status change handler")
    
    def _handle_health_alert(self, alert: HealthAlert):
        """Handle health alerts from the health monitor."""
        logger.warning(f"Health alert: {alert.service_name} - {alert.severity} - {alert.message}")
        
        # Trigger custom alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    def _trigger_status_change_handlers(self, event_type: str, service_name: str):
        """Trigger status change handlers."""
        for handler in self.status_change_handlers:
            try:
                handler(event_type, service_name)
            except Exception as e:
                logger.error(f"Status change handler failed: {e}")
    
    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get monitoring system statistics."""
        return {
            'system_initialized': self.system_initialized,
            'monitoring_active': self.monitoring_active,
            'registered_services': len(self.service_registry.services),
            'active_alerts': len(self.health_monitor.get_alerts(resolved=False)),
            'diagnostic_collections': len(self.diagnostic_collector.collection_history),
            'last_diagnostic_collection': self.last_diagnostic_collection.isoformat() if self.last_diagnostic_collection else None,
            'alert_handlers': len(self.alert_handlers),
            'status_change_handlers': len(self.status_change_handlers)
        }

# Global instance
health_monitoring_system = HealthMonitoringSystem()