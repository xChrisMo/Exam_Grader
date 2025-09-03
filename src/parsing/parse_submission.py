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
        logger.error(f"Error: {error}")
    else:
        logger.info(text)  # Raw document content
    ```
"""

import mimetypes
import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

from docx import Document
from pdf2image import convert_from_path

from src.config.config_manager import ConfigManager
from src.services.consolidated_ocr_service import (
    ConsolidatedOCRService as OCRService,
    OCRServiceError,
)
from utils.logger import logger

try:
    from utils.pdf_helper import get_helpful_error_message
except ImportError:

    def get_helpful_error_message(file_path, original_error):
        return f"Error processing PDF: {original_error}"


try:
    fallback_ocr_available = True
except ImportError:
    fallback_ocr_available = False

# Initialize configuration
config = ConfigManager()

# Initialize OCR service (optional)
ocr_service_instance = None
try:
    api_key = os.getenv("HANDWRITING_OCR_API_KEY")
    api_url = os.getenv(
        "HANDWRITING_OCR_API_URL", "https://www.handwritingocr.com/api/v3"
    )

    # Always try to initialize OCR service, allowing graceful degradation
    ocr_service_instance = OCRService(
        api_key=api_key, base_url=api_url, allow_no_key=True, enable_fallback=False
    )

    if api_key:
        logger.info("OCR service initialized successfully with API key")
    else:
        logger.warning(
            "OCR service initialized without API key - functionality will be limited"
        )

except Exception as e:
    logger.error(f"OCR Service Error: Failed to initialize OCR service: {str(e)}")
    logger.warning("OCR service will be disabled")
    ocr_service_instance = None
else:
    ocr_service_instance = OCRService(api_key=api_key, base_url=api_url)


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
            ext = Path(file_path).suffix.lower()
            if ext == ".pdf":
                return "application/pdf"
            elif ext in [".docx", ".doc"]:
                return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"]:
                return "image/" + ext[1:]  # Remove the dot
            elif ext == ".txt":
                return "text/plain"
        return mime_type or "application/octet-stream"

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text from a PDF file using OCR.

        This method converts PDF pages to images and processes them with HandwritingOCR.
        No direct text extraction is attempted - all PDFs are processed via OCR.

        Args:
            file_path: Path to the PDF file

        Returns:
            str: Extracted text

        Raises:
            Exception: If text extraction fails
        """
        try:
            logger.debug(f"Processing PDF with OCR: {file_path}")
            
            if not ocr_service_instance:
                logger.error("OCR service not available for PDF processing")
                raise Exception("OCR service not configured - cannot process PDF")

            # Convert PDF to images
            try:
                images = convert_from_path(file_path, dpi=200)
                if not images:
                    logger.error("PDF conversion resulted in no images")
                    raise Exception("PDF document has no pages or is corrupted")
                
                logger.info(f"Successfully converted PDF to {len(images)} images")
                
            except Exception as e:
                logger.error(f"Error converting PDF to images: {str(e)}")
                raise Exception(f"Failed to convert PDF to images: {str(e)}")

            # Process each page with OCR
            text_content = []
            temp_image_paths = []
            
            try:
                import tempfile
                import time
                
                temp_dir = tempfile.gettempdir()
                
                for page_num, image in enumerate(images, 1):
                    temp_filename = f"pdf_page_{page_num}_{int(time.time() * 1000)}_{os.getpid()}.png"
                    temp_path = os.path.join(temp_dir, temp_filename)
                    
                    try:
                        # Save image to temporary file
                        image.save(temp_path, 'PNG')
                        temp_image_paths.append(temp_path)
                        
                        logger.debug(f"Processing page {page_num} with OCR")
                        
                        # Process with OCR
                        page_text = ocr_service_instance.extract_text_from_image(temp_path)
                        
                        if page_text and page_text.strip():
                            text_content.append(page_text)
                            logger.debug(f"Page {page_num}: OCR extracted {len(page_text)} characters")
                        else:
                            logger.debug(f"Page {page_num}: No text extracted")
                            
                    except Exception as e:
                        logger.error(f"Error processing page {page_num}: {str(e)}")
                        continue
                
                # Combine all page text
                full_text = "\n\n".join(text_content)
                
                if not full_text.strip():
                    logger.error("No text could be extracted from PDF using OCR")
                    raise Exception("No readable text found in PDF")
                
                logger.info(f"Successfully extracted {len(full_text)} characters from PDF using OCR")
                return full_text
                
            finally:
                # Clean up temporary files
                for temp_path in temp_image_paths:
                    try:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                            logger.debug(f"Cleaned up temporary image: {temp_path}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up {temp_path}: {str(e)}")

        except Exception as e:
            logger.error(f"PDF OCR Error: Error extracting text from PDF: {str(e)}")
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
            logger.debug(f"Extracting text from DOCX: {file_path}")
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            logger.debug(f"Extracted {len(text)} characters from DOCX: {file_path}")
            return text
        except Exception as e:
            logger.error(f"DOCX Error: Error extracting text from DOCX: {str(e)}")
            raise

    @staticmethod
    def extract_text_from_image(file_path: str) -> str:
        """Extract text from an image using OCR.

        This method processes regular image files (PNG, JPG, etc.) with HandwritingOCR.
        PDF files should use extract_text_from_pdf() instead.

        Args:
            file_path: Path to the image file

        Returns:
            str: Extracted text

        Raises:
            OCRServiceError: If OCR processing fails
        """
        try:
            logger.debug(f"Starting OCR processing for image: {file_path}")
            
            if not ocr_service_instance:
                logger.error("OCR service not available for image processing")
                raise OCRServiceError("OCR service not configured")
            
            # Process the image file with OCR
            text = ocr_service_instance.extract_text_from_image(file_path)
            
            if text and text.strip():
                logger.info(f"Successfully extracted {len(text)} characters from image")
                return text
            else:
                # Process a regular image file
                logger.debug(f"Starting OCR processing for image: {file_path}")
                if ocr_service_instance:
                    text = ocr_service_instance.extract_text_from_image(file_path)
                    logger.debug(f"Extracted {len(text)} characters from image: {file_path}")
                    return text
                else:
                    logger.error("OCR service not available for image processing")
                    raise OCRServiceError("OCR service not configured")

        except OCRServiceError as e:
            logger.error(f"OCR Error: OCR processing failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"OCR Error: Error during OCR processing: {str(e)}")
            raise OCRServiceError(f"OCR processing failed: {str(e)}")

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
            logger.debug(f"Reading text file: {file_path}")
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            logger.debug(f"Extracted {len(text)} characters from text file: {file_path}")
            return text
        except Exception as e:
            logger.error(f"File Error: Error reading text file: {str(e)}")
            raise


def parse_student_submission(
    file_path: str,
    ocr_service: Optional[OCRService] = None,
    marking_guide: Optional[MarkingGuide] = None
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Parses a student submission file and extracts its raw text content.

    Args:
        file_path: The path to the student submission file.
        ocr_service: An optional OCRService instance for image-based PDFs or images.
        marking_guide: The MarkingGuide object containing questions to extract answers for.

    Returns:
        Tuple containing:
        - Dict[str, str]: Contains a single entry with raw text content
        - Optional[str]: Raw text content of the submission (same as in the dict)
        - Optional[str]: Error message if processing failed, None otherwise

    Example:
        ```python
        result, raw_text, error = parse_student_submission("exam.pdf")
        if error:
            logger.error(f"Failed to extract text: {error}")
        else:
            logger.info(f"Raw text: {raw_text}")
        ```

    Note:
        - For image files, OCR will be used to extract text
        - OCR will be used as a fallback for PDFs if direct text extraction fails
        - The function attempts to handle various common errors gracefully
        - Returns empty dict and error message if extraction fails
    """
    try:
        if not os.path.exists(file_path):
            return {}, None, f"File not found: {file_path}"

        # Get file type
        file_type = DocumentParser.get_file_type(file_path)
        logger.debug(f"Detected file type: {file_type}")

        if file_type == "application/pdf":
            # Try to extract text directly from PDF first
            extracted_pdf_text = DocumentParser.extract_text_from_pdf(file_path)
            if extracted_pdf_text:
                raw_text = extracted_pdf_text
            elif ocr_service and config.ocr.enabled:
                logger.info("PDF text extraction failed or yielded no content, attempting OCR...")
                try:
                    raw_text = ocr_service.extract_text_from_image(file_path)
                except OCRServiceError as e:
                    error_message = f"OCR processing failed for PDF: {str(e)}"
                    logger.error(error_message)
            else:
                error_message = "Could not extract text from PDF. OCR service not available or enabled."
                logger.error(error_message)

        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            raw_text = DocumentParser.extract_text_from_docx(file_path)

        elif file_type.startswith("image/"):
            if ocr_service and config.ocr.enabled:
                raw_text = ocr_service.extract_text_from_image(file_path)
            else:
                return {}, None, f"Unsupported file type: {file_type}"
        except Exception as e:
            logger.warning(
                f"Direct text extraction failed: {str(e)}. Attempting OCR fallback."
            )
            raw_text = None

        # If direct extraction failed and OCR wasn't already used, try OCR as fallback
        if (
            (not raw_text or not raw_text.strip())
            and not ocr_used
            and file_type != "text/plain"
        ):
            if not ocr_service_instance:
                logger.error(
                    "OCR service not available - cannot process document without extractable text"
                )
                return (
                    {},
                    None,
                    "Document contains no extractable text and OCR service is not configured. Please ensure the document contains readable text or configure OCR service.",
                )

            try:
                logger.info("Attempting OCR as fallback for text extraction")
                raw_text = DocumentParser.extract_text_from_image(file_path)
                if raw_text and raw_text.strip():
                    logger.info(
                        f"OCR fallback successful, extracted {len(raw_text)} characters"
                    )
                else:
                    logger.warning("OCR completed but returned empty text")
                    return (
                        {},
                        None,
                        "OCR processing completed but no readable text was found in the document. The document may be blank, contain only images, or have text that is too unclear to read.",
                    )
            except Exception as ocr_error:
                logger.error(f"OCR fallback also failed: {str(ocr_error)}")
                return (
                    {},
                    None,
                    f"Text extraction failed and OCR fallback also failed: {str(ocr_error)}",
                )

        if not raw_text or not raw_text.strip():
            error_message = f"No text could be extracted from the document: {file_path}"
            logger.error(error_message)
            return {}, "", error_message

        # Return the raw text without any further processing
        logger.info(f"Successfully extracted {len(raw_text)} characters of raw text")

        # Create result dictionary
        result = {"raw": raw_text}

        return result, raw_text, None

    except Exception as e:
        logger.error(
            f"Text Extraction Error: Error extracting text from submission: {str(e)}"
        )
        return {}, None, str(e)
