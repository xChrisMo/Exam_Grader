"""Tests for the parsing functionality."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from src.parsing.parse_submission import (
    DocumentParser,
    QuestionParser,
    parse_student_submission,
)

class TestDocumentParser(unittest.TestCase):
    """Test cases for the DocumentParser class."""

    def test_get_file_type(self):
        """Test file type detection for various file extensions."""
        test_cases = [
            ('test.pdf', 'application/pdf'),
            ('test.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
            ('test.jpg', 'image/jpg'),
            ('test.png', 'image/png'),
            ('test.txt', 'text/plain'),
            ('test.unknown', 'application/octet-stream'),
        ]
        
        for filename, expected_type in test_cases:
            with self.subTest(filename=filename):
                result = DocumentParser.get_file_type(filename)
                self.assertEqual(result, expected_type)
    
    @patch('fitz.open')
    def test_extract_text_from_pdf(self, mock_fitz_open):
        """Test PDF text extraction."""
        # Mock PDF content
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Sample PDF content"
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz_open.return_value = mock_doc
        
        result = DocumentParser.extract_text_from_pdf("test.pdf")
        self.assertEqual(result, "Sample PDF content")
    
    @patch('docx.Document')
    def test_extract_text_from_docx(self, mock_document):
        """Test DOCX text extraction."""
        # Mock DOCX content
        mock_doc = MagicMock()
        mock_doc.paragraphs = [
            MagicMock(text="Paragraph 1"),
            MagicMock(text="Paragraph 2"),
        ]
        mock_document.return_value = mock_doc
        
        result = DocumentParser.extract_text_from_docx("test.docx")
        self.assertEqual(result, "Paragraph 1\nParagraph 2")
    
    def test_extract_text_from_txt(self):
        """Test text file extraction."""
        test_content = "Line 1\nLine 2\nLine 3"
        mock_file = mock_open(read_data=test_content)
        
        with patch('builtins.open', mock_file):
            result = DocumentParser.extract_text_from_txt("test.txt")
            self.assertEqual(result, test_content)

class TestQuestionParser(unittest.TestCase):
    """Test cases for the QuestionParser class."""
    
    def test_find_question_numbers(self):
        """Test finding question numbers in various formats."""
        test_cases = [
            ("Q1. Answer\nQ2. Answer", [1, 2]),
            ("1. First\n2. Second", [1, 2]),
            ("(1) One\n(2) Two", [1, 2]),
            ("[1] First\n[2] Second", [1, 2]),
            ("A. 1 First\nB. 2 Second", [1, 2]),
            ("a) 1 First\nb) 2 Second", [1, 2]),
            ("Question 1:\nQuestion 2:", [1, 2]),
        ]
        
        for text, expected_numbers in test_cases:
            with self.subTest(text=text):
                result = QuestionParser.find_question_numbers(text)
                self.assertEqual(result, expected_numbers)
    
    def test_split_text_by_questions(self):
        """Test splitting text into question-answer pairs."""
        test_text = """
Q1. First question
This is the answer to question 1

Q2. Second question
This is the answer to question 2
Multiple lines for this answer

Q3. Third question
Final answer here
"""
        expected = {
            "1": "This is the answer to question 1",
            "2": "This is the answer to question 2\nMultiple lines for this answer",
            "3": "Final answer here"
        }
        
        result = QuestionParser.split_text_by_questions(test_text, [1, 2, 3])
        self.assertEqual(result, expected)

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
        with patch('os.path.exists', return_value=True):
            result, text, error = parse_student_submission("test.xyz")
            self.assertEqual(result, {})
            self.assertIsNone(text)
            self.assertTrue("Unsupported file type" in error)
    
    @patch('src.parsing.parse_submission.DocumentParser.extract_text_from_pdf')
    def test_successful_pdf_parsing(self, mock_extract):
        """Test successful parsing of a PDF file."""
        mock_extract.return_value = """
Q1. First question
Answer 1

Q2. Second question
Answer 2
"""
        with patch('os.path.exists', return_value=True):
            result, text, error = parse_student_submission("test.pdf")
            self.assertIsNone(error)
            self.assertEqual(len(result), 2)
            self.assertEqual(result["1"].strip(), "Answer 1")
            self.assertEqual(result["2"].strip(), "Answer 2")

if __name__ == '__main__':
    unittest.main() 