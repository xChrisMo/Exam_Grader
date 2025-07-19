/**
 * Unified API Client for Exam Grader Frontend
 * 
 * Provides a centralized, robust API client with:
 * - Automatic CSRF token management
 * - Retry logic with exponential backoff
 * - Request/response interceptors
 * - Comprehensive error handling
 * - Authentication state management
 * - Request timeout handling
 * - Response caching (optional)
 */

class APIClient {
    constructor(options = {}) {
        this.options = {
            baseURL: '',
            timeout: 30000, // 30 seconds
            retryAttempts: 3,
            retryDelay: 1000, // Base delay in ms
            maxRetryDelay: 10000, // Max delay in ms
            enableCache: false,
            cacheTimeout: 300000, // 5 minutes
            ...options
        };
        
        this.cache = new Map();
        this.requestInterceptors = [];
        this.responseInterceptors = [];
        this.pendingRequests = new Map();
        this.csrfToken = null;
        this.isAuthenticated = false;
        
        this.initializeCSRF();
        this.setupDefaultInterceptors();
    }
    
    /**
     * Initialize CSRF token management
     */
    async initializeCSRF() {
        this.csrfToken = this.getCSRFToken();
        if (!this.csrfToken) {
            await this.refreshCSRFToken();
        }
    }
    
    /**
     * Get CSRF token from multiple sources
     */
    getCSRFToken() {
        // Try meta tag first
        const metaTag = document.querySelector('meta[name=csrf-token]');
        if (metaTag && metaTag.getAttribute('content')) {
            return metaTag.getAttribute('content');
        }
        
        // Try form inputs
        const tokenInput = document.querySelector('input[name=csrf_token]');
        if (tokenInput && tokenInput.value) {
            return tokenInput.value;
        }
        
        return null;
    }
    
    /**
     * Refresh CSRF token
     */
    async refreshCSRFToken() {
        try {
            const response = await fetch('/get-csrf-token', {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.csrf_token) {
                    this.csrfToken = data.csrf_token;
                    this.updateCSRFTokenInDOM(data.csrf_token);
                    return data.csrf_token;
                }
            }
            
            throw new Error(`Failed to refresh CSRF token: ${response.status}`);
        } catch (error) {
            console.error('CSRF token refresh failed:', error);
            throw error;
        }
    }
    
    /**
     * Update CSRF token in DOM elements
     */
    updateCSRFTokenInDOM(token) {
        // Update meta tag
        let metaTag = document.querySelector('meta[name=csrf-token]');
        if (metaTag) {
            metaTag.setAttribute('content', token);
        } else {
            metaTag = document.createElement('meta');
            metaTag.name = 'csrf-token';
            metaTag.content = token;
            document.head.appendChild(metaTag);
        }
        
        // Update form inputs
        const tokenInputs = document.querySelectorAll('input[name=csrf_token]');
        tokenInputs.forEach(input => {
            input.value = token;
        });
    }
    
    /**
     * Setup default request/response interceptors
     */
    setupDefaultInterceptors() {
        // Request interceptor for CSRF and auth
        this.addRequestInterceptor(async (config) => {
            // Add CSRF token
            if (!config.headers['X-CSRFToken'] && this.csrfToken) {
                config.headers['X-CSRFToken'] = this.csrfToken;
            }
            
            // Add content type if not specified
            if (!config.headers['Content-Type'] && config.body && typeof config.body === 'object') {
                config.headers['Content-Type'] = 'application/json';
            }
            
            // Add credentials
            config.credentials = config.credentials || 'same-origin';
            
            return config;
        });
        
        // Response interceptor for error handling
        this.addResponseInterceptor(
            (response) => response,
            async (error, config) => {
                // Handle CSRF token expiration
                if (error.status === 403 || error.status === 419) {
                    try {
                        await this.refreshCSRFToken();
                        // Retry the request with new token
                        config.headers['X-CSRFToken'] = this.csrfToken;
                        return this.makeRequest(config);
                    } catch (csrfError) {
                        console.error('Failed to refresh CSRF token:', csrfError);
                    }
                }
                
                // Handle authentication errors
                if (error.status === 401) {
                    this.isAuthenticated = false;
                    this.handleAuthenticationError(error);
                }
                
                throw error;
            }
        );
    }
    
    /**
     * Add request interceptor
     */
    addRequestInterceptor(interceptor) {
        this.requestInterceptors.push(interceptor);
    }
    
