/**
 * Exam Grader - Main JavaScript
 * Handles global functionality and Socket.IO connections
 */

class ExamGraderApp {
    constructor() {
        this.socket = null;
        this.currentSession = null;
        this.init();
    }

    init() {
        this.initializeSocket();
        this.setupGlobalEventListeners();
        this.initializeLightMode();
        this.showWelcomeMessage();
    }

    initializeSocket() {
        // Initialize Socket.IO connection
        this.socket = io();

        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.showNotification('Connected to server', 'success');
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.showNotification('Disconnected from server', 'warning');
        });

        this.socket.on('connected', (data) => {
            console.log('Server message:', data.message);
        });

        this.socket.on('progress', (data) => {
            this.handleProgressUpdate(data);
        });

        this.socket.on('error', (data) => {
            this.handleError(data);
        });
    }

    setupGlobalEventListeners() {
        // Handle navigation active states
        this.updateActiveNavigation();

        // Handle responsive navigation
        this.setupResponsiveNavigation();

        // Handle global keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });

        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            this.handleVisibilityChange();
        });
    }

    updateActiveNavigation() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link');

        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href === currentPath) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }

    setupResponsiveNavigation() {
        const navbarToggler = document.querySelector('.navbar-toggler');
        const navbarCollapse = document.querySelector('.navbar-collapse');

        if (navbarToggler && navbarCollapse) {
            navbarToggler.addEventListener('click', () => {
                navbarCollapse.classList.toggle('show');
            });

            // Close navigation when clicking outside
            document.addEventListener('click', (e) => {
                if (!navbarToggler.contains(e.target) && !navbarCollapse.contains(e.target)) {
                    navbarCollapse.classList.remove('show');
                }
            });
        }
    }

    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + U: Go to upload page
        if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
            e.preventDefault();
            window.location.href = '/upload';
        }

        // Ctrl/Cmd + H: Go to dashboard
        if ((e.ctrlKey || e.metaKey) && e.key === 'h') {
            e.preventDefault();
            window.location.href = '/';
        }

        // Ctrl/Cmd + R: Go to results page
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            window.location.href = '/results';
        }

        // Escape: Close modals
        if (e.key === 'Escape') {
            this.closeAllModals();
        }
    }

    handleVisibilityChange() {
        if (document.hidden) {
            console.log('Page hidden');
        } else {
            console.log('Page visible');
            // Refresh connection if needed
            if (this.socket && !this.socket.connected) {
                this.socket.connect();
            }
        }
    }

    handleProgressUpdate(data) {
        console.log('Progress update:', data);

        if (data.session_id === this.currentSession) {
            this.updateProgressUI(data);
        }
    }

    updateProgressUI(data) {
        const progressBar = document.getElementById('progressBar');
        const progressStage = document.getElementById('progressStage');
        const progressMessage = document.getElementById('progressMessage');

        if (progressBar) {
            progressBar.style.width = `${data.progress}%`;
            progressBar.setAttribute('aria-valuenow', data.progress);
        }

        if (progressStage) {
            progressStage.textContent = this.getStageTitle(data.stage);
        }

        if (progressMessage) {
            progressMessage.textContent = data.message;
        }

        // Update progress steps
        this.updateProgressSteps(data.stage);

        // Handle completion
        if (data.stage === 'complete') {
            setTimeout(() => {
                this.handleProcessingComplete(data);
            }, 1000);
        }
    }

    getStageTitle(stage) {
        const stageTitles = {
            'upload': 'Uploading Files...',
            'parsing': 'Parsing Documents...',
            'analyzing': 'Analyzing Content...',
            'grading': 'Generating Grades...',
            'complete': 'Processing Complete!'
        };
        return stageTitles[stage] || 'Processing...';
    }

    updateProgressSteps(currentStage) {
        const steps = ['upload', 'parsing', 'analyzing', 'complete'];
        const currentIndex = steps.indexOf(currentStage);

        steps.forEach((step, index) => {
            const stepElement = document.getElementById(`step${index + 1}`);
            if (stepElement) {
                stepElement.classList.remove('active', 'completed');

                if (index < currentIndex) {
                    stepElement.classList.add('completed');
                } else if (index === currentIndex) {
                    stepElement.classList.add('active');
                }
            }
        });
    }

    handleProcessingComplete(data) {
        // Hide progress modal
        const progressModal = bootstrap.Modal.getInstance(document.getElementById('progressModal'));
        if (progressModal) {
            progressModal.hide();
        }

        // Show results
        this.showResults(data.results);
    }

    showResults(results) {
        const resultsModal = new bootstrap.Modal(document.getElementById('resultsModal'));
        const resultsContent = document.getElementById('resultsContent');

        if (resultsContent && results) {
            resultsContent.innerHTML = this.generateResultsHTML(results);
        }

        resultsModal.show();
    }

    generateResultsHTML(results) {
        return `
            <div class="row">
                <div class="col-md-6">
                    <div class="card border-0 bg-light">
                        <div class="card-body text-center">
                            <h2 class="display-4 text-primary mb-2">${results.score}%</h2>
                            <p class="text-muted mb-0">Overall Score</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card border-0 bg-light">
                        <div class="card-body">
                            <h6 class="card-title">Feedback</h6>
                            <p class="card-text">${results.feedback || 'No feedback available'}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    handleError(data) {
        console.error('Error:', data);
        this.showNotification(data.message, 'danger');

        // Hide progress modal if open
        const progressModal = bootstrap.Modal.getInstance(document.getElementById('progressModal'));
        if (progressModal) {
            progressModal.hide();
        }
    }

    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';

        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto-remove after duration
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
    }

    showWelcomeMessage() {
        // Show welcome message only on first visit
        if (!localStorage.getItem('exam_grader_visited')) {
            setTimeout(() => {
                this.showNotification('Welcome to Exam Grader! Upload your files to get started.', 'info', 8000);
                localStorage.setItem('exam_grader_visited', 'true');
            }, 1000);
        }
    }

    // Light Mode Toggle (inspired by the design)
    initializeLightMode() {
        // Check for saved theme preference or default to 'dark'
        const currentTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', currentTheme);
        this.updateThemeIcon(currentTheme);
    }

    toggleLightMode() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        this.updateThemeIcon(newTheme);
    }

    updateThemeIcon(theme) {
        const themeIcon = document.getElementById('theme-icon');
        const themeText = document.getElementById('theme-text');

        if (themeIcon && themeText) {
            if (theme === 'light') {
                themeIcon.className = 'bi bi-moon-fill me-1';
                themeText.textContent = 'Dark mode';
            } else {
                themeIcon.className = 'bi bi-sun-fill me-1';
                themeText.textContent = 'Light mode';
            }
        }
    }

    closeAllModals() {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            }
        });
    }

    joinSession(sessionId) {
        this.currentSession = sessionId;
        if (this.socket) {
            this.socket.emit('join_session', { session_id: sessionId });
        }
    }

    // Utility methods
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDate(date) {
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.examGraderApp = new ExamGraderApp();
});

// Global utility functions
window.ExamGraderUtils = {
    formatFileSize: (bytes) => window.examGraderApp.formatFileSize(bytes),
    formatDate: (date) => window.examGraderApp.formatDate(date),
    showNotification: (message, type, duration) => window.examGraderApp.showNotification(message, type, duration)
};

// Global functions for template usage
function toggleLightMode() {
    if (window.examGraderApp) {
        window.examGraderApp.toggleLightMode();
    }
}
