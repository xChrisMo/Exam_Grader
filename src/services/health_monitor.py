"""
Health Monitor - Tracks service status and performance for processing services.

This module provides comprehensive health monitoring for all processing services
with real-time status tracking, performance metrics, and diagnostic information.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque

from src.services.base_service import ServiceStatus
from src.config.processing_config import ProcessingConfigManager
from utils.logger import logger

class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"

@dataclass
class ServiceHealthInfo:
    """Health information for a service."""
    service_name: str
    status: HealthStatus
    last_check: datetime
    response_time_ms: float
    error_count: int
    success_count: int
    uptime_seconds: float
    details: Dict[str, Any]
    dependencies: List[str]
    alerts: List[str]

@dataclass
class HealthMetric:
    """Individual health metric."""
    name: str
    value: Any
    unit: str
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

@dataclass
class HealthAlert:
    """Health alert information."""
    alert_id: str
    service_name: str
    severity: str  # 'info', 'warning', 'critical'
    message: str
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None

class HealthMonitor:
    """
    Monitors service health status and performance with real-time tracking.
    """
    
    def __init__(self, check_interval: int = 30):
        # Initialize processing configuration
        self._config_manager = ProcessingConfigManager()
        self._health_config = self._config_manager.get_health_check_config()
        
        self.check_interval = self._health_config.get_interval('service_health') if self._health_config.enabled else check_interval
        self.services: Dict[str, ServiceHealthInfo] = {}
        self.health_checks: Dict[str, Callable] = {}
        self.metrics_history: Dict[str, deque] = {}
        self.alerts: List[HealthAlert] = []
        self.alert_handlers: List[Callable] = []
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread = None
        self.lock = threading.RLock()
        
        self.max_history_size = self._health_config.health_history_retention if self._health_config.enabled else 1000
        self.alert_cooldown = timedelta(minutes=5)
        self.last_alerts: Dict[str, datetime] = {}
        self.thresholds = self._health_config.thresholds if self._health_config.enabled else None
        
        logger.info(f"HealthMonitor initialized with config-driven settings (interval: {self.check_interval}s)")
    
    def register_service(
        self,
        service_name: str,
        health_check_func: Callable,
        dependencies: List[str] = None
    ):
        """
        Register a service for health monitoring.
        
        Args:
            service_name: Name of the service
            health_check_func: Function that returns health status
            dependencies: List of service dependencies
        """
        with self.lock:
            self.health_checks[service_name] = health_check_func
            
            if service_name not in self.services:
                self.services[service_name] = ServiceHealthInfo(
                    service_name=service_name,
                    status=HealthStatus.UNKNOWN,
                    last_check=datetime.now(timezone.utc),
                    response_time_ms=0.0,
                    error_count=0,
                    success_count=0,
                    uptime_seconds=0.0,
                    details={},
                    dependencies=dependencies or [],
                    alerts=[]
                )
            
            # Initialize metrics history
            if service_name not in self.metrics_history:
                self.metrics_history[service_name] = deque(maxlen=self.max_history_size)
        
        logger.info(f"Registered service for health monitoring: {service_name}")
    
    def unregister_service(self, service_name: str):
        """Unregister a service from health monitoring."""
        with self.lock:
            self.health_checks.pop(service_name, None)
            self.services.pop(service_name, None)
            self.metrics_history.pop(service_name, None)
        
        logger.info(f"Unregistered service from health monitoring: {service_name}")
    
    def check_service_health(self, service_name: str) -> HealthStatus:
        """
        Check health of a specific service.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            HealthStatus of the service
        """
        if service_name not in self.health_checks:
            logger.warning(f"No health check registered for service: {service_name}")
            return HealthStatus.UNKNOWN
        
        start_time = time.time()
        
        try:
            # Execute health check
            health_check_func = self.health_checks[service_name]
            health_result = health_check_func()
            
            response_time = (time.time() - start_time) * 1000
            
            # Parse health result
            if isinstance(health_result, bool):
                status = HealthStatus.HEALTHY if health_result else HealthStatus.UNHEALTHY
                details = {}
            elif isinstance(health_result, dict):
                status_str = health_result.get('status', 'unknown').lower()
                status = HealthStatus(status_str) if status_str in [s.value for s in HealthStatus] else HealthStatus.UNKNOWN
                details = health_result.get('details', {})
            else:
                status = HealthStatus.UNKNOWN
                details = {'raw_result': str(health_result)}
            
            # Update service info
            with self.lock:
                if service_name in self.services:
                    service_info = self.services[service_name]
                    service_info.status = status
                    service_info.last_check = datetime.now(timezone.utc)
                    service_info.response_time_ms = response_time
                    service_info.details = details
                    
                    if status == HealthStatus.HEALTHY:
                        service_info.success_count += 1
                    else:
                        service_info.error_count += 1
                    
                    # Record metric
                    self._record_metric(service_name, HealthMetric(
                        name='response_time',
                        value=response_time,
                        unit='ms',
                        threshold_warning=1000.0,
                        threshold_critical=5000.0
                    ))
                    
                    self._check_alerts(service_name, service_info)
            
            return status
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            logger.error(f"Health check failed for {service_name}: {e}")
            
            # Update service info with error
            with self.lock:
                if service_name in self.services:
                    service_info = self.services[service_name]
                    service_info.status = HealthStatus.UNHEALTHY
                    service_info.last_check = datetime.now(timezone.utc)
                    service_info.response_time_ms = response_time
                    service_info.error_count += 1
                    service_info.details = {'error': str(e)}
                    
                    self._create_alert(
                        service_name=service_name,
                        severity='critical',
                        message=f"Health check failed: {str(e)}"
                    )
            
            return HealthStatus.UNHEALTHY
    
    def get_service_health(self, service_name: str) -> Optional[ServiceHealthInfo]:
        """Get health information for a specific service."""
        with self.lock:
            return self.services.get(service_name)
    
    def get_overall_health(self) -> Dict[str, Any]:
        """
        Get overall system health status.
        
        Returns:
            Dictionary containing overall health information
        """
        with self.lock:
            if not self.services:
                return {
                    'status': HealthStatus.UNKNOWN.value,
                    'message': 'No services registered',
                    'services': {},
                    'summary': {'total': 0, 'healthy': 0, 'degraded': 0, 'unhealthy': 0, 'unknown': 0}
                }
            
            # Count service statuses
            status_counts = {status.value: 0 for status in HealthStatus}
            service_statuses = {}
            
            for service_name, service_info in self.services.items():
                status_counts[service_info.status.value] += 1
                service_statuses[service_name] = {
                    'status': service_info.status.value,
                    'last_check': service_info.last_check.isoformat(),
                    'response_time_ms': service_info.response_time_ms,
                    'error_count': service_info.error_count,
                    'success_count': service_info.success_count,
                    'uptime_seconds': service_info.uptime_seconds,
                    'dependencies': service_info.dependencies,
                    'alerts': len(service_info.alerts)
                }
            
            # Determine overall status
            if status_counts['unhealthy'] > 0:
                overall_status = HealthStatus.UNHEALTHY
                message = f"{status_counts['unhealthy']} services unhealthy"
            elif status_counts['degraded'] > 0:
                overall_status = HealthStatus.DEGRADED
                message = f"{status_counts['degraded']} services degraded"
            elif status_counts['healthy'] == len(self.services):
                overall_status = HealthStatus.HEALTHY
                message = "All services healthy"
            else:
                overall_status = HealthStatus.UNKNOWN
                message = "Some services have unknown status"
            
            return {
                'status': overall_status.value,
                'message': message,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'services': service_statuses,
                'summary': {
                    'total': len(self.services),
                    'healthy': status_counts['healthy'],
                    'degraded': status_counts['degraded'],
                    'unhealthy': status_counts['unhealthy'],
                    'unknown': status_counts['unknown'],
                    'maintenance': status_counts['maintenance']
                },
                'active_alerts': len([a for a in self.alerts if not a.resolved])
            }
    
    def start_monitoring(self):
        """Start continuous health monitoring."""
        if self.monitoring_active:
            logger.warning("Health monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info(f"Started health monitoring with {self.check_interval}s interval")
    
    def stop_monitoring(self):
        """Stop continuous health monitoring."""
        self.monitoring_active = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        try:
            logger.info("Stopped health monitoring")
        except Exception:
            print("Stopped health monitoring")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Check all registered services
                for service_name in list(self.health_checks.keys()):
                    if not self.monitoring_active:
                        break
                    
                    self.check_service_health(service_name)
                
                self._update_uptime()
                
                # Clean up old alerts
                self._cleanup_old_alerts()
                
                # Sleep until next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)
    
    def _update_uptime(self):
        """Update uptime for all services."""
        current_time = datetime.now(timezone.utc)
        
        with self.lock:
            for service_info in self.services.values():
                if service_info.status == HealthStatus.HEALTHY:
                    time_diff = (current_time - service_info.last_check).total_seconds()
                    service_info.uptime_seconds += time_diff
    
    def _record_metric(self, service_name: str, metric: HealthMetric):
        """Record a health metric for a service."""
        if service_name not in self.metrics_history:
            self.metrics_history[service_name] = deque(maxlen=self.max_history_size)
        
        self.metrics_history[service_name].append(metric)
    
    def get_service_metrics(self, service_name: str, metric_name: str = None) -> List[HealthMetric]:
        """Get metrics for a service."""
        if service_name not in self.metrics_history:
            return []
        
        metrics = list(self.metrics_history[service_name])
        
        if metric_name:
            metrics = [m for m in metrics if m.name == metric_name]
        
        return metrics
    
    def _check_alerts(self, service_name: str, service_info: ServiceHealthInfo):
        """Check if alerts should be generated for a service."""
        
        # Check response time alert
        if service_info.response_time_ms > 5000:  # 5 seconds
            self._create_alert(
                service_name=service_name,
                severity='critical',
                message=f"High response time: {service_info.response_time_ms:.0f}ms"
            )
        elif service_info.response_time_ms > 1000:  # 1 second
            self._create_alert(
                service_name=service_name,
                severity='warning',
                message=f"Elevated response time: {service_info.response_time_ms:.0f}ms"
            )
        
        # Check error rate alert
        total_checks = service_info.success_count + service_info.error_count
        if total_checks > 10:  # Only check after some history
            error_rate = service_info.error_count / total_checks
            if error_rate > 0.5:  # 50% error rate
                self._create_alert(
                    service_name=service_name,
                    severity='critical',
                    message=f"High error rate: {error_rate:.1%}"
                )
            elif error_rate > 0.2:  # 20% error rate
                self._create_alert(
                    service_name=service_name,
                    severity='warning',
                    message=f"Elevated error rate: {error_rate:.1%}"
                )
        
        # Check status-based alerts
        if service_info.status == HealthStatus.UNHEALTHY:
            self._create_alert(
                service_name=service_name,
                severity='critical',
                message="Service is unhealthy"
            )
        elif service_info.status == HealthStatus.DEGRADED:
            self._create_alert(
                service_name=service_name,
                severity='warning',
                message="Service is degraded"
            )
    
    def _create_alert(self, service_name: str, severity: str, message: str):
        """Create a new alert."""
        
        # Check cooldown to prevent spam
        alert_key = f"{service_name}:{severity}:{message}"
        current_time = datetime.now(timezone.utc)
        
        if alert_key in self.last_alerts:
            time_since_last = current_time - self.last_alerts[alert_key]
            if time_since_last < self.alert_cooldown:
                return  # Skip alert due to cooldown
        
        # Create alert
        alert = HealthAlert(
            alert_id=f"alert_{int(time.time())}_{len(self.alerts)}",
            service_name=service_name,
            severity=severity,
            message=message,
            timestamp=current_time
        )
        
        self.alerts.append(alert)
        self.last_alerts[alert_key] = current_time
        
        # Add to service alerts
        if service_name in self.services:
            self.services[service_name].alerts.append(alert.alert_id)
        
        # Notify alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
        
        logger.warning(f"Health alert created: {service_name} - {severity} - {message}")
    
    def register_alert_handler(self, handler: Callable[[HealthAlert], None]):
        """Register an alert handler function."""
        self.alert_handlers.append(handler)
        logger.info("Registered alert handler")
    
    def get_alerts(
        self,
        service_name: str = None,
        severity: str = None,
        resolved: bool = None,
        limit: int = 100
    ) -> List[HealthAlert]:
        """Get alerts with optional filtering."""
        
        filtered_alerts = self.alerts
        
        if service_name:
            filtered_alerts = [a for a in filtered_alerts if a.service_name == service_name]
        
        if severity:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity]
        
        if resolved is not None:
            filtered_alerts = [a for a in filtered_alerts if a.resolved == resolved]
        
        # Sort by timestamp (newest first) and limit
        filtered_alerts.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_alerts[:limit]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolution_time = datetime.now(timezone.utc)
                logger.info(f"Resolved alert: {alert_id}")
                return True
        
        logger.warning(f"Alert not found for resolution: {alert_id}")
        return False
    
    def _cleanup_old_alerts(self):
        """Clean up old resolved alerts."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)  # Keep alerts for 7 days
        
        initial_count = len(self.alerts)
        self.alerts = [
            alert for alert in self.alerts
            if not alert.resolved or alert.resolution_time > cutoff_time
        ]
        
        cleaned_count = initial_count - len(self.alerts)
        if cleaned_count > 0:
            logger.debug(f"Cleaned up {cleaned_count} old alerts")
    
    def get_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        
        overall_health = self.get_overall_health()
        
        # Service details
        service_details = {}
        with self.lock:
            for service_name, service_info in self.services.items():
                service_details[service_name] = {
                    'status': service_info.status.value,
                    'last_check': service_info.last_check.isoformat(),
                    'response_time_ms': service_info.response_time_ms,
                    'error_count': service_info.error_count,
                    'success_count': service_info.success_count,
                    'uptime_seconds': service_info.uptime_seconds,
                    'dependencies': service_info.dependencies,
                    'details': service_info.details,
                    'recent_metrics': [
                        asdict(m) for m in list(self.metrics_history.get(service_name, []))[-10:]
                    ]
                }
        
        # Recent alerts
        recent_alerts = [
            asdict(alert) for alert in self.get_alerts(limit=20)
        ]
        
        return {
            'report_type': 'health_monitoring_report',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'overall_health': overall_health,
            'service_details': service_details,
            'recent_alerts': recent_alerts,
            'monitoring_config': {
                'check_interval': self.check_interval,
                'monitoring_active': self.monitoring_active,
                'registered_services': len(self.health_checks),
                'max_history_size': self.max_history_size
            }
        }
    
    def export_health_data(self, output_file: str) -> bool:
        """Export health monitoring data to file."""
        try:
            import json
            from pathlib import Path
            
            health_report = self.get_health_report()
            
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(health_report, f, indent=2, default=str)
            
            logger.info(f"Health data exported to: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export health data: {e}")
            return False

# Global instance
health_monitor = HealthMonitor()