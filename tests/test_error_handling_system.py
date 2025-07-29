"""
Comprehensive tests for error handling system components

Tests the ProcessingErrorHandler, FallbackManager, RetryManager,
and related error handling infrastructure.
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.services.processing_error_handler import (
    ProcessingErrorHandler, ErrorContext, ErrorCategory, FallbackStrategy, RetryConfig
)
from src.services.fallback_manager import FallbackManager
from src.services.retry_manager import RetryManager
from src.exceptions.application_errors import ProcessingError, ServiceUnavailableError

class TestProcessingErrorHandler:
    """Test cases for ProcessingErrorHandler"""
    
    @pytest.fixture
    def error_handler(self):
        """Create ProcessingErrorHandler instance for testing"""
        return ProcessingErrorHandler()
    
    @pytest.fixture
    def error_context(self):
        """Create ErrorContext for testing"""
        return ErrorContext(
            operation="test_operation",
            service="test_service",
            timestamp=datetime.utcnow(),
            user_id="test_user",
            request_id="test_request",
            additional_data={"test_key": "test_value"}
        )
    
    def test_initialization(self, error_handler):
        """Test error handler initialization"""
        assert error_handler is not None
        assert len(error_handler.error_categories) > 0
        assert len(error_handler.fallback_strategies) > 0
        assert len(error_handler.retry_configs) > 0
        assert error_handler.error_history == []
    
    def test_handle_transient_error(self, error_handler, error_context):
        """Test handling of transient errors"""
        error = ConnectionError("Network timeout")
        
        response = error_handler.handle_error(error, error_context)
        
        assert response['category'] == ErrorCategory.TRANSIENT.value
        assert response['should_retry'] is True
        assert response['fallback_strategy'] is not None
        assert response['error_id'] is not None
        assert response['context']['operation'] == 'test_operation'
    
    def test_handle_permanent_error(self, error_handler, error_context):
        """Test handling of permanent errors"""
        error = ValueError("Invalid input format")
        
        response = error_handler.handle_error(error, error_context)
        
        assert response['category'] == ErrorCategory.PERMANENT.value
        assert response['should_retry'] is False
        assert 'recommendations' in response
    
    def test_handle_dependency_error(self, error_handler, error_context):
        """Test handling of dependency errors"""
        error = ImportError("Module not found")
        
        response = error_handler.handle_error(error, error_context)
        
        assert response['category'] == ErrorCategory.DEPENDENCY.value
        assert response['should_retry'] is False
        assert any('dependency' in rec.lower() for rec in response['recommendations'])
    
    def test_error_categorization(self, error_handler, error_context):
        """Test error categorization logic"""
        # Test different error types
        test_cases = [
            (ConnectionError("Connection failed"), ErrorCategory.TRANSIENT),
            (ImportError("Module not found"), ErrorCategory.DEPENDENCY),
            (ValueError("Invalid value"), ErrorCategory.PERMANENT),
            (MemoryError("Out of memory"), ErrorCategory.RESOURCE)
        ]
        
        for error, expected_category in test_cases:
            category = error_handler._categorize_error(error, error_context)
            assert category == expected_category
    
    def test_fallback_strategy_selection(self, error_handler):
        """Test fallback strategy selection"""
        # Test operation-specific strategies
        strategy = error_handler._get_fallback_strategy('ocr_processing', ErrorCategory.TRANSIENT)
        assert strategy in [FallbackStrategy.ALTERNATIVE_METHOD, FallbackStrategy.DEGRADED_SERVICE, FallbackStrategy.DEFAULT_VALUE]
        
        strategy = error_handler._get_fallback_strategy('unknown_operation', ErrorCategory.TRANSIENT)
        assert strategy == FallbackStrategy.RETRY
    
    def test_retry_decision(self, error_handler, error_context):
        """Test retry decision logic"""
        # Transient errors should be retryable
        transient_error = ConnectionError("Network timeout")
        assert error_handler._should_retry(transient_error, error_context, ErrorCategory.TRANSIENT) is True
        
        # Permanent errors should not be retryable
        permanent_error = ValueError("Invalid format")
        assert error_handler._should_retry(permanent_error, error_context, ErrorCategory.PERMANENT) is False
        
        # Validation errors should not be retryable
        validation_error = ValueError("Validation failed")
        assert error_handler._should_retry(validation_error, error_context, ErrorCategory.VALIDATION) is False
    
    def test_error_history_tracking(self, error_handler, error_context):
        """Test error history tracking"""
        initial_count = len(error_handler.error_history)
        
        error = ConnectionError("Test error")
        error_handler.handle_error(error, error_context)
        
        assert len(error_handler.error_history) == initial_count + 1
        
        # Check history entry structure
        history_entry = error_handler.error_history[-1]
        assert 'timestamp' in history_entry
        assert 'error_id' in history_entry
        assert 'operation' in history_entry
        assert 'service' in history_entry
    
    def test_error_statistics(self, error_handler, error_context):
        """Test error statistics generation"""
        # Generate some test errors
        errors = [
            ConnectionError("Network error 1"),
            ConnectionError("Network error 2"),
            ValueError("Validation error"),
            ImportError("Import error")
        ]
        
        for error in errors:
            error_handler.handle_error(error, error_context)
        
        stats = error_handler.get_error_statistics()
        
        assert stats['total_errors'] >= 4
        assert 'categories' in stats
        assert 'services' in stats
        assert 'operations' in stats
        assert 'recent_errors' in stats
    
    def test_custom_error_registration(self, error_handler):
        """Test custom error category registration"""
        error_handler.register_error_category('CustomError', ErrorCategory.CONFIGURATION)
        
        assert 'CustomError' in error_handler.error_categories
        assert error_handler.error_categories['CustomError'] == ErrorCategory.CONFIGURATION
    
    def test_custom_fallback_registration(self, error_handler):
        """Test custom fallback strategy registration"""
        strategies = [FallbackStrategy.CACHED_RESULT, FallbackStrategy.DEFAULT_VALUE]
        error_handler.register_fallback_strategy('custom_operation', strategies)
        
        assert 'custom_operation' in error_handler.fallback_strategies
        assert error_handler.fallback_strategies['custom_operation'] == strategies
    
    def test_custom_retry_config(self, error_handler):
        """Test custom retry configuration"""
        config = RetryConfig(max_attempts=5, base_delay=2.0, max_delay=120.0)
        error_handler.register_retry_config('custom_operation', config)
        
        assert 'custom_operation' in error_handler.retry_configs
        assert error_handler.retry_configs['custom_operation'] == config
    
    def test_error_history_size_limit(self, error_handler, error_context):
        """Test error history size limit"""
        original_limit = error_handler.max_history_size
        error_handler.max_history_size = 3
        
        # Generate more errors than the limit
        for i in range(5):
            error = ValueError(f"Test error {i}")
            error_handler.handle_error(error, error_context)
        
        assert len(error_handler.error_history) == 3
        
        # Restore original limit
        error_handler.max_history_size = original_limit

class TestFallbackManager:
    """Test cases for FallbackManager"""
    
    @pytest.fixture
    def error_handler(self):
        return ProcessingErrorHandler()
    
    @pytest.fixture
    def fallback_manager(self, error_handler):
        return FallbackManager(error_handler)
    
    @pytest.fixture
    def error_context(self):
        return ErrorContext(
            operation="test_operation",
            service="test_service",
            timestamp=datetime.utcnow(),
            request_id="test_request"
        )
    
    def test_successful_primary_execution(self, fallback_manager, error_context):
        """Test successful execution without fallback"""
        def primary_func(x, y):
            return x + y
        
        def fallback_func(x, y):
            return x * y
        
        result = fallback_manager.execute_with_fallback(
            primary_func, fallback_func, "test_operation", error_context, 2, 3
        )
        
        assert result == 5  # Primary function result
    
    def test_fallback_execution(self, fallback_manager, error_context):
        """Test fallback execution when primary fails"""
        def primary_func(x, y):
            raise ValueError("Primary function failed")
        
        def fallback_func(x, y):
            return x * y
        
        result = fallback_manager.execute_with_fallback(
            primary_func, fallback_func, "test_operation", error_context, 2, 3
        )
        
        assert result == 6  # Fallback function result
    
    def test_both_functions_fail(self, fallback_manager, error_context):
        """Test behavior when both primary and fallback fail"""
        def primary_func(x, y):
            raise ValueError("Primary function failed")
        
        def fallback_func(x, y):
            raise RuntimeError("Fallback function failed")
        
        with pytest.raises(RuntimeError, match="Fallback function failed"):
            fallback_manager.execute_with_fallback(
                primary_func, fallback_func, "test_operation", error_context, 2, 3
            )
    
    def test_fallback_statistics(self, fallback_manager, error_context):
        """Test fallback usage statistics"""
        def primary_func():
            raise ValueError("Always fails")
        
        def fallback_func():
            return "fallback_result"
        
        # Execute fallback multiple times
        for _ in range(3):
            fallback_manager.execute_with_fallback(
                primary_func, fallback_func, "test_operation", error_context
            )
        
        stats = fallback_manager.get_fallback_stats()
        assert stats.get("test_operation", 0) == 3
    
    def test_fallback_registration(self, fallback_manager):
        """Test fallback function registration"""
        def custom_fallback():
            return "custom_result"
        
        fallback_manager.register_fallback("custom_operation", custom_fallback, priority=10)
        
        # Verify registration through error handler
        assert "custom_operation" in fallback_manager.error_handler.fallback_strategies

class TestRetryManager:
    """Test cases for RetryManager"""
    
    @pytest.fixture
    def retry_config(self):
        return RetryConfig(max_attempts=3, base_delay=0.1, max_delay=1.0)
    
    @pytest.fixture
    def retry_manager(self, retry_config):
        return RetryManager(retry_config)
    
    @pytest.fixture
    def error_handler(self):
        return ProcessingErrorHandler()
    
    @pytest.fixture
    def error_context(self):
        return ErrorContext(
            operation="test_operation",
            service="test_service",
            timestamp=datetime.utcnow(),
            request_id="test_request"
        )
    
    def test_successful_execution_no_retry(self, retry_manager, error_handler, error_context):
        """Test successful execution without retry"""
        def test_func():
            return "success"
        
        result = retry_manager.execute_with_retry(
            test_func, "test_operation", error_handler, error_context
        )
        
        assert result == "success"
    
    def test_retry_on_transient_error(self, retry_manager, error_handler, error_context):
        """Test retry behavior on transient errors"""
        call_count = 0
        
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient error")
            return "success_after_retry"
        
        result = retry_manager.execute_with_retry(
            test_func, "test_operation", error_handler, error_context
        )
        
        assert result == "success_after_retry"
        assert call_count == 3
    
    def test_max_retries_exceeded(self, retry_manager, error_handler, error_context):
        """Test behavior when max retries are exceeded"""
        def test_func():
            raise ConnectionError("Always fails")
        
        with pytest.raises(ConnectionError, match="Always fails"):
            retry_manager.execute_with_retry(
                test_func, "test_operation", error_handler, error_context
            )
    
    def test_non_retryable_error(self, retry_manager, error_handler, error_context):
        """Test that non-retryable errors are not retried"""
        call_count = 0
        
        def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")
        
        with pytest.raises(ValueError, match="Non-retryable error"):
            retry_manager.execute_with_retry(
                test_func, "test_operation", error_handler, error_context
            )
        
        assert call_count == 1  # Should not retry
    
    def test_exponential_backoff(self, retry_manager):
        """Test exponential backoff delay calculation"""
        delays = []
        for attempt in range(3):
            delay = retry_manager._calculate_delay(attempt)
            delays.append(delay)
        
        # Each delay should be larger than the previous (exponential backoff)
        assert delays[1] > delays[0]
        assert delays[2] > delays[1]
        
        # All delays should be within reasonable bounds
        for delay in delays:
            assert 0.1 <= delay <= 1.0
    
    def test_retry_statistics(self, retry_manager, error_handler, error_context):
        """Test retry statistics collection"""
        def test_func():
            return "success"
        
        # Execute successful operation
        retry_manager.execute_with_retry(
            test_func, "test_operation", error_handler, error_context
        )
        
        stats = retry_manager.get_retry_stats()
        assert "test_operation" in stats
        assert stats["test_operation"]["success_rate"] == 100.0
        assert stats["test_operation"]["total_operations"] == 1
    
    def test_jitter_in_delay(self, retry_manager):
        """Test that jitter is applied to delays"""
        delays = []
        for _ in range(10):
            delay = retry_manager._calculate_delay(1)
            delays.append(delay)
        
        # With jitter, delays should vary
        assert len(set(delays)) > 1  # Should have some variation

class TestErrorHandlingIntegration:
    """Integration tests for error handling components"""
    
    @pytest.fixture
    def error_handler(self):
        return ProcessingErrorHandler()
    
    @pytest.fixture
    def fallback_manager(self, error_handler):
        return FallbackManager(error_handler)
    
    @pytest.fixture
    def retry_manager(self):
        return RetryManager()
    
    @pytest.fixture
    def error_context(self):
        return ErrorContext(
            operation="integration_test",
            service="test_service",
            timestamp=datetime.utcnow(),
            request_id="integration_test_request"
        )
    
    def test_full_error_handling_pipeline(self, error_handler, fallback_manager, retry_manager, error_context):
        """Test complete error handling pipeline"""
        attempt_count = 0
        
        def unreliable_function():
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count == 1:
                raise ConnectionError("First attempt fails")
            elif attempt_count == 2:
                raise TimeoutError("Second attempt times out")
            else:
                return "success_on_third_attempt"
        
        def fallback_function():
            return "fallback_result"
        
        # Test retry with eventual success
        result = retry_manager.execute_with_retry(
            unreliable_function, "integration_test", error_handler, error_context
        )
        
        assert result == "success_on_third_attempt"
        assert attempt_count == 3
        
        # Test fallback when primary always fails
        def always_fails():
            raise ValueError("Always fails")
        
        fallback_result = fallback_manager.execute_with_fallback(
            always_fails, fallback_function, "integration_test", error_context
        )
        
        assert fallback_result == "fallback_result"
    
    def test_error_tracking_across_components(self, error_handler, fallback_manager, error_context):
        """Test that errors are properly tracked across components"""
        initial_error_count = len(error_handler.error_history)
        
        def failing_function():
            raise ProcessingError("Test processing error", operation="integration_test")
        
        def fallback_function():
            return "fallback_used"
        
        # Execute with fallback
        result = fallback_manager.execute_with_fallback(
            failing_function, fallback_function, "integration_test", error_context
        )
        
        assert result == "fallback_used"
        assert len(error_handler.error_history) > initial_error_count
        
        # Check that error was properly categorized and logged
        latest_error = error_handler.error_history[-1]
        assert latest_error['operation'] == 'integration_test'
        assert latest_error['service'] == 'test_service'

if __name__ == '__main__':
    pytest.main([__file__, '-v'])