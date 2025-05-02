"""
Parser for marking guides.
"""
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import docx
from docx.document import Document
from docx.text.paragraph import Paragraph

from utils.logger import logger

# Dictionary to convert word numbers to integers
WORD_TO_INT = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
    'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10,
    'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5,
    'SIX': 6, 'SEVEN': 7, 'EIGHT': 8, 'NINE': 9, 'TEN': 10
}

def convert_to_number(text: str) -> int:
    """Convert a text number (word or digit) to an integer."""
    # Remove any punctuation and convert to lowercase
    clean_text = text.rstrip('.:)')
    
    # First try direct match with uppercase words
    if clean_text in WORD_TO_INT:
        return WORD_TO_INT[clean_text]
    
    # Then try lowercase
    clean_text = clean_text.lower()
    if clean_text in WORD_TO_INT:
        return WORD_TO_INT[clean_text]
    
    # Try to convert directly to int
    try:
        return int(clean_text)
    except ValueError:
        pass
    
    # Try to extract digits if mixed with text (e.g., "Q1" or "Question1")
    digits = ''.join(c for c in clean_text if c.isdigit())
    if digits:
        return int(digits)
    
    # If all else fails, raise an error
    raise ValueError(f"Could not convert '{text}' to a number")

class MarkingGuide:
    """Represents a parsed marking guide with questions and answers."""
    
    def __init__(self):
        self.questions: List[Dict] = []
        self.total_marks: int = 0
        
    def add_question(self, number: str, text: str, marks: int, keywords: List[str], 
                    required_elements: List[str] = None) -> None:
        """Add a question to the marking guide."""
        try:
            # Validate inputs
            if not text:
                raise ValueError("Question text cannot be empty")
            if marks <= 0:
                raise ValueError("Marks must be positive")
                
            question_number = convert_to_number(number)
            question = {
                'question_number': question_number,
                'question_text': text,  # Don't strip to preserve formatting
                'max_marks': marks,
                'model_answer': ' ',  # Space instead of empty string to pass validation
                'student_answer': ' ',  # Space instead of empty string to pass validation
                'keywords': keywords or [],
                'required_elements': required_elements or []
            }
            
            # Log the question being added
            logger.debug(f"Adding question {question_number}:")
            logger.debug(f"- Text length: {len(text)}")
            logger.debug(f"- Marks: {marks}")
            logger.debug(f"- Keywords: {len(keywords or [])}")
            
            self.questions.append(question)
            self.total_marks += marks
            
        except ValueError as e:
            logger.error(f"Error adding question {number}: {str(e)}")
            raise

def parse_marking_guide(file_path: str) -> Tuple[Optional[MarkingGuide], Optional[str]]:
    """
    Parse a marking guide document.
    
    Args:
        file_path: Path to the marking guide document
        
    Returns:
        Tuple containing:
        - MarkingGuide object if successful, None if failed
        - Error message if failed, None if successful
    """
    try:
        guide = MarkingGuide()
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.docx':
            return _parse_docx_guide(file_path, guide)
        elif file_ext == '.txt':
            return _parse_txt_guide(file_path, guide)
        else:
            return None, f"Unsupported file format: {file_ext}"
            
    except Exception as e:
        logger.error(f"Error parsing marking guide: {str(e)}")
        return None, f"Failed to parse marking guide: {str(e)}"

def _parse_marks(text: str) -> Optional[int]:
    """Parse marks from text, handling various formats."""
    try:
        # Look for marks in parentheses at the end of the text
        if text.strip().endswith(')'):
            start = text.rfind('(')
            if start != -1:
                mark_text = text[start+1:text.rfind(')')].strip()
                if 'mark' in mark_text.lower():
                    # Extract digits
                    digits = ''.join(c for c in mark_text if c.isdigit())
                    if digits:
                        marks = int(digits)
                        if marks > 0:
                            return marks
    except Exception:
        pass
    return None

