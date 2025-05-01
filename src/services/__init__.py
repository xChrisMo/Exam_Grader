"""
Service modules for external integrations.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from src.services.ocr_service import OCRService, OCRServiceError
from utils.logger import logger

# Load environment variables
load_dotenv()

# Initialize OCR service
try:
    api_key = os.getenv('HANDWRITING_OCR_API_KEY')
    if not api_key:
        raise ValueError("HandwritingOCR API key not configured. Set HANDWRITING_OCR_API_KEY in .env")
        
    api_url = os.getenv(
        'HANDWRITING_OCR_API_URL',
        'https://www.handwritingocr.com/api/v3'
    )
    
    ocr_service = OCRService(api_key=api_key, base_url=api_url)
    logger.log_info("OCR service initialized successfully")
except Exception as e:
    logger.log_error("OCR Service Error", f"Failed to initialize OCR service: {str(e)}")
    raise

__all__ = ['OCRService', 'OCRServiceError', 'ocr_service'] 