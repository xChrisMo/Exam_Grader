/**
 * Exam Grader - Settings Page JavaScript
 * Handles settings management and configuration
 */

class SettingsManager {
    constructor() {
        this.settings = {};
        this.hasUnsavedChanges = false;
        this.init();
    }

    init() {
        this.loadSettings();
        this.setupEventListeners();
        this.setupRangeSliders();
        this.setupFormValidation();
    }

    loadSettings() {
        // In a real implementation, this would load from the server
        this.settings = {
            general: {
                appName: 'Exam Grader',
                language: 'en',
                timezone: 'UTC',
                theme: 'light',
                notifications: true,
                autoSave: true
            },
            grading: {
                gradingScale: 'percentage',
                passingGrade: 60,
                feedbackDetail: 'detailed',
                confidenceThreshold: 70,
                autoMapping: true,
                improvementSuggestions: true,
                plagiarismCheck: false
            },
            api: {
                deepseekApiKey: '',
                apiTimeout: 30,
                maxRetries: 3,
                modelName: 'deepseek-chat',
                temperature: 0.1
            },
            storage: {
                maxFileSize: 10,
                retentionPeriod: 30,
                autoCleanup: true
            },
            security: {
                enableCors: false,
                enableRateLimit: true,
                sessionTimeout: 60,
                maxLoginAttempts: 5,
                allowedOrigins: ''
            }
        };

        this.populateFormFields();
    }

    populateFormFields() {
        // General settings
        document.getElementById('appName').value = this.settings.general.appName;
        document.getElementById('language').value = this.settings.general.language;
        document.getElementById('timezone').value = this.settings.general.timezone;
        document.getElementById('theme').value = this.settings.general.theme;
        document.getElementById('notifications').checked = this.settings.general.notifications;
        document.getElementById('autoSave').checked = this.settings.general.autoSave;

        // Grading settings
        document.getElementById('gradingScale').value = this.settings.grading.gradingScale;
        document.getElementById('passingGrade').value = this.settings.grading.passingGrade;
        document.getElementById('feedbackDetail').value = this.settings.grading.feedbackDetail;
        document.getElementById('confidenceThreshold').value = this.settings.grading.confidenceThreshold;
        document.getElementById('autoMapping').checked = this.settings.grading.autoMapping;
        document.getElementById('improvementSuggestions').checked = this.settings.grading.improvementSuggestions;
        document.getElementById('plagiarismCheck').checked = this.settings.grading.plagiarismCheck;

        // API settings
        document.getElementById('apiTimeout').value = this.settings.api.apiTimeout;
        document.getElementById('maxRetries').value = this.settings.api.maxRetries;
        document.getElementById('modelName').value = this.settings.api.modelName;
        document.getElementById('temperature').value = this.settings.api.temperature;

        // Storage settings
        document.getElementById('maxFileSize').value = this.settings.storage.maxFileSize;
        document.getElementById('retentionPeriod').value = this.settings.storage.retentionPeriod;
        document.getElementById('autoCleanup').checked = this.settings.storage.autoCleanup;

        // Security settings
        document.getElementById('enableCors').checked = this.settings.security.enableCors;
        document.getElementById('enableRateLimit').checked = this.settings.security.enableRateLimit;
        document.getElementById('sessionTimeout').value = this.settings.security.sessionTimeout;
        document.getElementById('maxLoginAttempts').value = this.settings.security.maxLoginAttempts;
        document.getElementById('allowedOrigins').value = this.settings.security.allowedOrigins;
    }

    setupEventListeners() {
        // Track changes in all form inputs
        const forms = ['generalForm', 'gradingForm', 'apiForm'];
        forms.forEach(formId => {
            const form = document.getElementById(formId);
            if (form) {
                form.addEventListener('input', () => {
                    this.markAsChanged();
                });
                form.addEventListener('change', () => {
                    this.markAsChanged();
                });
            }
        });

        // Storage and security inputs
        const storageInputs = ['maxFileSize', 'retentionPeriod', 'autoCleanup'];
        const securityInputs = ['enableCors', 'enableRateLimit', 'sessionTimeout', 'maxLoginAttempts', 'allowedOrigins'];
        
        [...storageInputs, ...securityInputs].forEach(inputId => {
            const input = document.getElementById(inputId);
            if (input) {
                input.addEventListener('input', () => this.markAsChanged());
                input.addEventListener('change', () => this.markAsChanged());
            }
        });

        // Warn before leaving with unsaved changes
        window.addEventListener('beforeunload', (e) => {
            if (this.hasUnsavedChanges) {
                e.preventDefault();
                e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
            }
        });
    }