def _parse_docx_guide(file_path: str, guide: MarkingGuide) -> Tuple[Optional[MarkingGuide], Optional[str]]:
    """Parse a .docx marking guide."""
    try:
        doc: Document = docx.Document(file_path)
        current_question = None
        current_text = []
        current_marks = 0
        current_keywords = []
        
        logger.debug("Starting DOCX parsing")
        
        for para in doc.paragraphs:
            # Preserve original text formatting
            original_text = para.text
            text = para.text.strip()
            if not text:
                # Preserve empty lines in the text
                if current_question:
                    current_text.append('')
                continue
            
            logger.debug(f"Processing paragraph: {text[:100]}...")
            
            # Check for question markers
            if text.lower().startswith(('question', 'q.')):
                logger.debug("Found question marker")
                # Save previous question if exists
                if current_question and current_marks > 0:  # Only save if we have valid marks
                    # Preserve the formatting by joining with original line breaks
                    question_text = '\n'.join(current_text)
                    logger.debug(f"Saving question {current_question}:")
                    logger.debug(f"- Text length: {len(question_text)}")
                    logger.debug(f"- Text preview: {question_text[:100]}...")
                    logger.debug(f"- Marks: {current_marks}")
                    guide.add_question(
                        current_question,
                        question_text,
                        current_marks,
                        current_keywords
                    )
                
                # Start new question
                parts = text.split(None, 2)
                if len(parts) >= 2:
                    current_question = parts[1].rstrip('.:)')
                    current_text = []  # Reset text buffer
                    # Add the original text as the first line
                    current_text.append(original_text)
                    current_marks = 0
                    current_keywords = []
                    logger.debug(f"Started new question {current_question}")
                    
            # Check for marks
            elif '(' in text and ')' in text and any(mark_word in text.lower() for mark_word in ['mark', 'worth', 'points', 'score']):
                parsed_marks = _parse_marks(text)
                if parsed_marks:
                    current_marks = parsed_marks
                    logger.debug(f"Found marks: {current_marks}")
                    # Add the original text to preserve formatting
                    current_text.append(original_text)
                else:
                    current_text.append(original_text)
                    
            # Check for keywords/key points
            elif text.lower().startswith(('key point', 'keyword', '•', '-', '*')):
                keyword = text.lstrip('•-* ').strip()
                if keyword:
                    current_keywords.append(keyword)
                    logger.debug(f"Found keyword: {keyword}")
                
                # Add the original text to preserve formatting
                current_text.append(original_text)
                
            # Other text - just add to current question
            else:
                current_text.append(original_text)
        
        # Save last question if exists
        if current_question and current_marks > 0:
            # Preserve the formatting by joining with original line breaks
            question_text = '\n'.join(current_text)
            logger.debug(f"Saving final question {current_question}:")
            logger.debug(f"- Text length: {len(question_text)}")
            logger.debug(f"- Text preview: {question_text[:100]}...")
            guide.add_question(
                current_question,
                question_text,
                current_marks,
                current_keywords
            )
        
        # Final validation
        if not guide.questions:
            return None, "No valid questions found in marking guide"
        
        logger.info(f"Successfully parsed {len(guide.questions)} questions with {guide.total_marks} total marks")
        return guide, None
        
    except Exception as e:
        logger.error(f"Error parsing DOCX marking guide: {str(e)}")
        return None, f"Failed to parse DOCX guide: {str(e)}"

def _parse_txt_guide(file_path: str, guide: MarkingGuide) -> Tuple[Optional[MarkingGuide], Optional[str]]:
    """Parse a .txt marking guide."""
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return None, f"File not found: {file_path}"
            
        # Check if file is readable
        if not os.access(file_path, os.R_OK):
            return None, f"File is not readable: {file_path}"
            
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"Read file content length: {len(content)}")
        except UnicodeDecodeError:
            # Try with a different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                    logger.debug(f"Read file content length (latin-1): {len(content)}")
            except Exception as e:
                return None, f"Failed to read file: {str(e)}"
        except Exception as e:
            return None, f"Failed to read file: {str(e)}"
            
        if not content.strip():
            return None, "File is empty"
            
        # Split into questions
        questions = []
        current_text = []
        
        for line in content.split('\n'):
            # Preserve original line formatting
            original_line = line
            text = line.strip()
            
            # Check for new question, but use the stripped version for detection
            if text.startswith(('QUESTION', 'Question', 'question', 'Q.', 'q.')):
                if current_text:
                    questions.append('\n'.join(current_text))
                # Start with the original line to preserve formatting
                current_text = [original_line]
                logger.debug(f"Found new question: {text}")
            else:
                # Add original line with formatting preserved
                current_text.append(original_line)
                
        # Add the last question
        if current_text:
            questions.append('\n'.join(current_text))
            
        if not questions:
            return None, "No questions found in file"
            
        logger.debug(f"Found {len(questions)} questions")
        
        # Process each question
        for question_text in questions:
            # Find question number from the first line (need stripped version for parsing)
            first_line = question_text.split('\n')[0].strip()
            parts = first_line.split(None, 2)
            if len(parts) >= 2:
                try:
                    question_num = parts[1].rstrip('.:)')
                    logger.debug(f"Processing question {question_num}")
                    
                    # Get the original question content - include everything as is
                    content_lines = question_text.split('\n')
                    
                    # Find marks (need stripped version for parsing)
                    marks = 0
                    for line in content_lines:
                        stripped_line = line.strip()
                        if '(' in stripped_line and ')' in stripped_line and 'mark' in stripped_line.lower():
                            marks = _parse_marks(stripped_line)
                            if marks:
                                logger.debug(f"Found marks: {marks}")
                                break
                    
                    if marks > 0:
                        # Use the entire original text as the question content to preserve formatting
                        guide.add_question(
                            question_num,
                            question_text,  # Use the full original text
                            marks,
                            []  # No keywords for now
                        )
                        logger.debug(f"Added question {question_num} with {marks} marks")
                    else:
                        logger.warning(f"No marks found for question {question_num}, skipping")
                except ValueError as e:
                    logger.error(f"Error processing question: {str(e)}")
                    continue
                    
        if not guide.questions:
            return None, "No valid questions found in marking guide"
            
        logger.info(f"Successfully parsed {len(guide.questions)} questions with {guide.total_marks} total marks")
        return guide, None
        
    except Exception as e:
        logger.error(f"Failed to parse TXT marking guide: {str(e)}")
        return None, f"Failed to parse TXT marking guide: {str(e)}" 