"""
Exam Submission Parser Module

This module provides functionality for parsing student exam submissions in various formats
(PDF, DOCX, images, text files) and extracting the raw content. It no longer parses 
question-answer pairs but simply returns the extracted document text.

Key Components:
    - DocumentParser: Handles different file formats and text extraction

Example Usage:
    ```python
    result, text, error = parse_student_submission("student_exam.pdf")
    if error:
        print(f"Error: {error}")
    else:
        print(text)  # Raw document content
    ```
"""

import os
from typing import Dict, Optional, Tuple, List
from pathlib import Path
import fitz  # PyMuPDF
from docx import Document
import mimetypes

from src.config.config_manager import ConfigManager
from utils.logger import logger
from src.services.ocr_service import OCRService, OCRServiceError

# Initialize configuration
config = ConfigManager()

# Initialize OCR service
try:
    api_key = os.getenv('HANDWRITING_OCR_API_KEY')
    if not api_key:
        raise ValueError("HandwritingOCR API key not configured. Set HANDWRITING_OCR_API_KEY in .env")
        
    api_url = os.getenv('HANDWRITING_OCR_API_URL', 'https://www.handwritingocr.com/api/v3')
    
    ocr_service_instance = OCRService(
        api_key=api_key,
        base_url=api_url
    )
    logger.log_info("OCR service initialized successfully")
except Exception as e:
    logger.log_error("OCR Service Error", f"Failed to initialize OCR service: {str(e)}")
    raise