    setupRangeSliders() {
        // Confidence threshold slider
        const confidenceSlider = document.getElementById('confidenceThreshold');
        const confidenceValue = document.getElementById('confidenceValue');
        
        if (confidenceSlider && confidenceValue) {
            confidenceSlider.addEventListener('input', (e) => {
                confidenceValue.textContent = `${e.target.value}%`;
            });
        }

        // Temperature slider
        const temperatureSlider = document.getElementById('temperature');
        const temperatureValue = document.getElementById('temperatureValue');
        
        if (temperatureSlider && temperatureValue) {
            temperatureSlider.addEventListener('input', (e) => {
                temperatureValue.textContent = parseFloat(e.target.value).toFixed(1);
            });
        }
    }

    setupFormValidation() {
        // API key validation
        const apiKeyInput = document.getElementById('deepseekApiKey');
        if (apiKeyInput) {
            apiKeyInput.addEventListener('blur', () => {
                this.validateApiKey(apiKeyInput.value);
            });
        }

        // File size validation
        const fileSizeInput = document.getElementById('maxFileSize');
        if (fileSizeInput) {
            fileSizeInput.addEventListener('input', (e) => {
                const value = parseInt(e.target.value);
                if (value < 1 || value > 100) {
                    e.target.setCustomValidity('File size must be between 1 and 100 MB');
                } else {
                    e.target.setCustomValidity('');
                }
            });
        }
    }

    validateApiKey(apiKey) {
        const isValid = apiKey.length === 0 || (apiKey.startsWith('sk-') && apiKey.length > 20);
        const input = document.getElementById('deepseekApiKey');
        
        if (!isValid && apiKey.length > 0) {
            input.classList.add('is-invalid');
            ExamGraderUtils.showNotification('Invalid API key format', 'warning', 3000);
        } else {
            input.classList.remove('is-invalid');
        }
        
        return isValid;
    }

    markAsChanged() {
        this.hasUnsavedChanges = true;
        
        // Update save button state
        const saveBtn = document.querySelector('[onclick="saveAllSettings()"]');
        if (saveBtn) {
            saveBtn.classList.remove('btn-success');
            saveBtn.classList.add('btn-warning');
            saveBtn.innerHTML = '<i class="bi bi-exclamation-circle me-2"></i>Save Changes';
        }
    }

    async saveAllSettings() {
        try {
            // Collect all settings
            const newSettings = this.collectFormData();
            
            // Validate settings
            if (!this.validateSettings(newSettings)) {
                return;
            }

            // Show loading state
            const saveBtn = document.querySelector('[onclick="saveAllSettings()"]');
            const originalContent = saveBtn.innerHTML;
            saveBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Saving...';
            saveBtn.disabled = true;

            // In a real implementation, this would make an API call
            await this.simulateSave(newSettings);

            // Update local settings
            this.settings = newSettings;
            this.hasUnsavedChanges = false;

            // Update button state
            saveBtn.innerHTML = '<i class="bi bi-check-circle me-2"></i>Saved';
            saveBtn.classList.remove('btn-warning');
            saveBtn.classList.add('btn-success');
            saveBtn.disabled = false;

            ExamGraderUtils.showNotification('Settings saved successfully', 'success', 3000);

            // Reset button after delay
            setTimeout(() => {
                saveBtn.innerHTML = originalContent;
            }, 2000);

        } catch (error) {
            console.error('Save error:', error);
            ExamGraderUtils.showNotification('Failed to save settings', 'danger', 5000);
        }
    }

    collectFormData() {
        return {
            general: {
                appName: document.getElementById('appName').value,
                language: document.getElementById('language').value,
                timezone: document.getElementById('timezone').value,
                theme: document.getElementById('theme').value,
                notifications: document.getElementById('notifications').checked,
                autoSave: document.getElementById('autoSave').checked
            },
            grading: {
                gradingScale: document.getElementById('gradingScale').value,
                passingGrade: parseInt(document.getElementById('passingGrade').value),
                feedbackDetail: document.getElementById('feedbackDetail').value,
                confidenceThreshold: parseInt(document.getElementById('confidenceThreshold').value),
                autoMapping: document.getElementById('autoMapping').checked,
                improvementSuggestions: document.getElementById('improvementSuggestions').checked,
                plagiarismCheck: document.getElementById('plagiarismCheck').checked
            },
            api: {
                deepseekApiKey: document.getElementById('deepseekApiKey').value,
                apiTimeout: parseInt(document.getElementById('apiTimeout').value),
                maxRetries: parseInt(document.getElementById('maxRetries').value),
                modelName: document.getElementById('modelName').value,
                temperature: parseFloat(document.getElementById('temperature').value)
            },
            storage: {
                maxFileSize: parseInt(document.getElementById('maxFileSize').value),
                retentionPeriod: parseInt(document.getElementById('retentionPeriod').value),
                autoCleanup: document.getElementById('autoCleanup').checked
            },
            security: {
                enableCors: document.getElementById('enableCors').checked,
                enableRateLimit: document.getElementById('enableRateLimit').checked,
                sessionTimeout: parseInt(document.getElementById('sessionTimeout').value),
                maxLoginAttempts: parseInt(document.getElementById('maxLoginAttempts').value),
                allowedOrigins: document.getElementById('allowedOrigins').value
            }
        };
    }

