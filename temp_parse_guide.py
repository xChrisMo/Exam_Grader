"""
Parser for marking guides.
"""
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import docx
from docx.document import Document

from utils.logger import logger

class MarkingGuide:
    """Represents a parsed marking guide with raw content."""
    
    def __init__(self):
        self.total_marks: int = 0
        self.questions: list = []  # Keep this for compatibility
        self.raw_content: str = ""
        
    def set_raw_content(self, content: str) -> None:
        """Set the raw content of the guide."""
        self.raw_content = content
        # Set a default question for compatibility with existing code
        self.questions = [{
            'question_number': 1,
            'question_text': content,
            'max_marks': 0,
            'model_answer': ' ',
            'student_answer': ' ',
            'keywords': [],
            'required_elements': []
        }]
        

def parse_marking_guide(file_path: str) -> Tuple[Optional[MarkingGuide], Optional[str]]:
    """
    Parse a marking guide document.
    
    Args:
        file_path: Path to the marking guide document
        
    Returns:
        Tuple containing:
        - MarkingGuide object with raw content if successful, None if failed
        - Error message if failed, None if successful
    """
    try:
        guide = MarkingGuide()
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.docx':
            return _parse_docx_guide(file_path, guide)
        elif file_ext == '.txt':
            return _parse_txt_guide(file_path, guide)
        else:
            return None, f"Unsupported file format: {file_ext}"
            
    except Exception as e:
        logger.error(f"Error parsing marking guide: {str(e)}")
        return None, f"Failed to parse marking guide: {str(e)}"

def _parse_docx_guide(file_path: str, guide: MarkingGuide) -> Tuple[Optional[MarkingGuide], Optional[str]]:
    """Parse a .docx marking guide and return the raw content."""
    try:
        doc: Document = docx.Document(file_path)
        
        # Extract all paragraphs with original formatting
        paragraphs = [para.text for para in doc.paragraphs]
        raw_content = '\n'.join(paragraphs)
        
        if not raw_content.strip():
            return None, "Document is empty"
        
        # Set the raw content
        guide.set_raw_content(raw_content)
        
        logger.info(f"Successfully extracted {len(raw_content)} characters from DOCX guide")
        return guide, None
        
    except Exception as e:
        logger.error(f"Error parsing DOCX marking guide: {str(e)}")
        return None, f"Failed to parse DOCX guide: {str(e)}"

def _parse_txt_guide(file_path: str, guide: MarkingGuide) -> Tuple[Optional[MarkingGuide], Optional[str]]:
    """Parse a .txt marking guide and return the raw content."""
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return None, f"File not found: {file_path}"
            
        # Check if file is readable
        if not os.access(file_path, os.R_OK):
            return None, f"File is not readable: {file_path}"
            
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"Read file content length: {len(content)}")
        except UnicodeDecodeError:
            # Try with a different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                    logger.debug(f"Read file content length (latin-1): {len(content)}")
            except Exception as e:
                return None, f"Failed to read file: {str(e)}"
        except Exception as e:
            return None, f"Failed to read file: {str(e)}"
            
        if not content.strip():
            return None, "File is empty"
        
        # Set the raw content
        guide.set_raw_content(content)
        
        logger.info(f"Successfully extracted {len(content)} characters from TXT guide")
        return guide, None
        
    except Exception as e:
        logger.error(f"Failed to parse TXT marking guide: {str(e)}")
        return None, f"Failed to parse TXT marking guide: {str(e)}" 