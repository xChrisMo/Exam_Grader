"""
Enhanced Processing Error System - Unified error handling infrastructure.

This module integrates all error handling components into a cohesive system
that provides comprehensive error handling, fallback mechanisms, retry logic,
and detailed error reporting for processing operations.
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timezone
from dataclasses import dataclass

from src.services.processing_error_handler import (
    ProcessingErrorHandler, ErrorContext, ErrorCategory, FallbackStrategy,
    processing_error_handler
)
from src.services.fallback_manager import (
    FallbackManager, FallbackResult, FallbackPriority,
    fallback_manager
)
from src.services.retry_manager import (
    RetryManager, RetryResult, RetryStrategy,
    retry_manager
)
from src.services.error_reporter import (
    ErrorReporter, ErrorReport,
    error_reporter
)
from src.exceptions.application_errors import ApplicationError, ProcessingError
from utils.logger import logger

@dataclass
class ProcessingResult:
    """Unified result structure for processing operations."""
    success: bool
    data: Any = None
    error_id: Optional[str] = None
    error_message: Optional[str] = None
    method_used: Optional[str] = None
    execution_time: float = 0.0
    retry_attempts: int = 0
    fallback_used: bool = False
    metadata: Optional[Dict[str, Any]] = None

class EnhancedProcessingErrorSystem:
    """
    Unified error handling system that integrates all error handling components.
    """
    
    def __init__(self):
        self.error_handler = processing_error_handler
        self.fallback_manager = fallback_manager
        self.retry_manager = retry_manager
        self.error_reporter = error_reporter
        
        # System configuration
        self.enable_fallbacks = True
        self.enable_retries = True
        self.enable_reporting = True
        
        logger.info("Enhanced Processing Error System initialized")
    
    def execute_with_protection(
        self,
        operation: str,
        service: str,
        func: Callable,
        *args,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        file_path: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        enable_fallback: bool = True,
        enable_retry: bool = True,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        **kwargs
    ) -> ProcessingResult:
        """
        Execute function with comprehensive error protection.
        
        Args:
            operation: Name of the operation
            service: Name of the service
            func: Function to execute
            *args: Arguments for the function
            user_id: User ID for context
            request_id: Request ID for tracking
            file_path: File path if applicable
            additional_context: Additional context data
            enable_fallback: Whether to use fallback mechanisms
            enable_retry: Whether to use retry mechanisms
            retry_strategy: Retry strategy to use
            **kwargs: Keyword arguments for the function
            
        Returns:
            ProcessingResult with execution results
        """
        start_time = datetime.now(timezone.utc)
        
        # Create error context
        context = ErrorContext(
            operation=operation,
            service=service,
            timestamp=start_time,
            user_id=user_id,
            request_id=request_id,
            file_path=file_path,
            additional_data=additional_context
        )
        
        try:
            if enable_retry and self.enable_retries:
                retry_result = self.retry_manager.retry_with_backoff(
                    operation=operation,
                    func=func,
                    *args,
                    strategy=retry_strategy,
                    **kwargs
                )
                
                if retry_result.success:
                    execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                    
                    return ProcessingResult(
                        success=True,
                        data=retry_result.data,
                        method_used='primary_with_retry',
                        execution_time=execution_time,
                        retry_attempts=retry_result.total_attempts,
                        metadata={
                            'retry_strategy': retry_strategy.value,
                            'total_retry_time': retry_result.total_time
                        }
                    )
                else:
                    if enable_fallback and self.enable_fallbacks:
                        return self._execute_with_fallback(
                            operation, context, Exception(retry_result.final_error),
                            *args, **kwargs
                        )
                    else:
                        # Handle the final error
                        error = ProcessingError(
                            message=retry_result.final_error,
                            operation=operation,
                            context=additional_context
                        )
                        return self._handle_final_error(error, context)
            
            elif enable_fallback and self.enable_fallbacks:
                fallback_result = self.fallback_manager.execute_with_fallback(
                    operation=operation,
                    primary_func=func,
                    *args,
                    **kwargs
                )
                
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                if fallback_result.success:
                    return ProcessingResult(
                        success=True,
                        data=fallback_result.data,
                        method_used=fallback_result.method_used,
                        execution_time=execution_time,
                        fallback_used=fallback_result.method_used != 'primary',
                        metadata=fallback_result.metadata
                    )
                else:
                    error = ProcessingError(
                        message=fallback_result.error,
                        operation=operation,
                        context=additional_context
                    )
                    return self._handle_final_error(error, context)
            
            # Execute directly without protection
            else:
                result = func(*args, **kwargs)
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                return ProcessingResult(
                    success=True,
                    data=result,
                    method_used='direct',
                    execution_time=execution_time
                )
                
        except Exception as e:
            # Handle unexpected errors
            if isinstance(e, ApplicationError):
                error = e
            else:
                error = ProcessingError(
                    message=str(e),
                    operation=operation,
                    context=additional_context,
                    original_error=e
                )
            
            return self._handle_final_error(error, context)
    
    async def execute_with_protection_async(
        self,
        operation: str,
        service: str,
        func: Callable,
        *args,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        file_path: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        enable_fallback: bool = True,
        enable_retry: bool = True,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        **kwargs
    ) -> ProcessingResult:
        """
        Execute async function with comprehensive error protection.
        """
        start_time = datetime.now(timezone.utc)
        
        # Create error context
        context = ErrorContext(
            operation=operation,
            service=service,
            timestamp=start_time,
            user_id=user_id,
            request_id=request_id,
            file_path=file_path,
            additional_data=additional_context
        )
        
        try:
            if enable_retry and self.enable_retries:
                retry_result = await self.retry_manager.retry_with_backoff_async(
                    operation=operation,
                    func=func,
                    *args,
                    strategy=retry_strategy,
                    **kwargs
                )
                
                if retry_result.success:
                    execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                    
                    return ProcessingResult(
                        success=True,
                        data=retry_result.data,
                        method_used='primary_with_retry',
                        execution_time=execution_time,
                        retry_attempts=retry_result.total_attempts,
                        metadata={
                            'retry_strategy': retry_strategy.value,
                            'total_retry_time': retry_result.total_time
                        }
                    )
                else:
                    if enable_fallback and self.enable_fallbacks:
                        return await self._execute_with_fallback_async(
                            operation, context, Exception(retry_result.final_error),
                            *args, **kwargs
                        )
                    else:
                        # Handle the final error
                        error = ProcessingError(
                            message=retry_result.final_error,
                            operation=operation,
                            context=additional_context
                        )
                        return self._handle_final_error(error, context)
            
            elif enable_fallback and self.enable_fallbacks:
                fallback_result = await self.fallback_manager.execute_with_fallback_async(
                    operation=operation,
                    primary_func=func,
                    *args,
                    **kwargs
                )
                
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                if fallback_result.success:
                    return ProcessingResult(
                        success=True,
                        data=fallback_result.data,
                        method_used=fallback_result.method_used,
                        execution_time=execution_time,
                        fallback_used=fallback_result.method_used != 'primary',
                        metadata=fallback_result.metadata
                    )
                else:
                    error = ProcessingError(
                        message=fallback_result.error,
                        operation=operation,
                        context=additional_context
                    )
                    return self._handle_final_error(error, context)
            
            # Execute directly without protection
            else:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                return ProcessingResult(
                    success=True,
                    data=result,
                    method_used='direct',
                    execution_time=execution_time
                )
                
        except Exception as e:
            # Handle unexpected errors
            if isinstance(e, ApplicationError):
                error = e
            else:
                error = ProcessingError(
                    message=str(e),
                    operation=operation,
                    context=additional_context,
                    original_error=e
                )
            
            return self._handle_final_error(error, context)
    
    def _execute_with_fallback(
        self,
        operation: str,
        context: ErrorContext,
        primary_error: Exception,
        *args,
        **kwargs
    ) -> ProcessingResult:
        """Execute with fallback after primary method failed."""
        
        logger.info(f"Attempting fallback for operation '{operation}' after primary failure")
        
        # Create a dummy primary function that raises the error
        def failed_primary(*args, **kwargs):
            raise primary_error
        
        fallback_result = self.fallback_manager.execute_with_fallback(
            operation=operation,
            primary_func=failed_primary,
            *args,
            **kwargs
        )
        
        execution_time = (datetime.now(timezone.utc) - context.timestamp).total_seconds()
        
        if fallback_result.success:
            return ProcessingResult(
                success=True,
                data=fallback_result.data,
                method_used=fallback_result.method_used,
                execution_time=execution_time,
                fallback_used=True,
                metadata=fallback_result.metadata
            )
        else:
            error = ProcessingError(
                message=fallback_result.error,
                operation=operation,
                context=context.additional_data,
                original_error=primary_error
            )
            return self._handle_final_error(error, context)
    
    async def _execute_with_fallback_async(
        self,
        operation: str,
        context: ErrorContext,
        primary_error: Exception,
        *args,
        **kwargs
    ) -> ProcessingResult:
        """Execute with fallback after primary method failed (async version)."""
        
        logger.info(f"Attempting async fallback for operation '{operation}' after primary failure")
        
        # Create a dummy primary function that raises the error
        async def failed_primary(*args, **kwargs):
            raise primary_error
        
        fallback_result = await self.fallback_manager.execute_with_fallback_async(
            operation=operation,
            primary_func=failed_primary,
            *args,
            **kwargs
        )
        
        execution_time = (datetime.now(timezone.utc) - context.timestamp).total_seconds()
        
        if fallback_result.success:
            return ProcessingResult(
                success=True,
                data=fallback_result.data,
                method_used=fallback_result.method_used,
                execution_time=execution_time,
                fallback_used=True,
                metadata=fallback_result.metadata
            )
        else:
            error = ProcessingError(
                message=fallback_result.error,
                operation=operation,
                context=context.additional_data,
                original_error=primary_error
            )
            return self._handle_final_error(error, context)
    
    def _handle_final_error(
        self,
        error: ApplicationError,
        context: ErrorContext
    ) -> ProcessingResult:
        """Handle final error when all recovery attempts have failed."""
        
        # Process error through error handler
        error_response = self.error_handler.handle_error(error, context)
        
        if self.enable_reporting:
            category = ErrorCategory(error_response['category'])
            self.error_reporter.report_error(error, context, category)
        
        execution_time = (datetime.now(timezone.utc) - context.timestamp).total_seconds()
        
        return ProcessingResult(
            success=False,
            error_id=error.error_id,
            error_message=error.user_message,
            execution_time=execution_time,
            metadata={
                'error_category': error_response['category'],
                'error_severity': error_response['severity'],
                'should_retry': error_response['should_retry'],
                'fallback_strategy': error_response['fallback_strategy'],
                'recommendations': error_response['recommendations']
            }
        )
    
    def register_fallback_method(
        self,
        operation: str,
        name: str,
        function: Callable,
        priority: FallbackPriority,
        timeout: Optional[float] = None
    ):
        """Register a custom fallback method."""
        self.fallback_manager.register_fallback(
            operation=operation,
            name=name,
            function=function,
            priority=priority,
            timeout=timeout
        )
        logger.info(f"Registered fallback method '{name}' for operation '{operation}'")
    
    def register_retry_config(self, operation: str, config):
        """Register custom retry configuration."""
        self.retry_manager.register_retry_config(operation, config)
        logger.info(f"Registered retry config for operation '{operation}'")
    
    def register_error_category(self, error_type: str, category: ErrorCategory):
        """Register custom error categorization."""
        self.error_handler.register_error_category(error_type, category)
        logger.info(f"Registered error category: {error_type} -> {category.value}")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health information."""
        return {
            'error_handler': {
                'statistics': self.error_handler.get_error_statistics()
            },
            'fallback_manager': {
                'statistics': self.fallback_manager.get_fallback_statistics()
            },
            'retry_manager': {
                'statistics': self.retry_manager.get_retry_statistics(),
                'circuit_breakers': self.retry_manager.get_circuit_breaker_status()
            },
            'error_reporter': {
                'statistics': self.error_reporter.get_error_statistics()
            },
            'system_config': {
                'enable_fallbacks': self.enable_fallbacks,
                'enable_retries': self.enable_retries,
                'enable_reporting': self.enable_reporting
            }
        }
    
    def get_error_reports(self, **filters) -> List[ErrorReport]:
        """Get error reports with filtering."""
        return self.error_reporter.get_error_reports(**filters)
    
    def resolve_error(self, error_id: str, resolution_notes: str, resolved_by: Optional[str] = None) -> bool:
        """Resolve an error."""
        return self.error_reporter.resolve_error(error_id, resolution_notes, resolved_by)
    
    def export_error_reports(self, output_file: str, format: str = 'json', **filters) -> bool:
        """Export error reports to file."""
        return self.error_reporter.export_error_reports(output_file, format, filters)
    
    def clear_old_data(self, days: int = 30):
        """Clear old error data."""
        self.error_handler.clear_error_history()
        self.retry_manager.clear_statistics()
        self.fallback_manager.clear_cache()
        cleared_reports = self.error_reporter.clear_old_errors(days)
        
        logger.info(f"Cleared old error data: {cleared_reports} reports removed")
    
    def enable_system_component(self, component: str):
        """Enable a system component."""
        if component == 'fallbacks':
            self.enable_fallbacks = True
        elif component == 'retries':
            self.enable_retries = True
        elif component == 'reporting':
            self.enable_reporting = True
        else:
            logger.warning(f"Unknown system component: {component}")
            return
        
        logger.info(f"Enabled system component: {component}")
    
    def disable_system_component(self, component: str):
        """Disable a system component."""
        if component == 'fallbacks':
            self.enable_fallbacks = False
        elif component == 'retries':
            self.enable_retries = False
        elif component == 'reporting':
            self.enable_reporting = False
        else:
            logger.warning(f"Unknown system component: {component}")
            return
        
        logger.info(f"Disabled system component: {component}")
    
    def with_protection(
        self,
        operation: str,
        service: str,
        enable_fallback: bool = True,
        enable_retry: bool = True,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    ):
        """Decorator for adding error protection to functions."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                result = self.execute_with_protection(
                    operation=operation,
                    service=service,
                    func=func,
                    *args,
                    enable_fallback=enable_fallback,
                    enable_retry=enable_retry,
                    retry_strategy=retry_strategy,
                    **kwargs
                )
                
                if result.success:
                    return result.data
                else:
                    raise ProcessingError(
                        message=result.error_message,
                        operation=operation
                    )
            
            return wrapper
        return decorator
    
    def with_protection_async(
        self,
        operation: str,
        service: str,
        enable_fallback: bool = True,
        enable_retry: bool = True,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    ):
        """Decorator for adding error protection to async functions."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                result = await self.execute_with_protection_async(
                    operation=operation,
                    service=service,
                    func=func,
                    *args,
                    enable_fallback=enable_fallback,
                    enable_retry=enable_retry,
                    retry_strategy=retry_strategy,
                    **kwargs
                )
                
                if result.success:
                    return result.data
                else:
                    raise ProcessingError(
                        message=result.error_message,
                        operation=operation
                    )
            
            return wrapper
        return decorator

# Global instance
enhanced_error_system = EnhancedProcessingErrorSystem()