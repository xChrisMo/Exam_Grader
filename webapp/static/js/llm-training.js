/**
 * LLM Training Page JavaScript
 * 
 * Handles all frontend functionality for the LLM training and fine-tuning interface.
 */

class DocumentManager {
    constructor() {
        this.documents = [];
        this.datasets = [];
        this.trainingJobs = [];
        this.reports = [];
        this.modelTests = [];
        this.currentDataset = 'all';
        this.currentTestId = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.setupFileUpload();
    }
    
    // Clear all data and reset to clean state
    clearAllData() {
        this.documents = [];
        this.datasets = [];
        this.trainingJobs = [];
        this.reports = [];
        this.currentDataset = 'all';
        
        // Update UI
        this.renderDocuments();
        this.renderTrainingJobs();
        this.renderReports();
        this.updateDatasetTabs();
        this.updateStats({
            datasets: { total_documents: 0, total_datasets: 0, total_words: 0, total_size_mb: 0 },
            training: { total_jobs: 0, running_jobs: 0, completed_jobs: 0, failed_jobs: 0 }
        });
    }
    
    // Clean up all mock/test data from the system
    async cleanupAllData() {
        try {
            this.showLoading('Cleaning up data...');
            
            // Delete all training jobs first (to avoid foreign key constraints)
            for (const job of this.trainingJobs) {
                try {
                    await fetch(`/llm-training/api/training-jobs/${job.id}`, {
                        method: 'DELETE',
                        headers: { 'X-CSRFToken': this.getCSRFToken() }
                    });
                } catch (error) {
                    console.warn(`Failed to delete training job ${job.id}:`, error);
                }
            }
            
            // Delete all datasets
            for (const dataset of this.datasets) {
                try {
                    await fetch(`/llm-training/api/datasets/${dataset.id}`, {
                        method: 'DELETE',
                        headers: { 'X-CSRFToken': this.getCSRFToken() }
                    });
                } catch (error) {
                    console.warn(`Failed to delete dataset ${dataset.id}:`, error);
                }
            }
            
            // Delete all documents
            for (const doc of this.documents) {
                try {
                    await fetch(`/llm-training/api/documents/${doc.id}`, {
                        method: 'DELETE',
                        headers: { 'X-CSRFToken': this.getCSRFToken() }
                    });
                } catch (error) {
                    console.warn(`Failed to delete document ${doc.id}:`, error);
                }
            }
            
            // Delete all reports
            for (const report of this.reports) {
                try {
                    await fetch(`/llm-training/api/reports/${report.id}`, {
                        method: 'DELETE',
                        headers: { 'X-CSRFToken': this.getCSRFToken() }
                    });
                } catch (error) {
                    console.warn(`Failed to delete report ${report.id}:`, error);
                }
            }
            
            // Clear local data and refresh
            this.clearAllData();
            await this.loadInitialData();
            
            this.showSuccess('All data cleaned up successfully');
            
        } catch (error) {
            console.error('Error during cleanup:', error);
            this.showError('Failed to clean up all data: ' + (error.message || 'Unknown error'));
        } finally {
            this.hideLoading();
        }
    }
    
    setupEventListeners() {
        // Dataset tab switching
        document.querySelectorAll('.dataset-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchDataset(e.target.dataset.dataset);
            });
        });
        
        // Form submissions
        const createDatasetForm = document.getElementById('create-dataset-form');
        if (createDatasetForm) {
            createDatasetForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createDataset();
            });
        }
        
        const createTrainingForm = document.getElementById('create-training-form');
        if (createTrainingForm) {
            createTrainingForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createTrainingJob();
            });
        }
        
        const generateReportForm = document.getElementById('generate-report-form');
        if (generateReportForm) {
            generateReportForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.generateReport();
            });
        }
        
        const editDocumentForm = document.getElementById('edit-document-form');
        if (editDocumentForm) {
            editDocumentForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.updateDocument();
            });
        }
        
        // Auto-refresh training jobs every 5 seconds
        setInterval(() => {
            this.refreshTrainingJobs();
        }, 5000);
    }
    
    setupFileUpload() {
        const fileInput = document.getElementById('file-input');
        const uploadArea = document.getElementById('upload-area');
        
        if (!fileInput || !uploadArea) return;
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#3b82f6';
            uploadArea.style.backgroundColor = '#f0f9ff';
        });
        
        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#d1d5db';
            uploadArea.style.backgroundColor = 'transparent';
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#d1d5db';
            uploadArea.style.backgroundColor = 'transparent';
            
            const files = Array.from(e.dataTransfer.files);
            this.handleFileUpload(files);
        });
        
        // File input change
        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            this.handleFileUpload(files);
        });
    }
    
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadDocuments(),
                this.loadDatasets(),
                this.loadTrainingJobs(),
                this.loadReports(),
                this.loadStats()
            ]);
            
            this.renderDocuments();
            this.renderTrainingJobs();
            this.renderReports();
            
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load data. Please refresh the page.');
        }
    }
    
