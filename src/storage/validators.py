"""
Data validation utilities for storage operations.
"""
import re
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

class DataValidator:
    """Comprehensive data validator for storage operations."""
    
    # File size limits (in bytes)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_TEXT_LENGTH = 1024 * 1024  # 1MB of text
    MAX_FILENAME_LENGTH = 255
    
    # Content validation patterns
    FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._\-\s()]+$')
    SAFE_STRING_PATTERN = re.compile(r'^[a-zA-Z0-9._\-\s()@]+$')
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate filename for safety and length."""
        if not filename or not isinstance(filename, str):
            raise ValidationError("Filename must be a non-empty string")
        
        if len(filename) > DataValidator.MAX_FILENAME_LENGTH:
            raise ValidationError(f"Filename too long (max {DataValidator.MAX_FILENAME_LENGTH} characters)")
        
        if not DataValidator.FILENAME_PATTERN.match(filename):
            raise ValidationError("Filename contains invalid characters")
        
        # Check for dangerous patterns
        dangerous_patterns = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        for pattern in dangerous_patterns:
            if pattern in filename:
                raise ValidationError(f"Filename contains dangerous pattern: {pattern}")
        
        return True
    
    @staticmethod
    def validate_file_content(content: bytes) -> bool:
        """Validate file content size and basic structure."""
        if not isinstance(content, bytes):
            raise ValidationError("File content must be bytes")
        
        if len(content) == 0:
            raise ValidationError("File content cannot be empty")
        
        if len(content) > DataValidator.MAX_FILE_SIZE:
            raise ValidationError(f"File too large (max {DataValidator.MAX_FILE_SIZE // (1024*1024)}MB)")
        
        return True
    
    @staticmethod
    def validate_text_content(text: str) -> bool:
        """Validate text content for length and safety."""
        if not isinstance(text, str):
            raise ValidationError("Text content must be a string")
        
        if len(text) > DataValidator.MAX_TEXT_LENGTH:
            raise ValidationError(f"Text content too long (max {DataValidator.MAX_TEXT_LENGTH} characters)")
        
        # Check for potentially dangerous content
        if '\x00' in text:  # Null bytes
            raise ValidationError("Text contains null bytes")
        
        return True
    
    @staticmethod
    def validate_json_data(data: Any) -> bool:
        """Validate that data can be safely serialized to JSON."""
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            if len(json_str) > DataValidator.MAX_TEXT_LENGTH:
                raise ValidationError("JSON data too large when serialized")
            
            # Try to parse it back to ensure it's valid
            json.loads(json_str)
            return True
        except (TypeError, ValueError) as e:
            raise ValidationError(f"Data is not JSON serializable: {str(e)}")
    
    @staticmethod
    def validate_guide_data(guide_data: Dict[str, Any]) -> bool:
        """Validate marking guide data structure."""
        required_fields = ['filename', 'questions', 'total_marks']
        
        if not isinstance(guide_data, dict):
            raise ValidationError("Guide data must be a dictionary")
        
        # Check required fields
        for field in required_fields:
            if field not in guide_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate filename
        DataValidator.validate_filename(guide_data['filename'])
        
        # Validate questions
        questions = guide_data['questions']
        if not isinstance(questions, list):
            raise ValidationError("Questions must be a list")
        
        for i, question in enumerate(questions):
            if not isinstance(question, dict):
                raise ValidationError(f"Question {i} must be a dictionary")
            
            if 'text' not in question:
                raise ValidationError(f"Question {i} missing 'text' field")
            
            if 'marks' not in question:
                raise ValidationError(f"Question {i} missing 'marks' field")
            
            if not isinstance(question['marks'], (int, float)):
                raise ValidationError(f"Question {i} marks must be a number")
            
            if question['marks'] < 0:
                raise ValidationError(f"Question {i} marks cannot be negative")
        
        # Validate total marks
        total_marks = guide_data['total_marks']
        if not isinstance(total_marks, (int, float)):
            raise ValidationError("Total marks must be a number")
        
        if total_marks < 0:
            raise ValidationError("Total marks cannot be negative")
        
        # Validate raw content if present
        if 'raw_content' in guide_data:
            DataValidator.validate_text_content(guide_data['raw_content'])
        
        return True
    
    @staticmethod
    def validate_submission_data(submission_data: Dict[str, Any]) -> bool:
        """Validate submission data structure."""
        required_fields = ['filename', 'answers', 'raw_text']
        
        if not isinstance(submission_data, dict):
            raise ValidationError("Submission data must be a dictionary")
        
        # Check required fields
        for field in required_fields:
            if field not in submission_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate filename
        DataValidator.validate_filename(submission_data['filename'])
        
        # Validate answers
        answers = submission_data['answers']
        if not isinstance(answers, dict):
            raise ValidationError("Answers must be a dictionary")
        
        # Validate each answer
        for key, value in answers.items():
            if not isinstance(key, str):
                raise ValidationError(f"Answer key must be string, got {type(key)}")
            
            if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                raise ValidationError(f"Answer value for '{key}' has invalid type: {type(value)}")
        
        # Validate raw text
        DataValidator.validate_text_content(submission_data['raw_text'])
        
        return True
    
    @staticmethod
    def validate_results_data(results_data: Dict[str, Any]) -> bool:
        """Validate grading results data structure."""
        required_fields = ['submission_id', 'score', 'total_score']
        
        if not isinstance(results_data, dict):
            raise ValidationError("Results data must be a dictionary")
        
        # Check required fields
        for field in required_fields:
            if field not in results_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate submission ID
        submission_id = results_data['submission_id']
        if not isinstance(submission_id, str) or not submission_id.strip():
            raise ValidationError("Submission ID must be a non-empty string")
        
        # Validate scores
        score = results_data['score']
        total_score = results_data['total_score']
        
        if not isinstance(score, (int, float)):
            raise ValidationError("Score must be a number")
        
        if not isinstance(total_score, (int, float)):
            raise ValidationError("Total score must be a number")
        
        if score < 0:
            raise ValidationError("Score cannot be negative")
        
        if total_score <= 0:
            raise ValidationError("Total score must be positive")
        
        if score > total_score:
            raise ValidationError("Score cannot exceed total score")
        
        # Validate question scores if present
        if 'question_scores' in results_data:
            question_scores = results_data['question_scores']
            if not isinstance(question_scores, list):
                raise ValidationError("Question scores must be a list")
            
            for i, q_score in enumerate(question_scores):
                if not isinstance(q_score, dict):
                    raise ValidationError(f"Question score {i} must be a dictionary")
                
                if 'score' not in q_score or 'max_score' not in q_score:
                    raise ValidationError(f"Question score {i} missing required fields")
                
                if not isinstance(q_score['score'], (int, float)):
                    raise ValidationError(f"Question {i} score must be a number")
                
                if not isinstance(q_score['max_score'], (int, float)):
                    raise ValidationError(f"Question {i} max score must be a number")
        
        return True
    
    @staticmethod
    def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input for safe storage."""
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        # Apply length limit
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    @staticmethod
    def validate_storage_metadata(metadata: Dict[str, Any]) -> bool:
        """Validate storage metadata structure."""
        if not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a dictionary")
        
        # Validate timestamp if present
        if 'timestamp' in metadata:
            timestamp = metadata['timestamp']
            if isinstance(timestamp, str):
                try:
                    datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except ValueError:
                    raise ValidationError("Invalid timestamp format")
            elif not isinstance(timestamp, (int, float)):
                raise ValidationError("Timestamp must be string or number")
        
        # Validate other common metadata fields
        string_fields = ['created_by', 'updated_by', 'description', 'version']
        for field in string_fields:
            if field in metadata and not isinstance(metadata[field], str):
                raise ValidationError(f"Metadata field '{field}' must be a string")
        
        return True

def validate_and_sanitize_input(data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
    """
    Validate and sanitize input data based on type.
    
    Args:
        data: Input data to validate
        data_type: Type of data ('guide', 'submission', 'results', 'metadata')
        
    Returns:
        Sanitized and validated data
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # First validate JSON serializability
        DataValidator.validate_json_data(data)
        
        # Type-specific validation
        if data_type == 'guide':
            DataValidator.validate_guide_data(data)
        elif data_type == 'submission':
            DataValidator.validate_submission_data(data)
        elif data_type == 'results':
            DataValidator.validate_results_data(data)
        elif data_type == 'metadata':
            DataValidator.validate_storage_metadata(data)
        else:
            raise ValidationError(f"Unknown data type: {data_type}")
        
        # Sanitize string fields
        sanitized_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized_data[key] = DataValidator.sanitize_string(value)
            else:
                sanitized_data[key] = value
        
        logger.debug(f"Successfully validated and sanitized {data_type} data")
        return sanitized_data
        
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Unexpected validation error: {str(e)}")
