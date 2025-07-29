/**
 * Frontend Error Handling Framework
 * 
 * Provides comprehensive error handling with categorization, retry mechanisms,
 * and user-friendly error messaging for the LLM training system.
 */

class ErrorHandler {
    constructor() {
        this.errorHistory = [];
        this.retryAttempts = new Map();
        this.maxRetries = 3;
        this.baseDelay = 1000; // 1 second
        this.maxDelay = 30000; // 30 seconds
        
        this.errorTypes = {
            NETWORK_ERROR: 'network',
            VALIDATION_ERROR: 'validation',
            SERVER_ERROR: 'server',
            TIMEOUT_ERROR: 'timeout',
            FILE_PROCESSING_ERROR: 'file_processing',
            TRAINING_ERROR: 'training',
            AUTHENTICATION_ERROR: 'authentication',
            PERMISSION_ERROR: 'permission',
            UNKNOWN_ERROR: 'unknown'
        };
        
        this.init();
    }
    
    init() {
        // Set up global error handlers
        window.addEventListener('error', (event) => {
            this.handleGlobalError(event.error, 'javascript_error');
        });
        
        window.addEventListener('unhandledrejection', (event) => {
            this.handleGlobalError(event.reason, 'unhandled_promise');
        });
        
        // Set up notification container
        this.createNotificationContainer();
    }
    
