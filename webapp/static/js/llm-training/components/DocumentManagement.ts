/**
 * Document Management Component for LLM Training
 * Handles document listing, organization, datasets, and deletion
 */

import { Document, Dataset, ApiResponse, ErrorResponse, ErrorType } from '../types/index';

export interface DocumentManagementOptions {
  container: HTMLElement;
  apiBaseUrl?: string;
  onDocumentDeleted?: (documentId: string) => void;
  onDatasetCreated?: (dataset: Dataset) => void;
  onDatasetUpdated?: (dataset: Dataset) => void;
  onError?: (error: ErrorResponse) => void;
}

export default class DocumentManagement {
    private container: HTMLElement;
    private options: DocumentManagementOptions;
    private documents: Document[] = [];
    private datasets: Dataset[] = [];
    private selectedDocuments: Set<string> = new Set();
    private currentView: 'documents' | 'datasets' = 'documents';
    private loading: boolean = false;

    // DOM elements
    private viewToggle!: HTMLElement;
    private documentsList!: HTMLElement;
    private datasetsList!: HTMLElement;
    private searchInput!: HTMLInputElement;
    private filterSelect!: HTMLSelectElement;
    private bulkActions!: HTMLElement;
    private createDatasetBtn!: HTMLButtonElement;
    private refreshBtn!: HTMLButtonElement;

    constructor(options: DocumentManagementOptions) {
        this.container = options.container;
        this.options = { apiBaseUrl: '/api', ...options };
        
        this.render();
        this.setupEventListeners();
        this.loadDocuments();
        this.loadDatasets();
    }

