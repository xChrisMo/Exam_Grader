# Standardized Error Handling System

This directory contains a comprehensive, standardized error handling system for the Exam Grader application. The system provides consistent error management, tracking, analytics, and user-friendly messaging across the entire application.

## Overview

The standardized error handling system consists of several key components:

- **Application Errors**: Custom exception hierarchy with rich metadata
- **Error Tracking**: Centralized error tracking with analytics
- **Error Mapping**: User-friendly message generation
- **Enhanced Error Handler**: Unified error processing
- **Flask Integration**: Automatic error handling for Flask applications

## Quick Start

### Basic Usage

```python
from src.exceptions.application_errors import ValidationError, ProcessingError
from src.exceptions.enhanced_error_handler import enhanced_error_handler

# Raise a standardized error
raise ValidationError(
    message="Invalid email format",
    user_message="Please enter a valid email address",
    context={"field": "email", "value": "invalid-email"}
)

# Handle errors with enhanced handler
try:
    # Some operation
    pass
except Exception as e:
    enhanced_error_handler.handle_error(
        error=e,
        context={"operation": "user_registration"},
        user_id="user123"
    )
```

### Flask Integration

```python
from flask import Flask
from src.exceptions.flask_error_integration import FlaskErrorIntegration

app = Flask(__name__)
flask_integration = FlaskErrorIntegration(app)
flask_integration.register_error_handlers()

# Use decorators for automatic error handling
from src.exceptions.flask_error_integration import api_error_handler

@app.route('/api/users')
@api_error_handler
def get_users():
    # Your code here - errors are automatically handled
    pass
```

## Components

### 1. Application Errors (`application_errors.py`)

Base `ApplicationError` class and specific error types:

- `ValidationError`: Input validation failures
- `AuthenticationError`: Authentication failures
- `AuthorizationError`: Authorization failures
- `NotFoundError`: Resource not found
- `ProcessingError`: Processing failures
- `ServiceUnavailableError`: Service unavailability
- `RateLimitError`: Rate limiting
- `TimeoutError`: Operation timeouts
- `ConfigurationError`: Configuration issues
- `FileOperationError`: File operation failures
- `DatabaseError`: Database operation failures

#### Features

- Unique error IDs for tracking
- Severity levels (low, medium, high, critical)
- User-friendly messages
- Rich context information
- Original error chaining

### 2. Error Tracking (`error_tracker.py`)

Centralized error tracking with analytics:

```python
from src.exceptions.error_tracker import ErrorTracker, ErrorAnalytics

tracker = ErrorTracker()
analytics = ErrorAnalytics(tracker)

# Track an error
tracker.track_error(error, context={"user_id": "123"})

# Get analytics
report = analytics.generate_report()
trends = analytics.analyze_trends()
recommendations = analytics.get_recommendations()
```

### 3. Error Mapping (`error_mapper.py`)

User-friendly message generation:

```python
from src.exceptions.error_mapper import UserFriendlyErrorMapper, LocalizedErrorMapper

# Basic mapping
mapper = UserFriendlyErrorMapper()
message = mapper.map_error(error)

# Localized mapping
localized_mapper = LocalizedErrorMapper(language="es")
message = localized_mapper.map_error(error)
```

### 4. Enhanced Error Handler (`enhanced_error_handler.py`)

Unified error processing:

```python
from src.exceptions.enhanced_error_handler import enhanced_error_handler

# Handle any error
enhanced_error_handler.handle_error(
    error=exception,
    context={"operation": "file_upload"},
    user_id="user123",
    flash_message=True
)

# Get user-friendly message
message = enhanced_error_handler.get_user_friendly_message(error)

# Create API response
response = enhanced_error_handler.create_error_response(error)
```

### 5. Flask Integration (`flask_error_integration.py`)

Automatic Flask error handling:

```python
# Register error handlers
flask_integration.register_error_handlers()

# Use decorators
@api_error_handler
def api_endpoint():
    pass

@web_error_handler
def web_endpoint():
    pass
```

## Migration Guide

### From Legacy Error Handling

The system maintains backward compatibility with existing `utils/error_handler.py`. New features are automatically used when available:

```python
# This will use enhanced error handling if available
from utils.error_handler import handle_error

handle_error(error, context="user_registration", user_id="123")
```

### Best Practices

1. **Use Specific Error Types**: Choose the most appropriate error type
2. **Provide Context**: Include relevant context information
3. **User-Friendly Messages**: Always provide clear user messages
4. **Error Tracking**: Use the tracking system for analytics
5. **Consistent Handling**: Use the enhanced error handler throughout

### Example Migration

**Before:**
```python
try:
    # Some operation
    pass
except Exception as e:
    logger.error(f"Error in operation: {e}")
    flash("An error occurred", "error")
    return {"error": str(e)}
```

**After:**
```python
try:
    # Some operation
    pass
except Exception as e:
    # Convert to ApplicationError if needed
    if not isinstance(e, ApplicationError):
        e = ProcessingError(
            message=str(e),
            user_message="An error occurred while processing your request",
            original_error=e
        )
    
    # Handle with enhanced system
    return enhanced_error_handler.create_error_response(e)
```

## Configuration

The error handling system can be configured through environment variables or configuration files:

```python
# Error tracking configuration
ERROR_TRACKING_ENABLED = True
MAX_TRACKED_ERRORS = 1000
ERROR_RETENTION_DAYS = 30

# User message configuration
DEFAULT_LANGUAGE = "en"
ENABLE_DETAILED_ERRORS = False  # Set to True for development

# Flask integration configuration
ENABLE_ERROR_PAGES = True
ERROR_TEMPLATE_DIR = "templates/errors"
```

## Testing

Comprehensive tests are available in the `tests/exceptions/` directory:

```bash
# Run all error handling tests
python -m pytest tests/exceptions/

# Run specific test files
python -m pytest tests/exceptions/test_application_errors.py
python -m pytest tests/exceptions/test_error_tracker.py
python -m pytest tests/exceptions/test_error_mapper.py
```

## Performance Considerations

- Error tracking is designed to be lightweight
- Analytics are computed on-demand
- Old errors are automatically cleaned up
- Memory usage is bounded by configuration limits

## Security

- Sensitive information is automatically filtered from error messages
- Error IDs are generated securely
- User messages never expose internal details
- Context information is sanitized

## Monitoring and Alerting

The system provides hooks for monitoring and alerting:

```python
# Get error metrics
metrics = enhanced_error_handler.get_error_metrics()

# Check for critical errors
critical_errors = tracker.get_recent_errors(severity="critical")

# Export metrics for monitoring systems
metrics_data = analytics.export_metrics()
```

## Support

For questions or issues with the error handling system:

1. Check the test files for usage examples
2. Review the docstrings in each module
3. Consult the legacy `utils/error_handler.py` for backward compatibility
4. Create an issue in the project repository