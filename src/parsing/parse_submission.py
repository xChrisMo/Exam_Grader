"""
Exam Submission Parser Module

This module provides functionality for parsing student exam submissions in various formats
(PDF, DOCX, images, text files) and extracting question-answer pairs. It supports multiple
question numbering formats and uses OCR for handwritten submissions.

Key Components:
    - DocumentParser: Handles different file formats and text extraction
    - QuestionParser: Processes text to identify and extract question-answer pairs
    - QUESTION_PATTERNS: Supported question number formats (e.g., "Q1", "1.", "(1)")

Example Usage:
    ```python
    result, text, error = parse_student_submission("student_exam.pdf")
    if error:
        print(f"Error: {error}")
    else:
        for question, answer in result.items():
            print(f"Question {question}: {answer}")
    ```
"""

import os
import re
from typing import Dict, Optional, Tuple, List, Pattern
from pathlib import Path
import fitz  # PyMuPDF
from docx import Document
import unicodedata
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

# Question patterns with descriptions and examples
QUESTION_PATTERNS: List[Tuple[Pattern, str]] = [
    (re.compile(r'(?:^|\n)(?:[Qq]uestion\s+|[Qq]\.\s*)(\d+)'), 'Question 1, Q. 1'),  # Matches: Question 1, Q. 1
    (re.compile(r'(?:^|\n)(\d+)\s*[.:]'), '1., 1:'),                                 # Matches: 1., 1:
    (re.compile(r'(?:^|\n)\((\d+)\)'), '(1)'),                                       # Matches: (1), (2)
    (re.compile(r'(?:^|\n)\[(\d+)\]'), '[1]'),                                       # Matches: [1], [2]
    (re.compile(r'(?:^|\n)[A-Za-z]\.\s*(\d+)'), 'A. 1'),                            # Matches: A. 1, B. 2
    (re.compile(r'(?:^|\n)[a-z]\)\s*(\d+)'), 'a) 1'),                               # Matches: a) 1, b) 2
    (re.compile(r'(?:^|\n)(\d+)[.:]?\s*[A-Za-z]'), '1. Casting'),                   # Matches: 1. Casting
]

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

class QuestionParser:
    """
    Handles the parsing and extraction of questions and answers from text content.
    """
    
    @staticmethod
    def find_question_numbers(text: str) -> list:
        """Find all question numbers in the text."""
        numbers = set()
        for pattern, _ in QUESTION_PATTERNS:
            matches = pattern.finditer(text)
            for match in matches:
                numbers.add(int(match.group(1)))
        return sorted(list(numbers))
    
    @staticmethod
    def split_text_by_questions(text: str, question_numbers: list) -> Dict[str, str]:
        """Split text into questions and answers."""
        result = {}
        lines = text.split('\n')
        current_question = None
        current_answer = []
        
        # Add debug logging
        logger.debug(f"Splitting text with {len(question_numbers)} expected questions")
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_answer:  # Keep blank lines within answers
                    current_answer.append('')
                continue
            
            # Check if this line starts a new question
            is_question = False
            question_number = None
            
            for pattern, _ in QUESTION_PATTERNS:
                match = pattern.match(line)
                if match:
                    question_num = int(match.group(1))
                    if question_num in question_numbers:  # Only match numbers we're looking for
                        is_question = True
                        question_number = question_num
                        logger.debug(f"Found question {question_number}")
                        break
            
            if is_question:
                # Save previous question if exists
                if current_question is not None and current_answer:
                    answer_text = '\n'.join(current_answer).strip()
                    logger.debug(f"Saving question {current_question} with length {len(answer_text)}")
                    result[str(current_question)] = answer_text
                
                # Start new question
                current_question = question_number
                # Include the question line in the answer if it has content after the question number
                parts = line.split(None, 2)
                current_answer = [parts[2]] if len(parts) > 2 else []
                logger.debug(f"Started question {current_question}")
            else:
                # Add line to current answer
                if current_question is not None:
                    current_answer.append(line)
        
        # Save last question
        if current_question is not None and current_answer:
            answer_text = '\n'.join(current_answer).strip()
            logger.debug(f"Saving final question {current_question} with length {len(answer_text)}")
            result[str(current_question)] = answer_text
        
        # Log results
        logger.debug(f"Found {len(result)} questions")
        for q_num, text in result.items():
            logger.debug(f"Question {q_num} length: {len(text)}")
            logger.debug(f"Question {q_num} preview: {text[:100]}...")
        
        return result

def parse_student_submission(file_path: str) -> Tuple[Dict[str, str], Optional[str], Optional[str]]:
    """
    Parse a student's exam submission file and extract questions and answers.
    
    This function serves as the main entry point for processing student submissions.
    It handles multiple file formats and uses appropriate parsers based on the file type.
    
    Args:
        file_path: Path to the submission file (PDF, DOCX, image, or text)
        
    Returns:
        Tuple containing:
        - Dict[str, str]: Mapping of question numbers to answers
        - Optional[str]: Raw text content of the submission (useful for debugging)
        - Optional[str]: Error message if processing failed, None otherwise
        
    Example:
        ```python
        answers, raw_text, error = parse_student_submission("exam.pdf")
        if error:
            print(f"Failed to parse: {error}")
        else:
            print(f"Found {len(answers)} questions")
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
        
        # Find question numbers
        question_numbers = QuestionParser.find_question_numbers(text)
        if not question_numbers:
            return {}, text, "No questions found in the document"
        
        # Split text into questions and answers
        parsed_data = QuestionParser.split_text_by_questions(text, question_numbers)
        
        if not parsed_data:
            return {}, text, "Could not parse questions and answers"
        
        return parsed_data, text, None
        
    except Exception as e:
        logger.log_error("Parse Error", f"Error parsing submission: {str(e)}")
        return {}, None, str(e) 