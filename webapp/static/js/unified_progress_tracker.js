/**
 * Unified Progress Tracker
 * Handles real-time progress tracking for processing operations with improved error handling
 */

class UnifiedProgressTracker {
    constructor(options = {}) {
        this.progressId = null;
        this.intervalId = null;
        this.isTracking = false;
        this.retryCount = 0;
        this.maxRetries = options.maxRetries || 10;
        this.pollingInterval = options.pollingInterval || 2000;
        this.callbacks = {
            onProgress: null,
            onComplete: null,
            onError: null,
            onStageChange: null
        };
        this.lastStage = null;
    }

    /**
     * Start tracking progress for a given progress ID
     */
    start(progressId, callbacks = {}) {
        this.progressId = progressId;
        this.callbacks = { ...this.callbacks, ...callbacks };
        this.isTracking = true;
        this.retryCount = 0;

        // Start polling for progress updates
        this.checkProgress();
    }

    /**
     * Set callbacks for progress events
     */
    setCallbacks(callbacks) {
        this.callbacks = { ...this.callbacks, ...callbacks };
    }

    /**
     * Stop tracking progress
     */
    stopTracking() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        this.isTracking = false;
    }

    /**
     * Check current progress status with improved error handling and retry logic
     */
    async checkProgress() {
        if (!this.progressId || !this.isTracking) {
            return;
        }

        try {
            // Try enhanced processing endpoint first, then fallback to legacy
            const endpoints = [
                `/api/enhanced-processing/progress/${this.progressId}`,
                `/processing/status/${this.progressId}`,
                `/api/progress/${this.progressId}`
            ];
            
            let response = null;
            let lastError = null;
            
            for (const endpoint of endpoints) {
                try {
                    response = await fetch(endpoint);
                    if (response.ok) {
                        break;
                    }
                } catch (err) {
                    lastError = err;
                    continue;
                }
            }
            
            if (!response || !response.ok) {
                throw lastError || new Error(`All endpoints failed`);
            }

            const data = await response.json();
            
            if (data.success) {
                this.retryCount = 0; // Reset retry count on success
                const progress = data;
                
                // Detect stage changes
                const currentStage = this.detectCurrentStage(progress);
                if (currentStage !== this.lastStage) {
                    if (this.callbacks.onStageChange) {
                        this.callbacks.onStageChange(currentStage, this.lastStage);
                    }
                    this.lastStage = currentStage;
                }
                
                // Call progress callback
                if (this.callbacks.onProgress) {
                    this.callbacks.onProgress(progress);
                }

                // Check if completed
                if (progress.status === 'completed') {
                    this.stopTracking();
                    if (this.callbacks.onComplete) {
                        this.callbacks.onComplete(progress);
                    }
                } else if (progress.status === 'failed') {
                    this.stopTracking();
                    if (this.callbacks.onError) {
                        this.callbacks.onError({ message: progress.message || 'Processing failed' });
                    }
                } else {
                    // Schedule next check with exponential backoff
                    const delay = Math.min(this.pollingInterval * Math.pow(1.5, this.retryCount), 10000);
                    this.intervalId = setTimeout(() => this.checkProgress(), delay);
                }
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        } catch (error) {
            this.retryCount++;
            
            if (this.retryCount >= this.maxRetries) {
                this.stopTracking();
                if (this.callbacks.onError) {
                    this.callbacks.onError(error);
                }
            } else {
                // Retry with exponential backoff
                const retryDelay = Math.min(1000 * Math.pow(2, this.retryCount), 30000);
                this.intervalId = setTimeout(() => this.checkProgress(), retryDelay);
            }
        }
    }

    /**
     * Detect current processing stage based on progress data
     */
    detectCurrentStage(progress) {
        const message = (progress.message || '').toLowerCase();
        const operation = (progress.current_operation || '').toLowerCase();
        
        if (message.includes('ocr') || operation.includes('ocr') || message.includes('extract')) {
            return 'ocr';
        } else if (message.includes('map') || operation.includes('map') || message.includes('align')) {
            return 'mapping';
        } else if (message.includes('grad') || operation.includes('grad') || message.includes('assess')) {
            return 'grading';
        } else if (message.includes('final') || operation.includes('final') || message.includes('complet')) {
            return 'finalization';
        }
        
        return 'processing';
    }

    /**
     * Destroy the tracker and clean up resources
     */
    destroy() {
        this.stopTracking();
        this.callbacks = {};
        this.progressId = null;
    }

    /**
     * Update progress display elements
     */
    updateProgressDisplay(progress) {
        // Update progress bar
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = `${progress.percentage}%`;
            progressBar.setAttribute('aria-valuenow', progress.percentage);
        }

        // Update progress text
        const progressText = document.querySelector('.progress-text');
        if (progressText) {
            progressText.textContent = `${Math.round(progress.percentage)}%`;
        }

        // Update current operation
        const operationText = document.querySelector('.current-operation');
        if (operationText) {
            operationText.textContent = progress.current_operation || 'Processing...';
        }

        // Update step counter
        const stepCounter = document.querySelector('.step-counter');
        if (stepCounter) {
            stepCounter.textContent = `Step ${progress.current_step} of ${progress.total_steps}`;
        }

        // Update time remaining
        if (progress.estimated_time_remaining) {
            const timeRemaining = document.querySelector('.time-remaining');
            if (timeRemaining) {
                const minutes = Math.floor(progress.estimated_time_remaining / 60);
                const seconds = Math.floor(progress.estimated_time_remaining % 60);
                timeRemaining.textContent = `${minutes}:${seconds.toString().padStart(2, '0')} remaining`;
            }
        }
    }
}

// Global instance
window.UnifiedProgressTracker = UnifiedProgressTracker;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UnifiedProgressTracker;
}