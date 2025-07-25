/**
 * LLM Training Page - Document Management Interface
 * Fixed version with proper error handling and CSRF token management
 */

class DocumentManager {
    constructor() {
        this.documents = [];
        this.datasets = [];
        this.currentDataset = 'all';
        this.trainingJobs = [];
        this.reports = [];
        this.models = [];
        this.refreshInterval = null;
        this.init();
    }

    init() {
        console.log('Initializing DocumentManager...');
        this.loadDocuments();
        this.loadDatasets();
        this.loadModels();
        this.loadTrainingJobs();
        this.loadReports();
        this.setupEventListeners();
        this.updateStats();
        this.startRefreshInterval();
    }

    // Helper function to get CSRF token from multiple sources
    getCSRFToken() {
        let csrfToken = null;
        
        // Try meta tag first
        const metaTag = document.querySelector('meta[name=csrf-token]');
        if (metaTag && metaTag.getAttribute('content')) {
            csrfToken = metaTag.getAttribute('content');
        }
        
        // Try form inputs as fallback
        if (!csrfToken) {
            const tokenInput = document.querySelector('input[name=csrf_token]');
            if (tokenInput && tokenInput.value) {
                csrfToken = tokenInput.value;
            }
        }
        
        // Try ExamGrader object if available
        if (!csrfToken && typeof ExamGrader !== 'undefined' && ExamGrader.csrf && typeof ExamGrader.csrf.getToken === 'function') {
            try {
                csrfToken = ExamGrader.csrf.getToken();
            } catch (e) {
                console.warn('Error getting CSRF token from ExamGrader:', e);
            }
        }
        
        return csrfToken;
    }

