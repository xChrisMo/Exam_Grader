/**
 * Refactored AI Processing Frontend Module
 * 
 * Provides detailed step-by-step progress tracking for the refactored unified AI pipeline:
 * - Real-time progress updates via SocketIO
 * - Fallback polling mechanism
 * - Detailed UI updates for each processing step
 * - Error handling and recovery
 */

class RefactoredAIProcessor {
    constructor(options = {}) {
        this.options = {
            apiBaseUrl: '/api/refactored-ai',
            pollInterval: 2000,
            maxRetries: 3,
            ...options
        };
        
        this.socket = null;
        this.currentSession = null;
        this.progressCallback = null;
        this.errorCallback = null;
        this.completeCallback = null;
        this.pollingInterval = null;
        this.isProcessing = false;
        
        this.initializeSocketIO();
    }
    
    /**
     * Initialize SocketIO connection for real-time updates
     */
    initializeSocketIO() {
        if (typeof io !== 'undefined') {
            this.socket = io();
            
            this.socket.on('connect', () => {
                console.log('Connected to SocketIO for AI processing');
                // Subscribe to user-specific progress updates
                this.socket.emit('subscribe_user_progress');
            });
            
            this.socket.on('disconnect', () => {
                console.log('Disconnected from SocketIO');
            });
            
            this.socket.on('progress_update', (data) => {
                this.handleProgressUpdate(data);
            });
            
            this.socket.on('ai_progress', (data) => {
                this.handleProgressUpdate(data);
            });
            
            this.socket.on('session_status', (data) => {
                this.handleSessionStatus(data);
            });
        } else {
            console.warn('SocketIO not available, using polling fallback');
        }
    }
    
