"""
PDF processing helper functions with improved error handling.
"""

import os
import logging
from pathlib import Path
from typing import Tuple, Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

def analyze_pdf_content(file_path: str) -> Tuple[bool, str, dict]:
    """
    Analyze PDF content to provide better error messages.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Tuple of (success, message, analysis_data)
    """
    try:
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}", {}
        
        doc = fitz.open(file_path)
        
        if doc.page_count == 0:
            doc.close()
            return False, "PDF document has no pages", {}
        
        analysis = {
            'page_count': doc.page_count,
            'has_text': False,
            'has_images': False,
            'total_text_length': 0,
            'pages_with_text': 0,
            'pages_with_images': 0
        }
        
        for page_num, page in enumerate(doc, 1):
            try:
                # Check for text
                page_text = page.get_text()
                text_length = len(page_text.strip())
                analysis['total_text_length'] += text_length
                
                if text_length > 0:
                    analysis['has_text'] = True
                    analysis['pages_with_text'] += 1
                
                # Check for images
                image_list = page.get_images()
                if image_list:
                    analysis['has_images'] = True
                    analysis['pages_with_images'] += 1
                    
            except Exception as e:
                logger.warning(f"Error analyzing page {page_num}: {e}")
        
        doc.close()
        
        # Generate helpful message
        if analysis['total_text_length'] == 0:
            if analysis['has_images']:
                message = (
                    "This PDF appears to be image-based (scanned document). "
                    "OCR processing is required but the OCR service is currently unavailable. "
                    "Please check your OCR configuration or try with a text-based PDF."
                )
            else:
                message = (
                    "This PDF contains no readable text content. "
                    "The document may be empty, corrupted, or require special processing."
                )
        elif analysis['total_text_length'] < 50:
            message = (
                f"This PDF contains very little text ({analysis['total_text_length']} characters). "
                "The document may be mostly images or have formatting issues."
            )
        else:
            message = f"PDF analysis successful. Contains {analysis['total_text_length']} characters of text."
        
        return True, message, analysis
        
    except Exception as e:
        return False, f"Error analyzing PDF: {str(e)}", {}

def get_helpful_error_message(file_path: str, original_error: str) -> str:
    """
    Generate a helpful error message based on PDF analysis.
    
    Args:
        file_path: Path to the PDF file
        original_error: Original error message
        
    Returns:
        str: Helpful error message for the user
    """
    try:
        success, analysis_message, analysis_data = analyze_pdf_content(file_path)
        
        if success:
            return f"{analysis_message} Original error: {original_error}"
        else:
            return f"{analysis_message} Original error: {original_error}"
            
    except Exception:
        return f"Unable to process PDF file. Original error: {original_error}"
