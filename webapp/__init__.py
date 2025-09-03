"""
Webapp package for the Exam Grader application.

This package contains the Flask web application components including
routes, templates, static files, and web-specific utilities.
"""

__version__ = "1.0.0"
__author__ = "Exam Grader Team"

from .app_factory import cleanup_services, create_app, create_database_tables

__all__ = ["create_app", "create_database_tables", "cleanup_services"]
