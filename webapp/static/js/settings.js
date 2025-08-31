/**
 * Enhanced Settings Manager for Exam Grader Application
 * Handles settings form, API integration, and real-time updates
 */

const ExamGraderSettings = {
    // State management
    isLoading: false,
    lastApiCall: 0,
    apiCallDelay: 1000,
    settingsCache: {},
    
    // Initialize settings manager
    init: function() {
        try {
            console.log('Initializing ExamGraderSettings...');
            
            // Set initialization flag to prevent unwanted notifications
            this._initializing = true;
            this._autoSaveSetup = false;
            
            // Check if we're on the settings page
            if (window.location.pathname !== '/settings') {
                console.log('Not on settings page, skipping initialization');
                return;
            }
            
            // Check if settings form exists
            const settingsForm = document.getElementById('settings-form');
            if (!settingsForm) {
                console.log('Settings form not found, skipping initialization');
                return;
            }
            
            // Set up settings-specific error handling
            this.setupErrorHandling();
            
            // Apply saved theme and language
            try {
                this.applyTheme();
                this.applyLanguage();
            } catch (e) {
                console.warn('Error applying theme/language:', e);
            }
            
            // Set up form handling
            try {
                this.setupFormHandling();
            } catch (e) {
                console.warn('Error setting up form handling:', e);
            }
            
            // Load current settings
            try {
                this.loadSettings();
            } catch (e) {
                console.warn('Error loading settings:', e);
            }
            
            // Set up service status updates (if available)
            try {
                this.setupServiceStatusUpdates();
            } catch (e) {
                console.warn('Error setting up service status updates:', e);
            }
            
            // Set up auto-save functionality
            try {
                this.setupAutoSave();
            } catch (e) {
                console.warn('Error setting up auto-save:', e);
            }
            
            // Clear initialization flag after a short delay
            setTimeout(() => {
                this._initializing = false;
                console.log('ExamGraderSettings initialization completed');
            }, 500);
            
            console.log('ExamGraderSettings initialized successfully');
        } catch (error) {
            console.error('Critical error during ExamGraderSettings initialization:', error);
            // Set flags to safe defaults
            this._initializing = false;
            this._autoSaveSetup = false;
            // Don't throw the error to prevent global error handlers from catching it
        }
    },
    
    // Setup settings-specific error handling
    setupErrorHandling: function() {
        // Override global error handlers for settings page only
        const originalErrorHandler = window.onerror;
        const originalRejectionHandler = window.onunhandledrejection;
        
        // Settings-specific error handler
        window.onerror = (message, source, lineno, colno, error) => {
            console.error('Settings page error:', { message, source, lineno, colno, error });
            
            // Handle settings-specific errors gracefully
            if (error && (error.name === 'TypeError' || error.name === 'ReferenceError')) {
                this.showNotification('A settings error occurred. Please refresh the page if issues persist.', 'warning');
            }
            
            // Don't propagate to global handler
            return true;
        };
        
        // Settings-specific promise rejection handler
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Settings page promise rejection:', event.reason);
            
            // Handle API-related rejections
            if (event.reason && event.reason.message && event.reason.message.includes('fetch')) {
                this.showNotification('Network error while saving settings. Please try again.', 'error');
                event.preventDefault();
            }
        });
        
        // Restore original handlers when leaving settings page
        window.addEventListener('beforeunload', () => {
            if (originalErrorHandler) {
                window.onerror = originalErrorHandler;
            }
        });
    },
    
    // Apply theme
    applyTheme: function() {
        const storedTheme = localStorage.getItem('theme');
        const theme = storedTheme || document.documentElement.getAttribute('data-theme') || 'light';
        
        document.documentElement.setAttribute('data-theme', theme);
        document.body.setAttribute('data-theme', theme);
        
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
            document.documentElement.classList.remove('light');
        } else {
            document.documentElement.classList.add('light');
            document.documentElement.classList.remove('dark');
        }
    },
    
    // Apply language
    applyLanguage: function() {
        const storedLanguage = localStorage.getItem('language');
        const language = storedLanguage || document.documentElement.getAttribute('lang') || 'en';
        
        document.documentElement.setAttribute('lang', language);
        this.currentLanguage = language;
        
        // Apply translations if available
        if (typeof ExamGrader !== 'undefined' && ExamGrader.translations) {
            this.translatePage();
        }
    },
    
    // Translate page elements
    translatePage: function() {
        if (!ExamGrader.translations || !ExamGrader.translations[this.currentLanguage]) {
            return;
        }
        
        const dictionary = ExamGrader.translations[this.currentLanguage];
        
        // Translate elements with data-i18n
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            if (dictionary[key]) {
                element.textContent = dictionary[key];
            }
        });
        
        // Translate placeholders
        document.querySelectorAll('input[data-i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            if (dictionary[key]) {
                element.placeholder = dictionary[key];
            }
        });
    },
    
    // Setup form handling
    setupFormHandling: function() {
        const form = document.getElementById('settings-form');
        if (!form) {
            console.warn('Settings form not found');
            return;
        }
        
        // Handle form submission with fallback
        const handleSubmit = async (e) => {
            e.preventDefault();
            
            if (this.isLoading) return;
            
            const formData = this.getFormData();
            const success = await this.saveSettingsAPI(formData);
            
            // If API save failed, fall back to regular form submission
            if (!success) {
                console.log('API save failed, falling back to form submission');
                this.showNotification('Falling back to standard form submission...', 'info');
                
                // Remove the event listener and submit normally
                form.removeEventListener('submit', handleSubmit);
                
                // Submit the form normally after a brief delay
                setTimeout(() => {
                    form.submit();
                }, 1000);
            }
        };
        
        form.addEventListener('submit', handleSubmit);
        
        // Handle reset button
        const resetBtn = document.getElementById('reset-settings-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.resetSettings();
            });
        }
        
        // Handle test API connection buttons
        const testLLMBtn = document.getElementById('test-llm-api');
        if (testLLMBtn) {
            testLLMBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.testAPIConnection('llm');
            });
        }
        
        const testOCRBtn = document.getElementById('test-ocr-api');
        if (testOCRBtn) {
            testOCRBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.testAPIConnection('ocr');
            });
        }
        
        // Handle export settings button
        const exportBtn = document.getElementById('export-settings-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.exportSettings();
            });
        }
        
        // Handle import settings button
        const importBtn = document.getElementById('import-settings-btn');
        const importFileInput = document.getElementById('import-file-input');
        if (importBtn && importFileInput) {
            importBtn.addEventListener('click', (e) => {
                e.preventDefault();
                importFileInput.click();
            });
            
            importFileInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (file) {
                    await this.importSettings(file);
                    // Reset the input so the same file can be selected again
                    e.target.value = '';
                }
            });
        }
        
        // Handle theme changes
        const themeSelect = document.getElementById('theme');
        if (themeSelect) {
            themeSelect.addEventListener('change', (e) => {
                localStorage.setItem('theme', e.target.value);
                this.applyTheme();
            });
        }
        
        // Handle language changes
        const languageSelect = document.getElementById('language');
        if (languageSelect) {
            languageSelect.addEventListener('change', (e) => {
                localStorage.setItem('language', e.target.value);
                this.applyLanguage();
            });
        }
    },
    
    // Get form data
    getFormData: function() {
        const form = document.getElementById('settings-form');
        if (!form) {
            console.error('Settings form not found');
            return {};
        }
        
        const formData = new FormData(form);
        const data = {};
        
        // Convert FormData to regular object
        for (let [key, value] of formData.entries()) {
            if (key === 'allowed_formats') {
                // Handle multiple checkboxes
                if (!data[key]) data[key] = [];
                data[key].push(value);
            } else if (key.endsWith('[]')) {
                // Handle array fields
                const cleanKey = key.slice(0, -2);
                if (!data[cleanKey]) data[cleanKey] = [];
                data[cleanKey].push(value);
            } else {
                // Handle different input types
                if (value === 'on' || value === 'off') {
                    data[key] = value === 'on';
                } else if (!isNaN(value) && value !== '') {
                    // Try to convert numbers, but avoid Infinity and NaN
                    const numValue = parseFloat(value);
                    if (isNaN(numValue) || !isFinite(numValue)) {
                        data[key] = value; // Keep as string if not a valid finite number
                    } else {
                        data[key] = numValue;
                    }
                } else {
                    data[key] = value;
                }
            }
        }
        
        // Handle checkboxes that might not be in FormData when unchecked
        const checkboxes = form.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            if (!checkbox.name.includes('allowed_formats')) {
                data[checkbox.name] = checkbox.checked;
            }
        });
        
        // Ensure allowed_formats is always an array
        if (!data.allowed_formats) {
            data.allowed_formats = [];
        }
        
        return data;
    },
    
    // Validate settings data
    validateSettings: function(data) {
        const errors = [];
        
        // Validate and sanitize max file size
        if (data.max_file_size !== undefined && data.max_file_size !== null) {
            if (data.max_file_size === '' || data.max_file_size === 'unlimited') {
                // Allow empty or "unlimited" to mean no limit
                data.max_file_size = null;
            } else {
                const size = parseFloat(data.max_file_size);
                if (isNaN(size) || !isFinite(size) || size < 1 || size > 1000) {
                    errors.push('Max file size must be between 1 and 1000 MB, or leave empty for unlimited');
                } else {
                    data.max_file_size = size; // Ensure it's a proper finite number
                }
            }
        }
        
        // Validate and sanitize results per page
        if (data.results_per_page !== undefined) {
            const count = parseInt(data.results_per_page);
            if (isNaN(count) || !isFinite(count) || count < 5 || count > 100) {
                errors.push('Results per page must be between 5 and 100');
            } else {
                data.results_per_page = count; // Ensure it's a proper finite number
            }
        }
        
        // Validate API keys format (basic check)
        if (data.llm_api_key && data.llm_api_key.length > 0 && data.llm_api_key.length < 10) {
            errors.push('LLM API key appears to be too short');
        }
        
        if (data.ocr_api_key && data.ocr_api_key.length > 0 && data.ocr_api_key.length < 10) {
            errors.push('OCR API key appears to be too short');
        }
        
        // Validate URLs
        if (data.llm_base_url && data.llm_base_url.trim()) {
            try {
                new URL(data.llm_base_url);
            } catch (e) {
                errors.push('LLM Base URL must be a valid URL');
            }
        }
        
        if (data.ocr_api_url && data.ocr_api_url.trim()) {
            try {
                new URL(data.ocr_api_url);
            } catch (e) {
                errors.push('OCR API URL must be a valid URL');
            }
        }
        
        // Validate allowed formats
        if (data.allowed_formats !== undefined) {
            let formatCount = 0;
            
            if (Array.isArray(data.allowed_formats)) {
                formatCount = data.allowed_formats.length;
            } else if (typeof data.allowed_formats === 'string') {
                // Count non-empty formats in comma-separated string
                formatCount = data.allowed_formats
                    .split(',')
                    .map(format => format.trim())
                    .filter(format => format.length > 0).length;
            }
            
            if (formatCount === 0) {
                errors.push('At least one file format must be allowed');
            }
        }
        
        return errors;
    },
    
    // Load settings from API
    loadSettings: async function() {
        try {
            const response = await fetch('/api/settings', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.settings) {
                    this.settingsCache = result.settings;
                    this.populateForm(result.settings);
                }
            }
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    },
    
    // Populate form with settings data
    populateForm: function(settings) {
        try {
            const form = document.getElementById('settings-form');
            if (!form) {
                console.warn('Settings form not found for population');
                return;
            }
            
            console.log('Populating form with settings:', settings);
            
            // Temporarily disable auto-save during form population
            const wasAutoSaveSetup = this._autoSaveSetup || false;
            this._autoSaveSetup = false;
        
            try {
                Object.keys(settings).forEach(key => {
                    const elements = form.querySelectorAll(`[name="${key}"]`);
                    
                    elements.forEach(element => {
                        try {
                            if (element.type === 'checkbox' && key !== 'allowed_formats') {
                                element.checked = Boolean(settings[key]);
                            } else if (element.type === 'radio') {
                                element.checked = element.value === String(settings[key]);
                            } else if (element.type === 'select-one') {
                                element.value = settings[key] || '';
                            } else if (element.type !== 'checkbox') {
                                // Special handling for max_file_size - null means unlimited
                                if (key === 'max_file_size' && (settings[key] === null || settings[key] === 'inf')) {
                                    element.value = ''; // Empty field for unlimited
                                    element.placeholder = 'Unlimited';
                                } else {
                                    element.value = settings[key] || '';
                                }
                            }
                        } catch (e) {
                            console.warn(`Error setting value for ${key}:`, e);
                        }
                    });
                });
                
                // Handle allowed_formats checkboxes specially
                if (settings.allowed_formats) {
                    try {
                        const formatCheckboxes = form.querySelectorAll('input[name="allowed_formats"]');
                        let allowedFormats;
                        
                        // Handle both string (comma-separated) and array formats
                        if (Array.isArray(settings.allowed_formats)) {
                            allowedFormats = settings.allowed_formats;
                        } else if (typeof settings.allowed_formats === 'string') {
                            // Split comma-separated string and clean up
                            allowedFormats = settings.allowed_formats
                                .split(',')
                                .map(format => format.trim())
                                .filter(format => format.length > 0);
                        } else {
                            allowedFormats = [settings.allowed_formats];
                        }
                            
                        formatCheckboxes.forEach(checkbox => {
                            try {
                                checkbox.checked = allowedFormats.includes(checkbox.value);
                            } catch (e) {
                                console.warn(`Error setting checkbox for format ${checkbox.value}:`, e);
                            }
                        });
                    } catch (e) {
                        console.warn('Error handling allowed_formats:', e);
                    }
                }
                
                // Re-enable auto-save after a short delay to prevent triggering on population
                setTimeout(() => {
                    this._autoSaveSetup = wasAutoSaveSetup;
                }, 100);
                
                // Only trigger change events for UI updates, not auto-save
                try {
                    const changeEvent = new Event('change', { bubbles: true });
                    form.querySelectorAll('input, select, textarea').forEach(element => {
                        try {
                            element.dispatchEvent(changeEvent);
                        } catch (e) {
                            console.warn('Error dispatching change event:', e);
                        }
                    });
                } catch (e) {
                    console.warn('Error triggering change events:', e);
                }
                
            } catch (error) {
                console.error('Error during form population:', error);
                // Re-enable auto-save even if there was an error
                setTimeout(() => {
                    this._autoSaveSetup = wasAutoSaveSetup;
                }, 100);
            }
        } catch (error) {
            console.error('Critical error in populateForm:', error);
        }
    },
    
    // Save settings via API
    saveSettingsAPI: async function(settingsData) {
        try {
            this.showLoading(true);
            
            // Rate limiting
            const now = Date.now();
            if (now - this.lastApiCall < this.apiCallDelay) {
                await new Promise(resolve => setTimeout(resolve, this.apiCallDelay - (now - this.lastApiCall)));
            }
            this.lastApiCall = Date.now();
            
            // Validate settings
            const errors = this.validateSettings(settingsData);
            if (errors.length > 0) {
                this.showNotification('Validation errors: ' + errors.join(', '), 'error');
                return false;
            }
            
            // Get CSRF token
            const csrfToken = document.querySelector('meta[name=csrf-token]')?.getAttribute('content') ||
                             document.querySelector('input[name=csrf_token]')?.value;
            
            const headers = {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            };
            
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }
            
            console.log('Saving settings:', settingsData);
            
            // Sanitize data before JSON serialization to prevent Infinity/NaN issues
            const sanitizedData = this.sanitizeForJSON(settingsData);
            
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(sanitizedData),
                credentials: 'same-origin'
            });
            
            // Check if response is HTML (likely a redirect to login page)
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                console.log('Received HTML response, likely authentication issue');
                this.showNotification('Authentication required. Redirecting to login...', 'error');
                setTimeout(() => {
                    window.location.href = '/auth/login';
                }, 2000);
                return false;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                // Only show success notification if not initializing
                if (!this._initializing) {
                    this.showNotification('Settings saved successfully!', 'success');
                }
                this.settingsCache = settingsData;
                
                // Apply theme and language changes immediately
                if (settingsData.theme) {
                    localStorage.setItem('theme', settingsData.theme);
                    this.applyTheme();
                }
                if (settingsData.language) {
                    localStorage.setItem('language', settingsData.language);
                    this.applyLanguage();
                }
                
                return true;
            } else {
                // Always show error notifications
                this.showNotification('Failed to save settings: ' + (result.error || 'Unknown error'), 'error');
                return false;
            }
            
        } catch (error) {
            console.error('Settings save error:', error);
            this.showNotification('Error saving settings: ' + error.message, 'error');
            return false;
        } finally {
            this.showLoading(false);
        }
    },
    
    // Reset settings to defaults
    resetSettings: async function() {
        if (!confirm('Are you sure you want to reset all settings to defaults? This action cannot be undone.')) {
            return;
        }
        
        try {
            this.showLoading(true);
            
            const csrfToken = document.querySelector('meta[name=csrf-token]')?.getAttribute('content') ||
                             document.querySelector('input[name=csrf_token]')?.value;
            
            const headers = {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            };
            
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }
            
            const response = await fetch('/api/settings/reset', {
                method: 'POST',
                headers: headers,
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Settings reset to defaults successfully!', 'success');
                // Reload the page to show default values
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                this.showNotification('Failed to reset settings: ' + (result.error || 'Unknown error'), 'error');
            }
            
        } catch (error) {
            console.error('Reset settings error:', error);
            this.showNotification('Error resetting settings: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    },
    
    // Test API connection
    testAPIConnection: async function(apiType) {
        const apiKey = document.querySelector(`input[name="${apiType}_api_key"]`)?.value;
        
        if (!apiKey || apiKey.trim() === '') {
            this.showNotification(`Please enter a ${apiType.toUpperCase()} API key first`, 'warning');
            return;
        }
        
        try {
            const testBtn = document.getElementById(`test-${apiType}-api`);
            if (testBtn) {
                testBtn.disabled = true;
                testBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Testing...';
            }
            
            // Prepare test data
            let testData = {
                api_key: apiKey.trim()
            };
            
            if (apiType === 'llm') {
                const model = document.querySelector('input[name="llm_model"]')?.value || 'deepseek-chat';
                const baseUrl = document.querySelector('input[name="llm_base_url"]')?.value || '';
                testData.model = model.trim();
                testData.base_url = baseUrl.trim();
            } else if (apiType === 'ocr') {
                const apiUrl = document.querySelector('input[name="ocr_api_url"]')?.value || 'https://www.handwritingocr.com/api/v3';
                testData.api_url = apiUrl.trim();
            }
            
            // Get CSRF token with debugging
            const csrfToken = document.querySelector('meta[name=csrf-token]')?.getAttribute('content') ||
                             document.querySelector('input[name=csrf_token]')?.value;
            
            console.log(`Testing ${apiType} API - CSRF Token:`, csrfToken ? 'Found' : 'Missing');
            
            const headers = {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            };
            
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            } else {
                console.warn('CSRF token missing - request may fail with 400 error');
            }
            
            console.log(`Making ${apiType} API test request to:`, `/api/settings/test-${apiType}`);
            console.log('Request headers:', headers);
            console.log('Request data:', testData);
            
            // Make API test request
            const response = await fetch(`/api/settings/test-${apiType}`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(testData),
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(result.message, 'success', 8000);
                
                // Show additional details if available
                if (result.response_time) {
                    console.log(`${apiType.toUpperCase()} API Response Time:`, result.response_time + 'ms');
                }
                if (result.response) {
                    console.log(`${apiType.toUpperCase()} API Response:`, result.response);
                }
                if (result.test_result) {
                    console.log(`${apiType.toUpperCase()} API Test Result:`, result.test_result);
                }
            } else {
                // Display the user-friendly error message
                this.showNotification(result.error, 'error', 12000);
                
                // Log technical details for debugging if available
                if (result.technical_details) {
                    console.error(`${apiType.toUpperCase()} API Technical Details:`, result.technical_details);
                }
            }
            
        } catch (error) {
            console.error(`${apiType} API test error:`, error);
            this.showNotification(`Error testing ${apiType.toUpperCase()} API: ` + error.message, 'error', 8000);
        } finally {
            const testBtn = document.getElementById(`test-${apiType}-api`);
            if (testBtn) {
                testBtn.disabled = false;
                testBtn.innerHTML = `<i class="fas fa-plug mr-2"></i>Test`;
            }
        }
    },
    
    // Export settings
    exportSettings: async function() {
        try {
            this.showLoading(true);
            
            const response = await fetch('/api/settings/export', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                // Create and download the file
                const blob = new Blob([JSON.stringify(result.data, null, 2)], {
                    type: 'application/json'
                });
                
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = result.filename || 'settings_export.json';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showNotification('Settings exported successfully!', 'success');
            } else {
                this.showNotification('Failed to export settings: ' + (result.error || 'Unknown error'), 'error');
            }
            
        } catch (error) {
            console.error('Export settings error:', error);
            this.showNotification('Error exporting settings: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    },
    
    // Import settings
    importSettings: async function(file) {
        try {
            this.showLoading(true);
            
            // Read the file
            const fileContent = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (e) => resolve(e.target.result);
                reader.onerror = (e) => reject(new Error('Failed to read file'));
                reader.readAsText(file);
            });
            
            // Parse JSON
            let settingsData;
            try {
                settingsData = JSON.parse(fileContent);
            } catch (e) {
                throw new Error('Invalid JSON file format');
            }
            
            // Validate the settings data
            if (!settingsData || typeof settingsData !== 'object') {
                throw new Error('Invalid settings file format');
            }
            
            // Confirm import
            const confirmMessage = `Are you sure you want to import these settings? This will overwrite your current configuration.\n\nFile: ${file.name}\nSize: ${(file.size / 1024).toFixed(1)} KB`;
            if (!confirm(confirmMessage)) {
                return;
            }
            
            // Send to server
            const success = await this.saveSettingsAPI(settingsData);
            
            if (success) {
                this.showNotification('Settings imported successfully! Reloading page...', 'success');
                // Reload the page to show imported settings
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                this.showNotification('Failed to import settings. Please check the file format.', 'error');
            }
            
        } catch (error) {
            console.error('Import settings error:', error);
            this.showNotification('Error importing settings: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    },
    
    // Show/hide loading state
    showLoading: function(show) {
        this.isLoading = show;
        const submitBtn = document.querySelector('#settings-form button[type="submit"]');
        const form = document.getElementById('settings-form');
        
        if (submitBtn) {
            submitBtn.disabled = show;
            if (show) {
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';
                submitBtn.classList.add('opacity-75', 'cursor-not-allowed');
            } else {
                submitBtn.innerHTML = '<i class="fas fa-save mr-2"></i>Save Settings';
                submitBtn.classList.remove('opacity-75', 'cursor-not-allowed');
            }
        }
        
        // Disable/enable form inputs during loading
        if (form) {
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.disabled = show;
            });
        }
        
        // Show/hide loading overlay if it exists
        const loadingOverlay = document.getElementById('settings-loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = show ? 'flex' : 'none';
        }
    },
    
    // Show notification
    showNotification: function(message, type = 'info', duration = 5000) {
        // Remove existing notifications
        const existing = document.querySelectorAll('.settings-notification');
        existing.forEach(el => {
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 300);
        });
        
        // Create notification element
        const notification = document.createElement('div');
        const iconClass = {
            'error': 'fas fa-exclamation-circle',
            'success': 'fas fa-check-circle',
            'warning': 'fas fa-exclamation-triangle',
            'info': 'fas fa-info-circle'
        }[type] || 'fas fa-info-circle';
        
        const bgClass = {
            'error': 'bg-red-500 text-white',
            'success': 'bg-green-500 text-white',
            'warning': 'bg-yellow-500 text-black',
            'info': 'bg-blue-500 text-white'
        }[type] || 'bg-blue-500 text-white';
        
        notification.className = `settings-notification fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 transition-all duration-300 transform translate-x-full ${bgClass} max-w-md`;
        notification.innerHTML = `
            <div class="flex items-start">
                <i class="${iconClass} mr-3 mt-1 flex-shrink-0"></i>
                <span class="flex-1 text-sm leading-relaxed">${message}</span>
                <button class="ml-3 text-white hover:text-gray-200 flex-shrink-0" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);
        
        // Auto-remove after specified duration
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.classList.add('translate-x-full');
                    setTimeout(() => notification.remove(), 300);
                }
            }, duration);
        }
    },
    
    // Setup service status updates
    setupServiceStatusUpdates: async function() {
        // Try to update service status once, and only set up periodic updates if it works
        try {
            const response = await fetch('/api/service-status', {
                method: 'GET',
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            
            if (response.ok) {
                // Service status API is available, set up periodic updates
                this.updateServiceStatus();
                setInterval(() => this.updateServiceStatus(), 30000); // Every 30 seconds
            }
        } catch (error) {
            // Service status API not available, skip periodic updates
            console.log('Service status API not available, skipping periodic updates');
        }
    },
    
    // Update service status
    updateServiceStatus: async function() {
        try {
            const response = await fetch('/api/service-status', {
                method: 'GET',
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.status) {
                    this.displayServiceStatus(result.status);
                }
            }
        } catch (error) {
            console.error('Error updating service status:', error);
        }
    },
    
    // Display service status
    displayServiceStatus: function(status) {
        // Update service status indicators if they exist
        Object.keys(status).forEach(service => {
            const indicator = document.querySelector(`[data-service="${service}"] .status-indicator`);
            if (indicator) {
                indicator.className = status[service] 
                    ? 'w-3 h-3 bg-green-500 rounded-full status-indicator'
                    : 'w-3 h-3 bg-red-500 rounded-full status-indicator';
            }
            
            const statusText = document.querySelector(`[data-service="${service}"] .status-text`);
            if (statusText) {
                statusText.textContent = status[service] ? 'Online' : 'Offline';
            }
        });
    },
    
    // Setup auto-save functionality
    setupAutoSave: function() {
        const form = document.getElementById('settings-form');
        if (!form) return;
        
        // Mark that auto-save is set up
        this._autoSaveSetup = true;
        
        let autoSaveTimeout;
        const autoSaveDelay = 2000; // 2 seconds after last change
        
        // Check if auto-save is enabled
        const autoSaveEnabled = () => {
            const autoSaveCheckbox = form.querySelector('input[name="auto_save"]');
            return autoSaveCheckbox ? autoSaveCheckbox.checked : false;
        };
        
        // Auto-save function
        const performAutoSave = async () => {
            // Don't auto-save if disabled, loading, or during form population
            if (!autoSaveEnabled() || this.isLoading || !this._autoSaveSetup) return;
            
            console.log('Performing auto-save...');
            const formData = this.getFormData();
            const success = await this.saveSettingsAPI(formData);
            
            if (success) {
                // Show subtle auto-save indicator
                const indicator = document.getElementById('auto-save-indicator');
                if (indicator) {
                    indicator.textContent = 'Auto-saved at ' + new Date().toLocaleTimeString();
                    indicator.classList.remove('opacity-0');
                    indicator.classList.add('opacity-100');
                    
                    setTimeout(() => {
                        indicator.classList.remove('opacity-100');
                        indicator.classList.add('opacity-0');
                    }, 3000);
                }
            }
        };
        
        // Add change listeners to form inputs
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('change', () => {
                if (autoSaveEnabled() && this._autoSaveSetup) {
                    clearTimeout(autoSaveTimeout);
                    autoSaveTimeout = setTimeout(performAutoSave, autoSaveDelay);
                }
            });
            
            // For text inputs, also listen to input events
            if (input.type === 'text' || input.type === 'email' || input.type === 'password' || input.type === 'url' || input.tagName === 'TEXTAREA') {
                input.addEventListener('input', () => {
                    if (autoSaveEnabled() && this._autoSaveSetup) {
                        clearTimeout(autoSaveTimeout);
                        autoSaveTimeout = setTimeout(performAutoSave, autoSaveDelay);
                    }
                });
            }
        });
    },
    
    // Sanitize data for JSON serialization (remove Infinity, NaN, etc.)
    sanitizeForJSON: function(obj) {
        if (obj === null || obj === undefined) {
            return obj;
        }
        
        if (typeof obj === 'number') {
            if (!isFinite(obj)) {
                console.warn('Sanitizing non-finite number:', obj);
                return null; // Convert Infinity, -Infinity, NaN to null
            }
            return obj;
        }
        
        if (typeof obj === 'string' || typeof obj === 'boolean') {
            return obj;
        }
        
        if (Array.isArray(obj)) {
            return obj.map(item => this.sanitizeForJSON(item));
        }
        
        if (typeof obj === 'object') {
            const sanitized = {};
            for (const [key, value] of Object.entries(obj)) {
                const sanitizedValue = this.sanitizeForJSON(value);
                if (sanitizedValue !== null || value === null) {
                    sanitized[key] = sanitizedValue;
                }
            }
            return sanitized;
        }
        
        return obj;
    }
};

// Initialize settings when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    try {
        // Only initialize if we're on the settings page
        if (window.location.pathname === '/settings') {
            ExamGraderSettings.init();
        }
    } catch (error) {
        console.error('Failed to initialize ExamGraderSettings:', error);
        // Don't re-throw to prevent global error handlers from showing notifications
    }
});