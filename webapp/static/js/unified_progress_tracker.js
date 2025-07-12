/**
 * Unified Progress Tracker for AI Processing
 * Enhanced frontend component for real-time progress tracking with WebSocket support
 * Combines polling and WebSocket for maximum reliability
 */

class UnifiedProgressTracker {
    constructor(options = {}) {
        this.options = {
            pollingInterval: 2000,
            maxRetries: 5,
            enableWebSocket: true,
            enablePolling: true,
            autoRetry: true,
            showDetailedStats: true,
            ...options
        };
        
        // State management
        this.progressId = null;
        this.isActive = false;
        this.retryCount = 0;
        this.pollingInterval = null;
        this.socket = null;
        this.isConnected = false;
        
        // Progress data
        this.currentProgress = {
            percentage: 0,
            current_step: 0,
            total_steps: 0,
            current_operation: 'Initializing...',
            submission_index: 0,
            total_submissions: 0,
            status: 'initializing',
            details: '',
            estimated_time_remaining: null,
            processing_speed: null,
            stage: 'initialization'
        };
        
        // UI elements cache
        this.elements = {};
        
        // Callbacks
        this.callbacks = {
            onProgress: null,
            onComplete: null,
            onError: null,
            onStageChange: null
        };
        
        this.initializeUI();
        if (this.options.enableWebSocket) {
            this.initializeWebSocket();
        }
    }
    
    /**
     * Initialize UI elements and cache references
     */
    initializeUI() {
        this.elements = {
            container: document.getElementById('unified-progress-container'),
            progressBar: document.getElementById('unified-progress-bar'),
            progressText: document.getElementById('unified-progress-text'),
            progressDetails: document.getElementById('unified-progress-details'),
            progressEta: document.getElementById('unified-progress-eta'),
            progressSpeed: document.getElementById('unified-progress-speed'),
            stageIndicator: document.getElementById('unified-stage-indicator'),
            submissionCounter: document.getElementById('unified-submission-counter'),
            connectionStatus: document.getElementById('unified-connection-status'),
            retryButton: document.getElementById('unified-retry-button'),
            cancelButton: document.getElementById('unified-cancel-button'),
            
            // Stage indicators
            stageOcr: document.getElementById('stage-ocr'),
            stageMapping: document.getElementById('stage-mapping'),
            stageGrading: document.getElementById('stage-grading'),
            stageFinalization: document.getElementById('stage-finalization'),
            
            // Status containers
            processingStatus: document.getElementById('processing-status'),
            completeStatus: document.getElementById('complete-status'),
            errorStatus: document.getElementById('error-status')
        };
        
        this.bindEventHandlers();
    }
    
    /**
     * Initialize WebSocket connection for real-time updates
     */
    initializeWebSocket() {
        try {
            if (typeof io !== 'undefined') {
                this.socket = io();
                
                this.socket.on('connect', () => {
                    console.log('Unified Progress Tracker: WebSocket connected');
                    this.isConnected = true;
                    this.updateConnectionStatus(true);
                });
                
                this.socket.on('disconnect', () => {
                    console.log('Unified Progress Tracker: WebSocket disconnected');
                    this.isConnected = false;
                    this.updateConnectionStatus(false);
                    
                    // Fallback to polling if WebSocket fails
                    if (this.isActive && this.options.enablePolling) {
                        this.startPolling();
                    }
                });
                
                this.socket.on('progress_update', (data) => {
                    if (data.progress_id === this.progressId) {
                        this.handleProgressUpdate(data);
                    }
                });
                
                this.socket.on('processing_complete', (data) => {
                    if (data.progress_id === this.progressId) {
                        this.handleComplete(data);
                    }
                });
                
                this.socket.on('processing_error', (data) => {
                    if (data.progress_id === this.progressId) {
                        this.handleError(data);
                    }
                });
                
            } else {
                console.warn('Socket.IO not available, falling back to polling only');
                this.options.enableWebSocket = false;
            }
        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
            this.options.enableWebSocket = false;
        }
    }
    
