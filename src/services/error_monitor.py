"""
Error Logging and Monitoring System

Provides comprehensive error logging, categorization, recovery mechanisms,
and system health monitoring for training processes.
"""

import json
import os
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
import time
from collections import defaultdict, deque

from src.database.models import db
from utils.logger import logger


class ErrorCategory(Enum):
    """Error categories for classification"""
    FILE_UPLOAD = "file_upload"
    FILE_PROCESSING = "file_processing"
    LLM_SERVICE = "llm_service"
    OCR_SERVICE = "ocr_service"
    DATABASE = "database"
    TRAINING_PROCESS = "training_process"
    REPORT_GENERATION = "report_generation"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    SYSTEM = "system"
    NETWORK = "network"
    CONFIGURATION = "configuration"


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """Recovery actions for errors"""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ABORT = "abort"
    MANUAL_INTERVENTION = "manual_intervention"
    IGNORE = "ignore"


@dataclass
class ErrorRecord:
    """Error record structure"""
    id: str
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any]
    stack_trace: Optional[str]
    user_id: Optional[int]
    session_id: Optional[str]
    component: str
    recovery_action: Optional[RecoveryAction]
    recovery_attempts: int
    resolved: bool
    resolution_notes: Optional[str]


@dataclass
class SystemHealthMetrics:
    """System health metrics"""
    timestamp: datetime
    error_rate: float
    critical_errors_count: int
    active_sessions: int
    failed_sessions: int
    average_response_time: float
    memory_usage: float
    disk_usage: float
    service_status: Dict[str, bool]


