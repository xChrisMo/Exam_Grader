"""Error tracking and analytics system for comprehensive error monitoring."""

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from src.models.api_responses import ErrorCode

from .application_errors import ApplicationError, ErrorSeverity

@dataclass
class ErrorMetrics:
    """Error metrics for analytics."""

    total_errors: int = 0
    errors_by_code: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_hour: Dict[str, int] = field(default_factory=dict)
    most_common_errors: List[Tuple[str, int]] = field(default_factory=list)
    error_rate_per_minute: float = 0.0
    recovery_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_errors": self.total_errors,
            "errors_by_code": self.errors_by_code,
            "errors_by_severity": self.errors_by_severity,
            "errors_by_hour": self.errors_by_hour,
            "most_common_errors": self.most_common_errors,
            "error_rate_per_minute": self.error_rate_per_minute,
            "recovery_rate": self.recovery_rate,
        }

class ErrorTracker:
    """Centralized error tracking system with analytics capabilities."""

    def __init__(self, max_errors: int = 10000, retention_hours: int = 24):
        """Initialize error tracker.

        Args:
            max_errors: Maximum number of errors to keep in memory
            retention_hours: Hours to retain error data
        """
        self.max_errors = max_errors
        self.retention_hours = retention_hours
        self.errors: List[Dict[str, Any]] = []
        self.error_counts = Counter()
        self.severity_counts = Counter()
        self.hourly_counts = defaultdict(int)
        self.recovery_attempts = defaultdict(int)
        self.successful_recoveries = defaultdict(int)
        self.total_requests = 0
        self._lock = Lock()

        # Setup logging
        self.logger = logging.getLogger(__name__)

    def track_error(
        self,
        error: ApplicationError,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Track an application error.

        Args:
            error: ApplicationError instance
            user_id: ID of the user who encountered the error
            request_id: Request ID for correlation
            endpoint: API endpoint where error occurred
            additional_context: Additional context information

        Returns:
            Error tracking ID
        """
        with self._lock:
            # Create error record
            error_record = {
                "error_id": error.error_id,
                "timestamp": error.timestamp.isoformat(),
                "error_code": error.error_code.value,
                "message": error.message,
                "user_message": error.user_message,
                "severity": error.severity.value,
                "field": error.field,
                "recoverable": error.recoverable,
                "retry_after": error.retry_after,
                "details": error.details,
                "context": error.context,
                "user_id": user_id,
                "request_id": request_id,
                "endpoint": endpoint,
                "additional_context": additional_context or {},
                "traceback": error.traceback_info,
            }

            # Add to errors list
            self.errors.append(error_record)

            # Update counters
            self.error_counts[error.error_code.value] += 1
            self.severity_counts[error.severity.value] += 1

            # Update hourly counts
            hour_key = error.timestamp.strftime("%Y-%m-%d-%H")
            self.hourly_counts[hour_key] += 1

            # Cleanup old errors
            self._cleanup_old_errors()

            # Log error
            self._log_error(error_record)

            return error.error_id

    def track_recovery_attempt(self, error_id: str, success: bool = False) -> None:
        """Track error recovery attempt.

        Args:
            error_id: ID of the error being recovered
            success: Whether the recovery was successful
        """
        with self._lock:
            self.recovery_attempts[error_id] += 1
            if success:
                self.successful_recoveries[error_id] += 1

    def increment_requests(self, count: int = 1) -> None:
        """Increment total request count.

        Args:
            count: Number of requests to add (default: 1)
        """
        with self._lock:
            self.total_requests += count

    def get_error_by_id(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Get error by ID.

        Args:
            error_id: Error ID to search for

        Returns:
            Error record or None if not found
        """
        with self._lock:
            for error in self.errors:
                if error["error_id"] == error_id:
                    return error.copy()
            return None

    def get_recent_errors(
        self,
        limit: int = 50,
        severity: Optional[ErrorSeverity] = None,
        error_code: Optional[ErrorCode] = None,
        user_id: Optional[str] = None,
        hours: int = 1,
    ) -> List[Dict[str, Any]]:
        """Get recent errors with optional filtering.

        Args:
            limit: Maximum number of errors to return
            severity: Filter by severity level
            error_code: Filter by error code
            user_id: Filter by user ID
            hours: Number of hours to look back

        Returns:
            List of error records
        """
        with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            filtered_errors = []
            for error in reversed(self.errors):  # Most recent first
                error_time = datetime.fromisoformat(error["timestamp"])
                if error_time < cutoff_time:
                    continue

                # Apply filters
                if severity and error["severity"] != severity.value:
                    continue
                if error_code and error["error_code"] != error_code.value:
                    continue
                if user_id and error["user_id"] != user_id:
                    continue

                filtered_errors.append(error.copy())

                if len(filtered_errors) >= limit:
                    break

            return filtered_errors

    def get_error_metrics(self, hours: int = 24) -> ErrorMetrics:
        """Get error metrics for the specified time period.

        Args:
            hours: Number of hours to analyze

        Returns:
            ErrorMetrics object
        """
        with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # Filter errors by time
            recent_errors = [
                error
                for error in self.errors
                if datetime.fromisoformat(error["timestamp"]) >= cutoff_time
            ]

            # Calculate metrics
            total_errors = len(recent_errors)

            # Errors by code
            errors_by_code = Counter(error["error_code"] for error in recent_errors)

            # Errors by severity
            errors_by_severity = Counter(error["severity"] for error in recent_errors)

            # Errors by hour
            errors_by_hour = defaultdict(int)
            for error in recent_errors:
                hour_key = datetime.fromisoformat(error["timestamp"]).strftime(
                    "%Y-%m-%d-%H"
                )
                errors_by_hour[hour_key] += 1

            # Most common errors
            most_common_errors = errors_by_code.most_common(10)

            # Error rate per minute
            minutes = hours * 60
            error_rate_per_minute = total_errors / minutes if minutes > 0 else 0

            # Recovery rate
            total_attempts = sum(self.recovery_attempts.values())
            total_successes = sum(self.successful_recoveries.values())
            recovery_rate = (
                (total_successes / total_attempts * 100) if total_attempts > 0 else 0
            )

            return ErrorMetrics(
                total_errors=total_errors,
                errors_by_code=dict(errors_by_code),
                errors_by_severity=dict(errors_by_severity),
                errors_by_hour=dict(errors_by_hour),
                most_common_errors=most_common_errors,
                error_rate_per_minute=round(error_rate_per_minute, 2),
                recovery_rate=round(recovery_rate, 2),
            )

    def get_error_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get error trends and patterns.

        Args:
            hours: Number of hours to analyze

        Returns:
            Dictionary with trend analysis
        """
        metrics = self.get_error_metrics(hours)

        # Calculate trends
        current_hour_errors = 0
        previous_hour_errors = 0

        current_hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
        previous_hour = (datetime.utcnow() - timedelta(hours=1)).strftime("%Y-%m-%d-%H")

        current_hour_errors = metrics.errors_by_hour.get(current_hour, 0)
        previous_hour_errors = metrics.errors_by_hour.get(previous_hour, 0)

        # Calculate percentage change
        if previous_hour_errors > 0:
            hourly_change = (
                (current_hour_errors - previous_hour_errors) / previous_hour_errors
            ) * 100
        else:
            hourly_change = 100 if current_hour_errors > 0 else 0

        return {
            "current_hour_errors": current_hour_errors,
            "previous_hour_errors": previous_hour_errors,
            "hourly_change_percent": round(hourly_change, 2),
            "trending_up": hourly_change > 10,
            "trending_down": hourly_change < -10,
            "critical_errors": metrics.errors_by_severity.get("critical", 0),
            "high_severity_errors": metrics.errors_by_severity.get("high", 0),
        }

    def export_errors(
        self,
        format_type: str = "json",
        hours: int = 24,
        include_traceback: bool = False,
    ) -> str:
        """Export errors in specified format.

        Args:
            format_type: Export format ('json' or 'csv')
            hours: Number of hours to export
            include_traceback: Whether to include traceback information

        Returns:
            Exported data as string
        """
        recent_errors = self.get_recent_errors(limit=self.max_errors, hours=hours)

        if not include_traceback:
            for error in recent_errors:
                error.pop("traceback", None)

        if format_type.lower() == "json":
            return json.dumps(recent_errors, indent=2, default=str)
        elif format_type.lower() == "csv":
            import csv
            import io

            output = io.StringIO()
            if recent_errors:
                fieldnames = recent_errors[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(recent_errors)

            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def clear_errors(self, older_than_hours: Optional[int] = None) -> int:
        """Clear errors from tracker.

        Args:
            older_than_hours: Only clear errors older than specified hours

        Returns:
            Number of errors cleared
        """
        with self._lock:
            if older_than_hours is None:
                cleared_count = len(self.errors)
                self.errors.clear()
                self.error_counts.clear()
                self.severity_counts.clear()
                self.hourly_counts.clear()
                return cleared_count
            else:
                cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
                original_count = len(self.errors)

                self.errors = [
                    error
                    for error in self.errors
                    if datetime.fromisoformat(error["timestamp"]) >= cutoff_time
                ]

                return original_count - len(self.errors)

    def _cleanup_old_errors(self) -> None:
        """Remove old errors to prevent memory issues."""
        # Remove errors older than retention period
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        self.errors = [
            error
            for error in self.errors
            if datetime.fromisoformat(error["timestamp"]) >= cutoff_time
        ]

        # Limit total number of errors
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors :]

    def _log_error(self, error_record: Dict[str, Any]) -> None:
        """Log error to application logger."""
        severity = error_record["severity"]
        message = f"[{error_record['error_id']}] {error_record['message']}"

        extra = {
            "error_id": error_record["error_id"],
            "error_code": error_record["error_code"],
            "user_id": error_record["user_id"],
            "request_id": error_record["request_id"],
            "endpoint": error_record["endpoint"],
        }

        if severity == "critical":
            self.logger.critical(message, extra=extra)
        elif severity == "high":
            self.logger.error(message, extra=extra)
        elif severity == "medium":
            self.logger.warning(message, extra=extra)
        else:  # low
            self.logger.info(message, extra=extra)

class ErrorAnalytics:
    """Advanced error analytics and reporting."""

    def __init__(self, error_tracker: ErrorTracker):
        """Initialize error analytics.

        Args:
            error_tracker: ErrorTracker instance
        """
        self.error_tracker = error_tracker

    def generate_error_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive error report.

        Args:
            hours: Number of hours to analyze

        Returns:
            Comprehensive error report
        """
        metrics = self.error_tracker.get_error_metrics(hours)
        trends = self.error_tracker.get_error_trends(hours)

        # Get top errors by user
        recent_errors = self.error_tracker.get_recent_errors(limit=1000, hours=hours)
        user_error_counts = Counter(
            error["user_id"] for error in recent_errors if error["user_id"]
        )

        # Get top errors by endpoint
        endpoint_error_counts = Counter(
            error["endpoint"] for error in recent_errors if error["endpoint"]
        )

        return {
            "report_generated_at": datetime.utcnow().isoformat(),
            "analysis_period_hours": hours,
            "metrics": metrics.to_dict(),
            "trends": trends,
            "top_users_with_errors": user_error_counts.most_common(10),
            "top_endpoints_with_errors": endpoint_error_counts.most_common(10),
            "recommendations": self._generate_recommendations(metrics, trends),
        }

    def _generate_recommendations(
        self, metrics: ErrorMetrics, trends: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on error patterns.

        Args:
            metrics: Error metrics
            trends: Error trends

        Returns:
            List of recommendations
        """
        recommendations = []

        # High error rate
        if metrics.error_rate_per_minute > 1.0:
            recommendations.append(
                "High error rate detected. Consider implementing circuit breakers "
                "and rate limiting to prevent cascading failures."
            )

        # Low recovery rate
        if metrics.recovery_rate < 50:
            recommendations.append(
                "Low error recovery rate. Review error handling logic and "
                "implement better retry mechanisms."
            )

        # High critical errors
        if trends["critical_errors"] > 0:
            recommendations.append(
                "Critical errors detected. Immediate investigation required."
            )

        # Trending up
        if trends["trending_up"]:
            recommendations.append(
                "Error rate is trending upward. Monitor system health and "
                "consider scaling resources."
            )

        # Common validation errors
        if (
            metrics.errors_by_code.get("VALIDATION_ERROR", 0)
            > metrics.total_errors * 0.3
        ):
            recommendations.append(
                "High number of validation errors. Review input validation "
                "and provide better user guidance."
            )

        return recommendations

# Global error tracker instance
_global_error_tracker = None

def get_error_tracker() -> ErrorTracker:
    """Get global error tracker instance.

    Returns:
        Global ErrorTracker instance
    """
    global _global_error_tracker
    if _global_error_tracker is None:
        _global_error_tracker = ErrorTracker()
    return _global_error_tracker

def track_error(
    error: ApplicationError,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Convenience function to track an error.

    Args:
        error: ApplicationError instance
        user_id: ID of the user who encountered the error
        request_id: Request ID for correlation
        endpoint: API endpoint where error occurred
        additional_context: Additional context information

    Returns:
        Error tracking ID
    """
    return get_error_tracker().track_error(
        error=error,
        user_id=user_id,
        request_id=request_id,
        endpoint=endpoint,
        additional_context=additional_context,
    )
