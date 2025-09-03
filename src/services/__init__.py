"""
Service modules for external integrations.
"""

# Import service classes only (no initialization)
from .consolidated_ocr_service import ConsolidatedOCRService, OCRServiceError
from .consolidated_llm_service import ConsolidatedLLMService, LLMServiceError
from .consolidated_mapping_service import ConsolidatedMappingService
from .consolidated_grading_service import ConsolidatedGradingService

# Backward compatibility aliases
OCRService = ConsolidatedOCRService
LLMService = ConsolidatedLLMService
MappingService = ConsolidatedMappingService
GradingService = ConsolidatedGradingService

__all__ = [
    "OCRService",
    "OCRServiceError", 
    "LLMService",
    "LLMServiceError",
    "MappingService",
    "GradingService",
    "ConsolidatedOCRService",
    "ConsolidatedLLMService", 
    "ConsolidatedMappingService",
    "ConsolidatedGradingService",
]