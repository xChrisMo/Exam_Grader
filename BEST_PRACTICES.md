# 🏆 Best Practices Guide

## Overview
This guide documents the best practices implemented in the Exam Grader application during the comprehensive code analysis and issue resolution. These practices can be applied to future development projects.

## 🔧 Code Quality Best Practices

### 1. Type Hints and Documentation
```python
# ✅ Good: Comprehensive type hints and docstrings
def process_file(file_path: str, max_size_mb: int = 50) -> Tuple[bool, Optional[str]]:
    """
    Process uploaded file with validation.
    
    Args:
        file_path: Path to the file to process
        max_size_mb: Maximum allowed file size in MB
        
    Returns:
        Tuple of (success, error_message)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file size exceeds limit
    """
    pass

# ❌ Bad: No type hints or documentation
def process_file(file_path, max_size_mb=50):
    pass
```

### 2. Error Handling Patterns
```python
# ✅ Good: Specific exception handling with context
try:
    result = risky_operation()
except FileNotFoundError as e:
    error_id = ErrorHandler.log_error(e, 'file_not_found', {'file_path': file_path})
    return ErrorHandler.create_error_response('file_not_found', {'error_id': error_id})
except PermissionError as e:
    error_id = ErrorHandler.log_error(e, 'access_denied', {'file_path': file_path})
    return ErrorHandler.create_error_response('access_denied', {'error_id': error_id})

# ❌ Bad: Generic exception handling
try:
    result = risky_operation()
except Exception as e:
    return {'error': str(e)}
```

### 3. Logging Standards
```python
# ✅ Good: Structured logging with context
logger.info(f"Processing file: {filename}", extra={
    'file_size': file_size,
    'user_id': user_id,
    'operation': 'file_upload'
})

# ❌ Bad: Unstructured logging
print(f"Processing {filename}")
```

## 🔒 Security Best Practices

### 1. Input Validation and Sanitization
```python
# ✅ Good: Comprehensive input validation
def upload_file(file_data: bytes, filename: str) -> Tuple[bool, str]:
    # Sanitize filename
    safe_filename = InputSanitizer.sanitize_filename(filename)
    
    # Validate file content
    is_valid, error_msg = validate_file_upload(file_data, filename, ALLOWED_TYPES)
    if not is_valid:
        return False, error_msg
    
    # Check for malicious content
    attacks = InputSanitizer.detect_encoding_attacks(file_data.decode('utf-8', errors='ignore'))
    if attacks:
        return False, f"Security threats detected: {', '.join(attacks)}"
    
    return True, "File validated successfully"

# ❌ Bad: No validation
def upload_file(file_data, filename):
    with open(filename, 'wb') as f:
        f.write(file_data)
```

### 2. Rate Limiting Implementation
```python
# ✅ Good: Granular rate limiting
@app.route('/api/upload', methods=['POST'])
@rate_limit_with_whitelist('upload_submission')  # 20 uploads per 5 minutes
def upload_endpoint():
    pass

@app.route('/api/process', methods=['POST'])
@rate_limit_with_whitelist('process_grading')    # 10 processes per minute
def process_endpoint():
    pass

# ❌ Bad: No rate limiting
@app.route('/api/upload', methods=['POST'])
def upload_endpoint():
    pass
```

### 3. CSRF Protection
```python
# ✅ Good: CSRF protection on all forms
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

# In templates
<form method="POST">
    {{ csrf_token() }}
    <!-- form fields -->
</form>

# ❌ Bad: No CSRF protection
<form method="POST">
    <!-- form fields -->
</form>
```

## ⚡ Performance Best Practices

### 1. Caching Strategy
```python
# ✅ Good: Multi-level caching with TTL
from utils.cache import Cache

cache = Cache()

def get_expensive_data(key: str) -> Any:
    # Try cache first
    cached_result = cache.get(key)
    if cached_result is not None:
        return cached_result
    
    # Compute expensive operation
    result = expensive_computation()
    
    # Cache with appropriate TTL
    cache.set(key, result, ttl=3600)  # 1 hour
    return result

# ❌ Bad: No caching
def get_expensive_data(key: str) -> Any:
    return expensive_computation()
```

### 2. Memory-Efficient File Processing
```python
# ✅ Good: Streaming for large files
def process_large_file(file_path: str) -> None:
    file_info = FileProcessor.get_file_info(file_path)
    
    if file_info.get('size_mb', 0) > 10:
        # Use memory-efficient processing
        with MemoryEfficientFileHandler(max_memory_usage_mb=50) as handler:
            file_handle = handler.open_file(file_path, 'rb')
            for chunk in FileProcessor.stream_file_chunks(file_path):
                process_chunk(chunk)
            handler.close_file(file_path)
    else:
        # Normal processing for small files
        with open(file_path, 'rb') as f:
            process_chunk(f.read())

# ❌ Bad: Loading entire file into memory
def process_large_file(file_path: str) -> None:
    with open(file_path, 'rb') as f:
        data = f.read()  # Could cause memory issues
        process_chunk(data)
```