class DocumentParser:
    """
    A utility class for handling different document formats and extracting text content.
    
    This class provides static methods to:
    - Determine file types based on MIME types and extensions
    - Extract text from various document formats (PDF, DOCX, images, text)
    - Handle encoding and OCR processing where necessary
    
    The class is designed to be stateless, with all methods being static to facilitate
    easy integration and testing.
    """
    
    @staticmethod
    def get_file_type(file_path: str) -> str:
        """
        Determine the MIME type of a file using both mimetypes and file extensions.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            str: MIME type of the file (e.g., 'application/pdf', 'image/jpeg')
            
        Note:
            Falls back to extension-based detection if mimetypes fails to identify the file.
            Returns 'application/octet-stream' if type cannot be determined.
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            # Try to determine type from file extension
            ext = Path(file_path).suffix.lower()
            if ext == '.pdf':
                return 'application/pdf'
            elif ext in ['.docx', '.doc']:
                return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']:
                return 'image/' + ext[1:]  # Remove the dot
            elif ext == '.txt':
                return 'text/plain'
        return mime_type or 'application/octet-stream'
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            str: Extracted text
            
        Raises:
            Exception: If text extraction fails
        """
        try:
            logger.log_debug(f"Opening PDF file: {file_path}")
            doc = fitz.open(file_path)
            
            if doc.page_count == 0:
                logger.log_error("PDF Error", "PDF document has no pages")
                raise Exception("PDF document has no pages")
                
            logger.log_info(f"Processing PDF with {doc.page_count} pages")
            text = ""
            
            # Try normal text extraction first
            for page_num, page in enumerate(doc, 1):
                try:
                    page_text = page.get_text()
                    logger.log_debug(f"Page {page_num}: Extracted {len(page_text)} characters")
                    text += page_text
                except Exception as e:
                    logger.log_error("PDF Page Error", f"Error extracting text from page {page_num}: {str(e)}")
                    continue
            
            # If no text was found, the PDF might contain images - try OCR
            if not text.strip():
                logger.log_info("No text found in PDF, attempting OCR processing")
                try:
                    # Convert PDF to images and process with OCR
                    text = ""
                    for page_num, page in enumerate(doc, 1):
                        try:
                            logger.log_debug(f"Converting page {page_num} to image")
                            # Convert page to image
                            pix = page.get_pixmap()
                            temp_img_path = f"temp_page_{page_num}.png"
                            pix.save(temp_img_path)
                            
                            logger.log_debug(f"Processing page {page_num} with OCR")
                            # Process image with OCR
                            page_text = ocr_service_instance.extract_text_from_image(temp_img_path)
                            text += page_text + "\n"
                            
                            # Clean up temporary image
                            try:
                                os.remove(temp_img_path)
                                logger.log_debug(f"Cleaned up temporary image for page {page_num}")
                            except Exception as e:
                                logger.log_warning(f"Failed to clean up temporary image {temp_img_path}: {str(e)}")
                                
                            logger.log_debug(f"Page {page_num}: OCR extracted {len(page_text)} characters")
                        except Exception as e:
                            logger.log_error("OCR Error", f"Error processing page {page_num}: {str(e)}")
                            continue
                            
                    if not text.strip():
                        logger.log_error("PDF Error", "No text could be extracted from PDF, even with OCR")
                        raise Exception("No text content could be extracted from PDF")
                        
                except Exception as e:
                    logger.log_error("OCR Error", f"Failed to process PDF with OCR: {str(e)}")
                    raise
            
            logger.log_info(f"Successfully extracted {len(text)} characters from PDF")
            return text
            
        except Exception as e:
            logger.log_error("PDF Error", f"Error extracting text from PDF: {str(e)}")
            raise
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """Extract text from a DOCX file.
        
        Args:
            file_path: Path to the DOCX file
            
        Returns:
            str: Extracted text
            
        Raises:
            Exception: If text extraction fails
        """
        try:
            logger.log_debug(f"Extracting text from DOCX: {file_path}")
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            logger.log_info(f"Successfully extracted {len(text)} characters from DOCX")
            return text
        except Exception as e:
            logger.log_error("DOCX Error", f"Error extracting text from DOCX: {str(e)}")
            raise
    
    @staticmethod
    def extract_text_from_image(file_path: str) -> str:
        """Extract text from an image using OCR.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            str: Extracted text
            
        Raises:
            OCRServiceError: If OCR processing fails
        """
        try:
            logger.log_debug(f"Starting OCR processing for image: {file_path}")
            text = ocr_service_instance.extract_text_from_image(file_path)
            logger.log_info(f"Successfully extracted {len(text)} characters from image")
            return text
        except OCRServiceError as e:
            logger.log_error("OCR Error", f"OCR processing failed: {str(e)}")
            raise
    
    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        """Extract text from a TXT file.
        
        Args:
            file_path: Path to the TXT file
            
        Returns:
            str: Extracted text
            
        Raises:
            Exception: If text extraction fails
        """
        try:
            logger.log_debug(f"Reading text file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            logger.log_info(f"Successfully read {len(text)} characters from text file")
            return text
        except Exception as e:
            logger.log_error("File Error", f"Error reading text file: {str(e)}")
            raise

def parse_student_submission(file_path: str) -> Tuple[Dict[str, str], Optional[str], Optional[str]]:
    """
    Parse a student's exam submission file and extract raw text content.
    
    This function serves as the main entry point for processing student submissions.
    It handles multiple file formats and uses appropriate parsers based on the file type.
    
    Args:
        file_path: Path to the submission file (PDF, DOCX, image, or text)
        
    Returns:
        Tuple containing:
        - Dict[str, str]: Contains a single entry with raw text content
        - Optional[str]: Raw text content of the submission (same as in the dict)
        - Optional[str]: Error message if processing failed, None otherwise
        
    Example:
        ```python
        answers, raw_text, error = parse_student_submission("exam.pdf")
        if error:
            print(f"Failed to parse: {error}")
        else:
            print(f"Raw text: {raw_text}")
        ```
        
    Note:
        - For image files, OCR will be used to extract text
        - The function attempts to handle various common errors gracefully
        - Returns empty dict and error message if parsing fails
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return {}, None, f"File not found: {file_path}"
        
        # Get file type
        file_type = DocumentParser.get_file_type(file_path)
        logger.log_debug(f"Processing file type: {file_type}")
        
        # Extract text based on file type
        if file_type == 'application/pdf':
            text = DocumentParser.extract_text_from_pdf(file_path)
        elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            text = DocumentParser.extract_text_from_docx(file_path)
        elif file_type.startswith('image/'):
            text = DocumentParser.extract_text_from_image(file_path)
        elif file_type == 'text/plain':
            text = DocumentParser.extract_text_from_txt(file_path)
        else:
            return {}, None, f"Unsupported file type: {file_type}"
        
        # Simply return the raw text without parsing for questions
        if not text:
            return {}, text, "No text extracted from the document"
        
        # Return a dictionary with a single 'raw' key containing the raw text
        return {'raw': text}, text, None
        
    except Exception as e:
        logger.log_error("Parse Error", f"Error parsing submission: {str(e)}")
        return {}, None, str(e) 