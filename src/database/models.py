"""
Database models for the Exam Grader application.

This module defines SQLAlchemy models for persistent data storage,
replacing the session-based storage system.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

# Initialize SQLAlchemy
db = SQLAlchemy()


# Use UUID for PostgreSQL, String for SQLite
def get_uuid_column():
    """Get appropriate UUID column type based on database."""
    return Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


class TimestampMixin:
    """Mixin for adding timestamp fields to models."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class User(db.Model, TimestampMixin):
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
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)

    def is_locked(self) -> bool:
        """Check if account is locked."""
        return self.locked_until and self.locked_until > datetime.utcnow()

    def is_account_locked(self) -> bool:
        """Check if account is locked (alias for is_locked for compatibility)."""
        return self.is_locked()

    def lock_account(self, duration_minutes: int = 30):
        """Lock account for specified duration."""
        self.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.failed_login_attempts = 0

    def unlock_account(self):
        """Unlock account."""
        self.locked_until = None
        self.failed_login_attempts = 0

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
    questions = Column(JSON)  # Structured question data
    total_marks = Column(Float, default=0.0)
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
    answers = Column(JSON)  # Extracted answers
    ocr_confidence = Column(Float)
    processing_status = Column(
        String(50), default="pending"
    )  # pending, processing, completed, failed
    processing_error = Column(Text)

    # Relationships
    user = relationship("User", back_populates="submissions")
    marking_guide = relationship("MarkingGuide", back_populates="submissions")
    mappings = relationship(
        "Mapping", back_populates="submission", cascade="all, delete-orphan"
    )
    grading_results = relationship(
        "GradingResult", back_populates="submission", cascade="all, delete-orphan"
    )

    # Composite indexes for performance optimization
    __table_args__ = (
        db.Index('idx_user_status', 'user_id', 'processing_status'),
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
            "answers": self.answers,
            "ocr_confidence": self.ocr_confidence,
            "processing_status": self.processing_status,
            "processing_error": self.processing_error,
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
    """Grading result model for storing scores and feedback."""

    __tablename__ = "grading_results"

    id = get_uuid_column()
    submission_id = Column(
        String(36), ForeignKey("submissions.id"), nullable=False, index=True
    )
    mapping_id = Column(
        String(36), ForeignKey("mappings.id"), nullable=False, index=True
    )
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    percentage = Column(Float, nullable=False)
    feedback = Column(Text)
    detailed_feedback = Column(JSON)
    grading_method = Column(String(50), default="llm")  # llm, similarity, manual
    confidence = Column(Float)

    # Relationships
    submission = relationship("Submission", back_populates="grading_results")
    mapping = relationship("Mapping", back_populates="grading_results")

    # Composite indexes for performance optimization
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
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Session(db.Model):
    """Session model for secure session management."""

    __tablename__ = "sessions"

    id = Column(String(255), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    data = Column(LargeBinary)  # Encrypted session data
    expires_at = Column(DateTime, nullable=False, index=True)
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at

    def extend_session(self, duration_seconds: int = 3600):
        """Extend session expiration."""
        self.expires_at = datetime.utcnow() + timedelta(seconds=duration_seconds)
        self.last_accessed = datetime.utcnow()

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
            "last_accessed": self.last_accessed.isoformat(),
        }
