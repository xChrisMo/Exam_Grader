"""Module for parsing marking guides from various formats.

This module provides functionality to parse marking guides from different file formats
including PDF, DOCX, images, and text files. It extracts the raw content which can then
be processed by the LLM service to identify questions, answers, and mark allocations.
"""
from typing import Optional, Tuple

import os
from dataclasses import dataclass

from utils.logger import logger
from src.parsing.parse_submission import DocumentParser

@dataclass
class MarkingGuide:
    """Class representing a parsed marking guide."""
    raw_content: str
    file_path: str
    file_type: str
    title: Optional[str] = None
    extraction_method: Optional[str] = None

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
        filename = os.path.basename(file_path)
        logger.info(f"📄 Processing Word document: {filename}")
        
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(f"✗ {error_msg}")
            return None, error_msg
        
        # Get file type
        mime_type = DocumentParser.get_file_type(file_path)
        
        if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            file_type = "docx"
        elif mime_type == "application/msword":
            file_type = "doc"
        else:
            file_type = os.path.splitext(file_path)[1].lower().lstrip('.')
            if file_type not in ['docx', 'doc']:
                error_msg = f"Only Word documents are supported. Found: {mime_type}"
                logger.error(f"✗ {error_msg}")
                return None, error_msg
        
        # Extract content - WORD DOCUMENTS ONLY (NO OCR)
        raw_content = ""
        extraction_method = "unknown"
        
        try:
            raw_content = DocumentParser.extract_text_from_docx(file_path)
            extraction_method = f"{file_type}_text_extraction"
            
            if raw_content and len(raw_content.strip()) >= 10:
                logger.info(f"✓ Extracted {len(raw_content)} characters from Word document")
            else:
                error_msg = f"Word document appears to be empty or contains insufficient text"
                logger.error(f"✗ {error_msg}")
                return None, error_msg
                
        except Exception as e:
            error_msg = f"Failed to extract text from Word document: {str(e)}"
            if file_type == "doc":
                error_msg += ". Please save as .docx format for better compatibility."
            logger.error(f"✗ {error_msg}")
            return None, error_msg
        
        # Create filename-based title (without extension)
        title = os.path.splitext(filename)[0]
        
        # Create and return MarkingGuide object
        guide = MarkingGuide(
            raw_content=raw_content,
            file_path=file_path,
            file_type=file_type,
            title=title,
            extraction_method=extraction_method
        )
        
        logger.info(f"✓ Successfully parsed: {title}")
        return guide, None
        
    except Exception as e:
        error_msg = f"Error parsing marking guide: {str(e)}"
        logger.error(error_msg)
        return None, error_msg