"""
Performance Monitor

This module provides comprehensive performance monitoring and metrics collection
for processing operations, including operation tracking, performance analysis,
and alerting capabilities.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import deque, defaultdict
import statistics
import json

from utils.logger import logger

class MetricType(Enum):
    """Types of performance metrics"""
    DURATION = "duration"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    CACHE_HIT_RATE = "cache_hit_rate"
    QUEUE_SIZE = "queue_size"
    CUSTOM = "custom"

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    operation: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'operation': self.operation,
            'metric_type': self.metric_type.value,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }

@dataclass
class OperationStats:
    """Statistics for an operation"""
    operation: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=1000))
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        return self.successful_requests / max(1, self.total_requests)
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate"""
        return self.failed_requests / max(1, self.total_requests)
    
    @property
    def average_duration(self) -> float:
        """Calculate average duration"""
        return self.total_duration / max(1, self.successful_requests)
    
    @property
    def recent_average_duration(self) -> float:
        """Calculate recent average duration"""
        if not self.recent_durations:
            return 0.0
        return statistics.mean(self.recent_durations)
    
    @property
    def throughput(self) -> float:
        """Calculate throughput (requests per second)"""
        if self.total_requests == 0:
            return 0.0
        
        # Calculate based on recent activity (last hour)
        now = datetime.now(timezone.utc)
        time_window = timedelta(hours=1)
        
        # This is a simplified calculation
        # In a real implementation, you'd track timestamps
        return self.total_requests / 3600.0  # Rough estimate
    
    def update(self, duration: float, success: bool):
        """Update statistics with new data point"""
        self.total_requests += 1
        self.last_updated = datetime.now(timezone.utc)
        
        if success:
            self.successful_requests += 1
            self.total_duration += duration
            self.min_duration = min(self.min_duration, duration)
            self.max_duration = max(self.max_duration, duration)
            self.recent_durations.append(duration)
        else:
            self.failed_requests += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'operation': self.operation,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.success_rate,
            'error_rate': self.error_rate,
            'average_duration': self.average_duration,
            'recent_average_duration': self.recent_average_duration,
            'min_duration': self.min_duration if self.min_duration != float('inf') else 0,
            'max_duration': self.max_duration,
            'throughput': self.throughput,
            'last_updated': self.last_updated.isoformat()
        }

@dataclass
class PerformanceAlert:
    """Performance alert"""
    operation: str
    metric_type: MetricType
    level: AlertLevel
    message: str
    value: float
    threshold: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'operation': self.operation,
            'metric_type': self.metric_type.value,
            'level': self.level.value,
            'message': self.message,
            'value': self.value,
            'threshold': self.threshold,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }

@dataclass
class AlertRule:
    """Alert rule configuration"""
    operation: str
    metric_type: MetricType
    threshold: float
    level: AlertLevel
    condition: str  # 'greater_than', 'less_than', 'equals'
    enabled: bool = True
    cooldown_seconds: int = 300  # 5 minutes
    last_triggered: Optional[datetime] = None
    
    def should_trigger(self, value: float) -> bool:
        """Check if alert should trigger"""
        if not self.enabled:
            return False
        
        # Check cooldown
        if self.last_triggered:
            cooldown_elapsed = (datetime.now(timezone.utc) - self.last_triggered).total_seconds()
            if cooldown_elapsed < self.cooldown_seconds:
                return False
        
        # Check condition
        if self.condition == 'greater_than':
            return value > self.threshold
        elif self.condition == 'less_than':
            return value < self.threshold
        elif self.condition == 'equals':
            return abs(value - self.threshold) < 0.001
        
        return False

