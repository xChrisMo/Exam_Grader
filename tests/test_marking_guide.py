"""Tests for the marking guide parsing functionality."""

import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

from src.parsing.parse_guide import (
    MarkingGuide,
    parse_marking_guide,
)
from src.parsing.parse_submission import DocumentParser


class TestMarkingGuide(unittest.TestCase):
    """Test cases for the MarkingGuide class and parse_marking_guide function."""

    def test_marking_guide_dataclass(self):
        """Test MarkingGuide dataclass initialization."""
        guide = MarkingGuide(
            raw_content="Test content",
            file_path="/path/to/file.pdf",
            file_type="pdf",
            title="Test Guide"
        )
        
        self.assertEqual(guide.raw_content, "Test content")
        self.assertEqual(guide.file_path, "/path/to/file.pdf")
        self.assertEqual(guide.file_type, "pdf")
        self.assertEqual(guide.title, "Test Guide")

    def test_nonexistent_file(self):
        """Test handling of non-existent files."""
        with patch("os.path.exists", return_value=False):
            guide, error = parse_marking_guide("nonexistent.pdf")
            self.assertIsNone(guide)
            self.assertTrue("File not found" in error)

    @patch("src.parsing.parse_submission.DocumentParser.get_file_type")
    def test_unsupported_file_type(self, mock_get_file_type):
        """Test handling of unsupported file types."""
        mock_get_file_type.return_value = "application/octet-stream"
        
        with patch("os.path.exists", return_value=True):
            with patch("os.path.splitext", return_value=("/path/to/file", ".xyz")):
                guide, error = parse_marking_guide("test.xyz")
                self.assertIsNone(guide)
                self.assertTrue("Unsupported file type" in error)

    @patch("src.parsing.parse_submission.DocumentParser.get_file_type")
    @patch("src.parsing.parse_submission.DocumentParser.extract_text_from_pdf")
    def test_successful_pdf_parsing(self, mock_extract, mock_get_file_type):
        """Test successful parsing of a PDF file."""
        test_content = "This is a sample marking guide with detailed content"
        mock_extract.return_value = test_content
        mock_get_file_type.return_value = "application/pdf"

        with patch("os.path.exists", return_value=True):
            with patch("os.path.basename", return_value="test.pdf"):
                with patch("os.path.splitext", return_value=("test", ".pdf")):
                    guide, error = parse_marking_guide("test.pdf")
                    self.assertIsNone(error)
                    self.assertIsInstance(guide, MarkingGuide)
                    self.assertEqual(guide.raw_content, test_content)
                    self.assertEqual(guide.file_type, "pdf")
                    self.assertEqual(guide.title, "test")

    @patch("src.parsing.parse_submission.DocumentParser.get_file_type")
    @patch("src.parsing.parse_submission.DocumentParser.extract_text_from_docx")
    def test_successful_docx_parsing(self, mock_extract, mock_get_file_type):
        """Test successful parsing of a DOCX file."""
        test_content = "This is a sample marking guide in DOCX format"
        mock_extract.return_value = test_content
        mock_get_file_type.return_value = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        with patch("os.path.exists", return_value=True):
            with patch("os.path.basename", return_value="test.docx"):
                with patch("os.path.splitext", return_value=("test", ".docx")):
                    guide, error = parse_marking_guide("test.docx")
                    self.assertIsNone(error)
                    self.assertIsInstance(guide, MarkingGuide)
                    self.assertEqual(guide.raw_content, test_content)
                    self.assertEqual(guide.file_type, "docx")
                    self.assertEqual(guide.title, "test")

    @patch("src.parsing.parse_submission.DocumentParser.get_file_type")
    @patch("src.parsing.parse_submission.DocumentParser.extract_text_from_image")
    def test_successful_image_parsing(self, mock_extract, mock_get_file_type):
        """Test successful parsing of an image file."""
        test_content = "This is OCR extracted text from an image"
        mock_extract.return_value = test_content
        mock_get_file_type.return_value = "image/jpeg"

        with patch("os.path.exists", return_value=True):
            with patch("os.path.basename", return_value="test.jpg"):
                with patch("os.path.splitext", return_value=("test", ".jpg")):
                    guide, error = parse_marking_guide("test.jpg")
                    self.assertIsNone(error)
                    self.assertIsInstance(guide, MarkingGuide)
                    self.assertEqual(guide.raw_content, test_content)
                    self.assertEqual(guide.file_type, "jpeg")
                    self.assertEqual(guide.title, "test")

    @patch("src.parsing.parse_submission.DocumentParser.get_file_type")
    @patch("src.parsing.parse_submission.DocumentParser.extract_text_from_pdf")
    @patch("src.parsing.parse_submission.DocumentParser.extract_text_from_image")
    def test_ocr_fallback(self, mock_extract_image, mock_extract_pdf, mock_get_file_type):
        """Test OCR fallback when PDF extraction fails."""
        # PDF extraction returns empty string (failure)
        mock_extract_pdf.return_value = ""
        # OCR extraction succeeds
        mock_extract_image.return_value = "OCR extracted content from PDF"
        mock_get_file_type.return_value = "application/pdf"

        with patch("os.path.exists", return_value=True):
            with patch("os.path.basename", return_value="test.pdf"):
                with patch("os.path.splitext", return_value=("test", ".pdf")):
                    guide, error = parse_marking_guide("test.pdf")
                    self.assertIsNone(error)
                    self.assertIsInstance(guide, MarkingGuide)
                    self.assertEqual(guide.raw_content, "OCR extracted content from PDF")
                    self.assertEqual(guide.file_type, "pdf")
                    # Verify OCR fallback was called
                    mock_extract_image.assert_called_once()


if __name__ == "__main__":
    unittest.main()