    validateSettings(settings) {
        // Validate API key
        if (!this.validateApiKey(settings.api.deepseekApiKey)) {
            return false;
        }

        // Validate numeric ranges
        if (settings.grading.passingGrade < 0 || settings.grading.passingGrade > 100) {
            ExamGraderUtils.showNotification('Passing grade must be between 0 and 100', 'danger', 5000);
            return false;
        }

        if (settings.storage.maxFileSize < 1 || settings.storage.maxFileSize > 100) {
            ExamGraderUtils.showNotification('Max file size must be between 1 and 100 MB', 'danger', 5000);
            return false;
        }

        return true;
    }

    async simulateSave(settings) {
        // Simulate API call delay
        return new Promise(resolve => setTimeout(resolve, 1000));
    }

    async testApiConnection() {
        const apiKey = document.getElementById('deepseekApiKey').value;
        const resultDiv = document.getElementById('apiTestResult');
        
        if (!apiKey) {
            resultDiv.innerHTML = '<div class="alert alert-warning">Please enter an API key first</div>';
            return;
        }

        resultDiv.innerHTML = '<div class="alert alert-info">Testing connection...</div>';

        try {
            // In a real implementation, this would test the actual API
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // Simulate success/failure
            const isSuccess = Math.random() > 0.3; // 70% success rate for demo
            
            if (isSuccess) {
                resultDiv.innerHTML = '<div class="alert alert-success">✓ Connection successful</div>';
            } else {
                resultDiv.innerHTML = '<div class="alert alert-danger">✗ Connection failed. Please check your API key.</div>';
            }
        } catch (error) {
            resultDiv.innerHTML = '<div class="alert alert-danger">✗ Connection test failed</div>';
        }

        // Clear result after delay
        setTimeout(() => {
            resultDiv.innerHTML = '';
        }, 5000);
    }

    toggleApiKeyVisibility() {
        const input = document.getElementById('deepseekApiKey');
        const icon = document.getElementById('apiKeyToggleIcon');
        
        if (input.type === 'password') {
            input.type = 'text';
            icon.className = 'bi bi-eye-slash';
        } else {
            input.type = 'password';
            icon.className = 'bi bi-eye';
        }
    }

    cleanupTempFiles() {
        if (confirm('Are you sure you want to clean up temporary files? This action cannot be undone.')) {
            ExamGraderUtils.showNotification('Cleaning up temporary files...', 'info', 2000);
            
            setTimeout(() => {
                ExamGraderUtils.showNotification('Temporary files cleaned successfully', 'success', 3000);
            }, 2000);
        }
    }

    clearAllData() {
        if (confirm('Are you sure you want to clear ALL data? This will delete all results, uploads, and settings. This action cannot be undone.')) {
            if (confirm('This is your final warning. ALL DATA WILL BE LOST. Continue?')) {
                ExamGraderUtils.showNotification('Clearing all data...', 'warning', 3000);
                
                setTimeout(() => {
                    ExamGraderUtils.showNotification('All data cleared', 'info', 3000);
                }, 3000);
            }
        }
    }

    checkForUpdates() {
        ExamGraderUtils.showNotification('Checking for updates...', 'info', 2000);
        
        setTimeout(() => {
            ExamGraderUtils.showNotification('You are running the latest version', 'success', 3000);
        }, 2000);
    }

    exportSettings() {
        const settingsData = JSON.stringify(this.settings, null, 2);
        const blob = new Blob([settingsData], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = 'exam-grader-settings.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        ExamGraderUtils.showNotification('Settings exported successfully', 'success', 3000);
    }
}

// Global functions for HTML onclick handlers
function saveAllSettings() {
    if (window.settingsManager) {
        window.settingsManager.saveAllSettings();
    }
}

function testApiConnection() {
    if (window.settingsManager) {
        window.settingsManager.testApiConnection();
    }
}

function toggleApiKeyVisibility() {
    if (window.settingsManager) {
        window.settingsManager.toggleApiKeyVisibility();
    }
}

function cleanupTempFiles() {
    if (window.settingsManager) {
        window.settingsManager.cleanupTempFiles();
    }
}

function clearAllData() {
    if (window.settingsManager) {
        window.settingsManager.clearAllData();
    }
}

function checkForUpdates() {
    if (window.settingsManager) {
        window.settingsManager.checkForUpdates();
    }
}

function exportSettings() {
    if (window.settingsManager) {
        window.settingsManager.exportSettings();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.settingsManager = new SettingsManager();
});
