"""Log Aggregation and Analytics System.

This module provides log aggregation, metrics collection, and analytics
for the comprehensive logging system.
"""

import json
import statistics
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
import re
from typing import Optional, Dict, Any, List, Union


@dataclass
class LogMetrics:
    """Metrics collected from log analysis."""
    
    # Time range
    start_time: datetime
    end_time: datetime
    
    # Basic counts
    total_logs: int = 0
    log_level_counts: Dict[str, int] = field(default_factory=dict)
    
    # Error analysis
    error_count: int = 0
    warning_count: int = 0
    critical_count: int = 0
    error_rate: float = 0.0
    
    # Performance metrics
    avg_response_time: Optional[float] = None
    max_response_time: Optional[float] = None
    min_response_time: Optional[float] = None
    response_times: List[float] = field(default_factory=list)
    
    # Operation metrics
    operation_counts: Dict[str, int] = field(default_factory=dict)
    operation_durations: Dict[str, List[float]] = field(default_factory=dict)
    
    # User activity
    active_users: int = 0
    user_activity: Dict[str, int] = field(default_factory=dict)
    
    # System metrics
    memory_usage: List[float] = field(default_factory=list)
    cpu_usage: List[float] = field(default_factory=list)
    
    # Security events
    security_events: int = 0
    failed_logins: int = 0
    suspicious_activities: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'time_range': {
                'start': self.start_time.isoformat(),
                'end': self.end_time.isoformat(),
                'duration_hours': (self.end_time - self.start_time).total_seconds() / 3600
            },
            'basic_counts': {
                'total_logs': self.total_logs,
                'log_level_counts': self.log_level_counts,
                'error_count': self.error_count,
                'warning_count': self.warning_count,
                'critical_count': self.critical_count,
                'error_rate': self.error_rate
            },
            'performance': {
                'avg_response_time': self.avg_response_time,
                'max_response_time': self.max_response_time,
                'min_response_time': self.min_response_time,
                'response_time_count': len(self.response_times)
            },
            'operations': {
                'operation_counts': self.operation_counts,
                'operation_avg_durations': {
                    op: statistics.mean(durations) if durations else 0
                    for op, durations in self.operation_durations.items()
                }
            },
            'user_activity': {
                'active_users': self.active_users,
                'top_users': dict(Counter(self.user_activity).most_common(10))
            },
            'security': {
                'security_events': self.security_events,
                'failed_logins': self.failed_logins,
                'suspicious_activities': self.suspicious_activities
            }
        }


