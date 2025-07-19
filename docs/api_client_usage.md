# API Client Usage Guide

## Overview

The Unified API Client provides a robust, feature-rich interface for making HTTP requests in the Exam Grader frontend. It includes automatic CSRF token management, retry logic, caching, and comprehensive error handling.

## Features

- **Automatic CSRF Token Management**: Handles token refresh and injection
- **Retry Logic**: Exponential backoff for failed requests
- **Request/Response Interceptors**: Modify requests and responses globally
- **Caching**: Optional response caching for GET requests
- **Error Handling**: Comprehensive error handling with custom error types
- **File Upload**: Progress tracking for file uploads
- **Request Deduplication**: Prevents duplicate simultaneous requests
- **Authentication Handling**: Automatic handling of auth errors

## Basic Usage

### Initialization

```javascript
// The API client is automatically initialized as a global instance
// Available as window.apiClient

// Or create a custom instance
const customClient = new APIClient({
    baseURL: '/api/v2',
    timeout: 60000,
    retryAttempts: 5,
    enableCache: true,
    cacheTimeout: 600000 // 10 minutes
});
```

### Making Requests

```javascript
// GET request
try {
    const guides = await apiClient.get('/guides');
    console.log('Marking guides:', guides.data);
} catch (error) {
    console.error('Failed to fetch guides:', error);
}

// POST request
try {
    const result = await apiClient.post('/process-submission', {
        submission_id: 123,
        guide_id: 456
    });
    console.log('Processing started:', result);
} catch (error) {
    console.error('Processing failed:', error);
}

// PUT request
const updatedGuide = await apiClient.put('/guides/123', {
    title: 'Updated Guide Title',
    content: 'Updated content'
});

// DELETE request
const deleteResult = await apiClient.delete('/submissions/123');

// PATCH request
const patchResult = await apiClient.patch('/guides/123', {
    title: 'New Title'
});
```

### File Upload with Progress

```javascript
const fileInput = document.getElementById('file-input');
const file = fileInput.files[0];

try {
    const result = await apiClient.uploadFile('/upload-submission', file, {
        onProgress: (percentComplete, loaded, total) => {
            console.log(`Upload progress: ${percentComplete.toFixed(2)}%`);
            updateProgressBar(percentComplete);
        },
        additionalData: {
            guide_id: 123,
            description: 'Student submission'
        }
    });
    
    console.log('Upload successful:', result);
} catch (error) {
    console.error('Upload failed:', error);
}
```

## Advanced Features

### Request Interceptors

```javascript
// Add custom headers to all requests
apiClient.addRequestInterceptor(async (config) => {
    config.headers['X-Client-Version'] = '1.0.0';
    config.headers['X-Request-ID'] = generateRequestId();
    return config;
});

// Add authentication token
apiClient.addRequestInterceptor(async (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
});
```

### Response Interceptors

```javascript
// Log all responses
apiClient.addResponseInterceptor(
    (response) => {
        console.log('Response received:', response.status);
        return response;
    },
    (error, config) => {
        console.error('Request failed:', error);
        // Optionally transform error
        throw error;
    }
);

// Handle specific error codes
apiClient.addResponseInterceptor(
    (response) => response,
    async (error, config) => {
        if (error.status === 429) { // Rate limited
            // Wait and retry
            await new Promise(resolve => setTimeout(resolve, 5000));
            return apiClient.makeRequest(config);
        }
        throw error;
    }
);
```

### Caching

```javascript
// Enable caching for specific requests
const guides = await apiClient.get('/guides', {
    enableCache: true,
    cacheTimeout: 300000 // 5 minutes
});

// Clear cache when needed
apiClient.clearCache();

// Disable caching for a request
const freshData = await apiClient.get('/real-time-data', {
    enableCache: false
});
```

## Migration Examples

### From Direct Fetch Calls

**Before:**
```javascript
// Old approach with manual error handling
async function processSubmission(submissionId, guideId) {
    try {
        const csrfToken = document.querySelector('meta[name=csrf-token]').getAttribute('content');
        
        const response = await fetch('/api/process-submission', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                submission_id: submissionId,
                guide_id: guideId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Processing failed:', error);
        throw error;
    }
}
```

**After:**
```javascript
// New approach with API client
async function processSubmission(submissionId, guideId) {
    return await apiClient.post('/process-submission', {
        submission_id: submissionId,
        guide_id: guideId
    });
}
```

### From jQuery AJAX

**Before:**
```javascript
// Old jQuery approach
$.ajax({
    url: '/api/guides',
    method: 'GET',
    dataType: 'json',
    success: function(data) {
        console.log('Guides loaded:', data);
    },
    error: function(xhr, status, error) {
        console.error('Failed to load guides:', error);
    }
});
```

**After:**
```javascript
// New approach with async/await
try {
    const guides = await apiClient.get('/guides');
    console.log('Guides loaded:', guides);
} catch (error) {
    console.error('Failed to load guides:', error);
}
```

### From XMLHttpRequest File Upload

