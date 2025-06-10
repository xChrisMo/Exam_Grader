"""Tests for the parsing functionality."""

import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from src.parsing.parse_submission import (
    DocumentParser,
    parse_student_submission,
)


class TestDocumentParser(unittest.TestCase):
    """Test cases for the DocumentParser class."""

    def test_get_file_type(self):
        """Test file type detection for various file extensions."""
        test_cases = [
            ("test.pdf", "application/pdf"),
            (
                "test.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ("test.jpg", "image/jpeg"),
            ("test.png", "image/png"),
            ("test.txt", "text/plain"),
            ("test.unknown", "application/octet-stream"),
        ]

        for filename, expected_type in test_cases:
            with self.subTest(filename=filename):
                result = DocumentParser.get_file_type(filename)
                self.assertEqual(result, expected_type)

    @patch("fitz.open")
    def test_extract_text_from_pdf(self, mock_fitz_open):
        """Test PDF text extraction."""
        # Mock PDF content
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Sample PDF content"
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]
        mock_doc.page_count = 1
        mock_fitz_open.return_value = mock_doc

        result = DocumentParser.extract_text_from_pdf("test.pdf")
        self.assertEqual(result, "Sample PDF content")

    @patch("src.parsing.parse_submission.Document")
    def test_extract_text_from_docx(self, mock_document_class):
        """Test DOCX text extraction."""
        # Mock DOCX content
        mock_doc = MagicMock()
        mock_doc.paragraphs = [
            MagicMock(text="Paragraph 1"),
            MagicMock(text="Paragraph 2"),
        ]
        mock_document_class.return_value = mock_doc

        result = DocumentParser.extract_text_from_docx("test.docx")
        self.assertEqual(result, "Paragraph 1\nParagraph 2")

    def test_extract_text_from_txt(self):
        """Test text file extraction."""
        test_content = "Line 1\nLine 2\nLine 3"
        mock_file = mock_open(read_data=test_content)

        with patch("builtins.open", mock_file):
            result = DocumentParser.extract_text_from_txt("test.txt")
            self.assertEqual(result, test_content)


class TestParseStudentSubmission(unittest.TestCase):
    """Test cases for the parse_student_submission function."""

    def test_nonexistent_file(self):
        """Test handling of non-existent files."""
        result, text, error = parse_student_submission("nonexistent.pdf")
        self.assertEqual(result, {})
        self.assertIsNone(text)
        self.assertTrue("File not found" in error)

    def test_unsupported_file_type(self):
        """Test handling of unsupported file types."""
        with patch("os.path.exists", return_value=True):
            result, text, error = parse_student_submission("test.xyz")
            self.assertEqual(result, {})
            self.assertIsNone(text)
            self.assertTrue("Unsupported file type" in error)

    @patch("src.parsing.parse_submission.DocumentParser.extract_text_from_pdf")
    def test_successful_pdf_parsing(self, mock_extract):
        """Test successful parsing of a PDF file."""
        test_content = "This is raw PDF content that contains some text"
        mock_extract.return_value = test_content

        with patch("os.path.exists", return_value=True):
            result, text, error = parse_student_submission("test.pdf")
            self.assertIsNone(error)
            self.assertEqual(text, test_content)
            self.assertEqual(result, {"raw": test_content})


if __name__ == "__main__":
    unittest.main()
