"""Database models for progress tracking persistence."""
from typing import Any, Dict, Optional

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

try:
    from .models import db, TimestampMixin, get_uuid_column
    DB_AVAILABLE = db is not None
except ImportError:
    try:
        from src.database.models import db, TimestampMixin, get_uuid_column
        DB_AVAILABLE = db is not None
    except ImportError:
        # Fallback when models are not available
        db = None
        TimestampMixin = object
        get_uuid_column = lambda: Column(String(36), primary_key=True)
        DB_AVAILABLE = False

if DB_AVAILABLE and db is not None:
    BaseModel = db.Model
else:
    BaseModel = object

class ProgressSession(BaseModel, TimestampMixin):
    """Model for tracking progress sessions with persistence."""
    
    __tablename__ = "progress_sessions"
    
    id = get_uuid_column()
    session_id = Column(String(36), nullable=False, unique=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    total_steps = Column(Integer, nullable=False)
    total_submissions = Column(Integer, nullable=False, default=1)
    current_step = Column(Integer, default=0)
    current_submission = Column(Integer, default=0)
    status = Column(String(50), default="active", nullable=False)  # active, completed, failed, cancelled
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    estimated_duration = Column(Float, nullable=True)  # in seconds
    session_type = Column(String(50), nullable=True)  # ocr, grading, mapping, etc.
    session_metadata = Column(JSON, nullable=True)  # Additional session data
    
    # Relationships
    user = relationship("User", backref="progress_sessions")
    progress_updates = relationship(
        "ProgressUpdate", 
        back_populates="session", 
        cascade="all, delete-orphan",
        order_by="ProgressUpdate.created_at"
    )
    
    __table_args__ = (
        Index('idx_session_user_status', 'session_id', 'user_id', 'status'),
        Index('idx_session_type_status', 'session_type', 'status'),
        Index('idx_session_start_time', 'start_time'),
        Index('idx_session_status_end_time', 'status', 'end_time'),
    )
    
    def calculate_progress_percentage(self) -> float:
        """Calculate overall progress percentage."""
        if self.total_steps == 0:
            return 0.0
        
        # Calculate based on submissions and steps
        submission_progress = (self.current_submission / self.total_submissions) * 100
        step_progress = (self.current_step / self.total_steps) * (100 / self.total_submissions)
        
        return min(submission_progress + step_progress, 100.0)
    
    def calculate_estimated_remaining(self) -> Optional[float]:
        """Calculate estimated time remaining in seconds."""
        if not self.start_time or self.status != "active":
            return None
        
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        progress_percentage = self.calculate_progress_percentage()
        
        if progress_percentage <= 0:
            return self.estimated_duration
        
        total_estimated = elapsed / (progress_percentage / 100)
        return max(0, total_estimated - elapsed)
    
    def is_active(self) -> bool:
        """Check if session is active."""
        return self.status == "active"
    
    def is_completed(self) -> bool:
        """Check if session is completed."""
        return self.status in ["completed", "failed", "cancelled"]
    
    def complete(self, status: str = "completed", end_time: Optional[datetime] = None):
        """Mark session as completed."""
        self.status = status
        self.end_time = end_time or datetime.now(timezone.utc)
        self.current_step = self.total_steps
        self.current_submission = self.total_submissions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "total_steps": self.total_steps,
            "total_submissions": self.total_submissions,
            "current_step": self.current_step,
            "current_submission": self.current_submission,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "estimated_duration": self.estimated_duration,
            "session_type": self.session_type,
            "metadata": self.metadata,
            "progress_percentage": self.calculate_progress_percentage(),
            "estimated_remaining": self.calculate_estimated_remaining(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class ProgressUpdate(BaseModel, TimestampMixin):
    """Model for individual progress updates with persistence."""
    
    __tablename__ = "progress_updates"
    
    id = get_uuid_column()
    session_id = Column(String(36), ForeignKey("progress_sessions.session_id"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    operation = Column(String(200), nullable=False)
    submission_index = Column(Integer, default=0)
    percentage = Column(Float, nullable=False)
    estimated_time_remaining = Column(Float, nullable=True)  # in seconds
    status = Column(String(50), default="processing", nullable=False)
    details = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    metrics = Column(JSON, nullable=True)  # Performance metrics, timing data, etc.
    
    # Relationships
    session = relationship("ProgressSession", back_populates="progress_updates")
    
    __table_args__ = (
        Index('idx_update_session_step', 'session_id', 'step_number'),
        Index('idx_update_session_created', 'session_id', 'created_at'),
        Index('idx_update_status_created', 'status', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "step_number": self.step_number,
            "operation": self.operation,
            "submission_index": self.submission_index,
            "percentage": self.percentage,
            "estimated_time_remaining": self.estimated_time_remaining,
            "status": self.status,
            "details": self.details,
            "error_message": self.error_message,
            "metrics": self.metrics,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class ProgressRecovery(BaseModel, TimestampMixin):
    """Model for tracking progress recovery operations."""
    
    __tablename__ = "progress_recovery"
    
    id = get_uuid_column()
    session_id = Column(String(36), nullable=False, index=True)
    recovery_type = Column(String(50), nullable=False)  # restart, resume, rollback
    recovery_point = Column(Integer, nullable=False)  # Step to recover from
    recovery_data = Column(JSON, nullable=True)  # Data needed for recovery
    recovery_status = Column(String(50), default="pending", nullable=False)  # pending, completed, failed
    recovery_message = Column(Text, nullable=True)
    recovered_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_recovery_session_type', 'session_id', 'recovery_type'),
        Index('idx_recovery_status_created', 'recovery_status', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "recovery_type": self.recovery_type,
            "recovery_point": self.recovery_point,
            "recovery_data": self.recovery_data,
            "recovery_status": self.recovery_status,
            "recovery_message": self.recovery_message,
            "recovered_at": self.recovered_at.isoformat() if self.recovered_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class ProgressMetrics(BaseModel, TimestampMixin):
    """Model for storing progress performance metrics."""
    
    __tablename__ = "progress_metrics"
    
    id = get_uuid_column()
    session_id = Column(String(36), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False)  # throughput, latency, error_rate, etc.
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20), nullable=True)  # seconds, requests/sec, percentage, etc.
    measurement_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    context_data = Column(JSON, nullable=True)  # Additional context for the metric
    
    __table_args__ = (
        Index('idx_metrics_session_type', 'session_id', 'metric_type'),
        Index('idx_metrics_type_time', 'metric_type', 'measurement_time'),
        Index('idx_metrics_session_time', 'session_id', 'measurement_time'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "metric_type": self.metric_type,
            "metric_value": self.metric_value,
            "metric_unit": self.metric_unit,
            "measurement_time": self.measurement_time.isoformat(),
            "context_data": self.context_data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }