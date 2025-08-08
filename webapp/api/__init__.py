"""
API Module

This module provides unified API endpoints with standardized error handling,
status reporting, and monitoring capabilities.
"""

from flask import Blueprint

from .error_handlers import APIErrorHandler
from .status_api import status_api_bp
from .unified_api import unified_api_bp

# Create the main API blueprint that other modules can import
api_bp = Blueprint("api", __name__, url_prefix="/api")

__all__ = ["unified_api_bp", "status_api_bp", "api_bp", "APIErrorHandler"]
