"""
Error Recovery Service

Provides automatic error recovery mechanisms, retry logic,
and fallback strategies for training processes.
"""

import time
import asyncio
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass
from functools import wraps
import threading
from concurrent.futures import ThreadPoolExecutor, Future

from src.services.error_monitor import error_monitor, ErrorCategory, ErrorSeverity
from utils.logger import logger


class RetryStrategy(Enum):
    """Retry strategies"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"
    IMMEDIATE = "immediate"


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    backoff_multiplier: float = 2.0
    jitter: bool = True


@dataclass
class FallbackConfig:
    """Fallback configuration"""
    enabled: bool = True
    fallback_function: Optional[Callable] = None
    fallback_args: tuple = ()
    fallback_kwargs: dict = None


class ErrorRecoveryService:
    """
    Service for automatic error recovery and retry mechanisms
    """
    
    def __init__(self):
        """Initialize error recovery service"""
        self.active_recoveries = {}
        self.recovery_stats = {
            'total_attempts': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'fallback_uses': 0
        }
        self.executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="recovery")
    
    def with_retry(self, 
                   retry_config: Optional[RetryConfig] = None,
                   fallback_config: Optional[FallbackConfig] = None,
                   error_categories: Optional[List[ErrorCategory]] = None):
        """
        Decorator for automatic retry and fallback functionality
        
        Args:
            retry_config: Retry configuration
            fallback_config: Fallback configuration
            error_categories: Error categories to handle (None = all)
            
        Returns:
            Decorated function with retry/fallback capability
        """
        if retry_config is None:
            retry_config = RetryConfig()
        
        if fallback_config is None:
            fallback_config = FallbackConfig(enabled=False)
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self._execute_with_recovery(
                    func, args, kwargs, retry_config, fallback_config, error_categories
                )
            return wrapper
        return decorator
    
    def execute_with_recovery(self,
                            func: Callable,
                            args: tuple = (),
                            kwargs: Optional[Dict] = None,
                            retry_config: Optional[RetryConfig] = None,
                            fallback_config: Optional[FallbackConfig] = None,
                            error_categories: Optional[List[ErrorCategory]] = None) -> Any:
        """
        Execute function with automatic recovery
        
        Args:
            func: Function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            retry_config: Retry configuration
            fallback_config: Fallback configuration
            error_categories: Error categories to handle
            
        Returns:
            Function result or fallback result
        """
        if kwargs is None:
            kwargs = {}
        
        if retry_config is None:
            retry_config = RetryConfig()
        
        if fallback_config is None:
            fallback_config = FallbackConfig(enabled=False)
        
        return self._execute_with_recovery(
            func, args, kwargs, retry_config, fallback_config, error_categories
        )
    
    def recover_training_session(self, session_id: str) -> Dict[str, Any]:
        """
        Attempt to recover a failed training session
        
        Args:
            session_id: Training session ID
            
        Returns:
            Recovery result
        """
        try:
            logger.info(f"Attempting to recover training session: {session_id}")
            
            # TODO: Implement actual session recovery logic
            # This should:
            # 1. Check session state and error history
            # 2. Identify recovery strategy based on failure type
            # 3. Attempt to resume from last checkpoint
            # 4. Validate recovered state
            # 5. Update session status
            
            recovery_result = {
                'session_id': session_id,
                'recovery_attempted': True,
                'recovery_successful': False,
                'recovery_method': 'checkpoint_resume',
                'recovery_notes': 'Recovery not yet implemented',
                'timestamp': time.time()
            }
            
            return recovery_result
            
        except Exception as e:
            error_id = error_monitor.log_error(
                error=e,
                category=ErrorCategory.TRAINING_PROCESS,
                component="error_recovery",
                session_id=session_id,
                additional_context={'operation': 'session_recovery'}
            )
            
            return {
                'session_id': session_id,
                'recovery_attempted': True,
                'recovery_successful': False,
                'error_id': error_id,
                'error_message': str(e),
                'timestamp': time.time()
            }
    
    def recover_file_processing(self, file_path: str, processing_type: str) -> Dict[str, Any]:
        """
        Attempt to recover failed file processing
        
        Args:
            file_path: Path to the file
            processing_type: Type of processing (ocr, llm, etc.)
            
        Returns:
            Recovery result
        """
        try:
            logger.info(f"Attempting to recover file processing: {file_path} ({processing_type})")
            
            recovery_strategies = {
                'ocr': self._recover_ocr_processing,
                'llm': self._recover_llm_processing,
                'pdf': self._recover_pdf_processing,
                'image': self._recover_image_processing
            }
            
            recovery_func = recovery_strategies.get(processing_type)
            if not recovery_func:
                raise ValueError(f"Unknown processing type: {processing_type}")
            
            return recovery_func(file_path)
            
        except Exception as e:
            error_id = error_monitor.log_error(
                error=e,
                category=ErrorCategory.FILE_PROCESSING,
                component="error_recovery",
                additional_context={
                    'operation': 'file_processing_recovery',
                    'file_path': file_path,
                    'processing_type': processing_type
                }
            )
            
            return {
                'file_path': file_path,
                'processing_type': processing_type,
                'recovery_attempted': True,
                'recovery_successful': False,
                'error_id': error_id,
                'error_message': str(e),
                'timestamp': time.time()
            }
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """
        Get error recovery statistics
        
        Returns:
            Recovery statistics
        """
        try:
            total_attempts = self.recovery_stats['total_attempts']
            successful = self.recovery_stats['successful_recoveries']
            
            success_rate = (successful / total_attempts * 100) if total_attempts > 0 else 0.0
            
            return {
                'total_recovery_attempts': total_attempts,
                'successful_recoveries': successful,
                'failed_recoveries': self.recovery_stats['failed_recoveries'],
                'fallback_uses': self.recovery_stats['fallback_uses'],
                'success_rate': success_rate,
                'active_recoveries': len(self.active_recoveries)
            }
            
        except Exception as e:
            logger.error(f"Error getting recovery statistics: {e}")
            return {'error': str(e)}
    
    def _execute_with_recovery(self,
                             func: Callable,
                             args: tuple,
                             kwargs: Dict,
                             retry_config: RetryConfig,
                             fallback_config: FallbackConfig,
                             error_categories: Optional[List[ErrorCategory]]) -> Any:
        """Execute function with retry and fallback logic"""
        last_exception = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                self.recovery_stats['total_attempts'] += 1
                
                # Execute the function
                result = func(*args, **kwargs)
                
                # Success - update stats and return
                if attempt > 0:  # Only count as recovery if it wasn't first attempt
                    self.recovery_stats['successful_recoveries'] += 1
                    logger.info(f"Function {func.__name__} succeeded after {attempt + 1} attempts")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Log the error
                error_id = error_monitor.log_error(
                    error=e,
                    component=f"{func.__module__}.{func.__name__}",
                    additional_context={
                        'attempt': attempt + 1,
                        'max_attempts': retry_config.max_attempts,
                        'args': str(args)[:200],  # Truncate for logging
                        'kwargs': str(kwargs)[:200]
                    }
                )
                
                # Check if we should retry this error category
                if error_categories is not None:
                    error_category = error_monitor._categorize_error(str(e))
                    if error_category not in error_categories:
                        logger.info(f"Error category {error_category.value} not in retry list, not retrying")
                        break
                
                # If this is the last attempt, don't wait
                if attempt == retry_config.max_attempts - 1:
                    break
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt, retry_config)
                logger.info(f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {delay:.2f}s")
                
                time.sleep(delay)
        
        # All retries failed
        self.recovery_stats['failed_recoveries'] += 1
        
        # Try fallback if configured
        if fallback_config.enabled and fallback_config.fallback_function:
            try:
                logger.info(f"Attempting fallback for {func.__name__}")
                self.recovery_stats['fallback_uses'] += 1
                
                fallback_kwargs = fallback_config.fallback_kwargs or {}
                return fallback_config.fallback_function(*fallback_config.fallback_args, **fallback_kwargs)
                
            except Exception as fallback_error:
                error_monitor.log_error(
                    error=fallback_error,
                    component=f"{func.__module__}.{func.__name__}_fallback",
                    additional_context={'original_error': str(last_exception)}
                )
                
                # Re-raise the original exception, not the fallback error
                raise last_exception
        
        # No fallback or fallback failed, raise original exception
        raise last_exception
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for retry attempt"""
        if config.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        
        elif config.strategy == RetryStrategy.FIXED_INTERVAL:
            delay = config.base_delay
        
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * (attempt + 1)
        
        elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.backoff_multiplier ** attempt)
        
        else:
            delay = config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, config.max_delay)
        
        # Add jitter if enabled
        if config.jitter:
            import random
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(0.0, delay)
    
    def _recover_ocr_processing(self, file_path: str) -> Dict[str, Any]:
        """Recover OCR processing"""
        try:
            # TODO: Implement OCR recovery strategies
            # - Try different OCR engines
            # - Adjust image preprocessing
            # - Use different confidence thresholds
            
            return {
                'file_path': file_path,
                'processing_type': 'ocr',
                'recovery_attempted': True,
                'recovery_successful': False,
                'recovery_method': 'alternative_engine',
                'recovery_notes': 'OCR recovery not yet implemented',
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise e
    
    def _recover_llm_processing(self, file_path: str) -> Dict[str, Any]:
        """Recover LLM processing"""
        try:
            # TODO: Implement LLM recovery strategies
            # - Try different models
            # - Adjust prompts
            # - Use different API endpoints
            
            return {
                'file_path': file_path,
                'processing_type': 'llm',
                'recovery_attempted': True,
                'recovery_successful': False,
                'recovery_method': 'alternative_model',
                'recovery_notes': 'LLM recovery not yet implemented',
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise e
    
    def _recover_pdf_processing(self, file_path: str) -> Dict[str, Any]:
        """Recover PDF processing"""
        try:
            # TODO: Implement PDF recovery strategies
            # - Try different PDF libraries
            # - Handle corrupted PDFs
            # - Extract images and use OCR
            
            return {
                'file_path': file_path,
                'processing_type': 'pdf',
                'recovery_attempted': True,
                'recovery_successful': False,
                'recovery_method': 'alternative_library',
                'recovery_notes': 'PDF recovery not yet implemented',
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise e
    
    def _recover_image_processing(self, file_path: str) -> Dict[str, Any]:
        """Recover image processing"""
        try:
            # TODO: Implement image recovery strategies
            # - Try different image libraries
            # - Apply image enhancement
            # - Convert formats
            
            return {
                'file_path': file_path,
                'processing_type': 'image',
                'recovery_attempted': True,
                'recovery_successful': False,
                'recovery_method': 'format_conversion',
                'recovery_notes': 'Image recovery not yet implemented',
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise e


# Global instance
error_recovery_service = ErrorRecoveryService()