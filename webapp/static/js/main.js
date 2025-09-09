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

        // Initialize training dropdown hover functionality
        this.initTrainingDropdown();
    },

    initTrainingDropdown: function() {
        const trainingDropdown = document.getElementById('training-dropdown');
        const trainingButton = document.getElementById('training-dropdown-button');
        const trainingMenu = document.getElementById('training-dropdown-menu');
        const trainingArrow = document.getElementById('training-dropdown-arrow');
        
        if (!trainingDropdown || !trainingButton || !trainingMenu || !trainingArrow) {
            return; // Elements not found, skip initialization
        }

        let hoverTimeout;

        // Show dropdown on hover
        const showDropdown = () => {
            clearTimeout(hoverTimeout);
            trainingMenu.classList.remove('opacity-0', 'invisible', 'pointer-events-none', 'scale-95');
            trainingMenu.classList.add('opacity-100', 'visible', 'pointer-events-auto', 'scale-100');
            trainingArrow.style.transform = 'rotate(180deg)';
            trainingButton.setAttribute('aria-expanded', 'true');
        };

        // Hide dropdown with delay
        const hideDropdown = () => {
            hoverTimeout = setTimeout(() => {
                trainingMenu.classList.remove('opacity-100', 'visible', 'pointer-events-auto', 'scale-100');
                trainingMenu.classList.add('opacity-0', 'invisible', 'pointer-events-none', 'scale-95');
                trainingArrow.style.transform = 'rotate(0deg)';
                trainingButton.setAttribute('aria-expanded', 'false');
            }, 150); // Small delay to allow moving to submenu
        };

        // Mouse enter events
        trainingDropdown.addEventListener('mouseenter', showDropdown);
        trainingButton.addEventListener('mouseenter', showDropdown);
        trainingMenu.addEventListener('mouseenter', showDropdown);

        // Mouse leave events
        trainingDropdown.addEventListener('mouseleave', hideDropdown);
        trainingButton.addEventListener('mouseleave', hideDropdown);
        trainingMenu.addEventListener('mouseleave', hideDropdown);

        // Click handler for button (fallback for touch devices)
        trainingButton.addEventListener('click', function(e) {
            e.preventDefault();
            const isVisible = trainingMenu.classList.contains('opacity-100');
            
            if (isVisible) {
                hideDropdown();
            } else {
                showDropdown();
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!trainingDropdown.contains(e.target)) {
                hideDropdown();
            }
        });

        // Handle keyboard navigation
        trainingButton.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const isVisible = trainingMenu.classList.contains('opacity-100');
                
                if (isVisible) {
                    hideDropdown();
                } else {
                    showDropdown();
                    // Focus first menu item
                    const firstMenuItem = trainingMenu.querySelector('a');
                    if (firstMenuItem) {
                        firstMenuItem.focus();
                    }
                }
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                showDropdown();
                const firstMenuItem = trainingMenu.querySelector('a');
                if (firstMenuItem) {
                    firstMenuItem.focus();
                }
            }
        });

        // Handle keyboard navigation within menu
        trainingMenu.addEventListener('keydown', function(e) {
            const menuItems = trainingMenu.querySelectorAll('a');
            const currentIndex = Array.from(menuItems).indexOf(document.activeElement);
            
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                const nextIndex = (currentIndex + 1) % menuItems.length;
                menuItems[nextIndex].focus();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                const prevIndex = currentIndex > 0 ? currentIndex - 1 : menuItems.length - 1;
                menuItems[prevIndex].focus();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                hideDropdown();
                trainingButton.focus();
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
    
    // Note: Global error handlers are now managed by app.js to avoid conflicts
    // This file focuses on page-specific functionality only
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ExamGrader;
}