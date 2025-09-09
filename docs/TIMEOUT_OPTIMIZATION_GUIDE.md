# Timeout Optimization Guide

## Overview

This guide explains the timeout optimization improvements made to resolve the LLM service timeout issues in the Exam Grader application.

## Issues Identified

1. **Async Service Initialization Warnings**: The service registry was not properly handling async `initialize()` methods
2. **Insufficient Timeout Values**: Default timeout values were too low for LLM API calls
3. **Poor Error Handling**: Timeout errors were not being handled with proper retry logic
4. **No Dynamic Adjustment**: Timeout values were static and couldn't adapt to performance patterns

## Solutions Implemented

### 1. Fixed Async Service Initialization

**File**: `src/services/service_registry.py`

- Added proper async/await handling for service initialization
- Implemented timeout protection for async initialization
- Added fallback mechanisms for different event loop scenarios

**Key Changes**:
```python
if inspect.iscoroutinefunction(service.initialize):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.create_task(service.initialize())
            success = asyncio.wait_for(task, timeout=self.dependency_timeout)
        else:
            success = loop.run_until_complete(
                asyncio.wait_for(service.initialize(), timeout=self.dependency_timeout)
            )
    except RuntimeError:
        success = asyncio.run(
            asyncio.wait_for(service.initialize(), timeout=self.dependency_timeout)
        )
```

### 2. Optimized Timeout Configuration

**Files**: 
- `src/config/dynamic_config.py`
- `src/config/unified_config.py`
- `env.example`

**Increased Timeout Values**:
- `API_TIMEOUT`: 30s → 60s
- `LLM_JSON_TIMEOUT`: 10s → 30s
- `TIMEOUT_LLM_PROCESSING`: 300s → 600s
- `LLM_RETRY_ATTEMPTS`: 3 → 5
- `LLM_CONNECTION_POOL_SIZE`: 3 → 5

### 3. Enhanced LLM Service Timeout Handling

**File**: `src/services/consolidated_llm_service.py`

**Improvements**:
- Added explicit timeout parameters to API calls
- Implemented dynamic timeout adjustment based on error patterns
- Enhanced retry logic with exponential backoff
- Added performance monitoring and recording

**Key Features**:
```python
# Dynamic timeout adjustment
if "timeout" in error_str and attempt < 2:
    new_timeout = timeout_manager.adjust_timeout("llm", "api_call", "timeout_error")
    self.api_timeout = new_timeout
    logger.info(f"Adjusted API timeout to {self.api_timeout}s for retry")
```

### 4. Created Timeout Manager

**File**: `src/utils/timeout_manager.py`

**Features**:
- Centralized timeout configuration management
- Dynamic timeout adjustment based on performance metrics
- Performance history tracking
- Error pattern analysis
- Automatic timeout optimization

**Usage**:
```python
from src.utils.timeout_manager import timeout_manager

# Get timeout for specific service/operation
timeout = timeout_manager.get_timeout("llm", "processing")

# Record performance metrics
timeout_manager.record_performance("llm", "api_call", duration, success)

# Adjust timeout based on performance
new_timeout = timeout_manager.adjust_timeout("llm", "api_call", "performance")
```

## Configuration

### Environment Variables

Update your `.env` file with these optimized values:

```bash
# API Configuration
API_TIMEOUT=60
API_RETRY_ATTEMPTS=5
API_RETRY_DELAY=2.0

# LLM Service Configuration
LLM_CONNECTION_POOL_SIZE=5
LLM_RETRY_ATTEMPTS=5
LLM_JSON_TIMEOUT=30.0
LLM_RETRY_ON_JSON_ERROR=3

# Timeout Configuration
TIMEOUT_LLM_PROCESSING=600
TIMEOUT_STANDARD_REQUEST=60
```

### Dynamic Configuration

The timeout manager automatically adjusts timeouts based on:
- Success rates (increases timeout if < 70% success)
- Performance patterns (decreases timeout if > 95% success and fast execution)
- Error patterns (tracks and responds to specific error types)

## Monitoring

### Performance Metrics

The system now tracks:
- API call duration
- Success/failure rates
- Error patterns
- Timeout adjustments

### Logging

Enhanced logging provides:
- Timeout adjustment notifications
- Performance metrics
- Error categorization
- Retry attempt details

## Best Practices

### 1. Monitor Performance

Regularly check the timeout manager status:
```python
status = timeout_manager.get_status()
print(f"Current timeouts: {status['config']}")
print(f"Performance history: {status['performance_history']}")
```

### 2. Adjust Based on Usage

- For high-volume processing: Increase `LLM_CONNECTION_POOL_SIZE`
- For slow networks: Increase `API_TIMEOUT` and `LLM_JSON_TIMEOUT`
- For unstable connections: Increase `LLM_RETRY_ATTEMPTS`

### 3. Error Handling

The system now provides better error handling:
- Automatic retry with exponential backoff
- Dynamic timeout adjustment
- Graceful degradation
- Detailed error logging

## Troubleshooting

### Common Issues

1. **Still Getting Timeouts**
   - Check your network connection
   - Verify API key is valid
   - Increase `TIMEOUT_LLM_PROCESSING` to 900s
   - Check DeepSeek API status

2. **Async Initialization Warnings**
   - These should be resolved with the new service registry
   - If still occurring, check for circular imports

3. **Performance Issues**
   - Monitor the timeout manager metrics
   - Adjust connection pool size
   - Check for memory leaks

### Debug Mode

Enable debug logging to see detailed timeout information:
```bash
LOG_LEVEL=DEBUG
```

## Migration

### From Previous Version

1. Update your `.env` file with new timeout values
2. Restart the application
3. Monitor logs for timeout adjustments
4. Verify improved performance

### Rollback

If issues occur, you can rollback by:
1. Reverting timeout values in `.env`
2. Restarting the application
3. The timeout manager will adapt to the new values

## Future Improvements

1. **Machine Learning**: Implement ML-based timeout prediction
2. **Circuit Breaker**: Add circuit breaker pattern for failing services
3. **Load Balancing**: Implement intelligent load balancing
4. **Caching**: Add response caching for repeated requests

## Support

For issues or questions:
1. Check the logs for timeout-related messages
2. Review the timeout manager status
3. Verify environment configuration
4. Contact the development team with specific error messages
