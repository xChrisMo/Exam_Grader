/**
 * Tests for Unified API Client
 * 
 * Comprehensive test suite covering:
 * - CSRF token management
 * - Retry logic and error handling
 * - Request/response interceptors
 * - Caching functionality
 * - Authentication handling
 * - File upload with progress
 */

// Mock fetch for testing
class MockResponse {
    constructor(data, options = {}) {
        this.data = data;
        this.ok = options.ok !== false;
        this.status = options.status || (this.ok ? 200 : 500);
        this.statusText = options.statusText || (this.ok ? 'OK' : 'Internal Server Error');
        this.headers = new Map(Object.entries(options.headers || {}));
    }
    
    async json() {
        return this.data;
    }
    
    async text() {
        return typeof this.data === 'string' ? this.data : JSON.stringify(this.data);
    }
    
    clone() {
        return new MockResponse(this.data, {
            ok: this.ok,
            status: this.status,
            statusText: this.statusText,
            headers: Object.fromEntries(this.headers)
        });
    }
}

// Mock DOM elements
class MockDocument {
    constructor() {
        this.elements = new Map();
        this.head = { appendChild: () => {} };
    }
    
    querySelector(selector) {
        return this.elements.get(selector) || null;
    }
    
    querySelectorAll(selector) {
        const element = this.elements.get(selector);
        return element ? [element] : [];
    }
    
    createElement(tagName) {
        return {
            tagName: tagName.toUpperCase(),
            setAttribute: () => {},
            getAttribute: () => null,
            name: '',
            content: '',
            value: ''
        };
    }
    
    dispatchEvent() {}
    
    setElement(selector, element) {
        this.elements.set(selector, element);
    }
}

// Test setup
function setupTestEnvironment() {
    global.fetch = jest.fn();
    global.document = new MockDocument();
    global.AbortController = class {
        constructor() {
            this.signal = {};
        }
        abort() {}
    };
    global.FormData = class {
        constructor() {
            this.data = new Map();
        }
        append(key, value) {
            this.data.set(key, value);
        }
    };
    global.XMLHttpRequest = class {
        constructor() {
            this.upload = { addEventListener: () => {} };
            this.status = 200;
            this.responseText = '{"success": true}';
        }
        addEventListener() {}
        setRequestHeader() {}
        open() {}
        send() {
            setTimeout(() => {
                if (this.onload) this.onload();
            }, 0);
        }
    };
}

// Load the APIClient class
require('../../../webapp/static/js/api-client.js');

