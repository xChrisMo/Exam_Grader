"""Tests for error tracking and analytics."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.exceptions.error_tracker import (
    ErrorMetrics,
    ErrorTracker,
    ErrorAnalytics
)
from src.exceptions.application_errors import (
    ApplicationError,
    ValidationError,
    AuthenticationError,
    ProcessingError,
    ErrorSeverity
)
from src.models.api_responses import ErrorCode


class TestErrorMetrics:
    """Test ErrorMetrics dataclass."""
    
    def test_error_metrics_creation(self):
        """Test error metrics creation."""
        metrics = ErrorMetrics(
            total_errors=100,
            errors_by_code={'VALIDATION_ERROR': 50, 'AUTH_ERROR': 30},
            errors_by_severity={'high': 20, 'medium': 60, 'low': 20},
            error_rate=0.05,
            avg_resolution_time=120.5,
            most_common_error='VALIDATION_ERROR',
            trend_direction='increasing'
        )
        
        assert metrics.total_errors == 100
        assert metrics.errors_by_code['VALIDATION_ERROR'] == 50
        assert metrics.errors_by_severity['high'] == 20
        assert metrics.error_rate == 0.05
        assert metrics.avg_resolution_time == 120.5
        assert metrics.most_common_error == 'VALIDATION_ERROR'
        assert metrics.trend_direction == 'increasing'
    
    def test_error_metrics_defaults(self):
        """Test error metrics with default values."""
        metrics = ErrorMetrics()
        
        assert metrics.total_errors == 0
        assert metrics.errors_by_code == {}
        assert metrics.errors_by_severity == {}
        assert metrics.error_rate == 0.0
        assert metrics.avg_resolution_time == 0.0
        assert metrics.most_common_error is None
        assert metrics.trend_direction == 'stable'


class TestErrorTracker:
    """Test ErrorTracker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = ErrorTracker(max_errors=100)
    
    def test_error_tracker_initialization(self):
        """Test error tracker initialization."""
        assert self.tracker.max_errors == 100
        assert len(self.tracker.errors) == 0
        assert len(self.tracker.resolved_errors) == 0
        assert self.tracker.total_requests == 0
    
    def test_track_error(self):
        """Test tracking an error."""
        error = ValidationError("Test validation error")
        
        self.tracker.track_error(error, user_id="user123", request_id="req456")
        
        assert len(self.tracker.errors) == 1
        tracked_error = self.tracker.errors[0]
        
        assert tracked_error['error'] == error
        assert tracked_error['user_id'] == "user123"
        assert tracked_error['request_id'] == "req456"
        assert isinstance(tracked_error['timestamp'], datetime)
        assert tracked_error['resolved'] is False
        assert tracked_error['resolution_time'] is None
    
    def test_track_error_with_context(self):
        """Test tracking an error with additional context."""
        error = ProcessingError("Processing failed")
        context = {"operation": "file_upload", "file_size": 1024}
        
        self.tracker.track_error(error, context=context)
        
        tracked_error = self.tracker.errors[0]
        assert tracked_error['context'] == context
    
    def test_resolve_error(self):
        """Test resolving an error."""
        error = ValidationError("Test error")
        self.tracker.track_error(error)
        
        error_id = error.error_id
        resolution_notes = "Fixed validation logic"
        
        result = self.tracker.resolve_error(error_id, resolution_notes)
        
        assert result is True
        assert len(self.tracker.errors) == 0
        assert len(self.tracker.resolved_errors) == 1
        
        resolved_error = self.tracker.resolved_errors[0]
        assert resolved_error['resolved'] is True
        assert resolved_error['resolution_notes'] == resolution_notes
        assert isinstance(resolved_error['resolution_time'], float)
        assert resolved_error['resolution_time'] > 0
    
    def test_resolve_nonexistent_error(self):
        """Test resolving a non-existent error."""
        result = self.tracker.resolve_error("nonexistent_id")
        assert result is False
    
    def test_get_recent_errors(self):
        """Test getting recent errors."""
        # Create errors with different timestamps
        for i in range(5):
            error = ValidationError(f"Error {i}")
            self.tracker.track_error(error)
        
        recent_errors = self.tracker.get_recent_errors(limit=3)
        
        assert len(recent_errors) == 3
        # Should be in reverse chronological order (most recent first)
        for i in range(len(recent_errors) - 1):
            assert recent_errors[i]['timestamp'] >= recent_errors[i + 1]['timestamp']
    
    def test_get_recent_errors_with_time_window(self):
        """Test getting recent errors within a time window."""
        # Create an old error
        old_error = ValidationError("Old error")
        with patch('src.exceptions.error_tracker.datetime') as mock_datetime:
            old_time = datetime.now() - timedelta(hours=2)
            mock_datetime.now.return_value = old_time
            self.tracker.track_error(old_error)
        
        # Create a recent error
        recent_error = ValidationError("Recent error")
        self.tracker.track_error(recent_error)
        
        # Get errors from last hour
        recent_errors = self.tracker.get_recent_errors(
            since=datetime.now() - timedelta(hours=1)
        )
        
        assert len(recent_errors) == 1
        assert "Recent error" in recent_errors[0]['error'].message
    
    def test_get_error_metrics(self):
        """Test getting error metrics."""
        # Track some errors
        errors = [
            ValidationError("Validation 1"),
            ValidationError("Validation 2"),
            AuthenticationError("Auth error"),
            ProcessingError("Processing error")
        ]
        
        for error in errors:
            self.tracker.track_error(error)
        
        # Resolve one error
        self.tracker.resolve_error(errors[0].error_id)
        
        # Set total requests for rate calculation
        self.tracker.total_requests = 100
        
        metrics = self.tracker.get_error_metrics()
        
        assert metrics.total_errors == 4
        assert metrics.errors_by_code['VALIDATION_ERROR'] == 2
        assert metrics.errors_by_code['AUTHENTICATION_ERROR'] == 1
        assert metrics.errors_by_code['PROCESSING_ERROR'] == 1
        assert metrics.error_rate == 0.04  # 4 errors / 100 requests
        assert metrics.most_common_error == 'VALIDATION_ERROR'
    
    def test_get_error_metrics_by_severity(self):
        """Test getting error metrics grouped by severity."""
        errors = [
            ValidationError("Low severity"),  # LOW
            AuthenticationError("Medium severity"),  # MEDIUM
            ProcessingError("Medium severity"),  # MEDIUM
        ]
        
        for error in errors:
            self.tracker.track_error(error)
        
        metrics = self.tracker.get_error_metrics()
        
        assert metrics.errors_by_severity['low'] == 1
        assert metrics.errors_by_severity['medium'] == 2
        assert metrics.errors_by_severity.get('high', 0) == 0
    
    def test_clear_old_errors(self):
        """Test clearing old errors."""
        # Create old errors
        with patch('src.exceptions.error_tracker.datetime') as mock_datetime:
            old_time = datetime.now() - timedelta(days=8)
            mock_datetime.now.return_value = old_time
            
            for i in range(3):
                error = ValidationError(f"Old error {i}")
                self.tracker.track_error(error)
        
        # Create recent errors
        for i in range(2):
            error = ValidationError(f"Recent error {i}")
            self.tracker.track_error(error)
        
        assert len(self.tracker.errors) == 5
        
        # Clear errors older than 7 days
        cleared_count = self.tracker.clear_old_errors(days=7)
        
        assert cleared_count == 3
        assert len(self.tracker.errors) == 2
    
    def test_max_errors_limit(self):
        """Test that error tracker respects max_errors limit."""
        tracker = ErrorTracker(max_errors=3)
        
        # Add more errors than the limit
        for i in range(5):
            error = ValidationError(f"Error {i}")
            tracker.track_error(error)
        
        # Should only keep the most recent 3 errors
        assert len(tracker.errors) == 3
        
        # Check that the most recent errors are kept
        error_messages = [e['error'].message for e in tracker.errors]
        assert "Error 2" in error_messages
        assert "Error 3" in error_messages
        assert "Error 4" in error_messages
        assert "Error 0" not in error_messages
        assert "Error 1" not in error_messages
    
    def test_increment_requests(self):
        """Test incrementing request count."""
        assert self.tracker.total_requests == 0
        
        self.tracker.increment_requests()
        assert self.tracker.total_requests == 1
        
        self.tracker.increment_requests(5)
        assert self.tracker.total_requests == 6


