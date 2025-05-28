/**
 * Exam Grader Application JavaScript
 * Common functionality and utilities
 */

// Application namespace
const ExamGrader = {
    // Configuration
    config: {
        maxFileSize: 16 * 1024 * 1024, // 16MB
        allowedFileTypes: ['.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'],
        apiEndpoints: {
            processMapping: '/api/process-mapping',
            processGrading: '/api/process-grading'
        }
    },

    // Utility functions
    utils: {
        /**
         * Format file size in human readable format
         */
        formatFileSize: function(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        /**
         * Check if file type is allowed
         */
        isAllowedFileType: function(filename) {
            if (!filename) return false;
            const ext = '.' + filename.split('.').pop().toLowerCase();
            return ExamGrader.config.allowedFileTypes.includes(ext);
        },

        /**
         * Show toast notification
         */
        showToast: function(message, type = 'info', duration = 5000) {
            const toast = document.createElement('div');
            toast.className = `fixed top-4 right-4 z-50 max-w-sm bg-white border-l-4 rounded-lg shadow-lg p-4 animate-slide-up ${
                type === 'error' ? 'border-red-500 bg-red-50' :
                type === 'success' ? 'border-green-500 bg-green-50' :
                type === 'warning' ? 'border-yellow-500 bg-yellow-50' :
                'border-blue-500 bg-blue-50'
            }`;

            toast.innerHTML = `
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        ${type === 'error' ? 
                            '<svg class="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>' :
                        type === 'success' ?
                            '<svg class="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>' :
                        type === 'warning' ?
                            '<svg class="h-5 w-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>' :
                            '<svg class="h-5 w-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>'
                        }
                    </div>
                    <div class="ml-3">
                        <p class="text-sm font-medium ${
                            type === 'error' ? 'text-red-800' :
                            type === 'success' ? 'text-green-800' :
                            type === 'warning' ? 'text-yellow-800' :
                            'text-blue-800'
                        }">${message}</p>
                    </div>
                    <div class="ml-auto pl-3">
                        <button type="button" class="inline-flex rounded-md p-1.5 ${
                            type === 'error' ? 'text-red-500 hover:bg-red-100' :
                            type === 'success' ? 'text-green-500 hover:bg-green-100' :
                            type === 'warning' ? 'text-yellow-500 hover:bg-yellow-100' :
                            'text-blue-500 hover:bg-blue-100'
                        } focus:outline-none" onclick="this.parentElement.parentElement.parentElement.remove()">
                            <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                            </svg>
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(toast);

            // Auto remove after duration
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.style.transition = 'opacity 0.3s ease-out';
                    toast.style.opacity = '0';
                    setTimeout(() => {
                        if (toast.parentNode) {
                            toast.remove();
                        }
                    }, 300);
                }
            }, duration);
        },

        /**
         * Show loading spinner on button
         */
        showButtonLoading: function(button, loadingText = 'Processing...') {
            if (!button) return;
            
            button.dataset.originalText = button.innerHTML;
            button.disabled = true;
            button.innerHTML = `
                <svg class="animate-spin mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                ${loadingText}
            `;
        },

        /**
         * Hide loading spinner on button
         */
        hideButtonLoading: function(button) {
            if (!button) return;
            
            button.disabled = false;
            button.innerHTML = button.dataset.originalText || button.innerHTML;
        },

        /**
         * Make API request with error handling
         */
        apiRequest: async function(url, options = {}) {
            try {
                const response = await fetch(url, {
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    },
                    ...options
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || `HTTP error! status: ${response.status}`);
                }

                return data;
            } catch (error) {
                console.error('API request failed:', error);
                throw error;
            }
        },

        /**
         * Debounce function
         */
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        /**
         * Format date for display
         */
        formatDate: function(dateString) {
            if (!dateString) return 'Unknown';
            const date = new Date(dateString);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        }
    },

    // File upload functionality
    fileUpload: {
        /**
         * Initialize drag and drop for file upload
         */
        initDragAndDrop: function(dropZone, fileInput, onFileSelect) {
            if (!dropZone || !fileInput) return;

            // Prevent default drag behaviors
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, preventDefaults, false);
                document.body.addEventListener(eventName, preventDefaults, false);
            });

            // Highlight drop zone when item is dragged over it
            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, highlight, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, unhighlight, false);
            });

            // Handle dropped files
            dropZone.addEventListener('drop', handleDrop, false);

            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }

            function highlight(e) {
                dropZone.classList.add('border-blue-500', 'bg-blue-50');
            }

            function unhighlight(e) {
                dropZone.classList.remove('border-blue-500', 'bg-blue-50');
            }

            function handleDrop(e) {
                const dt = e.dataTransfer;
                const files = dt.files;

                if (files.length > 0) {
                    fileInput.files = files;
                    if (onFileSelect) {
                        onFileSelect(files[0]);
                    }
                }
            }
        },

        /**
         * Validate file before upload
         */
        validateFile: function(file) {
            const errors = [];

            if (!file) {
                errors.push('No file selected');
                return errors;
            }

            // Check file size
            if (file.size > ExamGrader.config.maxFileSize) {
                errors.push(`File size exceeds ${ExamGrader.utils.formatFileSize(ExamGrader.config.maxFileSize)} limit`);
            }

            // Check file type
            if (!ExamGrader.utils.isAllowedFileType(file.name)) {
                errors.push('File type not supported');
            }

            return errors;
        }
    },

    // API interactions
    api: {
        /**
         * Process answer mapping
         */
        processMapping: async function() {
            try {
                const data = await ExamGrader.utils.apiRequest(ExamGrader.config.apiEndpoints.processMapping, {
                    method: 'POST'
                });
                
                if (data.success) {
                    ExamGrader.utils.showToast('Answer mapping completed successfully!', 'success');
                    return true;
                } else {
                    throw new Error(data.error || 'Mapping failed');
                }
            } catch (error) {
                ExamGrader.utils.showToast(`Mapping failed: ${error.message}`, 'error');
                return false;
            }
        },

        /**
         * Process grading
         */
        processGrading: async function() {
            try {
                const data = await ExamGrader.utils.apiRequest(ExamGrader.config.apiEndpoints.processGrading, {
                    method: 'POST'
                });
                
                if (data.success) {
                    ExamGrader.utils.showToast(`Grading completed! Score: ${data.score}%`, 'success');
                    return data;
                } else {
                    throw new Error(data.error || 'Grading failed');
                }
            } catch (error) {
                ExamGrader.utils.showToast(`Grading failed: ${error.message}`, 'error');
                return false;
            }
        }
    },

    // Initialize application
    init: function() {
        console.log('Exam Grader Application initialized');
        
        // Initialize common functionality
        this.initFlashMessages();
        this.initServiceWorker();
        
        // Add global error handler
        window.addEventListener('error', function(e) {
            console.error('Global error:', e.error);
            ExamGrader.utils.showToast('An unexpected error occurred', 'error');
        });

        // Add unhandled promise rejection handler
        window.addEventListener('unhandledrejection', function(e) {
            console.error('Unhandled promise rejection:', e.reason);
            ExamGrader.utils.showToast('An unexpected error occurred', 'error');
        });
    },

    /**
     * Initialize flash message handling
     */
    initFlashMessages: function() {
        // Auto-hide flash messages after 5 seconds
        setTimeout(() => {
            const flashMessages = document.querySelectorAll('.flash-message');
            flashMessages.forEach(message => {
                message.style.transition = 'opacity 0.5s ease-out';
                message.style.opacity = '0';
                setTimeout(() => {
                    if (message.parentNode) {
                        message.remove();
                    }
                }, 500);
            });
        }, 5000);

        // Close button functionality
        document.querySelectorAll('.flash-close').forEach(button => {
            button.addEventListener('click', function() {
                const message = this.closest('.flash-message');
                if (message) {
                    message.style.transition = 'opacity 0.3s ease-out';
                    message.style.opacity = '0';
                    setTimeout(() => {
                        if (message.parentNode) {
                            message.remove();
                        }
                    }, 300);
                }
            });
        });
    },

    /**
     * Initialize service worker for offline functionality (if needed)
     */
    initServiceWorker: function() {
        if ('serviceWorker' in navigator) {
            // Service worker registration would go here
            // navigator.serviceWorker.register('/static/js/sw.js');
        }
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    ExamGrader.init();
});

// Export for use in other scripts
window.ExamGrader = ExamGrader;