**Before:**
```javascript
// Old XMLHttpRequest approach
function uploadFile(file, onProgress) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append('file', file);
        
        xhr.upload.addEventListener('progress', (event) => {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                onProgress(percentComplete);
            }
        });
        
        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                reject(new Error(`Upload failed: ${xhr.status}`));
            }
        });
        
        xhr.addEventListener('error', () => {
            reject(new Error('Upload failed'));
        });
        
        const csrfToken = document.querySelector('meta[name=csrf-token]').getAttribute('content');
        xhr.setRequestHeader('X-CSRFToken', csrfToken);
        
        xhr.open('POST', '/api/upload');
        xhr.send(formData);
    });
}
```

**After:**
```javascript
// New approach with API client
async function uploadFile(file, onProgress) {
    return await apiClient.uploadFile('/upload', file, {
        onProgress: (percentComplete) => onProgress(percentComplete)
    });
}
```

## Error Handling

### Custom Error Types

```javascript
try {
    const result = await apiClient.post('/process', data);
} catch (error) {
    if (error.status === 400) {
        // Bad request - show validation errors
        showValidationErrors(error.response);
    } else if (error.status === 401) {
        // Unauthorized - redirect to login
        window.location.href = '/login';
    } else if (error.status === 429) {
        // Rate limited - show retry message
        showRetryMessage();
    } else if (error.name === 'AbortError') {
        // Request timeout
        showTimeoutMessage();
    } else {
        // Generic error
        showGenericError(error.message);
    }
}
```

### Global Error Handling

```javascript
// Listen for authentication errors
document.addEventListener('apiAuthError', (event) => {
    console.log('Authentication error:', event.detail.error);
    // Redirect to login or show auth modal
    showLoginModal();
});

// Add global error interceptor
apiClient.addResponseInterceptor(
    (response) => response,
    (error, config) => {
        // Log all errors to analytics
        analytics.track('api_error', {
            url: config.url,
            method: config.method,
            status: error.status,
            message: error.message
        });
        
        throw error;
    }
);
```

## Performance Optimization

### Request Deduplication

```javascript
// These requests will be deduplicated automatically
const [guides1, guides2] = await Promise.all([
    apiClient.get('/guides'),
    apiClient.get('/guides') // Same request, will reuse the first one
]);
```

### Caching Strategy

```javascript
// Cache static data for longer periods
const staticConfig = await apiClient.get('/config', {
    enableCache: true,
    cacheTimeout: 3600000 // 1 hour
});

// Don't cache dynamic data
const realtimeStatus = await apiClient.get('/status', {
    enableCache: false
});
```

### Batch Requests

```javascript
// Process multiple submissions efficiently
async function processBatch(submissionIds, guideId) {
    const batchSize = 5;
    const results = [];
    
    for (let i = 0; i < submissionIds.length; i += batchSize) {
        const batch = submissionIds.slice(i, i + batchSize);
        const batchPromises = batch.map(id => 
            apiClient.post('/process-submission', {
                submission_id: id,
                guide_id: guideId
            })
        );
        
        const batchResults = await Promise.all(batchPromises);
        results.push(...batchResults);
    }
    
    return results;
}
```

## Configuration Options

```javascript
const apiClient = new APIClient({
    // Base URL for all requests
    baseURL: '/api/v1',
    
    // Request timeout in milliseconds
    timeout: 30000,
    
    // Number of retry attempts for failed requests
    retryAttempts: 3,
    
    // Base delay between retries (exponential backoff)
    retryDelay: 1000,
    
    // Maximum delay between retries
    maxRetryDelay: 10000,
    
    // Enable response caching
    enableCache: true,
    
    // Cache timeout in milliseconds
    cacheTimeout: 300000,
    
    // Redirect on authentication errors
    redirectOnAuthError: true,
    
    // Login URL for redirects
    loginUrl: '/login'
});
```

## Monitoring and Debugging

### Client Statistics

```javascript
// Get client statistics
const stats = apiClient.getStats();
console.log('API Client Stats:', {
    cacheSize: stats.cacheSize,
    pendingRequests: stats.pendingRequests,
    isAuthenticated: stats.isAuthenticated,
    hasCSRFToken: stats.hasCSRFToken
});
```

### Debug Mode

```javascript
// Enable debug logging
apiClient.addRequestInterceptor((config) => {
    console.log('Making request:', config.method, config.url);
    return config;
});

apiClient.addResponseInterceptor(
    (response) => {
        console.log('Response received:', response.status);
        return response;
    },
    (error) => {
        console.error('Request failed:', error);
        throw error;
    }
);
```

## Best Practices

1. **Use the global instance**: The global `apiClient` instance is pre-configured and ready to use.

2. **Handle errors appropriately**: Always wrap API calls in try-catch blocks or use `.catch()`.

3. **Use caching wisely**: Enable caching for static data, disable for dynamic data.

4. **Implement proper loading states**: Show loading indicators during API calls.

5. **Batch requests when possible**: Group related requests to reduce server load.

6. **Use interceptors for cross-cutting concerns**: Authentication, logging, error handling.

7. **Monitor performance**: Use the statistics API to monitor client performance.

8. **Clean up resources**: Call `destroy()` when the client is no longer needed.

## Integration with Existing Code

The API client is designed to be a drop-in replacement for existing fetch calls and jQuery AJAX requests. It maintains backward compatibility while providing enhanced features.

### Gradual Migration

1. Start by replacing simple GET requests
2. Move to POST/PUT/DELETE requests
3. Migrate file uploads
4. Add interceptors for cross-cutting concerns
5. Enable caching where appropriate

This approach allows for gradual migration without breaking existing functionality.