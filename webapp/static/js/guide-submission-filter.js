/**
 * Guide-Submission Filter JavaScript
 * 
 * Handles dynamic loading of submissions based on selected guide
 */

class GuideSubmissionFilter {
    constructor() {
        this.guideSelect = null;
        this.submissionContainer = null;
        this.loadingIndicator = null;
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupEventListeners());
        } else {
            this.setupEventListeners();
        }
    }

    setupEventListeners() {
        // Find guide selection elements
        this.guideSelect = document.getElementById('guide_id') || 
                          document.querySelector('select[name="guide_id"]') ||
                          document.querySelector('.guide-selector');
        
        // Find submission container
        this.submissionContainer = document.getElementById('submissions-container') ||
                                 document.querySelector('.submissions-list') ||
                                 document.querySelector('#submission_id')?.parentElement;

        if (this.guideSelect) {
            this.guideSelect.addEventListener('change', (e) => {
                this.handleGuideChange(e.target.value);
            });

            // Load submissions for initially selected guide
            if (this.guideSelect.value) {
                this.handleGuideChange(this.guideSelect.value);
            }
        }
    }

    async handleGuideChange(guideId) {
        if (!guideId) {
            this.clearSubmissions();
            return;
        }

        this.showLoading();
        
        try {
            const submissions = await this.fetchSubmissions(guideId);
            this.updateSubmissions(submissions);
        } catch (error) {
            console.error('Error loading submissions:', error);
            this.showError('Failed to load submissions for selected guide');
        } finally {
            this.hideLoading();
        }
    }

    async fetchSubmissions(guideId) {
        const response = await fetch(`/processing/api/submissions?guide_id=${guideId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to fetch submissions');
        }

        return data.submissions || [];
    }

    updateSubmissions(submissions) {
        // Update submission select dropdown if it exists
        const submissionSelect = document.getElementById('submission_id') || 
                               document.querySelector('select[name="submission_id"]');
        
        if (submissionSelect) {
            this.updateSubmissionSelect(submissionSelect, submissions);
        }

        // Update submission list if it exists
        if (this.submissionContainer && !submissionSelect) {
            this.updateSubmissionList(submissions);
        }

        // Update submission count display
        this.updateSubmissionCount(submissions.length);

        // Trigger custom event for other components
        document.dispatchEvent(new CustomEvent('submissionsUpdated', {
            detail: { submissions, count: submissions.length }
        }));
    }

    updateSubmissionSelect(selectElement, submissions) {
        // Clear existing options except the first placeholder
        const placeholder = selectElement.querySelector('option[value=""]');
        selectElement.innerHTML = '';
        
        if (placeholder) {
            selectElement.appendChild(placeholder);
        } else {
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = submissions.length > 0 ? 
                'Select a submission...' : 'No submissions available for this guide';
            defaultOption.disabled = true;
            defaultOption.selected = true;
            selectElement.appendChild(defaultOption);
        }

        // Add submission options
        submissions.forEach(submission => {
            const option = document.createElement('option');
            option.value = submission.id;
            
            let displayText = submission.filename;
            if (submission.student_name) {
                displayText = `${submission.student_name} - ${submission.filename}`;
            }
            
            // Add status indicator
            if (submission.processing_status === 'completed') {
                displayText += ' ✓';
            } else if (submission.processing_status === 'failed') {
                displayText += ' ✗';
            } else if (submission.processing_status === 'processing') {
                displayText += ' ⏳';
            }
            
            option.textContent = displayText;
            option.title = `File: ${submission.filename}\nStatus: ${submission.processing_status}\nSize: ${this.formatFileSize(submission.file_size)}`;
            
            selectElement.appendChild(option);
        });

        // Enable/disable the select based on available submissions
        selectElement.disabled = submissions.length === 0;
    }

    updateSubmissionList(submissions) {
        if (!this.submissionContainer) return;

        this.submissionContainer.innerHTML = '';

        if (submissions.length === 0) {
            const emptyMessage = document.createElement('div');
            emptyMessage.className = 'text-center text-gray-500 py-8';
            emptyMessage.innerHTML = `
                <div class="text-4xl mb-4">📄</div>
                <p class="text-lg font-medium">No submissions found</p>
                <p class="text-sm">Upload submissions for this guide to see them here.</p>
            `;
            this.submissionContainer.appendChild(emptyMessage);
            return;
        }

        // Create submission cards
        submissions.forEach(submission => {
            const card = this.createSubmissionCard(submission);
            this.submissionContainer.appendChild(card);
        });
    }

    createSubmissionCard(submission) {
        const card = document.createElement('div');
        card.className = 'bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow';
        
        const statusColor = this.getStatusColor(submission.processing_status);
        const statusIcon = this.getStatusIcon(submission.processing_status);
        
        card.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <h3 class="font-medium text-gray-900">${this.escapeHtml(submission.filename)}</h3>
                    ${submission.student_name ? `<p class="text-sm text-gray-600 mt-1">Student: ${this.escapeHtml(submission.student_name)}</p>` : ''}
                    <div class="flex items-center mt-2 space-x-4">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColor}">
                            ${statusIcon} ${submission.processing_status}
                        </span>
                        <span class="text-xs text-gray-500">${this.formatFileSize(submission.file_size)}</span>
                        <span class="text-xs text-gray-500">${this.formatDate(submission.created_at)}</span>
                    </div>
                </div>
                <div class="ml-4">
                    <button class="text-blue-600 hover:text-blue-800 text-sm font-medium" 
                            onclick="selectSubmission('${submission.id}')">
                        Select
                    </button>
                </div>
            </div>
        `;
        
        return card;
    }

    updateSubmissionCount(count) {
        const countElements = document.querySelectorAll('.submission-count, [data-submission-count]');
        countElements.forEach(element => {
            element.textContent = count;
        });

        // Update any submission count messages
        const countMessages = document.querySelectorAll('.submission-count-message');
        countMessages.forEach(element => {
            element.textContent = count === 0 ? 
                'No submissions available for this guide' : 
                `${count} submission${count === 1 ? '' : 's'} available`;
        });
    }

    showLoading() {
        if (!this.loadingIndicator) {
            this.loadingIndicator = document.createElement('div');
            this.loadingIndicator.className = 'loading-indicator text-center py-4';
            this.loadingIndicator.innerHTML = `
                <div class="inline-flex items-center">
                    <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Loading submissions...
                </div>
            `;
        }

        if (this.submissionContainer) {
            this.submissionContainer.innerHTML = '';
            this.submissionContainer.appendChild(this.loadingIndicator);
        }
    }

    hideLoading() {
        if (this.loadingIndicator && this.loadingIndicator.parentNode) {
            this.loadingIndicator.parentNode.removeChild(this.loadingIndicator);
        }
    }

    clearSubmissions() {
        if (this.submissionContainer) {
            this.submissionContainer.innerHTML = `
                <div class="text-center text-gray-500 py-8">
                    <div class="text-4xl mb-4">📋</div>
                    <p class="text-lg font-medium">Select a guide</p>
                    <p class="text-sm">Choose a marking guide to see its submissions.</p>
                </div>
            `;
        }

        const submissionSelect = document.getElementById('submission_id');
        if (submissionSelect) {
            submissionSelect.innerHTML = `
                <option value="" disabled selected>Select a guide first...</option>
            `;
            submissionSelect.disabled = true;
        }

        this.updateSubmissionCount(0);
    }

    showError(message) {
        if (this.submissionContainer) {
            this.submissionContainer.innerHTML = `
                <div class="text-center text-red-500 py-8">
                    <div class="text-4xl mb-4">⚠️</div>
                    <p class="text-lg font-medium">Error</p>
                    <p class="text-sm">${this.escapeHtml(message)}</p>
                </div>
            `;
        }
    }

    // Utility methods
    getStatusColor(status) {
        switch (status) {
            case 'completed': return 'bg-green-100 text-green-800';
            case 'processing': return 'bg-yellow-100 text-yellow-800';
            case 'failed': return 'bg-red-100 text-red-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    }

    getStatusIcon(status) {
        switch (status) {
            case 'completed': return '✓';
            case 'processing': return '⏳';
            case 'failed': return '✗';
            default: return '○';
        }
    }

    formatFileSize(bytes) {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global function for submission selection (used by cards)
window.selectSubmission = function(submissionId) {
    const submissionSelect = document.getElementById('submission_id');
    if (submissionSelect) {
        submissionSelect.value = submissionId;
        submissionSelect.dispatchEvent(new Event('change'));
    }
    
    // Trigger custom event
    document.dispatchEvent(new CustomEvent('submissionSelected', {
        detail: { submissionId }
    }));
};

// Initialize when script loads
const guideSubmissionFilter = new GuideSubmissionFilter();

// Export for use in other scripts
window.GuideSubmissionFilter = GuideSubmissionFilter;