    /**
     * Start AI processing for a submission
     * @param {string} submissionId - ID of the submission to process
     * @param {string} guideId - ID of the marking guide to use
     * @param {Object} callbacks - Callback functions for progress, error, and completion
     */
    async startProcessing(submissionId, guideId, callbacks = {}) {
        if (this.isProcessing) {
            throw new Error('Processing already in progress');
        }
        
        this.progressCallback = callbacks.onProgress || null;
        this.errorCallback = callbacks.onError || null;
        this.completeCallback = callbacks.onComplete || null;
        
        try {
            this.isProcessing = true;
            
            // Start processing
            const response = await fetch(`${this.options.apiBaseUrl}/process`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    submission_id: submissionId,
                    guide_id: guideId
                })
            });
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Processing failed');
            }
            
            this.currentSession = {
                sessionId: result.session_id,
                submissionId: submissionId,
                guideId: guideId,
                roomId: result.room_id,
                startTime: Date.now()
            };
            
            // Join progress room for real-time updates
            if (this.socket && result.room_id) {
                this.socket.emit('join_progress_room', { room_id: result.room_id });
            }
            
            // Start polling as fallback
            this.startPolling();
            
            // If processing completed immediately, handle it
            if (result.status === 'completed') {
                this.handleCompletion(result);
            } else if (result.status === 'failed') {
                this.handleError(result.error || 'Processing failed', result);
            }
            
            return result;
            
        } catch (error) {
            this.isProcessing = false;
            this.handleError(error.message);
            throw error;
        }
    }
    
    /**
     * Get current session status
     * @param {string} sessionId - Session ID to check
     */
    async getSessionStatus(sessionId) {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/status/${sessionId}`);
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to get session status');
            }
            
            return result.status;
        } catch (error) {
            console.error('Error getting session status:', error);
            throw error;
        }
    }
    
    /**
     * Start polling for progress updates (fallback mechanism)
     */
    startPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
        
        this.pollingInterval = setInterval(async () => {
            if (!this.currentSession || !this.isProcessing) {
                this.stopPolling();
                return;
            }
            
            try {
                const status = await this.getSessionStatus(this.currentSession.sessionId);
                
                if (status.status === 'completed') {
                    this.handleCompletion(status);
                } else if (status.status === 'failed') {
                    this.handleError(status.error_message || 'Processing failed', status);
                }
            } catch (error) {
                console.warn('Polling error:', error);
            }
        }, this.options.pollInterval);
    }
    
    /**
     * Stop polling
     */
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
    
    /**
     * Handle progress update from SocketIO or polling
     * @param {Object} data - Progress data
     */
    handleProgressUpdate(data) {
        if (!this.currentSession || data.session_id !== this.currentSession.sessionId) {
            return;
        }
        
        console.log('Progress update:', data);
        
        // Update UI based on progress data
        this.updateProgressUI(data);
        
        // Call progress callback
        if (this.progressCallback) {
            this.progressCallback(data);
        }
        
        // Check if completed
        if (data.status === 'completed') {
            this.handleCompletion(data);
        } else if (data.status === 'failed') {
            this.handleError(data.error_message || 'Processing failed', data);
        }
    }
    
    /**
     * Handle session status update
     * @param {Object} data - Session status data
     */
    handleSessionStatus(data) {
        if (!this.currentSession || data.session_id !== this.currentSession.sessionId) {
            return;
        }
        
        this.handleProgressUpdate(data.status);
    }
    
    /**
     * Update progress UI elements
     * @param {Object} progressData - Progress data
     */
    updateProgressUI(progressData) {
        // Update progress bar
        const progressBar = document.querySelector('.ai-progress-bar');
        if (progressBar) {
            progressBar.style.width = `${progressData.progress_percentage || 0}%`;
            progressBar.setAttribute('aria-valuenow', progressData.progress_percentage || 0);
        }
        
        // Update progress percentage text
        const progressText = document.querySelector('.ai-progress-percentage');
        if (progressText) {
            progressText.textContent = `${Math.round(progressData.progress_percentage || 0)}%`;
        }
        
        // Update current operation
        const operationText = document.querySelector('.ai-current-operation');
        if (operationText) {
            operationText.textContent = progressData.current_operation || '';
        }
        
        // Update step indicators
        this.updateStepIndicators(progressData.steps || {});
        
        // Update statistics
        this.updateStatistics(progressData);
        
        // Update status
        const statusElement = document.querySelector('.ai-processing-status');
        if (statusElement) {
            statusElement.textContent = this.getStatusDisplayText(progressData.status);
            statusElement.className = `ai-processing-status status-${progressData.status}`;
        }
    }
    
    /**
     * Update step indicators in the UI
     * @param {Object} steps - Step status object
     */
    updateStepIndicators(steps) {
        const stepOrder = ['text_retrieval', 'mapping', 'grading', 'saving'];
        const stepLabels = {
            'text_retrieval': 'Retrieving Data',
            'mapping': 'Mapping Answers',
            'grading': 'Grading Responses',
            'saving': 'Saving Results'
        };
        
        stepOrder.forEach((stepKey, index) => {
            const stepElement = document.querySelector(`[data-step="${stepKey}"]`);
            if (stepElement) {
                const status = steps[stepKey] || 'pending';
                
                // Update step status class
                stepElement.className = `ai-step ai-step-${status}`;
                
                // Update step icon
                const iconElement = stepElement.querySelector('.step-icon');
                if (iconElement) {
                    iconElement.innerHTML = this.getStepIcon(status);
                }
                
                // Update step text
                const textElement = stepElement.querySelector('.step-text');
                if (textElement) {
                    textElement.textContent = stepLabels[stepKey];
                }
                
                // Update step status text
                const statusElement = stepElement.querySelector('.step-status');
                if (statusElement) {
                    statusElement.textContent = this.getStepStatusText(status);
                }
            }
        });
    }
    
    /**
     * Update processing statistics
     * @param {Object} progressData - Progress data
     */
    updateStatistics(progressData) {
        // Questions mapped
        const mappedElement = document.querySelector('.stat-questions-mapped');
        if (mappedElement) {
            mappedElement.textContent = progressData.questions_mapped || 0;
        }
        
        // Questions graded
        const gradedElement = document.querySelector('.stat-questions-graded');
        if (gradedElement) {
            gradedElement.textContent = progressData.questions_graded || 0;
        }
        
        // Max questions limit
        const limitElement = document.querySelector('.stat-max-questions');
        if (limitElement) {
            limitElement.textContent = progressData.max_questions_limit || 'No limit';
        }
        
        // Processing time
        if (this.currentSession) {
            const elapsed = (Date.now() - this.currentSession.startTime) / 1000;
            const timeElement = document.querySelector('.stat-processing-time');
            if (timeElement) {
                timeElement.textContent = `${elapsed.toFixed(1)}s`;
            }
        }
    }
    
    /**
     * Get step icon HTML based on status
     * @param {string} status - Step status
     */
    getStepIcon(status) {
        switch (status) {
            case 'completed':
                return '<i class="fas fa-check-circle text-success"></i>';
            case 'in_progress':
                return '<i class="fas fa-spinner fa-spin text-primary"></i>';
            case 'failed':
                return '<i class="fas fa-times-circle text-danger"></i>';
            default:
                return '<i class="fas fa-circle text-muted"></i>';
        }
    }
    
    /**
     * Get step status display text
     * @param {string} status - Step status
     */
    getStepStatusText(status) {
        switch (status) {
            case 'completed':
                return 'Completed';
            case 'in_progress':
                return 'In Progress';
            case 'failed':
                return 'Failed';
            default:
                return 'Pending';
        }
    }
    
    /**
     * Get status display text
     * @param {string} status - Processing status
     */
    getStatusDisplayText(status) {
        switch (status) {
            case 'not_started':
                return 'Not Started';
            case 'text_retrieval':
                return 'Retrieving Data';
            case 'mapping':
                return 'Mapping Answers';
            case 'grading':
                return 'Grading Responses';
            case 'saving':
                return 'Saving Results';
            case 'completed':
                return 'Completed';
            case 'failed':
                return 'Failed';
            default:
                return 'Processing';
        }
    }
    
    /**
     * Handle processing completion
     * @param {Object} result - Completion result
     */
    handleCompletion(result) {
        this.isProcessing = false;
        this.stopPolling();
        
        // Leave progress room
        if (this.socket && this.currentSession?.roomId) {
            this.socket.emit('leave_progress_room', { room_id: this.currentSession.roomId });
        }
        
        console.log('AI processing completed:', result);
        
        // Update UI to show completion
        this.showCompletionUI(result);
        
        // Call completion callback
        if (this.completeCallback) {
            this.completeCallback(result);
        }
    }
    
    /**
     * Handle processing error
     * @param {string} error - Error message
     * @param {Object} data - Additional error data
     */
    handleError(error, data = {}) {
        this.isProcessing = false;
        this.stopPolling();
        
        // Leave progress room
        if (this.socket && this.currentSession?.roomId) {
            this.socket.emit('leave_progress_room', { room_id: this.currentSession.roomId });
        }
        
        console.error('AI processing error:', error, data);
        
        // Update UI to show error
        this.showErrorUI(error, data);
        
        // Call error callback
        if (this.errorCallback) {
            this.errorCallback(error, data);
        }
    }
    
    /**
     * Show completion UI
     * @param {Object} result - Completion result
     */
    showCompletionUI(result) {
        // Update progress bar to 100%
        const progressBar = document.querySelector('.ai-progress-bar');
        if (progressBar) {
            progressBar.style.width = '100%';
            progressBar.classList.add('bg-success');
        }
        
        // Show completion message
        const messageElement = document.querySelector('.ai-completion-message');
        if (messageElement) {
            messageElement.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle"></i>
                    <strong>Processing Completed Successfully!</strong><br>
                    <small>
                        Mapped: ${result.questions_mapped || 0} questions | 
                        Graded: ${result.questions_graded || 0} answers | 
                        Selected: ${result.questions_selected || 0} best answers
                    </small>
                </div>
            `;
            messageElement.style.display = 'block';
        }
        
        // Show action buttons
        const actionsElement = document.querySelector('.ai-completion-actions');
        if (actionsElement) {
            actionsElement.innerHTML = `
                <button class="btn btn-primary" onclick="window.location.href='/results'">
                    <i class="fas fa-chart-bar"></i> View Results
                </button>
                <button class="btn btn-secondary" onclick="window.location.href='/dashboard'">
                    <i class="fas fa-home"></i> Return to Dashboard
                </button>
            `;
            actionsElement.style.display = 'block';
        }
    }
    
    /**
     * Show error UI
     * @param {string} error - Error message
     * @param {Object} data - Additional error data
     */
    showErrorUI(error, data) {
        // Update progress bar to show error
        const progressBar = document.querySelector('.ai-progress-bar');
        if (progressBar) {
            progressBar.classList.add('bg-danger');
        }
        
        // Show error message
        const messageElement = document.querySelector('.ai-error-message');
        if (messageElement) {
            messageElement.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i>
                    <strong>Processing Failed</strong><br>
                    ${error}
                </div>
            `;
            messageElement.style.display = 'block';
        }
        
        // Show retry button
        const actionsElement = document.querySelector('.ai-error-actions');
        if (actionsElement) {
            actionsElement.innerHTML = `
                <button class="btn btn-warning" onclick="location.reload()">
                    <i class="fas fa-redo"></i> Retry Processing
                </button>
                <button class="btn btn-secondary" onclick="window.location.href='/dashboard'">
                    <i class="fas fa-home"></i> Return to Dashboard
                </button>
            `;
            actionsElement.style.display = 'block';
        }
    }
    
    /**
     * Get CSRF token from meta tag or cookie
     */
    getCSRFToken() {
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            return metaToken.getAttribute('content');
        }
        
        // Fallback to cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrf_token') {
                return value;
            }
        }
        
        return '';
    }
    
    /**
     * Stop current processing
     */
    stopProcessing() {
        this.isProcessing = false;
        this.stopPolling();
        
        if (this.socket && this.currentSession?.roomId) {
            this.socket.emit('leave_progress_room', { room_id: this.currentSession.roomId });
        }
        
        this.currentSession = null;
    }
    
    /**
     * Cleanup resources
     */
    destroy() {
        this.stopProcessing();
        
        if (this.socket) {
            this.socket.emit('unsubscribe_user_progress');
            this.socket.disconnect();
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RefactoredAIProcessor;
} else {
    window.RefactoredAIProcessor = RefactoredAIProcessor;
}

// Auto-initialize if DOM is ready
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function() {
        // Initialize global instance
        window.aiProcessor = new RefactoredAIProcessor();
        
        // Bind to form submission if processing form exists
        const processingForm = document.querySelector('#refactored-ai-form');
        if (processingForm) {
            processingForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const submissionId = document.querySelector('#submission-id')?.value;
                const guideId = document.querySelector('#guide-id')?.value;
                
                if (!submissionId || !guideId) {
                    alert('Please select both a submission and marking guide.');
                    return;
                }
                
                try {
                    await window.aiProcessor.startProcessing(submissionId, guideId, {
                        onProgress: (data) => {
                            console.log('Progress:', data);
                        },
                        onComplete: (result) => {
                            console.log('Completed:', result);
                        },
                        onError: (error) => {
                            console.error('Error:', error);
                        }
                    });
                } catch (error) {
                    alert(`Failed to start processing: ${error.message}`);
                }
            });
        }
    });
}