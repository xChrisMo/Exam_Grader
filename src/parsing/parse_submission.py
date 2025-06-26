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

import mimetypes
import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

import fitz  # PyMuPDF
from docx import Document

from src.config.config_manager import ConfigManager
from src.services.ocr_service import OCRService, OCRServiceError
from utils.logger import logger
from src.database.models import MarkingGuide

# Initialize configuration
config = ConfigManager()

# Initialize OCR service (optional)
api_key = os.getenv("HANDWRITING_OCR_API_KEY")
api_url = os.getenv(
    "HANDWRITING_OCR_API_URL", "https://www.handwritingocr.com/api/v3"
)
if not api_key:
    logger.warning("OCR API key missing - image processing disabled")
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
            # Try to determine type from file extension
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
        """Extract text from a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            str: Extracted text

        Raises:
            Exception: If text extraction fails
        """
        try:
            logger.debug(f"Opening PDF file: {file_path}")
            doc = fitz.open(file_path)

            if doc.page_count == 0:
                logger.error("PDF Error: PDF document has no pages")
                raise Exception("PDF document has no pages")

            logger.info(f"Processing PDF with {doc.page_count} pages")
            text = ""

            # Try normal text extraction first
            for page_num, page in enumerate(doc, 1):
                try:
                    page_text = page.get_text()
                    logger.debug(
                        f"Page {page_num}: Extracted {len(page_text)} characters"
                    )
                    text += page_text
                except Exception as e:
                    logger.error(
                        f"PDF Page Error: Error extracting text from page {page_num}: {str(e)}"
                    )
                    continue

            # Check if we got meaningful text (more than just whitespace or a few characters)
            if not text.strip() or len(text.strip()) < 10:
                logger.warning(
                    "PDF text extraction yielded insufficient text, OCR may be needed"
                )
                # We'll let the caller handle OCR fallback
                return ""

            logger.info(f"Successfully extracted {len(text)} characters from PDF")
            return text

        except Exception as e:
            logger.error(f"PDF Error: Error extracting text from PDF: {str(e)}")
            # Return empty string to signal that extraction failed
            # The caller will handle OCR fallback
            return ""
        finally:
            doc.close() # Ensure the document is closed

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

        This method can be used for both image files and as a fallback for PDFs.
        For PDFs, it will convert each page to an image and process it with OCR.

        Args:
            file_path: Path to the image file or PDF

        Returns:
            str: Extracted text

        Raises:
            OCRServiceError: If OCR processing fails
        """
        try:
            # Check if the file is a PDF
            is_pdf = file_path.lower().endswith(".pdf")

            if is_pdf:
                logger.debug(f"Processing PDF with OCR: {file_path}")
                doc = fitz.open(file_path)

                if doc.page_count == 0:
                    logger.error(f"PDF Error: PDF document has no pages")
                    raise Exception("PDF document has no pages")

                # Process each page with OCR
                text = ""
                for page_num, page in enumerate(doc, 1):
                    try:
                        logger.debug(f"Converting page {page_num} to image")
                        # Convert page to image
                        import tempfile
                        # Create a temporary file for the image
                        fd, temp_img_path = tempfile.mkstemp(suffix=".png")
                        os.close(fd) # Close the file descriptor immediately
                        try:
                            pix = page.get_pixmap()
                            pix.save(temp_img_path)
                            del pix # Explicitly delete pixmap to release resources
                        except Exception as e:
                            logger.error(f"Error saving pixmap to temporary file {temp_img_path}: {str(e)}")
                            if os.path.exists(temp_img_path):
                                os.unlink(temp_img_path)
                            raise

                        logger.debug(f"Processing page {page_num} with OCR")
                        # Process image with OCR
                        if ocr_service_instance:
                            page_text = ocr_service_instance.extract_text_from_image(
                                temp_img_path
                            )
                        else:
                            logger.warning("OCR service not available, skipping page")
                            page_text = ""
                        text += page_text + "\n"
                        logger.debug("OCR processing completed")

                        # Clean up temporary image
                        try:
                            os.unlink(temp_img_path) # Use unlink for better cross-platform compatibility
                            logger.debug(
                                f"Cleaned up temporary image {temp_img_path} for page {page_num}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to clean up temporary image {temp_img_path}: {str(e)}"
                            )

                        logger.debug(
                            f"Page {page_num}: OCR extracted {len(page_text)} characters"
                        )
                    except Exception as e:
                        logger.error(f"OCR Error: Error processing page {page_num}: {str(e)}")
                        continue

                if not text.strip():
                    logger.error(f"OCR Error: No text could be extracted from PDF using OCR")
                    raise OCRServiceError(
                        "No text content could be extracted from PDF using OCR"
                    )

                logger.info(
                    f"Successfully extracted {len(text)} characters from PDF using OCR"
                )
                doc.close() # Ensure the document is closed
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
            with open(file_path, "r", encoding="utf-8") as f:
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
        A tuple containing:
        - A dictionary with 'raw_text' and 'answers' (extracted based on marking guide).
        - An error message string if an error occurred, otherwise None.
    """
    logger.info(f"Attempting to parse submission: {file_path}")
    raw_text = ""
    error_message = None
    extracted_answers = {}

    try:
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

        # Check if we have any text
        if not raw_text or not raw_text.strip():
            error_message = f"No text could be extracted from the document: {file_path}"
            logger.error(error_message)
            return {}, "", error_message


        elif file_type.startswith("image/"):
            if ocr_service and config.ocr.enabled:
                raw_text = ocr_service.extract_text_from_image(file_path)
            else:
                error_message = "OCR service not available or enabled for image processing."
                logger.error(error_message)

        elif file_type == "text/plain":
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()

        else:
            error_message = f"Unsupported file type: {file_type}"
            logger.warning(error_message)

        # If raw_text is successfully extracted and a marking_guide is provided, attempt to extract answers
        if raw_text and marking_guide and marking_guide.questions:
            logger.info("Attempting to extract answers based on marking guide questions.")
            # This is a placeholder for actual answer extraction logic.
            # In a real scenario, you would use an LLM or regex to find answers
            # to each question from the raw_text.
            for i, question_obj in enumerate(marking_guide.questions):
                question_text = question_obj.get('question', f'Question {i+1}')
                # Simple placeholder: assume the answer is just the raw text for now
                # In a real application, this would involve LLM calls or more complex parsing
                extracted_answers[question_text] = f"[Placeholder Answer for {question_text}]"
            logger.info(f"Extracted placeholder answers for {len(marking_guide.questions)} questions.")

    except Exception as e:
        error_message = f"Error processing file {file_path}: {str(e)}"
        logger.error(error_message)

    return {'raw_text': raw_text, 'answers': extracted_answers}, error_message
