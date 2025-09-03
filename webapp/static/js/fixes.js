/**
 * JavaScript fixes for Exam Grader Application
 * This file contains fixes for various JavaScript issues
 */

// Ensure ExamGrader namespace exists
if (typeof ExamGrader === 'undefined') {
    window.ExamGrader = {
        notificationManager: {
            notify: function (message, type, duration) {
                // Fallback to alert for critical errors
                if (type === 'error') {
                    alert(`Error: ${message}`);
                }
            }
        },
        utils: {
            showButtonLoading: function (button, text) {
                if (button) {
                    button.disabled = true;
                    button.dataset.originalText = button.innerHTML;
                    button.innerHTML = `<span class="spinner"></span> ${text || 'Loading...'}`;
                }
            },
            hideButtonLoading: function (button) {
                if (button && button.dataset.originalText) {
                    button.disabled = false;
                    button.innerHTML = button.dataset.originalText;
                }
            },
            // Safe innerHTML setter with null checks
            safeSetInnerHTML: function (elementOrId, content) {
                let element;
                if (typeof elementOrId === 'string') {
                    element = document.getElementById(elementOrId);
                } else {
                    element = elementOrId;
                }
                
                if (element) {
                    element.innerHTML = content;
                    return true;
                } else {
                    console.warn(`Element not found for innerHTML assignment: ${elementOrId}`);
                    return false;
                }
            }
        }
    };
}

// Global function definitions to prevent ReferenceError
window.viewDetails = window.viewDetails || function (submissionId) {

    if (!submissionId) {
        ExamGrader.notificationManager.notify('Invalid submission ID', 'error');
        return;
    }

    // Try to find modal elements
    const modal = document.getElementById('detailsModal');
    const modalContent = document.getElementById('modalContent');

    if (!modal || !modalContent) {
        // Fallback: show alert with basic info
        alert(`Viewing details for submission: ${submissionId}`);
        return;
    }

    // Show loading state
    modalContent.innerHTML = `
        <div class="flex justify-center items-center py-8">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
            <span class="ml-3">Loading submission details...</span>
        </div>
    `;

    modal.classList.remove('hidden');

    // Try to fetch submission details
    fetch(`/api/submission-details/${submissionId}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.submission) {
                const submission = data.submission;
                modalContent.innerHTML = `
                <div class="space-y-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <h4 class="text-sm font-medium text-gray-900">Filename</h4>
                            <p class="mt-1 text-sm text-gray-600">${submission.filename || 'Unknown'}</p>
                        </div>
                        <div>
                            <h4 class="text-sm font-medium text-gray-900">Score</h4>
                            <p class="mt-1 text-sm text-gray-600">${submission.score || 0}%</p>
                        </div>
                        <div>
                            <h4 class="text-sm font-medium text-gray-900">Status</h4>
                            <p class="mt-1 text-sm text-gray-600">${submission.status || 'Unknown'}</p>
                        </div>
                        <div>
                            <h4 class="text-sm font-medium text-gray-900">Processed At</h4>
                            <p class="mt-1 text-sm text-gray-600">${submission.processed_at || 'Not processed'}</p>
                        </div>
                    </div>
                    
                    ${submission.feedback ? `
                        <div>
                            <h4 class="text-sm font-medium text-gray-900">Feedback</h4>
                            <div class="mt-1 text-sm text-gray-600 bg-gray-50 p-3 rounded-md">
                                ${submission.feedback}
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
            } else {
                throw new Error(data.error || 'Failed to load submission details');
            }
        })
        .catch(error => {
            modalContent.innerHTML = `
            <div class="text-center py-8">
                <div class="text-red-500 mb-2">
                    <svg class="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                </div>
                <h3 class="text-lg font-medium text-gray-900">Error Loading Details</h3>
                <p class="mt-2 text-sm text-gray-600">${error.message}</p>
                <button onclick="closeDetailsModal()" class="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700">
                    Close
                </button>
            </div>
        `;
        });
};

window.exportResults = window.exportResults || function () {


    // Show loading state
    const exportBtn = document.querySelector('button[onclick="exportResults()"]');
    let originalText = '';
    if (exportBtn) {
        originalText = exportBtn.innerHTML;
        exportBtn.innerHTML = `
            <svg class="animate-spin mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Exporting...
        `;
        exportBtn.disabled = true;
    }

    // Call the API to export results
    fetch('/api/export-results', {
        method: 'GET',
        headers: {
            'Accept': 'application/pdf, application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Export failed: ${response.status} ${response.statusText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/pdf')) {
                return response.blob().then(blob => ({ type: 'pdf', data: blob }));
            } else {
                return response.json().then(json => ({ type: 'json', data: json }));
            }
        })
        .then(result => {
            if (result.type === 'pdf') {
                // Handle PDF download
                const url = window.URL.createObjectURL(result.data);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `grading_results_${new Date().toISOString().split('T')[0]}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else if (result.type === 'json') {
                // Handle JSON response
                const data = result.data;
                if (data.success) {
                    const dataStr = JSON.stringify(data.data, null, 2);
                    const dataBlob = new Blob([dataStr], { type: 'application/json' });
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(dataBlob);
                    link.download = data.filename || `grading_results_${new Date().toISOString().split('T')[0]}.json`;
                    link.click();
                    URL.revokeObjectURL(link.href);
                } else {
                    throw new Error(data.error || 'Export failed');
                }
            }

            ExamGrader.notificationManager.notify('Results exported successfully!', 'success');
        })
        .catch(error => {
            console.error('Export error:', error);
            ExamGrader.notificationManager.notify('Export failed: ' + error.message, 'error');
        })
        .finally(() => {
            // Reset button
            if (exportBtn) {
                exportBtn.innerHTML = originalText;
                exportBtn.disabled = false;
            }
        });
};

