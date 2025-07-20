/**
 * Document Management Component for LLM Training
 * Handles document listing, organization, datasets, and deletion
 */

class DocumentManagement {
    constructor(options) {
        this.container = options.container;
        this.options = { apiBaseUrl: '/api', ...options };
        this.documents = [];
        this.datasets = [];
        this.selectedDocuments = new Set();
        this.currentView = 'documents';
        this.loading = false;

        // DOM elements
        this.viewToggle = null;
        this.documentsList = null;
        this.datasetsList = null;
        this.searchInput = null;
        this.filterSelect = null;
        this.bulkActions = null;
        this.createDatasetBtn = null;
        this.refreshBtn = null;

        this.init();
    }

    init() {
        this.setupDOMReferences();
        this.setupEventListeners();
        this.loadDocuments();
        this.loadDatasets();
    }

    setupDOMReferences() {
        this.viewToggle = this.container.querySelector('.view-toggle');
        this.documentsList = this.container.querySelector('.documents-list');
        this.datasetsList = this.container.querySelector('.datasets-list');
        this.searchInput = this.container.querySelector('.search-input');
        this.filterSelect = this.container.querySelector('.filter-select');
        this.bulkActions = this.container.querySelector('.bulk-actions');
        this.createDatasetBtn = this.container.querySelector('.create-dataset-btn');
        this.refreshBtn = this.container.querySelector('.refresh-btn');
    }

    setupEventListeners() {
        // View toggle
        this.viewToggle.addEventListener('click', (e) => {
            if (e.target.classList.contains('view-btn')) {
                this.switchView(e.target.dataset.view);
            }
        });

        // Search and filter
        this.searchInput.addEventListener('input', () => {
            this.filterDocuments();
        });

        this.filterSelect.addEventListener('change', () => {
            this.filterDocuments();
        });

        // Refresh button
        this.refreshBtn.addEventListener('click', () => {
            this.refresh();
        });

        // Create dataset button
        this.createDatasetBtn.addEventListener('click', () => {
            this.showCreateDatasetModal();
        });

        // Bulk actions
        this.container.querySelector('.add-to-dataset-btn')?.addEventListener('click', () => {
            this.showAddToDatasetModal();
        });

        this.container.querySelector('.bulk-delete-btn')?.addEventListener('click', () => {
            this.bulkDeleteDocuments();
        });

        this.container.querySelector('.clear-selection-btn')?.addEventListener('click', () => {
            this.clearSelection();
        });
    }

    switchView(view) {
        this.currentView = view;

        // Update toggle buttons
        this.viewToggle.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        this.viewToggle.querySelector(`[data-view="${view}"]`)?.classList.add('active');

        // Show/hide views
        const documentsView = this.container.querySelector('.documents-view');
        const datasetsView = this.container.querySelector('.datasets-view');

        if (view === 'documents') {
            documentsView.classList.remove('hidden');
            datasetsView.classList.add('hidden');
            this.renderDocuments();
        } else {
            documentsView.classList.add('hidden');
            datasetsView.classList.remove('hidden');
            this.renderDatasets();
        }

        // Hide bulk actions when switching views
        this.bulkActions.classList.add('hidden');
        this.clearSelection();
    }   
 // API Methods
    async loadDocuments() {
        try {
            this.showLoading();
            const response = await fetch(`${this.options.apiBaseUrl}/documents`);
            const result = await response.json();

            if (result.success && result.data) {
                this.documents = result.data;
                if (this.currentView === 'documents') {
                    this.renderDocuments();
                }
            } else {
                this.handleError(result.error || { type: 'api_error', message: 'Failed to load documents' });
            }
        } catch (error) {
            this.handleError({ type: 'network_error', message: 'Network error loading documents' });
        } finally {
            this.hideLoading();
        }
    }

    async loadDatasets() {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/documents/datasets`);
            const result = await response.json();

            if (result.success && result.data) {
                this.datasets = result.data;
                if (this.currentView === 'datasets') {
                    this.renderDatasets();
                }
            } else {
                this.handleError(result.error || { type: 'api_error', message: 'Failed to load datasets' });
            }
        } catch (error) {
            this.handleError({ type: 'network_error', message: 'Network error loading datasets' });
        }
    }

    async deleteDocument(documentId) {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/documents/${documentId}`, {
                method: 'DELETE'
            });
            const result = await response.json();

