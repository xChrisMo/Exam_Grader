"""
Enhanced Error Handling Service

This service provides comprehensive error handling and recovery mechanisms
for the LLM training system.
"""

import traceback
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone, timedelta
from enum import Enum

from utils.logger import logger

class ErrorType(Enum):
    """Error type enumeration"""
    NETWORK_ERROR = "network"
    VALIDATION_ERROR = "validation"
    SERVER_ERROR = "server"
    TIMEOUT_ERROR = "timeout"
    FILE_PROCESSING_ERROR = "file_processing"
    TRAINING_ERROR = "training"
    DATABASE_ERROR = "database"
    AUTHENTICATION_ERROR = "authentication"
    PERMISSION_ERROR = "permission"
    RESOURCE_ERROR = "resource"
    UNKNOWN_ERROR = "unknown"

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class LLMTrainingError(Exception):
    """Custom exception for LLM training operations"""
    
    def __init__(self, message: str, error_type: ErrorType, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 details: Optional[Dict[str, Any]] = None, recoverable: bool = True):
        super().__init__(message)
        self.error_type = error_type
        self.severity = severity
        self.details = details or {}
        self.recoverable = recoverable
        self.timestamp = datetime.now(timezone.utc)
        self.error_id = f"{error_type.value}_{int(time.time())}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        return {
            'error_id': self.error_id,
            'message': str(self),
            'type': self.error_type.value,
            'severity': self.severity.value,
            'recoverable': self.recoverable,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'traceback': traceback.format_exc() if self.details.get('include_traceback') else None
        }

