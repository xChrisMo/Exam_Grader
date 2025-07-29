/**
 * Enhanced Document Management Interface v2
 * Fixed implementation based on existing patterns and requirements
 */

class EnhancedDocumentManagerV2 {
    constructor(options = {}) {
        this.options = {
            container: '#document-management-section',
            uploadUrl: '/api/llm-training/upload-documents',
            documentsUrl: '/api/llm-training/documents',
            validateUrl: '/api/llm-training/validate-document',
            retryUrl: '/api/llm-training/retry-processing',
            maxRetries: 3,
            autoRefresh: true,
            refreshInterval: 5000,
            ...options
        };

        this.documents = new Map();
        this.filters = {
            status: 'all',
            dataset: 'all',
            search: '',
            sortBy: 'created_at',
            sortOrder: 'desc'
        };
        
        this.init();
    }

    init() {
        this.setupContainer();
        this.setupEventListeners();
        this.loadDocuments();
        
        if (this.options.autoRefresh) {
            this.startAutoRefresh();
        }
    }

    setupContainer() {
        this.container = document.querySelector(this.options.container);
        if (!this.container) {
            console.error('Document manager container not found');
            return;
        }

        this.container.innerHTML = `
        <div class="document-manager">
            <div class="document-header">
                <div class="header-left">
                    <h3 class="section-title">Document Management</h3>
                </div>
                <div class="header-actions">
                    <button class="btn btn-secondary" id="refresh-docs-btn">Refresh</button>
                    <button class="btn btn-primary" id="upload-docs-btn">Upload Documents</button>
                </div>
            </div>
            <div id="document-grid"></div>
            <div id="loading-state" style="display: none;">Loading...</div>
            <div id="empty-state" style="display: none;">No documents found.</div>
        </div>`;

        this.documentGrid = this.container.querySelector('#document-grid');
        this.loadingState = this.container.querySelector('#loading-state');
        this.emptyState = this.container.querySelector('#empty-state');
    }

    setupEventListeners() {
        const refreshBtn = this.container.querySelector('#refresh-docs-btn');
        const uploadBtn = this.container.querySelector('#upload-docs-btn');

        refreshBtn.addEventListener('click', () => this.loadDocuments());
        uploadBtn.addEventListener('click', () => this.showUploadModal());
    }

    loadDocuments() {
        this.showLoading();
        fetch(this.options.documentsUrl)
            .then(response => response.json())
            .then(data => {
                this.documents = data.documents || [];
                this.renderDocuments();
            })
            .catch(error => {
                console.error('Error loading documents:', error);
            })
            .finally(() => this.hideLoading());
    }

    showLoading() {
        this.loadingState.style.display = 'block';
        this.documentGrid.style.display = 'none';
        this.emptyState.style.display = 'none';
    }

    hideLoading() {
        this.loadingState.style.display = 'none';
        this.documentGrid.style.display = 'block';
        if (this.documents.length === 0) {
            this.showEmptyState();
        }
    }

    showEmptyState() {
        this.emptyState.style.display = 'block';
    }

    renderDocuments() {
        if (this.documents.length === 0) {
            this.showEmptyState();
            return;
        }

        this.documentGrid.innerHTML = this.documents.map(doc => `
            <div class="document-item">
                <span>${doc.name}</span>
                <button onclick="documentManager.deleteDocument('${doc.id}')">Delete</button>
            </div>
        `).join('');
    }

    deleteDocument(documentId) {
        fetch(`${this.options.documentsUrl}/${documentId}`, { method: 'DELETE' })
            .then(() => {
                this.documents = this.documents.filter(doc => doc.id !== documentId);
                this.renderDocuments();
            })
            .catch(error => {
                console.error('Error deleting document:', error);
            });
    }

    showUploadModal() {
        // Implement upload modal
        alert('Upload modal logic here.');
    }

    startAutoRefresh() {
        setInterval(() => this.loadDocuments(), this.options.refreshInterval);
    }
}

// Attach to the window for global access
window.EnhancedDocumentManagerV2 = EnhancedDocumentManagerV2;

/**
 * Enhanced Document Management Interface v2
 * Provides improved file upload, validation, retry functionality, and organization
 * Requirements: 2.2, 2.3, 6.7
 */

class EnhancedDocumentManagerV2 {
    constructor(options = {}) {
        this.options = {
            container: '#document-management-section',
            uploadUrl: '/api/llm-training/upload-documents',
            documentsUrl: '/api/llm-training/documents',
            validateUrl: '/api/llm-training/validate-document',
            retryUrl: '/api/llm-training/retry-processing',
            maxRetries: 3,
            autoRefresh: true,
            refreshInterval: 5000,
            ...options
        };

        this.documents = new Map();
        this.filters = {
            status: 'all',
            dataset: 'all',
            search: '',
            sortBy: 'created_at',
            sortOrder: 'desc'
        };
        
        this.dragDropUpload = null;
        this.refreshTimer = null;
        this.isLoading = false;
        this.uploadQueue = [];
        this.processingQueue = [];

        this.init();
    }

