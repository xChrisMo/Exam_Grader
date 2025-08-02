"""
Service Initialization Status Reporter

This module provides comprehensive reporting and monitoring of service
initialization status, dependency resolution, and system readiness.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import json

from utils.logger import logger

class InitializationPhase(Enum):
    """Phases of service initialization"""
    PENDING = "pending"
    DEPENDENCY_CHECK = "dependency_check"
    INITIALIZING = "initializing"
    HEALTH_CHECK = "health_check"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class ServiceCriticality(Enum):
    """Service criticality levels"""
    CRITICAL = "critical"      # System cannot function without this service
    IMPORTANT = "important"    # System has degraded functionality without this service
    OPTIONAL = "optional"      # System can function normally without this service
    ENHANCEMENT = "enhancement" # Service provides additional features only

@dataclass
class InitializationEvent:
    """Event during service initialization"""
    timestamp: datetime
    service_name: str
    phase: InitializationPhase
    message: str
    success: Optional[bool] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'service_name': self.service_name,
            'phase': self.phase.value,
            'message': self.message,
            'success': self.success,
            'duration_ms': self.duration_ms,
            'error': self.error,
            'metadata': self.metadata
        }

@dataclass
class ServiceInitializationReport:
    """Comprehensive service initialization report"""
    service_name: str
    criticality: ServiceCriticality
    dependencies: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_phase: InitializationPhase = InitializationPhase.PENDING
    success: Optional[bool] = None
    error_message: Optional[str] = None
    events: List[InitializationEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get initialization duration"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Get initialization duration in milliseconds"""
        duration = self.duration
        return duration.total_seconds() * 1000 if duration else None
    
    def add_event(self, phase: InitializationPhase, message: str, 
                  success: Optional[bool] = None, error: Optional[str] = None,
                  metadata: Optional[Dict[str, Any]] = None):
        """Add an initialization event"""
        event = InitializationEvent(
            timestamp=datetime.now(timezone.utc),
            service_name=self.service_name,
            phase=phase,
            message=message,
            success=success,
            error=error,
            metadata=metadata or {}
        )
        
        self.events.append(event)
        self.current_phase = phase
        
        if phase == InitializationPhase.COMPLETED:
            self.success = True
            self.end_time = event.timestamp
        elif phase == InitializationPhase.FAILED:
            self.success = False
            self.error_message = error
            self.end_time = event.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'service_name': self.service_name,
            'criticality': self.criticality.value,
            'dependencies': self.dependencies,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_ms': self.duration_ms,
            'current_phase': self.current_phase.value,
            'success': self.success,
            'error_message': self.error_message,
            'events': [event.to_dict() for event in self.events],
            'metadata': self.metadata
        }

