"""
Service modules for external integrations.
"""

from src.services.consolidated_grading_service import ConsolidatedGradingService as GradingService
from src.services.consolidated_llm_service import ConsolidatedLLMService as LLMService, LLMServiceError
from src.services.consolidated_mapping_service import ConsolidatedMappingService as MappingService

# Import service classes only (no initialization)
from src.services.consolidated_ocr_service import ConsolidatedOCRService as OCRService, OCRServiceError

__all__ = [
    "OCRService",
    "OCRServiceError",
    "LLMService",
    "LLMServiceError",
    "MappingService",
    "GradingService",
]