window.closeDetailsModal = window.closeDetailsModal || function () {
    const modal = document.getElementById('detailsModal');
    if (modal) {
        modal.classList.add('hidden');
    }
};

// Dashboard stats refresh function
window.refreshDashboardStats = function () {
    fetch('/api/dashboard-stats', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(response => {
            // Check if response is ok and content type is JSON
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Response is not JSON');
            }
            
            return response.json();
        })
        .then(data => {
            if (data.success && data.stats) {
                // Update last score
                const lastScoreElement = document.getElementById('last-score-value');
                if (lastScoreElement) {
                    lastScoreElement.textContent = data.stats.lastScore > 0 ? `${data.stats.lastScore}%` : '--';
                }

                // Update submission counts
                const totalSubmissionsElement = document.getElementById('total-submissions-count');
                if (totalSubmissionsElement) {
                    totalSubmissionsElement.textContent = data.stats.totalSubmissions || 0;
                }

                const processedSubmissionsElement = document.getElementById('processed-submissions-count');
                if (processedSubmissionsElement) {
                    processedSubmissionsElement.textContent = data.stats.processedSubmissions || 0;
                }

                // Update dashboard processed submissions count
                const dashboardProcessedElement = document.getElementById('processed-submissions-dashboard-count');
                if (dashboardProcessedElement) {
                    dashboardProcessedElement.innerHTML = `${data.stats.processedSubmissions || 0} <span data-i18n="processed">processed</span>`;
                }
            }
        })
        .catch(error => {
            // Silently handle errors to avoid console spam during development
            // Dashboard stats API may be disabled for performance
            return;
        });
};

