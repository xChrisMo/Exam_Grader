"""
Database package for the Exam Grader application.

This package provides database models, migrations, and utilities for
persistent data storage replacing the session-based storage system.
"""

# Import core database components
from .models import (
    GradingResult,
    GradingSession,
    Mapping,
    MarkingGuide,
    Session,
    Submission,
    User,
    db,
)
from .utils import DatabaseUtils

# Import migration manager
try:
    from .migrations import MigrationManager
except ImportError:
    MigrationManager = None

# Import optimized models as well
try:
    from . import optimized_models
except ImportError:
    optimized_models = None

__all__ = [
    "db",
    "User",
    "MarkingGuide",
    "Submission",
    "Mapping",
    "GradingResult",
    "GradingSession",
    "Session",
    "MigrationManager",
    "DatabaseUtils",
    "optimized_models",
]