    private render(): void {
        this.container.innerHTML = `
            <div class="document-management">
                <!-- Header with view toggle and actions -->
                <div class="flex items-center justify-between mb-6">
                    <div class="flex items-center space-x-4">
                        <h2 class="text-xl font-semibold text-gray-900">Document Management</h2>
                        <div class="view-toggle bg-gray-100 rounded-lg p-1">
                            <button type="button" class="view-btn active" data-view="documents">
                                Documents
                            </button>
                            <button type="button" class="view-btn" data-view="datasets">
                                Datasets
                            </button>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        <button type="button" class="refresh-btn px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
                            <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                            </svg>
                            Refresh
                        </button>
                        <button type="button" class="create-dataset-btn px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700">
                            Create Dataset
                        </button>
                    </div>
                </div>

                <!-- Search and filters -->
                <div class="flex items-center space-x-4 mb-4">
                    <div class="flex-1">
                        <input type="text" class="search-input w-full px-3 py-2 border border-gray-300 rounded-md placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="Search documents...">
                    </div>
                    <select class="filter-select px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                        <option value="">All Types</option>
                        <option value="pdf">PDF</option>
                        <option value="txt">Text</option>
                        <option value="docx">Word</option>
                        <option value="json">JSON</option>
                    </select>
                </div>

                <!-- Bulk actions (hidden by default) -->
                <div class="bulk-actions hidden bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                    <div class="flex items-center justify-between">
                        <span class="text-sm text-blue-700">
                            <span class="selected-count">0</span> documents selected
                        </span>
                        <div class="flex items-center space-x-2">
                            <button type="button" class="add-to-dataset-btn px-3 py-1 text-xs font-medium text-blue-700 bg-blue-100 rounded hover:bg-blue-200">
                                Add to Dataset
                            </button>
                            <button type="button" class="bulk-delete-btn px-3 py-1 text-xs font-medium text-red-700 bg-red-100 rounded hover:bg-red-200">
                                Delete Selected
                            </button>
                            <button type="button" class="clear-selection-btn px-3 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded hover:bg-gray-200">
                                Clear Selection
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Documents view -->
                <div class="documents-view">
                    <div class="documents-list space-y-3">
                        <!-- Documents will be rendered here -->
                    </div>
                </div>

                <!-- Datasets view (hidden by default) -->
                <div class="datasets-view hidden">
                    <div class="datasets-list space-y-3">
                        <!-- Datasets will be rendered here -->
                    </div>
                </div>

                <!-- Loading state -->
                <div class="loading-state hidden flex items-center justify-center py-12">
                    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <span class="ml-3 text-gray-600">Loading...</span>
                </div>

                <!-- Empty state -->
                <div class="empty-state hidden text-center py-12">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                    </svg>
                    <h3 class="mt-2 text-sm font-medium text-gray-900">No documents</h3>
                    <p class="mt-1 text-sm text-gray-500">Get started by uploading your first document.</p>
                </div>
            </div>
        `;

        // Get DOM element references
        this.viewToggle = this.container.querySelector('.view-toggle')!;
        this.documentsList = this.container.querySelector('.documents-list')!;
        this.datasetsList = this.container.querySelector('.datasets-list')!;
        this.searchInput = this.container.querySelector('.search-input') as HTMLInputElement;
        this.filterSelect = this.container.querySelector('.filter-select') as HTMLSelectElement;
        this.bulkActions = this.container.querySelector('.bulk-actions')!;
        this.createDatasetBtn = this.container.querySelector('.create-dataset-btn') as HTMLButtonElement;
        this.refreshBtn = this.container.querySelector('.refresh-btn') as HTMLButtonElement;
    } 
   private setupEventListeners(): void {
        // View toggle
        this.viewToggle.addEventListener('click', (e) => {
            const target = e.target as HTMLElement;
            if (target.classList.contains('view-btn')) {
                this.switchView(target.dataset.view as 'documents' | 'datasets');
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

    private switchView(view: 'documents' | 'datasets'): void {
        this.currentView = view;

        // Update toggle buttons
        this.viewToggle.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        this.viewToggle.querySelector(`[data-view="${view}"]`)?.classList.add('active');

        // Show/hide views
        const documentsView = this.container.querySelector('.documents-view')!;
        const datasetsView = this.container.querySelector('.datasets-view')!;

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
    private async loadDocuments(): Promise<void> {
        try {
            this.showLoading();
            const response = await fetch(`${this.options.apiBaseUrl}/documents`);
            const result: ApiResponse<Document[]> = await response.json();

            if (result.success && result.data) {
                this.documents = result.data;
                if (this.currentView === 'documents') {
                    this.renderDocuments();
                }
            } else {
                this.handleError(result.error || { type: ErrorType.API_ERROR, message: 'Failed to load documents' });
            }
        } catch (error) {
            this.handleError({ type: ErrorType.NETWORK_ERROR, message: 'Network error loading documents' });
        } finally {
            this.hideLoading();
        }
    }

    private async loadDatasets(): Promise<void> {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/documents/datasets`);
            const result: ApiResponse<Dataset[]> = await response.json();

            if (result.success && result.data) {
                this.datasets = result.data;
                if (this.currentView === 'datasets') {
                    this.renderDatasets();
                }
            } else {
                this.handleError(result.error || { type: ErrorType.API_ERROR, message: 'Failed to load datasets' });
            }
        } catch (error) {
            this.handleError({ type: ErrorType.NETWORK_ERROR, message: 'Network error loading datasets' });
        }
    }

    private async deleteDocument(documentId: string): Promise<void> {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/documents/${documentId}`, {
                method: 'DELETE'
            });
            const result: ApiResponse = await response.json();

            if (result.success) {
                this.documents = this.documents.filter(doc => doc.id !== documentId);
                this.renderDocuments();
                this.showSuccess('Document deleted successfully');
                this.options.onDocumentDeleted?.(documentId);
            } else {
                this.handleError(result.error || { type: ErrorType.API_ERROR, message: 'Failed to delete document' });
            }
        } catch (error) {
            this.handleError({ type: ErrorType.NETWORK_ERROR, message: 'Network error deleting document' });
        }
    }

    private async createDataset(name: string, description: string): Promise<void> {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/documents/datasets`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, description })
            });
            const result: ApiResponse<Dataset> = await response.json();

            if (result.success && result.data) {
                this.datasets.push(result.data);
                this.showSuccess('Dataset created successfully');
                this.options.onDatasetCreated?.(result.data);
            } else {
                this.handleError(result.error || { type: ErrorType.API_ERROR, message: 'Failed to create dataset' });
            }
        } catch (error) {
            this.handleError({ type: ErrorType.NETWORK_ERROR, message: 'Network error creating dataset' });
        }
    }

    private async addDocumentsToDataset(documentIds: string[], datasetId: string): Promise<void> {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/documents/datasets/${datasetId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ documentIds })
            });
            const result: ApiResponse<Dataset> = await response.json();

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
                this.handleError(result.error || { type: ErrorType.API_ERROR, message: 'Failed to add documents to dataset' });
            }
        } catch (error) {
            this.handleError({ type: ErrorType.NETWORK_ERROR, message: 'Network error adding documents to dataset' });
        }
    }

    // Rendering Methods
    private renderDocuments(): void {
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
            this.setupDocumentItemListeners(item as HTMLElement, doc);
        });
    }

    private renderDocumentItem(doc: Document): string {
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
                                ${this.formatFileSize(doc.size)} • ${doc.metadata.wordCount} words • ${this.formatDate(doc.metadata.uploadDate)}
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

    private renderDatasets(): void {
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
            this.setupDatasetItemListeners(item as HTMLElement, dataset);
        });
    }

    private renderDatasetItem(dataset: Dataset): string {
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
                            <span>${dataset.statistics.totalDocuments} documents</span>
                            <span>${dataset.statistics.totalWords.toLocaleString()} words</span>
                            <span>${this.formatFileSize(dataset.statistics.totalSize)}</span>
                            <span>Created ${this.formatDate(dataset.createdAt)}</span>
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

    private setupDocumentItemListeners(item: HTMLElement, doc: Document): void {
        // Checkbox selection
        const checkbox = item.querySelector('.document-checkbox') as HTMLInputElement;
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

    private setupDatasetItemListeners(item: HTMLElement, dataset: Dataset): void {
        // Edit dataset
        item.querySelector('.edit-dataset-btn')?.addEventListener('click', () => {
            this.editDataset(dataset);
        });

        // Delete dataset
        item.querySelector('.delete-dataset-btn')?.addEventListener('click', () => {
            this.confirmDeleteDataset(dataset);
        });
    }

    // Utility Methods
    private getFilteredDocuments(): Document[] {
        const searchTerm = this.searchInput.value.toLowerCase();
        const typeFilter = this.filterSelect.value;

        return this.documents.filter(doc => {
            const matchesSearch = !searchTerm || 
                doc.name.toLowerCase().includes(searchTerm) ||
                doc.originalName.toLowerCase().includes(searchTerm);
            
            const matchesType = !typeFilter || doc.type === typeFilter;

            return matchesSearch && matchesType;
        });
    }

    private filterDocuments(): void {
        this.renderDocuments();
    }

    private updateBulkActions(): void {
        const selectedCount = this.selectedDocuments.size;
        const countSpan = this.bulkActions.querySelector('.selected-count')!;
        countSpan.textContent = selectedCount.toString();

        if (selectedCount > 0) {
            this.bulkActions.classList.remove('hidden');
        } else {
            this.bulkActions.classList.add('hidden');
        }
    }

    private clearSelection(): void {
        this.selectedDocuments.clear();
        this.documentsList.querySelectorAll('.document-checkbox').forEach(checkbox => {
            (checkbox as HTMLInputElement).checked = false;
        });
        this.updateBulkActions();
    }    
// Modal Methods
    private showCreateDatasetModal(): void {
        // Create modal dynamically
        const modal = document.createElement('div');
        modal.className = 'create-dataset-modal fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50';
        modal.innerHTML = `
            <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
                <div class="mt-3">
                    <h3 class="text-lg font-medium text-gray-900 mb-4">Create New Dataset</h3>
                    <form class="dataset-form">
                        <div class="mb-4">
                            <label class="block text-sm font-medium text-gray-700 mb-2">Dataset Name</label>
                            <input type="text" name="name" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500" required>
                        </div>
                        <div class="mb-4">
                            <label class="block text-sm font-medium text-gray-700 mb-2">Description</label>
                            <textarea name="description" rows="3" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"></textarea>
                        </div>
                        <div class="flex justify-end space-x-3">
                            <button type="button" class="cancel-dataset-btn px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200">
                                Cancel
                            </button>
                            <button type="submit" class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700">
                                Create Dataset
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Setup event listeners
        const form = modal.querySelector('.dataset-form') as HTMLFormElement;
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const name = formData.get('name') as string;
            const description = formData.get('description') as string;

            if (!name.trim()) {
                this.showError('Dataset name is required');
                return;
            }

            await this.createDataset(name.trim(), description.trim());
            document.body.removeChild(modal);
        });

        modal.querySelector('.cancel-dataset-btn')?.addEventListener('click', () => {
            document.body.removeChild(modal);
        });

        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });

