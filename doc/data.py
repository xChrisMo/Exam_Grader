"""
Database package for the Exam Grader application.

This package provides database models, migrations, and utilities for
persistent data storage replacing the session-based storage system.
"""

from .migration import MigrationManager
from .model import GradingResult, Mapping, MarkingGuide, Session, Submission, User, db
from .util import DatabaseUtils

__all__ = [
    "db",
    "User",
    "MarkingGuide",
    "Submission",
    "Mapping",
    "GradingResult",
    "Session",
    "MigrationManager",
    "DatabaseUtils",
]