// Auto-refresh dashboard stats every 30 seconds, but only if API is available
(async function() {
    try {
        const response = await fetch('/api/dashboard-stats', {
            method: 'GET',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        
        if (response.ok) {
            // Dashboard stats API is available, set up periodic refresh
            setInterval(refreshDashboardStats, 30000);
        }
    } catch (error) {
        // Dashboard stats API not available, skip periodic refresh
    }
})();

// Enhanced Progress bar improvements
window.updateProgressBar = function (progressId, percentage, message, details) {
    const progressBar = document.getElementById(`progress-${progressId}`) ||
        document.getElementById(`${progressId}-progress-bar`) ||
        document.getElementById('progress-bar');
    const progressText = document.getElementById(`progress-text-${progressId}`) ||
        document.getElementById(`${progressId}-progress-text`) ||
        document.getElementById('progress-text');
    const progressPercentage = document.getElementById(`progress-percentage-${progressId}`) ||
        document.getElementById(`${progressId}-progress-percentage`) ||
        document.getElementById('progress-percentage');

    // Ensure percentage is within bounds
    const safePercentage = Math.min(100, Math.max(0, percentage));

    if (progressBar) {
        progressBar.style.width = `${safePercentage}%`;
        progressBar.setAttribute('aria-valuenow', safePercentage);

        // Add visual feedback for different stages
        progressBar.className = progressBar.className.replace(/bg-\w+-\d+/, '');
        if (safePercentage < 25) {
            progressBar.classList.add('bg-red-500');
        } else if (safePercentage < 50) {
            progressBar.classList.add('bg-yellow-500');
        } else if (safePercentage < 75) {
            progressBar.classList.add('bg-blue-500');
        } else {
            progressBar.classList.add('bg-green-500');
        }

        // Add animation for smooth transitions
        progressBar.style.transition = 'width 0.5s ease-in-out, background-color 0.3s ease';
    }

    if (progressText && message) {
        progressText.textContent = message;
    }

    if (progressPercentage) {
        progressPercentage.textContent = `${Math.round(safePercentage)}%`;
    }

    // Update details if provided
    if (details) {
        const progressDetails = document.getElementById(`progress-details-${progressId}`) ||
            document.getElementById('progress-details');
        if (progressDetails) {
            progressDetails.textContent = details;
        }
    }

    // Trigger custom event for other components to listen to
    window.dispatchEvent(new CustomEvent('progressUpdate', {
        detail: {
            progressId: progressId,
            percentage: safePercentage,
            message: message,
            details: details
        }
    }));
};

// Enhanced progress bar creation
window.createProgressBar = function (containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Container ${containerId} not found`);
        return null;
    }

    const progressId = options.id || 'progress-' + Date.now();
    const showPercentage = options.showPercentage !== false;
    const showMessage = options.showMessage !== false;
    const animated = options.animated !== false;

    const progressHTML = `
        <div class="progress-container mb-4">
            ${showMessage ? `<div id="progress-text-${progressId}" class="text-sm text-gray-600 mb-2">${options.initialMessage || 'Processing...'}</div>` : ''}
            <div class="w-full bg-gray-200 rounded-full h-3 shadow-inner">
                <div id="progress-${progressId}" 
                     class="bg-blue-500 h-3 rounded-full transition-all duration-500 ease-out ${animated ? 'animate-pulse' : ''}" 
                     style="width: 0%" 
                     role="progressbar" 
                     aria-valuenow="0" 
                     aria-valuemin="0" 
                     aria-valuemax="100">
                </div>
            </div>
            ${showPercentage ? `
                <div class="flex justify-between text-xs text-gray-500 mt-1">
                    <span>0%</span>
                    <span id="progress-percentage-${progressId}">0%</span>
                    <span>100%</span>
                </div>
            ` : ''}
            ${options.showDetails ? `<div id="progress-details-${progressId}" class="text-xs text-gray-400 mt-1"></div>` : ''}
        </div>
    `;

    container.innerHTML = progressHTML;
    return progressId;
};

// Processing status improvements
window.updateProcessingStatus = function (status, message, progress) {
    const statusElements = document.querySelectorAll('.processing-status, #processing-status, .ai-processing-status');
    const progressBars = document.querySelectorAll('[id*="progress"], .progress-bar');

    statusElements.forEach(element => {
        if (element) {
            element.textContent = message || status;
            element.className = element.className.replace(/status-\w+/, '') + ` status-${status}`;

            // Add appropriate styling based on status
            element.classList.remove('text-blue-600', 'text-green-600', 'text-red-600', 'text-yellow-600');
            switch (status) {
                case 'processing':
                case 'started':
                    element.classList.add('text-blue-600');
                    break;
                case 'completed':
                case 'success':
                    element.classList.add('text-green-600');
                    break;
                case 'failed':
                case 'error':
                    element.classList.add('text-red-600');
                    break;
                case 'pending':
                case 'waiting':
                    element.classList.add('text-yellow-600');
                    break;
            }
        }
    });

    // Update progress bars if progress is provided
    if (typeof progress === 'number') {
        progressBars.forEach(bar => {
            if (bar.id && bar.id.includes('progress')) {
                updateProgressBar(bar.id.replace('progress-', ''), progress, message);
            }
        });
    }
};

// Enhanced notification system with queue and positioning
window.NotificationManager = {
    notifications: [],
    maxNotifications: 5,

    show: function (message, type = 'info', duration = 5000, options = {}) {
        // Remove oldest notification if we're at the limit
        if (this.notifications.length >= this.maxNotifications) {
            const oldest = this.notifications.shift();
            if (oldest && oldest.element && oldest.element.parentNode) {
                oldest.element.remove();
            }
        }

        const notification = this.createNotification(message, type, duration, options);
        this.notifications.push(notification);

        return notification;
    },

    createNotification: function (message, type, duration, options) {
        const id = 'notification-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        const position = options.position || 'top-right';
        const persistent = options.persistent || false;

        // Create notification element
        const notification = document.createElement('div');
        notification.id = id;
        notification.className = this.getNotificationClasses(type, position);

        notification.innerHTML = this.getNotificationHTML(message, type, !persistent, id);

        // Position the notification
        this.positionNotification(notification, position);

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.style.transform = this.getShowTransform(position);
            notification.style.opacity = '1';
        }, 100);

        const notificationObj = {
            id: id,
            element: notification,
            type: type,
            message: message,
            timestamp: Date.now()
        };

        // Auto remove if not persistent
        if (!persistent && duration > 0) {
            setTimeout(() => {
                this.remove(id);
            }, duration);
        }

        return notificationObj;
    },

    getNotificationClasses: function (type, position) {
        const baseClasses = 'fixed z-50 max-w-sm bg-white border-l-4 rounded-lg shadow-lg p-4 transform transition-all duration-300 opacity-0';
        const typeClasses = {
            'error': 'border-red-500 bg-red-50',
            'success': 'border-green-500 bg-green-50',
            'warning': 'border-yellow-500 bg-yellow-50',
            'info': 'border-blue-500 bg-blue-50'
        };

        const positionClasses = {
            'top-right': 'top-4 right-4 translate-x-full',
            'top-left': 'top-4 left-4 -translate-x-full',
            'bottom-right': 'bottom-4 right-4 translate-x-full',
            'bottom-left': 'bottom-4 left-4 -translate-x-full',
            'top-center': 'top-4 left-1/2 -translate-x-1/2 -translate-y-full',
            'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2 translate-y-full'
        };

        return `${baseClasses} ${typeClasses[type] || typeClasses.info} ${positionClasses[position] || positionClasses['top-right']}`;
    },

    getShowTransform: function (position) {
        const transforms = {
            'top-right': 'translateX(0)',
            'top-left': 'translateX(0)',
            'bottom-right': 'translateX(0)',
            'bottom-left': 'translateX(0)',
            'top-center': 'translate(-50%, 0)',
            'bottom-center': 'translate(-50%, 0)'
        };

        return transforms[position] || transforms['top-right'];
    },

    positionNotification: function (notification, position) {
        // Stack notifications
        const existingNotifications = document.querySelectorAll(`[id^="notification-"]`);
        const offset = existingNotifications.length * 80; // 80px spacing

        switch (position) {
            case 'top-right':
                notification.style.top = `${16 + offset}px`;
                break;
            case 'top-left':
                notification.style.top = `${16 + offset}px`;
                break;
            case 'bottom-right':
                notification.style.bottom = `${16 + offset}px`;
                break;
            case 'bottom-left':
                notification.style.bottom = `${16 + offset}px`;
                break;
            case 'top-center':
                notification.style.top = `${16 + offset}px`;
                break;
            case 'bottom-center':
                notification.style.bottom = `${16 + offset}px`;
                break;
        }
    },

    getNotificationHTML: function (message, type, showClose, notificationId) {
        const icons = {
            'error': '<svg class="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>',
            'success': '<svg class="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>',
            'warning': '<svg class="h-5 w-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>',
            'info': '<svg class="h-5 w-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>'
        };

        const textColors = {
            'error': 'text-red-800',
            'success': 'text-green-800',
            'warning': 'text-yellow-800',
            'info': 'text-blue-800'
        };

        const buttonColors = {
            'error': 'text-red-500 hover:bg-red-100',
            'success': 'text-green-500 hover:bg-green-100',
            'warning': 'text-yellow-500 hover:bg-yellow-100',
            'info': 'text-blue-500 hover:bg-blue-100'
        };

        // Escape HTML to prevent XSS
        const escapeHtml = (text) => {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        };

        const safeMessage = escapeHtml(message);

        return `
            <div class="flex items-center">
                <div class="flex-shrink-0">
                    ${icons[type] || icons.info}
                </div>
                <div class="ml-3">
                    <p class="text-sm font-medium ${textColors[type] || textColors.info}">${safeMessage}</p>
                </div>
                ${showClose ? `
                    <div class="ml-auto pl-3">
                        <button type="button" class="inline-flex rounded-md p-1.5 ${buttonColors[type] || buttonColors.info} focus:outline-none" onclick="NotificationManager.remove('${notificationId}')">
                            <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                            </svg>
                        </button>
                    </div>
                ` : ''}
            </div>
        `;
    },

    remove: function (id) {
        const notification = document.getElementById(id);
        if (notification) {
            notification.style.transform = notification.style.transform.replace('translateX(0)', 'translateX(100%)');
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }

        // Remove from array
        this.notifications = this.notifications.filter(n => n.id !== id);
    },

    clear: function () {
        this.notifications.forEach(notification => {
            if (notification.element && notification.element.parentNode) {
                notification.element.remove();
            }
        });
        this.notifications = [];
    }
};

// Backward compatibility
window.showNotification = function (message, type = 'info', duration = 5000, options = {}) {
    return NotificationManager.show(message, type, duration, options);
};

// Initialize fixes when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    console.log('JavaScript fixes loaded');

    // Override ExamGrader notification manager if it exists
    if (typeof ExamGrader !== 'undefined' && ExamGrader.notificationManager) {
        const originalNotify = ExamGrader.notificationManager.notify;
        ExamGrader.notificationManager.notify = function (message, type, duration) {
            try {
                if (typeof originalNotify === 'function') {
                    originalNotify.call(this, message, type, duration);
                } else {
                    NotificationManager.show(message, type, duration);
                }
            } catch (error) {
                console.error('Error in notification system:', error);
                NotificationManager.show(message, type, duration);
            }
        };
    }

    // Refresh dashboard stats on page load
    if (window.location.pathname === '/dashboard' || window.location.pathname === '/') {
        setTimeout(refreshDashboardStats, 1000);
    }

    // Initialize progress bar improvements for existing elements
    const existingProgressBars = document.querySelectorAll('[id*="progress"]');
    existingProgressBars.forEach(bar => {
        if (bar.style.width) {
            const percentage = parseFloat(bar.style.width.replace('%', '')) || 0;
            updateProgressBar(bar.id.replace('progress-', ''), percentage, 'Processing...');
        }
    });

    // Add global error handler for uncaught JavaScript errors
    window.addEventListener('error', function (event) {
        console.error('Global JavaScript error:', event.error);
        if (event.error && event.error.message && event.error.message.includes('is not defined')) {
            console.warn('Function not defined error caught, this may be expected during page transitions');
        }
    });

    // Add unhandled promise rejection handler
    window.addEventListener('unhandledrejection', function (event) {
        console.error('Unhandled promise rejection:', event.reason);
        event.preventDefault(); // Prevent the default browser behavior
    });
});

// Ensure all global functions are available immediately
window.addEventListener('load', function () {
    // Final check to ensure all functions are properly defined
    const requiredFunctions = ['viewDetails', 'exportResults', 'closeDetailsModal'];
    requiredFunctions.forEach(funcName => {
        if (typeof window[funcName] !== 'function') {
            console.warn(`Function ${funcName} not properly defined, creating fallback`);
            window[funcName] = function () {
                console.log(`Fallback ${funcName} called`);
                NotificationManager.show(`${funcName} function called`, 'info');
            };
        }
    });
});

console.log('JavaScript fixes module loaded successfully');