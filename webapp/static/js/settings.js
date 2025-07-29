/**
 * Enhanced Settings Manager for Exam Grader Application
 * Handles UI settings, API integration, and real-time updates
 */

// Settings namespace
const SettingsManager = {
    // Current language
    currentLanguage: 'en',
    
    // Settings cache
    settingsCache: {},
    
    // Loading state
    isLoading: false,
    
    // Apply theme based on saved setting
    applyTheme: function() {
        // Get theme from localStorage or fallback to server-side setting
        const storedTheme = localStorage.getItem('theme');
        const theme = storedTheme || document.documentElement.getAttribute('data-theme') || 'light';
        
        // Apply theme to HTML element
        document.documentElement.setAttribute('data-theme', theme);
        document.body.setAttribute('data-theme', theme);
        
        // Apply appropriate class to body
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
            document.documentElement.classList.remove('light');
        } else {
            document.documentElement.classList.add('light');
            document.documentElement.classList.remove('dark');
        }
        
        console.log(`Theme applied: ${theme}`);
    },
    
    // Apply language based on saved setting
    applyLanguage: function() {
        // Get language from localStorage or fallback to server-side setting
        const storedLanguage = localStorage.getItem('language');
        const language = storedLanguage || document.documentElement.getAttribute('lang') || 'en';
        
        // Apply language to HTML element
        document.documentElement.setAttribute('lang', language);
        this.currentLanguage = language;
        
        // Apply translations to all elements with data-i18n attribute
        this.translatePage();
        
        console.log(`Language applied: ${language}`);
    },
    
    // Translate the page based on current language
    translatePage: function() {
        // Skip if translations are not available
        if (typeof ExamGrader === 'undefined' || !ExamGrader.translations || !ExamGrader.translations[this.currentLanguage]) {
            console.warn('Translations not available for', this.currentLanguage);
            return;
        }
        
        // Get the translation dictionary for current language
        const dictionary = ExamGrader.translations[this.currentLanguage];
        
        // Find all elements with data-i18n attribute
        const elements = document.querySelectorAll('[data-i18n]');
        
        // Update text content for each element
        elements.forEach(element => {
            const key = element.getAttribute('data-i18n');
            if (dictionary[key]) {
                element.textContent = dictionary[key];
            }
        });
        
        // Update placeholders for input elements
        const inputElements = document.querySelectorAll('input[data-i18n-placeholder]');
        inputElements.forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            if (dictionary[key]) {
                element.placeholder = dictionary[key];
            }
        });
        
        // Update titles/tooltips
        const titleElements = document.querySelectorAll('[data-i18n-title]');
        titleElements.forEach(element => {
            const key = element.getAttribute('data-i18n-title');
            if (dictionary[key]) {
                element.title = dictionary[key];
            }
        });
    },
    
    // Show notification
    showNotification: function(message, type = 'info') {
        // Try to use ExamGrader notification system if available
        if (typeof ExamGrader !== 'undefined' && ExamGrader.notificationManager) {
            ExamGrader.notificationManager.notify(message, type);
        } else {
            // Fallback to alert
            alert(type.toUpperCase() + ': ' + message);
        }
    },
    
    // Show loading state
    showLoading: function(show = true) {
        this.isLoading = show;
        const submitButton = document.querySelector('button[type="submit"]');
        if (submitButton) {
            if (show) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';
            } else {
                submitButton.disabled = false;
                submitButton.innerHTML = '<i class="fas fa-save mr-2"></i>Save Settings';
            }
        }
    },
    
    // Validate form data
    validateSettings: function(data) {
        const errors = [];
        
        // Validate max file size
        if (data.max_file_size && (data.max_file_size < 1 || data.max_file_size > 500)) {
            errors.push('Max file size must be between 1 and 500 MB');
        }
        
        // Validate results per page
        if (data.results_per_page && (data.results_per_page < 5 || data.results_per_page > 100)) {
            errors.push('Results per page must be between 5 and 100');
        }
        
        // Validate URL format for OCR API
        if (data.ocr_api_url && data.ocr_api_url.trim()) {
            try {
                new URL(data.ocr_api_url);
            } catch (e) {
                errors.push('OCR API URL must be a valid URL');
            }
        }
        
        return errors;
    },
    
    // Save settings via API
    saveSettingsAPI: async function(settingsData) {
        try {
            this.showLoading(true);
            
            // Validate settings
            const errors = this.validateSettings(settingsData);
            if (errors.length > 0) {
                this.showNotification('Validation errors: ' + errors.join(', '), 'error');
                return false;
            }
            
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(settingsData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.settingsCache = result.settings;
                this.showNotification('Settings saved successfully!', 'success');
                
                // Apply theme and language changes immediately
                if (settingsData.theme) {
                    localStorage.setItem('theme', settingsData.theme);
                    this.applyTheme();
                }
                
                if (settingsData.language) {
                    localStorage.setItem('language', settingsData.language);
                    this.currentLanguage = settingsData.language;
                    this.applyLanguage();
                }
                
                return true;
            } else {
                this.showNotification('Error saving settings: ' + result.error, 'error');
                return false;
            }
            
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showNotification('Network error saving settings', 'error');
            return false;
        } finally {
            this.showLoading(false);
        }
    },
    
    // Load settings from API
    loadSettingsAPI: async function() {
        try {
            const response = await fetch('/api/settings', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.settingsCache = result.settings;
                this.populateForm(result.settings);
                return result.settings;
            } else {
                console.error('Error loading settings:', result.error);
                return null;
            }
            
        } catch (error) {
            console.error('Error loading settings:', error);
            return null;
        }
    },
    
    // Populate form with settings data
    populateForm: function(settings) {
        Object.keys(settings).forEach(key => {
            const element = document.getElementById(key);
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = settings[key];
                } else if (element.type === 'password') {
                    // Don't populate password fields for security
                    element.placeholder = settings[key] ? '••••••••' : 'Enter API key';
                } else {
                    element.value = settings[key] || '';
                }
            }
        });
        
        // Handle allowed formats checkboxes
        if (settings.allowed_formats && Array.isArray(settings.allowed_formats)) {
            const checkboxes = document.querySelectorAll('input[name="allowed_formats"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = settings.allowed_formats.includes(checkbox.value);
            });
        }
    },
    
    // Get form data
    getFormData: function() {
        const form = document.getElementById('settings-form');
        if (!form) return {};
        
        const formData = new FormData(form);
        const data = {};
        
        // Handle regular form fields
        for (let [key, value] of formData.entries()) {
            if (key === 'allowed_formats') {
                // Handle multiple checkboxes
                if (!data[key]) data[key] = [];
                data[key].push(value);
            } else {
                data[key] = value;
            }
        }
        
        // Handle checkboxes that might not be in FormData if unchecked
        const checkboxes = form.querySelectorAll('input[type="checkbox"]:not([name="allowed_formats"])');
        checkboxes.forEach(checkbox => {
            if (!data.hasOwnProperty(checkbox.name)) {
                data[checkbox.name] = false;
            } else {
                data[checkbox.name] = true;
            }
        });
        
        // Convert string numbers to actual numbers
        if (data.max_file_size) data.max_file_size = parseInt(data.max_file_size);
        if (data.results_per_page) data.results_per_page = parseInt(data.results_per_page);
        
        return data;
    },
    
    // Reset settings to defaults
    resetToDefaults: async function() {
        if (!confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
            return;
        }
        
        try {
            this.showLoading(true);
            
            const response = await fetch('/api/settings/reset', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.settingsCache = result.settings;
                this.populateForm(result.settings);
                this.showNotification('Settings reset to defaults', 'success');
                
                // Apply theme and language changes
                localStorage.setItem('theme', result.settings.theme);
                localStorage.setItem('language', result.settings.language);
                this.applyTheme();
                this.currentLanguage = result.settings.language;
                this.applyLanguage();
            } else {
                this.showNotification('Error resetting settings: ' + result.error, 'error');
            }
            
        } catch (error) {
            console.error('Error resetting settings:', error);
            this.showNotification('Network error resetting settings', 'error');
        } finally {
            this.showLoading(false);
        }
    },
    
    // Export settings
    exportSettings: async function() {
        try {
            const response = await fetch('/api/settings/export', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Create and download file
                const dataStr = JSON.stringify(result.data, null, 2);
                const dataBlob = new Blob([dataStr], { type: 'application/json' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(dataBlob);
                link.download = result.filename;
                link.click();
                URL.revokeObjectURL(link.href);
                
                this.showNotification('Settings exported successfully', 'success');
            } else {
                this.showNotification('Error exporting settings: ' + result.error, 'error');
            }
            
        } catch (error) {
            console.error('Error exporting settings:', error);
            this.showNotification('Network error exporting settings', 'error');
        }
    },
    
    // Update service status
    updateServiceStatus: async function() {
        try {
            const response = await fetch('/api/service-status', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Update service status indicators
                Object.keys(result.status).forEach(service => {
                    const indicator = document.querySelector(`[data-service="${service}"] .status-indicator`);
                    if (indicator) {
                        const isOnline = result.status[service];
                        indicator.className = `w-3 h-3 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'}`;
                        
                        const statusText = indicator.parentElement.querySelector('.status-text');
                        if (statusText) {
                            statusText.textContent = isOnline ? 'Online' : 'Offline';
                        }
                    }
                });
            }
            
        } catch (error) {
            console.error('Error updating service status:', error);
        }
    },
    
    // Set up form event listeners
    setupFormListeners: function() {
        const form = document.getElementById('settings-form');
        if (!form) return;
        
        // Handle form submission
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (this.isLoading) return;
            
            const formData = this.getFormData();
            await this.saveSettingsAPI(formData);
        });
        
        // Handle real-time theme changes
        const themeSelect = document.getElementById('theme');
        if (themeSelect) {
            themeSelect.addEventListener('change', (e) => {
                localStorage.setItem('theme', e.target.value);
                this.applyTheme();
            });
        }
        
        // Handle real-time language changes
        const languageSelect = document.getElementById('language');
        if (languageSelect) {
            languageSelect.addEventListener('change', (e) => {
                localStorage.setItem('language', e.target.value);
                this.currentLanguage = e.target.value;
                this.applyLanguage();
            });
        }
        
        // Add reset button if it doesn't exist
        const resetButton = document.getElementById('reset-settings-btn');
        if (!resetButton) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                const resetBtn = document.createElement('button');
                resetBtn.type = 'button';
                resetBtn.id = 'reset-settings-btn';
                resetBtn.className = 'inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 mr-3';
                resetBtn.innerHTML = '<i class="fas fa-undo mr-2"></i>Reset to Defaults';
                resetBtn.addEventListener('click', () => this.resetToDefaults());
                
                submitButton.parentElement.insertBefore(resetBtn, submitButton);
            }
        }
        
        // Add export button if it doesn't exist
        const exportButton = document.getElementById('export-settings-btn');
        if (!exportButton) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                const exportBtn = document.createElement('button');
                exportBtn.type = 'button';
                exportBtn.id = 'export-settings-btn';
                exportBtn.className = 'inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 mr-3';
                exportBtn.innerHTML = '<i class="fas fa-download mr-2"></i>Export Settings';
                exportBtn.addEventListener('click', () => this.exportSettings());
                
                submitButton.parentElement.insertBefore(exportBtn, submitButton);
            }
        }
    },
    
    // Initialize settings
    init: async function() {
        console.log('Initializing Enhanced Settings Manager');
        
        // Get current language first
        const storedLanguage = localStorage.getItem('language');
        this.currentLanguage = storedLanguage || document.documentElement.getAttribute('lang') || 'en';
        
        // Apply saved settings
        this.applyTheme();
        this.applyLanguage();
        
        // Set up form event listeners
        this.setupFormListeners();
        
        // Load settings from API if on settings page
        const settingsForm = document.getElementById('settings-form');
        if (settingsForm) {
            await this.loadSettingsAPI();
            
            // Update service status
            this.updateServiceStatus();
            
            // Set up periodic service status updates
            setInterval(() => this.updateServiceStatus(), 30000); // Every 30 seconds
        }
        
        console.log('Enhanced Settings Manager initialized');
    }
};

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", function() {
    SettingsManager.init();
});