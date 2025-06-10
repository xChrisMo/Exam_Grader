"""
Service modules for external integrations.
"""

from src.services.grading_service import GradingService
from src.services.llm_service import LLMService, LLMServiceError
from src.services.mapping_service import MappingService

# Import service classes only (no initialization)
from src.services.ocr_service import OCRService, OCRServiceError

__all__ = [
    "OCRService",
    "OCRServiceError",
    "LLMService",
    "LLMServiceError",
    "MappingService",
    "GradingService",
]
