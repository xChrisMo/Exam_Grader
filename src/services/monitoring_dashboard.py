"""
Monitoring Dashboard Service

This module provides real-time monitoring dashboards and alerting capabilities
for system health, performance metrics, and operational insights.
"""

import time
from datetime import datetime, timezone, timedelta
import json
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from utils.logger import logger

class DashboardType(Enum):
    """Types of monitoring dashboards"""
    SYSTEM_HEALTH = "system_health"
    PERFORMANCE = "performance"
    ERROR_TRACKING = "error_tracking"
    USER_ACTIVITY = "user_activity"
    RESOURCE_USAGE = "resource_usage"
    CACHE_METRICS = "cache_metrics"
    PROCESSING_PIPELINE = "processing_pipeline"

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class DashboardWidget:
    """Dashboard widget configuration"""
    id: str
    title: str
    type: str  # chart, gauge, table, metric, etc.
    data_source: str
    refresh_interval: int = 30  # seconds
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=dict)  # x, y, width, height

@dataclass
class Dashboard:
    """Dashboard configuration"""
    id: str
    name: str
    description: str
    dashboard_type: DashboardType
    widgets: List[DashboardWidget] = field(default_factory=list)
    auto_refresh: bool = True
    refresh_interval: int = 30
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class MonitoringAlert:
    """Monitoring alert"""
    id: str
    title: str
    message: str
    severity: AlertSeverity
    source: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'severity': self.severity.value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'metadata': self.metadata
        }

class DataCollector:
    """Base class for data collectors"""

    def __init__(self, name: str, collection_interval: int = 30):
        self.name = name
        self.collection_interval = collection_interval
        self.enabled = True
        self._last_collection = 0

    def should_collect(self) -> bool:
        """Check if data should be collected"""
        current_time = time.time()
        return (self.enabled and
                current_time - self._last_collection >= self.collection_interval)

    def collect_data(self) -> Dict[str, Any]:
        """Collect data - to be implemented by subclasses"""
        # Default implementation returns empty data
        # Subclasses should override this method with specific data collection logic
        return {
            'collector': self.name,
            'timestamp': time.time(),
            'data': {},
            'status': 'no_implementation'
        }

    def get_data(self) -> Optional[Dict[str, Any]]:
        """Get data if collection interval has passed"""
        if self.should_collect():
            try:
                data = self.collect_data()
                self._last_collection = time.time()
                return data
            except Exception as e:
                logger.error(f"Error collecting data from {self.name}: {e}")
        return None

class SystemHealthCollector(DataCollector):
    """Collector for system health metrics"""

    def __init__(self):
        super().__init__("system_health", 30)

    def collect_data(self) -> Dict[str, Any]:
        """Collect system health data"""
        try:
            # Get system resource usage
            from src.services.resource_optimizer import resource_optimizer
            resources = resource_optimizer.get_system_resources()

            # Get service health status
            from src.services.monitoring.monitoring_service import health_monitor
            health_status = health_monitor.get_overall_health()

            # Get cache statistics
            from src.services.cache_manager import cache_manager
            cache_stats = cache_manager.get_stats()

            return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
                'system_resources': {k: v.to_dict() for k, v in resources.items()},
                'service_health': health_status if health_status else None,
                'cache_stats': cache_stats,
                'overall_status': 'healthy' if all(
                    r.usage_percentage < 90 for r in resources.values()
                ) else 'warning'
            }

        except Exception as e:
            logger.error(f"Error collecting system health data: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'overall_status': 'error'
            }