    /**
     * Bind event handlers for UI interactions
     */
    bindEventHandlers() {
        if (this.elements.retryButton) {
            this.elements.retryButton.addEventListener('click', () => {
                this.retry();
            });
        }
        
        if (this.elements.cancelButton) {
            this.elements.cancelButton.addEventListener('click', () => {
                this.cancel();
            });
        }
    }
    
    /**
     * Start tracking progress for a given progress ID
     */
    start(progressId, callbacks = {}) {
        this.progressId = progressId;
        this.isActive = true;
        this.retryCount = 0;
        this.callbacks = { ...this.callbacks, ...callbacks };
        
        console.log('Starting unified progress tracking for ID:', progressId);
        
        // Join WebSocket room if available
        if (this.isConnected && this.socket) {
            this.socket.emit('join_progress_room', { progress_id: progressId });
        }
        
        // Start polling as primary or fallback method
        if (this.options.enablePolling) {
            this.startPolling();
        }
        
        this.showProcessingUI();
    }
    
    /**
     * Stop progress tracking
     */
    stop() {
        this.isActive = false;
        this.stopPolling();
        
        if (this.isConnected && this.socket && this.progressId) {
            this.socket.emit('leave_progress_room', { progress_id: this.progressId });
        }
        
        console.log('Stopped unified progress tracking');
    }
    
    /**
     * Start polling for progress updates
     */
    startPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
        
