# Exam Grader Backend API Reference

## Overview

The Exam Grader backend is a Python-based application that provides document parsing, OCR processing, LLM-powered grading, and result storage capabilities. The web interface has been removed, leaving only the core backend functionality.

## Core Architecture

### Main Components

1. **Configuration Management** (`src/config/`)
2. **Document Parsing** (`src/parsing/`)
3. **Core Services** (`src/services/`)
4. **Storage Systems** (`src/storage/`)
5. **Utilities** (`utils/`)

---

## 📁 Configuration Management

### ConfigManager Class (`src/config/config_manager.py`)

**Purpose**: Centralized configuration management using singleton pattern

**Key Methods**:
- `__init__()` - Initialize configuration from environment variables
- `_create_directories()` - Create required directories
- `_validate_config()` - Validate configuration settings

**Configuration Properties**:
- `debug: bool` - Debug mode flag
- `log_level: str` - Logging level
- `temp_dir: str` - Temporary files directory
- `output_dir: str` - Output files directory
- `max_file_size_mb: int` - Maximum file size limit
- `supported_formats: List[str]` - Supported file formats
- `ocr_confidence_threshold: float` - OCR confidence threshold
- `handwriting_ocr_api_key: str` - OCR API key

---

## 📄 Document Parsing

### parse_student_submission (`src/parsing/parse_submission.py`)

**Purpose**: Main entry point for parsing student submissions

**Function Signature**:
```python
def parse_student_submission(file_path: str) -> Tuple[Dict[str, str], Optional[str], Optional[str]]
```

**Parameters**:
- `file_path: str` - Path to the submission file

**Returns**:
- `Dict[str, str]` - Contains raw text content
- `Optional[str]` - Raw text content (same as dict)
- `Optional[str]` - Error message if failed

**Supported Formats**:
- PDF documents
- DOCX documents
- Images (JPG, JPEG, PNG, TIFF, BMP, GIF) - processed with OCR
- Plain text files

### DocumentParser Class (`src/parsing/parse_submission.py`)

**Key Methods**:
- `get_file_type(file_path: str) -> str` - Detect file MIME type
- `extract_text_from_pdf(file_path: str) -> str` - Extract text from PDF
- `extract_text_from_docx(file_path: str) -> str` - Extract text from DOCX
- `extract_text_from_image(file_path: str) -> str` - Extract text using OCR
- `extract_text_from_txt(file_path: str) -> str` - Read plain text file

### parse_marking_guide (`src/parsing/parse_guide.py`)

**Purpose**: Parse marking guide documents

**Function Signature**:
```python
def parse_marking_guide(file_path: str) -> Tuple[Optional[MarkingGuide], Optional[str]]
```

**Parameters**:
- `file_path: str` - Path to the marking guide file

**Returns**:
- `Optional[MarkingGuide]` - MarkingGuide object with raw content
- `Optional[str]` - Error message if failed

**Supported Formats**:
- DOCX documents
- Plain text files

---

## 🔧 Core Services

### LLMService Class (`src/services/llm_service.py`)

**Purpose**: Interface with DeepSeek API for AI-powered grading

**Constructor Parameters**:
- `api_key: Optional[str]` - DeepSeek API key
- `base_url: str` - API base URL (default: "https://api.deepseek.com/v1")
- `model: str` - Model name (default: "deepseek-chat")
- `temperature: float` - Response randomness (default: 0.1)
- `max_retries: int` - Maximum retry attempts (default: 2)
- `timeout: float` - Request timeout (default: 30.0)
- `max_tokens: int` - Maximum response tokens (default: 1000)

**Key Methods**:
- `compare_answers(student_answer: str, expected_answer: str, question: str, max_marks: int) -> Tuple[Dict, Optional[str]]`
- `grade_submission(marking_guide: str, student_submission: str) -> Tuple[Dict, Optional[str]]`
- `_make_api_request(messages: List[Dict], **kwargs) -> Tuple[Dict, Optional[str]]`
- `test_connection() -> Tuple[bool, str]`

### MappingService Class (`src/services/mapping_service.py`)

**Purpose**: Map student submissions to marking guide criteria

**Constructor Parameters**:
- `llm_service: Optional[LLMService]` - LLM service instance

**Key Methods**:
- `map_submission_to_guide(marking_guide_content: str, student_submission_content: str, num_questions: int = 1) -> Tuple[Dict, Optional[str]]`

**Returns Mapping Result**:
```python
{
    "status": "success",
    "message": "Content mapped successfully",
    "mappings": [...],  # List of question-answer mappings
    "metadata": {...},  # Mapping metadata
    "raw_guide_content": str,
    "raw_submission_content": str,
    "overall_grade": {...}  # Overall grading results
}
```

### GradingService Class (`src/services/grading_service.py`)

**Purpose**: Grade student submissions against marking guides

**Constructor Parameters**:
- `llm_service: Optional[LLMService]` - LLM service instance
- `mapping_service: Optional[MappingService]` - Mapping service instance

**Key Methods**:
- `grade_submission(marking_guide_content: str, student_submission_content: str) -> Tuple[Dict, Optional[str]]`

**Returns Grading Result**:
```python
{
    "status": "success",
    "overall_score": float,      # Sum of all points earned
    "max_possible_score": float, # Maximum possible points
    "normalized_score": float,   # Score normalized to 100
    "percent_score": float,      # Percentage score
    "letter_grade": str,         # Letter grade (A, B, C, D, F)
    "criteria_scores": [...],    # Individual criterion scores
    "detailed_feedback": {...},  # Strengths, weaknesses, suggestions
    "metadata": {...}            # Grading metadata
}
```

