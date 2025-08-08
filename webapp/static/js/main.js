/**
 * Main JavaScript file for Exam Grader
 * Provides core functionality and utilities
 */

// Global app namespace
window.ExamGrader = window.ExamGrader || {};

// DOM ready function
function domReady(fn) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
    } else {
        fn();
    }
}

// Utility functions
ExamGrader.utils = {
    // Show loading spinner
    showLoading: function(element) {
        if (element) {
            element.classList.add('loading');
            const spinner = document.createElement('span');
            spinner.className = 'spinner';
            element.prepend(spinner);
        }
    },

    // Hide loading spinner
    hideLoading: function(element) {
        if (element) {
            element.classList.remove('loading');
            const spinner = element.querySelector('.spinner');
            if (spinner) {
                spinner.remove();
            }
        }
    },

    // Show alert message
    showAlert: function(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.textContent = message;
        
        const container = document.querySelector('.container') || document.body;
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, 5000);
    },

    // AJAX helper
    ajax: function(url, options = {}) {
        const defaults = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        const config = Object.assign(defaults, options);
        
        return fetch(url, config)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error('AJAX error:', error);
                ExamGrader.utils.showAlert('An error occurred. Please try again.', 'error');
                throw error;
            });
    }
};

// Form handling
ExamGrader.forms = {
    // Initialize form validation
    init: function() {
        const forms = document.querySelectorAll('form[data-validate]');
        forms.forEach(form => {
            form.addEventListener('submit', this.handleSubmit.bind(this));
        });
    },

    // Handle form submission
    handleSubmit: function(event) {
        const form = event.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        
        if (submitBtn) {
            ExamGrader.utils.showLoading(submitBtn);
        }
        
        // Basic validation
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('error');
                isValid = false;
            } else {
                field.classList.remove('error');
            }
        });
        
        if (!isValid) {
            event.preventDefault();
            if (submitBtn) {
                ExamGrader.utils.hideLoading(submitBtn);
            }
            ExamGrader.utils.showAlert('Please fill in all required fields.', 'error');
        }
    }
};

// File upload handling
ExamGrader.upload = {
    init: function() {
        const uploadAreas = document.querySelectorAll('.upload-area');
        uploadAreas.forEach(area => {
            this.setupDragDrop(area);
        });
    },

    setupDragDrop: function(area) {
        area.addEventListener('dragover', function(e) {
            e.preventDefault();
            area.classList.add('drag-over');
        });

        area.addEventListener('dragleave', function(e) {
            e.preventDefault();
            area.classList.remove('drag-over');
        });

        area.addEventListener('drop', function(e) {
            e.preventDefault();
            area.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                ExamGrader.upload.handleFiles(files);
            }
        });
    },

    handleFiles: function(files) {
        Array.from(files).forEach(file => {
            console.log('Processing file:', file.name);
            ExamGrader.utils.showAlert(`Processing file: ${file.name}`, 'info');
        });
    }
};

// Navigation handling
ExamGrader.navigation = {
    init: function() {
        // Mobile menu toggle
        const mobileToggle = document.querySelector('.mobile-menu-toggle');
        const mobileMenu = document.querySelector('.mobile-menu');
        
        if (mobileToggle && mobileMenu) {
            mobileToggle.addEventListener('click', function() {
                mobileMenu.classList.toggle('active');
            });
        }
        
        // Active link highlighting
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });
    }
};

// Initialize everything when DOM is ready
domReady(function() {
    console.log('Exam Grader main.js loaded');
    
    // Initialize modules
    ExamGrader.forms.init();
    ExamGrader.upload.init();
    ExamGrader.navigation.init();
    
    // Global error handler
    window.addEventListener('error', function(e) {
        console.error('Global error:', e.error);
        ExamGrader.utils.showAlert('An unexpected error occurred.', 'error');
    });
    
    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', function(e) {
        console.error('Unhandled promise rejection:', e.reason);
        ExamGrader.utils.showAlert('An error occurred while processing your request.', 'error');
    });
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ExamGrader;
}