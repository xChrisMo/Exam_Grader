"""
Parsing Package for Exam Grader

This package provides functionality for parsing and processing student exam submissions
in various formats. It handles multiple file types including:
- PDF documents
- Microsoft Word documents (DOCX)
- Images (with OCR support for handwritten submissions)
- Plain text files

The package exposes the main parsing function `parse_student_submission` which serves
as the primary entry point for processing exam submissions. The function automatically
detects file types and uses appropriate parsing strategies.

Example:
    ```python
    from src.parsing import parse_student_submission

    answers, raw_text, error = parse_student_submission("student_exam.pdf")
    if not error:
        print(f"Successfully parsed {len(answers)} questions")
    ```
"""

from .parse_submission import parse_student_submission

__all__ = ["parse_student_submission"]
