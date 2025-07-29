/**
 * Enhanced Document Management Interface
 * Provides improved file upload, validation, retry functionality, and organization
 */

class EnhancedDocumentManager {
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

        this.init();
    }

    init() {
        this.setupContainer();
        this.setupDragDropUpload();
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

        // Enhanced container HTML with validation status and filtering
        this.container.innerHTML = this.getContainerHTML();

        // Get element references
        this.documentGrid = this.container.querySelector('#document-grid');
        this.loadingState = this.container.querySelector('#loading-state');
        this.emptyState = this.container.querySelector('#empty-state');
        this.uploadSection = this.container.querySelector('#upload-section');
        this.bulkActionsPanel = this.container.querySelector('#bulk-actions-panel');
    }

    getContainerHTML() {
        return `
            <div class="document-manager">
                <!-- Header with actions -->
                <div class="document-header">
                    <div class="header-left">
                        <h3 class="section-title">Document Management</h3>
                        <div class="document-stats">
                            <span class="stat-item">
                                <span class="stat-value" id="total-docs">0</span>
                                <span class="stat-label">Total</span>
                            </span>
                            <span class="stat-item">
                                <span class="stat-value" id="processing-docs">0</span>
                                <span class="stat-label">Processing</span>
                            </span>
                            <span class="stat-item">
                                <span class="stat-value" id="failed-docs">0</span>
                                <span class="stat-label">Failed</span>
                            </span>
                        </div>
                    </div>
                    <div class="header-actions">
                        <button class="btn btn-secondary" id="refresh-docs-btn">
                            <i class="fas fa-sync-alt"></i> Refresh
                        </button>
                        <button class="btn btn-secondary" id="bulk-actions-btn">
                            <i class="fas fa-tasks"></i> Bulk Actions
                        </button>
                        <button class="btn btn-primary" id="upload-docs-btn">
                            <i class="fas fa-upload"></i> Upload Documents
                        </button>
                    </div>
                </div>

                <!-- Filters and Search -->
                <div class="document-filters">
                    <div class="filter-row">
                        <div class="search-box">
                            <input type="text" id="doc-search" placeholder="Search documents..." class="form-input">
                            <i class="fas fa-search search-icon"></i>
                        </div>
                        <div class="filter-group">
                            <select id="status-filter" class="form-select">
                                <option value="all">All Status</option>
                                <option value="pending">Pending</option>
                                <option value="processing">Processing</option>
                                <option value="completed">Completed</option>
                                <option value="failed">Failed</option>
                                <option value="validation_failed">Validation Failed</option>
                            </select>
                            <select id="dataset-filter" class="form-select">
                                <option value="all">All Datasets</option>
                                <option value="unassigned">Unassigned</option>
                            </select>
                            <select id="sort-filter" class="form-select">
                                <option value="created_at">Date Created</option>
                                <option value="name">Name</option>
                                <option value="size">Size</option>
                                <option value="status">Status</option>
                            </select>
                            <button id="sort-order-btn" class="btn btn-secondary" title="Toggle sort order">
                                <i class="fas fa-sort-amount-down"></i>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Upload Area -->
                <div class="upload-section" id="upload-section" style="display: none;">
                    <div class="upload-container" id="upload-container">
                        <!-- Drag-drop upload will be initialized here -->
                    </div>
                </div>

                <!-- Document Grid -->
                <div class="document-grid-container">
                    <div class="document-grid" id="document-grid">
                        <!-- Documents will be rendered here -->
                    </div>
                    
                    <!-- Loading State -->
                    <div class="loading-state" id="loading-state" style="display: none;">
                        <div class="spinner"></div>
                        <p>Loading documents...</p>
                    </div>
                    
                    <!-- Empty State -->
                    <div class="empty-state" id="empty-state" style="display: none;">
                        <div class="empty-icon">📄</div>
                        <h3>No documents found</h3>
                        <p>Upload some documents to get started with training your models.</p>
                        <button class="btn btn-primary" id="empty-upload-btn">
                            <i class="fas fa-upload"></i> Upload Documents
                        </button>
                    </div>
                </div>

                <!-- Bulk Actions Panel -->
                <div class="bulk-actions-panel" id="bulk-actions-panel" style="display: none;">
                    <div class="panel-header">
                        <span class="selected-count">0 documents selected</span>
                        <button class="btn btn-secondary btn-sm" id="select-all-btn">Select All</button>
                        <button class="btn btn-secondary btn-sm" id="clear-selection-btn">Clear</button>
                    </div>
                    <div class="panel-actions">
                        <button class="btn btn-secondary" id="bulk-retry-btn">
                            <i class="fas fa-redo"></i> Retry Processing
                        </button>
                        <button class="btn btn-secondary" id="bulk-validate-btn">
                            <i class="fas fa-check-circle"></i> Validate
                        </button>
                        <button class="btn btn-secondary" id="bulk-assign-btn">
                            <i class="fas fa-folder"></i> Assign to Dataset
                        </button>
                        <button class="btn btn-danger" id="bulk-delete-btn">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
}    s
etupDragDropUpload() {
        const uploadContainer = this.container.querySelector('#upload-container');
        if (!uploadContainer) return;

        this.dragDropUpload = new DragDropUpload({
            container: uploadContainer,
            multiple: true,
            maxFiles: 20,
            maxFileSize: 50 * 1024 * 1024, // 50MB
            acceptedTypes: ['.pdf', '.docx', '.doc', '.txt', '.json', '.md'],
            uploadUrl: this.options.uploadUrl,
            onFileSelect: (files) => {
                console.log('Files selected:', files.length);
            },
            onUploadProgress: (percentage, loaded, total) => {
                this.updateUploadProgress(percentage, loaded, total);
            },
            onUploadComplete: (response) => {
                this.handleUploadComplete(response);
            },
            onError: (error) => {
                this.handleUploadError(error);
            }
        });
    }

    setupEventListeners() {
        // Upload button
        this.container.querySelector('#upload-docs-btn')?.addEventListener('click', () => {
            this.toggleUploadSection();
        });

        this.container.querySelector('#empty-upload-btn')?.addEventListener('click', () => {
            this.showUploadSection();
        });

        // Refresh button
        this.container.querySelector('#refresh-docs-btn')?.addEventListener('click', () => {
            this.loadDocuments(true);
        });

        // Search and filters
        this.container.querySelector('#doc-search')?.addEventListener('input', (e) => {
            this.filters.search = e.target.value;
            this.debounceFilter();
        });

        this.container.querySelector('#status-filter')?.addEventListener('change', (e) => {
            this.filters.status = e.target.value;
            this.applyFilters();
        });

        this.container.querySelector('#dataset-filter')?.addEventListener('change', (e) => {
            this.filters.dataset = e.target.value;
            this.applyFilters();
        });

        this.container.querySelector('#sort-filter')?.addEventListener('change', (e) => {
            this.filters.sortBy = e.target.value;
            this.applyFilters();
        });

        this.container.querySelector('#sort-order-btn')?.addEventListener('click', () => {
            this.toggleSortOrder();
        });

        // Bulk actions
        this.container.querySelector('#bulk-actions-btn')?.addEventListener('click', () => {
            this.toggleBulkActions();
        });

        this.container.querySelector('#select-all-btn')?.addEventListener('click', () => {
            this.selectAllDocuments();
        });

        this.container.querySelector('#clear-selection-btn')?.addEventListener('click', () => {
            this.clearSelection();
        });

        this.container.querySelector('#bulk-retry-btn')?.addEventListener('click', () => {
            this.bulkRetryProcessing();
        });

        this.container.querySelector('#bulk-validate-btn')?.addEventListener('click', () => {
            this.bulkValidateDocuments();
        });

        this.container.querySelector('#bulk-assign-btn')?.addEventListener('click', () => {
            this.showBulkAssignModal();
        });

        this.container.querySelector('#bulk-delete-btn')?.addEventListener('click', () => {
            this.bulkDeleteDocuments();
        });
    }

    // Document loading and management
    async loadDocuments(force = false) {
        if (this.isLoading && !force) return;
        
        this.isLoading = true;
        this.showLoading();

        try {
            const response = await fetch(this.options.documentsUrl);
            if (!response.ok) throw new Error('Failed to load documents');
            
            const data = await response.json();
            this.documents.clear();
            
            data.documents.forEach(doc => {
                this.documents.set(doc.id, doc);
            });

            this.updateStats();
            this.renderDocuments();
            
        } catch (error) {
            console.error('Error loading documents:', error);
            this.showError('Failed to load documents. Please try again.');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    renderDocuments() {
        const filteredDocs = this.getFilteredDocuments();
        
        if (filteredDocs.length === 0) {
            this.showEmptyState();
            return;
        }

        this.hideEmptyState();
        this.documentGrid.innerHTML = '';

        filteredDocs.forEach(doc => {
            const docElement = this.createDocumentCard(doc);
            this.documentGrid.appendChild(docElement);
        });
    }

    createDocumentCard(doc) {
        const card = document.createElement('div');
        card.className = 'document-card';
        card.dataset.docId = doc.id;

        const statusClass = this.getStatusClass(doc.validation_status || doc.processing_status);
        const statusIcon = this.getStatusIcon(doc.validation_status || doc.processing_status);
        
        card.innerHTML = this.getDocumentCardHTML(doc, statusClass, statusIcon);

        // Add event listeners
        this.setupDocumentCardEvents(card, doc);
        
        return card;
    }

    getDocumentCardHTML(doc, statusClass, statusIcon) {
        return `
            <div class="document-card-header">
                <div class="document-checkbox">
                    <input type="checkbox" class="doc-checkbox" data-doc-id="${doc.id}">
                </div>
                <div class="document-status ${statusClass}">
                    <i class="${statusIcon}"></i>
                    <span class="status-text">${this.getStatusText(doc.validation_status || doc.processing_status)}</span>
                </div>
                <div class="document-actions">
                    <button class="btn btn-sm btn-secondary" onclick="documentManager.viewDocument('${doc.id}')" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-secondary dropdown-toggle" data-doc-id="${doc.id}" title="More Actions">
                        <i class="fas fa-ellipsis-v"></i>
                    </button>
                </div>
            </div>
            
            <div class="document-content">
                <div class="document-name" title="${doc.original_name}">
                    ${doc.original_name}
                </div>
                <div class="document-meta">
                    <span class="meta-item">
                        <i class="fas fa-calendar"></i>
                        ${this.formatDate(doc.created_at)}
                    </span>
                    <span class="meta-item">
                        <i class="fas fa-file"></i>
                        ${this.formatFileSize(doc.file_size)}
                    </span>
                    ${doc.word_count ? `
                        <span class="meta-item">
                            <i class="fas fa-font"></i>
                            ${doc.word_count.toLocaleString()} words
                        </span>
                    ` : ''}
                </div>
                
                ${doc.validation_errors && doc.validation_errors.length > 0 ? `
                    <div class="validation-errors">
                        <div class="error-summary">
                            <i class="fas fa-exclamation-triangle"></i>
                            ${doc.validation_errors.length} validation error${doc.validation_errors.length > 1 ? 's' : ''}
                        </div>
                        <div class="error-details" style="display: none;">
                            ${doc.validation_errors.map(error => `<div class="error-item">${error}</div>`).join('')}
                        </div>
                    </div>
                ` : ''}
                
                ${doc.processing_retries > 0 ? `
                    <div class="retry-info">
                        <i class="fas fa-redo"></i>
                        Retried ${doc.processing_retries} time${doc.processing_retries > 1 ? 's' : ''}
                    </div>
                ` : ''}
                
                <div class="document-tags">
                    ${doc.datasets && doc.datasets.length > 0 ? 
                        doc.datasets.map(dataset => `<span class="tag">${dataset.name}</span>`).join('') :
                        '<span class="tag tag-unassigned">Unassigned</span>'
                    }
                </div>
            </div>
            
            <div class="document-footer">
                ${this.getDocumentActions(doc)}
            </div>
        `;
    }

    getDocumentActions(doc) {
        const actions = [];
        
        if (doc.validation_status === 'failed' || doc.processing_status === 'failed') {
            actions.push(`
                <button class="btn btn-sm btn-primary" onclick="documentManager.retryProcessing('${doc.id}')">
                    <i class="fas fa-redo"></i> Retry
                </button>
            `);
        }
        
        if (doc.validation_status === 'pending' || !doc.validation_status) {
            actions.push(`
                <button class="btn btn-sm btn-secondary" onclick="documentManager.validateDocument('${doc.id}')">
                    <i class="fas fa-check-circle"></i> Validate
                </button>
            `);
        }
        
        actions.push(`
            <button class="btn btn-sm btn-secondary" onclick="documentManager.assignToDataset('${doc.id}')">
                <i class="fas fa-folder"></i> Assign
            </button>
        `);
        
        return actions.join('');
    }

    setupDocumentCardEvents(card, doc) {
        // Checkbox selection
        const checkbox = card.querySelector('.doc-checkbox');
        checkbox.addEventListener('change', () => {
            this.updateBulkActionsPanel();
        });

        // Error details toggle
        const errorSummary = card.querySelector('.error-summary');
        if (errorSummary) {
            errorSummary.addEventListener('click', () => {
                const details = card.querySelector('.error-details');
                const isVisible = details.style.display !== 'none';
                details.style.display = isVisible ? 'none' : 'block';
                errorSummary.querySelector('i').className = isVisible ? 'fas fa-exclamation-triangle' : 'fas fa-chevron-up';
            });
        }

        // Dropdown menu
        const dropdownBtn = card.querySelector('.dropdown-toggle');
        if (dropdownBtn) {
            dropdownBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showDocumentDropdown(e.target, doc);
            });
        }
    }    
// Document actions
    async retryProcessing(docId) {
        try {
            const response = await fetch(`${this.options.retryUrl}/${docId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) throw new Error('Failed to retry processing');
            
            const result = await response.json();
            this.showSuccess('Document processing retry initiated');
            
            // Update document status
            const doc = this.documents.get(docId);
            if (doc) {
                doc.processing_status = 'processing';
                doc.processing_retries = (doc.processing_retries || 0) + 1;
                this.renderDocuments();
            }
            
        } catch (error) {
            console.error('Error retrying processing:', error);
            this.showError('Failed to retry processing. Please try again.');
        }
    }

    async validateDocument(docId) {
        try {
            const response = await fetch(`${this.options.validateUrl}/${docId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) throw new Error('Failed to validate document');
            
            const result = await response.json();
            
            // Update document with validation results
            const doc = this.documents.get(docId);
            if (doc) {
                doc.validation_status = result.status;
                doc.validation_errors = result.errors || [];
                doc.content_quality_score = result.quality_score;
                this.renderDocuments();
            }
            
            if (result.status === 'completed') {
                this.showSuccess('Document validation completed successfully');
            } else {
                this.showWarning(`Document validation completed with ${result.errors?.length || 0} issues`);
            }
            
        } catch (error) {
            console.error('Error validating document:', error);
            this.showError('Failed to validate document. Please try again.');
        }
    }

    // Filtering and sorting
    getFilteredDocuments() {
        let docs = Array.from(this.documents.values());

        // Apply status filter
        if (this.filters.status !== 'all') {
            docs = docs.filter(doc => {
                const status = doc.validation_status || doc.processing_status;
                return status === this.filters.status;
            });
        }

        // Apply dataset filter
        if (this.filters.dataset !== 'all') {
            if (this.filters.dataset === 'unassigned') {
                docs = docs.filter(doc => !doc.datasets || doc.datasets.length === 0);
            } else {
                docs = docs.filter(doc => 
                    doc.datasets && doc.datasets.some(dataset => dataset.id === this.filters.dataset)
                );
            }
        }

        // Apply search filter
        if (this.filters.search) {
            const searchTerm = this.filters.search.toLowerCase();
            docs = docs.filter(doc => 
                doc.original_name.toLowerCase().includes(searchTerm) ||
                (doc.datasets && doc.datasets.some(dataset => 
                    dataset.name.toLowerCase().includes(searchTerm)
                ))
            );
        }

        // Apply sorting
        docs.sort((a, b) => {
            let aVal = a[this.filters.sortBy];
            let bVal = b[this.filters.sortBy];

            if (this.filters.sortBy === 'name') {
                aVal = a.original_name;
                bVal = b.original_name;
            }

            if (typeof aVal === 'string') {
                aVal = aVal.toLowerCase();
                bVal = bVal.toLowerCase();
            }

            let comparison = 0;
            if (aVal < bVal) comparison = -1;
            if (aVal > bVal) comparison = 1;

            return this.filters.sortOrder === 'desc' ? -comparison : comparison;
        });

        return docs;
    }

    applyFilters() {
        this.renderDocuments();
    }

    debounceFilter() {
        clearTimeout(this.filterTimeout);
        this.filterTimeout = setTimeout(() => {
            this.applyFilters();
        }, 300);
    }

    toggleSortOrder() {
        this.filters.sortOrder = this.filters.sortOrder === 'asc' ? 'desc' : 'asc';
        const btn = this.container.querySelector('#sort-order-btn i');
        btn.className = this.filters.sortOrder === 'asc' ? 'fas fa-sort-amount-up' : 'fas fa-sort-amount-down';
        this.applyFilters();
    }

    // Bulk actions
    toggleBulkActions() {
        const panel = this.bulkActionsPanel;
        const isVisible = panel.style.display !== 'none';
        panel.style.display = isVisible ? 'none' : 'block';
        
        if (!isVisible) {
            this.updateBulkActionsPanel();
        }
    }

    updateBulkActionsPanel() {
        const checkboxes = this.container.querySelectorAll('.doc-checkbox:checked');
        const count = checkboxes.length;
        
        const countSpan = this.container.querySelector('.selected-count');
        if (countSpan) {
            countSpan.textContent = `${count} document${count !== 1 ? 's' : ''} selected`;
        }

        // Enable/disable bulk action buttons
        const actionButtons = this.container.querySelectorAll('.bulk-actions-panel .btn:not(#select-all-btn):not(#clear-selection-btn)');
        actionButtons.forEach(btn => {
            btn.disabled = count === 0;
        });
    }

    selectAllDocuments() {
        const checkboxes = this.container.querySelectorAll('.doc-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.checked = true;
        });
        this.updateBulkActionsPanel();
    }

    clearSelection() {
        const checkboxes = this.container.querySelectorAll('.doc-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        this.updateBulkActionsPanel();
    }

    getSelectedDocuments() {
        const checkboxes = this.container.querySelectorAll('.doc-checkbox:checked');
        return Array.from(checkboxes).map(checkbox => checkbox.dataset.docId);
    }

    async bulkRetryProcessing() {
        const selectedIds = this.getSelectedDocuments();
        if (selectedIds.length === 0) return;

        if (!confirm(`Retry processing for ${selectedIds.length} document${selectedIds.length > 1 ? 's' : ''}?`)) {
            return;
        }

        try {
            const promises = selectedIds.map(id => this.retryProcessing(id));
            await Promise.all(promises);
            this.showSuccess(`Retry initiated for ${selectedIds.length} document${selectedIds.length > 1 ? 's' : ''}`);
            this.clearSelection();
        } catch (error) {
            this.showError('Failed to retry processing for some documents');
        }
    }

    async bulkValidateDocuments() {
        const selectedIds = this.getSelectedDocuments();
        if (selectedIds.length === 0) return;

        try {
            const promises = selectedIds.map(id => this.validateDocument(id));
            await Promise.all(promises);
            this.showSuccess(`Validation initiated for ${selectedIds.length} document${selectedIds.length > 1 ? 's' : ''}`);
            this.clearSelection();
        } catch (error) {
            this.showError('Failed to validate some documents');
        }
    }

    // Upload handling
    toggleUploadSection() {
        const isVisible = this.uploadSection.style.display !== 'none';
        this.uploadSection.style.display = isVisible ? 'none' : 'block';
    }

    showUploadSection() {
        this.uploadSection.style.display = 'block';
    }

    updateUploadProgress(percentage, loaded, total) {
        // Update any global progress indicators
        console.log(`Upload progress: ${percentage}% (${loaded}/${total} bytes)`);
    }

    handleUploadComplete(response) {
        this.showSuccess(`Successfully uploaded ${response.uploaded?.length || 0} document${response.uploaded?.length !== 1 ? 's' : ''}`);
        this.uploadSection.style.display = 'none';
        this.loadDocuments(true);
    }

    handleUploadError(error) {
        this.showError(`Upload failed: ${error}`);
    }   
 // Utility methods
    updateStats() {
        const docs = Array.from(this.documents.values());
        const totalDocs = docs.length;
        const processingDocs = docs.filter(doc => 
            doc.processing_status === 'processing' || doc.validation_status === 'pending'
        ).length;
        const failedDocs = docs.filter(doc => 
            doc.processing_status === 'failed' || doc.validation_status === 'failed'
        ).length;

        this.container.querySelector('#total-docs').textContent = totalDocs;
        this.container.querySelector('#processing-docs').textContent = processingDocs;
        this.container.querySelector('#failed-docs').textContent = failedDocs;
    }

    getStatusClass(status) {
        const statusClasses = {
            'pending': 'status-pending',
            'processing': 'status-processing',
            'completed': 'status-completed',
            'failed': 'status-failed',
            'validation_failed': 'status-failed'
        };
        return statusClasses[status] || 'status-unknown';
    }

    getStatusIcon(status) {
        const statusIcons = {
            'pending': 'fas fa-clock',
            'processing': 'fas fa-spinner fa-spin',
            'completed': 'fas fa-check-circle',
            'failed': 'fas fa-exclamation-circle',
            'validation_failed': 'fas fa-exclamation-triangle'
        };
        return statusIcons[status] || 'fas fa-question-circle';
    }

    getStatusText(status) {
        const statusTexts = {
            'pending': 'Pending',
            'processing': 'Processing',
            'completed': 'Completed',
            'failed': 'Failed',
            'validation_failed': 'Validation Failed'
        };
        return statusTexts[status] || 'Unknown';
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString();
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    showLoading() {
        this.loadingState.style.display = 'block';
        this.documentGrid.style.display = 'none';
        this.emptyState.style.display = 'none';
    }

    hideLoading() {
        this.loadingState.style.display = 'none';
        this.documentGrid.style.display = 'grid';
    }

    showEmptyState() {
        this.emptyState.style.display = 'block';
        this.documentGrid.style.display = 'none';
    }

    hideEmptyState() {
        this.emptyState.style.display = 'none';
        this.documentGrid.style.display = 'grid';
    }

    showSuccess(message) {
        if (window.UIComponents) {
            window.UIComponents.showNotification(message, 'success');
        } else {
            console.log('Success:', message);
        }
    }

    showError(message) {
        if (window.UIComponents) {
            window.UIComponents.showNotification(message, 'error');
        } else {
            console.error('Error:', message);
        }
    }

    showWarning(message) {
        if (window.UIComponents) {
            window.UIComponents.showNotification(message, 'warning');
        } else {
            console.warn('Warning:', message);
        }
    }

    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    startAutoRefresh() {
        this.refreshTimer = setInterval(() => {
            if (!this.isLoading) {
                this.loadDocuments();
            }
        }, this.options.refreshInterval);
    }

    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    destroy() {
        this.stopAutoRefresh();
        if (this.dragDropUpload) {
            this.dragDropUpload.destroy();
        }
    }
}

// Global registration
if (typeof window !== 'undefined') {
    window.EnhancedDocumentManager = EnhancedDocumentManager;
}