            if (result.success) {
                this.documents = this.documents.filter(doc => doc.id !== documentId);
                this.renderDocuments();
                this.showSuccess('Document deleted successfully');
                this.options.onDocumentDeleted?.(documentId);
            } else {
                this.handleError(result.error || { type: 'api_error', message: 'Failed to delete document' });
            }
        } catch (error) {
            this.handleError({ type: 'network_error', message: 'Network error deleting document' });
        }
    }

    async bulkDeleteDocuments() {
        if (this.selectedDocuments.size === 0) {
            this.showError('Please select documents to delete');
            return;
        }

        if (!confirm(`Are you sure you want to delete ${this.selectedDocuments.size} selected documents?`)) {
            return;
        }

        try {
            const response = await fetch(`${this.options.apiBaseUrl}/documents/bulk-delete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    document_ids: Array.from(this.selectedDocuments)
                })
            });
            const result = await response.json();

            if (result.success) {
                // Remove deleted documents from local state
                this.documents = this.documents.filter(doc => !this.selectedDocuments.has(doc.id));
                this.clearSelection();
                this.renderDocuments();
                
                const { deleted_count, failed_deletions } = result.data;
                if (failed_deletions.length > 0) {
                    this.showWarning(`${deleted_count} documents deleted, ${failed_deletions.length} failed`);
                } else {
                    this.showSuccess(`${deleted_count} documents deleted successfully`);
                }
            } else {
                this.handleError(result.error || { type: 'api_error', message: 'Failed to delete documents' });
            }
        } catch (error) {
            this.handleError({ type: 'network_error', message: 'Network error during bulk deletion' });
        }
    }

    async createDataset(name, description) {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/documents/datasets`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, description })
            });
            const result = await response.json();

            if (result.success && result.data) {
                this.datasets.push(result.data);
                this.showSuccess('Dataset created successfully');
                this.options.onDatasetCreated?.(result.data);
                if (this.currentView === 'datasets') {
                    this.renderDatasets();
                }
            } else {
                this.handleError(result.error || { type: 'api_error', message: 'Failed to create dataset' });
            }
        } catch (error) {
            this.handleError({ type: 'network_error', message: 'Network error creating dataset' });
        }
    }

    async addDocumentsToDataset(documentIds, datasetId) {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/documents/datasets/${datasetId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ add_documents: documentIds })
            });
            const result = await response.json();

            if (result.success && result.data) {
                // Update local dataset
                const datasetIndex = this.datasets.findIndex(d => d.id === datasetId);
                if (datasetIndex !== -1) {
                    this.datasets[datasetIndex] = result.data;
                }
                
                // Update documents with dataset reference
                documentIds.forEach(docId => {
                    const doc = this.documents.find(d => d.id === docId);
                    if (doc && !doc.datasets.includes(datasetId)) {
                        doc.datasets.push(datasetId);
                    }
                });

                this.renderDocuments();
                this.showSuccess('Documents added to dataset successfully');
                this.options.onDatasetUpdated?.(result.data);
            } else {
                this.handleError(result.error || { type: 'api_error', message: 'Failed to add documents to dataset' });
            }
        } catch (error) {
            this.handleError({ type: 'network_error', message: 'Network error adding documents to dataset' });
        }
    }

    async deleteDataset(datasetId) {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/documents/datasets/${datasetId}`, {
                method: 'DELETE'
            });
            const result = await response.json();

            if (result.success) {
                this.datasets = this.datasets.filter(dataset => dataset.id !== datasetId);
                this.renderDatasets();
                this.showSuccess('Dataset deleted successfully');
            } else {
                this.handleError(result.error || { type: 'api_error', message: 'Failed to delete dataset' });
            }
        } catch (error) {
            this.handleError({ type: 'network_error', message: 'Network error deleting dataset' });
        }
    } 
   // Rendering Methods
    renderDocuments() {
        const filteredDocs = this.getFilteredDocuments();
        
        if (filteredDocs.length === 0) {
            this.showEmptyState();
            return;
        }

        this.hideEmptyState();
        this.documentsList.innerHTML = filteredDocs.map(doc => this.renderDocumentItem(doc)).join('');
        
        // Add event listeners to document items
        this.documentsList.querySelectorAll('.document-item').forEach((item, index) => {
            const doc = filteredDocs[index];
            this.setupDocumentItemListeners(item, doc);
        });
    }

    renderDocumentItem(doc) {
        const isSelected = this.selectedDocuments.has(doc.id);
        const datasetNames = doc.datasets.map(id => {
            const dataset = this.datasets.find(d => d.id === id);
            return dataset ? dataset.name : 'Unknown';
        }).join(', ');

        return `
            <div class="document-item bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow duration-200" data-document-id="${doc.id}">
                <div class="flex items-start justify-between">
                    <div class="flex items-start space-x-3">
                        <input type="checkbox" class="document-checkbox mt-1" ${isSelected ? 'checked' : ''}>
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center space-x-2">
                                ${this.getFileIcon(doc)}
                                <h4 class="text-sm font-medium text-gray-900 truncate" title="${doc.name}">
                                    ${doc.name}
                                </h4>
                                <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${this.getStatusColor(doc.status)}">
                                    ${this.getStatusText(doc.status)}
                                </span>
                            </div>
                            <div class="mt-1 text-xs text-gray-500">
                                ${this.formatFileSize(doc.metadata.file_size)} • ${doc.metadata.word_count} words • ${this.formatDate(doc.metadata.upload_date)}
                            </div>
                            ${datasetNames ? `
                                <div class="mt-2">
                                    <span class="text-xs text-gray-500">Datasets: </span>
                                    <span class="text-xs text-blue-600">${datasetNames}</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        <button type="button" class="view-document-btn text-blue-600 hover:text-blue-800 text-sm">
                            View
                        </button>
                        <button type="button" class="delete-document-btn text-red-600 hover:text-red-800 text-sm">
                            Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    renderDatasets() {
        if (this.datasets.length === 0) {
            this.datasetsList.innerHTML = `
                <div class="text-center py-12">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
                    </svg>
                    <h3 class="mt-2 text-sm font-medium text-gray-900">No datasets</h3>
                    <p class="mt-1 text-sm text-gray-500">Create your first dataset to organize documents.</p>
                </div>
            `;
            return;
        }

        this.datasetsList.innerHTML = this.datasets.map(dataset => this.renderDatasetItem(dataset)).join('');
        
        // Add event listeners to dataset items
        this.datasetsList.querySelectorAll('.dataset-item').forEach((item, index) => {
            const dataset = this.datasets[index];
            this.setupDatasetItemListeners(item, dataset);
        });
    }

    renderDatasetItem(dataset) {
        const stats = dataset.statistics || {};
        return `
            <div class="dataset-item bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow duration-200" data-dataset-id="${dataset.id}">
                <div class="flex items-start justify-between">
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center space-x-2">
                            <svg class="h-5 w-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
                            </svg>
                            <h4 class="text-sm font-medium text-gray-900 truncate" title="${dataset.name}">
                                ${dataset.name}
                            </h4>
                        </div>
                        ${dataset.description ? `
                            <p class="mt-1 text-sm text-gray-600">${dataset.description}</p>
                        ` : ''}
                        <div class="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                            <span>${stats.document_count || 0} documents</span>
                            <span>${(stats.total_words || 0).toLocaleString()} words</span>
                            <span>${this.formatFileSize(stats.total_file_size || 0)}</span>
                            <span>Created ${this.formatDate(dataset.created_date)}</span>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        <button type="button" class="edit-dataset-btn text-blue-600 hover:text-blue-800 text-sm">
                            Edit
                        </button>
                        <button type="button" class="delete-dataset-btn text-red-600 hover:text-red-800 text-sm">
                            Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    setupDocumentItemListeners(item, doc) {
        // Checkbox selection
        const checkbox = item.querySelector('.document-checkbox');
        checkbox.addEventListener('change', () => {
            if (checkbox.checked) {
                this.selectedDocuments.add(doc.id);
            } else {
                this.selectedDocuments.delete(doc.id);
            }
            this.updateBulkActions();
        });

        // View document
        item.querySelector('.view-document-btn')?.addEventListener('click', () => {
            this.viewDocument(doc);
        });

        // Delete document
        item.querySelector('.delete-document-btn')?.addEventListener('click', () => {
            this.confirmDeleteDocument(doc);
        });
    }

    setupDatasetItemListeners(item, dataset) {
        // Edit dataset
        item.querySelector('.edit-dataset-btn')?.addEventListener('click', () => {
            this.editDataset(dataset);
        });

        // Delete dataset
        item.querySelector('.delete-dataset-btn')?.addEventListener('click', () => {
            this.confirmDeleteDataset(dataset);
        });
    }