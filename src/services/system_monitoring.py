"""
System monitoring and health checks service for LLM training system.
"""

import psutil
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json
import os
from pathlib import Path

from src.database.models import db, ProcessingMetrics, LLMTrainingJob, LLMDocument
from src.utils.logger import get_logger

logger = get_logger(__name__)

class HealthStatus(Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    disk_free_gb: float
    active_processes: int
    database_connections: int
    response_time_ms: float
    error_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class HealthCheck:
    """Health check result."""
    service: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    response_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'service': self.service,
            'status': self.status.value,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'response_time_ms': self.response_time_ms
        }

class SystemMonitoringService:
    """Service for system monitoring and health checks."""
    
    def __init__(self):
        self.alerts = []
        self.metrics_history = []
        self.health_checks = {}
        
        self.cpu_warning_threshold = 90.0  # Increased from 80% to reduce false alarms
        self.cpu_critical_threshold = 98.0  # Increased from 95%
        self.memory_warning_threshold = 85.0
        self.memory_critical_threshold = 95.0
        self.disk_warning_threshold = 90.0
        self.disk_critical_threshold = 95.0
        self.response_time_warning_ms = 5000
        self.response_time_critical_ms = 10000
        self.error_rate_warning = 0.05  # 5%
        self.error_rate_critical = 0.10  # 10%
        
        # Metrics retention (keep last 24 hours)
        self.metrics_retention_hours = 24
        
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system performance metrics."""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024**3)  # Convert to GB
            
            # Process count
            active_processes = len(psutil.pids())
            
            # Database connections (approximate)
            database_connections = self._get_database_connections()
            
            # Response time (test database query)
            response_time_ms = self._measure_database_response_time()
            
            error_rate = self._calculate_error_rate()
            
            metrics = SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                disk_free_gb=disk_free_gb,
                active_processes=active_processes,
                database_connections=database_connections,
                response_time_ms=response_time_ms,
                error_rate=error_rate
            )
            
            # Store metrics
            self._store_metrics(metrics)
            
            self._check_metric_thresholds(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            raise
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        # Collect current metrics
        current_metrics = self.collect_system_metrics()
        
        # Perform health checks
        health_checks = self.perform_health_checks()
        
        # Determine overall status
        overall_status = self._determine_overall_status(health_checks)
        
        # Get recent alerts
        recent_alerts = [alert for alert in self.alerts 
                        if not alert.get('resolved', False) and 
                        alert['timestamp'] > datetime.utcnow() - timedelta(hours=1)]
        
        return {
            'overall_status': overall_status.value,
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': current_metrics.to_dict(),
            'health_checks': {k: v.to_dict() for k, v in health_checks.items()},
            'active_alerts': recent_alerts,
            'system_info': self._get_system_info()
        }
    
    def perform_health_checks(self) -> Dict[str, HealthCheck]:
        """Perform comprehensive health checks."""
        health_checks = {}
        
        # Database health check
        health_checks['database'] = self._check_database_health()
        
        # File system health check
        health_checks['filesystem'] = self._check_filesystem_health()
        
        # LLM training service health check
        health_checks['llm_training'] = self._check_llm_training_health()
        
        self.health_checks = health_checks
        return health_checks
    
    def _get_database_connections(self) -> int:
        """Get approximate number of database connections."""
        try:
            return len(db.engine.pool.checkedout())
        except:
            return 0
    
    def _measure_database_response_time(self) -> float:
        """Measure database response time."""
        try:
            start_time = time.time()
            db.session.execute("SELECT 1").fetchone()
            end_time = time.time()
            return (end_time - start_time) * 1000  # Convert to milliseconds
        except Exception as e:
            logger.error(f"Database response time check failed: {e}")
            return 999999  # Return high value to indicate failure
    
    def _calculate_error_rate(self) -> float:
        """Calculate recent error rate from processing metrics."""
        try:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_metrics = ProcessingMetrics.query.filter(
                ProcessingMetrics.created_at >= one_hour_ago
            ).all()
            
            if not recent_metrics:
                return 0.0
            
            total_operations = len(recent_metrics)
            failed_operations = sum(1 for m in recent_metrics if not m.success)
            
            return failed_operations / total_operations if total_operations > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating error rate: {e}")
            return 0.0
    
    def _store_metrics(self, metrics: SystemMetrics):
        """Store metrics in memory and clean up old data."""
        self.metrics_history.append(metrics)
        
        # Clean up old metrics
        cutoff_time = datetime.utcnow() - timedelta(hours=self.metrics_retention_hours)
        self.metrics_history = [m for m in self.metrics_history if m.timestamp > cutoff_time]
    
    def _check_metric_thresholds(self, metrics: SystemMetrics):
        """Check metrics against thresholds and create alerts."""
        # CPU usage alerts
        if metrics.cpu_usage >= self.cpu_critical_threshold:
            self._create_alert('CRITICAL', 'system', 
                            f'Critical CPU usage: {metrics.cpu_usage:.1f}%',
                            {'cpu_usage': metrics.cpu_usage})
        elif metrics.cpu_usage >= self.cpu_warning_threshold:
            self._create_alert('WARNING', 'system',
                            f'High CPU usage: {metrics.cpu_usage:.1f}%',
                            {'cpu_usage': metrics.cpu_usage})
    
    def _create_alert(self, level: str, service: str, message: str, details: Dict[str, Any] = None):
        """Create a new system alert with cooldown logic."""
        current_time = datetime.utcnow()
        
        cooldown_period = timedelta(minutes=2)
        for existing_alert in reversed(self.alerts[-5:]):  # Check last 5 alerts
            if (existing_alert.get('message') == message and 
                existing_alert.get('service') == service and
                not existing_alert.get('resolved', True) and
                current_time - existing_alert.get('timestamp', current_time) < cooldown_period):
                # Alert is in cooldown period, don't create duplicate
                logger.debug(f"System alert '{message}' is in cooldown period, skipping")
                return
        
        alert = {
            'id': f"{service}_{int(time.time())}",
            'level': level,
            'service': service,
            'message': message,
            'details': details or {},
            'timestamp': current_time,
            'resolved': False
        }
        
        self.alerts.append(alert)
        logger.warning(f"Alert created: {level} - {service}: {message}")
    
    def _check_database_health(self) -> HealthCheck:
        """Check database health."""
        start_time = time.time()
        try:
            db.session.execute("SELECT 1").fetchone()
            response_time = (time.time() - start_time) * 1000
            
            if response_time > self.response_time_critical_ms:
                status = HealthStatus.CRITICAL
                message = f"Database response time critical: {response_time:.0f}ms"
            elif response_time > self.response_time_warning_ms:
                status = HealthStatus.WARNING
                message = f"Database response time slow: {response_time:.0f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = "Database is healthy"
            
            return HealthCheck(
                service='database',
                status=status,
                message=message,
                details={'response_time_ms': response_time},
                timestamp=datetime.utcnow(),
                response_time_ms=response_time
            )
            
        except Exception as e:
            return HealthCheck(
                service='database',
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {str(e)}",
                details={'error': str(e)},
                timestamp=datetime.utcnow(),
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    def _check_filesystem_health(self) -> HealthCheck:
        """Check file system health."""
        start_time = time.time()
        try:
            critical_dirs = ['uploads', 'logs', 'temp', 'instance']
            issues = []
            
            for dir_name in critical_dirs:
                dir_path = Path(dir_name)
                if not dir_path.exists():
                    issues.append(f"Missing directory: {dir_name}")
                elif not os.access(dir_path, os.W_OK):
                    issues.append(f"No write access to: {dir_name}")
            
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            
            if issues:
                status = HealthStatus.CRITICAL
                message = f"File system issues: {', '.join(issues)}"
            elif disk_usage_percent > self.disk_critical_threshold:
                status = HealthStatus.CRITICAL
                message = f"Critical disk usage: {disk_usage_percent:.1f}%"
            elif disk_usage_percent > self.disk_warning_threshold:
                status = HealthStatus.WARNING
                message = f"High disk usage: {disk_usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = "File system is healthy"
            
            return HealthCheck(
                service='filesystem',
                status=status,
                message=message,
                details={
                    'disk_usage_percent': disk_usage_percent,
                    'disk_free_gb': disk.free / (1024**3),
                    'issues': issues
                },
                timestamp=datetime.utcnow(),
                response_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return HealthCheck(
                service='filesystem',
                status=HealthStatus.CRITICAL,
                message=f"File system check failed: {str(e)}",
                details={'error': str(e)},
                timestamp=datetime.utcnow(),
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    def _check_llm_training_health(self) -> HealthCheck:
        """Check LLM training service health."""
        start_time = time.time()
        try:
            stuck_jobs = LLMTrainingJob.query.filter(
                LLMTrainingJob.status.in_(['training', 'preparing']),
                LLMTrainingJob.updated_at < datetime.utcnow() - timedelta(hours=2)
            ).count()
            
            recent_failures = LLMTrainingJob.query.filter(
                LLMTrainingJob.status == 'failed',
                LLMTrainingJob.updated_at > datetime.utcnow() - timedelta(hours=1)
            ).count()
            
            if stuck_jobs > 0:
                status = HealthStatus.WARNING
                message = f"Found {stuck_jobs} potentially stuck training jobs"
            elif recent_failures > 5:
                status = HealthStatus.WARNING
                message = f"High number of recent training failures: {recent_failures}"
            else:
                status = HealthStatus.HEALTHY
                message = "LLM training service is healthy"
            
            return HealthCheck(
                service='llm_training',
                status=status,
                message=message,
                details={
                    'stuck_jobs': stuck_jobs,
                    'recent_failures': recent_failures
                },
                timestamp=datetime.utcnow(),
                response_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return HealthCheck(
                service='llm_training',
                status=HealthStatus.CRITICAL,
                message=f"LLM training health check failed: {str(e)}",
                details={'error': str(e)},
                timestamp=datetime.utcnow(),
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    def _determine_overall_status(self, health_checks: Dict[str, HealthCheck]) -> HealthStatus:
        """Determine overall system status from health checks."""
        if any(check.status == HealthStatus.CRITICAL for check in health_checks.values()):
            return HealthStatus.CRITICAL
        elif any(check.status == HealthStatus.WARNING for check in health_checks.values()):
            return HealthStatus.WARNING
        elif all(check.status == HealthStatus.HEALTHY for check in health_checks.values()):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        return {
            'platform': 'Windows' if os.name == 'nt' else 'Linux',
            'cpu_count': psutil.cpu_count(),
            'total_memory_gb': psutil.virtual_memory().total / (1024**3),
            'uptime_seconds': time.time() - psutil.boot_time()
        }

# Global monitoring service instance
monitoring_service = SystemMonitoringService()