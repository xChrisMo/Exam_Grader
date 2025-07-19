"""Optimized database models with improved indexes, constraints, and validation.

This module contains enhanced versions of the database models with:
- Additional performance indexes
- Proper foreign key constraints with cascading
- Data validation rules
- Optimized query methods
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

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
    CheckConstraint,
    UniqueConstraint,
    event,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, validates
from werkzeug.security import check_password_hash, generate_password_hash

# Initialize SQLAlchemy
db = SQLAlchemy()


def get_uuid_column():
    """Get appropriate UUID column type."""
    return Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


class TimestampMixin:
    """Mixin for adding timestamp fields to models."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False,
        index=True
    )


class ValidationMixin:
    """Mixin for adding validation methods to models."""
    
    def validate_required_fields(self, *fields):
        """Validate that required fields are not None or empty."""
        errors = []
        for field in fields:
            value = getattr(self, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"{field} is required")
        return errors
    
    def validate_string_length(self, field, min_length=None, max_length=None):
        """Validate string field length."""
        value = getattr(self, field, None)
        if value is None:
            return []
        
        errors = []
        if min_length and len(value) < min_length:
            errors.append(f"{field} must be at least {min_length} characters")
        if max_length and len(value) > max_length:
            errors.append(f"{field} must be no more than {max_length} characters")
        return errors