class ErrorMonitor:
    """
    Comprehensive error monitoring and logging system
    """
    
    def __init__(self, log_dir: str = "logs/training"):
        """
        Initialize error monitor
        
        Args:
            log_dir: Directory for error logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory error tracking
        self.error_history = deque(maxlen=1000)  # Keep last 1000 errors
        self.error_counts = defaultdict(int)
        self.recovery_stats = defaultdict(int)
        
        # Health monitoring
        self.health_metrics = deque(maxlen=100)  # Keep last 100 health checks
        self.service_status = {}
        
        # Threading for background monitoring
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Error patterns for automatic categorization
        self.error_patterns = {
            ErrorCategory.FILE_UPLOAD: [
                "file size", "file type", "upload", "multipart",
                "file not found", "permission denied"
            ],
            ErrorCategory.LLM_SERVICE: [
                "openai", "llm", "api key", "rate limit", "token",
                "model", "completion", "embedding"
            ],
            ErrorCategory.OCR_SERVICE: [
                "ocr", "handwriting", "image", "text extraction",
                "vision", "tesseract", "easyocr"
            ],
            ErrorCategory.DATABASE: [
                "database", "sql", "connection", "transaction",
                "constraint", "foreign key", "rollback"
            ],
            ErrorCategory.TRAINING_PROCESS: [
                "training", "session", "guide processing",
                "question extraction", "confidence"
            ]
        }
    
    def log_error(self, 
                  error: Exception,
                  category: Optional[ErrorCategory] = None,
                  severity: Optional[ErrorSeverity] = None,
                  user_id: Optional[int] = None,
                  session_id: Optional[str] = None,
                  component: str = "unknown",
                  additional_context: Optional[Dict] = None) -> str:
        """
        Log an error with comprehensive details
        
        Args:
            error: Exception object
            category: Error category (auto-detected if None)
            severity: Error severity (auto-detected if None)
            user_id: User ID associated with error
            session_id: Session ID associated with error
            component: Component where error occurred
            additional_context: Additional context information
            
        Returns:
            Error ID for tracking
        """
        try:
            # Generate unique error ID
            error_id = f"err_{int(time.time() * 1000)}_{threading.get_ident()}"
            
            # Auto-detect category if not provided
            if category is None:
                category = self._categorize_error(str(error))
            
            # Auto-detect severity if not provided
            if severity is None:
                severity = self._assess_severity(error, category)
            
            # Create error record
            error_record = ErrorRecord(
                id=error_id,
                timestamp=datetime.now(),
                category=category,
                severity=severity,
                message=str(error),
                details={
                    "error_type": type(error).__name__,
                    "component": component,
                    "additional_context": additional_context or {},
                    "thread_id": threading.get_ident(),
                    "process_id": os.getpid() if hasattr(os, 'getpid') else None
                },
                stack_trace=traceback.format_exc(),
                user_id=user_id,
                session_id=session_id,
                component=component,
                recovery_action=None,
                recovery_attempts=0,
                resolved=False,
                resolution_notes=None
            )
            
            # Add to in-memory tracking
            self.error_history.append(error_record)
            self.error_counts[category] += 1
            
            # Log to file
            self._write_error_log(error_record)
            
            # Log to application logger
            logger.error(f"[{error_id}] {category.value.upper()}: {str(error)}", 
                        extra={
                            "error_id": error_id,
                            "category": category.value,
                            "severity": severity.value,
                            "user_id": user_id,
                            "session_id": session_id,
                            "component": component
                        })
            
            # Trigger alerts for critical errors
            if severity == ErrorSeverity.CRITICAL:
                self._trigger_critical_alert(error_record)
            
            # Attempt automatic recovery
            recovery_action = self._determine_recovery_action(error_record)
            if recovery_action:
                self._attempt_recovery(error_record, recovery_action)
            
            return error_id
            
        except Exception as e:
            # Fallback logging if error monitoring fails
            logger.critical(f"Error monitor failed: {e}")
            return "error_monitor_failed"
    
    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get error statistics for the specified time period
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dict containing error statistics
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Filter recent errors
            recent_errors = [
                error for error in self.error_history
                if error.timestamp >= cutoff_time
            ]
            
            if not recent_errors:
                return {
                    "total_errors": 0,
                    "error_rate": 0.0,
                    "by_category": {},
                    "by_severity": {},
                    "by_component": {},
                    "recovery_success_rate": 0.0,
                    "top_errors": []
                }
            
            # Calculate statistics
            total_errors = len(recent_errors)
            error_rate = total_errors / hours  # Errors per hour
            
            # Group by category
            by_category = defaultdict(int)
            for error in recent_errors:
                by_category[error.category.value] += 1
            
            # Group by severity
            by_severity = defaultdict(int)
            for error in recent_errors:
                by_severity[error.severity.value] += 1
            
            # Group by component
            by_component = defaultdict(int)
            for error in recent_errors:
                by_component[error.component] += 1
            
            # Calculate recovery success rate
            errors_with_recovery = [e for e in recent_errors if e.recovery_attempts > 0]
            resolved_errors = [e for e in errors_with_recovery if e.resolved]
            recovery_success_rate = (len(resolved_errors) / len(errors_with_recovery) * 100 
                                   if errors_with_recovery else 0.0)
            
            # Get top error messages
            error_messages = defaultdict(int)
            for error in recent_errors:
                error_messages[error.message] += 1
            
            top_errors = sorted(error_messages.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "period_hours": hours,
                "total_errors": total_errors,
                "error_rate": error_rate,
                "by_category": dict(by_category),
                "by_severity": dict(by_severity),
                "by_component": dict(by_component),
                "recovery_success_rate": recovery_success_rate,
                "top_errors": [{"message": msg, "count": count} for msg, count in top_errors]
            }
            
        except Exception as e:
            logger.error(f"Error getting error statistics: {e}")
            return {"error": str(e)}
    
    def get_system_health(self) -> SystemHealthMetrics:
        """
        Get current system health metrics
        
        Returns:
            SystemHealthMetrics object
        """
        try:
            # Calculate error rate (errors per hour in last hour)
            one_hour_ago = datetime.now() - timedelta(hours=1)
            recent_errors = [
                error for error in self.error_history
                if error.timestamp >= one_hour_ago
            ]
            error_rate = len(recent_errors)
            
            # Count critical errors in last 24 hours
            twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
            critical_errors = [
                error for error in self.error_history
                if (error.timestamp >= twenty_four_hours_ago and 
                    error.severity == ErrorSeverity.CRITICAL)
            ]
            critical_errors_count = len(critical_errors)
            
            # TODO: Get actual system metrics
            # For now, return mock data
            health_metrics = SystemHealthMetrics(
                timestamp=datetime.now(),
                error_rate=error_rate,
                critical_errors_count=critical_errors_count,
                active_sessions=self._get_active_sessions_count(),
                failed_sessions=self._get_failed_sessions_count(),
                average_response_time=self._get_average_response_time(),
                memory_usage=self._get_memory_usage(),
                disk_usage=self._get_disk_usage(),
                service_status=self.service_status.copy()
            )
            
            # Add to health history
            self.health_metrics.append(health_metrics)
            
            return health_metrics
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            # Return minimal health metrics
            return SystemHealthMetrics(
                timestamp=datetime.now(),
                error_rate=0.0,
                critical_errors_count=0,
                active_sessions=0,
                failed_sessions=0,
                average_response_time=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                service_status={}
            )
    
    def start_monitoring(self, interval: int = 60):
        """
        Start background health monitoring
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info("Error monitoring started")
    
    def stop_monitoring(self):
        """Stop background health monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Error monitoring stopped")
    
    def resolve_error(self, error_id: str, resolution_notes: str) -> bool:
        """
        Mark an error as resolved
        
        Args:
            error_id: Error ID to resolve
            resolution_notes: Notes about the resolution
            
        Returns:
            Success status
        """
        try:
            for error in self.error_history:
                if error.id == error_id:
                    error.resolved = True
                    error.resolution_notes = resolution_notes
                    
                    # Log resolution
                    logger.info(f"Error {error_id} resolved: {resolution_notes}")
                    
                    return True
            
            logger.warning(f"Error {error_id} not found for resolution")
            return False
            
        except Exception as e:
            logger.error(f"Error resolving error {error_id}: {e}")
            return False
    
    def get_error_details(self, error_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific error
        
        Args:
            error_id: Error ID to look up
            
        Returns:
            Error details or None if not found
        """
        try:
            for error in self.error_history:
                if error.id == error_id:
                    return {
                        "id": error.id,
                        "timestamp": error.timestamp.isoformat(),
                        "category": error.category.value,
                        "severity": error.severity.value,
                        "message": error.message,
                        "details": error.details,
                        "stack_trace": error.stack_trace,
                        "user_id": error.user_id,
                        "session_id": error.session_id,
                        "component": error.component,
                        "recovery_action": error.recovery_action.value if error.recovery_action else None,
                        "recovery_attempts": error.recovery_attempts,
                        "resolved": error.resolved,
                        "resolution_notes": error.resolution_notes
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting error details for {error_id}: {e}")
            return None
    
    def _categorize_error(self, error_message: str) -> ErrorCategory:
        """Automatically categorize error based on message"""
        error_message_lower = error_message.lower()
        
        for category, patterns in self.error_patterns.items():
            if any(pattern in error_message_lower for pattern in patterns):
                return category
        
        return ErrorCategory.SYSTEM  # Default category
    
    def _assess_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Automatically assess error severity"""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Critical errors
        if (error_type in ['SystemExit', 'KeyboardInterrupt', 'MemoryError'] or
            'critical' in error_message or
            'fatal' in error_message or
            category == ErrorCategory.DATABASE and 'connection' in error_message):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if (error_type in ['ConnectionError', 'TimeoutError', 'PermissionError'] or
            'failed' in error_message or
            'error' in error_message and category == ErrorCategory.LLM_SERVICE):
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if (error_type in ['ValueError', 'TypeError', 'KeyError'] or
            'warning' in error_message or
            category in [ErrorCategory.VALIDATION, ErrorCategory.FILE_PROCESSING]):
            return ErrorSeverity.MEDIUM
        
        return ErrorSeverity.LOW  # Default severity
    
    def _determine_recovery_action(self, error_record: ErrorRecord) -> Optional[RecoveryAction]:
        """Determine appropriate recovery action for error"""
        category = error_record.category
        severity = error_record.severity
        error_type = error_record.details.get("error_type", "")
        
        # Critical errors require manual intervention
        if severity == ErrorSeverity.CRITICAL:
            return RecoveryAction.MANUAL_INTERVENTION
        
        # Network/service errors can be retried
        if (category in [ErrorCategory.LLM_SERVICE, ErrorCategory.OCR_SERVICE, ErrorCategory.NETWORK] or
            error_type in ['ConnectionError', 'TimeoutError', 'HTTPError']):
            return RecoveryAction.RETRY
        
        # File processing errors might have fallbacks
        if category in [ErrorCategory.FILE_PROCESSING, ErrorCategory.FILE_UPLOAD]:
            return RecoveryAction.FALLBACK
        
        # Validation errors can be skipped
        if category == ErrorCategory.VALIDATION:
            return RecoveryAction.SKIP
        
        return None  # No automatic recovery
    
    def _attempt_recovery(self, error_record: ErrorRecord, recovery_action: RecoveryAction):
        """Attempt automatic error recovery"""
        try:
            error_record.recovery_action = recovery_action
            error_record.recovery_attempts += 1
            
            if recovery_action == RecoveryAction.RETRY:
                # Implement retry logic
                logger.info(f"Attempting retry for error {error_record.id}")
                # TODO: Implement actual retry mechanism
                
            elif recovery_action == RecoveryAction.FALLBACK:
                # Implement fallback logic
                logger.info(f"Attempting fallback for error {error_record.id}")
                # TODO: Implement actual fallback mechanism
                
            elif recovery_action == RecoveryAction.SKIP:
                # Skip the problematic operation
                logger.info(f"Skipping operation for error {error_record.id}")
                error_record.resolved = True
                error_record.resolution_notes = "Operation skipped due to error"
                
            self.recovery_stats[recovery_action] += 1
            
        except Exception as e:
            logger.error(f"Recovery attempt failed for error {error_record.id}: {e}")
    
    def _trigger_critical_alert(self, error_record: ErrorRecord):
        """Trigger alert for critical errors"""
        try:
            alert_message = (
                f"CRITICAL ERROR DETECTED\n"
                f"ID: {error_record.id}\n"
                f"Category: {error_record.category.value}\n"
                f"Component: {error_record.component}\n"
                f"Message: {error_record.message}\n"
                f"User: {error_record.user_id}\n"
                f"Session: {error_record.session_id}\n"
                f"Time: {error_record.timestamp.isoformat()}"
            )
            
            # Log critical alert
            logger.critical(alert_message)
            
            # TODO: Implement additional alerting mechanisms
            # - Email notifications
            # - Slack/Teams notifications
            # - SMS alerts
            # - Webhook notifications
            
        except Exception as e:
            logger.error(f"Failed to trigger critical alert: {e}")
    
    def _write_error_log(self, error_record: ErrorRecord):
        """Write error to log file"""
        try:
            log_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
            
            log_entry = {
                "id": error_record.id,
                "timestamp": error_record.timestamp.isoformat(),
                "category": error_record.category.value,
                "severity": error_record.severity.value,
                "message": error_record.message,
                "details": error_record.details,
                "stack_trace": error_record.stack_trace,
                "user_id": error_record.user_id,
                "session_id": error_record.session_id,
                "component": error_record.component
            }
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to write error log: {e}")
    
    def _monitoring_loop(self, interval: int):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Update system health
                health = self.get_system_health()
                
                # Check for concerning patterns
                if health.error_rate > 10:  # More than 10 errors per hour
                    logger.warning(f"High error rate detected: {health.error_rate} errors/hour")
                
                if health.critical_errors_count > 0:
                    logger.warning(f"Critical errors detected: {health.critical_errors_count}")
                
                # Sleep until next check
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval)
    
    def _get_active_sessions_count(self) -> int:
        """Get count of active training sessions"""
        try:
            # TODO: Query database for active sessions
            return 0
        except Exception:
            return 0
    
    def _get_failed_sessions_count(self) -> int:
        """Get count of failed training sessions"""
        try:
            # TODO: Query database for failed sessions
            return 0
        except Exception:
            return 0
    
    def _get_average_response_time(self) -> float:
        """Get average response time"""
        try:
            # TODO: Calculate actual response time
            return 0.0
        except Exception:
            return 0.0
    
    def _get_memory_usage(self) -> float:
        """Get memory usage percentage"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0
        except Exception:
            return 0.0
    
    def _get_disk_usage(self) -> float:
        """Get disk usage percentage"""
        try:
            import psutil
            return psutil.disk_usage('/').percent
        except ImportError:
            return 0.0
        except Exception:
            return 0.0


# Global instance
error_monitor = ErrorMonitor()