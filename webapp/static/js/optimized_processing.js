/**
 * Optimized Processing Frontend Module
 * Handles real-time progress tracking and WebSocket communication for enhanced AI processing
 */

class OptimizedProcessingManager {
    constructor() {
        this.socket = null;
        this.currentTaskId = null;
        this.progressCallback = null;
        this.completionCallback = null;
        this.errorCallback = null;
        this.isConnected = false;
        
        this.initializeWebSocket();
        this.bindEventHandlers();
    }
    
    /**
     * Initialize WebSocket connection for real-time updates
     */
    initializeWebSocket() {
        try {
            this.socket = io();
            
            this.socket.on('connect', () => {
                console.log('WebSocket connected for optimized processing');
                this.isConnected = true;
                this.updateConnectionStatus(true);
            });
            
            this.socket.on('disconnect', () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.updateConnectionStatus(false);
            });
            
            this.socket.on('processing_progress', (data) => {
                this.handleProgressUpdate(data);
            });
            
            this.socket.on('task_completed', (data) => {
                this.handleTaskCompletion(data);
            });
            
            this.socket.on('task_error', (data) => {
                this.handleTaskError(data);
            });
            
        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
            this.isConnected = false;
        }
    }
    
    /**
     * Bind event handlers for UI elements
     */
    bindEventHandlers() {
        // Process submissions button
        $(document).on('click', '.btn-process-optimized', (e) => {
            e.preventDefault();
            this.startOptimizedProcessing();
        });
        
        // Cancel processing button
        $(document).on('click', '.btn-cancel-processing', (e) => {
            e.preventDefault();
            this.cancelProcessing();
        });
        
        // View results button
        $(document).on('click', '.btn-view-results', (e) => {
            e.preventDefault();
            const taskId = $(e.target).data('task-id');
            this.viewResults(taskId);
        });
        
        // Performance stats button
        $(document).on('click', '.btn-performance-stats', (e) => {
            e.preventDefault();
            this.showPerformanceStats();
        });
    }
    
    /**
     * Start optimized processing workflow
     */
    async startOptimizedProcessing() {
        try {
            // Get selected submissions
            const selectedSubmissions = this.getSelectedSubmissions();
            if (selectedSubmissions.length === 0) {
                this.showError('Please select at least one submission to process.');
                return;
            }
            
            // Show processing UI
            this.showProcessingUI();
            
            // Start processing
            const response = await fetch('/api/optimized/process-submissions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    submission_ids: selectedSubmissions,
                    batch_processing: selectedSubmissions.length > 5,
                    batch_size: 5
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.currentTaskId = result.task_id;
                this.joinTaskRoom(result.task_id);
                this.updateProcessingStatus('started', {
                    taskId: result.task_id,
                    message: result.message,
                    estimatedTime: result.estimated_time
                });
            } else {
                this.showError(result.error || 'Failed to start processing');
                this.hideProcessingUI();
            }
            
        } catch (error) {
            console.error('Failed to start optimized processing:', error);
            this.showError('Failed to start processing. Please try again.');
            this.hideProcessingUI();
        }
    }
    
    /**
     * Cancel current processing task
     */
    async cancelProcessing() {
        if (!this.currentTaskId) {
            return;
        }
        
        try {
            const response = await fetch(`/api/optimized/cancel-task/${this.currentTaskId}`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.updateProcessingStatus('cancelled', {
                    message: 'Processing cancelled by user'
                });
                this.leaveTaskRoom(this.currentTaskId);
                this.currentTaskId = null;
                this.hideProcessingUI();
            } else {
                this.showError(result.error || 'Failed to cancel processing');
            }
            
        } catch (error) {
            console.error('Failed to cancel processing:', error);
            this.showError('Failed to cancel processing.');
        }
    }
    
    /**
     * View processing results
     */
    async viewResults(taskId) {
        try {
            const response = await fetch(`/api/optimized/results/${taskId}`);
            const result = await response.json();
            
            if (result.success) {
                this.displayResults(result);
            } else {
                this.showError(result.error || 'Failed to load results');
            }
            
        } catch (error) {
            console.error('Failed to load results:', error);
            this.showError('Failed to load results.');
        }
    }
    
    /**
     * Show performance statistics
     */
    async showPerformanceStats() {
        try {
            const response = await fetch('/api/optimized/performance-stats');
            const result = await response.json();
            
            if (result.success) {
                this.displayPerformanceStats(result.stats);
            } else {
                this.showError(result.error || 'Failed to load performance stats');
            }
            
        } catch (error) {
            console.error('Failed to load performance stats:', error);
            this.showError('Failed to load performance stats.');
        }
    }
    
    /**
     * Handle progress updates from WebSocket
     */
    handleProgressUpdate(data) {
        if (data.task_id === this.currentTaskId) {
            this.updateProgressBar(data.progress);
            this.updateProgressDetails(data);
            
            if (this.progressCallback) {
                this.progressCallback(data);
            }
        }
    }
    
    /**
     * Handle task completion
     */
    handleTaskCompletion(data) {
        if (data.task_id === this.currentTaskId) {
            this.updateProcessingStatus('completed', data);
            this.leaveTaskRoom(this.currentTaskId);
            
            if (this.completionCallback) {
                this.completionCallback(data);
            }
            
            // Auto-load results after a short delay
            setTimeout(() => {
                this.viewResults(this.currentTaskId);
            }, 1000);
        }
    }
    
    /**
     * Handle task errors
     */
    handleTaskError(data) {
        if (data.task_id === this.currentTaskId) {
            this.updateProcessingStatus('error', data);
            this.leaveTaskRoom(this.currentTaskId);
            
            if (this.errorCallback) {
                this.errorCallback(data);
            }
        }
    }
    
    /**
     * Join WebSocket room for task updates
     */
    joinTaskRoom(taskId) {
        if (this.socket && this.isConnected) {
            this.socket.emit('join_task_room', { task_id: taskId });
        }
    }
    
    /**
     * Leave WebSocket room
     */
    leaveTaskRoom(taskId) {
        if (this.socket && this.isConnected) {
            this.socket.emit('leave_task_room', { task_id: taskId });
        }
    }
    
    /**
     * Update connection status indicator
     */
    updateConnectionStatus(connected) {
        const indicator = $('.connection-status');
        if (connected) {
            indicator.removeClass('disconnected').addClass('connected')
                     .html('<i class="fas fa-circle text-success"></i> Connected');
        } else {
            indicator.removeClass('connected').addClass('disconnected')
                     .html('<i class="fas fa-circle text-danger"></i> Disconnected');
        }
    }
    
    /**
     * Show processing UI elements
     */
    showProcessingUI() {
        $('.processing-container').show();
        $('.btn-process-optimized').prop('disabled', true);
        $('.progress-container').show();
        this.updateProgressBar(0);
    }
    
    /**
     * Hide processing UI elements
     */
    hideProcessingUI() {
        $('.processing-container').hide();
        $('.btn-process-optimized').prop('disabled', false);
        $('.progress-container').hide();
    }
    
    /**
     * Update progress bar
     */
    updateProgressBar(progress) {
        const progressBar = $('.progress-bar');
        progressBar.css('width', `${progress}%`)
                   .attr('aria-valuenow', progress)
                   .text(`${Math.round(progress)}%`);
        
        // Update color based on progress
        progressBar.removeClass('bg-info bg-warning bg-success')
                   .addClass(progress < 30 ? 'bg-info' : progress < 80 ? 'bg-warning' : 'bg-success');
    }
    
    /**
     * Update progress details
     */
    updateProgressDetails(data) {
        $('.progress-stage').text(data.stage || 'Processing');
        $('.progress-message').text(data.message || '');
        $('.progress-submission').text(`${data.current_submission}/${data.total_submissions}`);
        $('.progress-elapsed').text(`${data.elapsed_time}s`);
        
        if (data.errors_count > 0) {
            $('.progress-errors').text(`${data.errors_count} errors`).show();
        }
        
        if (data.warnings_count > 0) {
            $('.progress-warnings').text(`${data.warnings_count} warnings`).show();
        }
    }
    
    /**
     * Update processing status
     */
    updateProcessingStatus(status, data) {
        const statusElement = $('.processing-status');
        
        switch (status) {
            case 'started':
                statusElement.html(`<i class="fas fa-spinner fa-spin"></i> Processing started...`);
                break;
            case 'completed':
                statusElement.html(`<i class="fas fa-check-circle text-success"></i> Processing completed!`);
                this.hideProcessingUI();
                break;
            case 'cancelled':
                statusElement.html(`<i class="fas fa-times-circle text-warning"></i> Processing cancelled`);
                break;
            case 'error':
                statusElement.html(`<i class="fas fa-exclamation-circle text-danger"></i> Processing failed`);
                this.hideProcessingUI();
                break;
        }
    }
    
    /**
     * Display processing results
     */
    displayResults(results) {
        const resultsContainer = $('.results-container');
        
        let html = `
            <div class="card">
                <div class="card-header">
                    <h5><i class="fas fa-chart-bar"></i> Processing Results</h5>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-3">
                            <div class="stat-card">
                                <h6>Total Submissions</h6>
                                <span class="stat-value">${results.total_submissions}</span>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <h6>Successfully Graded</h6>
                                <span class="stat-value text-success">${results.successful_count}</span>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <h6>Failed</h6>
                                <span class="stat-value text-danger">${results.failed_count}</span>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <h6>Processing Time</h6>
                                <span class="stat-value">${results.processing_time}s</span>
                            </div>
                        </div>
                    </div>
        `;
        
        if (results.grading_results && results.grading_results.length > 0) {
            html += `
                <h6>Individual Results:</h6>
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Submission ID</th>
                                <th>Score</th>
                                <th>Percentage</th>
                                <th>Letter Grade</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            results.grading_results.forEach(result => {
                html += `
                    <tr>
                        <td>${result.submission_id}</td>
                        <td>${result.total_score}/${result.max_possible_score}</td>
                        <td>${result.percentage}%</td>
                        <td><span class="badge badge-${this.getGradeBadgeClass(result.letter_grade)}">${result.letter_grade}</span></td>
                        <td>
                            <button class="btn btn-sm btn-outline-primary" onclick="viewDetailedFeedback(${result.submission_id})">
                                <i class="fas fa-eye"></i> View Details
                            </button>
                        </td>
                    </tr>
                `;
            });
            
            html += `
                        </tbody>
                    </table>
                </div>
            `;
        }
        
        html += `
                </div>
            </div>
        `;
        
        resultsContainer.html(html).show();
    }
    
    /**
     * Display performance statistics
     */
    displayPerformanceStats(stats) {
        const modal = $('#performanceStatsModal');
        
        let html = `
            <div class="row">
                <div class="col-md-6">
                    <h6><i class="fas fa-memory"></i> OCR Cache</h6>
                    <ul class="list-unstyled">
                        <li>Cache Enabled: ${stats.ocr_cache.cache_enabled ? 'Yes' : 'No'}</li>
                        <li>Total Keys: ${stats.ocr_cache.total_keys || 'N/A'}</li>
                        <li>Memory Usage: ${stats.ocr_cache.memory_usage || 'N/A'}</li>
                    </ul>
                </div>
                <div class="col-md-6">
                    <h6><i class="fas fa-cogs"></i> System Info</h6>
                    <ul class="list-unstyled">
                        <li>Max Workers: ${stats.system_info.max_workers}</li>
                        <li>Batch Size: ${stats.grading_config.max_batch_size}</li>
                        <li>LLM Available: ${stats.grading_config.llm_available ? 'Yes' : 'No'}</li>
                    </ul>
                </div>
            </div>
        `;
        
        if (stats.recent_tasks) {
            html += `
                <hr>
                <h6><i class="fas fa-chart-line"></i> Recent Performance (24h)</h6>
                <div class="row">
                    <div class="col-md-4">
                        <div class="stat-card">
                            <span class="stat-label">Total Processed</span>
                            <span class="stat-value">${stats.recent_tasks.total_processed}</span>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="stat-card">
                            <span class="stat-label">Average Score</span>
                            <span class="stat-value">${stats.recent_tasks.average_score}%</span>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="stat-card">
                            <span class="stat-label">Processing Time</span>
                            <span class="stat-value">${stats.recent_tasks.processing_time_avg || 'N/A'}s</span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        modal.find('.modal-body').html(html);
        modal.modal('show');
    }
    
    /**
     * Get selected submission IDs
     */
    getSelectedSubmissions() {
        const selected = [];
        $('.submission-checkbox:checked').each(function() {
            selected.push(parseInt($(this).val()));
        });
        return selected;
    }
    
    /**
     * Get marking guide ID
     */
    getMarkingGuideId() {
        return parseInt($('#marking-guide-select').val()) || null;
    }
    
    /**
     * Get badge class for letter grade
     */
    getGradeBadgeClass(grade) {
        const gradeClasses = {
            'A': 'success',
            'B': 'primary',
            'C': 'warning',
            'D': 'secondary',
            'F': 'danger'
        };
        return gradeClasses[grade] || 'secondary';
    }
    
    /**
     * Show error message
     */
    showError(message) {
        const alert = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="fas fa-exclamation-triangle"></i> ${message}
                <button type="button" class="close" data-dismiss="alert">
                    <span>&times;</span>
                </button>
            </div>
        `;
        $('.alerts-container').html(alert);
    }
    
    /**
     * Set callback functions
     */
    setCallbacks(progressCallback, completionCallback, errorCallback) {
        this.progressCallback = progressCallback;
        this.completionCallback = completionCallback;
        this.errorCallback = errorCallback;
    }
}

// Initialize the optimized processing manager
const optimizedProcessing = new OptimizedProcessingManager();

// Global functions for backward compatibility
function startOptimizedProcessing() {
    optimizedProcessing.startOptimizedProcessing();
}

function cancelProcessing() {
    optimizedProcessing.cancelProcessing();
}

function viewDetailedFeedback(submissionId) {
    // Implementation for viewing detailed feedback
    window.location.href = `/submission/${submissionId}/feedback`;
}

function showPerformanceStats() {
    optimizedProcessing.showPerformanceStats();
}