class PerformanceCollector(DataCollector):
    """Collector for performance metrics"""

    def __init__(self):
        super().__init__("performance", 15)

    def collect_data(self) -> Dict[str, Any]:
        """Collect performance data"""
        try:
            # Get performance metrics
            from src.services.monitoring.monitoring_service import performance_monitor
            summary = performance_monitor.get_performance_summary()

            # Get recent operation stats
            all_stats = performance_monitor.get_all_operation_stats()

            # Calculate aggregate metrics
            total_requests = sum(stats['total_requests'] for stats in all_stats.values())
            avg_success_rate = sum(stats['success_rate'] for stats in all_stats.values()) / max(1, len(all_stats))

            return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
                'summary': summary,
                'operation_stats': all_stats,
                'aggregate_metrics': {
                    'total_requests': total_requests,
                    'average_success_rate': avg_success_rate,
                    'active_operations': len(all_stats)
                }
            }

        except Exception as e:
            logger.error(f"Error collecting performance data: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }

class ErrorTrackingCollector(DataCollector):
    """Collector for error tracking metrics"""

    def __init__(self):
        super().__init__("error_tracking", 60)

    def collect_data(self) -> Dict[str, Any]:
        """Collect error tracking data"""
        try:
            # Get logging metrics
            from src.services.enhanced_logging_service import enhanced_logging_service
            log_metrics = enhanced_logging_service.get_metrics()

            # Get recent alerts
            recent_alerts = performance_monitor.get_alerts(limit=50)

            return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
                'log_metrics': log_metrics.__dict__ if log_metrics else None,
                'recent_alerts': recent_alerts,
                'error_summary': {
                    'total_errors': log_metrics.logs_by_level.get('ERROR', 0) if log_metrics else 0,
                    'critical_errors': log_metrics.logs_by_level.get('CRITICAL', 0) if log_metrics else 0,
                    'error_rate': log_metrics.error_rate if log_metrics else 0.0
                }
            }

        except Exception as e:
            logger.error(f"Error collecting error tracking data: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }

class MonitoringDashboardService:
    """Main monitoring dashboard service"""

    def __init__(self):
        self.dashboards: Dict[str, Dashboard] = {}
        self.data_collectors: Dict[str, DataCollector] = {}
        self.alerts: List[MonitoringAlert] = []
        self.alert_handlers: List[Callable[[MonitoringAlert], None]] = []

        self._monitoring_thread: Optional[threading.Thread] = None
        self._running = False
        self._data_cache: Dict[str, Any] = {}
        self._cache_lock = threading.RLock()

        # Setup default collectors and dashboards
        self._setup_default_collectors()
        self._setup_default_dashboards()

    def _setup_default_collectors(self):
        """Setup default data collectors"""
        self.add_data_collector(SystemHealthCollector())
        self.add_data_collector(PerformanceCollector())
        self.add_data_collector(ErrorTrackingCollector())

    def _setup_default_dashboards(self):
        """Setup default dashboards"""
        # System Health Dashboard
        system_dashboard = Dashboard(
            id="system_health",
            name="System Health",
            description="Overall system health and resource usage",
            dashboard_type=DashboardType.SYSTEM_HEALTH
        )

        system_dashboard.widgets = [
            DashboardWidget(
                id="cpu_usage",
                title="CPU Usage",
                type="gauge",
                data_source="system_health.system_resources.cpu.usage_percentage",
                position={"x": 0, "y": 0, "width": 4, "height": 3}
            ),
            DashboardWidget(
                id="memory_usage",
                title="Memory Usage",
                type="gauge",
                data_source="system_health.system_resources.memory.usage_percentage",
                position={"x": 4, "y": 0, "width": 4, "height": 3}
            ),
            DashboardWidget(
                id="disk_usage",
                title="Disk Usage",
                type="gauge",
                data_source="system_health.system_resources.disk.usage_percentage",
                position={"x": 8, "y": 0, "width": 4, "height": 3}
            ),
            DashboardWidget(
                id="service_status",
                title="Service Status",
                type="table",
                data_source="system_health.service_health.services",
                position={"x": 0, "y": 3, "width": 12, "height": 4}
            )
        ]

        self.add_dashboard(system_dashboard)

        # Performance Dashboard
        performance_dashboard = Dashboard(
            id="performance",
            name="Performance Metrics",
            description="Application performance and operation metrics",
            dashboard_type=DashboardType.PERFORMANCE
        )

        performance_dashboard.widgets = [
            DashboardWidget(
                id="request_rate",
                title="Request Rate",
                type="line_chart",
                data_source="performance.aggregate_metrics.total_requests",
                position={"x": 0, "y": 0, "width": 6, "height": 4}
            ),
            DashboardWidget(
                id="success_rate",
                title="Success Rate",
                type="gauge",
                data_source="performance.aggregate_metrics.average_success_rate",
                position={"x": 6, "y": 0, "width": 6, "height": 4}
            ),
            DashboardWidget(
                id="operation_stats",
                title="Operation Statistics",
                type="table",
                data_source="performance.operation_stats",
                position={"x": 0, "y": 4, "width": 12, "height": 4}
            )
        ]

        self.add_dashboard(performance_dashboard)

        # Error Tracking Dashboard
        error_dashboard = Dashboard(
            id="error_tracking",
            name="Error Tracking",
            description="Error monitoring and alert management",
            dashboard_type=DashboardType.ERROR_TRACKING
        )

        error_dashboard.widgets = [
            DashboardWidget(
                id="error_rate",
                title="Error Rate",
                type="line_chart",
                data_source="error_tracking.error_summary.error_rate",
                position={"x": 0, "y": 0, "width": 6, "height": 4}
            ),
            DashboardWidget(
                id="error_breakdown",
                title="Error Breakdown",
                type="pie_chart",
                data_source="error_tracking.log_metrics.logs_by_level",
                position={"x": 6, "y": 0, "width": 6, "height": 4}
            ),
            DashboardWidget(
                id="recent_alerts",
                title="Recent Alerts",
                type="table",
                data_source="error_tracking.recent_alerts",
                position={"x": 0, "y": 4, "width": 12, "height": 4}
            )
        ]

        self.add_dashboard(error_dashboard)

    def add_dashboard(self, dashboard: Dashboard):
        """Add a dashboard"""
        self.dashboards[dashboard.id] = dashboard
        logger.info(f"Added dashboard: {dashboard.name}")

    def remove_dashboard(self, dashboard_id: str) -> bool:
        """Remove a dashboard"""
        if dashboard_id in self.dashboards:
            del self.dashboards[dashboard_id]
            logger.info(f"Removed dashboard: {dashboard_id}")
            return True
        return False

    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get a dashboard by ID"""
        return self.dashboards.get(dashboard_id)

    def list_dashboards(self) -> List[Dict[str, Any]]:
        """List all dashboards"""
        return [
            {
                'id': dashboard.id,
                'name': dashboard.name,
                'description': dashboard.description,
                'type': dashboard.dashboard_type.value,
                'widget_count': len(dashboard.widgets),
                'last_updated': dashboard.last_updated.isoformat()
            }
            for dashboard in self.dashboards.values()
        ]

    def add_data_collector(self, collector: DataCollector):
        """Add a data collector"""
        self.data_collectors[collector.name] = collector
        logger.info(f"Added data collector: {collector.name}")

    def remove_data_collector(self, name: str) -> bool:
        """Remove a data collector"""
        if name in self.data_collectors:
            del self.data_collectors[name]
            logger.info(f"Removed data collector: {name}")
            return True
        return False

    def get_dashboard_data(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific dashboard"""
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            return None

        dashboard_data = {
            'dashboard': {
                'id': dashboard.id,
                'name': dashboard.name,
                'description': dashboard.description,
                'type': dashboard.dashboard_type.value,
                'last_updated': dashboard.last_updated.isoformat()
            },
            'widgets': [],
            'data': {}
        }

        with self._cache_lock:
            for widget in dashboard.widgets:
                widget_data = {
                    'id': widget.id,
                    'title': widget.title,
                    'type': widget.type,
                    'position': widget.position,
                    'config': widget.config
                }

                data_path = widget.data_source.split('.')
                data_value = self._get_nested_data(self._data_cache, data_path)
                widget_data['data'] = data_value

                dashboard_data['widgets'].append(widget_data)

        return dashboard_data

    def _get_nested_data(self, data: Dict[str, Any], path: List[str]) -> Any:
        """Get nested data using dot notation path"""
        current = data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def create_alert(self, title: str, message: str, severity: AlertSeverity,
                    source: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new alert with cooldown logic"""
        current_time = datetime.now(timezone.utc)

        cooldown_period = timedelta(minutes=5)
        for existing_alert in reversed(self.alerts[-10:]):  # Check last 10 alerts
            if (existing_alert.title == title and
                existing_alert.source == source and
                not existing_alert.resolved and
                current_time - existing_alert.timestamp < cooldown_period):
                # Alert is in cooldown period, don't create duplicate
                logger.debug(f"Alert '{title}' is in cooldown period, skipping")
                return existing_alert.id

        alert_id = f"alert_{int(time.time())}_{len(self.alerts)}"

        alert = MonitoringAlert(
            id=alert_id,
            title=title,
            message=message,
            severity=severity,
            source=source,
            timestamp=current_time,
            metadata=metadata or {}
        )

        self.alerts.append(alert)

        # Call alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")

        logger.warning(f"Alert created: {title} ({severity.value})")
        return alert_id

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now(timezone.utc)
                logger.info(f"Alert resolved: {alert_id}")
                return True
        return False

    def get_alerts(self, severity: Optional[AlertSeverity] = None,
                  resolved: Optional[bool] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alerts with optional filtering"""
        filtered_alerts = []

        for alert in reversed(self.alerts[-limit:]):  # Most recent first
            if severity and alert.severity != severity:
                continue
            if resolved is not None and alert.resolved != resolved:
                continue

            filtered_alerts.append(alert.to_dict())

        return filtered_alerts

    def add_alert_handler(self, handler: Callable[[MonitoringAlert], None]):
        """Add an alert handler"""
        self.alert_handlers.append(handler)
        logger.info("Added alert handler")

    def start_monitoring(self):
        """Start background monitoring"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return

        self._running = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
        self._monitoring_thread.start()
        logger.info("Started monitoring dashboard service")

    def stop_monitoring(self):
        """Stop background monitoring"""
        self._running = False
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)
        try:
            logger.info("Stopped monitoring dashboard service")
        except Exception:
            # Ignore logging errors during shutdown
            pass

    def _monitoring_worker(self):
        """Background monitoring worker"""
        while self._running:
            try:
                with self._cache_lock:
                    for name, collector in self.data_collectors.items():
                        data = collector.get_data()
                        if data:
                            self._data_cache[name] = data

                self._check_alert_conditions()

                time.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Error in monitoring worker: {e}")
                time.sleep(30)  # Wait longer on error

    def _check_alert_conditions(self):
        """Check for conditions that should trigger alerts"""
        try:
            # Check system health
            system_data = self._data_cache.get('system_health', {})
            if system_data.get('overall_status') == 'warning':
                self.create_alert(
                    "System Resource Warning",
                    "System resources are running high",
                    AlertSeverity.MEDIUM,
                    "system_health",
                    {'system_data': system_data}
                )

            # Check error rates
            error_data = self._data_cache.get('error_tracking', {})
            error_summary = error_data.get('error_summary', {})
            if error_summary.get('error_rate', 0) > 0.1:  # 10% error rate
                self.create_alert(
                    "High Error Rate",
                    f"Error rate is {error_summary.get('error_rate', 0):.2%}",
                    AlertSeverity.HIGH,
                    "error_tracking",
                    {'error_data': error_summary}
                )

        except Exception as e:
            logger.error(f"Error checking alert conditions: {e}")

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring service statistics"""
        return {
            'dashboards_count': len(self.dashboards),
            'collectors_count': len(self.data_collectors),
            'active_alerts': len([a for a in self.alerts if not a.resolved]),
            'total_alerts': len(self.alerts),
            'monitoring_active': self._running,
            'data_cache_keys': list(self._data_cache.keys()),
            'last_data_update': max(
                (data.get('timestamp') for data in self._data_cache.values() if isinstance(data, dict) and 'timestamp' in data),
                default=None
            )
        }

# Global instance
monitoring_dashboard_service = MonitoringDashboardService()