class User(UserMixin, db.Model, TimestampMixin, ValidationMixin):
    """Enhanced User model with improved validation and indexes."""

    __tablename__ = "users"
    __table_args__ = (
        # Composite indexes for common queries
        Index('idx_user_active_login', 'is_active', 'last_login'),
        Index('idx_user_created_active', 'created_at', 'is_active'),
        # Unique constraints
        UniqueConstraint('username', name='uq_user_username'),
        UniqueConstraint('email', name='uq_user_email'),
        # Check constraints for data validation
        CheckConstraint('failed_login_attempts >= 0', name='ck_user_failed_attempts'),
        CheckConstraint("email LIKE '%@%'", name='ck_user_email_format'),
    )

    id = get_uuid_column()
    username = Column(String(80), nullable=False, index=True)
    email = Column(String(120), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_login = Column(DateTime, index=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, index=True)
    
    # Additional fields for enhanced security
    password_changed_at = Column(DateTime, default=datetime.utcnow)
    email_verified = Column(Boolean, default=False, nullable=False)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)

    # Relationships with proper cascading
    marking_guides = relationship(
        "MarkingGuide", 
        back_populates="user", 
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    submissions = relationship(
        "Submission", 
        back_populates="user", 
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    sessions = relationship(
        "Session", 
        back_populates="user", 
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    @validates('username')
    def validate_username(self, key, username):
        """Validate username format and length."""
        if not username or len(username.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if len(username) > 80:
            raise ValueError("Username must be no more than 80 characters")
        if not username.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return username.strip()

    @validates('email')
    def validate_email(self, key, email):
        """Validate email format."""
        if not email or '@' not in email:
            raise ValueError("Valid email address is required")
        if len(email) > 120:
            raise ValueError("Email must be no more than 120 characters")
        return email.lower().strip()

    def set_password(self, password: str):
        """Set password hash with validation."""
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.utcnow()

    def check_password(self, password: str) -> bool:
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)

    def is_locked(self) -> bool:
        """Check if account is locked."""
        return self.locked_until and self.locked_until > datetime.utcnow()

    def lock_account(self, duration_minutes: int = 30):
        """Lock account for specified duration."""
        self.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.failed_login_attempts = 0

    def unlock_account(self):
        """Unlock account."""
        self.locked_until = None
        self.failed_login_attempts = 0

    @hybrid_property
    def is_password_expired(self):
        """Check if password is expired (older than 90 days)."""
        if not self.password_changed_at:
            return True
        return datetime.utcnow() - self.password_changed_at > timedelta(days=90)

    def to_dict(self, include_sensitive=False) -> Dict[str, Any]:
        """Convert to dictionary with optional sensitive data."""
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "two_factor_enabled": self.two_factor_enabled,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        if include_sensitive:
            data.update({
                "failed_login_attempts": self.failed_login_attempts,
                "locked_until": self.locked_until.isoformat() if self.locked_until else None,
                "password_changed_at": self.password_changed_at.isoformat() if self.password_changed_at else None,
                "is_password_expired": self.is_password_expired,
            })
        
        return data

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


class MarkingGuide(db.Model, TimestampMixin, ValidationMixin):
    """Enhanced MarkingGuide model with improved validation and indexes."""
    
    __tablename__ = "marking_guides"
    __table_args__ = (
        # Composite indexes for performance
        Index('idx_guide_user_title', 'user_id', 'title'),
        Index('idx_guide_user_active', 'user_id', 'is_active'),
        Index('idx_guide_created_active', 'created_at', 'is_active'),
        Index('idx_guide_hash_size', 'content_hash', 'file_size'),
        # Check constraints
        CheckConstraint('file_size > 0', name='ck_guide_file_size'),
        CheckConstraint('total_marks >= 0', name='ck_guide_total_marks'),
        CheckConstraint('max_questions_to_answer >= 0', name='ck_guide_max_questions'),
    )
    
    id = get_uuid_column()
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    content_text = Column(Text)
    content_hash = Column(String(64), index=True)
    questions = Column(JSON)
    total_marks = Column(Float, default=0.0, nullable=False)
    max_questions_to_answer = Column(Integer)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="marking_guides")
    submissions = relationship(
        "Submission", 
        back_populates="marking_guide",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    @validates('title')
    def validate_title(self, key, title):
        """Validate title."""
        if not title or not title.strip():
            raise ValueError("Title is required")
        if len(title) > 200:
            raise ValueError("Title must be no more than 200 characters")
        return title.strip()

    @validates('file_size')
    def validate_file_size(self, key, file_size):
        """Validate file size."""
        if file_size <= 0:
            raise ValueError("File size must be positive")
        if file_size > 100 * 1024 * 1024:  # 100MB limit
            raise ValueError("File size cannot exceed 100MB")
        return file_size

    @validates('file_type')
    def validate_file_type(self, key, file_type):
        """Validate file type."""
        allowed_types = {
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain', 'image/jpeg', 'image/png', 'image/gif'
        }
        if file_type not in allowed_types:
            raise ValueError(f"File type {file_type} is not allowed")
        return file_type

    def generate_content_hash(self, content: bytes = None):
        """Generate SHA-256 hash of file content."""
        if content:
            self.content_hash = hashlib.sha256(content).hexdigest()
        elif self.content_text:
            self.content_hash = hashlib.sha256(self.content_text.encode('utf-8')).hexdigest()

    @hybrid_property
    def question_count(self):
        """Get number of questions in the guide."""
        return len(self.questions) if self.questions else 0

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


class Submission(db.Model, TimestampMixin, ValidationMixin):
    """Enhanced Submission model with improved validation and indexes."""

    __tablename__ = "submissions"
    __table_args__ = (
        # Composite indexes for performance optimization
        Index('idx_user_status', 'user_id', 'processing_status'),
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_status_created', 'processing_status', 'created_at'),
        Index('idx_guide_status', 'marking_guide_id', 'processing_status'),
        Index('idx_hash_guide_user', 'content_hash', 'marking_guide_id', 'user_id'),
        # Check constraints
        CheckConstraint('file_size > 0', name='ck_submission_file_size'),
        CheckConstraint('ocr_confidence >= 0 AND ocr_confidence <= 1', name='ck_submission_ocr_confidence'),
        CheckConstraint("processing_status IN ('pending', 'processing', 'completed', 'failed')", name='ck_submission_status'),
    )

    id = get_uuid_column()
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    marking_guide_id = Column(
        String(36), ForeignKey("marking_guides.id", ondelete="CASCADE"), nullable=True, index=True
    )
    student_name = Column(String(200))
    student_id = Column(String(100))
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    content_text = Column(Text)
    content_hash = Column(String(64), index=True)
    answers = Column(JSON)
    ocr_confidence = Column(Float)
    processing_status = Column(String(50), default="pending")
    processing_error = Column(Text)
    archived = Column(Boolean, default=False, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="submissions")
    marking_guide = relationship("MarkingGuide", back_populates="submissions")
    mappings = relationship(
        "Mapping", back_populates="submission", cascade="all, delete-orphan"
    )
    grading_results = relationship(
        "GradingResult", back_populates="submission", cascade="all, delete-orphan"
    )

    @validates('processing_status')
    def validate_status(self, key, status):
        """Validate processing status."""
        valid_statuses = {'pending', 'processing', 'completed', 'failed'}
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return status

    @validates('file_size')
    def validate_file_size(self, key, file_size):
        """Validate file size."""
        if file_size <= 0:
            raise ValueError("File size must be greater than 0")
        if file_size > 100 * 1024 * 1024:  # 100MB limit
            raise ValueError("File size must be less than 100MB")
        return file_size

    @validates('student_name')
    def validate_student_name(self, key, student_name):
        """Validate student name."""
        if not student_name or not student_name.strip():
            raise ValueError("Student name is required")
        if len(student_name) > 200:
            raise ValueError("Student name must be no more than 200 characters")
        return student_name.strip()

    @validates('student_id')
    def validate_student_id(self, key, student_id):
        """Validate student ID."""
        if not student_id or not student_id.strip():
            raise ValueError("Student ID is required")
        if len(student_id) > 100:
            raise ValueError("Student ID must be no more than 100 characters")
        return student_id.strip()

    def generate_content_hash(self, content: bytes = None):
        """Generate SHA-256 hash of file content."""
        if content:
            self.content_hash = hashlib.sha256(content).hexdigest()
        elif self.content_text:
            self.content_hash = hashlib.sha256(self.content_text.encode('utf-8')).hexdigest()

    @property
    def is_duplicate(self) -> bool:
        """Check if this submission is a duplicate based on content hash."""
        if not self.content_hash or not self.marking_guide_id:
            return False
        
        duplicate = Submission.query.filter(
            Submission.content_hash == self.content_hash,
            Submission.marking_guide_id == self.marking_guide_id,
            Submission.id != self.id
        ).first()
        
        return duplicate is not None

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


class Mapping(db.Model, TimestampMixin, ValidationMixin):
    """Enhanced Answer mapping model."""

    __tablename__ = "mappings"
    __table_args__ = (
        Index('idx_submission_question', 'submission_id', 'guide_question_id'),
        Index('idx_mapping_score', 'match_score'),
        Index('idx_mapping_method', 'mapping_method'),
        CheckConstraint('match_score >= 0 AND match_score <= 1', name='ck_mapping_score'),
        CheckConstraint('max_score >= 0', name='ck_mapping_max_score'),
    )

    id = get_uuid_column()
    submission_id = Column(
        String(36), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    guide_question_id = Column(String(100), nullable=False)
    guide_question_text = Column(Text, nullable=False)
    guide_answer = Column(Text)
    max_score = Column(Float, nullable=False)
    submission_answer = Column(Text, nullable=False)
    match_score = Column(Float, default=0.0)
    match_reason = Column(Text)
    mapping_method = Column(String(50), default="llm")

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
    """Enhanced grading result model."""

    __tablename__ = "grading_results"
    __table_args__ = (
        Index('idx_submission_mapping', 'submission_id', 'mapping_id'),
        Index('idx_submission_score', 'submission_id', 'score'),
        Index('idx_method_created', 'grading_method', 'created_at'),
        Index('idx_progress_id', 'progress_id'),
        CheckConstraint('score >= 0', name='ck_grading_score'),
        CheckConstraint('max_score >= 0', name='ck_grading_max_score'),
        CheckConstraint('percentage >= 0 AND percentage <= 100', name='ck_grading_percentage'),
        CheckConstraint('confidence >= 0 AND confidence <= 1', name='ck_grading_confidence'),
    )

    id = get_uuid_column()
    submission_id = Column(String(36), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    marking_guide_id = Column(String(36), ForeignKey("marking_guides.id", ondelete="CASCADE"), nullable=True)
    mapping_id = Column(String(36), ForeignKey("mappings.id", ondelete="CASCADE"), nullable=True)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    percentage = Column(Float, nullable=False)
    feedback = Column(Text)
    detailed_feedback = Column(JSON)
    progress_id = Column(String(36), nullable=True, index=True)
    grading_session_id = Column(
        String(36),
        ForeignKey("grading_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    grading_method = Column(String(50), default="llm")
    confidence = Column(Float)

    # Relationship to GradingSession with cascade delete
    grading_session = relationship("GradingSession", backref="grading_results")

    # Relationships
    submission = relationship("Submission", back_populates="grading_results")
    marking_guide = relationship("MarkingGuide", backref="grading_results")
    mapping = relationship("Mapping", back_populates="grading_results")

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
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Session(db.Model, TimestampMixin):
    """Enhanced session model."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
        Index('idx_session_ip', 'ip_address'),
    )

    id = Column(String(255), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    data = Column(LargeBinary)
    salt = Column(String(255), nullable=True, default='')
    expires_at = Column(DateTime, nullable=False, index=True)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at

    def extend_session(self, duration_seconds: int = 3600):
        """Extend session expiration."""
        self.expires_at = datetime.utcnow() + timedelta(seconds=duration_seconds)
        self.updated_at = datetime.utcnow()

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


class GradingSession(db.Model, TimestampMixin, ValidationMixin):
    """Enhanced grading session tracking model."""

    __tablename__ = "grading_sessions"
    __table_args__ = (
        Index('idx_submission_guide', 'submission_id', 'marking_guide_id'),
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_progress_status', 'progress_id', 'status'),
        CheckConstraint('total_questions_mapped >= 0', name='ck_grading_session_mapped'),
        CheckConstraint('total_questions_graded >= 0', name='ck_grading_session_graded'),
        CheckConstraint('max_questions_limit >= 0', name='ck_grading_session_limit'),
        CheckConstraint("status IN ('not_started', 'in_progress', 'completed', 'failed')", name='ck_grading_session_status'),
    )

    id = get_uuid_column()
    submission_id = Column(String(36), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    marking_guide_id = Column(String(36), ForeignKey("marking_guides.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    progress_id = Column(String(36), nullable=True, index=True)
    status = Column(String(50), default="not_started", nullable=False)
    current_step = Column(String(50), nullable=True)
    total_questions_mapped = Column(Integer, default=0)
    total_questions_graded = Column(Integer, default=0)
    max_questions_limit = Column(Integer, nullable=True)
    processing_start_time = Column(DateTime, nullable=True)
    processing_end_time = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    session_data = Column(JSON, nullable=True)

    # Relationships
    submission = relationship("Submission", backref="grading_sessions")
    marking_guide = relationship("MarkingGuide", backref="grading_sessions")
    user = relationship("User", backref="grading_sessions")

    @validates('status')
    def validate_status(self, key, status):
        """Validate session status."""
        valid_statuses = {'not_started', 'in_progress', 'completed', 'failed'}
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return status

    @validates('current_step')
    def validate_current_step(self, key, current_step):
        """Validate processing current step."""
        if current_step is not None:
            valid_steps = {'text_retrieval', 'mapping', 'grading', 'saving'}
            if current_step not in valid_steps:
                raise ValueError(f"Current step must be one of: {valid_steps}")
        return current_step

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