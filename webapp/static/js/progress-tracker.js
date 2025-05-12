/**
 * Progress Tracker
 * 
 * This module handles tracking and displaying progress for long-running operations
 * like LLM calls and OCR processing.
 */

class ProgressTracker {
    /**
     * Initialize the progress tracker
     * @param {Object} options - Configuration options
     * @param {string} options.containerId - ID of the container element for the progress bar
     * @param {number} options.pollInterval - Polling interval in milliseconds (default: 1000)
     * @param {Function} options.onComplete - Callback function when operation completes
     * @param {Function} options.onError - Callback function when operation fails
     */
    constructor(options = {}) {
        this.containerId = options.containerId || 'progress-container';
        this.pollInterval = options.pollInterval || 1000;
        this.onComplete = options.onComplete || function() {};
        this.onError = options.onError || function() {};
        
        this.trackerId = null;
        this.pollTimer = null;
        this.operationType = null;
        this.isActive = false;
    }
    
    /**
     * Start tracking progress for an operation
     * @param {string} trackerId - ID of the progress tracker
     * @param {string} operationType - Type of operation (llm, ocr)
     */
    startTracking(trackerId, operationType) {
        if (!trackerId) {
            console.error('No tracker ID provided');
            return;
        }
        
        this.trackerId = trackerId;
        this.operationType = operationType;
        this.isActive = true;
        
        // Create or show the progress container
        this._createProgressUI();
        
        // Start polling for updates
        this._startPolling();
        
        console.log(`Started tracking progress for ${operationType} operation: ${trackerId}`);
    }
    
    /**
     * Stop tracking progress
     */
    stopTracking() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
        
        this.isActive = false;
        this.trackerId = null;
        
        // Hide the progress container
        const container = document.getElementById(this.containerId);
        if (container) {
            container.style.display = 'none';
        }
        
        console.log('Stopped progress tracking');
    }
    
    /**
     * Create or update the progress UI
     * @private
     */
    _createProgressUI() {
        let container = document.getElementById(this.containerId);
        
        // If container doesn't exist, create it
        if (!container) {
            container = document.createElement('div');
            container.id = this.containerId;
            container.className = 'progress-container';
            
            // Create the progress UI structure
            container.innerHTML = `
                <div class="progress-card">
                    <div class="progress-header">
                        <h5 class="progress-title">Processing...</h5>
                        <button type="button" class="btn-close progress-close" aria-label="Close"></button>
                    </div>
                    <div class="progress-body">
                        <div class="progress">
                            <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                 role="progressbar" style="width: 0%" 
                                 aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
                        </div>
                        <p class="progress-message mt-2">Starting operation...</p>
                        <p class="progress-details text-muted small"></p>
                    </div>
                </div>
            `;
            
            // Add to document body
            document.body.appendChild(container);
            
            // Add event listener for close button
            const closeBtn = container.querySelector('.progress-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.stopTracking());
            }
        }
        
        // Show the container
        container.style.display = 'flex';
        
        // Set initial title based on operation type
        const titleElement = container.querySelector('.progress-title');
        if (titleElement) {
            titleElement.textContent = this.operationType === 'llm' 
                ? 'Processing with AI...' 
                : this.operationType === 'ocr' 
                    ? 'Extracting Text from Image...' 
                    : 'Processing...';
        }
    }
    
    /**
     * Start polling for progress updates
     * @private
     */
    _startPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
        }
        
        // Immediately fetch the first update
        this._fetchProgress();
        
        // Then start polling at regular intervals
        this.pollTimer = setInterval(() => {
            if (this.isActive) {
                this._fetchProgress();
            } else {
                clearInterval(this.pollTimer);
                this.pollTimer = null;
            }
        }, this.pollInterval);
    }
    
    /**
     * Fetch progress from the API
     * @private
     */
    _fetchProgress() {
        if (!this.trackerId || !this.isActive) return;
        
        fetch(`/api/progress/${this.trackerId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this._updateProgressUI(data);
                
                // If operation is complete, stop polling
                if (data.completed) {
                    if (data.success) {
                        console.log('Operation completed successfully');
                        setTimeout(() => {
                            this.stopTracking();
                            this.onComplete(data);
                        }, 1500); // Show 100% for a moment before hiding
                    } else {
                        console.error('Operation failed:', data.error);
                        this.onError(data);
                        // Keep the error visible, don't auto-hide
                    }
                }
            })
            .catch(error => {
                console.error('Error fetching progress:', error);
                // Don't stop tracking on fetch error, might be temporary
            });
    }
    
    /**
     * Update the progress UI with the latest data
     * @param {Object} data - Progress data from the API
     * @private
     */
    _updateProgressUI(data) {
        const container = document.getElementById(this.containerId);
        if (!container) return;
        
        // Update progress bar
        const progressBar = container.querySelector('.progress-bar');
        if (progressBar) {
            const percent = data.percent_complete || 0;
            progressBar.style.width = `${percent}%`;
            progressBar.setAttribute('aria-valuenow', percent);
            progressBar.textContent = `${percent}%`;
            
            // Update progress bar color based on status
            progressBar.classList.remove('bg-success', 'bg-danger', 'bg-warning');
            if (data.completed) {
                if (data.success) {
                    progressBar.classList.add('bg-success');
                } else {
                    progressBar.classList.add('bg-danger');
                }
            } else if (data.status === 'processing') {
                progressBar.classList.add('bg-warning');
            }
        }
        
        // Update message
        const messageElement = container.querySelector('.progress-message');
        if (messageElement) {
            messageElement.textContent = data.message || 'Processing...';
        }
        
        // Update details
        const detailsElement = container.querySelector('.progress-details');
        if (detailsElement) {
            let details = '';
            
            if (data.start_time) {
                const startTime = new Date(data.start_time * 1000);
                details += `Started: ${startTime.toLocaleTimeString()} | `;
            }
            
            if (data.current_step && data.total_steps) {
                details += `Step ${data.current_step}/${data.total_steps} | `;
            }
            
            if (data.status) {
                details += `Status: ${data.status.charAt(0).toUpperCase() + data.status.slice(1)}`;
            }
            
            detailsElement.textContent = details;
        }
        
        // Update title based on completion status
        const titleElement = container.querySelector('.progress-title');
        if (titleElement && data.completed) {
            if (data.success) {
                titleElement.textContent = 'Completed Successfully';
            } else {
                titleElement.textContent = 'Operation Failed';
            }
        }
    }
}

// Create a global instance
const progressTracker = new ProgressTracker({
    onComplete: (data) => {
        // Reload the page if needed or show success message
        if (data.result && data.result.reload) {
            window.location.reload();
        }
    },
    onError: (data) => {
        // Show error message
        const errorMessage = data.error || 'An unknown error occurred';
        alert(`Operation failed: ${errorMessage}`);
    }
});

// Export for global use
window.progressTracker = progressTracker;
