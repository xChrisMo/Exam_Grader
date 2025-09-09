"""
PDF processing helper functions using pdf2image and HandwritingOCR.
"""

import os
import time
import logging
import tempfile
from typing import List, Tuple

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    convert_from_path = None

logger = logging.getLogger(__name__)

def convert_pdf_to_images(file_path: str, dpi: int = 200) -> List[str]:
    """
    Convert PDF pages to images using pdf2image.

    Args:
        file_path: Path to the PDF file
        dpi: Resolution for image conversion (default: 200)

    Returns:
        List[str]: List of temporary image file paths

    Raises:
        Exception: If PDF conversion fails
    """
    if not PDF2IMAGE_AVAILABLE:
        raise Exception("pdf2image is not available. Please install it: pip install pdf2image")

    if not os.path.exists(file_path):
        raise Exception(f"File not found: {file_path}")

    try:
        logger.debug(f"Converting PDF to images: {file_path}")

        # Convert PDF to images
        images = convert_from_path(file_path, dpi=dpi)

        if not images:
            raise Exception("PDF conversion resulted in no images")

        logger.info(f"Successfully converted PDF to {len(images)} images")

        # Save images to temporary files
        temp_image_paths = []
        temp_dir = tempfile.gettempdir()

        for i, image in enumerate(images):
            temp_filename = f"pdf_page_{i+1}_{int(time.time() * 1000)}_{os.getpid()}.png"
            temp_path = os.path.join(temp_dir, temp_filename)

            image.save(temp_path, 'PNG')
            temp_image_paths.append(temp_path)
            logger.debug(f"Saved page {i+1} to {temp_path}")

        return temp_image_paths

    except Exception as e:
        logger.error(f"Error converting PDF to images: {str(e)}")
        raise

def cleanup_temp_images(image_paths: List[str]) -> None:
    """
    Clean up temporary image files.

    Args:
        image_paths: List of temporary image file paths to delete
    """
    for image_path in image_paths:
        try:
            if os.path.exists(image_path):
                os.unlink(image_path)
                logger.debug(f"Cleaned up temporary image: {image_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary image {image_path}: {str(e)}")

def analyze_pdf_content(file_path: str) -> Tuple[bool, str, dict]:
    """
    Analyze PDF content using pdf2image.

    Args:
        file_path: Path to the PDF file

    Returns:
        Tuple of (success, message, analysis_data)
    """
    try:
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}", {}

        if not PDF2IMAGE_AVAILABLE:
            return False, "pdf2image is not available for PDF analysis", {}

        # Convert PDF to images to analyze
        try:
            images = convert_from_path(file_path, dpi=150)  # Lower DPI for analysis

            if not images:
                return False, "PDF document has no pages", {}

            analysis = {
                "page_count": len(images),
                "has_content": True,  # Assume content if we can convert to images
                "processing_method": "OCR_required",
            }

            message = (
                f"PDF analysis successful. Contains {len(images)} pages. "
                "All content will be processed using OCR via HandwritingOCR API."
            )

            return True, message, analysis

        except Exception as e:
            return False, f"Error analyzing PDF: {str(e)}", {}

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