async loadDocuments() {
        try {
            const response = await fetch('/llm-training/api/documents', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                if (response.status === 404) {
                    console.warn('Documents endpoint not found, using empty array');
                    this.documents = [];
                    return;
                } else if (response.status >= 500) {
                    throw new Error('Server error occurred while loading documents');
                } else {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Transform API response to match expected format with better validation
                this.documents = (data.documents || []).map(doc => {
                    // Validate required fields
                    if (!doc.id || !doc.name) {
                        console.warn('Invalid document data:', doc);
                        return null;
                    }
                    
                    return {
                        id: doc.id,
                        name: doc.name || 'Unnamed Document',
                        size: parseInt(doc.file_size || doc.size || 0),
                        type: (doc.file_type || doc.type || 'unknown').toLowerCase(),
                        dataset: doc.datasets && doc.datasets.length > 0 ? doc.datasets[0] : null,
                        uploaded_at: doc.created_at || doc.uploaded_at || new Date().toISOString(),
                        word_count: parseInt(doc.word_count || 0)
                    };
                }).filter(doc => doc !== null); // Remove invalid documents
            } else {
                console.error('Failed to load documents:', data.error);
                this.documents = [];
                if (data.error && !data.error.includes('not found')) {
                    this.showError(data.error || 'Failed to load documents');
                }
            }
        } catch (error) {
            console.error('Error loading documents:', error);
            this.documents = [];
            if (error.message && !error.message.includes('not found')) {
                this.showError('Failed to load documents. Please check your connection.');
            }
        }
    }
    
    async loadDatasets() {
        try {
            const response = await fetch('/llm-training/api/datasets', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                if (response.status === 404) {
                    console.warn('Datasets endpoint not found, using empty array');
                    this.datasets = [];
                    this.updateDatasetTabs();
                    return;
                } else if (response.status >= 500) {
                    throw new Error('Server error occurred while loading datasets');
                } else {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.datasets = data.datasets || [];
                this.updateDatasetTabs();
            } else {
                console.error('Failed to load datasets:', data.error);
                this.datasets = [];
                if (data.error && !data.error.includes('not found')) {
                    this.showError(data.error || 'Failed to load datasets');
                }
                this.updateDatasetTabs();
            }
        } catch (error) {
            console.error('Error loading datasets:', error);
            this.datasets = [];
            if (error.message && !error.message.includes('not found')) {
                this.showError('Failed to load datasets. Please check your connection.');
            }
            this.updateDatasetTabs();
        }
    }
    
    async loadTrainingJobs() {
        try {
            const response = await fetch('/llm-training/api/training-jobs', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                if (response.status === 404) {
                    console.warn('Training jobs endpoint not found, using empty array');
                    this.trainingJobs = [];
                    return;
                } else if (response.status >= 500) {
                    throw new Error('Server error occurred while loading training jobs');
                } else {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.trainingJobs = data.jobs || [];
            } else {
                console.error('Failed to load training jobs:', data.error);
                this.trainingJobs = [];
                if (data.error && !data.error.includes('not found')) {
                    this.showError(data.error || 'Failed to load training jobs');
                }
            }
        } catch (error) {
            console.error('Error loading training jobs:', error);
            this.trainingJobs = [];
            if (error.message && !error.message.includes('not found')) {
                this.showError('Failed to load training jobs. Please check your connection.');
            }
        }
    }
    
    async loadReports() {
        try {
            const response = await fetch('/llm-training/api/reports');
            const data = await response.json();
            
            if (data.success) {
                this.reports = data.reports;
            }
        } catch (error) {
            console.error('Error loading reports:', error);
        }
    }
    
    async loadStats() {
        try {
            const response = await fetch('/llm-training/api/stats');
            const data = await response.json();
            
            if (data.success) {
                this.updateStats(data.stats);
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }
    
    updateStats(stats) {
        // Safely update document stats
        const docStats = stats.datasets || {};
        this.safeUpdateElement('total-documents', docStats.total_documents || 0);
        this.safeUpdateElement('total-datasets', docStats.total_datasets || 0);
        this.safeUpdateElement('total-words', this.formatNumber(docStats.total_words || 0));
        this.safeUpdateElement('total-size', `${docStats.total_size_mb || 0} MB`);
        
        // Safely update training stats
        const trainingStats = stats.training || {};
        this.safeUpdateElement('total-jobs', trainingStats.total_jobs || 0);
        this.safeUpdateElement('running-jobs', trainingStats.running_jobs || 0);
        this.safeUpdateElement('completed-jobs', trainingStats.completed_jobs || 0);
        this.safeUpdateElement('failed-jobs', trainingStats.failed_jobs || 0);
    }
    
    safeUpdateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        } else {
            console.warn(`Element with ID '${id}' not found`);
        }
    }
    
    updateDatasetTabs() {
        const tabsContainer = document.getElementById('dataset-tabs');
        if (!tabsContainer) return;
        
        // Clear existing tabs except "All Documents" and "Unassigned"
        const existingTabs = tabsContainer.querySelectorAll('.dataset-tab');
        existingTabs.forEach(tab => {
            if (!['all', 'unassigned'].includes(tab.dataset.dataset)) {
                tab.remove();
            }
        });
        
        // Add dataset tabs
        this.datasets.forEach(dataset => {
            const tab = document.createElement('button');
            tab.className = 'dataset-tab';
            tab.dataset.dataset = dataset.id;
            tab.textContent = dataset.name;
            tab.addEventListener('click', (e) => {
                this.switchDataset(e.target.dataset.dataset);
            });
            tabsContainer.appendChild(tab);
        });
    }
    
    switchDataset(datasetId) {
        this.currentDataset = datasetId;
        
        // Update active tab
        document.querySelectorAll('.dataset-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.dataset === datasetId);
        });
        
        this.renderDocuments();
    }
    
    renderDocuments() {
        const container = document.getElementById('document-grid');
        const emptyState = document.getElementById('empty-state');
        
        if (!container) return;
        
        // Filter documents based on current dataset
        let filteredDocuments = this.documents;
        if (this.currentDataset !== 'all') {
            if (this.currentDataset === 'unassigned') {
                filteredDocuments = this.documents.filter(doc => !doc.dataset);
            } else {
                filteredDocuments = this.documents.filter(doc => doc.dataset === this.currentDataset);
            }
        }
        
        if (filteredDocuments.length === 0) {
            if (container) container.style.display = 'none';
            if (emptyState) emptyState.style.display = 'block';
            return;
        }
        
        if (container) container.style.display = 'grid';
        if (emptyState) emptyState.style.display = 'none';
        
        container.innerHTML = filteredDocuments.map(doc => this.renderDocumentCard(doc)).join('');
    }
    
    renderDocumentCard(doc) {
        const sizeFormatted = this.formatFileSize(doc.size);
        const dateFormatted = new Date(doc.uploaded_at).toLocaleDateString();
        const datasetName = doc.dataset ? 
            (this.datasets.find(d => d.id === doc.dataset)?.name || 'Unknown Dataset') : 
            'Unassigned';
        
        return `
            <div class="document-card">
                <div class="document-header">
                    <div class="document-name">${doc.name}</div>
                    <div class="document-actions">
                        <button class="btn btn-sm btn-secondary" onclick="documentManager.editDocument('${doc.id}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="documentManager.deleteDocument('${doc.id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="document-meta">
                    ${sizeFormatted} • ${doc.word_count} words • ${dateFormatted}
                </div>
                <div class="document-tags">
                    <span class="tag">${doc.type.toUpperCase()}</span>
                    <span class="tag">${datasetName}</span>
                </div>
            </div>
        `;
    }
    
    renderTrainingJobs() {
        const container = document.getElementById('training-jobs-container');
        const emptyState = document.getElementById('training-empty-state');
        
        if (!container) return;
        
        if (this.trainingJobs.length === 0) {
            if (emptyState) {
                emptyState.style.display = 'block';
            }
            return;
        }
        
        if (emptyState) {
            emptyState.style.display = 'none';
        }
        
        const jobsHtml = this.trainingJobs.map(job => this.renderTrainingJob(job)).join('');
        container.innerHTML = jobsHtml;
    }
    
    renderTrainingJob(job) {
        const progress = job.progress || 0;
        const statusClass = `status-${job.status}`;
        
        // Handle date formatting more safely
        let createdAt = 'Unknown';
        try {
            if (job.created_at) {
                createdAt = new Date(job.created_at).toLocaleDateString();
            }
        } catch (e) {
            console.warn('Invalid date format for job:', job.id);
        }
        
        return `
            <div class="training-job">
                <div class="job-header">
                    <div class="job-name">${job.name || 'Unnamed Job'}</div>
                    <span class="job-status ${statusClass}">${job.status || 'unknown'}</span>
                </div>
                <div class="job-meta">
                    <div>Model: ${job.model_id || 'Not specified'}</div>
                    <div>Created: ${createdAt}</div>
                    <div>Progress: ${progress}%</div>
                    ${job.current_epoch && job.total_epochs ? `<div>Epoch: ${job.current_epoch}/${job.total_epochs}</div>` : ''}
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                <div class="job-actions">
                    ${job.status === 'pending' || job.status === 'failed' || job.status === 'cancelled' ? 
                        `<button class="btn btn-sm btn-primary" onclick="documentManager.startTrainingJob('${job.id}')">Start</button>` : ''}
                    ${job.status === 'training' || job.status === 'preparing' ? 
                        `<button class="btn btn-sm btn-danger" onclick="documentManager.cancelTrainingJob('${job.id}')">Cancel</button>` : ''}
                    <button class="btn btn-sm btn-secondary" onclick="documentManager.showJobDetails('${job.id}')">Details</button>
                    ${job.status !== 'training' && job.status !== 'preparing' ? 
                        `<button class="btn btn-sm btn-danger" onclick="documentManager.deleteTrainingJob('${job.id}', '${(job.name || 'this job').replace(/'/g, '\\\'')}')" title="Delete this training job">Delete</button>` : ''}
                </div>
            </div>
        `;
    }
    
    renderReports() {
        const container = document.getElementById('reports-container');
        const emptyState = document.getElementById('reports-empty-state');
        
        if (!container) return;
        
        if (this.reports.length === 0) {
            if (emptyState) emptyState.style.display = 'block';
            return;
        }
        
        if (emptyState) emptyState.style.display = 'none';
        
        const reportsHtml = this.reports.map(report => this.renderReport(report)).join('');
        container.innerHTML = reportsHtml;
    }
    
    renderReport(report) {
        const createdAt = new Date(report.created_at).toLocaleDateString();
        
        return `
            <div class="report-item">
                <div class="report-info">
                    <h4>${report.name}</h4>
                    <p>Created: ${createdAt} • Format: ${report.format.toUpperCase()} • Status: ${report.status}</p>
                </div>
                <div class="report-actions">
                    ${report.status === 'completed' ? 
                        `<button class="btn btn-sm btn-primary" onclick="documentManager.downloadReport('${report.id}')">Download</button>` : ''}
                    <button class="btn btn-sm btn-danger" onclick="documentManager.deleteReport('${report.id}')">Delete</button>
                </div>
            </div>
        `;
    }
    
    async handleFileUpload(files) {
        const uploadProgress = document.getElementById('upload-progress');
        const uploadBar = document.getElementById('upload-bar');
        const uploadPercentage = document.getElementById('upload-percentage');
        
        // Validate files first
        if (!files || files.length === 0) {
            this.showError('No files selected for upload.');
            return;
        }
        
        // Show progress indicators
        if (uploadProgress) uploadProgress.style.display = 'block';
        if (uploadBar) uploadBar.style.width = '0%';
        if (uploadPercentage) uploadPercentage.textContent = '0%';
        
        let progressInterval;
        
        try {
            // Create FormData for file upload
            const formData = new FormData();
            let validFileCount = 0;
            
            for (let file of files) {
                // Validate file size (100MB limit)
                if (file.size > 100 * 1024 * 1024) {
                    this.showError(`File ${file.name} is too large. Maximum size is 100MB.`);
                    continue;
                }
                
                // Validate file type
                const allowedTypes = ['.pdf', '.txt', '.docx', '.doc', '.json', '.md'];
                const fileExt = '.' + file.name.split('.').pop().toLowerCase();
                if (!allowedTypes.includes(fileExt)) {
                    this.showError(`File ${file.name} has unsupported format. Allowed: ${allowedTypes.join(', ')}`);
                    continue;
                }
                
                formData.append('files', file);
                validFileCount++;
            }
            
            if (validFileCount === 0) {
                if (uploadProgress) uploadProgress.style.display = 'none';
                this.showError('No valid files to upload.');
                return;
            }
            
            // Simulate progress during upload
            progressInterval = setInterval(() => {
                if (uploadBar && uploadPercentage) {
                    const currentWidth = parseFloat(uploadBar.style.width) || 0;
                    if (currentWidth < 90) {
                        const newWidth = Math.min(currentWidth + Math.random() * 10, 90);
                        uploadBar.style.width = `${newWidth}%`;
                        uploadPercentage.textContent = `${Math.round(newWidth)}%`;
                    }
                }
            }, 200);
            
            // Upload files to server
            const response = await fetch('/llm-training/api/documents/upload', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: formData
            });
            
            // Clear progress interval
            if (progressInterval) {
                clearInterval(progressInterval);
            }
            
            // Complete progress bar
            if (uploadBar && uploadPercentage) {
                uploadBar.style.width = '100%';
                uploadPercentage.textContent = '100%';
            }
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Transform uploaded documents to match expected format
                const newDocuments = (data.documents || []).map(doc => {
                    // Handle different API response formats
                    return {
                        id: doc.id,
                        name: doc.name || doc.original_name || 'Unnamed Document',
                        size: parseInt(doc.file_size || doc.size || 0),
                        type: (doc.file_type || doc.type || 'unknown').toLowerCase(),
                        dataset: doc.datasets && doc.datasets.length > 0 ? doc.datasets[0] : null,
                        uploaded_at: doc.created_at || doc.uploaded_at || new Date().toISOString(),
                        word_count: parseInt(doc.word_count || 0)
                    };
                }).filter(doc => doc.id); // Only add documents with valid IDs
                
                // Add to local documents array
                this.documents.push(...newDocuments);
                
                // Hide progress and update UI
                setTimeout(() => {
                    if (uploadProgress) uploadProgress.style.display = 'none';
                    this.renderDocuments();
                    this.loadStats(); // Refresh stats
                    
                    // Close modal and reset form
                    this.hideUploadModal();
                    
                    const successCount = newDocuments.length;
                    const failedCount = validFileCount - successCount;
                    
                    if (successCount > 0) {
                        this.showSuccess(`Successfully uploaded ${successCount} file(s)${failedCount > 0 ? ` (${failedCount} failed)` : ''}`);
                    } else {
                        this.showError('No files were successfully uploaded.');
                    }
                }, 500);
                
            } else {
                if (uploadProgress) uploadProgress.style.display = 'none';
                this.showError(data.error || 'Upload failed - server responded with error');
            }
            
        } catch (error) {
            console.error('Error uploading files:', error);
            
            // Clear progress interval
            if (progressInterval) {
                clearInterval(progressInterval);
            }
            
            if (uploadProgress) uploadProgress.style.display = 'none';
            
            // Show more specific error messages
            let errorMessage = 'Upload failed. ';
            if (error.message.includes('413')) {
                errorMessage += 'File size too large.';
            } else if (error.message.includes('415')) {
                errorMessage += 'Unsupported file type.';
            } else if (error.message.includes('network') || error.message.includes('fetch')) {
                errorMessage += 'Network error. Please check your connection.';
            } else {
                errorMessage += error.message || 'Please try again.';
            }
            
            this.showError(errorMessage);
        }
    }
    
    async createDataset() {
        const name = document.getElementById('dataset-name').value;
        const description = document.getElementById('dataset-description').value;
        const selectedDocs = Array.from(document.querySelectorAll('#document-selection input:checked'))
            .map(cb => cb.value);
        
        try {
            const response = await fetch('/llm-training/api/datasets', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    name,
                    description,
                    document_ids: selectedDocs
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.datasets.push(data.dataset);
                this.updateDatasetTabs();
                this.hideCreateDatasetModal();
                this.showSuccess('Dataset created successfully');
            } else {
                this.showError(data.error || 'Failed to create dataset');
            }
        } catch (error) {
            console.error('Error creating dataset:', error);
            this.showError('Failed to create dataset');
        }
    }
    
    async createTrainingJob() {
        const formData = {
            name: document.getElementById('training-name').value,
            model: document.getElementById('training-model').value,
            dataset_id: document.getElementById('training-dataset').value,
            epochs: parseInt(document.getElementById('config-epochs').value),
            batch_size: parseInt(document.getElementById('config-batch-size').value),
            learning_rate: parseFloat(document.getElementById('config-learning-rate').value),
            max_length: parseInt(document.getElementById('config-max-length').value)
        };
        
        try {
            const response = await fetch('/llm-training/api/training-jobs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(formData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.trainingJobs.unshift(data.job);
                this.renderTrainingJobs();
                this.hideCreateTrainingModal();
                this.showSuccess('Training job created and started');
            } else {
                this.showError(data.error || 'Failed to create training job');
            }
        } catch (error) {
            console.error('Error creating training job:', error);
            this.showError('Failed to create training job');
        }
    }
    
    async generateReport() {
        const selectedJobs = Array.from(document.querySelectorAll('#job-selection input:checked'))
            .map(cb => cb.value);
        
        const reportData = {
            job_ids: selectedJobs,
            include_metrics: document.getElementById('include-metrics').checked,
            include_logs: document.getElementById('include-logs').checked,
            include_model_info: document.getElementById('include-model-info').checked,
            format: document.getElementById('report-format').value
        };
        
        try {
            const response = await fetch('/llm-training/api/reports', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(reportData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.reports.unshift(data.report);
                this.renderReports();
                this.hideGenerateReportModal();
                this.showSuccess('Report generation started');
            } else {
                this.showError(data.error || 'Failed to generate report');
            }
        } catch (error) {
            console.error('Error generating report:', error);
            this.showError('Failed to generate report');
        }
    }
    
    async deleteReport(reportId) {
        // Validate reportId
        if (!reportId || typeof reportId !== 'string') {
            this.showError('Invalid report ID');
            return;
        }
        
        // Find report name for confirmation
        const report = this.reports.find(r => r.id === reportId);
        const reportName = report ? report.name : 'this report';
        
        if (!confirm(`Are you sure you want to delete "${reportName}"? This action cannot be undone.`)) {
            return;
        }
        
        try {
            const response = await fetch(`/llm-training/api/reports/${reportId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                if (response.status === 404) {
                    this.showError('Report not found. It may have already been deleted.');
                    // Remove from local array anyway
                    this.reports = this.reports.filter(r => r.id !== reportId);
                    this.renderReports();
                    return;
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Remove from local reports array
                this.reports = this.reports.filter(r => r.id !== reportId);
                this.renderReports();
                this.showSuccess(data.message || 'Report deleted successfully');
            } else {
                this.showError(data.error || 'Failed to delete report');
            }
        } catch (error) {
            console.error('Error deleting report:', error);
            this.showError('Failed to delete report. Please try again.');
        }
    }
    
    async downloadReport(reportId) {
        // Validate reportId
        if (!reportId || typeof reportId !== 'string') {
            this.showError('Invalid report ID');
            return;
        }
        
        try {
            const response = await fetch(`/llm-training/api/reports/${reportId}/download`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    this.showError('Report not found or not ready for download.');
                    return;
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Create download link
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `training_report_${reportId}.html`; // Default filename
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.showSuccess('Report downloaded successfully');
            
        } catch (error) {
            console.error('Error downloading report:', error);
            this.showError('Failed to download report. Please try again.');
        }
    }
    
    async startTrainingJob(jobId) {
        // Validate jobId
        if (!jobId || typeof jobId !== 'string') {
            this.showError('Invalid training job ID');
            return;
        }
        
        try {
            const response = await fetch(`/llm-training/api/training-jobs/${jobId}/start`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                if (response.status === 404) {
                    this.showError('Training job not found. It may have been deleted.');
                    this.refreshTrainingJobs(); // Refresh to remove stale data
                    return;
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Training job started');
                this.refreshTrainingJobs();
            } else {
                this.showError(data.error || 'Failed to start training job');
            }
        } catch (error) {
            console.error('Error starting training job:', error);
            this.showError('Failed to start training job. Please try again.');
        }
    }
    
    async cancelTrainingJob(jobId) {
        try {
            const response = await fetch(`/llm-training/api/training-jobs/${jobId}/cancel`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Training job cancelled');
                this.refreshTrainingJobs();
            } else {
                this.showError(data.error || 'Failed to cancel training job');
            }
        } catch (error) {
            console.error('Error cancelling training job:', error);
            this.showError('Failed to cancel training job');
        }
    }
    
    async refreshTrainingJobs() {
        await this.loadTrainingJobs();
        this.renderTrainingJobs();
    }
    
    async deleteTrainingJob(jobId, jobName) {
        if (!confirm(`Are you sure you want to delete the training job "${jobName}"? This action cannot be undone.`)) {
            return;
        }
        
        try {
            const response = await fetch(`/llm-training/api/training-jobs/${jobId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Remove from local training jobs array
                this.trainingJobs = this.trainingJobs.filter(job => job.id !== jobId);
                
                // Update UI
                this.renderTrainingJobs();
                this.loadStats(); // Refresh stats
                
                this.showSuccess(data.message || 'Training job deleted successfully');
            } else {
                this.showError(data.error || 'Failed to delete training job');
            }
        } catch (error) {
            console.error('Error deleting training job:', error);
            this.showError('Failed to delete training job');
        }
    }
    
    async refreshModels() {
        try {
            this.showLoading('Refreshing models...');
            
            const response = await fetch('/llm-training/api/models/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Update model options in the training form
                this.updateModelOptions(data.models);
                this.showSuccess(data.message || `Models refreshed successfully (${data.models.length} models found)`);
                
                // Log the models for debugging
                console.log('Available models:', data.models);
                
                // Also update the model datalist
                this.updateModelDatalist(data.models);
            } else {
                this.showError(data.error || 'Failed to refresh models');
            }
        } catch (error) {
            console.error('Error refreshing models:', error);
            this.showError('Failed to refresh models: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    updateModelDatalist(models) {
        const datalist = document.getElementById('model-options');
        if (datalist && models) {
            datalist.innerHTML = models.map(model => 
                `<option value="${model.id}">${model.name} (${model.provider})</option>`
            ).join('');
        }
    }
    
    async testFunctionality() {
        try {
            this.showLoading('Running system tests...');
            
            const response = await fetch('/llm-training/api/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                const results = data.test_results;
                const status = results.overall_status;
                
                // Calculate totals if not provided
                results.total_tests = results.tests ? results.tests.length : 0;
                results.passed_tests = results.tests ? results.tests.filter(t => t.status === 'passed').length : 0;
                results.failed_tests = results.total_tests - results.passed_tests;
                
                if (status === 'passed') {
                    this.showSuccess(`✅ All tests passed! (${results.passed_tests}/${results.total_tests})`);
                } else {
                    this.showWarning(`⚠️ Some tests failed (${results.passed_tests}/${results.total_tests} passed)`);
                }
                
                // Show detailed test results in console
                console.log('System test results:', results);
                
                // Show detailed results in a modal
                this.showTestResults(results);
            } else {
                this.showError(data.error || 'System test failed');
            }
        } catch (error) {
            console.error('Error running system test:', error);
            this.showError('Failed to run system test: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    updateModelOptions(models) {
        const modelInput = document.getElementById('training-model');
        const modelOptions = document.getElementById('model-options');
        
        if (modelOptions) {
            // Clear existing options
            modelOptions.innerHTML = '';
            
            // Add new model options
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = `${model.name} (${model.provider})`;
                modelOptions.appendChild(option);
            });
        }
    }
    
    showTestResults(results) {
        // Create a simple modal to show test results
        const modal = document.createElement('div');
        modal.className = 'modal show';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3 class="modal-title">System Test Results</h3>
                    <button class="close-btn" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div style="max-height: 400px; overflow-y: auto;">
                    <div style="margin-bottom: 16px;">
                        <strong>Overall Status:</strong> 
                        <span style="color: ${results.overall_status === 'passed' ? 'green' : 'red'}">
                            ${results.overall_status.toUpperCase()}
                        </span>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <strong>Results:</strong> ${results.passed_tests}/${results.total_tests} tests passed
                    </div>
                    <div>
                        <strong>Test Details:</strong>
                        <ul style="margin-top: 8px;">
                            ${results.tests.map(test => `
                                <li style="margin-bottom: 8px;">
                                    <strong>${test.name}:</strong> 
                                    <span style="color: ${test.status === 'passed' ? 'green' : 'red'}">
                                        ${test.status.toUpperCase()}
                                    </span>
                                    <br>
                                    <small style="color: #666;">${test.message}</small>
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                </div>
                <div style="display: flex; justify-content: flex-end; margin-top: 16px;">
                    <button class="btn btn-primary" onclick="this.closest('.modal').remove()">Close</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    showLoading(message = 'Loading...') {
        // Create or update loading indicator
        let loader = document.getElementById('global-loader');
        if (!loader) {
            loader = document.createElement('div');
            loader.id = 'global-loader';
            loader.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #3b82f6;
                color: white;
                padding: 12px 20px;
                border-radius: 6px;
                z-index: 9999;
                display: flex;
                align-items: center;
                gap: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            `;
            document.body.appendChild(loader);
        }
        
        loader.innerHTML = `
            <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            ${message}
        `;
        loader.style.display = 'flex';
    }
    
    hideLoading() {
        const loader = document.getElementById('global-loader');
        if (loader) {
            loader.style.display = 'none';
        }
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showWarning(message) {
        this.showNotification(message, 'warning');
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 6px;
            z-index: 10000;
            max-width: 400px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: slideIn 0.3s ease-out;
        `;
        
        const colors = {
            success: { bg: '#10b981', text: 'white' },
            error: { bg: '#ef4444', text: 'white' },
            warning: { bg: '#f59e0b', text: 'white' },
            info: { bg: '#3b82f6', text: 'white' }
        };
        
        const color = colors[type] || colors.info;
        notification.style.backgroundColor = color.bg;
        notification.style.color = color.text;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOut 0.3s ease-in';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }
        }, 5000);
        
        // Add click to dismiss
        notification.addEventListener('click', () => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        });
    }
    
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }
    
    async deleteDocument(documentId) {
        // Show confirmation dialog
        if (!confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`/llm-training/api/documents/${documentId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Remove document from local array
                this.documents = this.documents.filter(doc => doc.id !== documentId);
                
                // Re-render documents and refresh stats
                this.renderDocuments();
                this.loadStats();
                
                this.showSuccess('Document deleted successfully');
            } else {
                this.showError(data.error || 'Failed to delete document');
            }
        } catch (error) {
            console.error('Error deleting document:', error);
            this.showError('Failed to delete document');
        }
    }
    
    async editDocument(documentId) {
        const document = this.documents.find(doc => doc.id === documentId);
        if (!document) {
            this.showError('Document not found');
            return;
        }
        
        this.showEditDocumentModal(document);
    }
    
    async updateDocument() {
        const documentId = document.getElementById('edit-document-id').value;
        const name = document.getElementById('edit-document-name').value;
        const datasetId = document.getElementById('edit-document-dataset').value || null;
        
        try {
            const response = await fetch(`/llm-training/api/documents/${documentId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    name: name,
                    dataset_id: datasetId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update document in local array
                const docIndex = this.documents.findIndex(doc => doc.id === documentId);
                if (docIndex !== -1) {
                    this.documents[docIndex].name = name;
                    this.documents[docIndex].dataset = datasetId;
                }
                
                // Re-render documents and refresh stats
                this.renderDocuments();
                this.loadStats();
                
                this.hideEditDocumentModal();
                this.showSuccess('Document updated successfully');
            } else {
                this.showError(data.error || 'Failed to update document');
            }
        } catch (error) {
            console.error('Error updating document:', error);
            this.showError('Failed to update document');
        }
    }
    
    // Modal management
    showCreateDatasetModal() {
        this.populateDocumentSelection();
        document.getElementById('create-dataset-modal').classList.add('show');
    }
    
    hideCreateDatasetModal() {
        document.getElementById('create-dataset-modal').classList.remove('show');
        document.getElementById('create-dataset-form').reset();
    }
    
    showUploadModal() {
        document.getElementById('upload-modal').classList.add('show');
    }
    
    hideUploadModal() {
        document.getElementById('upload-modal').classList.remove('show');
        
        // Reset file input and upload progress
        const fileInput = document.getElementById('file-input');
        const uploadProgress = document.getElementById('upload-progress');
        
        if (fileInput) {
            fileInput.value = '';
        }
        
        if (uploadProgress) {
            uploadProgress.style.display = 'none';
        }
    }
    
    showCreateTrainingModal() {
        this.populateDatasetSelection();
        this.populateModelOptions();
        document.getElementById('create-training-modal').classList.add('show');
    }
    
    hideCreateTrainingModal() {
        document.getElementById('create-training-modal').classList.remove('show');
        document.getElementById('create-training-form').reset();
    }
    
    showGenerateReportModal() {
        this.populateJobSelection();
        document.getElementById('generate-report-modal').classList.add('show');
    }
    
    hideGenerateReportModal() {
        document.getElementById('generate-report-modal').classList.remove('show');
        document.getElementById('generate-report-form').reset();
    }
    
    async showDatasetManager() {
        // Show the modal
        document.getElementById('dataset-manager-modal').classList.add('show');
        
        // Load fresh data and render datasets
        await this.loadDatasets();
        await this.loadStats(); // Refresh stats to ensure accuracy
        this.renderDatasetManager();
    }
    
    renderDatasetManager() {
        const emptyState = document.getElementById('dataset-manager-empty-state');
        const datasetList = document.getElementById('dataset-list');
        
        if (!emptyState || !datasetList) return;
        
        if (this.datasets.length === 0) {
            // Show empty state
            emptyState.style.display = 'block';
            datasetList.style.display = 'none';
        } else {
            // Hide empty state and show dataset list
            emptyState.style.display = 'none';
            datasetList.style.display = 'block';
            
            // Render dataset list
            datasetList.innerHTML = this.datasets.map(dataset => `
                <div class="dataset-item" style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 16px; background: #f9fafb;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                        <div style="flex: 1;">
                            <h4 style="margin: 0 0 4px 0; font-weight: 600; color: #1f2937;">${dataset.name}</h4>
                            <p style="margin: 0; font-size: 0.875rem; color: #6b7280;">${dataset.description || 'No description'}</p>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <button class="btn btn-sm btn-secondary" onclick="documentManager.editDataset('${dataset.id}')">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="documentManager.deleteDataset('${dataset.id}', '${dataset.name}')">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 12px; font-size: 0.875rem; color: #6b7280;">
                        <div>
                            <strong>${dataset.document_count || 0}</strong><br>
                            <span>Documents</span>
                        </div>
                        <div>
                            <strong>${this.formatNumber(dataset.total_words || 0)}</strong><br>
                            <span>Words</span>
                        </div>
                        <div>
                            <strong>${this.formatFileSize(dataset.total_size || 0)}</strong><br>
                            <span>Size</span>
                        </div>
                        <div>
                            <strong>${new Date(dataset.created_at).toLocaleDateString()}</strong><br>
                            <span>Created</span>
                        </div>
                    </div>
                </div>
            `).join('');
        }
    }
    
    async editDataset(datasetId) {
        // For now, just show an alert - you can implement a proper edit modal later
        const dataset = this.datasets.find(d => d.id === datasetId);
        if (dataset) {
            const newName = prompt('Enter new dataset name:', dataset.name);
            if (newName && newName !== dataset.name) {
                try {
                    const response = await fetch(`/llm-training/api/datasets/${datasetId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.getCSRFToken()
                        },
                        body: JSON.stringify({ name: newName })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        // Update local dataset
                        dataset.name = newName;
                        this.renderDatasetManager();
                        this.updateDatasetTabs();
                        this.showSuccess('Dataset updated successfully');
                    } else {
                        this.showError(data.error || 'Failed to update dataset');
                    }
                } catch (error) {
                    console.error('Error updating dataset:', error);
                    this.showError('Failed to update dataset');
                }
            }
        }
    }
    
    async deleteDataset(datasetId, datasetName) {
        // Validate inputs
        if (!datasetId || typeof datasetId !== 'string') {
            this.showError('Invalid dataset ID');
            return;
        }
        
        const safeName = datasetName || 'this dataset';
        
        if (!confirm(`Are you sure you want to delete the dataset "${safeName}"? This action cannot be undone.`)) {
            return;
        }
        
        try {
            const response = await fetch(`/llm-training/api/datasets/${datasetId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                if (response.status === 404) {
                    this.showError('Dataset not found. It may have already been deleted.');
                    // Remove from local array anyway
                    this.datasets = this.datasets.filter(d => d.id !== datasetId);
                    this.renderDatasetManager();
                    this.updateDatasetTabs();
                    return;
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Remove from local datasets array
                this.datasets = this.datasets.filter(d => d.id !== datasetId);
                
                // Update UI
                this.renderDatasetManager();
                this.updateDatasetTabs();
                this.loadStats(); // Refresh stats
                
                // If we were viewing this dataset, switch to 'all'
                if (this.currentDataset === datasetId) {
                    this.switchDataset('all');
                }
                
                this.showSuccess(data.message || 'Dataset deleted successfully');
            } else {
                this.showError(data.error || 'Failed to delete dataset');
            }
        } catch (error) {
            console.error('Error deleting dataset:', error);
            this.showError('Failed to delete dataset. Please try again.');
        }
    }
    
    hideDatasetManagerModal() {
        document.getElementById('dataset-manager-modal').classList.remove('show');
    }
    
    showEditDocumentModal(doc) {
        // Populate form with document data
        document.getElementById('edit-document-id').value = doc.id;
        document.getElementById('edit-document-name').value = doc.name;
        
        // Populate dataset dropdown
        const datasetSelect = document.getElementById('edit-document-dataset');
        datasetSelect.innerHTML = '<option value="">Unassigned</option>' +
            this.datasets.map(dataset => 
                `<option value="${dataset.id}" ${doc.dataset === dataset.id ? 'selected' : ''}>${dataset.name}</option>`
            ).join('');
        
        // Populate document information
        document.getElementById('edit-document-type').textContent = doc.type.toUpperCase();
        document.getElementById('edit-document-size').textContent = this.formatFileSize(doc.size);
        document.getElementById('edit-document-words').textContent = this.formatNumber(doc.word_count);
        document.getElementById('edit-document-date').textContent = new Date(doc.uploaded_at).toLocaleDateString();
        
        // Show modal
        document.getElementById('edit-document-modal').classList.add('show');
    }
    
    hideEditDocumentModal() {
        document.getElementById('edit-document-modal').classList.remove('show');
        document.getElementById('edit-document-form').reset();
    }
    
    showJobDetails(jobId) {
        const job = this.trainingJobs.find(j => j.id === jobId);
        if (!job) return;
        
        document.getElementById('job-details-title').textContent = `Training Job: ${job.name}`;
        document.getElementById('job-details-content').innerHTML = this.renderJobDetails(job);
        document.getElementById('job-details-modal').classList.add('show');
    }
    
    hideJobDetailsModal() {
        document.getElementById('job-details-modal').classList.remove('show');
    }
    
    renderJobDetails(job) {
        return `
            <div class="space-y-4">
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="form-label">Status</label>
                        <div class="job-status status-${job.status}">${job.status}</div>
                    </div>
                    <div>
                        <label class="form-label">Progress</label>
                        <div>${job.progress || 0}%</div>
                    </div>
                    <div>
                        <label class="form-label">Model</label>
                        <div>${job.model}</div>
                    </div>
                    <div>
                        <label class="form-label">Created</label>
                        <div>${new Date(job.created_at).toLocaleString()}</div>
                    </div>
                </div>
                
                ${job.config ? `
                    <div>
                        <label class="form-label">Configuration</label>
                        <pre class="bg-gray-100 p-3 rounded text-sm">${JSON.stringify(job.config, null, 2)}</pre>
                    </div>
                ` : ''}
                
                ${job.results ? `
                    <div>
                        <label class="form-label">Results</label>
                        <pre class="bg-gray-100 p-3 rounded text-sm">${JSON.stringify(job.results, null, 2)}</pre>
                    </div>
                ` : ''}
                
                ${job.error_message ? `
                    <div>
                        <label class="form-label">Error</label>
                        <div class="text-red-600">${job.error_message}</div>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    populateDocumentSelection() {
        const container = document.getElementById('document-selection');
        if (!container) return;
        
        container.innerHTML = this.documents.map(doc => `
            <div class="checkbox-item">
                <input type="checkbox" id="doc-${doc.id}" value="${doc.id}">
                <label for="doc-${doc.id}">${doc.name}</label>
            </div>
        `).join('');
    }
    
    populateDatasetSelection() {
        const select = document.getElementById('training-dataset');
        if (!select) return;
        
        select.innerHTML = '<option value="">Select a dataset...</option>' +
            this.datasets.map(dataset => 
                `<option value="${dataset.id}">${dataset.name}</option>`
            ).join('');
    }
    
    populateModelOptions() {
        const datalist = document.getElementById('model-options');
        if (!datalist) return;
        
        // Load models from API instead of using mock data
        this.loadAvailableModels();
    }
    
    async loadAvailableModels() {
        try {
            const response = await fetch('/llm-training/api/models', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success && data.models) {
                this.updateModelOptions(data.models);
            } else {
                console.warn('Failed to load models from API, using fallback options');
                // Fallback to basic options if API fails
                const fallbackModels = [
                    { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'OpenAI' },
                    { id: 'gpt-4', name: 'GPT-4', provider: 'OpenAI' },
                    { id: 'deepseek-chat', name: 'DeepSeek Chat', provider: 'DeepSeek' }
                ];
                this.updateModelOptions(fallbackModels);
            }
        } catch (error) {
            console.error('Error loading models:', error);
            // Use fallback options on error
            const fallbackModels = [
                { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'OpenAI' },
                { id: 'gpt-4', name: 'GPT-4', provider: 'OpenAI' },
                { id: 'deepseek-chat', name: 'DeepSeek Chat', provider: 'DeepSeek' }
            ];
            this.updateModelOptions(fallbackModels);
        }
    }
    
    populateJobSelection() {
        const container = document.getElementById('job-selection');
        if (!container) return;
        
        container.innerHTML = this.trainingJobs.map(job => `
            <div class="checkbox-item">
                <input type="checkbox" id="job-${job.id}" value="${job.id}">
                <label for="job-${job.id}">${job.name} (${job.status})</label>
            </div>
        `).join('');
    }
    
    // Utility methods
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    formatNumber(num) {
        return num.toLocaleString();
    }
    
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
    
    showSuccess(message) {
        this.showFlashMessage(message, 'success');
    }
    
    showError(message) {
        this.showFlashMessage(message, 'error');
    }
    
    showFlashMessage(message, type) {
        // Create flash message element
        const flashContainer = document.getElementById('flash-messages') || this.createFlashContainer();
        
        const messageEl = document.createElement('div');
        messageEl.className = `flash-message animate-slide-up max-w-sm bg-white border-l-4 ${
            type === 'error' ? 'border-red-500 bg-red-50' : 'border-green-500 bg-green-50'
        } rounded-lg shadow-lg p-4`;
        
        messageEl.innerHTML = `
            <div class="flex items-center">
                <div class="flex-shrink-0">
                    <svg class="h-5 w-5 ${type === 'error' ? 'text-red-500' : 'text-green-500'}" fill="currentColor" viewBox="0 0 20 20">
                        ${type === 'error' ? 
                            '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />' :
                            '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />'
                        }
                    </svg>
                </div>
                <div class="ml-3">
                    <p class="text-sm font-medium ${type === 'error' ? 'text-red-800' : 'text-green-800'}">${message}</p>
                </div>
                <div class="ml-auto pl-3">
                    <button type="button" class="flash-close inline-flex rounded-md p-1.5 ${
                        type === 'error' ? 'text-red-500 hover:bg-red-100' : 'text-green-500 hover:bg-green-100'
                    } focus:outline-none">
                        <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                        </svg>
                    </button>
                </div>
            </div>
        `;
        
        flashContainer.appendChild(messageEl);
        
        // Add close functionality
        messageEl.querySelector('.flash-close').addEventListener('click', () => {
            messageEl.style.transition = 'opacity 0.3s ease-out';
            messageEl.style.opacity = '0';
            setTimeout(() => messageEl.remove(), 300);
        });
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.style.transition = 'opacity 0.5s ease-out';
                messageEl.style.opacity = '0';
                setTimeout(() => messageEl.remove(), 500);
            }
        }, 5000);
    }
    
    createFlashContainer() {
        const container = document.createElement('div');
        container.id = 'flash-messages';
        container.className = 'fixed top-4 right-4 z-50 space-y-2';
        document.body.appendChild(container);
        return container;
    }
}

// Global functions for template onclick handlers
function showCreateDatasetModal() {
    documentManager.showCreateDatasetModal();
}

function hideCreateDatasetModal() {
    documentManager.hideCreateDatasetModal();
}

function showUploadModal() {
    documentManager.showUploadModal();
}

function hideUploadModal() {
    documentManager.hideUploadModal();
}

function showCreateTrainingModal() {
    documentManager.showCreateTrainingModal();
}

function hideCreateTrainingModal() {
    documentManager.hideCreateTrainingModal();
}

function showGenerateReportModal() {
    documentManager.showGenerateReportModal();
}

function hideGenerateReportModal() {
    documentManager.hideGenerateReportModal();
}

function hideJobDetailsModal() {
    documentManager.hideJobDetailsModal();
}

function hideDatasetManagerModal() {
    documentManager.hideDatasetManagerModal();
}

function showEditDocumentModal(document) {
    documentManager.showEditDocumentModal(document);
}

function hideEditDocumentModal() {
    documentManager.hideEditDocumentModal();
}

// Initialize when DOM is ready
// Initialize document manager when DOM is loaded
let documentManager;
document.addEventListener('DOMContentLoaded', function() {
    try {
        documentManager = new DocumentManager();
        
        // Make it globally accessible for onclick handlers
        window.documentManager = documentManager;
        
        console.log('LLM Training page initialized successfully');
    } catch (error) {
        console.error('Error initializing LLM Training page:', error);
    }
});
// Utility Functions
function showLoading(message = 'Loading...') {
    console.log('LLM Training Loading:', message);
    // Show loading indicator
    const loadingEl = document.getElementById('loading-indicator');
    if (loadingEl) {
        loadingEl.textContent = message;
        loadingEl.style.display = 'block';
    } else {
        // Create a simple loading indicator if none exists
        const loading = document.createElement('div');
        loading.id = 'loading-indicator';
        loading.className = 'fixed top-4 right-4 bg-blue-500 text-white px-4 py-2 rounded shadow-lg z-50';
        loading.textContent = message;
        document.body.appendChild(loading);
    }
}

function hideLoading() {
    // Hide loading indicator
    const loadingEl = document.getElementById('loading-indicator');
    if (loadingEl) {
        loadingEl.style.display = 'none';
    }
}

function showError(message) {
    console.error('LLM Training Error:', message);
    // Show error notification
    if (window.NotificationManager) {
        window.NotificationManager.show(message, 'error', 5000);
    } else if (window.showNotification) {
        window.showNotification(message, 'error', 5000);
    } else {
        // Fallback to alert if no notification system available
        alert('Error: ' + message);
    }
}

function showSuccess(message) {
    console.log('LLM Training Success:', message);
    // Show success notification
    if (window.NotificationManager) {
        window.NotificationManager.show(message, 'success', 3000);
    } else if (window.showNotification) {
        window.showNotification(message, 'success', 3000);
    } else {
        // Fallback to console log if no notification system available
        console.log('Success: ' + message);
    }
}

function getCSRFToken() {
        const token = document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || 
                     document.querySelector('input[name=csrf_token]')?.value || '';
        if (!token) {
            console.warn('CSRF token not found');
        }
        return token;
    }

// Format utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatNumber(num) {
    if (num === 0) return '0';
    return num.toLocaleString();
}

// Modal management functions
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
    }
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
    }
}

// Additional utility functions for better error handling
function handleApiError(error, operation = 'operation') {
    console.error(`Error during ${operation}:`, error);
    
    let message = `Failed to ${operation}`;
    if (error.message) {
        if (error.message.includes('404')) {
            message += ': Resource not found';
        } else if (error.message.includes('500')) {
            message += ': Server error occurred';
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
            message += ': Network error. Please check your connection';
        } else {
            message += `: ${error.message}`;
        }
    }
    
    showError(message);
}

// Safe API call wrapper
async function safeApiCall(url, options = {}, operation = 'API call') {
    try {
        // Ensure CSRF token is included
        if (!options.headers) {
            options.headers = {};
        }
        if (!options.headers['X-CSRFToken']) {
            options.headers['X-CSRFToken'] = getCSRFToken();
        }
        
        // Ensure credentials are included
        if (!options.credentials) {
            options.credentials = 'same-origin';
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error(`Resource not found (404)`);
            } else if (response.status >= 500) {
                throw new Error(`Server error (${response.status})`);
            } else if (response.status === 403) {
                throw new Error(`Access denied (403)`);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        }
        
        const data = await response.json();
        return data;
        
    } catch (error) {
        handleApiError(error, operation);
        throw error;
    }
}

// Initialize the document manager when the page loads
document.addEventListener('DOMContentLoaded', function() {
    try {
        window.documentManager = new DocumentManager();
        console.log('LLM Training page initialized successfully');
    } catch (error) {
        console.error('Failed to initialize LLM Training page:', error);
        // Show error to user
        if (window.showNotification) {
            window.showNotification('Failed to initialize page. Please refresh and try again.', 'error', 5000);
        } else {
            alert('Failed to initialize page. Please refresh and try again.');
        }
    }
});

// Export for global access
window.DocumentManager = DocumentManager;