    /**
     * Add response interceptor
     */
    addResponseInterceptor(successHandler, errorHandler) {
        this.responseInterceptors.push({ successHandler, errorHandler });
    }
    
    /**
     * Apply request interceptors
     */
    async applyRequestInterceptors(config) {
        let modifiedConfig = { ...config };
        
        for (const interceptor of this.requestInterceptors) {
            modifiedConfig = await interceptor(modifiedConfig);
        }
        
        return modifiedConfig;
    }
    
    /**
     * Apply response interceptors
     */
    async applyResponseInterceptors(response, config) {
        let modifiedResponse = response;
        
        for (const { successHandler, errorHandler } of this.responseInterceptors) {
            try {
                if (response.ok) {
                    modifiedResponse = await successHandler(modifiedResponse);
                }
            } catch (error) {
                if (errorHandler) {
                    modifiedResponse = await errorHandler(error, config);
                } else {
                    throw error;
                }
            }
        }
        
        return modifiedResponse;
    }
    
    /**
     * Generate cache key for request
     */
    generateCacheKey(config) {
        const { method, url, body } = config;
        const bodyStr = body ? JSON.stringify(body) : '';
        return `${method}:${url}:${bodyStr}`;
    }
    
    /**
     * Get cached response
     */
    getCachedResponse(cacheKey) {
        if (!this.options.enableCache) return null;
        
        const cached = this.cache.get(cacheKey);
        if (cached && Date.now() - cached.timestamp < this.options.cacheTimeout) {
            return cached.response;
        }
        
        // Remove expired cache entry
        if (cached) {
            this.cache.delete(cacheKey);
        }
        
        return null;
    }
    
    /**
     * Cache response
     */
    cacheResponse(cacheKey, response) {
        if (!this.options.enableCache) return;
        
        this.cache.set(cacheKey, {
            response: response.clone(),
            timestamp: Date.now()
        });
    }
    