describe('APIClient', () => {
    let apiClient;
    
    beforeEach(() => {
        setupTestEnvironment();
        apiClient = new APIClient({
            baseURL: '/api',
            timeout: 5000,
            retryAttempts: 2,
            enableCache: true
        });
        jest.clearAllMocks();
    });
    
    afterEach(() => {
        apiClient.destroy();
    });
    
    describe('CSRF Token Management', () => {
        test('should get CSRF token from meta tag', () => {
            const mockMeta = {
                getAttribute: jest.fn().mockReturnValue('test-csrf-token')
            };
            document.setElement('meta[name=csrf-token]', mockMeta);
            
            const token = apiClient.getCSRFToken();
            expect(token).toBe('test-csrf-token');
            expect(mockMeta.getAttribute).toHaveBeenCalledWith('content');
        });
        
        test('should get CSRF token from form input as fallback', () => {
            const mockInput = { value: 'form-csrf-token' };
            document.setElement('input[name=csrf_token]', mockInput);
            
            const token = apiClient.getCSRFToken();
            expect(token).toBe('form-csrf-token');
        });
        
        test('should refresh CSRF token when expired', async () => {
            fetch.mockResolvedValueOnce(new MockResponse({
                csrf_token: 'new-csrf-token'
            }));
            
            const token = await apiClient.refreshCSRFToken();
            expect(token).toBe('new-csrf-token');
            expect(fetch).toHaveBeenCalledWith('/get-csrf-token', expect.objectContaining({
                method: 'GET',
                credentials: 'same-origin'
            }));
        });
        
        test('should handle CSRF token refresh failure', async () => {
            fetch.mockResolvedValueOnce(new MockResponse({}, { ok: false, status: 500 }));
            
            await expect(apiClient.refreshCSRFToken()).rejects.toThrow('Failed to refresh CSRF token: 500');
        });
    });
    
    describe('Request Interceptors', () => {
        test('should apply request interceptors', async () => {
            const interceptor = jest.fn().mockImplementation(config => ({
                ...config,
                headers: { ...config.headers, 'Custom-Header': 'test-value' }
            }));
            
            apiClient.addRequestInterceptor(interceptor);
            
            fetch.mockResolvedValueOnce(new MockResponse({ success: true }));
            
            await apiClient.get('/test');
            
            expect(interceptor).toHaveBeenCalled();
            expect(fetch).toHaveBeenCalledWith(
                '/api/test',
                expect.objectContaining({
                    headers: expect.objectContaining({
                        'Custom-Header': 'test-value'
                    })
                })
            );
        });
        
        test('should add CSRF token in request interceptor', async () => {
            apiClient.csrfToken = 'test-token';
            fetch.mockResolvedValueOnce(new MockResponse({ success: true }));
            
            await apiClient.post('/test', { data: 'test' });
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/test',
                expect.objectContaining({
                    headers: expect.objectContaining({
                        'X-CSRFToken': 'test-token',
                        'Content-Type': 'application/json'
                    })
                })
            );
        });
    });
    
    describe('Response Interceptors', () => {
        test('should apply response interceptors', async () => {
            const successHandler = jest.fn().mockImplementation(response => response);
            const errorHandler = jest.fn();
            
            apiClient.addResponseInterceptor(successHandler, errorHandler);
            
            fetch.mockResolvedValueOnce(new MockResponse({ success: true }));
            
            await apiClient.get('/test');
            
            expect(successHandler).toHaveBeenCalled();
            expect(errorHandler).not.toHaveBeenCalled();
        });
        
        test('should handle CSRF token expiration in response interceptor', async () => {
            // First request fails with 403
            fetch.mockResolvedValueOnce(new MockResponse({}, { ok: false, status: 403 }));
            // CSRF refresh succeeds
            fetch.mockResolvedValueOnce(new MockResponse({ csrf_token: 'new-token' }));
            // Retry succeeds
            fetch.mockResolvedValueOnce(new MockResponse({ success: true }));
            
            const result = await apiClient.get('/test');
            
            expect(fetch).toHaveBeenCalledTimes(3);
            expect(result.success).toBe(true);
        });
    });
    
    describe('Retry Logic', () => {
        test('should retry on retryable errors', async () => {
            // First two requests fail, third succeeds
            fetch
                .mockRejectedValueOnce(new Error('Network error'))
                .mockRejectedValueOnce(new Error('Network error'))
                .mockResolvedValueOnce(new MockResponse({ success: true }));
            
            const result = await apiClient.get('/test');
            
            expect(fetch).toHaveBeenCalledTimes(3);
            expect(result.success).toBe(true);
        });
        
        test('should not retry on non-retryable errors', async () => {
            const error = new Error('Bad Request');
            error.status = 400;
            fetch.mockRejectedValueOnce(error);
            
            await expect(apiClient.get('/test')).rejects.toThrow('Bad Request');
            expect(fetch).toHaveBeenCalledTimes(1);
        });
        
        test('should respect maximum retry attempts', async () => {
            fetch.mockRejectedValue(new Error('Network error'));
            
            await expect(apiClient.get('/test')).rejects.toThrow('Network error');
            expect(fetch).toHaveBeenCalledTimes(2); // Initial + 1 retry (retryAttempts: 2)
        });
        
        test('should calculate retry delay with exponential backoff', () => {
            const delay1 = apiClient.calculateRetryDelay(1);
            const delay2 = apiClient.calculateRetryDelay(2);
            const delay3 = apiClient.calculateRetryDelay(3);
            
            expect(delay1).toBeGreaterThanOrEqual(1000);
            expect(delay2).toBeGreaterThanOrEqual(2000);
            expect(delay3).toBeGreaterThanOrEqual(4000);
            expect(delay3).toBeLessThanOrEqual(10000); // Max delay
        });
    });
    
    describe('Caching', () => {
        test('should cache GET responses', async () => {
            fetch.mockResolvedValue(new MockResponse({ data: 'test' }));
            
            // First request
            const result1 = await apiClient.get('/test');
            // Second request should use cache
            const result2 = await apiClient.get('/test');
            
            expect(fetch).toHaveBeenCalledTimes(1);
            expect(result1).toEqual(result2);
        });
        
        test('should not cache non-GET requests', async () => {
            fetch.mockResolvedValue(new MockResponse({ success: true }));
            
            await apiClient.post('/test', { data: 'test' });
            await apiClient.post('/test', { data: 'test' });
            
            expect(fetch).toHaveBeenCalledTimes(2);
        });
        
        test('should expire cached responses', async () => {
            // Set short cache timeout
            apiClient.options.cacheTimeout = 100;
            
            fetch.mockResolvedValue(new MockResponse({ data: 'test' }));
            
            await apiClient.get('/test');
            
            // Wait for cache to expire
            await new Promise(resolve => setTimeout(resolve, 150));
            
            await apiClient.get('/test');
            
            expect(fetch).toHaveBeenCalledTimes(2);
        });
        
        test('should clear cache', async () => {
            fetch.mockResolvedValue(new MockResponse({ data: 'test' }));
            
            await apiClient.get('/test');
            apiClient.clearCache();
            await apiClient.get('/test');
            
            expect(fetch).toHaveBeenCalledTimes(2);
        });
    });
    
    describe('HTTP Methods', () => {
        test('should make GET request', async () => {
            fetch.mockResolvedValueOnce(new MockResponse({ data: 'test' }));
            
            const result = await apiClient.get('/test');
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/test',
                expect.objectContaining({ method: 'GET' })
            );
            expect(result.data).toBe('test');
        });
        
        test('should make POST request', async () => {
            fetch.mockResolvedValueOnce(new MockResponse({ success: true }));
            
            const result = await apiClient.post('/test', { data: 'test' });
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/test',
                expect.objectContaining({
                    method: 'POST',
                    body: '{"data":"test"}'
                })
            );
            expect(result.success).toBe(true);
        });
        
        test('should make PUT request', async () => {
            fetch.mockResolvedValueOnce(new MockResponse({ success: true }));
            
            await apiClient.put('/test', { data: 'test' });
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/test',
                expect.objectContaining({ method: 'PUT' })
            );
        });
        
        test('should make DELETE request', async () => {
            fetch.mockResolvedValueOnce(new MockResponse({ success: true }));
            
            await apiClient.delete('/test');
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/test',
                expect.objectContaining({ method: 'DELETE' })
            );
        });
        
        test('should make PATCH request', async () => {
            fetch.mockResolvedValueOnce(new MockResponse({ success: true }));
            
            await apiClient.patch('/test', { data: 'test' });
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/test',
                expect.objectContaining({ method: 'PATCH' })
            );
        });
    });
    
    describe('File Upload', () => {
        test('should upload file with progress tracking', async () => {
            const mockFile = new Blob(['test content'], { type: 'text/plain' });
            const progressCallback = jest.fn();
            
            // Mock XMLHttpRequest
            const mockXHR = {
                upload: { addEventListener: jest.fn() },
                addEventListener: jest.fn(),
                setRequestHeader: jest.fn(),
                open: jest.fn(),
                send: jest.fn(),
                status: 200,
                responseText: '{"success": true}'
            };
            
            global.XMLHttpRequest = jest.fn(() => mockXHR);
            
            const uploadPromise = apiClient.uploadFile('/upload', mockFile, {
                onProgress: progressCallback
            });
            
            // Simulate successful upload
            setTimeout(() => {
                const loadHandler = mockXHR.addEventListener.mock.calls
                    .find(call => call[0] === 'load')[1];
                loadHandler();
            }, 0);
            
            const result = await uploadPromise;
            
            expect(mockXHR.open).toHaveBeenCalledWith('POST', '/api/upload');
            expect(mockXHR.send).toHaveBeenCalled();
            expect(result.success).toBe(true);
        });
        
        test('should handle upload errors', async () => {
            const mockFile = new Blob(['test content'], { type: 'text/plain' });
            
            const mockXHR = {
                upload: { addEventListener: jest.fn() },
                addEventListener: jest.fn(),
                setRequestHeader: jest.fn(),
                open: jest.fn(),
                send: jest.fn(),
                status: 500
            };
            
            global.XMLHttpRequest = jest.fn(() => mockXHR);
            
            const uploadPromise = apiClient.uploadFile('/upload', mockFile);
            
            // Simulate error
            setTimeout(() => {
                const errorHandler = mockXHR.addEventListener.mock.calls
                    .find(call => call[0] === 'error')[1];
                errorHandler();
            }, 0);
            
            await expect(uploadPromise).rejects.toThrow('Upload failed: Network error');
        });
    });
    
    describe('Authentication Handling', () => {
        test('should handle authentication errors', async () => {
            const authErrorHandler = jest.fn();
            document.addEventListener = jest.fn();
            
            fetch.mockResolvedValueOnce(new MockResponse({}, { ok: false, status: 401 }));
            
            await expect(apiClient.get('/test')).rejects.toThrow();
            expect(apiClient.isAuthenticated).toBe(false);
        });
    });
    
    describe('Request Deduplication', () => {
        test('should deduplicate identical requests', async () => {
            fetch.mockImplementation(() => 
                new Promise(resolve => 
                    setTimeout(() => resolve(new MockResponse({ data: 'test' })), 100)
                )
            );
            
            // Make two identical requests simultaneously
            const [result1, result2] = await Promise.all([
                apiClient.get('/test'),
                apiClient.get('/test')
            ]);
            
            expect(fetch).toHaveBeenCalledTimes(1);
            expect(result1).toEqual(result2);
        });
    });
    
    describe('Statistics and Cleanup', () => {
        test('should provide client statistics', () => {
            const stats = apiClient.getStats();
            
            expect(stats).toHaveProperty('cacheSize');
            expect(stats).toHaveProperty('pendingRequests');
            expect(stats).toHaveProperty('isAuthenticated');
            expect(stats).toHaveProperty('hasCSRFToken');
        });
        
        test('should cleanup resources on destroy', () => {
            apiClient.cache.set('test', 'value');
            apiClient.pendingRequests.set('test', Promise.resolve());
            
            apiClient.destroy();
            
            expect(apiClient.cache.size).toBe(0);
            expect(apiClient.pendingRequests.size).toBe(0);
            expect(apiClient.requestInterceptors.length).toBe(0);
            expect(apiClient.responseInterceptors.length).toBe(0);
        });
    });
    
    describe('Error Handling', () => {
        test('should handle network timeouts', async () => {
            // Mock AbortController to simulate timeout
            const mockController = {
                signal: {},
                abort: jest.fn()
            };
            global.AbortController = jest.fn(() => mockController);
            
            fetch.mockImplementation(() => 
                new Promise((resolve, reject) => {
                    setTimeout(() => {
                        const error = new Error('Request timeout');
                        error.name = 'AbortError';
                        reject(error);
                    }, 100);
                })
            );
            
            await expect(apiClient.get('/test')).rejects.toThrow();
        });
        
        test('should handle malformed JSON responses', async () => {
            const mockResponse = {
                ok: true,
                status: 200,
                json: jest.fn().mockRejectedValue(new Error('Invalid JSON'))
            };
            
            fetch.mockResolvedValueOnce(mockResponse);
            
            await expect(apiClient.get('/test')).rejects.toThrow('Invalid JSON');
        });
    });
});