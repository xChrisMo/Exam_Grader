"""
Core Services Module

This module contains the core business logic services that have been
consolidated from multiple redundant implementations.
"""

from .error_service import ErrorService, error_service
from .file_processing_service import FileProcessingService, file_processing_service

__all__ = [
    "ErrorService",
    "error_service",
    "FileProcessingService",
    "file_processing_service",
]