    /**
     * Create request timeout controller
     */
    createTimeoutController(timeout) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            controller.abort();
        }, timeout);
        
        return { controller, timeoutId };
    }
    
    /**
     * Calculate retry delay with exponential backoff
     */
    calculateRetryDelay(attempt) {
        const delay = this.options.retryDelay * Math.pow(2, attempt - 1);
        const jitter = Math.random() * 0.1 * delay; // Add 10% jitter
        return Math.min(delay + jitter, this.options.maxRetryDelay);
    }
    
    /**
     * Check if error is retryable
     */
    isRetryableError(error) {
        // Network errors
        if (error.name === 'TypeError' || error.name === 'AbortError') {
            return true;
        }
        
        // HTTP status codes that are retryable
        const retryableStatuses = [408, 429, 500, 502, 503, 504];
        return retryableStatuses.includes(error.status);
    }
    
    /**
     * Make HTTP request with retry logic
     */
    async makeRequest(config) {
        const { url, method = 'GET', body, headers = {}, timeout = this.options.timeout } = config;
        
        // Apply request interceptors
        const finalConfig = await this.applyRequestInterceptors({
            url: this.options.baseURL + url,
            method,
            body: body && typeof body === 'object' ? JSON.stringify(body) : body,
            headers,
            timeout
        });
        
        // Check cache for GET requests
        if (method === 'GET' && this.options.enableCache) {
            const cacheKey = this.generateCacheKey(finalConfig);
            const cachedResponse = this.getCachedResponse(cacheKey);
            if (cachedResponse) {
                return cachedResponse;
            }
        }
        
        // Check for duplicate requests
        const requestKey = `${method}:${finalConfig.url}`;
        if (this.pendingRequests.has(requestKey)) {
            return this.pendingRequests.get(requestKey);
        }
        
        const requestPromise = this.executeRequestWithRetry(finalConfig);
        this.pendingRequests.set(requestKey, requestPromise);
        
        try {
            const response = await requestPromise;
            return response;
        } finally {
            this.pendingRequests.delete(requestKey);
        }
    }
    
    /**
     * Execute request with retry logic
     */
    async executeRequestWithRetry(config) {
        let lastError;
        
        for (let attempt = 1; attempt <= this.options.retryAttempts; attempt++) {
            try {
                const { controller, timeoutId } = this.createTimeoutController(config.timeout);
                
                const response = await fetch(config.url, {
                    method: config.method,
                    headers: config.headers,
                    body: config.body,
                    credentials: config.credentials,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                // Apply response interceptors
                const finalResponse = await this.applyResponseInterceptors(response, config);
                
                if (!finalResponse.ok) {
                    const error = new Error(`HTTP ${finalResponse.status}: ${finalResponse.statusText}`);
                    error.status = finalResponse.status;
                    error.response = finalResponse;
                    throw error;
                }
                
                // Cache successful GET responses
                if (config.method === 'GET' && this.options.enableCache) {
                    const cacheKey = this.generateCacheKey(config);
                    this.cacheResponse(cacheKey, finalResponse);
                }
                
                return finalResponse;
                
            } catch (error) {
                lastError = error;
                
                console.warn(`Request attempt ${attempt} failed:`, error);
                
                // Don't retry if it's the last attempt or error is not retryable
                if (attempt === this.options.retryAttempts || !this.isRetryableError(error)) {
                    break;
                }
                
                // Wait before retrying
                const delay = this.calculateRetryDelay(attempt);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
        
        throw lastError;
    }
    
    /**
     * Handle authentication errors
     */
    handleAuthenticationError(error) {
        // Emit custom event for authentication error
        const authEvent = new CustomEvent('apiAuthError', {
            detail: { error, client: this }
        });
        document.dispatchEvent(authEvent);
        
        // Optionally redirect to login page
        if (this.options.redirectOnAuthError) {
            window.location.href = this.options.loginUrl || '/login';
        }
    }
    
    /**
     * GET request
     */
    async get(url, config = {}) {
        const response = await this.makeRequest({
            url,
            method: 'GET',
            ...config
        });
        return response.json();
    }
    
    /**
     * POST request
     */
    async post(url, data, config = {}) {
        const response = await this.makeRequest({
            url,
            method: 'POST',
            body: data,
            ...config
        });
        return response.json();
    }
    
    /**
     * PUT request
     */
    async put(url, data, config = {}) {
        const response = await this.makeRequest({
            url,
            method: 'PUT',
            body: data,
            ...config
        });
        return response.json();
    }
    
    /**
     * DELETE request
     */
    async delete(url, config = {}) {
        const response = await this.makeRequest({
            url,
            method: 'DELETE',
            ...config
        });
        return response.json();
    }
    
    /**
     * PATCH request
     */
    async patch(url, data, config = {}) {
        const response = await this.makeRequest({
            url,
            method: 'PATCH',
            body: data,
            ...config
        });
        return response.json();
    }
    
    /**
     * Upload file with progress tracking
     */
    async uploadFile(url, file, options = {}) {
        const {
            onProgress,
            additionalData = {},
            fieldName = 'file'
        } = options;
        
        const formData = new FormData();
        formData.append(fieldName, file);
        
        // Add additional form data
        Object.entries(additionalData).forEach(([key, value]) => {
            formData.append(key, value);
        });
        
        // Create XMLHttpRequest for progress tracking
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            // Progress tracking
            if (onProgress) {
                xhr.upload.addEventListener('progress', (event) => {
                    if (event.lengthComputable) {
                        const percentComplete = (event.loaded / event.total) * 100;
                        onProgress(percentComplete, event.loaded, event.total);
                    }
                });
            }
            
            // Success handler
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (error) {
                        resolve(xhr.responseText);
                    }
                } else {
                    reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
                }
            });
            
            // Error handler
            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed: Network error'));
            });
            
            // Abort handler
            xhr.addEventListener('abort', () => {
                reject(new Error('Upload aborted'));
            });
            
            // Set headers
            if (this.csrfToken) {
                xhr.setRequestHeader('X-CSRFToken', this.csrfToken);
            }
            
            // Start upload
            xhr.open('POST', this.options.baseURL + url);
            xhr.send(formData);
        });
    }
    
    /**
     * Clear cache
     */
    clearCache() {
        this.cache.clear();
    }
    
    /**
     * Get client statistics
     */
    getStats() {
        return {
            cacheSize: this.cache.size,
            pendingRequests: this.pendingRequests.size,
            isAuthenticated: this.isAuthenticated,
            hasCSRFToken: !!this.csrfToken
        };
    }
    
    /**
     * Destroy client and cleanup
     */
    destroy() {
        this.clearCache();
        this.pendingRequests.clear();
        this.requestInterceptors.length = 0;
        this.responseInterceptors.length = 0;
    }
}

// Create global API client instance
window.apiClient = new APIClient({
    timeout: 30000,
    retryAttempts: 3,
    enableCache: true,
    cacheTimeout: 300000
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIClient;
}