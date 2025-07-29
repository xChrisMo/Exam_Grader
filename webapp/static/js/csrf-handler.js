/**
 * Enhanced CSRF Token Handler
 * Provides robust CSRF token management for AJAX requests
 */

ExamGrader.csrf = ExamGrader.csrf || {
    // Cache for CSRF token
    _token: null,
    _tokenExpiry: null,
    
    // Get CSRF token with caching and refresh
    getToken: function() {
        // Check if cached token is still valid
        if (this._token && this._tokenExpiry && Date.now() < this._tokenExpiry) {
            return this._token;
        }
        
        // Try to get from meta tag first
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            this._token = metaToken.getAttribute('content');
            this._tokenExpiry = Date.now() + (30 * 60 * 1000); // 30 minutes
            return this._token;
        }
        
        // Try to get from hidden input
        const inputToken = document.querySelector('input[name="csrf_token"]');
        if (inputToken) {
            this._token = inputToken.value;
            this._tokenExpiry = Date.now() + (30 * 60 * 1000); // 30 minutes
            return this._token;
        }
        
        // Fallback: fetch from server
        this.refreshToken();
        return this._token;
    },
    
    // Refresh CSRF token from server
    refreshToken: function() {
        try {
            const xhr = new XMLHttpRequest();
            xhr.open('GET', '/get-csrf-token', false); // Synchronous for immediate use
            xhr.send();
            
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                if (data.success && data.csrf_token) {
                    this._token = data.csrf_token;
                    this._tokenExpiry = Date.now() + (30 * 60 * 1000); // 30 minutes
                }
            }
        } catch (error) {
            console.error('Failed to refresh CSRF token:', error);
        }
    },
    
    // Setup CSRF token for all AJAX requests
    setupAjaxCSRF: function() {
        // jQuery setup (if available)
        if (typeof $ !== 'undefined') {
            $.ajaxSetup({
                beforeSend: function(xhr, settings) {
                    if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                        xhr.setRequestHeader("X-CSRFToken", ExamGrader.csrf.getToken());
                    }
                }
            });
        }
        
        // Fetch API interceptor
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            if (options.method && !/^(GET|HEAD|OPTIONS|TRACE)$/i.test(options.method)) {
                options.headers = options.headers || {};
                if (!options.headers['X-CSRFToken']) {
                    options.headers['X-CSRFToken'] = ExamGrader.csrf.getToken();
                }
            }
            return originalFetch(url, options);
        };
    },
    
    // Validate CSRF token
    validateToken: function() {
        const token = this.getToken();
        return token && token.length > 0;
    }
};

// Auto-setup CSRF handling when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    ExamGrader.csrf.setupAjaxCSRF();
});