class PerformanceMonitor:
    """Comprehensive performance monitoring system"""
    
    def __init__(self, max_metrics: int = 10000, max_alerts: int = 1000):
        self.max_metrics = max_metrics
        self.max_alerts = max_alerts
        
        self._metrics: deque = deque(maxlen=max_metrics)
        self._operation_stats: Dict[str, OperationStats] = {}
        self._alert_rules: Dict[str, List[AlertRule]] = defaultdict(list)
        self._alerts: deque = deque(maxlen=max_alerts)
        self._alert_handlers: List[Callable[[PerformanceAlert], None]] = []
        
        self._lock = threading.RLock()
        
        # Setup default alert rules
        self._setup_default_alert_rules()
    
    def start_monitoring(self):
        """Start monitoring (compatibility method for service manager)"""
        logger.info("Performance monitoring started")
        return True
    
    def _setup_default_alert_rules(self):
        """Setup default alert rules"""
        # High error rate alerts
        self.add_alert_rule(
            operation="*",  # All operations
            metric_type=MetricType.ERROR_RATE,
            threshold=0.1,  # 10% error rate
            level=AlertLevel.WARNING,
            condition="greater_than"
        )
        
        self.add_alert_rule(
            operation="*",
            metric_type=MetricType.ERROR_RATE,
            threshold=0.25,  # 25% error rate
            level=AlertLevel.ERROR,
            condition="greater_than"
        )
        
        # Slow operation alerts
        self.add_alert_rule(
            operation="*",
            metric_type=MetricType.DURATION,
            threshold=10.0,  # 10 seconds
            level=AlertLevel.WARNING,
            condition="greater_than"
        )
        
        self.add_alert_rule(
            operation="*",
            metric_type=MetricType.DURATION,
            threshold=30.0,  # 30 seconds
            level=AlertLevel.ERROR,
            condition="greater_than"
        )
        
        # Low cache hit rate
        self.add_alert_rule(
            operation="*",
            metric_type=MetricType.CACHE_HIT_RATE,
            threshold=0.5,  # 50% hit rate
            level=AlertLevel.WARNING,
            condition="less_than"
        )
    
    def track_operation(self, operation: str, duration: float, success: bool = True,
                       metadata: Optional[Dict[str, Any]] = None):
        """Track an operation's performance"""
        with self._lock:
            # Update operation statistics
            if operation not in self._operation_stats:
                self._operation_stats[operation] = OperationStats(operation)
            
            self._operation_stats[operation].update(duration, success)
            
            # Add metric
            metric = PerformanceMetric(
                operation=operation,
                metric_type=MetricType.DURATION,
                value=duration,
                timestamp=datetime.now(timezone.utc),
                metadata=metadata or {}
            )
            self._metrics.append(metric)
            
            self._check_alerts(operation, MetricType.DURATION, duration)
            
            # Check error rate alerts
            stats = self._operation_stats[operation]
            self._check_alerts(operation, MetricType.ERROR_RATE, stats.error_rate)
    
    def track_metric(self, operation: str, metric_type: MetricType, value: float,
                    metadata: Optional[Dict[str, Any]] = None):
        """Track a custom metric"""
        with self._lock:
            metric = PerformanceMetric(
                operation=operation,
                metric_type=metric_type,
                value=value,
                timestamp=datetime.now(timezone.utc),
                metadata=metadata or {}
            )
            self._metrics.append(metric)
            
            self._check_alerts(operation, metric_type, value)
    
    def get_operation_stats(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific operation"""
        with self._lock:
            if operation in self._operation_stats:
                return self._operation_stats[operation].to_dict()
            return None
    
    def get_all_operation_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all operations"""
        with self._lock:
            return {
                op: stats.to_dict() 
                for op, stats in self._operation_stats.items()
            }
    
    def get_metrics(self, operation: Optional[str] = None, 
                   metric_type: Optional[MetricType] = None,
                   since: Optional[datetime] = None,
                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get metrics with optional filtering"""
        with self._lock:
            filtered_metrics = []
            
            for metric in self._metrics:
                # Filter by operation
                if operation and metric.operation != operation:
                    continue
                
                # Filter by metric type
                if metric_type and metric.metric_type != metric_type:
                    continue
                
                # Filter by time
                if since and metric.timestamp < since:
                    continue
                
                filtered_metrics.append(metric.to_dict())
                
                # Apply limit
                if limit and len(filtered_metrics) >= limit:
                    break
            
            return filtered_metrics
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        with self._lock:
            total_operations = len(self._operation_stats)
            total_requests = sum(stats.total_requests for stats in self._operation_stats.values())
            total_errors = sum(stats.failed_requests for stats in self._operation_stats.values())
            
            # Calculate overall metrics
            overall_error_rate = total_errors / max(1, total_requests)
            
            # Find slowest operations
            slowest_ops = sorted(
                [(op, stats.average_duration) for op, stats in self._operation_stats.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            # Find operations with highest error rates
            error_prone_ops = sorted(
                [(op, stats.error_rate) for op, stats in self._operation_stats.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            return {
                'total_operations': total_operations,
                'total_requests': total_requests,
                'total_errors': total_errors,
                'overall_error_rate': overall_error_rate,
                'total_metrics': len(self._metrics),
                'total_alerts': len(self._alerts),
                'slowest_operations': [{'operation': op, 'avg_duration': dur} for op, dur in slowest_ops],
                'error_prone_operations': [{'operation': op, 'error_rate': rate} for op, rate in error_prone_ops],
                'recent_alerts': [alert.to_dict() for alert in list(self._alerts)[-10:]]
            }
    
    def add_alert_rule(self, operation: str, metric_type: MetricType, threshold: float,
                      level: AlertLevel, condition: str, cooldown_seconds: int = 300):
        """Add an alert rule"""
        with self._lock:
            rule = AlertRule(
                operation=operation,
                metric_type=metric_type,
                threshold=threshold,
                level=level,
                condition=condition,
                cooldown_seconds=cooldown_seconds
            )
            
            self._alert_rules[operation].append(rule)
            logger.info(f"Added alert rule: {operation} {metric_type.value} {condition} {threshold}")
    
    def remove_alert_rule(self, operation: str, metric_type: MetricType) -> bool:
        """Remove alert rules for operation and metric type"""
        with self._lock:
            if operation in self._alert_rules:
                original_count = len(self._alert_rules[operation])
                self._alert_rules[operation] = [
                    rule for rule in self._alert_rules[operation]
                    if rule.metric_type != metric_type
                ]
                removed_count = original_count - len(self._alert_rules[operation])
                
                if not self._alert_rules[operation]:
                    del self._alert_rules[operation]
                
                return removed_count > 0
            return False
    
    def add_alert_handler(self, handler: Callable[[PerformanceAlert], None]):
        """Add an alert handler function"""
        self._alert_handlers.append(handler)
        logger.info("Added performance alert handler")
    
    def get_alerts(self, level: Optional[AlertLevel] = None,
                  since: Optional[datetime] = None,
                  limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get alerts with optional filtering"""
        with self._lock:
            filtered_alerts = []
            
            for alert in self._alerts:
                # Filter by level
                if level and alert.level != level:
                    continue
                
                # Filter by time
                if since and alert.timestamp < since:
                    continue
                
                filtered_alerts.append(alert.to_dict())
                
                # Apply limit
                if limit and len(filtered_alerts) >= limit:
                    break
            
            return filtered_alerts
    
    def clear_metrics(self, operation: Optional[str] = None):
        """Clear metrics, optionally for specific operation"""
        with self._lock:
            if operation:
                self._metrics = deque(
                    (m for m in self._metrics if m.operation != operation),
                    maxlen=self.max_metrics
                )
                # Clear operation stats
                if operation in self._operation_stats:
                    del self._operation_stats[operation]
            else:
                # Clear all metrics
                self._metrics.clear()
                self._operation_stats.clear()
            
            logger.info(f"Cleared metrics for: {operation or 'all operations'}")
    
    def clear_alerts(self):
        """Clear all alerts"""
        with self._lock:
            self._alerts.clear()
            logger.info("Cleared all alerts")
    
    def _check_alerts(self, operation: str, metric_type: MetricType, value: float):
        """Check if any alert rules should trigger"""
        # Check operation-specific rules
        rules_to_check = self._alert_rules.get(operation, [])
        
        # Check wildcard rules
        rules_to_check.extend(self._alert_rules.get("*", []))
        
        for rule in rules_to_check:
            if rule.metric_type == metric_type and rule.should_trigger(value):
                self._trigger_alert(rule, operation, value)
    
    def _trigger_alert(self, rule: AlertRule, operation: str, value: float):
        """Trigger an alert"""
        rule.last_triggered = datetime.now(timezone.utc)
        
        alert = PerformanceAlert(
            operation=operation,
            metric_type=rule.metric_type,
            level=rule.level,
            message=f"{operation} {rule.metric_type.value} {rule.condition} {rule.threshold} (actual: {value})",
            value=value,
            threshold=rule.threshold,
            timestamp=datetime.now(timezone.utc)
        )
        
        self._alerts.append(alert)
        
        # Call alert handlers
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
        
        # Log the alert
        log_level = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }.get(rule.level, logger.info)
        
        log_level(f"Performance Alert: {alert.message}")
    
    def export_metrics(self, filepath: str, format: str = 'json'):
        """Export metrics to file"""
        with self._lock:
            data = {
                'metrics': [metric.to_dict() for metric in self._metrics],
                'operation_stats': self.get_all_operation_stats(),
                'alerts': [alert.to_dict() for alert in self._alerts],
                'exported_at': datetime.now(timezone.utc).isoformat()
            }
            
            try:
                if format.lower() == 'json':
                    with open(filepath, 'w') as f:
                        json.dump(data, f, indent=2)
                else:
                    raise ValueError(f"Unsupported export format: {format}")
                
                logger.info(f"Exported metrics to {filepath}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to export metrics: {e}")
                return False

class OperationTracker:
    """Context manager for tracking operation performance"""
    
    def __init__(self, monitor: PerformanceMonitor, operation: str, 
                 metadata: Optional[Dict[str, Any]] = None):
        self.monitor = monitor
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None
        self.success = True
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.success = exc_type is None
            
            self.monitor.track_operation(
                self.operation,
                duration,
                self.success,
                self.metadata
            )
    
    def set_metadata(self, key: str, value: Any):
        """Add metadata to the operation"""
        self.metadata[key] = value
    
    def mark_failure(self):
        """Mark the operation as failed"""
        self.success = False

# Global instance
performance_monitor = PerformanceMonitor()

def track_operation(operation: str, metadata: Optional[Dict[str, Any]] = None):
    """Decorator/context manager for tracking operations"""
    return OperationTracker(performance_monitor, operation, metadata)