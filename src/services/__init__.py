"""
Service modules for external integrations.
"""

# Import service classes only (no initialization)
from src.services.ocr_service import OCRService, OCRServiceError
from src.services.llm_service import LLMService, LLMServiceError
from src.services.mapping_service import MappingService
from src.services.grading_service import GradingService

__all__ = [
    'OCRService', 'OCRServiceError',
    'LLMService', 'LLMServiceError',
    'MappingService', 'GradingService'
]