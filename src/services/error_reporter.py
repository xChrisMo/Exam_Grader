"""
Error Reporter - Comprehensive error logging with context information.

This module provides enhanced error logging capabilities with structured logging,
context enrichment, and integration with the processing error handling system.
"""

import json
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

from src.services.processing_error_handler import ErrorContext, ErrorCategory
from src.exceptions.application_errors import ApplicationError, ErrorSeverity
from utils.logger import logger

@dataclass
class ErrorReport:
    """Structured error report."""
    error_id: str
    timestamp: datetime
    error_type: str
    category: str
    severity: str
    message: str
    user_message: str
    operation: str
    service: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    file_path: Optional[str] = None
    stack_trace: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None
    resolution_status: str = "unresolved"
    resolution_notes: Optional[str] = None
    tags: Optional[List[str]] = None

class ErrorReporter:
    """
    Comprehensive error reporter with structured logging and context enrichment.
    """
    
    def __init__(self, log_file_path: Optional[str] = None):
        self.log_file_path = log_file_path or "logs/processing_errors.jsonl"
        self.error_reports: List[ErrorReport] = []
        self.max_reports = 10000  # Maximum number of reports to keep in memory
        
        # Ensure log directory exists
        Path(self.log_file_path).parent.mkdir(parents=True, exist_ok=True)
    
    def report_error(
        self,
        error: ApplicationError,
        context: ErrorContext,
        category: ErrorCategory,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Report an error with comprehensive logging.
        
        Args:
            error: The ApplicationError to report
            context: Error context information
            category: Error category
            additional_context: Additional context data
            
        Returns:
            Error report ID
        """
        try:
            # Create error report
            error_report = ErrorReport(
                error_id=error.error_id,
                timestamp=context.timestamp,
                error_type=type(error).__name__,
                category=category.value,
                severity=error.severity.value,
                message=error.message,
                user_message=error.user_message,
                operation=context.operation,
                service=context.service,
                user_id=context.user_id,
                request_id=context.request_id,
                file_path=context.file_path,
                stack_trace=error.traceback_info,
                context_data=self._merge_context_data(context.additional_data, additional_context),
                tags=self._generate_tags(error, context, category)
            )
            
            # Add to in-memory storage
            self._add_error_report(error_report)
            
            # Log to structured log file
            self._log_to_file(error_report)
            
            # Log to application logger
            self._log_to_application_logger(error_report)
            
            logger.info(f"Error reported with ID: {error.error_id}")
            return error.error_id
            
        except Exception as reporting_error:
            logger.error(f"Failed to report error: {reporting_error}")
            # Fallback logging
            logger.error(f"Original error: {error.message}")
            return "REPORTING_FAILED"
    
    def _merge_context_data(
        self,
        context_data: Optional[Dict[str, Any]],
        additional_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge context data from different sources."""
        merged = {}
        
        if context_data:
            merged.update(context_data)
        
        if additional_context:
            merged.update(additional_context)
        
        return merged
    
    def _generate_tags(
        self,
        error: ApplicationError,
        context: ErrorContext,
        category: ErrorCategory
    ) -> List[str]:
        """Generate tags for error categorization and filtering."""
        tags = []
        
        # Add category tag
        tags.append(f"category:{category.value}")
        
        # Add severity tag
        tags.append(f"severity:{error.severity.value}")
        
        # Add service tag
        tags.append(f"service:{context.service}")
        
        # Add operation tag
        tags.append(f"operation:{context.operation}")
        
        # Add error type tag
        tags.append(f"type:{type(error).__name__}")
        
        # Add time-based tags
        now = datetime.utcnow()
        tags.append(f"hour:{now.hour}")
        tags.append(f"day:{now.strftime('%A').lower()}")
        
        if context.user_id:
            tags.append(f"user:{context.user_id}")
        
        if context.file_path:
            file_ext = Path(context.file_path).suffix.lower()
            if file_ext:
                tags.append(f"file_type:{file_ext}")
        
        # Add error-specific tags based on message content
        message_lower = error.message.lower()
        if 'timeout' in message_lower:
            tags.append('timeout')
        if 'connection' in message_lower:
            tags.append('connection')
        if 'memory' in message_lower:
            tags.append('memory')
        if 'disk' in message_lower:
            tags.append('disk')
        if 'permission' in message_lower:
            tags.append('permission')
        
        return tags
    
    def _add_error_report(self, error_report: ErrorReport):
        """Add error report to in-memory storage."""
        self.error_reports.append(error_report)
        
        # Maintain size limit
        if len(self.error_reports) > self.max_reports:
            self.error_reports = self.error_reports[-self.max_reports:]
    
    def _log_to_file(self, error_report: ErrorReport):
        """Log error report to structured JSON file."""
        try:
            # Convert to dictionary and handle datetime serialization
            report_dict = asdict(error_report)
            report_dict['timestamp'] = error_report.timestamp.isoformat()
            
            # Write to JSONL file
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(report_dict) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to write error report to file: {e}")
    
    def _log_to_application_logger(self, error_report: ErrorReport):
        """Log error report to application logger with appropriate level."""
        
        # Create structured log message
        log_data = {
            'error_id': error_report.error_id,
            'error_type': error_report.error_type,
            'category': error_report.category,
            'operation': error_report.operation,
            'service': error_report.service,
            'user_id': error_report.user_id,
            'request_id': error_report.request_id,
            'message': error_report.message,
            'tags': error_report.tags
        }
        
        log_message = f"Processing Error Report: {json.dumps(log_data)}"
        
        # Log with appropriate level based on severity
        if error_report.severity == ErrorSeverity.CRITICAL.value:
            logger.critical(log_message)
        elif error_report.severity == ErrorSeverity.HIGH.value:
            logger.error(log_message)
        elif error_report.severity == ErrorSeverity.MEDIUM.value:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def get_error_reports(
        self,
        limit: int = 100,
        severity_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        service_filter: Optional[str] = None,
        operation_filter: Optional[str] = None,
        user_id_filter: Optional[str] = None,
        resolved_only: bool = False,
        unresolved_only: bool = False
    ) -> List[ErrorReport]:
        """
        Get error reports with optional filtering.
        
        Args:
            limit: Maximum number of reports to return
            severity_filter: Filter by severity level
            category_filter: Filter by error category
            service_filter: Filter by service name
            operation_filter: Filter by operation name
            user_id_filter: Filter by user ID
            resolved_only: Return only resolved errors
            unresolved_only: Return only unresolved errors
            
        Returns:
            List of filtered error reports
        """
        filtered_reports = []
        
        for report in reversed(self.error_reports):  # Most recent first
            # Apply filters
            if severity_filter and report.severity != severity_filter:
                continue
            if category_filter and report.category != category_filter:
                continue
            if service_filter and report.service != service_filter:
                continue
            if operation_filter and report.operation != operation_filter:
                continue
            if user_id_filter and report.user_id != user_id_filter:
                continue
            if resolved_only and report.resolution_status != "resolved":
                continue
            if unresolved_only and report.resolution_status == "resolved":
                continue
            
            filtered_reports.append(report)
            
            if len(filtered_reports) >= limit:
                break
        
        return filtered_reports
    
    def get_error_report_by_id(self, error_id: str) -> Optional[ErrorReport]:
        """Get error report by ID."""
        for report in self.error_reports:
            if report.error_id == error_id:
                return report
        return None
    
    def resolve_error(
        self,
        error_id: str,
        resolution_notes: str,
        resolved_by: Optional[str] = None
    ) -> bool:
        """
        Mark an error as resolved.
        
        Args:
            error_id: Error ID to resolve
            resolution_notes: Notes about the resolution
            resolved_by: User who resolved the error
            
        Returns:
            True if error was found and resolved, False otherwise
        """
        for report in self.error_reports:
            if report.error_id == error_id:
                report.resolution_status = "resolved"
                report.resolution_notes = resolution_notes
                
                if resolved_by:
                    if not report.context_data:
                        report.context_data = {}
                    report.context_data['resolved_by'] = resolved_by
                    report.context_data['resolved_at'] = datetime.utcnow().isoformat()
                
                logger.info(f"Error {error_id} marked as resolved by {resolved_by}")
                return True
        
        logger.warning(f"Error {error_id} not found for resolution")
        return False
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        if not self.error_reports:
            return {
                'total_errors': 0,
                'by_severity': {},
                'by_category': {},
                'by_service': {},
                'by_operation': {},
                'resolution_status': {},
                'recent_errors': []
            }
        
        # Count by severity
        by_severity = {}
        for report in self.error_reports:
            by_severity[report.severity] = by_severity.get(report.severity, 0) + 1
        
        # Count by category
        by_category = {}
        for report in self.error_reports:
            by_category[report.category] = by_category.get(report.category, 0) + 1
        
        # Count by service
        by_service = {}
        for report in self.error_reports:
            by_service[report.service] = by_service.get(report.service, 0) + 1
        
        # Count by operation
        by_operation = {}
        for report in self.error_reports:
            by_operation[report.operation] = by_operation.get(report.operation, 0) + 1
        
        # Count by resolution status
        by_resolution = {}
        for report in self.error_reports:
            by_resolution[report.resolution_status] = by_resolution.get(report.resolution_status, 0) + 1
        
        # Get recent errors (last 10)
        recent_errors = []
        for report in reversed(self.error_reports[-10:]):
            recent_errors.append({
                'error_id': report.error_id,
                'timestamp': report.timestamp.isoformat(),
                'severity': report.severity,
                'category': report.category,
                'service': report.service,
                'operation': report.operation,
                'message': report.message[:100] + '...' if len(report.message) > 100 else report.message,
                'resolution_status': report.resolution_status
            })
        
        return {
            'total_errors': len(self.error_reports),
            'by_severity': by_severity,
            'by_category': by_category,
            'by_service': by_service,
            'by_operation': by_operation,
            'resolution_status': by_resolution,
            'recent_errors': recent_errors
        }
    
    def export_error_reports(
        self,
        output_file: str,
        format: str = 'json',
        filters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Export error reports to file.
        
        Args:
            output_file: Output file path
            format: Export format ('json' or 'csv')
            filters: Optional filters to apply
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            if filters:
                reports = self.get_error_reports(**filters)
            else:
                reports = self.error_reports
            
            if format.lower() == 'json':
                self._export_to_json(reports, output_file)
            elif format.lower() == 'csv':
                self._export_to_csv(reports, output_file)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
            
            logger.info(f"Exported {len(reports)} error reports to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export error reports: {e}")
            return False
    
    def _export_to_json(self, reports: List[ErrorReport], output_file: str):
        """Export reports to JSON format."""
        reports_data = []
        for report in reports:
            report_dict = asdict(report)
            report_dict['timestamp'] = report.timestamp.isoformat()
            reports_data.append(report_dict)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(reports_data, f, indent=2, ensure_ascii=False)
    
    def _export_to_csv(self, reports: List[ErrorReport], output_file: str):
        """Export reports to CSV format."""
        import csv
        
        if not reports:
            return
        
        fieldnames = [
            'error_id', 'timestamp', 'error_type', 'category', 'severity',
            'message', 'operation', 'service', 'user_id', 'request_id',
            'resolution_status', 'resolution_notes'
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for report in reports:
                row = {
                    'error_id': report.error_id,
                    'timestamp': report.timestamp.isoformat(),
                    'error_type': report.error_type,
                    'category': report.category,
                    'severity': report.severity,
                    'message': report.message,
                    'operation': report.operation,
                    'service': report.service,
                    'user_id': report.user_id or '',
                    'request_id': report.request_id or '',
                    'resolution_status': report.resolution_status,
                    'resolution_notes': report.resolution_notes or ''
                }
                writer.writerow(row)
    
    def clear_resolved_errors(self) -> int:
        """Clear resolved errors from memory."""
        initial_count = len(self.error_reports)
        self.error_reports = [r for r in self.error_reports if r.resolution_status != "resolved"]
        cleared_count = initial_count - len(self.error_reports)
        
        logger.info(f"Cleared {cleared_count} resolved error reports")
        return cleared_count
    
    def clear_old_errors(self, days: int = 30) -> int:
        """Clear errors older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        initial_count = len(self.error_reports)
        
        self.error_reports = [r for r in self.error_reports if r.timestamp > cutoff_date]
        cleared_count = initial_count - len(self.error_reports)
        
        logger.info(f"Cleared {cleared_count} error reports older than {days} days")
        return cleared_count

# Global instance
error_reporter = ErrorReporter()