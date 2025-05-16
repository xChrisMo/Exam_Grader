"""
Service modules for external integrations.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from utils.logger import logger

# Load environment variables
load_dotenv()

# Import services
from src.services.ocr_service import OCRService, OCRServiceError
from src.services.llm_service_latest import LLMService, LLMServiceError
from src.services.mapping_service import MappingService
from src.services.grading_service import GradingService

# Initialize OCR service
ocr_service = None
try:
    api_key = os.getenv('HANDWRITING_OCR_API_KEY')
    if not api_key:
        logger.warning("HandwritingOCR API key not configured. OCR service will not be available.")
    else:
        api_url = os.getenv(
            'HANDWRITING_OCR_API_URL',
            'https://www.handwritingocr.com/api/v3'
        )

        ocr_service = OCRService(api_key=api_key, base_url=api_url)
        logger.info("OCR service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize OCR service: {str(e)}")

# Initialize LLM service
llm_service = None
try:
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        logger.warning("DeepSeek API key not configured. LLM service will not be available.")
    else:
        llm_service = LLMService()
        logger.info("LLM service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize LLM service: {str(e)}")

__all__ = [
    'OCRService', 'OCRServiceError', 'ocr_service',
    'LLMService', 'LLMServiceError', 'llm_service',
    'MappingService', 'GradingService'
]