class LogAggregator:
    """Log aggregation and metrics collection system."""
    
    def __init__(self, log_dir: Union[str, Path] = 'logs'):
        """Initialize log aggregator.
        
        Args:
            log_dir: Directory containing log files
        """
        self.log_dir = Path(log_dir)
        self.metrics_cache: Dict[str, LogMetrics] = {}
        self._cache_lock = Lock()
        
        # Patterns for log parsing
        self.log_patterns = {
            'timestamp': re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'),
            'level': re.compile(r'\[(\w+)\]'),
            'response_time': re.compile(r'Duration: ([\d.]+)s'),
            'operation': re.compile(r'operation: ([\w_]+)'),
            'user_id': re.compile(r'user_id["\']?:\s*["\']?([\w-]+)["\']?'),
            'error_id': re.compile(r'\[([\w-]+)\]'),
            'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        }
    
    def analyze_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        log_files: Optional[List[str]] = None
    ) -> LogMetrics:
        """Analyze logs and generate metrics.
        
        Args:
            start_time: Start time for analysis (default: 24 hours ago)
            end_time: End time for analysis (default: now)
            log_files: Specific log files to analyze (default: all)
        
        Returns:
            LogMetrics object with analysis results
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(hours=24)
        
        # Create cache key
        cache_key = f"{start_time.isoformat()}_{end_time.isoformat()}_{log_files}"
        
        with self._cache_lock:
            if cache_key in self.metrics_cache:
                return self.metrics_cache[cache_key]
        
        # Initialize metrics
        metrics = LogMetrics(start_time=start_time, end_time=end_time)
        
        # Get log files to analyze
        if log_files is None:
            log_files = self._get_log_files()
        
        # Analyze each log file
        for log_file in log_files:
            self._analyze_log_file(log_file, metrics, start_time, end_time)
        
        # Calculate derived metrics
        self._calculate_derived_metrics(metrics)
        
        # Cache results
        with self._cache_lock:
            self.metrics_cache[cache_key] = metrics
        
        return metrics
    
    def _get_log_files(self) -> List[str]:
        """Get list of log files to analyze."""
        log_files = []
        
        if self.log_dir.exists():
            for file_path in self.log_dir.glob('*.log'):
                log_files.append(str(file_path))
        
        return log_files
    
    def _analyze_log_file(
        self,
        log_file: str,
        metrics: LogMetrics,
        start_time: datetime,
        end_time: datetime
    ):
        """Analyze a single log file."""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    self._analyze_log_line(line.strip(), metrics, start_time, end_time)
        except Exception as e:
            # Log parsing errors shouldn't break the analysis
            print(f"Error analyzing log file {log_file}: {e}")
    
    def _analyze_log_line(
        self,
        line: str,
        metrics: LogMetrics,
        start_time: datetime,
        end_time: datetime
    ):
        """Analyze a single log line."""
        if not line:
            return
        
        # Extract timestamp
        timestamp_match = self.log_patterns['timestamp'].search(line)
        if timestamp_match:
            try:
                log_time = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                log_time = log_time.replace(tzinfo=timezone.utc)
                
                # Skip logs outside time range
                if log_time < start_time or log_time > end_time:
                    return
            except ValueError:
                return
        else:
            return  # Skip lines without timestamps
        
        metrics.total_logs += 1
        
        # Extract log level
        level_match = self.log_patterns['level'].search(line)
        if level_match:
            level = level_match.group(1)
            metrics.log_level_counts[level] = metrics.log_level_counts.get(level, 0) + 1
            
            # Count specific levels
            if level == 'ERROR':
                metrics.error_count += 1
            elif level == 'WARNING':
                metrics.warning_count += 1
            elif level == 'CRITICAL':
                metrics.critical_count += 1
            elif level == 'SECURITY':
                metrics.security_events += 1
        
        # Extract response time
        response_time_match = self.log_patterns['response_time'].search(line)
        if response_time_match:
            try:
                response_time = float(response_time_match.group(1))
                metrics.response_times.append(response_time)
            except ValueError:
                pass
        
        # Extract operation
        operation_match = self.log_patterns['operation'].search(line)
        if operation_match:
            operation = operation_match.group(1)
            metrics.operation_counts[operation] = metrics.operation_counts.get(operation, 0) + 1
            
            # Extract operation duration if available
            if response_time_match:
                try:
                    duration = float(response_time_match.group(1))
                    if operation not in metrics.operation_durations:
                        metrics.operation_durations[operation] = []
                    metrics.operation_durations[operation].append(duration)
                except ValueError:
                    pass
        
        # Extract user activity
        user_match = self.log_patterns['user_id'].search(line)
        if user_match:
            user_id = user_match.group(1)
            metrics.user_activity[user_id] = metrics.user_activity.get(user_id, 0) + 1
        
        # Detect security events
        if 'failed authentication' in line.lower() or 'login failed' in line.lower():
            metrics.failed_logins += 1
        
        if 'suspicious activity' in line.lower():
            metrics.suspicious_activities += 1
    
    def _calculate_derived_metrics(self, metrics: LogMetrics):
        """Calculate derived metrics from collected data."""
        # Calculate error rate
        if metrics.total_logs > 0:
            metrics.error_rate = (metrics.error_count + metrics.critical_count) / metrics.total_logs * 100
        
        # Calculate response time statistics
        if metrics.response_times:
            metrics.avg_response_time = statistics.mean(metrics.response_times)
            metrics.max_response_time = max(metrics.response_times)
            metrics.min_response_time = min(metrics.response_times)
        
        # Calculate active users
        metrics.active_users = len(metrics.user_activity)
    
    def get_real_time_metrics(self, window_minutes: int = 5) -> LogMetrics:
        """Get real-time metrics for the last N minutes.
        
        Args:
            window_minutes: Time window in minutes
        
        Returns:
            LogMetrics for the specified time window
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=window_minutes)
        
        return self.analyze_logs(start_time, end_time)
    
    def get_hourly_metrics(self, hours: int = 24) -> List[LogMetrics]:
        """Get hourly metrics for the last N hours.
        
        Args:
            hours: Number of hours to analyze
        
        Returns:
            List of LogMetrics, one for each hour
        """
        end_time = datetime.now(timezone.utc)
        metrics_list = []
        
        for i in range(hours):
            hour_end = end_time - timedelta(hours=i)
            hour_start = hour_end - timedelta(hours=1)
            
            hour_metrics = self.analyze_logs(hour_start, hour_end)
            metrics_list.append(hour_metrics)
        
        return list(reversed(metrics_list))  # Return in chronological order
    
    def export_metrics(
        self,
        metrics: LogMetrics,
        format: str = 'json',
        output_file: Optional[str] = None
    ) -> Union[str, Dict[str, Any]]:
        """Export metrics in specified format.
        
        Args:
            metrics: LogMetrics to export
            format: Export format ('json', 'csv', 'dict')
            output_file: Optional output file path
        
        Returns:
            Exported data as string or dict
        """
        if format == 'dict':
            data = metrics.to_dict()
        elif format == 'json':
            data = json.dumps(metrics.to_dict(), indent=2, default=str)
        elif format == 'csv':
            data = self._metrics_to_csv(metrics)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                if isinstance(data, dict):
                    json.dump(data, f, indent=2, default=str)
                else:
                    f.write(data)
        
        return data
    
    def _metrics_to_csv(self, metrics: LogMetrics) -> str:
        """Convert metrics to CSV format."""
        lines = []
        lines.append("metric,value")
        
        # Basic metrics
        lines.append(f"total_logs,{metrics.total_logs}")
        lines.append(f"error_count,{metrics.error_count}")
        lines.append(f"warning_count,{metrics.warning_count}")
        lines.append(f"error_rate,{metrics.error_rate:.2f}")
        
        # Performance metrics
        if metrics.avg_response_time:
            lines.append(f"avg_response_time,{metrics.avg_response_time:.3f}")
            lines.append(f"max_response_time,{metrics.max_response_time:.3f}")
            lines.append(f"min_response_time,{metrics.min_response_time:.3f}")
        
        # User activity
        lines.append(f"active_users,{metrics.active_users}")
        
        # Security
        lines.append(f"security_events,{metrics.security_events}")
        lines.append(f"failed_logins,{metrics.failed_logins}")
        
        return '\n'.join(lines)
    
    def clear_cache(self):
        """Clear metrics cache."""
        with self._cache_lock:
            self.metrics_cache.clear()