class TestErrorAnalytics:
    """Test ErrorAnalytics class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = ErrorTracker()
        self.analytics = ErrorAnalytics(self.tracker)
    
    def test_error_analytics_initialization(self):
        """Test error analytics initialization."""
        assert self.analytics.tracker == self.tracker
    
    def test_generate_report_empty(self):
        """Test generating report with no errors."""
        report = self.analytics.generate_report()
        
        assert "summary" in report
        assert "metrics" in report
        assert "trends" in report
        assert "recommendations" in report
        
        assert report["summary"]["total_errors"] == 0
        assert "No errors recorded" in report["summary"]["status"]
    
    def test_generate_report_with_errors(self):
        """Test generating report with errors."""
        # Add some test errors
        errors = [
            ValidationError("Validation 1"),
            ValidationError("Validation 2"),
            AuthenticationError("Auth error"),
            ProcessingError("Processing error")
        ]
        
        for error in errors:
            self.tracker.track_error(error)
        
        self.tracker.total_requests = 100
        
        report = self.analytics.generate_report()
        
        assert report["summary"]["total_errors"] == 4
        assert report["summary"]["error_rate"] == 0.04
        assert report["summary"]["most_common_error"] == "VALIDATION_ERROR"
        
        # Check that recommendations are provided
        assert len(report["recommendations"]) > 0
    
    def test_analyze_trends_increasing(self):
        """Test trend analysis for increasing errors."""
        # Simulate increasing error trend
        with patch('src.exceptions.error_tracker.datetime') as mock_datetime:
            # Add errors over time with increasing frequency
            base_time = datetime.now() - timedelta(hours=24)
            
            # Hour 1: 1 error
            mock_datetime.now.return_value = base_time + timedelta(hours=1)
            self.tracker.track_error(ValidationError("Error 1"))
            
            # Hour 12: 2 errors
            mock_datetime.now.return_value = base_time + timedelta(hours=12)
            self.tracker.track_error(ValidationError("Error 2"))
            self.tracker.track_error(ValidationError("Error 3"))
            
            # Hour 23: 3 errors
            mock_datetime.now.return_value = base_time + timedelta(hours=23)
            self.tracker.track_error(ValidationError("Error 4"))
            self.tracker.track_error(ValidationError("Error 5"))
            self.tracker.track_error(ValidationError("Error 6"))
        
        trends = self.analytics.analyze_trends()
        
        assert "hourly_distribution" in trends
        assert "trend_direction" in trends
        assert trends["trend_direction"] in ["increasing", "stable", "decreasing"]
    
    def test_get_recommendations_validation_errors(self):
        """Test recommendations for validation errors."""
        # Add many validation errors
        for i in range(10):
            self.tracker.track_error(ValidationError(f"Validation error {i}"))
        
        recommendations = self.analytics.get_recommendations()
        
        # Should recommend input validation improvements
        validation_rec = next(
            (r for r in recommendations if "validation" in r["description"].lower()),
            None
        )
        assert validation_rec is not None
        assert validation_rec["priority"] == "high"
    
    def test_get_recommendations_authentication_errors(self):
        """Test recommendations for authentication errors."""
        # Add many authentication errors
        for i in range(8):
            self.tracker.track_error(AuthenticationError(f"Auth error {i}"))
        
        recommendations = self.analytics.get_recommendations()
        
        # Should recommend authentication improvements
        auth_rec = next(
            (r for r in recommendations if "authentication" in r["description"].lower()),
            None
        )
        assert auth_rec is not None
    
    def test_get_recommendations_high_error_rate(self):
        """Test recommendations for high error rate."""
        # Add many errors with low request count
        for i in range(20):
            self.tracker.track_error(ValidationError(f"Error {i}"))
        
        self.tracker.total_requests = 50  # High error rate: 40%
        
        recommendations = self.analytics.get_recommendations()
        
        # Should recommend error rate investigation
        rate_rec = next(
            (r for r in recommendations if "error rate" in r["description"].lower()),
            None
        )
        assert rate_rec is not None
        assert rate_rec["priority"] == "critical"
    
    def test_get_recommendations_no_issues(self):
        """Test recommendations when there are no significant issues."""
        # Add a few errors with high request count (low error rate)
        for i in range(2):
            self.tracker.track_error(ValidationError(f"Error {i}"))
        
        self.tracker.total_requests = 1000  # Low error rate: 0.2%
        
        recommendations = self.analytics.get_recommendations()
        
        # Should have general monitoring recommendation
        assert len(recommendations) >= 1
        general_rec = recommendations[-1]  # Usually the last one
        assert "monitoring" in general_rec["description"].lower()
    
    def test_export_metrics(self):
        """Test exporting metrics to dictionary."""
        # Add some test data
        errors = [
            ValidationError("Validation error"),
            AuthenticationError("Auth error")
        ]
        
        for error in errors:
            self.tracker.track_error(error)
        
        self.tracker.total_requests = 100
        
        exported = self.analytics.export_metrics()
        
        assert "timestamp" in exported
        assert "metrics" in exported
        assert "trends" in exported
        assert "recommendations" in exported
        
        assert exported["metrics"]["total_errors"] == 2
        assert exported["metrics"]["error_rate"] == 0.02
    
    def test_time_based_analysis(self):
        """Test time-based error analysis."""
        # Create errors at different times
        with patch('src.exceptions.error_tracker.datetime') as mock_datetime:
            base_time = datetime.now()
            
            # Morning errors
            mock_datetime.now.return_value = base_time.replace(hour=9)
            self.tracker.track_error(ValidationError("Morning error 1"))
            self.tracker.track_error(ValidationError("Morning error 2"))
            
            # Afternoon errors
            mock_datetime.now.return_value = base_time.replace(hour=14)
            self.tracker.track_error(AuthenticationError("Afternoon error"))
            
            # Evening errors
            mock_datetime.now.return_value = base_time.replace(hour=20)
            self.tracker.track_error(ProcessingError("Evening error"))
        
        trends = self.analytics.analyze_trends()
        
        assert "hourly_distribution" in trends
        hourly_dist = trends["hourly_distribution"]
        
        # Check that errors are distributed across different hours
        assert hourly_dist.get(9, 0) == 2  # Morning
        assert hourly_dist.get(14, 0) == 1  # Afternoon
        assert hourly_dist.get(20, 0) == 1  # Evening


class TestErrorTrackerIntegration:
    """Test integration between ErrorTracker and ErrorAnalytics."""
    
    def test_full_error_lifecycle(self):
        """Test complete error tracking and analysis lifecycle."""
        tracker = ErrorTracker(max_errors=50)
        analytics = ErrorAnalytics(tracker)
        
        # Simulate a day of errors
        error_types = [ValidationError, AuthenticationError, ProcessingError]
        
        for hour in range(24):
            # Simulate varying error rates throughout the day
            error_count = max(1, hour // 4)  # More errors later in the day
            
            with patch('src.exceptions.error_tracker.datetime') as mock_datetime:
                mock_datetime.now.return_value = datetime.now().replace(hour=hour)
                
                for i in range(error_count):
                    error_type = error_types[i % len(error_types)]
                    error = error_type(f"Error at hour {hour}, #{i}")
                    tracker.track_error(
                        error,
                        user_id=f"user_{i % 10}",
                        context={"hour": hour, "error_num": i}
                    )
        
        # Set request count
        tracker.total_requests = 1000
        
        # Resolve some errors
        recent_errors = tracker.get_recent_errors(limit=5)
        for error_info in recent_errors[:2]:
            tracker.resolve_error(
                error_info['error'].error_id,
                "Resolved during testing"
            )
        
        # Generate comprehensive report
        report = analytics.generate_report()
        
        # Verify report structure and content
        assert report["summary"]["total_errors"] > 0
        assert report["summary"]["resolved_errors"] == 2
        assert report["summary"]["error_rate"] > 0
        
        assert len(report["metrics"]["errors_by_code"]) == 3
        assert len(report["recommendations"]) > 0
        
        # Verify trends analysis
        assert "hourly_distribution" in report["trends"]
        assert "peak_hours" in report["trends"]
        
        # Export metrics
        exported = analytics.export_metrics()
        assert "timestamp" in exported
        assert exported["metrics"]["total_errors"] == report["summary"]["total_errors"]