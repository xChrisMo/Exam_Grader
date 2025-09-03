/**
 * Training Sessions Management JavaScript
 * 
 * Handles session listing, filtering, management actions,
 * and real-time updates for training sessions.
 */

class TrainingSessionsManager {
    constructor() {
        this.sessions = [];
        this.filteredSessions = [];
        this.currentSessionToDelete = null;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadSessions();
        this.startProgressPolling();
    }
    
    bindEvents() {
        // Filter and search controls
        const searchInput = document.getElementById('search-sessions');
        const statusFilter = document.getElementById('filter-status');
        const sortSelect = document.getElementById('sort-by');
        const applyFiltersBtn = document.getElementById('apply-filters');
        
        if (searchInput) {
            searchInput.addEventListener('input', () => this.debounce(() => this.applyFilters(), 300));
        }
        
        if (statusFilter) {
            statusFilter.addEventListener('change', () => this.applyFilters());
        }
        
        if (sortSelect) {
            sortSelect.addEventListener('change', () => this.applyFilters());
        }
        
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => this.applyFilters());
        }
        
        // Delete modal events
        const deleteModal = document.getElementById('delete-modal');
        const confirmDeleteBtn = document.getElementById('confirm-delete');
        const cancelDeleteBtn = document.getElementById('cancel-delete');
        
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', () => this.confirmDelete());
        }
        
        if (cancelDeleteBtn) {
            cancelDeleteBtn.addEventListener('click', () => this.cancelDelete());
        }
        
        // Close modal when clicking outside
        if (deleteModal) {
            deleteModal.addEventListener('click', (e) => {
                if (e.target === deleteModal) {
                    this.cancelDelete();
                }
            });
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.cancelDelete();
            }
        });
    }
    
    async loadSessions() {
        try {
            const response = await fetch('/training/sessions', {
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.sessions = data.sessions || [];
                this.applyFilters();
            } else {
                this.showError('Failed to load training sessions');
            }
        } catch (error) {
            this.showError('Failed to load training sessions');
        }
    }
    
    applyFilters() {
        const searchTerm = document.getElementById('search-sessions')?.value.toLowerCase() || '';
        const statusFilter = document.getElementById('filter-status')?.value || '';
        const sortBy = document.getElementById('sort-by')?.value || 'created_at_desc';
        
        // Filter sessions
        this.filteredSessions = this.sessions.filter(session => {
            const matchesSearch = !searchTerm || 
                session.name.toLowerCase().includes(searchTerm) ||
                session.description?.toLowerCase().includes(searchTerm);
            
            const matchesStatus = !statusFilter || session.status === statusFilter;
            
            return matchesSearch && matchesStatus;
        });
        
        // Sort sessions
        this.filteredSessions.sort((a, b) => {
            switch (sortBy) {
                case 'created_at_asc':
                    return new Date(a.created_at) - new Date(b.created_at);
                case 'created_at_desc':
                    return new Date(b.created_at) - new Date(a.created_at);
                case 'name_asc':
                    return a.name.localeCompare(b.name);
                case 'name_desc':
                    return b.name.localeCompare(a.name);
                default:
                    return new Date(b.created_at) - new Date(a.created_at);
            }
        });
        
        this.renderSessions();
    }
    
    renderSessions() {
        const container = document.getElementById('sessions-container');
        if (!container) return;
        
        if (this.filteredSessions.length === 0) {
            container.innerHTML = this.getEmptyStateHTML();
            return;
        }
        
        container.innerHTML = this.filteredSessions.map(session => 
            this.getSessionCardHTML(session)
        ).join('');
    }
    
    getSessionCardHTML(session) {
        const statusBadge = this.getStatusBadgeHTML(session.status);
        const progressBar = session.status === 'in_progress' ? this.getProgressBarHTML(session) : '';
        const actionButtons = this.getActionButtonsHTML(session);
        
        return `
            <div class="session-card bg-white overflow-hidden shadow rounded-lg" data-session-id="${session.id}">
                <div class="p-6">
                    <!-- Session Header -->
                    <div class="flex items-center justify-between mb-4">
                        <div class="flex-1 min-w-0">
                            <h3 class="text-lg font-medium text-gray-900 truncate">${session.name}</h3>
                            <p class="text-sm text-gray-500">${this.formatDate(session.created_at)}</p>
                        </div>
                        <div class="flex-shrink-0 ml-4">
                            ${statusBadge}
                        </div>
                    </div>

                    ${progressBar}

                    <!-- Session Metrics -->
                    <div class="grid grid-cols-2 gap-4 mb-4">
                        <div class="text-center">
                            <div class="text-2xl font-bold text-gray-900">${session.total_guides || 0}</div>
                            <div class="text-xs text-gray-500">Guides</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-gray-900">${session.total_questions || 0}</div>
                            <div class="text-xs text-gray-500">Questions</div>
                        </div>
                    </div>

                    ${session.average_confidence ? this.getConfidenceBarHTML(session.average_confidence) : ''}

                    <!-- Action Buttons -->
                    <div class="flex space-x-2">
                        ${actionButtons}
                    </div>

                    <!-- Delete Button -->
                    <div class="mt-3 pt-3 border-t border-gray-200">
                        <button type="button" class="w-full text-red-600 hover:text-red-800 text-xs font-medium py-1 focus:outline-none"
                                onclick="trainingSessionsManager.deleteSession('${session.id}', '${session.name}')">
                            Delete Session
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    getStatusBadgeHTML(status) {
        const statusConfig = {
            completed: { color: 'green', text: 'Completed', icon: true },
            in_progress: { color: 'blue', text: 'In Progress', icon: true, animated: true },
            failed: { color: 'red', text: 'Failed', icon: true },
            created: { color: 'gray', text: 'Created', icon: true }
        };
        
        const config = statusConfig[status] || statusConfig.created;
        const animationClass = config.animated ? 'status-indicator' : '';
        
        return `
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-${config.color}-100 text-${config.color}-800">
                <svg class="-ml-0.5 mr-1.5 h-2 w-2 text-${config.color}-400 ${animationClass}" fill="currentColor" viewBox="0 0 8 8">
                    <circle cx="4" cy="4" r="3"/>
                </svg>
                ${config.text}
            </span>
        `;
    }
    
    getProgressBarHTML(session) {
        const progress = session.progress_percentage || 0;
        const currentStep = session.current_step || 'Processing...';
        
        return `
            <div class="mb-4">
                <div class="flex justify-between text-sm font-medium text-gray-900 mb-2">
                    <span>${currentStep}</span>
                    <span>${progress}%</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                    <div class="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                         style="width: ${progress}%"></div>
                </div>
            </div>
        `;
    }
    
    getConfidenceBarHTML(confidence) {
        const percentage = Math.round(confidence * 100);
        let colorClass = 'bg-red-500';
        if (confidence >= 0.8) colorClass = 'bg-green-500';
        else if (confidence >= 0.6) colorClass = 'bg-yellow-500';
        
        return `
            <div class="mb-4">
                <div class="flex justify-between text-sm font-medium text-gray-700 mb-1">
                    <span>Average Confidence</span>
                    <span>${percentage}%</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                    <div class="h-2 rounded-full transition-all duration-300 ${colorClass}" 
                         style="width: ${percentage}%"></div>
                </div>
            </div>
        `;
    }
    
    getActionButtonsHTML(session) {
        switch (session.status) {
            case 'completed':
                return `
                    <button type="button" class="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium py-2 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                            onclick="trainingSessionsManager.viewReport('${session.id}')">
                        View Report
                    </button>
                    ${session.is_active ? 
                        '<button type="button" class="flex-1 bg-gray-400 text-white text-xs font-medium py-2 px-3 rounded-md cursor-not-allowed" disabled>Active Model</button>' :
                        `<button type="button" class="flex-1 bg-green-600 hover:bg-green-700 text-white text-xs font-medium py-2 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                                onclick="trainingSessionsManager.setActiveModel('${session.id}')">Set Active</button>`
                    }
                `;
            case 'in_progress':
                return `
                    <button type="button" class="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium py-2 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                            onclick="trainingSessionsManager.viewProgress('${session.id}')">
                        View Progress
                    </button>
                    <button type="button" class="flex-1 bg-red-600 hover:bg-red-700 text-white text-xs font-medium py-2 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                            onclick="trainingSessionsManager.stopTraining('${session.id}')">
                        Stop
                    </button>
                `;
            case 'failed':
                return `
                    <button type="button" class="flex-1 bg-yellow-600 hover:bg-yellow-700 text-white text-xs font-medium py-2 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500"
                            onclick="trainingSessionsManager.retryTraining('${session.id}')">
                        Retry
                    </button>
                    <button type="button" class="flex-1 bg-gray-600 hover:bg-gray-700 text-white text-xs font-medium py-2 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                            onclick="trainingSessionsManager.viewLogs('${session.id}')">
                        View Logs
                    </button>
                `;
            default:
                return `
                    <button type="button" class="flex-1 bg-green-600 hover:bg-green-700 text-white text-xs font-medium py-2 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                            onclick="trainingSessionsManager.startTraining('${session.id}')">
                        Start Training
                    </button>
                    <button type="button" class="flex-1 bg-gray-600 hover:bg-gray-700 text-white text-xs font-medium py-2 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                            onclick="trainingSessionsManager.editSession('${session.id}')">
                        Edit
                    </button>
                `;
        }
    }
    
    getEmptyStateHTML() {
        return `
            <div class="col-span-full">
                <div class="text-center py-12">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                    </svg>
                    <h3 class="mt-2 text-sm font-medium text-gray-900">No training sessions found</h3>
                    <p class="mt-1 text-sm text-gray-500">Try adjusting your filters or create a new training session.</p>
                    <div class="mt-6">
                        <a href="/training/" 
                           class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                            <svg class="-ml-1 mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                            </svg>
                            New Training Session
                        </a>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Action Methods
    async viewReport(sessionId) {
        try {
            const response = await fetch(`/training/session/${sessionId}/report`);
            if (response.ok) {
                const data = await response.json();
                window.open(data.report_url, '_blank');
            } else {
                this.showError('Failed to load report');
            }
        } catch (error) {
            this.showError('Failed to load report');
        }
    }
    
    async setActiveModel(sessionId) {
        try {
            const response = await fetch(`/training/session/${sessionId}/set-active`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                this.showSuccess('Model set as active successfully');
                this.loadSessions(); // Refresh the list
            } else {
                const errorData = await response.json();
                this.showError(errorData.error || 'Failed to set active model');
            }
        } catch (error) {
            this.showError('Failed to set active model');
        }
    }
    
    viewProgress(sessionId) {
        // Navigate to progress view or open modal
        window.location.href = `/training/session/${sessionId}/progress`;
    }
    
    async stopTraining(sessionId) {
        if (!confirm('Are you sure you want to stop this training session?')) {
            return;
        }
        
        try {
            const response = await fetch(`/training/session/${sessionId}/stop`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                this.showSuccess('Training stopped successfully');
                this.loadSessions();
            } else {
                const errorData = await response.json();
                this.showError(errorData.error || 'Failed to stop training');
            }
        } catch (error) {
            this.showError('Failed to stop training');
        }
    }
    
    async retryTraining(sessionId) {
        try {
            const response = await fetch(`/training/session/${sessionId}/retry`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                this.showSuccess('Training restarted successfully');
                this.loadSessions();
            } else {
                const errorData = await response.json();
                this.showError(errorData.error || 'Failed to retry training');
            }
        } catch (error) {
            this.showError('Failed to retry training');
        }
    }
    
    viewLogs(sessionId) {
        // Navigate to logs view or open modal
        window.location.href = `/training/session/${sessionId}/logs`;
    }
    
    async startTraining(sessionId) {
        try {
            const response = await fetch('/training/start-training', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ session_id: sessionId })
            });
            
            if (response.ok) {
                this.showSuccess('Training started successfully');
                this.loadSessions();
            } else {
                const errorData = await response.json();
                this.showError(errorData.error || 'Failed to start training');
            }
        } catch (error) {
            this.showError('Failed to start training');
        }
    }
    
    editSession(sessionId) {
        // Navigate to edit view
        window.location.href = `/training/session/${sessionId}/edit`;
    }
    
    deleteSession(sessionId, sessionName) {
        this.currentSessionToDelete = sessionId;
        const modal = document.getElementById('delete-modal');
        const nameSpan = document.getElementById('delete-session-name');
        
        if (nameSpan) {
            nameSpan.textContent = sessionName;
        }
        
        if (modal) {
            modal.classList.remove('hidden');
        }
    }
    
    async confirmDelete() {
        if (!this.currentSessionToDelete) return;
        
        try {
            const response = await fetch(`/training/session/${this.currentSessionToDelete}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                this.showSuccess('Training session deleted successfully');
                this.loadSessions();
            } else {
                const errorData = await response.json();
                this.showError(errorData.error || 'Failed to delete session');
            }
        } catch (error) {
            this.showError('Failed to delete session');
        }
        
        this.cancelDelete();
    }
    
    cancelDelete() {
        this.currentSessionToDelete = null;
        const modal = document.getElementById('delete-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }
    
    // Progress polling for in-progress sessions
    startProgressPolling() {
        setInterval(() => {
            const inProgressSessions = this.sessions.filter(s => s.status === 'in_progress');
            if (inProgressSessions.length > 0) {
                this.updateProgressForSessions(inProgressSessions);
            }
        }, 5000); // Poll every 5 seconds
    }
    
    async updateProgressForSessions(sessions) {
        for (const session of sessions) {
            try {
                const response = await fetch(`/training/progress/${session.id}`);
                if (response.ok) {
                    const progress = await response.json();
                    
                    // Update session in memory
                    const sessionIndex = this.sessions.findIndex(s => s.id === session.id);
                    if (sessionIndex !== -1) {
                        this.sessions[sessionIndex] = { ...this.sessions[sessionIndex], ...progress };
                    }
                    
                    // Update UI for this specific session
                    this.updateSessionCard(session.id, progress);
                }
            } catch (error) {
                // Error updating progress for session
            }
        }
    }
    
    updateSessionCard(sessionId, progress) {
        const sessionCard = document.querySelector(`[data-session-id="${sessionId}"]`);
        if (!sessionCard) return;
        
        // Update progress bar
        const progressBar = sessionCard.querySelector('.bg-blue-600');
        const progressText = sessionCard.querySelector('.text-sm.font-medium.text-gray-900 span:last-child');
        const stepText = sessionCard.querySelector('.text-sm.font-medium.text-gray-900 span:first-child');
        
        if (progressBar) {
            progressBar.style.width = `${progress.percentage || 0}%`;
        }
        
        if (progressText) {
            progressText.textContent = `${Math.round(progress.percentage || 0)}%`;
        }
        
        if (stepText) {
            stepText.textContent = progress.current_step || 'Processing...';
        }
        
        // If status changed, reload the entire list
        if (progress.status !== 'in_progress') {
            this.loadSessions();
        }
    }
    
    // Utility Methods
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
    
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 max-w-sm p-4 rounded-lg shadow-lg ${
            type === 'error' ? 'bg-red-50 border border-red-200 text-red-800' :
            type === 'success' ? 'bg-green-50 border border-green-200 text-green-800' :
            'bg-blue-50 border border-blue-200 text-blue-800'
        }`;
        
        notification.innerHTML = `
            <div class="flex items-center">
                <div class="flex-shrink-0">
                    ${type === 'error' ? 
                        '<svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>' :
                        type === 'success' ?
                        '<svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>' :
                        '<svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>'
                    }
                </div>
                <div class="ml-3 flex-1">
                    <p class="text-sm font-medium">${message}</p>
                </div>
                <div class="ml-auto pl-3">
                    <button type="button" class="notification-close inline-flex rounded-md p-1.5 hover:bg-gray-100 focus:outline-none">
                        <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
        
        // Add close functionality
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
}

// Global instance for template onclick handlers
let trainingSessionsManager;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    trainingSessionsManager = new TrainingSessionsManager();
});