### OCRService Class (`src/services/ocr_service.py`)

**Purpose**: Extract text from images using HandwritingOCR API

**Constructor Parameters**:
- `api_key: Optional[str]` - HandwritingOCR API key
- `base_url: Optional[str]` - API base URL

**Key Methods**:
- `extract_text_from_image(file: Union[str, Path, BinaryIO]) -> str`
- `_upload_document(file: Union[str, Path, BinaryIO]) -> str`
- `_get_document_status(document_id: str) -> Dict`
- `_get_document_text(document_id: str) -> str`

---

## 💾 Storage Systems

### BaseStorage Class (`src/storage/base_storage.py`)

**Purpose**: Base class for all storage implementations

**Key Methods**:
- `store(file_content: bytes, filename: str, data: Dict) -> str`
- `get(file_content: bytes) -> Optional[Tuple[Dict, str]]`
- `exists(file_content: bytes) -> bool`
- `delete(file_content: bytes) -> bool`

### GuideStorage Class (`src/storage/guide_storage.py`)

**Purpose**: Store and retrieve parsed marking guides

**Key Methods**:
- `store_guide(file_content: bytes, filename: str, guide_data: Dict) -> str`
- `get_guide(file_content: bytes) -> Optional[Tuple[Dict, str]]`

### SubmissionStorage Class (`src/storage/submission_storage.py`)

**Purpose**: Store and retrieve parsed submission results

**Key Methods**:
- `store_results(file_content: bytes, filename: str, results: Dict, raw_text: str) -> str`
- `get_results(file_content: bytes) -> Optional[Tuple[Dict, str, str]]`
- `cleanup_expired() -> int`

### ResultsStorage Class (`src/storage/results_storage.py`)

**Purpose**: Store grading and mapping results

**Key Methods**:
- `store_mapping_result(mapping_result: Dict) -> str`
- `store_grading_result(grading_result: Dict) -> str`
- `store_batch_results(batch_type: str, results: List) -> str`
- `get_mapping_result(result_id: str) -> Optional[Dict]`
- `get_grading_result(result_id: str) -> Optional[Dict]`
- `get_batch_results(batch_id: str) -> Optional[Dict]`
- `list_results(result_type: str = 'all') -> List[Dict]`

---

## 🛠️ Utilities

### Logger (`utils/logger.py`)

**Purpose**: Centralized logging configuration

**Functions**:
- `setup_logger(name: str) -> logging.Logger`

### Cache (`utils/cache.py`)

**Purpose**: File-based caching system

**Key Methods**:
- `set(key: str, value: Any, ttl: Optional[int] = None) -> bool`
- `get(key: str) -> Any`
- `delete(key: str) -> bool`
- `exists(key: str) -> bool`
- `clear() -> bool`

---

## 🚀 Usage Examples

### Basic Document Parsing
```python
from src.parsing.parse_submission import parse_student_submission

# Parse a student submission
result, raw_text, error = parse_student_submission("exam.pdf")
if error:
    print(f"Error: {error}")
else:
    print(f"Extracted text: {raw_text}")
```

### Complete Grading Workflow
```python
from src.parsing.parse_submission import parse_student_submission
from src.parsing.parse_guide import parse_marking_guide
from src.services.llm_service import LLMService
from src.services.mapping_service import MappingService
from src.services.grading_service import GradingService

# Initialize services
llm_service = LLMService()
mapping_service = MappingService(llm_service)
grading_service = GradingService(llm_service, mapping_service)

# Parse documents
guide, guide_error = parse_marking_guide("marking_guide.docx")
submission, raw_text, sub_error = parse_student_submission("student_exam.pdf")

if not guide_error and not sub_error:
    # Grade the submission
    result, error = grading_service.grade_submission(
        guide.raw_content, 
        raw_text
    )
    
    if not error:
        print(f"Score: {result['percent_score']}%")
        print(f"Grade: {result['letter_grade']}")
```

---

## 📋 Entry Points

### Main Application (`run_app.py`)
- Core application without web interface
- Validates setup and displays usage information
- Entry point for programmatic usage

### Validation Script (`validate_setup.py`)
- Validates environment configuration
- Checks dependencies and API connectivity
- Verifies directory structure

---

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Core settings
DEBUG=False
LOG_LEVEL=INFO

# Directory settings
TEMP_DIR=temp
OUTPUT_DIR=output

# File processing
MAX_FILE_SIZE_MB=10
SUPPORTED_FORMATS=.txt,.docx,.pdf,.jpg,.jpeg,.png,.tiff,.bmp,.gif

# OCR settings
OCR_CONFIDENCE_THRESHOLD=0.7
OCR_LANGUAGE=en
HANDWRITING_OCR_API_KEY=your_api_key_here

# LLM settings (handled by LLMService)
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

---

## 📦 Dependencies

### Core Dependencies
- `requests>=2.31.0` - HTTP requests
- `python-dotenv>=1.0.1` - Environment variable loading
- `numpy>=1.26.4` - Numerical operations
- `pandas>=2.2.0` - Data manipulation
- `openpyxl>=3.1.2` - Excel file support
- `openai>=1.12.0` - OpenAI-compatible API client
- `validators>=0.22.0` - Input validation
- `packaging>=23.0` - Version handling

### Document Processing
- `PyMuPDF>=1.23.8` - PDF processing
- `python-docx>=1.1.0` - DOCX processing
- `Pillow>=10.2.0` - Image processing

### Text Processing
- `nltk>=3.8.1` - Natural language processing
- `scikit-learn>=1.4.0` - Machine learning utilities

---

This backend provides a complete document processing and grading system that can be integrated into any application or used as a standalone service.