### 3. Database Query Optimization
```python
# ✅ Good: Efficient queries with pagination
def get_submissions(page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    offset = (page - 1) * per_page
    
    # Use efficient query with LIMIT/OFFSET
    submissions = db.session.query(Submission)\
        .options(selectinload(Submission.results))\
        .limit(per_page)\
        .offset(offset)\
        .all()
    
    total = db.session.query(Submission).count()
    
    return {
        'submissions': submissions,
        'total': total,
        'page': page,
        'per_page': per_page
    }

# ❌ Bad: Loading all records
def get_submissions():
    return db.session.query(Submission).all()  # Could be thousands of records
```

## 📱 User Experience Best Practices

### 1. Progress Tracking
```python
# ✅ Good: Real-time progress updates
def process_submissions(submission_ids: List[str]) -> str:
    operation_id = str(uuid.uuid4())
    
    # Start progress tracking
    loading_manager.start_operation(
        operation_id,
        "Processing Submissions",
        len(submission_ids),
        "Starting submission processing..."
    )
    
    for i, submission_id in enumerate(submission_ids):
        # Update progress
        loading_manager.update_progress(
            operation_id,
            current_step=i + 1,
            message=f"Processing submission {i + 1} of {len(submission_ids)}",
            state=LoadingState.PROCESSING
        )
        
        process_submission(submission_id)
    
    # Complete operation
    loading_manager.complete_operation(operation_id, "All submissions processed")
    return operation_id

# ❌ Bad: No progress feedback
def process_submissions(submission_ids: List[str]) -> None:
    for submission_id in submission_ids:
        process_submission(submission_id)
```

### 2. User-Friendly Error Messages
```python
# ✅ Good: Helpful error messages with suggestions
def handle_upload_error(error: Exception, filename: str) -> Dict[str, Any]:
    error_type, context = ErrorHandler.handle_file_error(error, filename)
    error_info = ErrorHandler.get_user_friendly_error(error_type, context)
    
    return {
        'success': False,
        'message': error_info['message'],
        'suggestions': error_info['suggestions'][:3],  # Top 3 suggestions
        'error_id': ErrorHandler.log_error(error, error_type, context)
    }

# ❌ Bad: Technical error messages
def handle_upload_error(error: Exception, filename: str) -> Dict[str, Any]:
    return {
        'success': False,
        'message': str(error)  # Technical jargon
    }
```

## 🏗️ Architecture Best Practices

### 1. Separation of Concerns
```python
# ✅ Good: Separated utilities
# utils/file_processor.py - File operations
# utils/cache.py - Caching logic
# utils/rate_limiter.py - Rate limiting
# utils/input_sanitizer.py - Input validation
# utils/error_handler.py - Error management

# webapp/exam_grader_app.py - Web interface only
from utils.file_processor import FileProcessor
from utils.cache import Cache
from utils.rate_limiter import rate_limit_with_whitelist

# ❌ Bad: Everything in one file
# All logic mixed in the main application file
```

### 2. Configuration Management
```python
# ✅ Good: Centralized configuration with fallbacks
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', '16'))
    CACHE_TTL = int(os.environ.get('CACHE_TTL', '3600'))
    
    @staticmethod
    def init_app(app):
        pass

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

# ❌ Bad: Hardcoded values
SECRET_KEY = 'hardcoded-secret'
MAX_FILE_SIZE = 16777216  # Magic number
```

### 3. Dependency Injection
```python
# ✅ Good: Dependency injection for testability
class FileUploadService:
    def __init__(self, file_processor: FileProcessor, cache: Cache):
        self.file_processor = file_processor
        self.cache = cache
    
    def upload_file(self, file_data: bytes, filename: str) -> bool:
        # Use injected dependencies
        is_valid = self.file_processor.validate_file(file_data, filename)
        if is_valid:
            self.cache.set(f"file:{filename}", file_data)
        return is_valid

# ❌ Bad: Hard dependencies
class FileUploadService:
    def upload_file(self, file_data: bytes, filename: str) -> bool:
        # Hard dependency on global objects
        is_valid = FileProcessor().validate_file(file_data, filename)
        if is_valid:
            Cache().set(f"file:{filename}", file_data)
        return is_valid
```

## 🧪 Testing Best Practices