class LogAnalytics:
    """Advanced log analytics and insights."""
    
    def __init__(self, aggregator: LogAggregator):
        """Initialize log analytics.
        
        Args:
            aggregator: LogAggregator instance
        """
        self.aggregator = aggregator
    
    def detect_anomalies(
        self,
        current_metrics: LogMetrics,
        baseline_hours: int = 168  # 1 week
    ) -> Dict[str, Any]:
        """Detect anomalies in current metrics compared to baseline.
        
        Args:
            current_metrics: Current metrics to analyze
            baseline_hours: Hours of historical data for baseline
        
        Returns:
            Dictionary of detected anomalies
        """
        # Get baseline metrics
        baseline_end = current_metrics.start_time
        baseline_start = baseline_end - timedelta(hours=baseline_hours)
        baseline_metrics = self.aggregator.analyze_logs(baseline_start, baseline_end)
        
        anomalies = {
            'detected': [],
            'baseline_period': f"{baseline_hours} hours",
            'analysis_time': datetime.now(timezone.utc).isoformat()
        }
        
        # Error rate anomaly
        if baseline_metrics.error_rate > 0:
            error_rate_increase = (current_metrics.error_rate - baseline_metrics.error_rate) / baseline_metrics.error_rate
            if error_rate_increase > 0.5:  # 50% increase
                anomalies['detected'].append({
                    'type': 'error_rate_spike',
                    'severity': 'high' if error_rate_increase > 1.0 else 'medium',
                    'current_value': current_metrics.error_rate,
                    'baseline_value': baseline_metrics.error_rate,
                    'increase_percentage': error_rate_increase * 100
                })
        
        # Response time anomaly
        if (current_metrics.avg_response_time and baseline_metrics.avg_response_time and
            baseline_metrics.avg_response_time > 0):
            response_time_increase = (
                (current_metrics.avg_response_time - baseline_metrics.avg_response_time) /
                baseline_metrics.avg_response_time
            )
            if response_time_increase > 0.3:  # 30% increase
                anomalies['detected'].append({
                    'type': 'response_time_spike',
                    'severity': 'high' if response_time_increase > 0.8 else 'medium',
                    'current_value': current_metrics.avg_response_time,
                    'baseline_value': baseline_metrics.avg_response_time,
                    'increase_percentage': response_time_increase * 100
                })
        
        # Security events anomaly
        if baseline_metrics.security_events > 0:
            security_increase = (
                (current_metrics.security_events - baseline_metrics.security_events) /
                baseline_metrics.security_events
            )
            if security_increase > 0.2:  # 20% increase
                anomalies['detected'].append({
                    'type': 'security_events_spike',
                    'severity': 'critical',
                    'current_value': current_metrics.security_events,
                    'baseline_value': baseline_metrics.security_events,
                    'increase_percentage': security_increase * 100
                })
        
        return anomalies
    
    def generate_insights(self, metrics: LogMetrics) -> Dict[str, Any]:
        """Generate insights from metrics.
        
        Args:
            metrics: LogMetrics to analyze
        
        Returns:
            Dictionary of insights and recommendations
        """
        insights = {
            'summary': {},
            'recommendations': [],
            'trends': {},
            'health_score': 0
        }
        
        # Calculate health score (0-100)
        health_score = 100
        
        # Error rate impact
        if metrics.error_rate > 5:
            health_score -= 30
            insights['recommendations'].append({
                'type': 'error_reduction',
                'priority': 'high',
                'message': f"High error rate ({metrics.error_rate:.1f}%). Investigate and fix recurring errors."
            })
        elif metrics.error_rate > 1:
            health_score -= 10
            insights['recommendations'].append({
                'type': 'error_monitoring',
                'priority': 'medium',
                'message': f"Moderate error rate ({metrics.error_rate:.1f}%). Monitor for trends."
            })
        
        # Response time impact
        if metrics.avg_response_time and metrics.avg_response_time > 2.0:
            health_score -= 20
            insights['recommendations'].append({
                'type': 'performance_optimization',
                'priority': 'high',
                'message': f"Slow average response time ({metrics.avg_response_time:.2f}s). Consider optimization."
            })
        elif metrics.avg_response_time and metrics.avg_response_time > 1.0:
            health_score -= 10
            insights['recommendations'].append({
                'type': 'performance_monitoring',
                'priority': 'medium',
                'message': f"Response time could be improved ({metrics.avg_response_time:.2f}s)."
            })
        
        # Security events impact
        if metrics.failed_logins > 10:
            health_score -= 15
            insights['recommendations'].append({
                'type': 'security_review',
                'priority': 'high',
                'message': f"High number of failed logins ({metrics.failed_logins}). Review security measures."
            })
        
        if metrics.suspicious_activities > 0:
            health_score -= 25
            insights['recommendations'].append({
                'type': 'security_investigation',
                'priority': 'critical',
                'message': f"Suspicious activities detected ({metrics.suspicious_activities}). Immediate investigation required."
            })
        
        insights['health_score'] = max(0, health_score)
        
        # Summary
        insights['summary'] = {
            'total_logs': metrics.total_logs,
            'error_rate': f"{metrics.error_rate:.1f}%",
            'avg_response_time': f"{metrics.avg_response_time:.2f}s" if metrics.avg_response_time else "N/A",
            'active_users': metrics.active_users,
            'security_events': metrics.security_events,
            'health_status': self._get_health_status(insights['health_score'])
        }
        
        return insights
    
    def _get_health_status(self, score: int) -> str:
        """Get health status based on score."""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 40:
            return "Poor"
        else:
            return "Critical"
    
    def compare_periods(
        self,
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime
    ) -> Dict[str, Any]:
        """Compare metrics between two time periods.
        
        Args:
            period1_start: Start of first period
            period1_end: End of first period
            period2_start: Start of second period
            period2_end: End of second period
        
        Returns:
            Comparison results
        """
        metrics1 = self.aggregator.analyze_logs(period1_start, period1_end)
        metrics2 = self.aggregator.analyze_logs(period2_start, period2_end)
        
        comparison = {
            'period1': {
                'start': period1_start.isoformat(),
                'end': period1_end.isoformat(),
                'metrics': metrics1.to_dict()
            },
            'period2': {
                'start': period2_start.isoformat(),
                'end': period2_end.isoformat(),
                'metrics': metrics2.to_dict()
            },
            'changes': {}
        }
        
        # Calculate changes
        changes = comparison['changes']
        
        # Error rate change
        if metrics1.error_rate > 0:
            error_rate_change = ((metrics2.error_rate - metrics1.error_rate) / metrics1.error_rate) * 100
            changes['error_rate_change'] = f"{error_rate_change:+.1f}%"
        
        # Response time change
        if metrics1.avg_response_time and metrics2.avg_response_time:
            response_time_change = ((metrics2.avg_response_time - metrics1.avg_response_time) / metrics1.avg_response_time) * 100
            changes['response_time_change'] = f"{response_time_change:+.1f}%"
        
        # User activity change
        if metrics1.active_users > 0:
            user_activity_change = ((metrics2.active_users - metrics1.active_users) / metrics1.active_users) * 100
            changes['user_activity_change'] = f"{user_activity_change:+.1f}%"
        
        # Log volume change
        if metrics1.total_logs > 0:
            log_volume_change = ((metrics2.total_logs - metrics1.total_logs) / metrics1.total_logs) * 100
            changes['log_volume_change'] = f"{log_volume_change:+.1f}%"
        
        return comparison