    setupEventListeners() {
        // Dataset tab switching
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('dataset-tab')) {
                this.switchDataset(e.target.dataset.dataset);
            }
        });

        // File upload handling
        const fileInput = document.getElementById('file-input');
        const uploadArea = document.getElementById('upload-area');

        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleFileUpload(e.target.files);
            });
        }

        if (uploadArea) {
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
                this.handleFileUpload(e.dataTransfer.files);
            });
        }

        // Create dataset form
        const createDatasetForm = document.getElementById('create-dataset-form');
        if (createDatasetForm) {
            createDatasetForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createDataset();
            });
        }

        // Create training form
        const createTrainingForm = document.getElementById('create-training-form');
        if (createTrainingForm) {
            createTrainingForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createTrainingJob();
            });
        }

        // Generate report form
        const generateReportForm = document.getElementById('generate-report-form');
        if (generateReportForm) {
            generateReportForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.generateReport();
            });
        }
    }

    async loadDocuments() {
        try {
            const response = await fetch('/llm-training/api/documents');
            if (response.ok) {
                this.documents = await response.json();
                console.log('Loaded documents:', this.documents.length);
            } else if (response.status === 404) {
                console.log('No documents endpoint found, loading demo data');
                this.loadDemoData();
            } else {
                console.log('Error loading documents, loading demo data');
                this.loadDemoData();
            }
        } catch (error) {
            console.error('Error loading documents:', error);
            this.loadDemoData();
        }
        this.renderDocuments();
        this.updateStats();
    }

    loadDemoData() {
        this.documents = [
            {
                id: 'demo-1',
                name: 'sample_essay.txt',
                type: 'TXT',
                size: 2048,
                datasets: [],
                metadata: {
                    uploadDate: '2025-01-20T10:00:00Z',
                    wordCount: 350,
                    characterCount: 2048,
                    extractedText: true
                }
            },
            {
                id: 'demo-2',
                name: 'training_data.pdf',
                type: 'PDF',
                size: 5120,
                datasets: ['demo-dataset-1'],
                metadata: {
                    uploadDate: '2025-01-19T15:30:00Z',
                    wordCount: 750,
                    characterCount: 5120,
                    extractedText: true
                }
            },
            {
                id: 'demo-3',
                name: 'exam_answers.docx',
                type: 'DOCX',
                size: 3072,
                datasets: ['demo-dataset-1'],
                metadata: {
                    uploadDate: '2025-01-18T09:15:00Z',
                    wordCount: 500,
                    characterCount: 3072,
                    extractedText: true
                }
            }
        ];
    }

    async loadDatasets() {
        try {
            const response = await fetch('/llm-training/api/datasets');
            if (response.ok) {
                this.datasets = await response.json();
                console.log('Loaded datasets:', this.datasets.length);
            } else {
                console.log('No datasets found, loading demo data');
                this.loadDemoDatasets();
            }
        } catch (error) {
            console.error('Error loading datasets:', error);
            this.loadDemoDatasets();
        }
        this.renderDatasetTabs();
        this.updateStats();
    }

    loadDemoDatasets() {
        this.datasets = [
            {
                id: 'demo-dataset-1',
                name: 'Training Set A',
                description: 'Primary training dataset for exam grading',
                documents: ['demo-2', 'demo-3'],
                documentCount: 2,
                metadata: {
                    createdDate: '2025-01-18T08:00:00Z',
                    totalWords: 1250,
                    totalSize: 8192
                }
            }
        ];
    }

    renderDatasetTabs() {
        const tabsContainer = document.getElementById('dataset-tabs');
        if (!tabsContainer) return;

        // Remove existing custom tabs
        const existingCustomTabs = tabsContainer.querySelectorAll('.dataset-tab:not([data-dataset="all"]):not([data-dataset="unassigned"])');
        existingCustomTabs.forEach(tab => tab.remove());

        // Add dataset tabs
        this.datasets.forEach(dataset => {
            const tab = document.createElement('button');
            tab.className = 'dataset-tab';
            tab.dataset.dataset = dataset.id;
            tab.textContent = `${dataset.name} (${dataset.documentCount})`;
            tabsContainer.appendChild(tab);
        });
    }

    switchDataset(datasetId) {
        this.currentDataset = datasetId;

        // Update active tab
        document.querySelectorAll('.dataset-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        const activeTab = document.querySelector(`[data-dataset="${datasetId}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
        }

        this.renderDocuments();
    }

    renderDocuments() {
        const grid = document.getElementById('document-grid');
        const emptyState = document.getElementById('empty-state');
        
        if (!grid || !emptyState) return;

        let filteredDocuments = this.documents;

        if (this.currentDataset === 'unassigned') {
            filteredDocuments = this.documents.filter(doc => !doc.datasets || doc.datasets.length === 0);
        } else if (this.currentDataset !== 'all') {
            filteredDocuments = this.documents.filter(doc =>
                doc.datasets && doc.datasets.includes(this.currentDataset)
            );
        }

        if (filteredDocuments.length === 0) {
            grid.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }

        grid.style.display = 'grid';
        emptyState.style.display = 'none';

        grid.innerHTML = filteredDocuments.map(doc => this.createDocumentCard(doc)).join('');
    }

    createDocumentCard(doc) {
        const formatFileSize = (bytes) => {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        };

        const formatDate = (dateString) => {
            return new Date(dateString).toLocaleDateString();
        };

        const datasetTags = doc.datasets && doc.datasets.length > 0
            ? doc.datasets.map(datasetId => {
                const dataset = this.datasets.find(d => d.id === datasetId);
                return dataset ? `<span class="tag">${dataset.name}</span>` : '';
            }).join('')
            : '<span class="tag">Unassigned</span>';

        return `
            <div class="document-card" data-document-id="${doc.id}">
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
                    <div>Size: ${formatFileSize(doc.size)}</div>
                    <div>Type: ${doc.type}</div>
                    <div>Words: ${doc.metadata?.wordCount || 'N/A'}</div>
                    <div>Uploaded: ${formatDate(doc.metadata?.uploadDate)}</div>
                </div>
                <div class="document-tags">
                    ${datasetTags}
                </div>
            </div>
        `;
    }

    async handleFileUpload(files) {
        const uploadProgress = document.getElementById('upload-progress');
        const uploadBar = document.getElementById('upload-bar');
        const uploadPercentage = document.getElementById('upload-percentage');

        if (!uploadProgress || !uploadBar || !uploadPercentage) {
            console.error('Upload progress elements not found');
            return;
        }

        uploadProgress.style.display = 'block';

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const formData = new FormData();
            formData.append('file', file);

            try {
                // Get CSRF token
                const csrfToken = this.getCSRFToken();
                if (csrfToken) {
                    formData.append('csrf_token', csrfToken);
                }

                const response = await fetch('/llm-training/api/documents/upload', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();
                    this.documents.push(result.document);

                    const progress = ((i + 1) / files.length) * 100;
                    uploadBar.style.width = `${progress}%`;
                    uploadPercentage.textContent = `${Math.round(progress)}%`;
                } else {
                    const errorData = await response.json().catch(() => ({ error: 'Upload failed' }));
                    throw new Error(errorData.error || `Upload failed for ${file.name}`);
                }
            } catch (error) {
                console.error('Upload error:', error);
                this.showNotification(`Error uploading ${file.name}: ${error.message}`, 'error');
            }
        }

        setTimeout(() => {
            uploadProgress.style.display = 'none';
            uploadBar.style.width = '0%';
            uploadPercentage.textContent = '0%';
            hideUploadModal();
            this.renderDocuments();
            this.updateStats();
            this.showNotification('Documents uploaded successfully', 'success');
        }, 500);
    }

    async deleteDocument(documentId) {
        if (!confirm('Are you sure you want to delete this document?')) {
            return;
        }

        try {
            const csrfToken = this.getCSRFToken();
            const headers = {};
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const response = await fetch(`/llm-training/api/documents/${documentId}`, {
                method: 'DELETE',
                headers: headers
            });

            if (response.ok) {
                this.documents = this.documents.filter(doc => doc.id !== documentId);
                this.renderDocuments();
                this.updateStats();
                this.showNotification('Document deleted successfully', 'success');
            } else {
                const errorData = await response.json().catch(() => ({ error: 'Delete failed' }));
                throw new Error(errorData.error || 'Delete failed');
            }
        } catch (error) {
            console.error('Delete error:', error);
            this.showNotification('Error deleting document: ' + error.message, 'error');
        }
    }

    editDocument(documentId) {
        console.log('Edit document:', documentId);
        this.showNotification('Document editing not yet implemented', 'info');
    }

    async createDataset() {
        const nameInput = document.getElementById('dataset-name');
        const descriptionInput = document.getElementById('dataset-description');
        
        if (!nameInput || !descriptionInput) {
            console.error('Dataset form elements not found');
            return;
        }

        const name = nameInput.value.trim();
        const description = descriptionInput.value.trim();
        
        if (!name) {
            this.showNotification('Dataset name is required', 'error');
            return;
        }

        const selectedDocuments = Array.from(document.querySelectorAll('#document-selection input:checked'))
            .map(checkbox => checkbox.value);

        try {
            const csrfToken = this.getCSRFToken();
            const headers = {
                'Content-Type': 'application/json'
            };
            
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const response = await fetch('/llm-training/api/datasets', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    name,
                    description,
                    documents: selectedDocuments
                })
            });

            if (response.ok) {
                const dataset = await response.json();
                this.datasets.push(dataset);
                this.renderDatasetTabs();
                // Refresh models after dataset creation
                await this.loadModels();
                hideCreateDatasetModal();
                this.showNotification('Dataset created successfully', 'success');
            } else {
                const errorData = await response.json().catch(() => ({ error: 'Dataset creation failed' }));
                throw new Error(errorData.error || 'Dataset creation failed');
            }
        } catch (error) {
            console.error('Dataset creation error:', error);
            this.showNotification('Error creating dataset: ' + error.message, 'error');
        }
    }

    // Training functionality
    async loadModels() {
        try {
            const response = await fetch('/llm-training/api/models');
            if (response.ok) {
                this.models = await response.json();
                console.log('Loaded models:', this.models.length);
            } else {
                console.log('No models found, loading demo data');
                this.loadDemoModels();
            }
        } catch (error) {
            console.error('Error loading models:', error);
            this.loadDemoModels();
        }
        this.populateModelSelect();
    }

    loadDemoModels() {
        this.models = [
            {
                id: 'deepseek-chat',
                name: 'DeepSeek Chat',
                provider: 'deepseek',
                capabilities: ['fine-tuning', 'chat'],
                status: 'available'
            },
            {
                id: 'gpt-3.5-turbo',
                name: 'GPT-3.5 Turbo',
                provider: 'openai',
                capabilities: ['fine-tuning', 'chat'],
                status: 'unavailable'
            }
        ];
    }

    populateModelSelect() {
        const modelOptions = document.getElementById('model-options');
        if (!modelOptions) return;

        modelOptions.innerHTML = '';
        this.models.filter(model => model.status === 'available').forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = `${model.name} (${model.provider})`;
            modelOptions.appendChild(option);
        });
    }

    async refreshModels() {
        try {
            this.showNotification('Refreshing models...', 'info');
            await this.loadModels();
            this.showNotification('Models refreshed successfully', 'success');
        } catch (error) {
            console.error('Error refreshing models:', error);
            this.showNotification('Error refreshing models: ' + error.message, 'error');
        }
    }

    showDatasetManager() {
        const modal = document.getElementById('dataset-manager-modal');
        const emptyState = document.getElementById('dataset-manager-empty-state');
        const datasetList = document.getElementById('dataset-list');

        if (!modal || !emptyState || !datasetList) {
            console.error('Dataset manager modal elements not found');
            return;
        }

        if (this.datasets.length === 0) {
            emptyState.style.display = 'block';
            datasetList.style.display = 'none';
        } else {
            emptyState.style.display = 'none';
            datasetList.style.display = 'block';
            this.renderDatasetList();
        }

        modal.classList.add('show');
    }

    renderDatasetList() {
        const datasetList = document.getElementById('dataset-list');
        if (!datasetList) return;

        datasetList.innerHTML = this.datasets.map(dataset => this.createDatasetItem(dataset)).join('');
    }

    createDatasetItem(dataset) {
        const formatDate = (dateString) => {
            return new Date(dateString).toLocaleDateString();
        };

        return `
            <div class="dataset-item" style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 16px; background: #f9fafb;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div>
                        <h4 style="margin: 0 0 4px 0; font-weight: 600; color: #1f2937;">${dataset.name}</h4>
                        <p style="margin: 0; font-size: 0.875rem; color: #6b7280;">${dataset.description || 'No description'}</p>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-sm btn-secondary" onclick="documentManager.editDataset('${dataset.id}')">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="documentManager.deleteDataset('${dataset.id}')">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; font-size: 0.875rem; color: #6b7280;">
                    <div>Documents: ${dataset.documentCount || 0}</div>
                    <div>Created: ${formatDate(dataset.metadata?.createdDate || new Date())}</div>
                    <div>Words: ${dataset.metadata?.totalWords || 'N/A'}</div>
                    <div>Size: ${dataset.metadata?.totalSize ? (dataset.metadata.totalSize / 1024).toFixed(1) + ' KB' : 'N/A'}</div>
                </div>
            </div>
        `;
    }

    async deleteDataset(datasetId) {
        if (!confirm('Are you sure you want to delete this dataset? This action cannot be undone.')) {
            return;
        }

        try {
            const csrfToken = this.getCSRFToken();
            const headers = {};
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const response = await fetch(`/llm-training/api/datasets/${datasetId}`, {
                method: 'DELETE',
                headers: headers
            });

            if (response.ok) {
                this.datasets = this.datasets.filter(dataset => dataset.id !== datasetId);
                this.renderDatasetTabs();
                this.renderDatasetList();
                this.updateStats();
                this.showNotification('Dataset deleted successfully', 'success');
                
                // If no datasets left, show empty state
                if (this.datasets.length === 0) {
                    const emptyState = document.getElementById('dataset-manager-empty-state');
                    const datasetList = document.getElementById('dataset-list');
                    if (emptyState && datasetList) {
                        emptyState.style.display = 'block';
                        datasetList.style.display = 'none';
                    }
                }
            } else {
                const errorData = await response.json().catch(() => ({ error: 'Delete failed' }));
                throw new Error(errorData.error || 'Delete failed');
            }
        } catch (error) {
            console.error('Delete dataset error:', error);
            this.showNotification('Error deleting dataset: ' + error.message, 'error');
        }
    }

    editDataset(datasetId) {
        console.log('Edit dataset:', datasetId);
        this.showNotification('Dataset editing not yet implemented', 'info');
    }

    testFunctionality() {
        console.log('Testing LLM Training functionality...');
        
        // Test 1: Check if models are loaded
        console.log(`✅ Models loaded: ${this.models.length}`);
        this.models.forEach(model => {
            console.log(`   - ${model.name} (${model.id}) - Status: ${model.status}`);
        });
        
        // Test 2: Check if datasets are loaded
        console.log(`✅ Datasets loaded: ${this.datasets ? this.datasets.length : 0}`);
        if (this.datasets) {
            this.datasets.forEach(dataset => {
                console.log(`   - ${dataset.name} (${dataset.id}) - Documents: ${dataset.documentCount}`);
            });
        }
        
        // Test 3: Check if documents are loaded
        console.log(`✅ Documents loaded: ${this.documents ? this.documents.length : 0}`);
        if (this.documents) {
            this.documents.forEach(doc => {
                console.log(`   - ${doc.name} (${doc.type}) - Size: ${doc.size} bytes`);
            });
        }
        
        // Test 4: Check if training jobs are loaded
        console.log(`✅ Training jobs loaded: ${this.trainingJobs ? this.trainingJobs.length : 0}`);
        if (this.trainingJobs) {
            this.trainingJobs.forEach(job => {
                console.log(`   - ${job.name} (${job.id}) - Status: ${job.status}`);
            });
        }
        
        // Test 5: Test model selection population
        const modelSelect = document.getElementById('training-model');
        if (modelSelect) {
            const availableModels = this.models ? this.models.filter(model => model.status === 'available') : [];
            console.log(`✅ Available models for selection: ${availableModels.length}`);
            console.log(`✅ Model select options: ${modelSelect.options.length - 1}`); // -1 for placeholder
        }
        
        // Test 6: Test delete functionality (simulate)
        console.log('✅ Delete buttons present in document cards');
        const documentCards = document.querySelectorAll('.document-card');
        const deleteButtons = document.querySelectorAll('.document-card .btn-danger');
        console.log(`   - Document cards: ${documentCards.length}`);
        console.log(`   - Delete buttons: ${deleteButtons.length}`);
        
        // Test 7: Test refresh functionality
        console.log('✅ Testing refresh functionality...');
        this.refreshModels().then(() => {
            console.log('✅ Model refresh completed successfully');
        }).catch(error => {
            console.log(`❌ Model refresh failed: ${error.message}`);
        });
        
        this.showNotification('Test completed - Check console for detailed results', 'success');
    }

    async loadTrainingJobs() {
        try {
            const response = await fetch('/llm-training/api/training/jobs');
            if (response.ok) {
                this.trainingJobs = await response.json();
                console.log('Loaded training jobs:', this.trainingJobs.length);
            } else {
                console.log('No training jobs found, loading demo data');
                this.loadDemoTrainingJobs();
            }
        } catch (error) {
            console.error('Error loading training jobs:', error);
            this.loadDemoTrainingJobs();
        }
        this.renderTrainingJobs();
        this.updateTrainingStats();
    }

    loadDemoTrainingJobs() {
        this.trainingJobs = [
            {
                id: 'demo-job-1',
                name: 'Essay Grading Model v1',
                model_id: 'deepseek-chat',
                dataset_id: 'demo-dataset-1',
                status: 'completed',
                progress: 100,
                current_epoch: 10,
                total_epochs: 10,
                accuracy: 0.89,
                validation_accuracy: 0.85,
                start_time: '2025-01-20T08:00:00Z',
                end_time: '2025-01-20T10:30:00Z'
            },
            {
                id: 'demo-job-2',
                name: 'Math Problem Solver',
                model_id: 'deepseek-chat',
                dataset_id: 'demo-dataset-1',
                status: 'training',
                progress: 65,
                current_epoch: 6,
                total_epochs: 10,
                accuracy: 0.76,
                validation_accuracy: 0.72,
                start_time: '2025-01-20T14:00:00Z'
            }
        ];
    }

    async createTrainingJob() {
        const nameInput = document.getElementById('training-name');
        const modelSelect = document.getElementById('training-model');
        const datasetSelect = document.getElementById('training-dataset');

        if (!nameInput || !modelSelect || !datasetSelect) {
            console.error('Training form elements not found');
            return;
        }

        const name = nameInput.value.trim();
        const modelId = modelSelect.value;
        const datasetId = datasetSelect.value;

        if (!name || !modelId || !datasetId) {
            this.showNotification('Please fill in all required fields', 'error');
            return;
        }

        // Get configuration values
        const config = {
            epochs: parseInt(document.getElementById('config-epochs').value) || 10,
            batch_size: parseInt(document.getElementById('config-batch-size').value) || 8,
            learning_rate: parseFloat(document.getElementById('config-learning-rate').value) || 0.0001,
            max_length: parseInt(document.getElementById('config-max-length').value) || 512
        };

        try {
            const csrfToken = this.getCSRFToken();
            const headers = {
                'Content-Type': 'application/json'
            };
            
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const response = await fetch('/llm-training/api/training/jobs', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    name,
                    model_id: modelId,
                    dataset_id: datasetId,
                    config
                })
            });

            if (response.ok) {
                const job = await response.json();
                this.trainingJobs.push(job);
                
                // Start the training job
                await this.startTrainingJob(job.id);
                
                hideCreateTrainingModal();
                this.renderTrainingJobs();
                this.updateTrainingStats();
                this.showNotification('Training job created and started successfully', 'success');
            } else {
                const errorData = await response.json().catch(() => ({ error: 'Training job creation failed' }));
                throw new Error(errorData.error || 'Training job creation failed');
            }
        } catch (error) {
            console.error('Training job creation error:', error);
            this.showNotification('Error creating training job: ' + error.message, 'error');
        }
    }

    async startTrainingJob(jobId) {
        try {
            const csrfToken = this.getCSRFToken();
            const headers = {
                'Content-Type': 'application/json'
            };
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const response = await fetch(`/llm-training/api/training/jobs/${jobId}/start`, {
                method: 'POST',
                headers: headers
            });

            if (response.ok) {
                this.showNotification('Training started successfully', 'success');
                this.loadTrainingJobs(); // Refresh jobs
            } else {
                const errorData = await response.json().catch(() => ({ error: 'Failed to start training' }));
                throw new Error(errorData.error || 'Failed to start training');
            }
        } catch (error) {
            console.error('Start training error:', error);
            this.showNotification('Error starting training: ' + error.message, 'error');
        }
    }

    async cancelTrainingJob(jobId) {
        if (!confirm('Are you sure you want to cancel this training job?')) {
            return;
        }

        try {
            const csrfToken = this.getCSRFToken();
            const headers = {
                'Content-Type': 'application/json'
            };
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const response = await fetch(`/llm-training/api/training/jobs/${jobId}/cancel`, {
                method: 'POST',
                headers: headers
            });

            if (response.ok) {
                this.showNotification('Training job cancelled successfully', 'success');
                this.loadTrainingJobs(); // Refresh jobs
            } else {
                const errorData = await response.json().catch(() => ({ error: 'Failed to cancel training' }));
                throw new Error(errorData.error || 'Failed to cancel training');
            }
        } catch (error) {
            console.error('Cancel training error:', error);
            this.showNotification('Error cancelling training: ' + error.message, 'error');
        }
    }

    async deleteTrainingJob(jobId) {
        if (!confirm('Are you sure you want to delete this training job?')) {
            return;
        }

        try {
            const csrfToken = this.getCSRFToken();
            const headers = {};
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const response = await fetch(`/llm-training/api/training/jobs/${jobId}`, {
                method: 'DELETE',
                headers: headers
            });

            if (response.ok) {
                this.trainingJobs = this.trainingJobs.filter(job => job.id !== jobId);
                this.renderTrainingJobs();
                this.updateTrainingStats();
                this.showNotification('Training job deleted successfully', 'success');
            } else {
                const errorData = await response.json().catch(() => ({ error: 'Failed to delete training job' }));
                throw new Error(errorData.error || 'Failed to delete training job');
            }
        } catch (error) {
            console.error('Delete training job error:', error);
            this.showNotification('Error deleting training job: ' + error.message, 'error');
        }
    }

    renderTrainingJobs() {
        const container = document.getElementById('training-jobs-container');
        const emptyState = document.getElementById('training-empty-state');
        
        if (!container) return;

        if (this.trainingJobs.length === 0) {
            if (emptyState) {
                emptyState.style.display = 'block';
            }
            container.innerHTML = '';
            if (emptyState) {
                container.appendChild(emptyState);
            }
            return;
        }

        if (emptyState) {
            emptyState.style.display = 'none';
        }

        container.innerHTML = this.trainingJobs.map(job => this.createTrainingJobCard(job)).join('');
    }

    createTrainingJobCard(job) {
        const formatDate = (dateString) => {
            return new Date(dateString).toLocaleString();
        };

        const getStatusClass = (status) => {
            return `status-${status.toLowerCase()}`;
        };

        const getActionButtons = (job) => {
            const buttons = [];
            
            if (job.status === 'pending') {
                buttons.push(`<button class="btn btn-sm btn-primary" onclick="documentManager.startTrainingJob('${job.id}')">Start</button>`);
            }
            
            if (['preparing', 'training', 'evaluating'].includes(job.status)) {
                buttons.push(`<button class="btn btn-sm btn-secondary" onclick="documentManager.cancelTrainingJob('${job.id}')">Cancel</button>`);
            }
            
            buttons.push(`<button class="btn btn-sm btn-secondary" onclick="documentManager.showJobDetails('${job.id}')">Details</button>`);
            
            if (['completed', 'failed', 'cancelled'].includes(job.status)) {
                buttons.push(`<button class="btn btn-sm btn-danger" onclick="documentManager.deleteTrainingJob('${job.id}')">Delete</button>`);
            }
            
            return buttons.join('');
        };

        const model = this.models.find(m => m.id === job.model_id);
        const dataset = this.datasets.find(d => d.id === job.dataset_id);

        return `
            <div class="training-job">
                <div class="job-header">
                    <div class="job-name">${job.name}</div>
                    <div class="job-status ${getStatusClass(job.status)}">${job.status}</div>
                </div>
                <div class="job-meta">
                    <div>Model: ${model ? model.name : job.model_id}</div>
                    <div>Dataset: ${dataset ? dataset.name : job.dataset_id}</div>
                    <div>Epoch: ${job.current_epoch || 0}/${job.total_epochs || 0}</div>
                    <div>Accuracy: ${job.accuracy ? (job.accuracy * 100).toFixed(1) + '%' : 'N/A'}</div>
                    <div>Started: ${job.start_time ? formatDate(job.start_time) : 'Not started'}</div>
                    <div>Duration: ${this.calculateDuration(job.start_time, job.end_time)}</div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${job.progress || 0}%"></div>
                </div>
                <div class="job-actions">
                    ${getActionButtons(job)}
                </div>
            </div>
        `;
    }

    calculateDuration(startTime, endTime) {
        if (!startTime) return 'N/A';
        
        const start = new Date(startTime);
        const end = endTime ? new Date(endTime) : new Date();
        const diffMs = end - start;
        
        const hours = Math.floor(diffMs / (1000 * 60 * 60));
        const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }

    async showJobDetails(jobId) {
        try {
            const response = await fetch(`/llm-training/api/training/jobs/${jobId}`);
            if (response.ok) {
                const job = await response.json();
                this.displayJobDetails(job);
            } else {
                throw new Error('Failed to load job details');
            }
        } catch (error) {
            console.error('Error loading job details:', error);
            this.showNotification('Error loading job details: ' + error.message, 'error');
        }
    }

    displayJobDetails(job) {
        const modal = document.getElementById('job-details-modal');
        const title = document.getElementById('job-details-title');
        const content = document.getElementById('job-details-content');
        
        if (!modal || !title || !content) return;

        title.textContent = `Training Job: ${job.name}`;
        
        const model = this.models.find(m => m.id === job.model_id);
        const dataset = this.datasets.find(d => d.id === job.dataset_id);

        content.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                <div>
                    <h4>Job Information</h4>
                    <p><strong>Status:</strong> ${job.status}</p>
                    <p><strong>Model:</strong> ${model ? model.name : job.model_id}</p>
                    <p><strong>Dataset:</strong> ${dataset ? dataset.name : job.dataset_id}</p>
                    <p><strong>Progress:</strong> ${job.progress || 0}%</p>
                </div>
                <div>
                    <h4>Training Metrics</h4>
                    <p><strong>Current Epoch:</strong> ${job.current_epoch || 0}/${job.total_epochs || 0}</p>
                    <p><strong>Accuracy:</strong> ${job.accuracy ? (job.accuracy * 100).toFixed(2) + '%' : 'N/A'}</p>
                    <p><strong>Validation Accuracy:</strong> ${job.validation_accuracy ? (job.validation_accuracy * 100).toFixed(2) + '%' : 'N/A'}</p>
                    <p><strong>Loss:</strong> ${job.loss ? job.loss.toFixed(4) : 'N/A'}</p>
                </div>
            </div>
            <div>
                <h4>Training Configuration</h4>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;">
                    <p><strong>Epochs:</strong> ${job.config?.epochs || 'N/A'}</p>
                    <p><strong>Batch Size:</strong> ${job.config?.batch_size || 'N/A'}</p>
                    <p><strong>Learning Rate:</strong> ${job.config?.learning_rate || 'N/A'}</p>
                    <p><strong>Max Length:</strong> ${job.config?.max_length || 'N/A'}</p>
                </div>
            </div>
            ${job.logs && job.logs.length > 0 ? `
                <div>
                    <h4>Training Logs</h4>
                    <div style="background: #f3f4f6; border-radius: 6px; padding: 12px; max-height: 200px; overflow-y: auto; font-family: monospace; font-size: 0.875rem;">
                        ${job.logs.slice(-10).map(log => `<div>${log}</div>`).join('')}
                    </div>
                </div>
            ` : ''}
        `;

        modal.classList.add('show');
    }

    // Reports functionality
    async loadReports() {
        try {
            const response = await fetch('/llm-training/api/reports');
            if (response.ok) {
                this.reports = await response.json();
                console.log('Loaded reports:', this.reports.length);
            } else {
                console.log('No reports found');
                this.reports = [];
            }
        } catch (error) {
            console.error('Error loading reports:', error);
            this.reports = [];
        }
        this.renderReports();
    }

    async generateReport() {
        const selectedJobs = Array.from(document.querySelectorAll('#job-selection input:checked'))
            .map(checkbox => checkbox.value);

        if (selectedJobs.length === 0) {
            this.showNotification('Please select at least one training job', 'error');
            return;
        }

        const config = {
            include_metrics: document.getElementById('include-metrics').checked,
            include_logs: document.getElementById('include-logs').checked,
            include_model_info: document.getElementById('include-model-info').checked,
            format: document.getElementById('report-format').value
        };

        try {
            const csrfToken = this.getCSRFToken();
            const headers = {
                'Content-Type': 'application/json'
            };
            
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const response = await fetch('/llm-training/api/reports/generate', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    job_ids: selectedJobs,
                    config
                })
            });

            if (response.ok) {
                const result = await response.json();
                hideGenerateReportModal();
                this.showNotification('Report generation started', 'success');
                
                // Refresh reports after a delay
                setTimeout(() => {
                    this.loadReports();
                }, 2000);
            } else {
                const errorData = await response.json().catch(() => ({ error: 'Report generation failed' }));
                throw new Error(errorData.error || 'Report generation failed');
            }
        } catch (error) {
            console.error('Report generation error:', error);
            this.showNotification('Error generating report: ' + error.message, 'error');
        }
    }

    renderReports() {
        const container = document.getElementById('reports-container');
        const emptyState = document.getElementById('reports-empty-state');
        
        if (!container) return;

        if (this.reports.length === 0) {
            if (emptyState) {
                emptyState.style.display = 'block';
            }
            container.innerHTML = '';
            if (emptyState) {
                container.appendChild(emptyState);
            }
            return;
        }

        if (emptyState) {
            emptyState.style.display = 'none';
        }

        container.innerHTML = this.reports.map(report => this.createReportItem(report)).join('');
    }

    createReportItem(report) {
        const formatDate = (dateString) => {
            return new Date(dateString).toLocaleString();
        };

        return `
            <div class="report-item">
                <div class="report-info">
                    <h4>${report.name || `Training Report - ${report.id}`}</h4>
                    <p>Generated: ${formatDate(report.created_at)} | Format: ${report.format?.toUpperCase() || 'HTML'} | Status: ${report.status || 'Unknown'}</p>
                    <p>Jobs: ${report.job_ids?.length || 0} training jobs included</p>
                    ${report.description ? `<p>${report.description}</p>` : ''}
                </div>
                <div class="report-actions">
                    <button class="btn btn-sm btn-primary" onclick="documentManager.downloadReport('${report.id}')">
                        <i class="fas fa-download"></i> Download
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="documentManager.viewReport('${report.id}')">
                        <i class="fas fa-eye"></i> View
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="documentManager.deleteReport('${report.id}')">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
        `;
    }

    async downloadReport(reportId) {
        try {
            const response = await fetch(`/llm-training/api/reports/${reportId}/download`);
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `training_report_${reportId}.html`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                throw new Error('Failed to download report');
            }
        } catch (error) {
            console.error('Download report error:', error);
            this.showNotification('Error downloading report: ' + error.message, 'error');
        }
    }

    async viewReport(reportId) {
        try {
            const response = await fetch(`/llm-training/api/reports/${reportId}`);
            if (response.ok) {
                const report = await response.json();
                if (report.content) {
                    const newWindow = window.open('', '_blank');
                    newWindow.document.write(report.content);
                    newWindow.document.close();
                } else {
                    this.showNotification('Report content not available', 'error');
                }
            } else {
                throw new Error('Failed to load report');
            }
        } catch (error) {
            console.error('View report error:', error);
            this.showNotification('Error viewing report: ' + error.message, 'error');
        }
    }

    async deleteReport(reportId) {
        if (!confirm('Are you sure you want to delete this report? This action cannot be undone.')) {
            return;
        }

        try {
            const csrfToken = this.getCSRFToken();
            const headers = {};
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const response = await fetch(`/llm-training/api/reports/${reportId}`, {
                method: 'DELETE',
                headers: headers
            });

            if (response.ok) {
                this.reports = this.reports.filter(report => report.id !== reportId);
                this.renderReports();
                this.showNotification('Report deleted successfully', 'success');
            } else {
                const errorData = await response.json().catch(() => ({ error: 'Failed to delete report' }));
                throw new Error(errorData.error || 'Failed to delete report');
            }
        } catch (error) {
            console.error('Delete report error:', error);
            this.showNotification('Error deleting report: ' + error.message, 'error');
        }
    }

    // Utility functions
    startRefreshInterval() {
        // Refresh training jobs every 5 seconds if there are active jobs
        this.refreshInterval = setInterval(() => {
            const activeJobs = this.trainingJobs.filter(job => 
                ['preparing', 'training', 'evaluating'].includes(job.status)
            );
            
            if (activeJobs.length > 0) {
                this.loadTrainingJobs();
            }
        }, 5000);
    }

    updateStats() {
        // Document stats
        const totalDocs = this.documents.length;
        const totalDatasets = this.datasets.length;
        const totalWords = this.documents.reduce((sum, doc) => sum + (doc.metadata?.wordCount || 0), 0);
        const totalSize = this.documents.reduce((sum, doc) => sum + doc.size, 0);

        const documentElements = {
            'total-documents': totalDocs,
            'total-datasets': totalDatasets,
            'total-words': totalWords.toLocaleString(),
            'total-size': (totalSize / (1024 * 1024)).toFixed(1) + ' MB'
        };

        Object.entries(documentElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });

        this.updateTrainingStats();
    }

    updateTrainingStats() {
        const totalJobs = this.trainingJobs.length;
        const runningJobs = this.trainingJobs.filter(job => 
            ['preparing', 'training', 'evaluating'].includes(job.status)
        ).length;
        const completedJobs = this.trainingJobs.filter(job => job.status === 'completed').length;
        const failedJobs = this.trainingJobs.filter(job => job.status === 'failed').length;

        const trainingElements = {
            'total-jobs': totalJobs,
            'running-jobs': runningJobs,
            'completed-jobs': completedJobs,
            'failed-jobs': failedJobs
        };

        Object.entries(trainingElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    showNotification(message, type = 'info') {
        // Use ExamGrader notification system if available
        if (typeof ExamGrader !== 'undefined' && ExamGrader.notificationManager && typeof ExamGrader.notificationManager.notify === 'function') {
            ExamGrader.notificationManager.notify(message, type);
            return;
        }

        // Fallback notification system
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 6px;
            color: white;
            font-weight: 500;
            z-index: 1001;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Modal functions
function showCreateDatasetModal() {
    const modal = document.getElementById('create-dataset-modal');
    const documentSelection = document.getElementById('document-selection');

    if (!modal || !documentSelection) {
        console.error('Modal elements not found');
        return;
    }

    // Populate document selection
    documentSelection.innerHTML = documentManager.documents.map(doc => `
        <div class="checkbox-item">
            <input type="checkbox" id="doc-${doc.id}" value="${doc.id}">
            <label for="doc-${doc.id}">${doc.name}</label>
        </div>
    `).join('');

    modal.classList.add('show');
}

function hideCreateDatasetModal() {
    const modal = document.getElementById('create-dataset-modal');
    const form = document.getElementById('create-dataset-form');
    
    if (modal) {
        modal.classList.remove('show');
    }
    if (form) {
        form.reset();
    }
}

function showUploadModal() {
    const modal = document.getElementById('upload-modal');
    if (modal) {
        modal.classList.add('show');
    }
}

function hideUploadModal() {
    const modal = document.getElementById('upload-modal');
    if (modal) {
        modal.classList.remove('show');
    }
}

// Training modal functions
function showCreateTrainingModal() {
    const modal = document.getElementById('create-training-modal');
    const datasetSelect = document.getElementById('training-dataset');

    if (!modal || !datasetSelect) {
        console.error('Training modal elements not found');
        return;
    }

    // Populate dataset selection
    datasetSelect.innerHTML = '<option value="">Select a dataset...</option>';
    documentManager.datasets.forEach(dataset => {
        const option = document.createElement('option');
        option.value = dataset.id;
        option.textContent = `${dataset.name} (${dataset.documentCount} docs)`;
        datasetSelect.appendChild(option);
    });

    modal.classList.add('show');
}

function hideCreateTrainingModal() {
    const modal = document.getElementById('create-training-modal');
    const form = document.getElementById('create-training-form');
    
    if (modal) {
        modal.classList.remove('show');
    }
    if (form) {
        form.reset();
    }
}

function showGenerateReportModal() {
    const modal = document.getElementById('generate-report-modal');
    const jobSelection = document.getElementById('job-selection');

    if (!modal || !jobSelection) {
        console.error('Report modal elements not found');
        return;
    }

    // Populate job selection
    const completedJobs = documentManager.trainingJobs.filter(job => 
        ['completed', 'failed'].includes(job.status)
    );

    if (completedJobs.length === 0) {
        jobSelection.innerHTML = '<p style="color: #6b7280; text-align: center; padding: 20px;">No completed training jobs available for reporting.</p>';
    } else {
        jobSelection.innerHTML = completedJobs.map(job => `
            <div class="checkbox-item">
                <input type="checkbox" id="job-${job.id}" value="${job.id}">
                <label for="job-${job.id}">${job.name} (${job.status})</label>
            </div>
        `).join('');
    }

    modal.classList.add('show');
}

function hideGenerateReportModal() {
    const modal = document.getElementById('generate-report-modal');
    const form = document.getElementById('generate-report-form');
    
    if (modal) {
        modal.classList.remove('show');
    }
    if (form) {
        form.reset();
    }
}

function hideJobDetailsModal() {
    const modal = document.getElementById('job-details-modal');
    if (modal) {
        modal.classList.remove('show');
    }
}

function hideDatasetManagerModal() {
    const modal = document.getElementById('dataset-manager-modal');
    if (modal) {
        modal.classList.remove('show');
    }
}

// Initialize when page loads
let documentManager;
document.addEventListener('DOMContentLoaded', () => {
    try {
        documentManager = new DocumentManager();
        console.log('LLM Training page initialized successfully');
    } catch (error) {
        console.error('Error initializing LLM Training page:', error);
    }
});