    createNotificationContainer() {
        if (document.getElementById('error-notifications')) return;
        
        const container = document.createElement('div');
        container.id = 'error-notifications';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
        `;
        document.body.appendChild(container);
    }
    
    /**
     * Handle API errors with categorization and recovery options
     */
    handleApiError(error, context = {}) {
        const categorizedError = this.categorizeError(error);
        
        // Log error
        this.logError(categorizedError, context);
        
        // Determine if retry is appropriate
        if (this.shouldRetry(categorizedError)) {
            return this.scheduleRetry(categorizedError, context);
        }
        
        // Show user-friendly error message
        this.showUserFriendlyError(categorizedError);
        
        return {
            success: false,
            error: categorizedError,
            canRetry: this.canRetry(categorizedError),
            userMessage: this.getUserMessage(categorizedError)
        };
    }
    
    /**
     * Categorize error based on type and content
     */
    categorizeError(error) {
        const errorInfo = {
            originalError: error,
            type: this.errorTypes.UNKNOWN_ERROR,
            severity: 'medium',
            recoverable: true,
            userMessage: 'An unexpected error occurred',
            technicalMessage: error?.message || String(error),
            timestamp: new Date().toISOString(),
            errorId: this.generateErrorId()
        };
        
        // Network errors
        if (error?.code === 'NETWORK_ERROR' || 
            error?.message?.includes('fetch') ||
            error?.message?.includes('network') ||
            !navigator.onLine) {
            errorInfo.type = this.errorTypes.NETWORK_ERROR;
            errorInfo.userMessage = 'Network connection error. Please check your internet connection.';
            errorInfo.severity = 'high';
        }
        
        // HTTP status-based categorization
        else if (error?.status) {
            switch (Math.floor(error.status / 100)) {
                case 4:
                    if (error.status === 401) {
                        errorInfo.type = this.errorTypes.AUTHENTICATION_ERROR;
                        errorInfo.userMessage = 'Authentication required. Please log in again.';
                        errorInfo.severity = 'high';
                        errorInfo.recoverable = false;
                    } else if (error.status === 403) {
                        errorInfo.type = this.errorTypes.PERMISSION_ERROR;
                        errorInfo.userMessage = 'You do not have permission to perform this action.';
                        errorInfo.recoverable = false;
                    } else if (error.status === 408 || error.status === 504) {
                        errorInfo.type = this.errorTypes.TIMEOUT_ERROR;
                        errorInfo.userMessage = 'Request timed out. Please try again.';
                    } else if (error.status === 422) {
                        errorInfo.type = this.errorTypes.VALIDATION_ERROR;
                        errorInfo.userMessage = 'Invalid data provided. Please check your input.';
                    } else {
                        errorInfo.type = this.errorTypes.VALIDATION_ERROR;
                        errorInfo.userMessage = 'Invalid request. Please check your input and try again.';
                    }
                    break;
                    
                case 5:
                    errorInfo.type = this.errorTypes.SERVER_ERROR;
                    errorInfo.userMessage = 'Server error occurred. Please try again later.';
                    errorInfo.severity = 'high';
                    break;
            }
        }
        
        // Content-based categorization
        else if (error?.message) {
            const message = error.message.toLowerCase();
            
            if (message.includes('file') || message.includes('upload') || message.includes('processing')) {
                errorInfo.type = this.errorTypes.FILE_PROCESSING_ERROR;
                errorInfo.userMessage = 'File processing error. Please check the file format and try again.';
            } else if (message.includes('training') || message.includes('model')) {
                errorInfo.type = this.errorTypes.TRAINING_ERROR;
                errorInfo.userMessage = 'Training error occurred. Please check your configuration.';
            } else if (message.includes('timeout')) {
                errorInfo.type = this.errorTypes.TIMEOUT_ERROR;
                errorInfo.userMessage = 'Operation timed out. Please try again.';
            } else if (message.includes('validation') || message.includes('invalid')) {
                errorInfo.type = this.errorTypes.VALIDATION_ERROR;
                errorInfo.userMessage = 'Invalid data provided. Please check your input.';
            }
        }
        
        return errorInfo;
    }
    
    /**
     * Retry operation with exponential backoff
     */
    async retryWithBackoff(operation, context = {}) {
        const operationId = context.operationId || this.generateErrorId();
        const currentAttempts = this.retryAttempts.get(operationId) || 0;
        
        if (currentAttempts >= this.maxRetries) {
            throw new Error(`Operation failed after ${this.maxRetries} attempts`);
        }
        
        // Calculate delay with exponential backoff and jitter
        const delay = Math.min(
            this.baseDelay * Math.pow(2, currentAttempts) + Math.random() * 1000,
            this.maxDelay
        );
        
        this.retryAttempts.set(operationId, currentAttempts + 1);
        
        // Show retry notification
        this.showRetryNotification(currentAttempts + 1, this.maxRetries, delay);
        
        // Wait before retry
        await this.sleep(delay);
        
        try {
            const result = await operation();
            
            // Success - clear retry count
            this.retryAttempts.delete(operationId);
            this.hideRetryNotification();
            
            return result;
        } catch (error) {
            // If this was the last attempt, clear retry count and rethrow
            if (currentAttempts + 1 >= this.maxRetries) {
                this.retryAttempts.delete(operationId);
                this.hideRetryNotification();
                throw error;
            }
            
            // Otherwise, retry recursively
            return this.retryWithBackoff(operation, { ...context, operationId });
        }
    }
    
    /**
     * Show user-friendly error notification
     */
    showUserFriendlyError(errorInfo) {
        const notification = this.createNotification({
            type: 'error',
            title: this.getErrorTitle(errorInfo.type),
            message: errorInfo.userMessage,
            actions: this.getErrorActions(errorInfo),
            persistent: errorInfo.severity === 'high'
        });
        
        this.displayNotification(notification);
    }
    
    /**
     * Show success notification
     */
    showSuccess(message, title = 'Success') {
        const notification = this.createNotification({
            type: 'success',
            title: title,
            message: message,
            duration: 3000
        });
        
        this.displayNotification(notification);
    }
    
    /**
     * Show warning notification
     */
    showWarning(message, title = 'Warning') {
        const notification = this.createNotification({
            type: 'warning',
            title: title,
            message: message,
            duration: 5000
        });
        
        this.displayNotification(notification);
    }
    
    /**
     * Show info notification
     */
    showInfo(message, title = 'Information') {
        const notification = this.createNotification({
            type: 'info',
            title: title,
            message: message,
            duration: 4000
        });
        
        this.displayNotification(notification);
    }
    
    /**
     * Create notification element
     */
    createNotification({ type, title, message, actions = [], duration = 5000, persistent = false }) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            background: ${this.getNotificationColor(type)};
            border: 1px solid ${this.getNotificationBorderColor(type)};
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            animation: slideIn 0.3s ease-out;
            position: relative;
        `;
        
        const icon = this.getNotificationIcon(type);
        const closeButton = persistent ? '' : `
            <button onclick="this.parentElement.remove()" style="
                position: absolute;
                top: 8px;
                right: 8px;
                background: none;
                border: none;
                font-size: 18px;
                cursor: pointer;
                color: #6b7280;
                padding: 4px;
            ">&times;</button>
        `;
        
        const actionsHtml = actions.length > 0 ? `
            <div style="margin-top: 12px; display: flex; gap: 8px;">
                ${actions.map(action => `
                    <button onclick="${action.onClick}" style="
                        background: ${action.primary ? '#3b82f6' : 'transparent'};
                        color: ${action.primary ? 'white' : '#3b82f6'};
                        border: 1px solid #3b82f6;
                        padding: 6px 12px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 14px;
                    ">${action.text}</button>
                `).join('')}
            </div>
        ` : '';
        
        notification.innerHTML = `
            ${closeButton}
            <div style="display: flex; align-items: flex-start; gap: 12px;">
                <div style="font-size: 20px; margin-top: 2px;">${icon}</div>
                <div style="flex: 1;">
                    <div style="font-weight: 600; margin-bottom: 4px; color: #1f2937;">${title}</div>
                    <div style="color: #4b5563; font-size: 14px; line-height: 1.4;">${message}</div>
                    ${actionsHtml}
                </div>
            </div>
        `;
        
        // Auto-remove after duration (if not persistent)
        if (!persistent && duration > 0) {
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.style.animation = 'slideOut 0.3s ease-in';
                    setTimeout(() => notification.remove(), 300);
                }
            }, duration);
        }
        
        return notification;
    }
    
    /**
     * Display notification in container
     */
    displayNotification(notification) {
        const container = document.getElementById('error-notifications');
        if (container) {
            container.appendChild(notification);
            
            // Limit number of notifications
            const notifications = container.children;
            if (notifications.length > 5) {
                notifications[0].remove();
            }
        }
    }
    
    /**
     * Show retry notification
     */
    showRetryNotification(attempt, maxAttempts, delay) {
        const existingRetry = document.getElementById('retry-notification');
        if (existingRetry) {
            existingRetry.remove();
        }
        
        const notification = this.createNotification({
            type: 'info',
            title: 'Retrying Operation',
            message: `Attempt ${attempt} of ${maxAttempts}. Retrying in ${Math.round(delay / 1000)} seconds...`,
            persistent: true
        });
        
        notification.id = 'retry-notification';
        this.displayNotification(notification);
    }
    
    /**
     * Hide retry notification
     */
    hideRetryNotification() {
        const retryNotification = document.getElementById('retry-notification');
        if (retryNotification) {
            retryNotification.remove();
        }
    }
    
    /**
     * Helper methods
     */
    shouldRetry(errorInfo) {
        const retryableTypes = [
            this.errorTypes.NETWORK_ERROR,
            this.errorTypes.TIMEOUT_ERROR,
            this.errorTypes.SERVER_ERROR
        ];
        
        return retryableTypes.includes(errorInfo.type) && errorInfo.recoverable;
    }
    
    canRetry(errorInfo) {
        return errorInfo.recoverable && errorInfo.type !== this.errorTypes.AUTHENTICATION_ERROR;
    }
    
    scheduleRetry(errorInfo, context) {
        // This would typically schedule a retry operation
        // For now, just return retry information
        return {
            willRetry: true,
            retryIn: this.calculateRetryDelay(context.attempt || 0),
            maxAttempts: this.maxRetries
        };
    }
    
    calculateRetryDelay(attempt) {
        return Math.min(this.baseDelay * Math.pow(2, attempt), this.maxDelay);
    }
    
    getUserMessage(errorInfo) {
        return errorInfo.userMessage;
    }
    
    getErrorTitle(errorType) {
        const titles = {
            [this.errorTypes.NETWORK_ERROR]: 'Connection Error',
            [this.errorTypes.VALIDATION_ERROR]: 'Validation Error',
            [this.errorTypes.SERVER_ERROR]: 'Server Error',
            [this.errorTypes.TIMEOUT_ERROR]: 'Timeout Error',
            [this.errorTypes.FILE_PROCESSING_ERROR]: 'File Processing Error',
            [this.errorTypes.TRAINING_ERROR]: 'Training Error',
            [this.errorTypes.AUTHENTICATION_ERROR]: 'Authentication Required',
            [this.errorTypes.PERMISSION_ERROR]: 'Permission Denied',
            [this.errorTypes.UNKNOWN_ERROR]: 'Unexpected Error'
        };
        
        return titles[errorType] || 'Error';
    }
    
    getErrorActions(errorInfo) {
        const actions = [];
        
        if (errorInfo.type === this.errorTypes.AUTHENTICATION_ERROR) {
            actions.push({
                text: 'Login',
                primary: true,
                onClick: 'window.location.href="/auth/login"'
            });
        } else if (this.canRetry(errorInfo)) {
            actions.push({
                text: 'Retry',
                primary: true,
                onClick: 'location.reload()'
            });
        }
        
        actions.push({
            text: 'Dismiss',
            primary: false,
            onClick: 'this.closest(".notification").remove()'
        });
        
        return actions;
    }
    
    getNotificationColor(type) {
        const colors = {
            error: '#fef2f2',
            success: '#f0fdf4',
            warning: '#fffbeb',
            info: '#eff6ff'
        };
        return colors[type] || colors.info;
    }
    
    getNotificationBorderColor(type) {
        const colors = {
            error: '#fecaca',
            success: '#bbf7d0',
            warning: '#fed7aa',
            info: '#bfdbfe'
        };
        return colors[type] || colors.info;
    }
    
    getNotificationIcon(type) {
        const icons = {
            error: '❌',
            success: '✅',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || icons.info;
    }
    
    generateErrorId() {
        return 'error_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    logError(errorInfo, context) {
        this.errorHistory.push({
            ...errorInfo,
            context,
            timestamp: new Date().toISOString()
        });
        
        // Keep only last 100 errors
        if (this.errorHistory.length > 100) {
            this.errorHistory = this.errorHistory.slice(-100);
        }
        
        // Log to console in development
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            console.error('Error logged:', errorInfo, context);
        }
    }
    
    handleGlobalError(error, type) {
        const errorInfo = this.categorizeError(error);
        this.logError(errorInfo, { type, global: true });
        
        // Don't show notifications for all global errors to avoid spam
        if (errorInfo.severity === 'high') {
            this.showUserFriendlyError(errorInfo);
        }
    }
    
    getErrorHistory() {
        return this.errorHistory;
    }
    
    clearErrorHistory() {
        this.errorHistory = [];
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .notification {
        transition: all 0.3s ease;
    }
    
    .notification:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
    }
`;
document.head.appendChild(style);

// Create global error handler instance
window.errorHandler = new ErrorHandler();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ErrorHandler;
}