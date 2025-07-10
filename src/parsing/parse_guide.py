"""Module for parsing marking guides from various formats.

This module provides functionality to parse marking guides from different file formats
including PDF, DOCX, images, and text files. It extracts the raw content which can then
be processed by the LLM service to identify questions, answers, and mark allocations.
"""

import os
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

from utils.logger import logger
from src.parsing.parse_submission import DocumentParser


@dataclass
class MarkingGuide:
    """Class representing a parsed marking guide."""
    raw_content: str
    file_path: str
    file_type: str
    title: Optional[str] = None


def parse_marking_guide(file_path: str) -> Tuple[Optional[MarkingGuide], Optional[str]]:
    """Parse a marking guide from a file.
    
    Args:
        file_path: Path to the marking guide file
        
    Returns:
        Tuple containing:
        - MarkingGuide object if successful, None otherwise
        - Error message if parsing failed, None otherwise
    """
    try:
        logger.info(f"Parsing marking guide from file: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            return None, error_msg
        
        # Get file type
        mime_type = DocumentParser.get_file_type(file_path)
        logger.info(f"Detected MIME type: {mime_type}")
        
        # Extract file type from MIME type or file extension
        if mime_type == "application/pdf":
            file_type = "pdf"
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            file_type = "docx"
        elif mime_type.startswith("image/"):
            file_type = mime_type.split("/")[1]
        elif mime_type == "text/plain":
            file_type = "txt"
        else:
            # Fallback to extension if MIME type is not recognized
            file_type = os.path.splitext(file_path)[1].lower().lstrip('.')
            if not file_type:
                error_msg = f"Unsupported file type: {mime_type}"
                logger.error(error_msg)
                return None, error_msg
        
        logger.info(f"Using file type: {file_type}")
        
        # Extract content based on file type
        raw_content = ""
        
        if file_type == "pdf":
            raw_content = DocumentParser.extract_text_from_pdf(file_path)
        elif file_type == "docx":
            raw_content = DocumentParser.extract_text_from_docx(file_path)
        elif file_type in ["jpg", "jpeg", "png"]:
            raw_content = DocumentParser.extract_text_from_image(file_path)
        elif file_type == "txt":
            raw_content = DocumentParser.extract_text_from_txt(file_path)
        else:
            error_msg = f"Unsupported file type: {file_type}"
            logger.error(error_msg)
            return None, error_msg
        
        # Check if content was extracted successfully
        if not raw_content or len(raw_content.strip()) < 10:
            # Try OCR as fallback for PDFs and images
            if file_type in ["pdf", "jpg", "jpeg", "png"]:
                logger.info(f"Attempting OCR extraction as fallback for {file_type} file")
                raw_content = DocumentParser.extract_text_from_image(file_path)
            
            # If still no content, return error
            if not raw_content or len(raw_content.strip()) < 10:
                error_msg = "Failed to extract content from file or content too short"
                logger.error(error_msg)
                return None, error_msg
        
        # Create filename-based title (without extension)
        filename = os.path.basename(file_path)
        title = os.path.splitext(filename)[0]
        
        # Create and return MarkingGuide object
        guide = MarkingGuide(
            raw_content=raw_content,
            file_path=file_path,
            file_type=file_type,
            title=title
        )
        
        logger.info(f"Successfully parsed marking guide: {title}")
        logger.debug(f"Content preview: {raw_content[:200]}...")
        
        return guide, None
        
    except Exception as e:
        error_msg = f"Error parsing marking guide: {str(e)}"
        logger.error(error_msg)
        return None, error_msg