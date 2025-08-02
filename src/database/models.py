"""
Database models for the Exam Grader application.

This module defines SQLAlchemy models for persistent data storage,
replacing the session-based storage system.
"""
from typing import Any, Dict

import uuid
from datetime import datetime, timezone, timedelta

# Fix datetime import for models
from datetime import datetime, timezone as datetime_class

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
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

class LLMDocument(db.Model, TimestampMixin):
    """LLM training document model"""
    
    __tablename__ = "llm_documents"
    
    id = get_uuid_column()
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=False)
    text_content = Column(Text)
    content_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hash of content for deduplication
    word_count = Column(Integer, default=0)
    character_count = Column(Integer, default=0)
    extracted_text = Column(Boolean, default=False)
    type = Column(String(50), default='document', nullable=False)  # document, training_guide, test_submission
    
    # Enhanced validation and processing fields
    validation_status = Column(String(50), default='pending')  # pending, valid, invalid, error
    validation_errors = Column(JSON)
    processing_retries = Column(Integer, default=0)
    content_quality_score = Column(Float)
    extraction_method = Column(String(50))  # auto, manual, fallback
    processing_duration_ms = Column(Integer)
    
    # Relationships
    user = relationship("User", backref="llm_documents")
    dataset_documents = relationship("LLMDatasetDocument", back_populates="document", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "originalName": self.original_name,
            "storedName": self.stored_name,
            "type": self.file_type.upper(),
            "mimeType": self.mime_type,
            "size": self.file_size,
            "datasets": [dd.dataset_id for dd in self.dataset_documents],
            "metadata": {
                "uploadDate": self.created_at.isoformat(),
                "wordCount": self.word_count,
                "characterCount": self.character_count,
                "extractedText": self.extracted_text
            }
        }

class LLMDataset(db.Model, TimestampMixin):
    """LLM training dataset model"""
    
    __tablename__ = "llm_datasets"
    
    id = get_uuid_column()
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    document_count = Column(Integer, default=0)
    total_words = Column(Integer, default=0)
    total_size = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", backref="llm_datasets")
    dataset_documents = relationship("LLMDatasetDocument", back_populates="dataset", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "documents": [dd.document_id for dd in self.dataset_documents],
            "documentCount": self.document_count,
            "metadata": {
                "createdDate": self.created_at.isoformat(),
                "totalWords": self.total_words,
                "totalSize": self.total_size
            }
        }

class LLMDatasetDocument(db.Model):
    """Association table for datasets and documents"""
    
    __tablename__ = "llm_dataset_documents"
    
    dataset_id = Column(String(36), ForeignKey("llm_datasets.id"), primary_key=True)
    document_id = Column(String(36), ForeignKey("llm_documents.id"), primary_key=True)
    
    # Relationships
    dataset = relationship("LLMDataset", back_populates="dataset_documents")
    document = relationship("LLMDocument", back_populates="dataset_documents")