### 1. Comprehensive Test Coverage
```python
# ✅ Good: Multiple test types
class TestFileProcessor:
    def test_file_validation_success(self):
        """Test successful file validation."""
        processor = FileProcessor()
        result = processor.validate_file(b"valid content", "test.txt")
        assert result is True
    
    def test_file_validation_failure(self):
        """Test file validation with invalid content."""
        processor = FileProcessor()
        result = processor.validate_file(b"", "test.exe")
        assert result is False
    
    def test_large_file_processing(self):
        """Test memory-efficient processing of large files."""
        # Integration test with actual large file
        pass
    
    def test_file_processor_error_handling(self):
        """Test error handling in file processor."""
        # Test various error conditions
        pass

# ❌ Bad: Minimal testing
def test_file_processor():
    assert FileProcessor().validate_file(b"test", "test.txt")
```

### 2. Mock External Dependencies
```python
# ✅ Good: Proper mocking
@patch('utils.file_processor.os.path.getsize')
def test_file_size_validation(mock_getsize):
    mock_getsize.return_value = 1024 * 1024  # 1MB
    
    processor = FileProcessor()
    result = processor.validate_file_size('/fake/path', max_size_mb=2)
    assert result is True

# ❌ Bad: Testing with real files
def test_file_size_validation():
    # Creates dependency on actual file system
    with open('test_file.txt', 'w') as f:
        f.write('test content')
    
    processor = FileProcessor()
    result = processor.validate_file_size('test_file.txt', max_size_mb=2)
    assert result is True
```

## 📊 Monitoring Best Practices

### 1. Structured Logging
```python
# ✅ Good: Structured logging with metrics
import structlog

logger = structlog.get_logger()

def process_request(request_id: str, user_id: str):
    logger.info(
        "Processing request",
        request_id=request_id,
        user_id=user_id,
        operation="file_upload",
        timestamp=datetime.utcnow().isoformat()
    )

# ❌ Bad: Unstructured logging
def process_request(request_id, user_id):
    print(f"Processing request {request_id} for user {user_id}")
```

### 2. Health Checks
```python
# ✅ Good: Comprehensive health checks
@app.route('/health')
def health_check():
    """Comprehensive health check endpoint."""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {}
    }
    
    # Check database
    try:
        db.session.execute('SELECT 1')
        health_status['services']['database'] = 'healthy'
    except Exception as e:
        health_status['services']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check cache
    try:
        cache = Cache()
        cache.set('health_check', 'ok', ttl=60)
        health_status['services']['cache'] = 'healthy'
    except Exception as e:
        health_status['services']['cache'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code

# ❌ Bad: Simple health check
@app.route('/health')
def health_check():
    return 'OK'
```

## 🔄 Deployment Best Practices

### 1. Environment-Specific Configuration
```python
# ✅ Good: Environment-specific settings
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

config_name = os.getenv('FLASK_ENV', 'default')
app.config.from_object(config[config_name])

# ❌ Bad: Single configuration for all environments
app.config['DEBUG'] = True  # Always debug mode
```

### 2. Graceful Shutdown
```python
# ✅ Good: Graceful shutdown handling
import signal
import sys

def signal_handler(sig, frame):
    logger.info('Graceful shutdown initiated')
    
    # Close database connections
    db.session.close()
    
    # Clear cache
    cache.cleanup()
    
    # Stop background tasks
    loading_manager.cleanup_old_operations()
    
    logger.info('Shutdown complete')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ❌ Bad: Abrupt shutdown
# No cleanup on shutdown
```

## 📚 Documentation Best Practices

### 1. API Documentation
```python
# ✅ Good: Comprehensive API documentation
@app.route('/api/upload', methods=['POST'])
@rate_limit_with_whitelist('upload_submission')
def upload_submission():
    """
    Upload student submission for grading.
    
    Request:
        - Content-Type: multipart/form-data
        - Files: submission_file (required)
        - Max file size: 50MB
        - Supported formats: .txt, .pdf, .docx, .jpg, .png
    
    Response:
        200: Success
        {
            "success": true,
            "submission_id": "uuid",
            "message": "File uploaded successfully"
        }
        
        400: Bad Request
        {
            "success": false,
            "error": "File validation failed",
            "suggestions": ["Use supported file format", "Check file size"]
        }
        
        429: Rate Limit Exceeded
        {
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please wait before trying again."
        }
    
    Rate Limits:
        - 20 uploads per 5 minutes per IP
        - Whitelisted IPs bypass rate limits
    
    Security:
        - CSRF protection enabled
        - File content validation
        - Filename sanitization
        - Malware scanning
    """
    pass

# ❌ Bad: No documentation
@app.route('/api/upload', methods=['POST'])
def upload_submission():
    pass
```

These best practices ensure maintainable, secure, performant, and user-friendly applications. They should be followed in all future development work.
