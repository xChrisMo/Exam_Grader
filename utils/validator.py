"""
Validation utilities for the Exam Grader application.
"""
from typing import List, Dict, Any, Union
import os
import re
from utils.logger import Logger

logger = Logger().get_logger()

class Validator:
    @staticmethod
    def validate_file_path(file_path: str) -> bool:
        """Validate file path exists and is accessible."""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False
        if not os.access(file_path, os.R_OK):
            logger.error(f"File not readable: {file_path}")
            return False
        return True
    
    @staticmethod
    def validate_file_extension(file_path: str, allowed_extensions: List[str]) -> bool:
        """Validate file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in allowed_extensions:
            logger.error(f"Invalid file extension: {ext}")
            return False
        return True
    
    @staticmethod
    def validate_answer_format(answer: Dict[str, Any]) -> bool:
        """Validate answer format with comprehensive checks."""
        required_fields = {
            'question_number': (int, 'Question number must be an integer'),
            'question_text': (str, 'Question text must be a string'),
            'student_answer': (str, 'Student answer must be a string'),
            'model_answer': (str, 'Model answer must be a string'),
            'max_marks': (Union[int, float], 'Max marks must be a number')
        }
        
        # Check required fields
        for field, (field_type, error_msg) in required_fields.items():
            if field not in answer:
                logger.error(f"Missing required field: {field}")
                return False
            if not isinstance(answer[field], field_type):
                logger.error(f"{error_msg}: {field}")
                return False
        
        # Validate question number
        if answer['question_number'] <= 0:
            logger.error("Question number must be positive")
            return False
        
        # Validate max marks
        if answer['max_marks'] <= 0:
            logger.error("Max marks must be positive")
            return False
        
        # Validate text content
        if not answer['question_text'].strip():
            logger.error("Question text cannot be empty")
            return False
        if not answer['student_answer'].strip():
            logger.error("Student answer cannot be empty")
            return False
        if not answer['model_answer'].strip():
            logger.error("Model answer cannot be empty")
            return False
        
        return True
    
    @staticmethod
    def validate_marking_guide_question(question: Dict[str, Any]) -> bool:
        """Validate a marking guide question format."""
        required_fields = {
            'question_number': (int, 'Question number must be an integer'),
            'question_text': (str, 'Question text must be a string'),
            'max_marks': (Union[int, float], 'Max marks must be a number'),
            'keywords': (list, 'Keywords must be a list'),
            'required_elements': (list, 'Required elements must be a list')
        }
        
        # Check required fields
        for field, (field_type, error_msg) in required_fields.items():
            if field not in question:
                logger.error(f"Missing required field in question: {field}")
                return False
            if not isinstance(question[field], field_type):
                logger.error(f"{error_msg}: got {type(question[field])}")
                return False
        
        # Validate question number
        if question['question_number'] <= 0:
            logger.error("Question number must be positive")
            return False
        
        # Validate max marks
        if question['max_marks'] <= 0:
            logger.error("Max marks must be positive")
            return False
        
        # Validate text content
        if not question['question_text'].strip():
            logger.error("Question text cannot be empty")
            return False
        
        return True
    
    @staticmethod
    def validate_marking_guide_format(guide: Dict[str, Any]) -> bool:
        """Validate marking guide format with comprehensive checks."""
        logger.debug(f"Validating marking guide format. Guide data: {guide}")
        
        required_fields = {
            'questions': (list, 'Questions must be a list'),
            'total_marks': (Union[int, float], 'Total marks must be a number')
        }
        
        # Check required fields
        for field, (field_type, error_msg) in required_fields.items():
            if field not in guide:
                logger.error(f"Missing required field in marking guide: {field}")
                return False
            logger.debug(f"Checking field {field}, type: {type(guide[field])}, expected: {field_type}")
            if not isinstance(guide[field], field_type):
                logger.error(f"{error_msg}: {field}")
                return False
        
        # Validate total marks
        if guide['total_marks'] <= 0:
            logger.error("Total marks must be positive")
            return False
        
        # Validate questions
        if not guide['questions']:
            logger.error("Questions list cannot be empty")
            return False
        
        # Validate each question
        for question in guide['questions']:
            if not Validator.validate_marking_guide_question(question):
                return False
        
        # Validate marks sum
        total_question_marks = sum(q['max_marks'] for q in guide['questions'])
        if abs(total_question_marks - guide['total_marks']) > 0.01:  # Allow for floating point imprecision
            logger.error(f"Sum of question marks ({total_question_marks}) does not match total marks ({guide['total_marks']})")
            return False
        
        # Log successful validation
        logger.debug("Marking guide format validation successful")
        return True
    
    @staticmethod
    def validate_submission_format(submission: Dict[str, Any]) -> bool:
        """Validate submission format with comprehensive checks."""
        required_fields = {
            'student_id': (str, 'Student ID must be a string'),
            'answers': (list, 'Answers must be a list')
        }
        
        # Check required fields
        for field, (field_type, error_msg) in required_fields.items():
            if field not in submission:
                logger.error(f"Missing required field in submission: {field}")
                return False
            if not isinstance(submission[field], field_type):
                logger.error(f"{error_msg}: {field}")
                return False
        
        # Validate student ID format
        if not re.match(r'^[A-Za-z0-9]+$', submission['student_id']):
            logger.error("Student ID must contain only alphanumeric characters")
            return False
        
        # Validate answers
        if not submission['answers']:
            logger.error("Answers list cannot be empty")
            return False
        
        # Validate each answer
        for answer in submission['answers']:
            if not Validator.validate_answer_format(answer):
                return False
        
        return True
    
    @staticmethod
    def validate_grading_result(result: Dict[str, Any]) -> bool:
        """Validate grading result format."""
        required_fields = {
            'score': (Union[int, float], 'Score must be a number'),
            'feedback': (str, 'Feedback must be a string'),
            'grading_confidence': (float, 'Grading confidence must be a float')
        }
        
        # Check required fields
        for field, (field_type, error_msg) in required_fields.items():
            if field not in result:
                logger.error(f"Missing required field in grading result: {field}")
                return False
            if not isinstance(result[field], field_type):
                logger.error(f"{error_msg}: {field}")
                return False
        
        # Validate score range
        if result['score'] < 0:
            logger.error("Score cannot be negative")
            return False
        
        # Validate confidence range
        if not 0 <= result['grading_confidence'] <= 1:
            logger.error("Grading confidence must be between 0 and 1")
            return False
        
        return True 