        // Focus on name input
        const nameInput = modal.querySelector('input[name="name"]') as HTMLInputElement;
        setTimeout(() => nameInput.focus(), 100);
    }

    private showAddToDatasetModal(): void {
        if (this.selectedDocuments.size === 0) {
            this.showError('Please select documents to add to a dataset');
            return;
        }

        // Create modal dynamically
        const modal = document.createElement('div');
        modal.className = 'add-to-dataset-modal fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50';
        modal.innerHTML = `
            <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
                <div class="mt-3">
                    <h3 class="text-lg font-medium text-gray-900 mb-4">Add to Dataset</h3>
                    <form class="add-to-dataset-form">
                        <div class="mb-4">
                            <label class="block text-sm font-medium text-gray-700 mb-2">Select Dataset</label>
                            <select name="datasetId" class="dataset-select w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500" required>
                                <option value="">Choose a dataset...</option>
                                ${this.datasets.map(dataset => `<option value="${dataset.id}">${dataset.name}</option>`).join('')}
                            </select>
                        </div>
                        <div class="flex justify-end space-x-3">
                            <button type="button" class="cancel-add-dataset-btn px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200">
                                Cancel
                            </button>
                            <button type="submit" class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700">
                                Add to Dataset
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Setup event listeners
        const form = modal.querySelector('.add-to-dataset-form') as HTMLFormElement;
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const datasetId = formData.get('datasetId') as string;

            if (!datasetId) {
                this.showError('Please select a dataset');
                return;
            }

            const documentIds = Array.from(this.selectedDocuments);
            await this.addDocumentsToDataset(documentIds, datasetId);
            document.body.removeChild(modal);
            this.clearSelection();
        });

        modal.querySelector('.cancel-add-dataset-btn')?.addEventListener('click', () => {
            document.body.removeChild(modal);
        });

        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }

    // Action Methods
    private viewDocument(doc: Document): void {
        // Create a simple document viewer modal
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50';
        modal.innerHTML = `
            <div class="relative top-20 mx-auto p-5 border w-3/4 max-w-4xl shadow-lg rounded-md bg-white">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-medium text-gray-900">${doc.name}</h3>
                    <button type="button" class="close-viewer text-gray-400 hover:text-gray-600">
                        <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
                <div class="max-h-96 overflow-y-auto bg-gray-50 p-4 rounded">
                    <pre class="whitespace-pre-wrap text-sm">${this.escapeHtml(doc.content.substring(0, 5000))}${doc.content.length > 5000 ? '...' : ''}</pre>
                </div>
                <div class="mt-4 text-sm text-gray-500">
                    <p>Size: ${this.formatFileSize(doc.size)} • Words: ${doc.metadata.wordCount} • Uploaded: ${this.formatDate(doc.metadata.uploadDate)}</p>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close modal handlers
        const closeBtn = modal.querySelector('.close-viewer')!;
        const closeModal = () => {
            document.body.removeChild(modal);
        };

        closeBtn.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });
    }

    private confirmDeleteDocument(doc: Document): void {
        if (confirm(`Are you sure you want to delete "${doc.name}"? This action cannot be undone.`)) {
            this.deleteDocument(doc.id);
        }
    }

    private async bulkDeleteDocuments(): Promise<void> {
        const count = this.selectedDocuments.size;
        if (count === 0) return;

        if (confirm(`Are you sure you want to delete ${count} document${count > 1 ? 's' : ''}? This action cannot be undone.`)) {
            const promises = Array.from(this.selectedDocuments).map(id => this.deleteDocument(id));
            await Promise.all(promises);
            this.clearSelection();
        }
    }

    private editDataset(dataset: Dataset): void {
        // For now, just show an alert. In a full implementation, this would open an edit modal
        alert(`Edit dataset functionality would be implemented here for: ${dataset.name}`);
    }

    private confirmDeleteDataset(dataset: Dataset): void {
        if (confirm(`Are you sure you want to delete the dataset "${dataset.name}"? This will not delete the documents, only the dataset organization.`)) {
            this.deleteDataset(dataset.id);
        }
    }

    private async deleteDataset(datasetId: string): Promise<void> {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/documents/datasets/${datasetId}`, {
                method: 'DELETE'
            });
            const result: ApiResponse = await response.json();

            if (result.success) {
                this.datasets = this.datasets.filter(d => d.id !== datasetId);
                
                // Remove dataset reference from documents
                this.documents.forEach(doc => {
                    doc.datasets = doc.datasets.filter(id => id !== datasetId);
                });

                this.renderDatasets();
                this.showSuccess('Dataset deleted successfully');
            } else {
                this.handleError(result.error || { type: ErrorType.API_ERROR, message: 'Failed to delete dataset' });
            }
        } catch (error) {
            this.handleError({ type: ErrorType.NETWORK_ERROR, message: 'Network error deleting dataset' });
        }
    }

    // UI State Methods
    private showLoading(): void {
        this.loading = true;
        this.container.querySelector('.loading-state')?.classList.remove('hidden');
        this.container.querySelector('.documents-view')?.classList.add('hidden');
        this.container.querySelector('.datasets-view')?.classList.add('hidden');
    }

    private hideLoading(): void {
        this.loading = false;
        this.container.querySelector('.loading-state')?.classList.add('hidden');
        
        if (this.currentView === 'documents') {
            this.container.querySelector('.documents-view')?.classList.remove('hidden');
        } else {
            this.container.querySelector('.datasets-view')?.classList.remove('hidden');
        }
    }

    private showEmptyState(): void {
        this.container.querySelector('.empty-state')?.classList.remove('hidden');
        this.documentsList.innerHTML = '';
    }

    private hideEmptyState(): void {
        this.container.querySelector('.empty-state')?.classList.add('hidden');
    }

    // Utility Methods
    private getFileIcon(doc: Document): string {
        const iconClass = 'h-5 w-5';
        const extension = doc.name.split('.').pop()?.toLowerCase();
        
        const icons = {
            pdf: `<svg class="${iconClass} text-red-500" fill="currentColor" viewBox="0 0 24 24"><path d="M7 2a2 2 0 00-2 2v16a2 2 0 002 2h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7z"/></svg>`,
            txt: `<svg class="${iconClass} text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>`,
            docx: `<svg class="${iconClass} text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>`,
            json: `<svg class="${iconClass} text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>`
        };

        return icons[extension as keyof typeof icons] || icons.txt;
    }

    private getStatusColor(status: string): string {
        const colors = {
            pending: 'bg-gray-100 text-gray-800',
            processing: 'bg-blue-100 text-blue-800',
            ready: 'bg-green-100 text-green-800',
            error: 'bg-red-100 text-red-800'
        };
        return colors[status as keyof typeof colors] || colors.pending;
    }

    private getStatusText(status: string): string {
        const texts = {
            pending: 'Pending',
            processing: 'Processing',
            ready: 'Ready',
            error: 'Error'
        };
        return texts[status as keyof typeof texts] || 'Unknown';
    }

    private formatFileSize(bytes: number): string {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    private formatDate(date: Date | string): string {
        const d = new Date(date);
        return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    private escapeHtml(text: string): string {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Notification Methods
    private showSuccess(message: string): void {
        this.showNotification(message, 'success');
    }

    private showError(message: string): void {
        this.showNotification(message, 'error');
    }

    private showNotification(message: string, type: 'success' | 'error'): void {
        const bgColor = type === 'error' ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200';
        const textColor = type === 'error' ? 'text-red-800' : 'text-green-800';
        const iconColor = type === 'error' ? 'text-red-400' : 'text-green-400';

        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 max-w-sm w-full ${bgColor} border rounded-lg p-4 shadow-lg z-50`;
        notification.innerHTML = `
            <div class="flex">
                <div class="flex-shrink-0">
                    <svg class="h-5 w-5 ${iconColor}" fill="currentColor" viewBox="0 0 20 20">
                        ${type === 'error' ? 
                            '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>' :
                            '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>'
                        }
                    </svg>
                </div>
                <div class="ml-3">
                    <p class="text-sm font-medium ${textColor}">${this.escapeHtml(message)}</p>
                </div>
                <div class="ml-auto pl-3">
                    <button type="button" class="close-notification inline-flex text-gray-400 hover:text-gray-600">
                        <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);

        // Close button
        notification.querySelector('.close-notification')?.addEventListener('click', () => {
            notification.remove();
        });
    }

    private handleError(error: ErrorResponse): void {
        console.error('Document management error:', error);
        this.showError(error.message);
        this.options.onError?.(error);
    }

    // Public API
    public refresh(): void {
        this.loadDocuments();
        this.loadDatasets();
    }

    public getSelectedDocuments(): string[] {
        return Array.from(this.selectedDocuments);
    }

    public selectDocument(documentId: string): void {
        this.selectedDocuments.add(documentId);
        const checkbox = this.documentsList.querySelector(`[data-document-id="${documentId}"] .document-checkbox`) as HTMLInputElement;
        if (checkbox) {
            checkbox.checked = true;
        }
        this.updateBulkActions();
    }

    public deselectDocument(documentId: string): void {
        this.selectedDocuments.delete(documentId);
        const checkbox = this.documentsList.querySelector(`[data-document-id="${documentId}"] .document-checkbox`) as HTMLInputElement;
        if (checkbox) {
            checkbox.checked = false;
        }
        this.updateBulkActions();
    }

    public destroy(): void {
        // Clean up event listeners and remove DOM elements
        this.container.innerHTML = '';
    }
}