        this.pollingInterval = setInterval(async () => {
            if (!this.isActive || !this.progressId) {
                this.stopPolling();
                return;
            }
            
            try {
                const progress = await this.fetchProgress(this.progressId);
                this.handleProgressUpdate({ progress });
                this.retryCount = 0; // Reset on successful fetch
                
            } catch (error) {
                console.error('Polling error:', error);
                this.retryCount++;
                
                if (this.retryCount >= this.options.maxRetries) {
                    this.stopPolling();
                    this.handleError({ 
                        error: `Failed to fetch progress after ${this.options.maxRetries} attempts`,
                        details: error.message 
                    });
                }
            }
        }, this.options.pollingInterval);
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
     * Fetch progress data from API
     */
    async fetchProgress(progressId) {
        const response = await fetch(`/api/progress/${progressId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to fetch progress');
        }
        
        return data.progress;
    }
    
    /**
     * Handle progress update from WebSocket or polling
     */
    handleProgressUpdate(data) {
        const progress = data.progress || data;
        this.currentProgress = { ...this.currentProgress, ...progress };
        
        this.updateProgressUI(this.currentProgress);
        
        // Check for completion or error
        if (progress.status === 'completed') {
            this.handleComplete(data);
        } else if (progress.status === 'failed' || progress.status === 'error') {
            this.handleError(data);
        }
        
        // Trigger callback
        if (this.callbacks.onProgress) {
            this.callbacks.onProgress(this.currentProgress);
        }
    }
    
    /**
     * Handle processing completion
     */
    handleComplete(data) {
        this.stop();
        this.showCompleteUI();
        
        if (this.callbacks.onComplete) {
            this.callbacks.onComplete(data);
        }
    }
    
    /**
     * Handle processing error
     */
    handleError(data) {
        this.stop();
        this.showErrorUI(data.error || data.message || 'Processing failed');
        
        if (this.callbacks.onError) {
            this.callbacks.onError(data);
        }
    }
    
    /**
     * Update progress UI elements
     */
    updateProgressUI(progress) {
        // Update progress bar
        if (this.elements.progressBar) {
            this.elements.progressBar.style.width = `${progress.percentage || 0}%`;
            this.elements.progressBar.setAttribute('aria-valuenow', progress.percentage || 0);
        }
        
        // Update progress text
        if (this.elements.progressText) {
            this.elements.progressText.textContent = progress.current_operation || 'Processing...';
        }
        
        // Update details
        if (this.elements.progressDetails) {
            const details = progress.details || 
                `Step ${progress.current_step || 0}/${progress.total_steps || 0}`;
            this.elements.progressDetails.textContent = details;
        }
        
        // Update submission counter
        if (this.elements.submissionCounter) {
            this.elements.submissionCounter.textContent = 
                `Submission ${progress.submission_index || 0}/${progress.total_submissions || 0}`;
        }
        
        // Update ETA
        if (this.elements.progressEta && progress.estimated_time_remaining) {
            const eta = Math.round(progress.estimated_time_remaining);
            this.elements.progressEta.textContent = `ETA: ${this.formatTime(eta)}`;
        }
        
        // Update processing speed
        if (this.elements.progressSpeed && progress.processing_speed) {
            this.elements.progressSpeed.textContent = 
                `Speed: ${progress.processing_speed.toFixed(2)} items/min`;
        }
        
        // Update stage indicators
        this.updateStageIndicators(progress.current_operation, progress.stage);
        
        // Update progress bar color based on status
        this.updateProgressBarColor(progress.status);
    }
    
    /**
     * Update stage indicators based on current operation
     */
    updateStageIndicators(currentOperation, stage) {
        const stages = {
            ocr: this.elements.stageOcr,
            mapping: this.elements.stageMapping,
            grading: this.elements.stageGrading,
            finalization: this.elements.stageFinalization
        };
        
        // Reset all stages
        Object.values(stages).forEach(element => {
            if (element) {
                element.className = element.className.replace(/bg-\w+-\d+/, 'bg-gray-300');
            }
        });
        
        // Determine current stage
        let currentStage = stage || this.determineStageFromOperation(currentOperation);
        
        // Update stage indicators
        const stageOrder = ['ocr', 'mapping', 'grading', 'finalization'];
        const currentIndex = stageOrder.indexOf(currentStage);
        
        stageOrder.forEach((stageName, index) => {
            const element = stages[stageName];
            if (element) {
                if (index < currentIndex) {
                    // Completed stage
                    element.className = element.className.replace(/bg-\w+-\d+/, 'bg-green-500');
                } else if (index === currentIndex) {
                    // Current stage
                    element.className = element.className.replace(/bg-\w+-\d+/, 'bg-blue-500');
                    element.classList.add('animate-pulse');
                } else {
                    // Future stage
                    element.className = element.className.replace(/bg-\w+-\d+/, 'bg-gray-300');
                    element.classList.remove('animate-pulse');
                }
            }
        });
        
        // Trigger stage change callback
        if (this.callbacks.onStageChange && currentStage !== this.currentProgress.stage) {
            this.callbacks.onStageChange(currentStage, this.currentProgress.stage);
        }
    }
    
    /**
     * Determine processing stage from operation text
     */
    determineStageFromOperation(operation) {
        if (!operation) return 'ocr';
        
        const op = operation.toLowerCase();
        
        if (op.includes('ocr') || op.includes('extract') || op.includes('image') || op.includes('text')) {
            return 'ocr';
        } else if (op.includes('map') || op.includes('match') || op.includes('align')) {
            return 'mapping';
        } else if (op.includes('grade') || op.includes('score') || op.includes('evaluate') || op.includes('assess')) {
            return 'grading';
        } else if (op.includes('finalize') || op.includes('complete') || op.includes('save')) {
            return 'finalization';
        }
        
        return 'ocr'; // Default
    }
    
    /**
     * Update progress bar color based on status
     */
    updateProgressBarColor(status) {
        if (!this.elements.progressBar) return;
        
        // Remove existing color classes
        this.elements.progressBar.classList.remove('bg-blue-600', 'bg-green-600', 'bg-red-600', 'bg-yellow-600');
        
        switch (status) {
            case 'completed':
                this.elements.progressBar.classList.add('bg-green-600');
                break;
            case 'failed':
            case 'error':
                this.elements.progressBar.classList.add('bg-red-600');
                break;
            case 'paused':
                this.elements.progressBar.classList.add('bg-yellow-600');
                break;
            default:
                this.elements.progressBar.classList.add('bg-blue-600');
        }
    }
    
    /**
     * Show processing UI state
     */
    showProcessingUI() {
        if (this.elements.processingStatus) {
            this.elements.processingStatus.classList.remove('hidden');
        }
        if (this.elements.completeStatus) {
            this.elements.completeStatus.classList.add('hidden');
        }
        if (this.elements.errorStatus) {
            this.elements.errorStatus.classList.add('hidden');
        }
    }
    
    /**
     * Show completion UI state
     */
    showCompleteUI() {
        if (this.elements.processingStatus) {
            this.elements.processingStatus.classList.add('hidden');
        }
        if (this.elements.completeStatus) {
            this.elements.completeStatus.classList.remove('hidden');
        }
        if (this.elements.errorStatus) {
            this.elements.errorStatus.classList.add('hidden');
        }
    }
    
    /**
     * Show error UI state
     */
    showErrorUI(errorMessage) {
        if (this.elements.processingStatus) {
            this.elements.processingStatus.classList.add('hidden');
        }
        if (this.elements.completeStatus) {
            this.elements.completeStatus.classList.add('hidden');
        }
        if (this.elements.errorStatus) {
            this.elements.errorStatus.classList.remove('hidden');
            
            const errorElement = this.elements.errorStatus.querySelector('.error-message');
            if (errorElement) {
                errorElement.textContent = errorMessage;
            }
        }
    }
    
    /**
     * Update connection status indicator
     */
    updateConnectionStatus(isConnected) {
        if (this.elements.connectionStatus) {
            if (isConnected) {
                this.elements.connectionStatus.className = 'w-2 h-2 bg-green-500 rounded-full';
                this.elements.connectionStatus.title = 'Real-time connection active';
            } else {
                this.elements.connectionStatus.className = 'w-2 h-2 bg-yellow-500 rounded-full';
                this.elements.connectionStatus.title = 'Using polling updates';
            }
        }
    }
    
    /**
     * Retry processing
     */
    async retry() {
        try {
            const response = await fetch('/api/process-unified-ai', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({}),
                credentials: 'same-origin'
            });
            
            const data = await response.json();
            
            if (data.success && data.progress_id) {
                this.start(data.progress_id);
            } else {
                throw new Error(data.error || 'Retry failed');
            }
            
        } catch (error) {
            console.error('Retry failed:', error);
            this.showErrorUI(`Retry failed: ${error.message}`);
        }
    }
    
    /**
     * Cancel processing
     */
    async cancel() {
        if (!this.progressId) return;
        
        try {
            const response = await fetch(`/api/cancel-processing/${this.progressId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.stop();
                this.showErrorUI('Processing cancelled by user');
            } else {
                throw new Error(data.error || 'Cancel failed');
            }
            
        } catch (error) {
            console.error('Cancel failed:', error);
        }
    }
    
    /**
     * Get CSRF token
     */
    getCSRFToken() {
        if (typeof ExamGrader !== 'undefined' && ExamGrader.csrf) {
            return ExamGrader.csrf.getToken();
        }
        
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }
    
    /**
     * Format time in seconds to human readable format
     */
    formatTime(seconds) {
        if (seconds < 60) {
            return `${seconds}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            return `${minutes}m ${remainingSeconds}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }
    
    /**
     * Get current progress data
     */
    getCurrentProgress() {
        return { ...this.currentProgress };
    }
    
    /**
     * Set callback functions
     */
    setCallbacks(callbacks) {
        this.callbacks = { ...this.callbacks, ...callbacks };
    }
    
    /**
     * Destroy the progress tracker and clean up resources
     */
    destroy() {
        this.stop();
        
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        
        // Remove event listeners
        Object.values(this.elements).forEach(element => {
            if (element && element.removeEventListener) {
                element.removeEventListener('click', () => {});
            }
        });
        
        console.log('Unified Progress Tracker destroyed');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UnifiedProgressTracker;
} else if (typeof window !== 'undefined') {
    window.UnifiedProgressTracker = UnifiedProgressTracker;
}