"""
Exam Grader - A tool for parsing and grading exam submissions.

This package provides functionality for:
- Processing handwritten exam submissions using OCR
- Parsing and grading submissions based on marking guides
- Generating detailed feedback and scores
"""

from dotenv import load_dotenv

__version__ = "0.1.0"
__author__ = "Exam Grader Team"
__license__ = "MIT"


# Load environment variables
load_dotenv(".env", override=True)

# Configuration will be initialized by the Flask app when needed

# Export public interface
__all__ = ["parse_student_submission", "OCRService", "ConfigManager"]
