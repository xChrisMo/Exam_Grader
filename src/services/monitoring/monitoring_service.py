"""
Consolidated Monitoring Service

This service consolidates all monitoring functionality from:
- health_monitor.py
- health_monitoring_system.py
- performance_monitor.py
- system_monitoring.py
- monitoring_service_manager.py
"""

import time
from datetime import datetime, timezone
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.services.base_service import BaseService, ServiceStatus
from utils.logger import logger

class HealthStatus(Enum):
    """Health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"

class AlertLevel(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ServiceHealthInfo:
    """Health information for a service"""

    service_name: str
    status: HealthStatus
    last_check: datetime
    response_time_ms: float
    error_count: int
    success_count: int
    uptime_seconds: float
    details: Dict[str, Any]

@dataclass
class PerformanceMetric:
    """Performance metric data"""

    service_name: str
    metric_name: str
    value: float
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class SystemAlert:
    """System alert information"""

    alert_id: str
    service_name: str
    level: AlertLevel
    message: str
    timestamp: datetime
    resolved: bool = False

class MonitoringService(BaseService):
    """Consolidated monitoring service with health, performance, and alerting"""

    def __init__(self, check_interval: int = 30):
        super().__init__("monitoring_service")
        self.check_interval = check_interval

        # Service tracking
        self.services: Dict[str, ServiceHealthInfo] = {}
        self.health_checks: Dict[str, Callable] = {}

        # Performance tracking
        self.performance_metrics: List[PerformanceMetric] = []
        self.max_metrics = 10000

        # Alert tracking
        self.alerts: List[SystemAlert] = []
        self.alert_handlers: List[Callable] = []

        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread = None
        self.lock = threading.RLock()

    async def initialize(self) -> bool:
        """Initialize the monitoring service"""
        try:
            self.status = ServiceStatus.HEALTHY
            logger.info("Monitoring service initialized successfully")
            return True
        except Exception as e:
            self.status = ServiceStatus.UNHEALTHY
            logger.error(f"Failed to initialize monitoring service: {str(e)}")
            return False

    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            return len(self.services) >= 0  # Always healthy if we can track services
        except Exception as e:
            logger.error(f"Monitoring service health check failed: {str(e)}")
            return False

    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            self.stop_monitoring()
            self.services.clear()
            self.performance_metrics.clear()
            self.alerts.clear()
            logger.info("Monitoring service cleanup completed")
        except Exception as e:
            logger.error(f"Error during monitoring service cleanup: {str(e)}")

    def register_service(
        self,
        service_name: str,
        health_check_func: Callable,
        dependencies: List[str] = None,
    ):
        """Register a service for health monitoring"""
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
                )

        logger.info(f"Registered service for monitoring: {service_name}")

    def unregister_service(self, service_name: str):
        """Unregister a service from monitoring"""
        with self.lock:
            self.health_checks.pop(service_name, None)
            self.services.pop(service_name, None)

        logger.info(f"Unregistered service from monitoring: {service_name}")

    def check_service_health(self, service_name: str) -> HealthStatus:
        """Check health of a specific service"""
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
                status = (
                    HealthStatus.HEALTHY if health_result else HealthStatus.UNHEALTHY
                )
            else:
                status = HealthStatus.UNKNOWN

            # Update service info
            with self.lock:
                if service_name in self.services:
                    service_info = self.services[service_name]
                    service_info.status = status
                    service_info.last_check = datetime.now(timezone.utc)
                    service_info.response_time_ms = response_time

                    if status == HealthStatus.HEALTHY:
                        service_info.success_count += 1
                    else:
                        service_info.error_count += 1

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

            return HealthStatus.UNHEALTHY

    def get_service_health(self, service_name: str) -> Optional[ServiceHealthInfo]:
        """Get health information for a specific service"""
        with self.lock:
            return self.services.get(service_name)

    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        with self.lock:
            if not self.services:
                return {
                    "status": HealthStatus.UNKNOWN.value,
                    "message": "No services registered",
                    "services": {},
                    "summary": {
                        "total": 0,
                        "healthy": 0,
                        "degraded": 0,
                        "unhealthy": 0,
                        "unknown": 0,
                    },
                }

            # Count service statuses
            status_counts = {status.value: 0 for status in HealthStatus}
            service_statuses = {}

            for service_name, service_info in self.services.items():
                status_counts[service_info.status.value] += 1
                service_statuses[service_name] = {
                    "status": service_info.status.value,
                    "last_check": service_info.last_check.isoformat(),
                    "response_time_ms": service_info.response_time_ms,
                    "error_count": service_info.error_count,
                    "success_count": service_info.success_count,
                }

            # Determine overall status
            if status_counts["unhealthy"] > 0:
                overall_status = HealthStatus.UNHEALTHY
                message = f"{status_counts['unhealthy']} services unhealthy"
            elif status_counts["degraded"] > 0:
                overall_status = HealthStatus.DEGRADED
                message = f"{status_counts['degraded']} services degraded"
            elif status_counts["healthy"] == len(self.services):
                overall_status = HealthStatus.HEALTHY
                message = "All services healthy"
            else:
                overall_status = HealthStatus.UNKNOWN
                message = "Some services have unknown status"

            return {
                "status": overall_status.value,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "services": service_statuses,
                "summary": {
                    "total": len(self.services),
                    "healthy": status_counts["healthy"],
                    "degraded": status_counts["degraded"],
                    "unhealthy": status_counts["unhealthy"],
                    "unknown": status_counts["unknown"],
                    "maintenance": status_counts["maintenance"],
                },
                "active_alerts": len([a for a in self.alerts if not a.resolved]),
            }

    def record_performance_metric(
        self,
        service_name: str,
        metric_name: str,
        value: float,
        metadata: Dict[str, Any] = None,
    ):
        """Record a performance metric"""
        metric = PerformanceMetric(
            service_name=service_name,
            metric_name=metric_name,
            value=value,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

        with self.lock:
            self.performance_metrics.append(metric)

            # Limit metrics history
            if len(self.performance_metrics) > self.max_metrics:
                self.performance_metrics = self.performance_metrics[-self.max_metrics :]

    def get_performance_metrics(
        self, service_name: str = None, metric_name: str = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get performance metrics with optional filtering"""
        with self.lock:
            filtered_metrics = []

            for metric in self.performance_metrics[-limit:]:
                if service_name and metric.service_name != service_name:
                    continue
                if metric_name and metric.metric_name != metric_name:
                    continue

                filtered_metrics.append(
                    {
                        "service_name": metric.service_name,
                        "metric_name": metric.metric_name,
                        "value": metric.value,
                        "timestamp": metric.timestamp.isoformat(),
                        "metadata": metric.metadata,
                    }
                )

            return filtered_metrics

    def create_alert(self, service_name: str, level: AlertLevel, message: str) -> str:
        """Create a system alert"""
        alert_id = f"alert_{int(time.time())}_{len(self.alerts)}"

        alert = SystemAlert(
            alert_id=alert_id,
            service_name=service_name,
            level=level,
            message=message,
            timestamp=datetime.now(timezone.utc),
        )

        with self.lock:
            self.alerts.append(alert)

        # Notify alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")

        # Log the alert
        log_level = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical,
        }.get(level, logger.info)

        log_level(f"System Alert [{service_name}]: {message}")

        return alert_id

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        with self.lock:
            for alert in self.alerts:
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    logger.info(f"Resolved alert: {alert_id}")
                    return True

        logger.warning(f"Alert not found for resolution: {alert_id}")
        return False

    def get_alerts(
        self,
        service_name: str = None,
        level: AlertLevel = None,
        resolved: bool = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get alerts with optional filtering"""
        with self.lock:
            filtered_alerts = []

            for alert in self.alerts[-limit:]:
                if service_name and alert.service_name != service_name:
                    continue
                if level and alert.level != level:
                    continue
                if resolved is not None and alert.resolved != resolved:
                    continue

                filtered_alerts.append(
                    {
                        "alert_id": alert.alert_id,
                        "service_name": alert.service_name,
                        "level": alert.level.value,
                        "message": alert.message,
                        "timestamp": alert.timestamp.isoformat(),
                        "resolved": alert.resolved,
                    }
                )

            return filtered_alerts

    def register_alert_handler(self, handler: Callable[[SystemAlert], None]):
        """Register an alert handler function"""
        self.alert_handlers.append(handler)
        logger.info("Registered alert handler")

    def start_monitoring(self):
        """Start continuous health monitoring"""
        if self.monitoring_active:
            logger.warning("Monitoring is already active")
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitor_thread.start()

        logger.info(f"Started monitoring with {self.check_interval}s interval")

    def stop_monitoring(self):
        """Stop continuous health monitoring"""
        self.monitoring_active = False

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)

        logger.info("Stopped monitoring")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Check all registered services
                for service_name in list(self.health_checks.keys()):
                    if not self.monitoring_active:
                        break

                    self.check_service_health(service_name)

                # Sleep until next check
                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)

    def get_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        overall_health = self.get_overall_health()

        return {
            "report_type": "monitoring_report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_health": overall_health,
            "performance_metrics_count": len(self.performance_metrics),
            "alerts_count": len(self.alerts),
            "active_alerts_count": len([a for a in self.alerts if not a.resolved]),
            "monitoring_config": {
                "check_interval": self.check_interval,
                "monitoring_active": self.monitoring_active,
                "registered_services": len(self.health_checks),
            },
        }

# Global instances
monitoring_service = MonitoringService()
health_monitor = monitoring_service  # Alias for backward compatibility
performance_monitor = monitoring_service  # Alias for backward compatibility

# Utility functions for backward compatibility
def track_operation(operation_name: str, duration: float = None, success: bool = True, **kwargs):
    """Track an operation for monitoring purposes"""
    try:
        monitoring_service.record_performance_metric(
            "system",
            operation_name,
            duration or 0.0,
            {"success": success, "unit": "ms", **kwargs}
        )
    except Exception as e:
        logger.error(f"Error tracking operation {operation_name}: {e}")

def get_system_health():
    """Get overall system health status"""
    try:
        return monitoring_service.get_system_health()
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return {"status": "unknown", "error": str(e)}
