"""
Database models for the Exam Grader application.

This module defines SQLAlchemy models for persistent data storage,
replacing the session-based storage system.
"""
import uuid

# Fix datetime import for models
from datetime import datetime, timedelta, timezone, timezone as datetime_class
from typing import Any, Dict

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

# Initialize SQLAlchemy
db = SQLAlchemy()

def get_uuid_column():
    """Get appropriate UUID column type based on database."""
    return Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

class TimestampMixin:
    """Mixin for adding timestamp fields to models."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

class User(UserMixin, db.Model, TimestampMixin):
    """User model for authentication and session management."""

    __tablename__ = "users"

    id = get_uuid_column()
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)

    # Relationships
    marking_guides = relationship(
        "MarkingGuide", back_populates="user", cascade="all, delete-orphan"
    )
    submissions = relationship(
        "Submission", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: str):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check password against hash with timing optimization."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def is_locked(self) -> bool:
        """Check if account is locked."""
        return self.locked_until and self.locked_until > datetime.now(timezone.utc)

    def is_account_locked(self) -> bool:
        """Check if account is locked (alias for is_locked for compatibility)."""
        return self.is_locked()

    def lock_account(self, duration_minutes: int = 30):
        """Lock account for specified duration."""
        self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        self.failed_login_attempts = 0

    def unlock_account(self):
        """Unlock account."""
        self.locked_until = None
        self.failed_login_attempts = 0

    # Flask-Login required methods
    def get_id(self):
        """Return the user ID as a string for Flask-Login."""
        return str(self.id)

    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return True

    def is_anonymous(self):
        """Return False as this is not an anonymous user."""
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "processed": self.processing_status == "completed",
        }

class MarkingGuide(db.Model, TimestampMixin):
    """Marking guide model for storing grading criteria."""
    
    __tablename__ = "marking_guides"
    __table_args__ = (
        Index('idx_guide_user_title', 'user_id', 'title'),
        Index('idx_guide_created', 'created_at'),
    )
    
    id = get_uuid_column()
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    content_text = Column(Text)
    content_hash = Column(String(64), index=True)  # SHA256 hash for duplicate detection
    questions = Column(JSON)  # Structured question data
    total_marks = Column(Float, default=0.0)
    max_questions_to_answer = Column(Integer, default=None)  # Form-configured limit for AI processing
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="marking_guides")
    submissions = relationship("Submission", back_populates="marking_guide")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "filename": self.filename,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "total_marks": self.total_marks,
            "is_active": self.is_active,
            "questions": self.questions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class Submission(db.Model, TimestampMixin):
    """Student submission model."""

    __tablename__ = "submissions"

    id = get_uuid_column()
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    marking_guide_id = Column(
        String(36), ForeignKey("marking_guides.id"), nullable=True, index=True
    )
    student_name = Column(String(200))
    student_id = Column(String(100))
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    content_text = Column(Text)
    content_hash = Column(String(64), index=True)  # SHA256 hash for duplicate detection
    answers = Column(JSON)  # Extracted answers
    ocr_confidence = Column(Float)
    processing_status = Column(
        String(50), default="pending"
    )  # pending, processing, completed, failed
    processing_error = Column(Text)
    archived = Column(Boolean, default=False, nullable=False)  # Add archived field with default value
    processed = Column(Boolean, default=False, nullable=False)  # Track if processing is complete

    # Relationships
    user = relationship("User", back_populates="submissions")
    marking_guide = relationship("MarkingGuide", back_populates="submissions")
    mappings = relationship(
        "Mapping", back_populates="submission", cascade="all, delete-orphan"
    )
    grading_results = relationship(
        "GradingResult", back_populates="submission", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.Index('idx_submission_user_status', 'user_id', 'processing_status'),
        db.Index('idx_user_created', 'user_id', 'created_at'),
        db.Index('idx_status_created', 'processing_status', 'created_at'),
        db.Index('idx_guide_status', 'marking_guide_id', 'processing_status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "marking_guide_id": self.marking_guide_id,
            "student_name": self.student_name,
            "student_id": self.student_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "content_text": self.content_text,
            "answers": self.answers,
            "ocr_confidence": self.ocr_confidence,
            "processing_status": self.processing_status,
            "processing_error": self.processing_error,
            "archived": self.archived,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class Mapping(db.Model, TimestampMixin):
    """Answer mapping model for linking submission answers to guide questions."""

    __tablename__ = "mappings"

    id = get_uuid_column()
    submission_id = Column(
        String(36), ForeignKey("submissions.id"), nullable=False, index=True
    )
    guide_question_id = Column(String(100), nullable=False)
    guide_question_text = Column(Text, nullable=False)
    guide_answer = Column(Text)
    max_score = Column(Float, nullable=False)
    submission_answer = Column(Text, nullable=False)
    match_score = Column(Float, default=0.0)
    match_reason = Column(Text)
    mapping_method = Column(String(50), default="llm")  # llm, similarity, manual

    # Relationships
    submission = relationship("Submission", back_populates="mappings")
    grading_results = relationship(
        "GradingResult", back_populates="mapping", cascade="all, delete-orphan"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "submission_id": self.submission_id,
            "guide_question_id": self.guide_question_id,
            "guide_question_text": self.guide_question_text,
            "guide_answer": self.guide_answer,
            "max_score": self.max_score,
            "submission_answer": self.submission_answer,
            "match_score": self.match_score,
            "match_reason": self.match_reason,
            "mapping_method": self.mapping_method,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class GradingResult(db.Model, TimestampMixin):
    """Stores the result of a single grading operation."""

    __tablename__ = "grading_results"

    id = get_uuid_column()
    submission_id = Column(String(36), ForeignKey("submissions.id"), nullable=False)
    marking_guide_id = Column(String(36), ForeignKey("marking_guides.id"), nullable=True)
    mapping_id = Column(String(36), ForeignKey("mappings.id"), nullable=True)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    percentage = Column(Float, nullable=False)
    feedback = Column(Text)
    detailed_feedback = Column(JSON)
    progress_id = Column(String(36), nullable=True, index=True)
    grading_session_id = Column(String(36), ForeignKey("grading_sessions.id"), nullable=True, index=True)
    grading_method = Column(String(50), default="llm")  # llm, similarity, manual
    confidence = Column(Float)
    
    # Add total_score as an alias property for backward compatibility
    @property
    def total_score(self):
        """Alias for score field to maintain compatibility."""
        return self.score
    
    @total_score.setter
    def total_score(self, value):
        """Setter for total_score alias."""
        self.score = value

    # Relationship to GradingSession
    grading_session = relationship("GradingSession", backref="grading_results")

    # Relationships
    submission = relationship("Submission", back_populates="grading_results")
    marking_guide = relationship("MarkingGuide", backref="grading_results")
    mapping = relationship("Mapping", back_populates="grading_results")

    __table_args__ = (
        db.Index('idx_submission_mapping', 'submission_id', 'mapping_id'),
        db.Index('idx_submission_score', 'submission_id', 'score'),
        db.Index('idx_method_created', 'grading_method', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "submission_id": self.submission_id,
            "mapping_id": self.mapping_id,
            "score": self.score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "feedback": self.feedback,
            "detailed_feedback": self.detailed_feedback,
            "grading_method": self.grading_method,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "graded_at": self.created_at.isoformat() if self.created_at else None,  # For template compatibility
        }

class Session(db.Model, TimestampMixin):
    """Session model for secure session management."""

    __tablename__ = "sessions"

    id = Column(String(255), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    data = Column(LargeBinary)  # Encrypted session data
    salt = Column(String(255), nullable=True, default='')  # Salt for session data encryption
    expires_at = Column(DateTime, nullable=False, index=True)
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def extend_session(self, duration_seconds: int = 3600):
        """Extend session expiration."""
        self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
        self.updated_at = datetime.now(timezone.utc)

    def invalidate(self):
        """Invalidate session."""
        self.is_active = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "expires_at": self.expires_at.isoformat(),
            "ip_address": self.ip_address,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "salt": self.salt,
        }

class GradingSession(db.Model, TimestampMixin):
    """Tracks the overall AI processing session status by submission_id + guide_id."""

    __tablename__ = "grading_sessions"

    id = get_uuid_column()
    submission_id = Column(String(36), ForeignKey("submissions.id"), nullable=False, index=True)
    marking_guide_id = Column(String(36), ForeignKey("marking_guides.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    progress_id = Column(String(36), nullable=True, index=True)  # For real-time tracking
    status = Column(String(50), default="not_started", nullable=False)  # not_started, in_progress, completed, failed
    current_step = Column(String(50), nullable=True)  # text_retrieval, mapping, grading, saving
    total_questions_mapped = Column(Integer, default=0)
    total_questions_graded = Column(Integer, default=0)
    max_questions_limit = Column(Integer, nullable=True)  # Copied from marking guide for this session
    processing_start_time = Column(DateTime, nullable=True)
    processing_end_time = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    session_data = Column(JSON, nullable=True)  # Additional session metadata

    # Relationships
    submission = relationship("Submission", backref="grading_sessions")
    marking_guide = relationship("MarkingGuide", backref="grading_sessions")
    user = relationship("User", backref="grading_sessions")

    __table_args__ = (
        db.Index('idx_submission_guide', 'submission_id', 'marking_guide_id'),
        db.Index('idx_grading_session_user_status', 'user_id', 'status'),
        db.Index('idx_progress_status', 'progress_id', 'status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "submission_id": self.submission_id,
            "marking_guide_id": self.marking_guide_id,
            "user_id": self.user_id,
            "progress_id": self.progress_id,
            "status": self.status,
            "current_step": self.current_step,
            "total_questions_mapped": self.total_questions_mapped,
            "total_questions_graded": self.total_questions_graded,
            "max_questions_limit": self.max_questions_limit,
            "processing_start_time": self.processing_start_time.isoformat() if self.processing_start_time else None,
            "processing_end_time": self.processing_end_time.isoformat() if self.processing_end_time else None,
            "error_message": self.error_message,
            "session_data": self.session_data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }









class ProcessingMetrics(db.Model, TimestampMixin):
    """Performance metrics for monitoring service operations."""
    
    __tablename__ = "processing_metrics"
    __table_args__ = (
        Index('idx_service_operation', 'service_name', 'operation'),
        Index('idx_created_success', 'created_at', 'success'),
        Index('idx_duration', 'duration_ms'),
    )
    
    id = get_uuid_column()
    service_name = Column(String(100), nullable=False)
    operation = Column(String(100), nullable=False)
    duration_ms = Column(Integer, nullable=False)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    processing_metadata = Column(JSON)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "service_name": self.service_name,
            "operation": self.operation,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class ProcessingError(db.Model, TimestampMixin):
    """Model for tracking processing errors with detailed context and categorization."""
    
    __tablename__ = "processing_errors"
    __table_args__ = (
        Index('idx_error_service_operation', 'service_name', 'operation'),
        Index('idx_error_category_severity', 'error_category', 'severity'),
        Index('idx_error_created', 'created_at'),
        Index('idx_error_user', 'user_id'),
        Index('idx_error_request', 'request_id'),
    )
    
    id = get_uuid_column()
    error_id = Column(String(100), nullable=False, unique=True, index=True)  # Unique error identifier
    service_name = Column(String(100), nullable=False)
    operation = Column(String(100), nullable=False)
    error_type = Column(String(100), nullable=False)  # Exception class name
    error_category = Column(String(50), nullable=False)  # transient, permanent, configuration, etc.
    severity = Column(String(20), nullable=False)  # critical, high, medium, low
    error_message = Column(Text, nullable=False)
    user_message = Column(Text)  # User-friendly error message
    
    # Context information
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    request_id = Column(String(100), nullable=True, index=True)
    file_path = Column(String(500), nullable=True)
    
    # Error details and metadata
    stack_trace = Column(Text)
    context_data = Column(JSON)  # Additional context information
    error_metadata = Column(JSON)  # Error handler response data
    
    # Resolution tracking
    resolved = Column(Boolean, default=False, nullable=False)
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime)
    resolved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Retry and fallback information
    retry_attempted = Column(Boolean, default=False)
    retry_count = Column(Integer, default=0)
    fallback_used = Column(Boolean, default=False)
    fallback_strategy = Column(String(50))
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="processing_errors")
    resolver = relationship("User", foreign_keys=[resolved_by], backref="resolved_errors")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "error_id": self.error_id,
            "service_name": self.service_name,
            "operation": self.operation,
            "error_type": self.error_type,
            "error_category": self.error_category,
            "severity": self.severity,
            "error_message": self.error_message,
            "user_message": self.user_message,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "file_path": self.file_path,
            "stack_trace": self.stack_trace,
            "context_data": self.context_data,
            "error_metadata": self.error_metadata,
            "resolved": self.resolved,
            "resolution_notes": self.resolution_notes,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "retry_attempted": self.retry_attempted,
            "retry_count": self.retry_count,
            "fallback_used": self.fallback_used,
            "fallback_strategy": self.fallback_strategy,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class ServiceHealth(db.Model, TimestampMixin):
    """Model for tracking service health status and diagnostics."""
    
    __tablename__ = "service_health"
    __table_args__ = (
        Index('idx_service_status', 'service_name', 'status'),
        Index('idx_health_created', 'created_at'),
        Index('idx_health_check_type', 'check_type'),
    )
    
    id = get_uuid_column()
    service_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # healthy, degraded, unhealthy, unknown
    check_type = Column(String(50), nullable=False)  # startup, periodic, manual, api_request
    response_time_ms = Column(Integer)
    
    # Health metrics
    cpu_usage_percent = Column(Float)
    memory_usage_percent = Column(Float)
    disk_usage_percent = Column(Float)
    active_connections = Column(Integer)
    queue_size = Column(Integer)
    
    # Service-specific metrics
    cache_hit_rate = Column(Float)
    error_rate = Column(Float)
    throughput_per_second = Column(Float)
    
    # Detailed health information
    health_details = Column(JSON)  # Detailed health check results
    diagnostic_info = Column(JSON)  # Diagnostic information
    dependencies_status = Column(JSON)  # Status of service dependencies
    
    # Issues and recommendations
    issues = Column(JSON)  # List of identified issues
    recommendations = Column(JSON)  # List of recommendations
    alerts_triggered = Column(JSON)  # List of alerts triggered
    
    # Check metadata
    check_duration_ms = Column(Integer)
    check_error = Column(Text)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "service_name": self.service_name,
            "status": self.status,
            "check_type": self.check_type,
            "response_time_ms": self.response_time_ms,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_percent": self.memory_usage_percent,
            "disk_usage_percent": self.disk_usage_percent,
            "active_connections": self.active_connections,
            "queue_size": self.queue_size,
            "cache_hit_rate": self.cache_hit_rate,
            "error_rate": self.error_rate,
            "throughput_per_second": self.throughput_per_second,
            "health_details": self.health_details,
            "diagnostic_info": self.diagnostic_info,
            "dependencies_status": self.dependencies_status,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "alerts_triggered": self.alerts_triggered,
            "check_duration_ms": self.check_duration_ms,
            "check_error": self.check_error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class PerformanceMetrics(db.Model, TimestampMixin):
    """Enhanced performance metrics model for detailed monitoring and analysis."""
    
    __tablename__ = "performance_metrics"
    __table_args__ = (
        Index('idx_perf_service_operation', 'service_name', 'operation'),
        Index('idx_perf_metric_type', 'metric_type'),
        Index('idx_perf_created', 'created_at'),
        Index('idx_perf_user', 'user_id'),
    )
    
    id = get_uuid_column()
    service_name = Column(String(100), nullable=False)
    operation = Column(String(100), nullable=False)
    metric_type = Column(String(50), nullable=False)  # duration, throughput, error_rate, memory_usage, etc.
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20))  # ms, seconds, bytes, percent, count, etc.
    
    # Request context
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    request_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(100), nullable=True)
    
    # Performance context
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    
    # Detailed metrics
    cpu_usage_percent = Column(Float)
    memory_usage_mb = Column(Float)
    disk_io_mb = Column(Float)
    network_io_mb = Column(Float)
    
    # Timing information
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_ms = Column(Integer)
    
    # Additional metadata
    performance_metadata = Column(JSON)  # Additional performance data
    tags = Column(JSON)  # Tags for categorization and filtering
    
    # Aggregation helpers
    batch_id = Column(String(100), nullable=True, index=True)  # For batch operations
    parent_operation = Column(String(100), nullable=True)  # For nested operations
    
    # Relationships
    user = relationship("User", backref="performance_metrics")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "service_name": self.service_name,
            "operation": self.operation,
            "metric_type": self.metric_type,
            "metric_value": self.metric_value,
            "metric_unit": self.metric_unit,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "success": self.success,
            "error_message": self.error_message,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_mb": self.memory_usage_mb,
            "disk_io_mb": self.disk_io_mb,
            "network_io_mb": self.network_io_mb,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "tags": self.tags,
            "batch_id": self.batch_id,
            "parent_operation": self.parent_operation,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class SystemAlert(db.Model, TimestampMixin):
    """Model for system alerts and notifications."""
    
    __tablename__ = 'system_alert'
    
    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(50), nullable=False)  # 'error', 'warning', 'info'
    severity = db.Column(db.String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(100))  # Source component/service
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime)
    resolved_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    def __repr__(self):
        return f'<SystemAlert {self.id}: {self.title}>'

# Training models are defined later in the file


class SystemAlertsV2(db.Model, TimestampMixin):
    """Model for system alerts and notifications (v2)."""
    
    __tablename__ = "system_alerts_v2"
    __table_args__ = (
        Index('idx_alert_v2_level_status', 'alert_level', 'status'),
        Index('idx_alert_v2_service', 'service_name'),
        Index('idx_alert_v2_created', 'created_at'),
        Index('idx_alert_v2_resolved', 'resolved_at'),
    )
    
    id = get_uuid_column()
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    alert_type = Column(String(50), nullable=False)  # performance, error, health, resource, security
    alert_level = Column(String(20), nullable=False)  # info, warning, error, critical
    service_name = Column(String(100), nullable=False)
    operation = Column(String(100))
    
    # Alert details
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    description = Column(Text)
    
    # Alert data
    metric_value = Column(Float)
    threshold_value = Column(Float)
    condition = Column(String(50))  # greater_than, less_than, equals, contains
    
    # Status tracking
    status = Column(String(20), default='active', nullable=False)  # active, acknowledged, resolved, suppressed
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime)
    resolved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Resolution information
    resolution_notes = Column(Text)
    auto_resolved = Column(Boolean, default=False)
    
    # Alert metadata
    alert_data = Column(JSON)  # Additional alert data
    context_data = Column(JSON)  # Context when alert was triggered
    
    # Notification tracking
    notifications_sent = Column(JSON)  # Track sent notifications
    notification_channels = Column(JSON)  # Channels to notify
    
    # Relationships (with explicit foreign_keys to avoid conflicts)
    acknowledger = relationship("User", foreign_keys=[acknowledged_by], backref="acknowledged_alerts_v2")
    resolver = relationship("User", foreign_keys=[resolved_by], backref="resolved_alerts_v2")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "alert_type": self.alert_type,
            "alert_level": self.alert_level,
            "service_name": self.service_name,
            "operation": self.operation,
            "title": self.title,
            "message": self.message,
            "description": self.description,
            "metric_value": self.metric_value,
            "threshold_value": self.threshold_value,
            "condition": self.condition,
            "status": self.status,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes,
            "auto_resolved": self.auto_resolved,
            "alert_data": self.alert_data,
            "context_data": self.context_data,
            "notifications_sent": self.notifications_sent,
            "notification_channels": self.notification_channels,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# Training-related models for LLM Training Page feature

class TrainingSession(db.Model, TimestampMixin):
    """Training session model for managing AI model training"""
    
    __tablename__ = "training_sessions"
    __table_args__ = (
        Index('idx_training_session_user_status', 'user_id', 'status'),
        Index('idx_training_session_created', 'created_at'),
        Index('idx_training_session_active', 'is_active'),
    )
    
    id = get_uuid_column()
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="created", nullable=False)  # created, processing, completed, failed
    
    # Training configuration
    max_questions_to_answer = Column(Integer, nullable=True)
    use_in_main_app = Column(Boolean, default=False, nullable=False)
    confidence_threshold = Column(Float, default=0.6, nullable=False)
    
    # Training metrics
    total_guides = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    average_confidence = Column(Float, nullable=True)
    training_duration_seconds = Column(Integer, nullable=True)
    
    # Status tracking
    current_step = Column(String(100), nullable=True)
    progress_percentage = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    
    # Model metadata
    model_data = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user = relationship("User", backref="training_sessions")
    training_guides = relationship("TrainingGuide", back_populates="session", cascade="all, delete-orphan")
    training_results = relationship("TrainingResult", back_populates="session", cascade="all, delete-orphan")
    test_submissions = relationship("TestSubmission", back_populates="session", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "max_questions_to_answer": self.max_questions_to_answer,
            "use_in_main_app": self.use_in_main_app,
            "confidence_threshold": self.confidence_threshold,
            "total_guides": self.total_guides,
            "total_questions": self.total_questions,
            "average_confidence": self.average_confidence,
            "training_duration_seconds": self.training_duration_seconds,
            "current_step": self.current_step,
            "progress_percentage": self.progress_percentage,
            "error_message": self.error_message,
            "model_data": self.model_data,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TrainingGuide(db.Model, TimestampMixin):
    """Training guide model for storing uploaded marking guides"""
    
    __tablename__ = "training_guides"
    __table_args__ = (
        Index('idx_training_guide_session', 'session_id'),
        Index('idx_training_guide_status', 'processing_status'),
        Index('idx_training_guide_hash', 'content_hash'),
    )
    
    id = get_uuid_column()
    session_id = Column(String(36), ForeignKey("training_sessions.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    
    # Guide classification
    guide_type = Column(String(50), nullable=False)  # questions_only, questions_answers, answers_only
    content_text = Column(Text)
    content_hash = Column(String(64), index=True)
    
    # Processing results
    processing_status = Column(String(50), default="pending", nullable=False)
    processing_error = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Extracted metadata
    question_count = Column(Integer, default=0)
    total_marks = Column(Float, default=0.0)
    format_confidence = Column(Float, nullable=True)
    
    # Relationships
    session = relationship("TrainingSession", back_populates="training_guides")
    training_questions = relationship("TrainingQuestion", back_populates="guide", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "guide_type": self.guide_type,
            "content_text": self.content_text,
            "content_hash": self.content_hash,
            "processing_status": self.processing_status,
            "processing_error": self.processing_error,
            "confidence_score": self.confidence_score,
            "question_count": self.question_count,
            "total_marks": self.total_marks,
            "format_confidence": self.format_confidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TrainingQuestion(db.Model, TimestampMixin):
    """Training question model for storing extracted questions and criteria"""
    
    __tablename__ = "training_questions"
    __table_args__ = (
        Index('idx_training_question_guide', 'guide_id'),
        Index('idx_training_question_confidence', 'extraction_confidence'),
        Index('idx_training_question_review', 'manual_review_required'),
    )
    
    id = get_uuid_column()
    guide_id = Column(String(36), ForeignKey("training_guides.id"), nullable=False, index=True)
    question_number = Column(String(50), nullable=False)
    question_text = Column(Text, nullable=False)
    expected_answer = Column(Text)
    point_value = Column(Float, nullable=False)
    
    # Rubric details
    rubric_details = Column(JSON)
    visual_elements = Column(JSON)
    context = Column(Text)
    
    # Confidence and quality metrics
    extraction_confidence = Column(Float, nullable=True)
    manual_review_required = Column(Boolean, default=False)
    
    # Relationships
    guide = relationship("TrainingGuide", back_populates="training_questions")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "guide_id": self.guide_id,
            "question_number": self.question_number,
            "question_text": self.question_text,
            "expected_answer": self.expected_answer,
            "point_value": self.point_value,
            "rubric_details": self.rubric_details,
            "visual_elements": self.visual_elements,
            "context": self.context,
            "extraction_confidence": self.extraction_confidence,
            "manual_review_required": self.manual_review_required,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TrainingResult(db.Model, TimestampMixin):
    """Training result model for storing training outcomes"""
    
    __tablename__ = "training_results"
    __table_args__ = (
        Index('idx_training_result_session', 'session_id'),
        Index('idx_training_result_confidence', 'average_confidence_score'),
    )
    
    id = get_uuid_column()
    session_id = Column(String(36), ForeignKey("training_sessions.id"), nullable=False, index=True)
    
    # Training metrics
    total_processing_time = Column(Float, nullable=False)
    questions_processed = Column(Integer, nullable=False)
    questions_with_high_confidence = Column(Integer, default=0)
    questions_requiring_review = Column(Integer, default=0)
    
    # Model performance
    average_confidence_score = Column(Float, nullable=True)
    predicted_accuracy = Column(Float, nullable=True)
    
    # Training data
    training_metadata = Column(JSON)
    model_parameters = Column(JSON)
    
    # Relationships
    session = relationship("TrainingSession", back_populates="training_results")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "total_processing_time": self.total_processing_time,
            "questions_processed": self.questions_processed,
            "questions_with_high_confidence": self.questions_with_high_confidence,
            "questions_requiring_review": self.questions_requiring_review,
            "average_confidence_score": self.average_confidence_score,
            "predicted_accuracy": self.predicted_accuracy,
            "training_metadata": self.training_metadata,
            "model_parameters": self.model_parameters,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TestSubmission(db.Model, TimestampMixin):
    """Test submission model for model validation"""
    
    __tablename__ = "test_submissions"
    __table_args__ = (
        Index('idx_test_submission_session', 'session_id'),
        Index('idx_test_submission_status', 'processing_status'),
    )
    
    id = get_uuid_column()
    session_id = Column(String(36), ForeignKey("training_sessions.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    
    # OCR and processing results
    extracted_text = Column(Text)
    ocr_confidence = Column(Float, nullable=True)
    
    # Grading results
    predicted_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    matched_questions = Column(JSON)
    misalignments = Column(JSON)
    
    # Test metadata
    processing_status = Column(String(50), default="pending")
    processing_error = Column(Text, nullable=True)
    
    # Relationships
    session = relationship("TrainingSession", back_populates="test_submissions")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "extracted_text": self.extracted_text,
            "ocr_confidence": self.ocr_confidence,
            "predicted_score": self.predicted_score,
            "confidence_score": self.confidence_score,
            "matched_questions": self.matched_questions,
            "misalignments": self.misalignments,
            "processing_status": self.processing_status,
            "processing_error": self.processing_error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class UserSettings(db.Model, TimestampMixin):
    """User settings model for storing user preferences and configuration."""
    
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, unique=True)
    
    # File processing settings
    max_file_size = db.Column(db.Integer, nullable=True, default=None)  # MB, NULL = unlimited
    allowed_formats = db.Column(db.Text, default='.pdf,.jpg,.jpeg,.png,.docx,.doc,.txt')  # Comma-separated
    
    # API configuration (encrypted)
    llm_api_key_encrypted = db.Column(db.Text)
    llm_model = db.Column(db.String(100), default='deepseek-chat')
    llm_base_url = db.Column(db.String(500))
    ocr_api_key_encrypted = db.Column(db.Text)
    ocr_api_url = db.Column(db.String(500))
    
    # UI preferences
    theme = db.Column(db.String(20), default='light')
    language = db.Column(db.String(10), default='en')
    
    # Notification settings
    email_notifications = db.Column(db.Boolean, default=True)
    processing_notifications = db.Column(db.Boolean, default=True)
    notification_level = db.Column(db.String(20), default='info')
    
    # Additional preferences
    auto_save = db.Column(db.Boolean, default=False)
    show_tooltips = db.Column(db.Boolean, default=True)
    results_per_page = db.Column(db.Integer, default=10)
    
    # Processing & Performance settings
    default_processing_method = db.Column(db.String(50), default='traditional_ocr')
    processing_timeout = db.Column(db.Integer, default=300)  # seconds
    max_retry_attempts = db.Column(db.Integer, default=3)
    enable_processing_fallback = db.Column(db.Boolean, default=True)
    
    # Grading & AI settings
    llm_strict_mode = db.Column(db.Boolean, default=False)
    llm_require_json_response = db.Column(db.Boolean, default=True)
    grading_confidence_threshold = db.Column(db.Integer, default=75)  # percentage
    auto_grade_threshold = db.Column(db.Integer, default=80)  # percentage
    
    # Security & Privacy settings
    session_timeout = db.Column(db.Integer, default=120)  # minutes
    auto_delete_after_days = db.Column(db.Integer, default=30)
    enable_audit_logging = db.Column(db.Boolean, default=False)
    encrypt_stored_files = db.Column(db.Boolean, default=False)
    
    # Monitoring & Logging settings
    log_level = db.Column(db.String(20), default='INFO')
    enable_performance_monitoring = db.Column(db.Boolean, default=True)
    enable_error_reporting = db.Column(db.Boolean, default=True)
    metrics_retention_days = db.Column(db.Integer, default=90)
    
    # Email & Notification settings
    notification_email = db.Column(db.String(255))
    webhook_url = db.Column(db.String(500))
    
    # Cache & Storage settings
    cache_type = db.Column(db.String(20), default='simple')
    cache_ttl_hours = db.Column(db.Integer, default=24)
    enable_cache_warming = db.Column(db.Boolean, default=False)
    auto_cleanup_storage = db.Column(db.Boolean, default=True)
    
    # Advanced System settings
    debug_mode = db.Column(db.Boolean, default=False)
    maintenance_mode = db.Column(db.Boolean, default=False)
    max_concurrent_processes = db.Column(db.Integer, default=4)
    memory_limit_gb = db.Column(db.Integer, default=4)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        try:
            # Handle max_file_size - convert inf to a safe value for JSON serialization
            max_file_size_value = self.max_file_size
            if isinstance(max_file_size_value, str) and max_file_size_value.lower() == 'inf':
                max_file_size_value = None  # Use None instead of inf for unlimited
            elif max_file_size_value == float('inf'):
                max_file_size_value = None  # Use None instead of inf for unlimited
            elif max_file_size_value is not None and not isinstance(max_file_size_value, (int, float)):
                max_file_size_value = None  # Invalid value = unlimited
        
            return {
                "id": self.id,
                "user_id": self.user_id,
                "max_file_size": max_file_size_value,
                "allowed_formats": self.allowed_formats or ".pdf,.jpg,.jpeg,.png,.docx,.doc,.txt",
                "llm_model": self.llm_model or "deepseek-chat",
                "llm_base_url": self.llm_base_url or "",
                "llm_api_key": self.get_llm_api_key(),
                "ocr_api_url": self.ocr_api_url or "https://www.handwritingocr.com/api/v3",
                "ocr_api_key": self.get_ocr_api_key(),
                "theme": self.theme or "light",
                "language": self.language or "en",
                "email_notifications": bool(self.email_notifications),
                "processing_notifications": bool(self.processing_notifications),
                "notification_level": self.notification_level or "info",
                "auto_save": bool(self.auto_save),
                "show_tooltips": bool(self.show_tooltips),
                "results_per_page": self.results_per_page or 10,
                # Processing & Performance
                "default_processing_method": self.default_processing_method or "traditional_ocr",
                "processing_timeout": self.processing_timeout or 300,
                "max_retry_attempts": self.max_retry_attempts or 3,
                "enable_processing_fallback": bool(self.enable_processing_fallback),
                # Grading & AI
                "llm_strict_mode": bool(self.llm_strict_mode),
                "llm_require_json_response": bool(self.llm_require_json_response),
                "grading_confidence_threshold": self.grading_confidence_threshold or 75,
                "auto_grade_threshold": self.auto_grade_threshold or 80,
                # Security & Privacy
                "session_timeout": self.session_timeout or 120,
                "auto_delete_after_days": self.auto_delete_after_days or 30,
                "enable_audit_logging": bool(self.enable_audit_logging),
                "encrypt_stored_files": bool(self.encrypt_stored_files),
                # Monitoring & Logging
                "log_level": self.log_level or "INFO",
                "enable_performance_monitoring": bool(self.enable_performance_monitoring),
                "enable_error_reporting": bool(self.enable_error_reporting),
                "metrics_retention_days": self.metrics_retention_days or 90,
                # Email & Notifications
                "notification_email": self.notification_email or "",
                "webhook_url": self.webhook_url or "",
                # Cache & Storage
                "cache_type": self.cache_type or "simple",
                "cache_ttl_hours": self.cache_ttl_hours or 24,
                "enable_cache_warming": bool(self.enable_cache_warming),
                "auto_cleanup_storage": bool(self.auto_cleanup_storage),
                # Advanced System
                "debug_mode": bool(self.debug_mode),
                "maintenance_mode": bool(self.maintenance_mode),
                "max_concurrent_processes": self.max_concurrent_processes or 4,
                "memory_limit_gb": self.memory_limit_gb or 4,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }
        except Exception as e:
            logger.error(f"Error converting UserSettings to dict: {e}")
            # Return safe defaults if conversion fails
            return self.get_default_settings()
    
    @classmethod
    def get_default_settings(cls) -> Dict[str, Any]:
        """Get default settings dictionary."""
        import os
        
        return {
            "max_file_size": None,  # MB, None = unlimited
            "allowed_formats": ".pdf,.jpg,.jpeg,.png,.docx,.doc,.txt",
            "llm_model": os.getenv("LLM_MODEL_NAME", "deepseek-chat"),
            "llm_base_url": os.getenv("LLM_API_URL", "https://api.deepseek.com/v1"),
            "ocr_api_url": os.getenv("HANDWRITING_OCR_API_URL", "https://www.handwritingocr.com/api/v3"),
            "theme": "light",
            "language": "en",
            "email_notifications": True,
            "processing_notifications": True,
            "notification_level": "info",
            "auto_save": False,
            "show_tooltips": True,
            "results_per_page": 10,
            "llm_api_key": os.getenv("LLM_API_KEY", ""),
            "ocr_api_key": os.getenv("HANDWRITING_OCR_API_KEY", ""),
            # Processing & Performance
            "default_processing_method": "traditional_ocr",
            "processing_timeout": 300,
            "max_retry_attempts": 3,
            "enable_processing_fallback": True,
            # Grading & AI
            "llm_strict_mode": False,
            "llm_require_json_response": True,
            "grading_confidence_threshold": 75,
            "auto_grade_threshold": 80,
            # Security & Privacy
            "session_timeout": 120,
            "auto_delete_after_days": 30,
            "enable_audit_logging": False,
            "encrypt_stored_files": False,
            # Monitoring & Logging
            "log_level": "INFO",
            "enable_performance_monitoring": True,
            "enable_error_reporting": True,
            "metrics_retention_days": 90,
            # Email & Notifications
            "notification_email": "",
            "webhook_url": "",
            # Cache & Storage
            "cache_type": "simple",
            "cache_ttl_hours": 24,
            "enable_cache_warming": False,
            "auto_cleanup_storage": True,
            # Advanced System
            "debug_mode": False,
            "maintenance_mode": False,
            "max_concurrent_processes": 4,
            "memory_limit_gb": 4,
        }
    
    @classmethod
    def get_or_create_for_user(cls, user_id: str) -> 'UserSettings':
        """Get or create user settings for a specific user."""
        settings = cls.query.filter_by(user_id=user_id).first()
        if not settings:
            # Create new settings with default values
            defaults = cls.get_default_settings()
            settings = cls(
                user_id=user_id,
                # Basic settings
                max_file_size=defaults['max_file_size'],
                allowed_formats=defaults['allowed_formats'],
                llm_model=defaults['llm_model'],
                llm_base_url=defaults['llm_base_url'],
                ocr_api_url=defaults['ocr_api_url'],
                theme=defaults['theme'],
                language=defaults['language'],
                email_notifications=defaults['email_notifications'],
                processing_notifications=defaults['processing_notifications'],
                notification_level=defaults['notification_level'],
                auto_save=defaults['auto_save'],
                show_tooltips=defaults['show_tooltips'],
                results_per_page=defaults['results_per_page'],
                # Processing & Performance
                default_processing_method=defaults['default_processing_method'],
                processing_timeout=defaults['processing_timeout'],
                max_retry_attempts=defaults['max_retry_attempts'],
                enable_processing_fallback=defaults['enable_processing_fallback'],
                # Grading & AI
                llm_strict_mode=defaults['llm_strict_mode'],
                llm_require_json_response=defaults['llm_require_json_response'],
                grading_confidence_threshold=defaults['grading_confidence_threshold'],
                auto_grade_threshold=defaults['auto_grade_threshold'],
                # Security & Privacy
                session_timeout=defaults['session_timeout'],
                auto_delete_after_days=defaults['auto_delete_after_days'],
                enable_audit_logging=defaults['enable_audit_logging'],
                encrypt_stored_files=defaults['encrypt_stored_files'],
                # Monitoring & Logging
                log_level=defaults['log_level'],
                enable_performance_monitoring=defaults['enable_performance_monitoring'],
                enable_error_reporting=defaults['enable_error_reporting'],
                metrics_retention_days=defaults['metrics_retention_days'],
                # Email & Notifications
                notification_email=defaults['notification_email'],
                webhook_url=defaults['webhook_url'],
                # Cache & Storage
                cache_type=defaults['cache_type'],
                cache_ttl_hours=defaults['cache_ttl_hours'],
                enable_cache_warming=defaults['enable_cache_warming'],
                auto_cleanup_storage=defaults['auto_cleanup_storage'],
                # Advanced System
                debug_mode=defaults['debug_mode'],
                maintenance_mode=defaults['maintenance_mode'],
                max_concurrent_processes=defaults['max_concurrent_processes'],
                memory_limit_gb=defaults['memory_limit_gb']
            )
            db.session.add(settings)
            db.session.commit()
        return settings
    
    @property
    def allowed_formats_list(self) -> list:
        """Get allowed formats as a list."""
        if not self.allowed_formats:
            return []
        return [fmt.strip() for fmt in self.allowed_formats.split(',') if fmt.strip()]
    
    @allowed_formats_list.setter
    def allowed_formats_list(self, formats: list):
        """Set allowed formats from a list."""
        if isinstance(formats, list):
            self.allowed_formats = ','.join(formats)
        else:
            self.allowed_formats = str(formats)
    
    def set_llm_api_key(self, api_key: str):
        """Set LLM API key (encrypted storage)."""
        # For now, just store as plain text - in production, this should be encrypted
        self.llm_api_key_encrypted = api_key
    
    def get_llm_api_key(self) -> str:
        """Get LLM API key (decrypted)."""
        # For now, just return as plain text - in production, this should be decrypted
        return self.llm_api_key_encrypted or ""
    
    def set_ocr_api_key(self, api_key: str):
        """Set OCR API key (encrypted storage)."""
        # For now, just store as plain text - in production, this should be encrypted
        self.ocr_api_key_encrypted = api_key
    
    def get_ocr_api_key(self) -> str:
        """Get OCR API key (decrypted)."""
        # For now, just return as plain text - in production, this should be decrypted
        return self.ocr_api_key_encrypted or ""