class LLMTrainingErrorHandler:
    """Comprehensive error handler for LLM training operations"""
    
    def __init__(self):
        self.error_history: List[Dict[str, Any]] = []
        self.recovery_strategies: Dict[ErrorType, List[Callable]] = {
            ErrorType.FILE_PROCESSING_ERROR: [
                self._retry_with_fallback_method,
                self._try_alternative_extraction,
                self._manual_processing_suggestion
            ],
            ErrorType.TRAINING_ERROR: [
                self._resume_from_checkpoint,
                self._adjust_training_parameters,
                self._restart_with_validation
            ],
            ErrorType.NETWORK_ERROR: [
                self._retry_with_backoff,
                self._switch_to_offline_mode,
                self._queue_for_later
            ],
            ErrorType.DATABASE_ERROR: [
                self._retry_database_operation,
                self._use_cached_data,
                self._rollback_transaction
            ],
            ErrorType.VALIDATION_ERROR: [
                self._provide_validation_guidance,
                self._suggest_data_fixes,
                self._skip_invalid_items
            ]
        }
    
    @staticmethod
    def handle_file_processing_error(error: Exception, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file processing errors with fallback options"""
        try:
            # Categorize the error
            if "encoding" in str(error).lower():
                error_type = ErrorType.FILE_PROCESSING_ERROR
                recovery_suggestions = [
                    "Try different character encoding (UTF-8, Latin-1, CP1252)",
                    "Check if file is corrupted or incomplete",
                    "Use alternative text extraction method"
                ]
            elif "permission" in str(error).lower():
                error_type = ErrorType.PERMISSION_ERROR
                recovery_suggestions = [
                    "Check file permissions",
                    "Ensure file is not locked by another process",
                    "Try copying file to temporary location"
                ]
            elif "not found" in str(error).lower():
                error_type = ErrorType.FILE_PROCESSING_ERROR
                recovery_suggestions = [
                    "Verify file path is correct",
                    "Check if file was moved or deleted",
                    "Re-upload the file"
                ]
            else:
                error_type = ErrorType.FILE_PROCESSING_ERROR
                recovery_suggestions = [
                    "Try alternative file processing method",
                    "Check file format compatibility",
                    "Contact support if issue persists"
                ]
            
            # Create structured error response
            error_response = {
                'success': False,
                'error_type': error_type.value,
                'error_message': str(error),
                'file_info': {
                    'name': file_info.get('name', 'unknown'),
                    'size': file_info.get('size', 0),
                    'type': file_info.get('type', 'unknown')
                },
                'recovery_suggestions': recovery_suggestions,
                'retry_possible': True,
                'fallback_available': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.error(f"File processing error for {file_info.get('name', 'unknown')}: {error}")
            return error_response
            
        except Exception as e:
            logger.error(f"Error in file processing error handler: {e}")
            return {
                'success': False,
                'error_type': ErrorType.UNKNOWN_ERROR.value,
                'error_message': 'Unknown error occurred during file processing',
                'recovery_suggestions': ['Contact support'],
                'retry_possible': False,
                'fallback_available': False
            }
    
    @staticmethod
    def handle_training_error(error: Exception, job_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle training errors with recovery options"""
        context = context or {}
        
        try:
            # Categorize training error
            error_str = str(error).lower()
            
            if "out of memory" in error_str or "cuda out of memory" in error_str:
                error_type = ErrorType.RESOURCE_ERROR
                recovery_suggestions = [
                    "Reduce batch size in training configuration",
                    "Use gradient accumulation to simulate larger batches",
                    "Try training on CPU if GPU memory is insufficient",
                    "Clear GPU cache and restart training"
                ]
                auto_recovery = {
                    'reduce_batch_size': True,
                    'enable_gradient_checkpointing': True,
                    'clear_cache': True
                }
            elif "connection" in error_str or "timeout" in error_str:
                error_type = ErrorType.NETWORK_ERROR
                recovery_suggestions = [
                    "Check internet connection",
                    "Retry training with exponential backoff",
                    "Switch to offline training mode if available"
                ]
                auto_recovery = {
                    'retry_with_backoff': True,
                    'max_retries': 3
                }
            elif "validation" in error_str or "invalid" in error_str:
                error_type = ErrorType.VALIDATION_ERROR
                recovery_suggestions = [
                    "Check training data format and quality",
                    "Validate dataset integrity",
                    "Review training configuration parameters"
                ]
                auto_recovery = {
                    'validate_data': True,
                    'check_config': True
                }
            elif "checkpoint" in error_str:
                error_type = ErrorType.TRAINING_ERROR
                recovery_suggestions = [
                    "Resume training from last valid checkpoint",
                    "Clear corrupted checkpoint files",
                    "Restart training with checkpoint disabled"
                ]
                auto_recovery = {
                    'resume_from_checkpoint': True,
                    'clear_corrupted_checkpoints': True
                }
            else:
                error_type = ErrorType.TRAINING_ERROR
                recovery_suggestions = [
                    "Review training logs for specific error details",
                    "Check training data and configuration",
                    "Restart training with default parameters"
                ]
                auto_recovery = {
                    'restart_with_defaults': True
                }
            
            error_response = {
                'success': False,
                'error_type': error_type.value,
                'error_message': str(error),
                'job_id': job_id,
                'context': context,
                'recovery_suggestions': recovery_suggestions,
                'auto_recovery_options': auto_recovery,
                'can_resume': 'checkpoint' in context,
                'estimated_recovery_time': '5-10 minutes',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.error(f"Training error for job {job_id}: {error}")
            return error_response
            
        except Exception as e:
            logger.error(f"Error in training error handler: {e}")
            return {
                'success': False,
                'error_type': ErrorType.UNKNOWN_ERROR.value,
                'error_message': 'Unknown training error occurred',
                'job_id': job_id,
                'recovery_suggestions': ['Contact support'],
                'auto_recovery_options': {},
                'can_resume': False
            }
    
    @staticmethod
    def handle_validation_error(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle validation errors with detailed feedback"""
        try:
            error_str = str(error).lower()
            
            # Categorize validation error
            if "required" in error_str or "missing" in error_str:
                validation_type = "missing_required_field"
                suggestions = [
                    "Check that all required fields are provided",
                    "Review the API documentation for required parameters",
                    "Ensure data is properly formatted"
                ]
            elif "format" in error_str or "invalid format" in error_str:
                validation_type = "invalid_format"
                suggestions = [
                    "Check data format matches expected schema",
                    "Validate file extensions and MIME types",
                    "Ensure numeric values are within valid ranges"
                ]
            elif "size" in error_str or "too large" in error_str or "too small" in error_str:
                validation_type = "size_constraint"
                suggestions = [
                    "Check file size limits",
                    "Compress large files if possible",
                    "Split large datasets into smaller chunks"
                ]
            elif "duplicate" in error_str:
                validation_type = "duplicate_data"
                suggestions = [
                    "Remove duplicate entries",
                    "Check for existing records with same identifier",
                    "Use update operation instead of create"
                ]
            else:
                validation_type = "general_validation"
                suggestions = [
                    "Review input data for correctness",
                    "Check data types and constraints",
                    "Validate against schema requirements"
                ]
            
            error_response = {
                'success': False,
                'error_type': ErrorType.VALIDATION_ERROR.value,
                'validation_type': validation_type,
                'error_message': str(error),
                'context': context,
                'field_errors': LLMTrainingErrorHandler._extract_field_errors(error),
                'suggestions': suggestions,
                'can_auto_fix': validation_type in ['duplicate_data', 'size_constraint'],
                'severity': 'medium',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.warning(f"Validation error: {error}")
            return error_response
            
        except Exception as e:
            logger.error(f"Error in validation error handler: {e}")
            return {
                'success': False,
                'error_type': ErrorType.VALIDATION_ERROR.value,
                'error_message': 'Validation error occurred',
                'suggestions': ['Check input data and try again']
            }
    
    @staticmethod
    def _extract_field_errors(error: Exception) -> List[Dict[str, str]]:
        """Extract field-specific errors from validation exception"""
        field_errors = []
        error_str = str(error)
        
        # In a real implementation, this would be more sophisticated
        if "name" in error_str.lower():
            field_errors.append({
                'field': 'name',
                'message': 'Name field validation failed',
                'code': 'invalid_name'
            })
        
        if "email" in error_str.lower():
            field_errors.append({
                'field': 'email',
                'message': 'Email format is invalid',
                'code': 'invalid_email'
            })
        
        return field_errors
    
    def _retry_with_fallback_method(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Retry operation with fallback method"""
        return {
            'strategy': 'fallback_method',
            'action': 'retry_with_alternative',
            'estimated_time': '2-5 minutes',
            'success_probability': 0.7
        }
    
    def _try_alternative_extraction(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Try alternative text extraction method"""
        return {
            'strategy': 'alternative_extraction',
            'action': 'use_different_library',
            'estimated_time': '1-3 minutes',
            'success_probability': 0.6
        }
    
    def _manual_processing_suggestion(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Suggest manual processing"""
        return {
            'strategy': 'manual_processing',
            'action': 'convert_file_manually',
            'estimated_time': '5-10 minutes',
            'success_probability': 0.9
        }
    
    def _resume_from_checkpoint(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Resume training from checkpoint"""
        return {
            'strategy': 'resume_checkpoint',
            'action': 'load_last_checkpoint',
            'estimated_time': '1-2 minutes',
            'success_probability': 0.8
        }
    
    def _adjust_training_parameters(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Adjust training parameters"""
        return {
            'strategy': 'adjust_parameters',
            'action': 'reduce_batch_size_and_learning_rate',
            'estimated_time': '30 seconds',
            'success_probability': 0.7
        }
    
    def _restart_with_validation(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Restart with validation"""
        return {
            'strategy': 'restart_validated',
            'action': 'validate_data_and_restart',
            'estimated_time': '3-5 minutes',
            'success_probability': 0.8
        }
    
    def _retry_with_backoff(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Retry with exponential backoff"""
        return {
            'strategy': 'exponential_backoff',
            'action': 'retry_with_increasing_delays',
            'estimated_time': '1-10 minutes',
            'success_probability': 0.6
        }
    
    def _switch_to_offline_mode(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Switch to offline mode"""
        return {
            'strategy': 'offline_mode',
            'action': 'use_cached_resources',
            'estimated_time': '30 seconds',
            'success_probability': 0.5
        }
    
    def _queue_for_later(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Queue operation for later"""
        return {
            'strategy': 'queue_operation',
            'action': 'add_to_retry_queue',
            'estimated_time': '10-30 minutes',
            'success_probability': 0.9
        }
    
    def _retry_database_operation(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Retry database operation"""
        return {
            'strategy': 'database_retry',
            'action': 'retry_with_connection_refresh',
            'estimated_time': '30 seconds',
            'success_probability': 0.8
        }
    
    def _use_cached_data(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Use cached data"""
        return {
            'strategy': 'use_cache',
            'action': 'fallback_to_cached_data',
            'estimated_time': '10 seconds',
            'success_probability': 0.7
        }
    
    def _rollback_transaction(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Rollback database transaction"""
        return {
            'strategy': 'rollback',
            'action': 'rollback_and_retry',
            'estimated_time': '1 minute',
            'success_probability': 0.8
        }
    
    def _provide_validation_guidance(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Provide validation guidance"""
        return {
            'strategy': 'validation_guidance',
            'action': 'show_detailed_validation_errors',
            'estimated_time': '0 seconds',
            'success_probability': 1.0
        }
    
    def _suggest_data_fixes(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Suggest data fixes"""
        return {
            'strategy': 'data_fixes',
            'action': 'provide_fix_suggestions',
            'estimated_time': '0 seconds',
            'success_probability': 1.0
        }
    
    def _skip_invalid_items(self, error: LLMTrainingError) -> Dict[str, Any]:
        """Skip invalid items"""
        return {
            'strategy': 'skip_invalid',
            'action': 'continue_with_valid_items',
            'estimated_time': '30 seconds',
            'success_probability': 0.9
        }
    
    def get_recovery_options(self, error: LLMTrainingError) -> List[Dict[str, Any]]:
        """Get available recovery options for an error"""
        strategies = self.recovery_strategies.get(error.error_type, [])
        return [strategy(error) for strategy in strategies]
    
    def log_error(self, error: LLMTrainingError, context: Dict[str, Any] = None) -> None:
        """Log error with context"""
        error_entry = {
            'error': error.to_dict(),
            'context': context or {},
            'logged_at': datetime.now(timezone.utc).isoformat()
        }
        
        self.error_history.append(error_entry)
        
        # Log based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {error}")
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error: {error}")
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error: {error}")
        else:
            logger.info(f"Low severity error: {error}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.error_history:
            return {'total_errors': 0}
        
        # Count errors by type
        error_counts = {}
        severity_counts = {}
        
        for entry in self.error_history:
            error_type = entry['error']['type']
            severity = entry['error']['severity']
            
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'total_errors': len(self.error_history),
            'error_types': error_counts,
            'severity_distribution': severity_counts,
            'most_common_error': max(error_counts.items(), key=lambda x: x[1])[0] if error_counts else None,
            'error_rate_last_hour': self._calculate_error_rate(timedelta(hours=1)),
            'error_rate_last_day': self._calculate_error_rate(timedelta(days=1))
        }
    
    def _calculate_error_rate(self, time_window: timedelta) -> float:
        """Calculate error rate within time window"""
        cutoff_time = datetime.now(timezone.utc) - time_window
        recent_errors = [
            entry for entry in self.error_history
            if datetime.fromisoformat(entry['logged_at']) > cutoff_time
        ]
        return len(recent_errors)

class RetryManager:
    """Manages retry logic with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def retry_with_backoff(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    # Last attempt failed
                    break
                
                # Calculate delay with exponential backoff
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                logger.info(f"Operation failed (attempt {attempt + 1}/{self.max_retries + 1}), retrying in {delay}s: {e}")
                time.sleep(delay)
        
        # All retries failed
        raise LLMTrainingError(
            f"Operation failed after {self.max_retries + 1} attempts: {last_exception}",
            ErrorType.UNKNOWN_ERROR,
            ErrorSeverity.HIGH,
            details={'last_exception': str(last_exception), 'attempts': self.max_retries + 1}
        )