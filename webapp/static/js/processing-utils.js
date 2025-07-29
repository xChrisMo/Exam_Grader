/**
 * Processing Utilities
 * Common utilities for processing page functionality
 */

ExamGrader.processingUtils = {
    // Format time duration
    formatDuration: function(seconds) {
        if (seconds < 60) {
            return `${Math.round(seconds)}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = Math.round(seconds % 60);
            return `${minutes}m ${remainingSeconds}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    },
    
    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // Show processing status
    showStatus: function(message, type = 'info') {
        const statusDiv = document.getElementById('processing-status');
        if (!statusDiv) return;
        
        const typeClasses = {
            info: 'text-blue-600',
            success: 'text-green-600',
            warning: 'text-yellow-600',
            error: 'text-red-600'
        };
        
        statusDiv.innerHTML = `<div class="${typeClasses[type] || typeClasses.info}">${message}</div>`;
    },
    
    // Update progress bar
    updateProgressBar: function(percentage, message = '') {
        const progressBar = document.querySelector('.progress-bar');
        const progressText = document.querySelector('.progress-text');
        const progressMessage = document.querySelector('.progress-message');
        
        if (progressBar) {
            progressBar.style.width = `${Math.max(0, Math.min(100, percentage))}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
        }
        
        if (progressText) {
            progressText.textContent = `${Math.round(percentage)}%`;
        }
        
        if (progressMessage && message) {
            progressMessage.textContent = message;
        }
    },
    
    // Show/hide processing sections
    showSection: function(sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.classList.remove('hidden');
        }
    },
    
    hideSection: function(sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.classList.add('hidden');
        }
    },
    
    // Reset processing UI
    resetProcessingUI: function() {
        this.hideSection('progress-section');
        this.hideSection('results-section');
        this.showStatus('Ready to begin processing...');
        
        const startButton = document.getElementById('start-processing');
        if (startButton) {
            startButton.disabled = false;
            startButton.textContent = 'Start Enhanced Processing';
        }
    },
    
    // Validate form inputs
    validateProcessingForm: function() {
        const guideSelect = document.getElementById('marking-guide-select');
        const submissionCheckboxes = document.querySelectorAll('.submission-checkbox:checked');
        
        if (!guideSelect || !guideSelect.value) {
            this.showStatus('Please select a marking guide', 'warning');
            return false;
        }
        
        if (submissionCheckboxes.length === 0) {
            this.showStatus('Please select at least one submission', 'warning');
            return false;
        }
        
        return true;
    },
    
    // Handle processing errors
    handleProcessingError: function(error, context = '') {
        console.error(`Processing error${context ? ' in ' + context : ''}:`, error);
        
        let message = 'An error occurred during processing';
        if (error.message) {
            message += `: ${error.message}`;
        }
        
        this.showStatus(message, 'error');
        
        // Show user-friendly error messages
        if (error.message && error.message.includes('CSRF')) {
            message = 'Security token expired. Please refresh the page and try again.';
        } else if (error.message && error.message.includes('404')) {
            message = 'Resource not found. Please check your selection and try again.';
        } else if (error.message && error.message.includes('500')) {
            message = 'Server error occurred. Please try again later.';
        }
        
        this.showStatus(message, 'error');
    }
};
