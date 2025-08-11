# Timeout Fix for AI Grading Operations

## Problem Solved
The application was timing out during AI grading operations because:
- Flask's default request timeout was too short for AI processing
- LLM operations can take several minutes for complex submissions
- No proper timeout configuration for long-running operations

## Solutions Implemented

### 1. Extended Request Timeouts
- **Flask app timeout**: Extended to 10 minutes (600 seconds)
- **Socket timeout**: Set to 10 minutes for network operations
- **LLM processing timeout**: Set to 5 minutes with proper error handling
- **Grading service timeout**: Extended to 10 minutes (600 seconds)

### 2. Production Server Configuration
- **Gunicorn integration**: Automatic fallback to Gunicorn for better timeout handling
- **Worker configuration**: Optimized for AI processing workloads
- **Request timeout**: 10 minutes for long-running operations

### 3. Timeout Middleware
- **AI endpoint detection**: Automatically applies extended timeouts to AI operations
- **Progress monitoring**: Tracks request duration and logs slow operations
- **Error handling**: Provides user-friendly timeout error messages

### 4. Enhanced Error Handling
- **Graceful degradation**: Falls back to individual grading if batch processing times out
- **Progress reporting**: Real-time updates during long operations
- **Recovery mechanisms**: Automatic retry with exponential backoff

## How to Run with Timeout Fixes

### Option 1: Quick Start (Recommended)
```bash
# Windows
start_with_timeout.bat

# Linux/Mac
python run_with_timeout.py
```

### Option 2: Manual Configuration
```bash
# Set environment variables
export USE_GUNICORN=true
export GUNICORN_TIMEOUT=600
export REQUEST_TIMEOUT=600

# Run the application
python run_app.py
```

### Option 3: Direct Waitress (Production - Windows Compatible)
```bash
# Windows
python -c "from waitress import serve; from webapp.app import app; serve(app, host='127.0.0.1', port=5000, threads=4, channel_timeout=600)"

# Or use environment variable
set USE_WAITRESS=true
python run_app.py
```

## Configuration Files Updated

### 1. Environment Variables (.env)
```env
# New timeout settings
REQUEST_TIMEOUT=600
SOCKET_TIMEOUT=600
LLM_TIMEOUT=300
GRADING_TIMEOUT=600
```

### 2. Processing Configuration (config/processing.json)
```json
{
  "timeouts": {
    "grading_service": 600,
    "llm_processing": 300,
    "mapping_service": 180
  }
}
```

### 3. Flask App Configuration
- Extended session lifetime to 2 hours
- Socket timeout set to 10 minutes
- Timeout middleware for AI endpoints

## Monitoring and Debugging

### Check if Timeouts are Working
1. **Start the application** with timeout fixes
2. **Monitor logs** for timeout-related messages:
   ```
   Setting extended timeout (600s) for AI endpoint: /processing/api/process
   LLM grading completed in 45.23 seconds
   AI request completed: /processing/api/process took 67.89s
   ```

### Performance Monitoring
- **Slow requests** (>1 minute) are automatically logged
- **AI operations** have detailed timing information
- **Progress tracking** shows real-time processing status

### Troubleshooting Common Issues

#### 1. Still Getting Timeouts?
```bash
# Increase timeout further (15 minutes)
export REQUEST_TIMEOUT=900
export GUNICORN_TIMEOUT=900
python run_with_timeout.py
```

#### 2. Memory Issues with Large Files?
```bash
# Reduce batch size for processing
export MAX_BATCH_SIZE=3
export CHUNK_SIZE=2000
```

#### 3. LLM API Timeouts?
```bash
# Increase LLM-specific timeout
export LLM_TIMEOUT=600
export DEEPSEEK_TIMEOUT=600
```

## Best Practices for Large Submissions

### 1. File Size Optimization
- **PDF files**: Keep under 10MB when possible
- **Image files**: Use compressed formats (JPEG instead of PNG)
- **Text extraction**: Pre-process files to extract text before upload

### 2. Submission Strategies
- **Batch processing**: Process multiple small files instead of one large file
- **Progressive grading**: Grade sections individually for very long submissions
- **Caching**: Enable result caching to avoid re-processing identical content

### 3. Monitoring Progress
- **Use progress tracking**: Monitor real-time processing status
- **Check logs**: Review application logs for performance insights
- **Resource monitoring**: Watch CPU and memory usage during processing

## Technical Details

### Timeout Hierarchy
1. **Socket timeout**: 600 seconds (network operations)
2. **Flask request timeout**: 600 seconds (HTTP requests)
3. **Gunicorn worker timeout**: 600 seconds (worker processes)
4. **LLM operation timeout**: 300 seconds (individual AI calls)
5. **Overall grading timeout**: 600 seconds (complete grading process)

### Error Recovery
- **Automatic retry**: Failed operations retry with exponential backoff
- **Fallback processing**: Batch failures fall back to individual processing
- **Graceful degradation**: Partial results returned if some operations fail

### Performance Optimizations
- **Connection pooling**: Reuse database and API connections
- **Result caching**: Cache grading results to avoid reprocessing
- **Async processing**: Non-blocking operations where possible
- **Resource limits**: Prevent memory exhaustion during processing

## Verification Steps

After implementing these fixes, verify they're working:

1. **Start the application**:
   ```bash
   python run_with_timeout.py
   ```

2. **Check startup logs** for timeout configuration:
   ```
   🚀 Starting Exam Grader with extended timeouts for AI processing...
   ⏱️  Request timeout: 10 minutes
   Timeout middleware initialized for AI operations
   ```

3. **Test with a large submission** and monitor the logs for timing information

4. **Verify no timeout errors** during grading operations

## Support

If you continue to experience timeout issues:

1. **Check the logs** in the `logs/` directory for detailed error information
2. **Increase timeouts further** using environment variables
3. **Consider breaking large submissions** into smaller parts
4. **Monitor system resources** (CPU, memory) during processing

The timeout fixes should resolve the grading timeout issues you were experiencing. The application now has proper timeout handling for AI operations while maintaining responsiveness for regular web requests.