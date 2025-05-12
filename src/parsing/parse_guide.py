"""
Parser for marking guides.

This module provides functionality to extract raw text content from marking guide documents.
It supports DOCX and TXT formats and focuses solely on extracting the raw text without
any additional parsing or analysis.
"""
import os
from pathlib import Path
from typing import Optional, Tuple

import docx
from docx.document import Document

from utils.logger import logger

class MarkingGuide:
    """
    Represents a marking guide with raw text content.

    This class is a simple container for the raw text content of a marking guide.
    It includes placeholder attributes for total_marks and questions to maintain
    compatibility with existing code, but these are not populated during parsing.
    """

    def __init__(self):
        # Raw text content of the guide
        self.raw_content: str = ""
        # Placeholder attributes for compatibility
        self.total_marks: int = 0
        self.questions: list = []

    def set_raw_content(self, content: str) -> None:
        """Set the raw content of the guide."""
        self.raw_content = content

def parse_marking_guide(file_path: str) -> Tuple[Optional[MarkingGuide], Optional[str]]:
    """
    Extract raw text content from a marking guide document.

    This function reads the document and extracts only the raw text content without
    any additional parsing or analysis. It supports DOCX and TXT formats.

    Args:
        file_path: Path to the marking guide document (DOCX or TXT)

    Returns:
        Tuple containing:
        - MarkingGuide object with raw content if successful, None if failed
        - Error message if failed, None if successful
    """
    try:
        # Validate file exists
        if not os.path.exists(file_path):
            return None, f"File not found: {file_path}"

        # Create guide object
        guide = MarkingGuide()

        # Determine file type and extract text
        file_ext = Path(file_path).suffix.lower()
        logger.info(f"Processing marking guide with extension: {file_ext}")

        if file_ext == '.docx':
            return _parse_docx_guide(file_path, guide)
        elif file_ext == '.txt':
            return _parse_txt_guide(file_path, guide)
        else:
            return None, f"Unsupported file format: {file_ext}. Only .docx and .txt are supported."

    except Exception as e:
        logger.error(f"Error extracting text from marking guide: {str(e)}")
        return None, f"Failed to extract text from marking guide: {str(e)}"

def _parse_docx_guide(file_path: str, guide: MarkingGuide) -> Tuple[Optional[MarkingGuide], Optional[str]]:
    """
    Extract raw text content from a .docx marking guide.

    This function extracts only the text content from the document without any
    additional parsing or analysis.
    """
    try:
        # Open the document
        doc: Document = docx.Document(file_path)

        # Extract all paragraphs as plain text
        paragraphs = [para.text for para in doc.paragraphs]
        raw_content = '\n'.join(paragraphs)

        # Check if document has content
        if not raw_content.strip():
            return None, "Document is empty or contains only whitespace"

        # Set the raw content in the guide object
        guide.set_raw_content(raw_content)

        logger.info(f"Successfully extracted {len(raw_content)} characters from DOCX guide")
        return guide, None

    except Exception as e:
        logger.error(f"Error extracting text from DOCX marking guide: {str(e)}")
        return None, f"Failed to extract text from DOCX guide: {str(e)}"

def _parse_txt_guide(file_path: str, guide: MarkingGuide) -> Tuple[Optional[MarkingGuide], Optional[str]]:
    """
    Extract raw text content from a .txt marking guide.

    This function reads the text file and extracts its content without any
    additional parsing or analysis. It handles different encodings (UTF-8, Latin-1)
    to maximize compatibility.
    """
    try:
        # Check if file is readable
        if not os.access(file_path, os.R_OK):
            return None, f"File is not readable: {file_path}"

        # Read file content with encoding fallback
        content = None

        # Try UTF-8 first (most common encoding)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"Successfully read file with UTF-8 encoding: {len(content)} characters")
        except UnicodeDecodeError:
            # Fall back to Latin-1 (should handle most Western text)
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                    logger.debug(f"Successfully read file with Latin-1 encoding: {len(content)} characters")
            except Exception as e:
                return None, f"Failed to read file with fallback encoding: {str(e)}"
        except Exception as e:
            return None, f"Failed to read file: {str(e)}"

        # Check if file has content
        if not content or not content.strip():
            return None, "File is empty or contains only whitespace"

        # Set the raw content in the guide object
        guide.set_raw_content(content)

        logger.info(f"Successfully extracted {len(content)} characters from TXT guide")
        return guide, None

    except Exception as e:
        logger.error(f"Error extracting text from TXT marking guide: {str(e)}")
        return None, f"Failed to extract text from TXT marking guide: {str(e)}"