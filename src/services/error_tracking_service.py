"""
Error Tracking Service

This service provides methods to interact with the error tracking database models,
including logging errors, tracking service health, and managing performance metrics.
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_, or_

from src.database.models import (
    db, ProcessingError, ServiceHealth, PerformanceMetrics, SystemAlert, User
)
from src.services.processing_error_handler import ErrorContext, ErrorCategory
from utils.logger import logger

class ErrorTrackingService:
    """Service for managing error tracking and monitoring data"""
    
    def __init__(self):
        self.max_error_history = 10000  # Maximum errors to keep in database
        self.cleanup_interval_hours = 24  # How often to run cleanup
        
    def log_processing_error(self, 
                           error: Exception, 
                           context: ErrorContext,
                           error_response: Dict[str, Any]) -> str:
        """
        Log a processing error to the database
        
        Args:
            error: The exception that occurred
            context: Error context information
            error_response: Response from error handler
            
        Returns:
            Error ID for tracking
        """
        try:
            # Create error record
            error_record = ProcessingError(
                error_id=error_response.get('error_id', f'err_{int(time.time())}'),
                service_name=context.service,
                operation=context.operation,
                error_type=type(error).__name__,
                error_category=error_response.get('category', 'unknown'),
                severity=error_response.get('severity', 'medium'),
                error_message=str(error),
                user_message=error_response.get('user_message', str(error)),
                user_id=context.user_id,
                request_id=context.request_id,
                file_path=context.additional_data.get('file_path') if context.additional_data else None,
                stack_trace=error_response.get('stack_trace'),
                context_data=context.additional_data,
                error_metadata=error_response,
                retry_attempted=error_response.get('should_retry', False),
                fallback_used=error_response.get('fallback_strategy') is not None,
                fallback_strategy=error_response.get('fallback_strategy')
            )
            
            db.session.add(error_record)
            db.session.commit()
            
            logger.debug(f"Logged processing error: {error_record.error_id}")
            return error_record.error_id
            
        except Exception as e:
            logger.error(f"Failed to log processing error: {e}")
            db.session.rollback()
            return None
    
    def log_service_health(self, 
                          service_name: str,
                          status: str,
                          check_type: str = 'periodic',
                          health_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log service health status
        
        Args:
            service_name: Name of the service
            status: Health status (healthy, degraded, unhealthy, unknown)
            check_type: Type of health check
            health_data: Additional health information
            
        Returns:
            Success status
        """
        try:
            if health_data is None:
                health_data = {}
            
            health_record = ServiceHealth(
                service_name=service_name,
                status=status,
                check_type=check_type,
                response_time_ms=health_data.get('response_time_ms'),
                cpu_usage_percent=health_data.get('cpu_usage_percent'),
                memory_usage_percent=health_data.get('memory_usage_percent'),
                disk_usage_percent=health_data.get('disk_usage_percent'),
                active_connections=health_data.get('active_connections'),
                queue_size=health_data.get('queue_size'),
                cache_hit_rate=health_data.get('cache_hit_rate'),
                error_rate=health_data.get('error_rate'),
                throughput_per_second=health_data.get('throughput_per_second'),
                health_details=health_data.get('details'),
                diagnostic_info=health_data.get('diagnostic_info'),
                dependencies_status=health_data.get('dependencies_status'),
                issues=health_data.get('issues', []),
                recommendations=health_data.get('recommendations', []),
                alerts_triggered=health_data.get('alerts_triggered', []),
                check_duration_ms=health_data.get('check_duration_ms'),
                check_error=health_data.get('check_error')
            )
            
            db.session.add(health_record)
            db.session.commit()
            
            logger.debug(f"Logged service health: {service_name} - {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log service health: {e}")
            db.session.rollback()
            return False
    
    def log_performance_metric(self,
                             service_name: str,
                             operation: str,
                             metric_type: str,
                             metric_value: float,
                             success: bool = True,
                             metadata: Optional[Dict[str, Any]] = None,
                             user_id: Optional[str] = None,
                             request_id: Optional[str] = None) -> bool:
        """
        Log a performance metric
        
        Args:
            service_name: Name of the service
            operation: Operation being measured
            metric_type: Type of metric (duration, throughput, etc.)
            metric_value: Metric value
            success: Whether operation was successful
            metadata: Additional metadata
            user_id: User ID if applicable
            request_id: Request ID if applicable
            
        Returns:
            Success status
        """
        try:
            if metadata is None:
                metadata = {}
            
            # Determine metric unit based on type
            metric_unit = self._get_metric_unit(metric_type)
            
            metric_record = PerformanceMetrics(
                service_name=service_name,
                operation=operation,
                metric_type=metric_type,
                metric_value=metric_value,
                metric_unit=metric_unit,
                user_id=user_id,
                request_id=request_id,
                success=success,
                error_message=metadata.get('error_message'),
                cpu_usage_percent=metadata.get('cpu_usage_percent'),
                memory_usage_mb=metadata.get('memory_usage_mb'),
                disk_io_mb=metadata.get('disk_io_mb'),
                network_io_mb=metadata.get('network_io_mb'),
                start_time=metadata.get('start_time'),
                end_time=metadata.get('end_time'),
                duration_ms=metadata.get('duration_ms'),
                metadata=metadata,
                tags=metadata.get('tags'),
                batch_id=metadata.get('batch_id'),
                parent_operation=metadata.get('parent_operation')
            )
            
            db.session.add(metric_record)
            db.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log performance metric: {e}")
            db.session.rollback()
            return False
    
    def create_system_alert(self,
                          alert_type: str,
                          alert_level: str,
                          service_name: str,
                          title: str,
                          message: str,
                          operation: Optional[str] = None,
                          metric_value: Optional[float] = None,
                          threshold_value: Optional[float] = None,
                          alert_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Create a system alert
        
        Args:
            alert_type: Type of alert (performance, error, health, etc.)
            alert_level: Alert level (info, warning, error, critical)
            service_name: Service that triggered the alert
            title: Alert title
            message: Alert message
            operation: Operation that triggered alert
            metric_value: Current metric value
            threshold_value: Threshold that was exceeded
            alert_data: Additional alert data
            
        Returns:
            Alert ID if successful
        """
        try:
            alert_record = SystemAlert(
                alert_type=alert_type,
                alert_level=alert_level,
                service_name=service_name,
                operation=operation,
                title=title,
                message=message,
                metric_value=metric_value,
                threshold_value=threshold_value,
                alert_data=alert_data or {},
                context_data={
                    'created_by': 'system',
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            
            db.session.add(alert_record)
            db.session.commit()
            
            logger.info(f"Created system alert: {alert_level} - {title}")
            return alert_record.id
            
        except Exception as e:
            logger.error(f"Failed to create system alert: {e}")
            db.session.rollback()
            return None
    
    def get_error_statistics(self, 
                           hours: int = 24,
                           service_name: Optional[str] = None) -> Dict[str, Any]:
        """Get error statistics for the specified time period"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            query = ProcessingError.query.filter(ProcessingError.created_at >= since)
            if service_name:
                query = query.filter(ProcessingError.service_name == service_name)
            
            errors = query.all()
            
            # Calculate statistics
            total_errors = len(errors)
            
            # Group by category
            by_category = {}
            by_severity = {}
            by_service = {}
            
            for error in errors:
                by_category[error.error_category] = by_category.get(error.error_category, 0) + 1
                by_severity[error.severity] = by_severity.get(error.severity, 0) + 1
                by_service[error.service_name] = by_service.get(error.service_name, 0) + 1
            
            # Recent errors
            recent_errors = ProcessingError.query.filter(
                ProcessingError.created_at >= since
            ).order_by(desc(ProcessingError.created_at)).limit(10).all()
            
            return {
                'total_errors': total_errors,
                'time_period_hours': hours,
                'by_category': by_category,
                'by_severity': by_severity,
                'by_service': by_service,
                'recent_errors': [error.to_dict() for error in recent_errors],
                'unresolved_count': ProcessingError.query.filter(
                    ProcessingError.resolved == False,
                    ProcessingError.created_at >= since
                ).count()
            }
            
        except Exception as e:
            logger.error(f"Failed to get error statistics: {e}")
            return {}
    
    def get_service_health_history(self,
                                 service_name: str,
                                 hours: int = 24) -> List[Dict[str, Any]]:
        """Get service health history"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            health_records = ServiceHealth.query.filter(
                ServiceHealth.service_name == service_name,
                ServiceHealth.created_at >= since
            ).order_by(ServiceHealth.created_at).all()
            
            return [record.to_dict() for record in health_records]
            
        except Exception as e:
            logger.error(f"Failed to get service health history: {e}")
            return []
    
    def get_performance_summary(self,
                              service_name: Optional[str] = None,
                              hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics summary"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            query = PerformanceMetrics.query.filter(PerformanceMetrics.created_at >= since)
            if service_name:
                query = query.filter(PerformanceMetrics.service_name == service_name)
            
            metrics = query.all()
            
            if not metrics:
                return {}
            
            # Calculate summary statistics
            total_operations = len(metrics)
            successful_operations = sum(1 for m in metrics if m.success)
            
            # Group by operation
            by_operation = {}
            for metric in metrics:
                op = metric.operation
                if op not in by_operation:
                    by_operation[op] = {
                        'count': 0,
                        'success_count': 0,
                        'total_duration': 0,
                        'durations': []
                    }
                
                by_operation[op]['count'] += 1
                if metric.success:
                    by_operation[op]['success_count'] += 1
                
                if metric.metric_type == 'duration' and metric.metric_value:
                    by_operation[op]['total_duration'] += metric.metric_value
                    by_operation[op]['durations'].append(metric.metric_value)
            
            # Calculate averages
            for op_data in by_operation.values():
                if op_data['durations']:
                    op_data['avg_duration'] = sum(op_data['durations']) / len(op_data['durations'])
                    op_data['min_duration'] = min(op_data['durations'])
                    op_data['max_duration'] = max(op_data['durations'])
                else:
                    op_data['avg_duration'] = 0
                    op_data['min_duration'] = 0
                    op_data['max_duration'] = 0
                
                op_data['success_rate'] = op_data['success_count'] / max(1, op_data['count'])
                del op_data['durations']  # Remove raw data
            
            return {
                'total_operations': total_operations,
                'successful_operations': successful_operations,
                'success_rate': successful_operations / max(1, total_operations),
                'time_period_hours': hours,
                'by_operation': by_operation
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {}
    
    def get_active_alerts(self, 
                         alert_level: Optional[str] = None,
                         service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active system alerts"""
        try:
            query = SystemAlert.query.filter(SystemAlert.status == 'active')
            
            if alert_level:
                query = query.filter(SystemAlert.alert_level == alert_level)
            
            if service_name:
                query = query.filter(SystemAlert.service_name == service_name)
            
            alerts = query.order_by(desc(SystemAlert.created_at)).all()
            return [alert.to_dict() for alert in alerts]
            
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
    
    def resolve_error(self, error_id: str, resolution_notes: str, resolved_by: str) -> bool:
        """Mark an error as resolved"""
        try:
            error = ProcessingError.query.filter_by(error_id=error_id).first()
            if not error:
                return False
            
            error.resolved = True
            error.resolution_notes = resolution_notes
            error.resolved_at = datetime.utcnow()
            error.resolved_by = resolved_by
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve error: {e}")
            db.session.rollback()
            return False
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge a system alert"""
        try:
            alert = SystemAlert.query.get(alert_id)
            if not alert:
                return False
            
            alert.status = 'acknowledged'
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            db.session.rollback()
            return False
    
    def cleanup_old_records(self, days_to_keep: int = 30) -> Dict[str, int]:
        """Clean up old records to prevent database bloat"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Count records to be deleted
            old_errors = ProcessingError.query.filter(
                ProcessingError.created_at < cutoff_date,
                ProcessingError.resolved == True
            ).count()
            
            old_health = ServiceHealth.query.filter(
                ServiceHealth.created_at < cutoff_date
            ).count()
            
            old_metrics = PerformanceMetrics.query.filter(
                PerformanceMetrics.created_at < cutoff_date
            ).count()
            
            old_alerts = SystemAlert.query.filter(
                SystemAlert.created_at < cutoff_date,
                SystemAlert.status.in_(['resolved', 'acknowledged'])
            ).count()
            
            # Delete old records
            ProcessingError.query.filter(
                ProcessingError.created_at < cutoff_date,
                ProcessingError.resolved == True
            ).delete()
            
            ServiceHealth.query.filter(
                ServiceHealth.created_at < cutoff_date
            ).delete()
            
            PerformanceMetrics.query.filter(
                PerformanceMetrics.created_at < cutoff_date
            ).delete()
            
            SystemAlert.query.filter(
                SystemAlert.created_at < cutoff_date,
                SystemAlert.status.in_(['resolved', 'acknowledged'])
            ).delete()
            
            db.session.commit()
            
            cleanup_stats = {
                'errors_deleted': old_errors,
                'health_records_deleted': old_health,
                'metrics_deleted': old_metrics,
                'alerts_deleted': old_alerts
            }
            
            logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            db.session.rollback()
            return {}
    
    def _get_metric_unit(self, metric_type: str) -> str:
        """Get appropriate unit for metric type"""
        unit_mapping = {
            'duration': 'ms',
            'throughput': 'ops/sec',
            'error_rate': 'percent',
            'memory_usage': 'mb',
            'cpu_usage': 'percent',
            'disk_usage': 'percent',
            'cache_hit_rate': 'percent',
            'response_time': 'ms',
            'queue_size': 'count',
            'connection_count': 'count'
        }
        
        return unit_mapping.get(metric_type, 'value')

# Global instance
error_tracking_service = ErrorTrackingService()