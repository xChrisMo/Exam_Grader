"""
API Module

This module provides unified API endpoints with standardized error handling,
status reporting, and monitoring capabilities.
"""

from flask import Blueprint
from .unified_api import unified_api_bp
from .status_api import status_api_bp
from .error_handlers import APIErrorHandler

# Create the main API blueprint that other modules can import
api_bp = Blueprint('api', __name__, url_prefix='/llm-training/api')

# Import documents routes after creating api_bp to avoid circular imports
from . import documents

__all__ = ['unified_api_bp', 'status_api_bp', 'api_bp', 'APIErrorHandler']
