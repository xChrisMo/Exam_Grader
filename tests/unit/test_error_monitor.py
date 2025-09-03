"""
Unit tests for the error monitoring service
"""

import pytest
import tempfile
import json
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

from src.services.error_monitor import (
    ErrorMonitor, ErrorCategory, ErrorSeverity, RecoveryAction,
    ErrorRecord, SystemHealthMetrics
)


class TestErrorMonitor:
    """Test error monitoring functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.monitor = ErrorMonitor(log_dir=temp_dir)
    
    def test_categorize_error(self):
        """Test automatic error categorization"""
        # Test file upload errors
        assert self.monitor._categorize_error("file size exceeded") == ErrorCategory.FILE_UPLOAD
        assert self.monitor._categorize_error("file not found") == ErrorCategory.FILE_UPLOAD
        
        # Test LLM service errors
        assert self.monitor._categorize_error("openai api error") == ErrorCategory.LLM_SERVICE
        assert self.monitor._categorize_error("rate limit exceeded") == ErrorCategory.LLM_SERVICE
        
        # Test OCR service errors
        assert self.monitor._categorize_error("ocr processing failed") == ErrorCategory.OCR_SERVICE
        assert self.monitor._categorize_error("image text extraction error") == ErrorCategory.OCR_SERVICE
        
        # Test database errors
        assert self.monitor._categorize_error("database connection failed") == ErrorCategory.DATABASE
        assert self.monitor._categorize_error("sql constraint violation") == ErrorCategory.DATABASE
        
        # Test default category
        assert self.monitor._categorize_error("unknown error type") == ErrorCategory.SYSTEM
    
    def test_assess_severity(self):
        """Test automatic severity assessment"""
        # Test critical errors
        critical_error = SystemExit("System shutdown")
        assert self.monitor._assess_severity(critical_error, ErrorCategory.SYSTEM) == ErrorSeverity.CRITICAL
        
        memory_error = MemoryError("Out of memory")
        assert self.monitor._assess_severity(memory_error, ErrorCategory.SYSTEM) == ErrorSeverity.CRITICAL
        
        # Test high severity errors
        connection_error = ConnectionError("Connection failed")
        assert self.monitor._assess_severity(connection_error, ErrorCategory.NETWORK) == ErrorSeverity.HIGH
        
        # Test medium severity errors
        value_error = ValueError("Invalid value")
        assert self.monitor._assess_severity(value_error, ErrorCategory.VALIDATION) == ErrorSeverity.MEDIUM
        
        # Test low severity errors (default)
        runtime_error = RuntimeError("Runtime issue")
        assert self.monitor._assess_severity(runtime_error, ErrorCategory.SYSTEM) == ErrorSeverity.LOW
    
    def test_determine_recovery_action(self):
        """Test recovery action determination"""
        # Test critical errors require manual intervention
        error_record = Mock()
        error_record.category = ErrorCategory.SYSTEM
        error_record.severity = ErrorSeverity.CRITICAL
        error_record.details = {"error_type": "SystemExit"}
        
        action = self.monitor._determine_recovery_action(error_record)
        assert action == RecoveryAction.MANUAL_INTERVENTION
        
        # Test network errors can be retried
        error_record.category = ErrorCategory.NETWORK
        error_record.severity = ErrorSeverity.HIGH
        error_record.details = {"error_type": "ConnectionError"}
        
        action = self.monitor._determine_recovery_action(error_record)
        assert action == RecoveryAction.RETRY
        
        # Test file processing errors have fallbacks
        error_record.category = ErrorCategory.FILE_PROCESSING
        error_record.severity = ErrorSeverity.MEDIUM
        error_record.details = {"error_type": "ProcessingError"}
        
        action = self.monitor._determine_recovery_action(error_record)
        assert action == RecoveryAction.FALLBACK
        
        # Test validation errors can be skipped
        error_record.category = ErrorCategory.VALIDATION
        error_record.severity = ErrorSeverity.LOW
        error_record.details = {"error_type": "ValidationError"}
        
        action = self.monitor._determine_recovery_action(error_record)
        assert action == RecoveryAction.SKIP
    
    @patch('src.services.error_monitor.logger')
    def test_log_error(self, mock_logger):
        """Test error logging functionality"""
        test_error = ValueError("Test error message")
        
        error_id = self.monitor.log_error(
            error=test_error,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            user_id=123,
            session_id="test_session",
            component="test_component",
            additional_context={"test_key": "test_value"}
        )
        
        # Check that error ID was generated
        assert error_id is not None
        assert error_id.startswith("err_")
        
        # Check that error was added to history
        assert len(self.monitor.error_history) == 1
        
        error_record = self.monitor.error_history[0]
        assert error_record.id == error_id
        assert error_record.category == ErrorCategory.VALIDATION
        assert error_record.severity == ErrorSeverity.MEDIUM
        assert error_record.message == "Test error message"
        assert error_record.user_id == 123
        assert error_record.session_id == "test_session"
        assert error_record.component == "test_component"
        
        # Check that logger was called
        mock_logger.error.assert_called()
    
    def test_get_error_statistics_empty(self):
        """Test error statistics with no errors"""
        stats = self.monitor.get_error_statistics(hours=24)
        
        assert stats["total_errors"] == 0
        assert stats["error_rate"] == 0.0
        assert stats["by_category"] == {}
        assert stats["by_severity"] == {}
        assert stats["recovery_success_rate"] == 0.0
    
    def test_get_error_statistics_with_data(self):
        """Test error statistics with sample data"""
        # Add some test errors
        test_errors = [
            ValueError("Error 1"),
            ConnectionError("Error 2"),
            ValueError("Error 3")
        ]
        
        for i, error in enumerate(test_errors):
            self.monitor.log_error(
                error=error,
                category=ErrorCategory.VALIDATION if i % 2 == 0 else ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                user_id=i,
                component="test"
            )
        
        stats = self.monitor.get_error_statistics(hours=24)
        
        assert stats["total_errors"] == 3
        assert stats["error_rate"] == 3 / 24  # 3 errors in 24 hours
        assert stats["by_category"]["validation"] == 2
        assert stats["by_category"]["network"] == 1
        assert stats["by_severity"]["medium"] == 3
    
    def test_get_system_health(self):
        """Test system health metrics"""
        # Add some test errors
        self.monitor.log_error(
            error=ValueError("Test error"),
            severity=ErrorSeverity.CRITICAL,
            component="test"
        )
        
        health = self.monitor.get_system_health()
        
        assert isinstance(health, SystemHealthMetrics)
        assert health.error_rate >= 0
        assert health.critical_errors_count >= 1
        assert isinstance(health.timestamp, datetime)
    
    def test_resolve_error(self):
        """Test error resolution"""
        # Log an error first
        test_error = ValueError("Test error")
        error_id = self.monitor.log_error(error=test_error, component="test")
        
        # Resolve the error
        success = self.monitor.resolve_error(error_id, "Fixed by updating configuration")
        
        assert success is True
        
        # Check that error is marked as resolved
        error_record = next(e for e in self.monitor.error_history if e.id == error_id)
        assert error_record.resolved is True
        assert error_record.resolution_notes == "Fixed by updating configuration"
    
    def test_get_error_details(self):
        """Test error details retrieval"""
        # Log an error first
        test_error = ValueError("Test error")
        error_id = self.monitor.log_error(
            error=test_error,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            user_id=123,
            component="test"
        )
        
        # Get error details
        details = self.monitor.get_error_details(error_id)
        
        assert details is not None
        assert details["id"] == error_id
        assert details["category"] == "validation"
        assert details["severity"] == "medium"
        assert details["message"] == "Test error"
        assert details["user_id"] == 123
        assert details["component"] == "test"
    
    def test_get_error_details_not_found(self):
        """Test error details retrieval for non-existent error"""
        details = self.monitor.get_error_details("non_existent_error")
        assert details is None
    
    @patch('src.services.error_monitor.logger')
    def test_trigger_critical_alert(self, mock_logger):
        """Test critical error alerting"""
        error_record = Mock()
        error_record.id = "test_error_123"
        error_record.category = ErrorCategory.SYSTEM
        error_record.component = "test_component"
        error_record.message = "Critical system error"
        error_record.user_id = 123
        error_record.session_id = "test_session"
        error_record.timestamp = datetime.now()
        
        self.monitor._trigger_critical_alert(error_record)
        
        # Check that critical log was made
        mock_logger.critical.assert_called()
        
        # Check that the alert message contains key information
        call_args = mock_logger.critical.call_args[0][0]
        assert "CRITICAL ERROR DETECTED" in call_args
        assert error_record.id in call_args
        assert error_record.message in call_args
    
    def test_monitoring_lifecycle(self):
        """Test monitoring start/stop lifecycle"""
        # Test starting monitoring
        self.monitor.start_monitoring(interval=1)
        assert self.monitor.monitoring_active is True
        assert self.monitor.monitoring_thread is not None
        
        # Test stopping monitoring
        self.monitor.stop_monitoring()
        assert self.monitor.monitoring_active is False
    
    def test_error_patterns_matching(self):
        """Test error pattern matching for categorization"""
        # Test various error messages
        test_cases = [
            ("File size exceeds limit", ErrorCategory.FILE_UPLOAD),
            ("OpenAI API rate limit", ErrorCategory.LLM_SERVICE),
            ("OCR text extraction failed", ErrorCategory.OCR_SERVICE),
            ("Database connection timeout", ErrorCategory.DATABASE),
            ("Training session failed", ErrorCategory.TRAINING_PROCESS),
            ("Unknown error occurred", ErrorCategory.SYSTEM)  # Default
        ]
        
        for error_message, expected_category in test_cases:
            actual_category = self.monitor._categorize_error(error_message)
            assert actual_category == expected_category, f"Failed for: {error_message}"
    
    def test_error_count_tracking(self):
        """Test error count tracking by category"""
        # Log errors of different categories
        categories = [
            ErrorCategory.FILE_UPLOAD,
            ErrorCategory.LLM_SERVICE,
            ErrorCategory.FILE_UPLOAD,  # Duplicate to test counting
            ErrorCategory.OCR_SERVICE
        ]
        
        for category in categories:
            self.monitor.log_error(
                error=ValueError("Test error"),
                category=category,
                component="test"
            )
        
        # Check error counts
        assert self.monitor.error_counts[ErrorCategory.FILE_UPLOAD] == 2
        assert self.monitor.error_counts[ErrorCategory.LLM_SERVICE] == 1
        assert self.monitor.error_counts[ErrorCategory.OCR_SERVICE] == 1
    
    def test_error_history_limit(self):
        """Test error history size limit"""
        # The error history should be limited to 1000 items
        # Add more than 1000 errors to test the limit
        for i in range(1005):
            self.monitor.log_error(
                error=ValueError(f"Test error {i}"),
                component="test"
            )
        
        # Should be limited to 1000
        assert len(self.monitor.error_history) == 1000
        
        # Should contain the most recent errors
        latest_error = self.monitor.error_history[-1]
        assert "Test error 1004" in latest_error.message


if __name__ == '__main__':
    pytest.main([__file__, '-v'])