class ServiceInitializationReporter:
    """Reports and monitors service initialization status"""
    
    def __init__(self):
        self.reports: Dict[str, ServiceInitializationReport] = {}
        self.initialization_start_time: Optional[datetime] = None
        self.initialization_end_time: Optional[datetime] = None
        self.status_callbacks: List[Callable[[str, InitializationPhase], None]] = []
        self._lock = threading.RLock()
        
        # System-wide initialization tracking
        self.system_initialization_events: List[InitializationEvent] = []
        self.overall_success: Optional[bool] = None
    
    def register_service(self, service_name: str, criticality: ServiceCriticality,
                        dependencies: List[str] = None, metadata: Dict[str, Any] = None):
        """Register a service for initialization tracking"""
        with self._lock:
            if service_name in self.reports:
                logger.warning(f"Service {service_name} already registered for initialization tracking")
                return
            
            report = ServiceInitializationReport(
                service_name=service_name,
                criticality=criticality,
                dependencies=dependencies or [],
                metadata=metadata or {}
            )
            
            self.reports[service_name] = report
            logger.debug(f"Registered service for initialization tracking: {service_name}")
    
    def start_initialization(self, service_name: str):
        """Mark the start of service initialization"""
        with self._lock:
            if self.initialization_start_time is None:
                self.initialization_start_time = datetime.now(timezone.utc)
                self._add_system_event("System initialization started")
            
            report = self.reports.get(service_name)
            if report:
                report.start_time = datetime.now(timezone.utc)
                report.add_event(
                    InitializationPhase.INITIALIZING,
                    f"Starting initialization of {service_name}"
                )
                
                self._notify_status_change(service_name, InitializationPhase.INITIALIZING)
                logger.info(f"Started initialization tracking for {service_name}")
    
    def report_dependency_check(self, service_name: str, dependencies_met: Dict[str, bool],
                               missing_dependencies: List[str] = None):
        """Report dependency check results"""
        with self._lock:
            report = self.reports.get(service_name)
            if not report:
                return
            
            all_met = all(dependencies_met.values())
            missing = missing_dependencies or [dep for dep, met in dependencies_met.items() if not met]
            
            message = f"Dependency check: {sum(dependencies_met.values())}/{len(dependencies_met)} met"
            if missing:
                message += f" (missing: {', '.join(missing)})"
            
            report.add_event(
                InitializationPhase.DEPENDENCY_CHECK,
                message,
                success=all_met,
                metadata={
                    'dependencies_met': dependencies_met,
                    'missing_dependencies': missing
                }
            )
            
            self._notify_status_change(service_name, InitializationPhase.DEPENDENCY_CHECK)
    
    def report_initialization_progress(self, service_name: str, message: str,
                                     metadata: Dict[str, Any] = None):
        """Report initialization progress"""
        with self._lock:
            report = self.reports.get(service_name)
            if not report:
                return
            
            report.add_event(
                InitializationPhase.INITIALIZING,
                message,
                metadata=metadata
            )
    
    def report_health_check(self, service_name: str, healthy: bool, details: str = None):
        """Report health check results"""
        with self._lock:
            report = self.reports.get(service_name)
            if not report:
                return
            
            message = f"Health check: {'passed' if healthy else 'failed'}"
            if details:
                message += f" - {details}"
            
            report.add_event(
                InitializationPhase.HEALTH_CHECK,
                message,
                success=healthy,
                metadata={'health_details': details}
            )
            
            self._notify_status_change(service_name, InitializationPhase.HEALTH_CHECK)
    
    def report_success(self, service_name: str, message: str = None,
                      metadata: Dict[str, Any] = None):
        """Report successful initialization"""
        with self._lock:
            report = self.reports.get(service_name)
            if not report:
                return
            
            message = message or f"Service {service_name} initialized successfully"
            
            report.add_event(
                InitializationPhase.COMPLETED,
                message,
                success=True,
                metadata=metadata
            )
            
            self._notify_status_change(service_name, InitializationPhase.COMPLETED)
            logger.info(f"Service {service_name} initialization completed successfully")
    
    def report_failure(self, service_name: str, error: str, message: str = None,
                      metadata: Dict[str, Any] = None):
        """Report initialization failure"""
        with self._lock:
            report = self.reports.get(service_name)
            if not report:
                return
            
            message = message or f"Service {service_name} initialization failed"
            
            report.add_event(
                InitializationPhase.FAILED,
                message,
                success=False,
                error=error,
                metadata=metadata
            )
            
            self._notify_status_change(service_name, InitializationPhase.FAILED)
            logger.error(f"Service {service_name} initialization failed: {error}")
    
    def report_skipped(self, service_name: str, reason: str):
        """Report that service initialization was skipped"""
        with self._lock:
            report = self.reports.get(service_name)
            if not report:
                return
            
            report.add_event(
                InitializationPhase.SKIPPED,
                f"Service initialization skipped: {reason}",
                metadata={'skip_reason': reason}
            )
            
            self._notify_status_change(service_name, InitializationPhase.SKIPPED)
            logger.info(f"Service {service_name} initialization skipped: {reason}")
    
    def finalize_initialization(self):
        """Finalize system initialization"""
        with self._lock:
            if self.initialization_end_time is not None:
                return  # Already finalized
            
            self.initialization_end_time = datetime.now(timezone.utc)
            
            # Calculate overall success
            critical_services = [
                report for report in self.reports.values()
                if report.criticality == ServiceCriticality.CRITICAL
            ]
            
            important_services = [
                report for report in self.reports.values()
                if report.criticality == ServiceCriticality.IMPORTANT
            ]
            
            critical_success = all(
                report.success for report in critical_services
            )
            
            important_success_rate = (
                sum(1 for report in important_services if report.success) / 
                max(1, len(important_services))
            )
            
            self.overall_success = critical_success and important_success_rate >= 0.7
            
            duration = self.initialization_end_time - self.initialization_start_time
            
            self._add_system_event(
                f"System initialization {'completed' if self.overall_success else 'failed'} "
                f"in {duration.total_seconds():.3f}s"
            )
            
            logger.info(f"System initialization finalized: success={self.overall_success}")
    
    def add_status_callback(self, callback: Callable[[str, InitializationPhase], None]):
        """Add a callback for status changes"""
        self.status_callbacks.append(callback)
    
    def _notify_status_change(self, service_name: str, phase: InitializationPhase):
        """Notify callbacks of status changes"""
        for callback in self.status_callbacks:
            try:
                callback(service_name, phase)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
    
    def _add_system_event(self, message: str):
        """Add a system-wide initialization event"""
        event = InitializationEvent(
            timestamp=datetime.now(timezone.utc),
            service_name="system",
            phase=InitializationPhase.INITIALIZING,
            message=message
        )
        self.system_initialization_events.append(event)
    
    def get_initialization_summary(self) -> Dict[str, Any]:
        """Get comprehensive initialization summary"""
        with self._lock:
            total_services = len(self.reports)
            successful_services = sum(1 for report in self.reports.values() if report.success)
            failed_services = sum(1 for report in self.reports.values() if report.success is False)
            pending_services = total_services - successful_services - failed_services
            
            # Group by criticality
            by_criticality = {}
            for criticality in ServiceCriticality:
                services = [
                    report for report in self.reports.values()
                    if report.criticality == criticality
                ]
                by_criticality[criticality.value] = {
                    'total': len(services),
                    'successful': sum(1 for s in services if s.success),
                    'failed': sum(1 for s in services if s.success is False),
                    'pending': sum(1 for s in services if s.success is None)
                }
            
            duration = None
            if self.initialization_start_time:
                end_time = self.initialization_end_time or datetime.now(timezone.utc)
                duration = (end_time - self.initialization_start_time).total_seconds()
            
            return {
                'overall_success': self.overall_success,
                'start_time': self.initialization_start_time.isoformat() if self.initialization_start_time else None,
                'end_time': self.initialization_end_time.isoformat() if self.initialization_end_time else None,
                'duration_seconds': duration,
                'total_services': total_services,
                'successful_services': successful_services,
                'failed_services': failed_services,
                'pending_services': pending_services,
                'success_rate': successful_services / max(1, total_services),
                'by_criticality': by_criticality,
                'system_events': [event.to_dict() for event in self.system_initialization_events]
            }
    
    def get_service_report(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed report for a specific service"""
        with self._lock:
            report = self.reports.get(service_name)
            return report.to_dict() if report else None
    
    def get_all_reports(self) -> Dict[str, Dict[str, Any]]:
        """Get all service reports"""
        with self._lock:
            return {
                name: report.to_dict()
                for name, report in self.reports.items()
            }
    
    def export_report(self, filepath: str):
        """Export initialization report to file"""
        report_data = {
            'summary': self.get_initialization_summary(),
            'services': self.get_all_reports(),
            'exported_at': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report_data, f, indent=2)
            logger.info(f"Initialization report exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export initialization report: {e}")
    
    def get_failed_services(self) -> List[Dict[str, Any]]:
        """Get list of services that failed to initialize"""
        with self._lock:
            failed = []
            for report in self.reports.values():
                if report.success is False:
                    failed.append({
                        'service_name': report.service_name,
                        'criticality': report.criticality.value,
                        'error_message': report.error_message,
                        'duration_ms': report.duration_ms
                    })
            return failed
    
    def get_slow_services(self, threshold_ms: float = 5000) -> List[Dict[str, Any]]:
        """Get list of services that took longer than threshold to initialize"""
        with self._lock:
            slow = []
            for report in self.reports.values():
                if report.duration_ms and report.duration_ms > threshold_ms:
                    slow.append({
                        'service_name': report.service_name,
                        'criticality': report.criticality.value,
                        'duration_ms': report.duration_ms,
                        'success': report.success
                    })
            return sorted(slow, key=lambda x: x['duration_ms'], reverse=True)

# Global instance
service_initialization_reporter = ServiceInitializationReporter()