    init() {
        this.setupContainer();
        this.setupAdvancedDragDropUpload();
        this.setupEventListeners();
        this.loadDocuments();
        
        if (this.options.autoRefresh) {
            this.startAutoRefresh();
        }
    }

    setupContainer() {
        this.container = document.querySelector(this.options.container);
        if (!this.container) {
            console.error('Document manager container not found');
            return;
        }

        // Enhanced container HTML with improved validation status and filtering
        this.container.innerHTML = this.getEnhancedContainerHTML();

        // Get element references
        this.documentGrid = this.container.querySelector('#document-grid');
        this.loadingState = this.container.querySelector('#loading-state');
        this.emptyState = this.container.querySelector('#empty-state');
        this.uploadSection = this.container.querySelector('#upload-section');
        this.bulkActionsPanel = this.container.querySelector('#bulk-actions-panel');
        this.progressPanel = this.container.querySelector('#progress-panel');
    }

    getEnhancedContainerHTML() {
        return `
            <div class="document-manager enhanced">
                <!-- Header with enhanced actions -->
                <div class="document-header">
                    <div class="header-left">
                        <h3 class="section-title">Document Management</h3>
                        <div class="document-stats enhanced">
                            <div class="stat-item">
                                <span class="stat-value" id="total-docs">0</span>
                                <span class="stat-label">Total</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value" id="processing-docs">0</span>
                                <span class="stat-label">Processing</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value" id="failed-docs">0</span>
                                <span class="stat-label">Failed</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value" id="validated-docs">0</span>
                                <span class="stat-label">Validated</span>
                            </div>
                        </div>
                    </div>
                    <div class="header-actions">
                        <button class="btn btn-secondary" id="refresh-docs-btn" title="Refresh documents">
                            <i class="fas fa-sync-alt"></i> Refresh
                        </button>
                        <button class="btn btn-secondary" id="bulk-actions-btn" title="Bulk operations">
                            <i class="fas fa-tasks"></i> Bulk Actions
                        </button>
                        <button class="btn btn-secondary" id="validation-panel-btn" title="Validation overview">
                            <i class="fas fa-check-circle"></i> Validation
                        </button>
                        <button class="btn btn-primary" id="upload-docs-btn" title="Upload new documents">
                            <i class="fas fa-upload"></i> Upload Documents
                        </button>
                    </div>
                </div>

                <!-- Enhanced Filters and Search -->
                <div class="document-filters enhanced">
                    <div class="filter-row">
                        <div class="search-box enhanced">
                            <input type="text" id="doc-search" placeholder="Search documents by name, content, or dataset..." class="form-input">
                            <i class="fas fa-search search-icon"></i>
                            <button class="clear-search-btn" id="clear-search" title="Clear search" style="display: none;">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        <div class="filter-group enhanced">
                            <select id="status-filter" class="form-select" title="Filter by status">
                                <option value="all">All Status</option>
                                <option value="pending">Pending</option>
                                <option value="processing">Processing</option>
                                <option value="completed">Completed</option>
                                <option value="failed">Failed</option>
                                <option value="validation_failed">Validation Failed</option>
                                <option value="needs_retry">Needs Retry</option>
                            </select>
                            <select id="dataset-filter" class="form-select" title="Filter by dataset">
                                <option value="all">All Datasets</option>
                                <option value="unassigned">Unassigned</option>
                            </select>
                            <select id="sort-filter" class="form-select" title="Sort by">
                                <option value="created_at">Date Created</option>
                                <option value="name">Name</option>
                                <option value="size">Size</option>
                                <option value="status">Status</option>
                                <option value="validation_score">Quality Score</option>
                            </select>
                            <button id="sort-order-btn" class="btn btn-secondary" title="Toggle sort order">
                                <i class="fas fa-sort-amount-down"></i>
                            </button>
                            <button id="view-mode-btn" class="btn btn-secondary" title="Toggle view mode">
                                <i class="fas fa-th"></i>
                            </button>
                        </div>
                    </div>
                    <div class="filter-tags" id="active-filters" style="display: none;">
                        <!-- Active filter tags will appear here -->
                    </div>
                </div>

                <!-- Enhanced Upload Area with Progress -->
                <div class="upload-section enhanced" id="upload-section" style="display: none;">
                    <div class="upload-container" id="upload-container">
                        <div class="drag-drop-zone" id="drag-drop-zone">
                            <div class="upload-icon">
                                <i class="fas fa-cloud-upload-alt"></i>
                            </div>
                            <div class="upload-text">
                                <h4>Drag & Drop Documents Here</h4>
                                <p>or <button class="btn btn-link" id="browse-files-btn">browse files</button></p>
                                <small>Supported: PDF, DOCX, TXT, JSON, MD (Max 50MB each)</small>
                            </div>
                            <input type="file" id="file-input" multiple accept=".pdf,.docx,.doc,.txt,.json,.md" style="display: none;">
                        </div>
                        
                        <!-- Upload Progress Panel -->
                        <div class="upload-progress-panel" id="upload-progress-panel" style="display: none;">
                            <div class="progress-header">
                                <h4>Upload Progress</h4>
                                <button class="btn btn-sm btn-secondary" id="cancel-upload-btn">Cancel All</button>
                            </div>
                            <div class="upload-queue" id="upload-queue">
                                <!-- Upload progress items will appear here -->
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Document Grid with Enhanced Cards -->
                <div class="document-grid-container enhanced">
                    <div class="document-grid" id="document-grid">
                        <!-- Documents will be rendered here -->
                    </div>
                    
                    <!-- Loading State -->
                    <div class="loading-state" id="loading-state" style="display: none;">
                        <div class="spinner"></div>
                        <p>Loading documents...</p>
                    </div>
                    
                    <!-- Empty State -->
                    <div class="empty-state enhanced" id="empty-state" style="display: none;">
                        <div class="empty-icon">📄</div>
                        <h3>No documents found</h3>
                        <p>Upload some documents to get started with training your models.</p>
                        <div class="empty-actions">
                            <button class="btn btn-primary" id="empty-upload-btn">
                                <i class="fas fa-upload"></i> Upload Documents
                            </button>
                            <button class="btn btn-secondary" id="sample-docs-btn">
                                <i class="fas fa-download"></i> Download Samples
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Enhanced Bulk Actions Panel -->
                <div class="bulk-actions-panel enhanced" id="bulk-actions-panel" style="display: none;">
                    <div class="panel-header">
                        <div class="selection-info">
                            <span class="selected-count">0 documents selected</span>
                            <div class="selection-actions">
                                <button class="btn btn-secondary btn-sm" id="select-all-btn">Select All</button>
                                <button class="btn btn-secondary btn-sm" id="select-failed-btn">Select Failed</button>
                                <button class="btn btn-secondary btn-sm" id="clear-selection-btn">Clear</button>
                            </div>
                        </div>
                    </div>
                    <div class="panel-actions">
                        <button class="btn btn-secondary" id="bulk-retry-btn" title="Retry processing for selected documents">
                            <i class="fas fa-redo"></i> Retry Processing
                        </button>
                        <button class="btn btn-secondary" id="bulk-validate-btn" title="Validate selected documents">
                            <i class="fas fa-check-circle"></i> Validate
                        </button>
                        <button class="btn btn-secondary" id="bulk-assign-btn" title="Assign to dataset">
                            <i class="fas fa-folder"></i> Assign to Dataset
                        </button>
                        <button class="btn btn-secondary" id="bulk-download-btn" title="Download selected documents">
                            <i class="fas fa-download"></i> Download
                        </button>
                        <button class="btn btn-danger" id="bulk-delete-btn" title="Delete selected documents">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    // Enhanced utility methods
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }

    getStatusClass(status) {
        const statusClasses = {
            'pending': 'status-pending',
            'processing': 'status-processing',
            'completed': 'status-completed',
            'failed': 'status-failed',
            'validation_failed': 'status-failed',
            'needs_retry': 'status-warning'
        };
        return statusClasses[status] || 'status-unknown';
    }

    getStatusIcon(status) {
        const statusIcons = {
            'pending': 'fas fa-clock',
            'processing': 'fas fa-spinner fa-spin',
            'completed': 'fas fa-check-circle',
            'failed': 'fas fa-exclamation-circle',
            'validation_failed': 'fas fa-times-circle',
            'needs_retry': 'fas fa-exclamation-triangle'
        };
        return statusIcons[status] || 'fas fa-question-circle';
    }

    getStatusText(status) {
        const statusTexts = {
            'pending': 'Pending',
            'processing': 'Processing',
            'completed': 'Completed',
            'failed': 'Failed',
            'validation_failed': 'Validation Failed',
            'needs_retry': 'Needs Retry'
        };
        return statusTexts[status] || 'Unknown';
    }

    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

    showSuccess(message) {
        console.log('Success:', message);
    }

    showError(message) {
        console.error('Error:', message);
    }

    showWarning(message) {
        console.warn('Warning:', message);
    }
}

// Initialize the enhanced document manager
window.EnhancedDocumentManagerV2 = EnhancedDocumentManagerV2;