class LLMTrainingJob(db.Model, TimestampMixin):
    """LLM training job model"""
    
    __tablename__ = "llm_training_jobs"
    
    id = get_uuid_column()
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    model_id = Column(String(100), nullable=False)
    dataset_id = Column(String(36), ForeignKey("llm_datasets.id"), nullable=False, index=True)
    status = Column(String(50), default="pending", nullable=False)  # pending, preparing, training, evaluating, completed, failed, cancelled
    progress = Column(Float, default=0.0)
    current_epoch = Column(Integer, default=0)
    total_epochs = Column(Integer, default=10)
    accuracy = Column(Float)
    validation_accuracy = Column(Float)
    loss = Column(Float)
    validation_loss = Column(Float)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    error_message = Column(Text)
    
    # Training configuration
    config_epochs = Column(Integer, default=10)
    config_batch_size = Column(Integer, default=8)
    config_learning_rate = Column(Float, default=0.0001)
    config_max_tokens = Column(Integer, default=512)
    config_temperature = Column(Float)
    config_custom_parameters = Column(JSON)
    
    # Results and metrics
    training_metrics = Column(JSON)
    evaluation_results = Column(JSON)
    model_output_path = Column(String(500))
    
    # Enhanced validation and monitoring fields
    validation_results = Column(JSON)
    health_metrics = Column(JSON)
    resume_count = Column(Integer, default=0)
    quality_score = Column(Float)
    
    # Relationships
    user = relationship("User", backref="llm_training_jobs")
    dataset = relationship("LLMDataset", backref="training_jobs")
    model_tests = relationship("LLMModelTest", back_populates="training_job", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "model_id": self.model_id,
            "dataset_id": self.dataset_id,
            "status": self.status,
            "progress": self.progress,
            "current_epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "accuracy": self.accuracy,
            "validation_accuracy": self.validation_accuracy,
            "loss": self.loss,
            "validation_loss": self.validation_loss,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_message": self.error_message,
            "config": {
                "epochs": self.config_epochs,
                "batch_size": self.config_batch_size,
                "learning_rate": self.config_learning_rate,
                "max_tokens": self.config_max_tokens,
                "temperature": self.config_temperature,
                "custom_parameters": self.config_custom_parameters
            },
            "training_metrics": self.training_metrics,
            "evaluation_results": self.evaluation_results,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class LLMTrainingReport(db.Model, TimestampMixin):
    """LLM training report model"""
    
    __tablename__ = "llm_training_reports"
    
    id = get_uuid_column()
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    job_ids = Column(JSON, nullable=False)  # List of training job IDs
    report_type = Column(String(50), default="training_summary")
    format = Column(String(20), default="html")  # html, pdf, json
    status = Column(String(50), default="generating")  # generating, completed, failed
    file_path = Column(String(500))
    file_size = Column(Integer)
    
    # Report configuration
    include_metrics = Column(Boolean, default=True)
    include_logs = Column(Boolean, default=False)
    include_charts = Column(Boolean, default=True)
    chart_format = Column(String(10), default="png")
    
    # Report data
    report_data = Column(JSON)
    generation_error = Column(Text)
    
    # Relationships
    user = relationship("User", backref="llm_training_reports")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "job_ids": self.job_ids,
            "report_type": self.report_type,
            "format": self.format,
            "status": self.status,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "config": {
                "include_metrics": self.include_metrics,
                "include_logs": self.include_logs,
                "include_charts": self.include_charts,
                "chart_format": self.chart_format
            },
            "report_data": self.report_data,
            "generation_error": self.generation_error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class LLMModelTest(db.Model, TimestampMixin):
    """LLM model testing session model"""
    
    __tablename__ = "llm_model_tests"
    
    id = get_uuid_column()
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    training_job_id = Column(String(36), ForeignKey("llm_training_jobs.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='pending')  # pending, running, completed, failed, cancelled
    progress = Column(Float, default=0.0)
    
    # Test configuration
    config = Column(JSON)  # Test configuration parameters
    grading_criteria = Column(JSON)  # Grading criteria and thresholds
    confidence_threshold = Column(Float, default=0.8)
    comparison_mode = Column(String(50), default='strict')  # strict, lenient, custom
    feedback_level = Column(String(50), default='detailed')  # basic, detailed, comprehensive
    
    # Test results and metrics
    results = Column(JSON)  # Overall test results and summary
    performance_metrics = Column(JSON)  # Detailed performance metrics
    accuracy_score = Column(Float)
    average_confidence = Column(Float)
    total_submissions = Column(Integer, default=0)
    processed_submissions = Column(Integer, default=0)
    
    # Timing information
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    processing_duration_ms = Column(Integer)
    
    # Error handling
    error_message = Column(Text)
    error_details = Column(JSON)
    
    # Relationships
    user = relationship("User", backref="llm_model_tests")
    training_job = relationship("LLMTrainingJob", back_populates="model_tests")
    test_submissions = relationship("LLMTestSubmission", back_populates="test", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "training_job_id": self.training_job_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "progress": self.progress,
            "config": self.config,
            "grading_criteria": self.grading_criteria,
            "confidence_threshold": self.confidence_threshold,
            "comparison_mode": self.comparison_mode,
            "feedback_level": self.feedback_level,
            "results": self.results,
            "performance_metrics": self.performance_metrics,
            "accuracy_score": self.accuracy_score,
            "average_confidence": self.average_confidence,
            "total_submissions": self.total_submissions,
            "processed_submissions": self.processed_submissions,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_duration_ms": self.processing_duration_ms,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class LLMTestSubmission(db.Model, TimestampMixin):
    """Individual test submission for model testing"""
    
    __tablename__ = "llm_test_submissions"
    
    id = get_uuid_column()
    test_id = Column(String(36), ForeignKey("llm_model_tests.id"), nullable=False, index=True)
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    
    # Content and processing
    text_content = Column(Text)
    word_count = Column(Integer, default=0)
    processing_status = Column(String(50), default='pending')  # pending, processing, completed, failed
    processing_error = Column(Text)
    processing_duration_ms = Column(Integer)
    
    # Expected vs actual results
    expected_grade = Column(Float)
    expected_feedback = Column(Text)
    model_grade = Column(Float)
    model_feedback = Column(Text)
    confidence_score = Column(Float)
    
    # Analysis and comparison
    grade_difference = Column(Float)  # Difference between expected and model grade
    grade_accuracy = Column(Boolean)  # Whether grade is within acceptable range
    feedback_similarity = Column(Float)  # Similarity score between expected and model feedback
    
    # Detailed results
    detailed_results = Column(JSON)  # Detailed grading breakdown
    comparison_analysis = Column(JSON)  # Detailed comparison analysis
    
    # Relationships
    test = relationship("LLMModelTest", back_populates="test_submissions")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "test_id": self.test_id,
            "original_name": self.original_name,
            "stored_name": self.stored_name,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "text_content": self.text_content,
            "word_count": self.word_count,
            "processing_status": self.processing_status,
            "processing_error": self.processing_error,
            "processing_duration_ms": self.processing_duration_ms,
            "expected_grade": self.expected_grade,
            "expected_feedback": self.expected_feedback,
            "model_grade": self.model_grade,
            "model_feedback": self.model_feedback,
            "confidence_score": self.confidence_score,
            "grade_difference": self.grade_difference,
            "grade_accuracy": self.grade_accuracy,
            "feedback_similarity": self.feedback_similarity,
            "detailed_results": self.detailed_results,
            "comparison_analysis": self.comparison_analysis,
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

class UserSettings(db.Model, TimestampMixin):
    """User settings model for storing user preferences and configuration."""
    
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, unique=True)
    
    # File processing settings
    max_file_size = db.Column(db.Integer, default=100)  # MB
    allowed_formats = db.Column(db.Text, default='.pdf,.jpg,.jpeg,.png,.docx,.doc,.txt')  # Comma-separated
    
    # API configuration (encrypted)
    llm_api_key_encrypted = db.Column(db.Text)
    llm_model = db.Column(db.String(100), default='deepseek-chat')
    ocr_api_key_encrypted = db.Column(db.Text)
    ocr_api_url = db.Column(db.String(500))
    
    # UI preferences
    theme = db.Column(db.String(20), default='light')
    language = db.Column(db.String(10), default='en')
    notification_level = db.Column(db.String(20), default='info')
    
    # Additional preferences
    auto_save = db.Column(db.Boolean, default=True)
    show_tooltips = db.Column(db.Boolean, default=True)
    results_per_page = db.Column(db.Integer, default=10)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    
    def __repr__(self):
        return f'<UserSettings {self.user_id}>'
    
    @property
    def allowed_formats_list(self):
        """Get allowed formats as a list."""
        if not self.allowed_formats:
            return []
        return [fmt.strip() for fmt in self.allowed_formats.split(',') if fmt.strip()]
    
    @allowed_formats_list.setter
    def allowed_formats_list(self, formats):
        """Set allowed formats from a list."""
        if isinstance(formats, list):
            self.allowed_formats = ','.join(formats)
        else:
            self.allowed_formats = str(formats)
    
    def get_decrypted_llm_api_key(self):
        """Get decrypted LLM API key."""
        if not self.llm_api_key_encrypted:
            return ''
        try:
            from src.utils.encryption import decrypt_data
            return decrypt_data(self.llm_api_key_encrypted)
        except Exception:
            return ''
    
    def set_llm_api_key(self, api_key):
        """Set encrypted LLM API key."""
        if not api_key:
            self.llm_api_key_encrypted = None
            return
        try:
            from src.utils.encryption import encrypt_data
            self.llm_api_key_encrypted = encrypt_data(api_key)
        except Exception:
            self.llm_api_key_encrypted = api_key
    
    def get_decrypted_ocr_api_key(self):
        """Get decrypted OCR API key."""
        if not self.ocr_api_key_encrypted:
            return ''
        try:
            from src.utils.encryption import decrypt_data
            return decrypt_data(self.ocr_api_key_encrypted)
        except Exception:
            return ''
    
    def set_ocr_api_key(self, api_key):
        """Set encrypted OCR API key."""
        if not api_key:
            self.ocr_api_key_encrypted = None
            return
        try:
            from src.utils.encryption import encrypt_data
            self.ocr_api_key_encrypted = encrypt_data(api_key)
        except Exception:
            self.ocr_api_key_encrypted = api_key
    
    def to_dict(self):
        """Convert settings to dictionary."""
        return {
            'max_file_size': self.max_file_size,
            'allowed_formats': self.allowed_formats_list,
            'llm_api_key': self.get_decrypted_llm_api_key(),
            'llm_model': self.llm_model,
            'ocr_api_key': self.get_decrypted_ocr_api_key(),
            'ocr_api_url': self.ocr_api_url,
            'theme': self.theme,
            'language': self.language,
            'notification_level': self.notification_level,
            'auto_save': self.auto_save,
            'show_tooltips': self.show_tooltips,
            'results_per_page': self.results_per_page
        }
    
    @classmethod
    def get_or_create_for_user(cls, user_id):
        """Get or create settings for a user."""
        settings = cls.query.filter_by(user_id=user_id).first()
        if not settings:
            settings = cls(user_id=user_id)
            db.session.add(settings)
            db.session.commit()
        return settings
    
    @classmethod
    def get_default_settings(cls):
        """Get default settings dictionary."""
        return {
            'max_file_size': 100,
            'allowed_formats': ['.pdf', '.jpg', '.jpeg', '.png', '.docx', '.doc', '.txt'],
            'llm_api_key': '',
            'llm_model': 'deepseek-chat',
            'ocr_api_key': '',
            'ocr_api_url': '',
            'theme': 'light',
            'language': 'en',
            'notification_level': 'info',
            'auto_save': True,
            'show_tooltips': True,
            'results_per_page': 10
        }


class SystemAlertsV2(db.Model, TimestampMixin):
    """Model for system alerts and notifications (v2)."""
    
    __tablename__ = "system_alerts"
    __table_args__ = (
        Index('idx_alert_level_status', 'alert_level', 'status'),
        Index('idx_alert_service', 'service_name'),
        Index('idx_alert_created', 'created_at'),
        Index('idx_alert_resolved', 'resolved_at'),
    )
    
    id = get_uuid_column()
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
    
    # Relationships
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
