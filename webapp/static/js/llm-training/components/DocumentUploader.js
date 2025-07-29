/**
 * Document Uploader Component for LLM Training
 * Specialized uploader for training documents with validation and processing
 */

class DocumentUploader {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' 
            ? document.querySelector(container) 
            : container;
            
        if (!this.container) {
            throw new Error('DocumentUploader: Container not found');
        }
        
        this.options = {
            maxFileSize: 10 * 1024 * 1024, // 10MB
            acceptedTypes: ['.pdf', '.txt', '.docx', '.doc'],
            maxFiles: 5,
            uploadUrl: '/api/llm-training/upload-document',
            ...options
        };
        
        this.files = [];
        this.uploadQueue = [];
        this.isUploading = false;
        
        this.init();
    }
    
    init() {
        this.createUploadInterface();
        this.setupEventListeners();
    }
    
    createUploadInterface() {
        this.container.innerHTML = `
            <div class="document-uploader">
                <div class="upload-area" id="upload-area">
                    <div class="upload-content">
                        <i class="fas fa-cloud-upload-alt text-4xl text-gray-400 mb-4"></i>
                        <h3 class="text-lg font-medium text-gray-900 mb-2">Upload Training Documents</h3>
                        <p class="text-sm text-gray-500 mb-4">
                            Drag and drop files here or click to browse
                        </p>
                        <button type="button" class="btn btn-primary" id="browse-btn">
                            Browse Files
                        </button>
                        <input type="file" id="file-input" multiple accept="${this.options.acceptedTypes.join(',')}" style="display: none;">
                    </div>
                </div>
                <div class="file-list" id="file-list"></div>
                <div class="upload-progress" id="upload-progress" style="display: none;">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill"></div>
                    </div>
                    <div class="progress-text" id="progress-text">Uploading...</div>
                </div>
            </div>
        `;
    }
    
    setupEventListeners() {
        const uploadArea = this.container.querySelector('#upload-area');
        const fileInput = this.container.querySelector('#file-input');
        const browseBtn = this.container.querySelector('#browse-btn');
        
        // Drag and drop events
        uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
        uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
        uploadArea.addEventListener('drop', this.handleDrop.bind(this));
        
        // File input events
        fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        browseBtn.addEventListener('click', () => fileInput.click());
    }
    
    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        this.container.querySelector('#upload-area').classList.add('drag-over');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        this.container.querySelector('#upload-area').classList.remove('drag-over');
    }
    
    handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        this.container.querySelector('#upload-area').classList.remove('drag-over');
        
        const files = Array.from(e.dataTransfer.files);
        this.processFiles(files);
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.processFiles(files);
    }
    
    processFiles(files) {
        const validFiles = files.filter(file => this.validateFile(file));
        
        if (validFiles.length === 0) {
            return;
        }
        
        this.files = [...this.files, ...validFiles];
        this.updateFileList();
        
        if (this.options.autoUpload) {
            this.startUpload();
        }
    }
    
    validateFile(file) {
        // Check file size
        if (file.size > this.options.maxFileSize) {
            this.showError(`File "${file.name}" is too large. Maximum size is ${this.formatFileSize(this.options.maxFileSize)}.`);
            return false;
        }
        
        // Check file type
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!this.options.acceptedTypes.includes(fileExtension)) {
            this.showError(`File "${file.name}" has an unsupported format. Accepted formats: ${this.options.acceptedTypes.join(', ')}.`);
            return false;
        }
        
        // Check total file count
        if (this.files.length >= this.options.maxFiles) {
            this.showError(`Maximum ${this.options.maxFiles} files allowed.`);
            return false;
        }
        
        return true;
    }
    
    updateFileList() {
        const fileList = this.container.querySelector('#file-list');
        
        if (this.files.length === 0) {
            fileList.innerHTML = '';
            return;
        }
        
        fileList.innerHTML = this.files.map((file, index) => `
            <div class="file-item" data-index="${index}">
                <div class="file-info">
                    <i class="fas fa-file-alt text-gray-400"></i>
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${this.formatFileSize(file.size)}</span>
                </div>
                <button type="button" class="remove-file" onclick="documentUploader.removeFile(${index})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
    }
    
    removeFile(index) {
        this.files.splice(index, 1);
        this.updateFileList();
    }
    
    async startUpload() {
        if (this.isUploading || this.files.length === 0) {
            return;
        }
        
        this.isUploading = true;
        this.showProgress();
        
        try {
            for (let i = 0; i < this.files.length; i++) {
                const file = this.files[i];
                await this.uploadFile(file, i);
                this.updateProgress((i + 1) / this.files.length * 100);
            }
            
            this.onUploadComplete();
        } catch (error) {
            this.onUploadError(error);
        } finally {
            this.isUploading = false;
            this.hideProgress();
        }
    }
    
    async uploadFile(file, index) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('index', index);
        
        const response = await fetch(this.options.uploadUrl, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Upload failed for ${file.name}: ${response.statusText}`);
        }
        
        return response.json();
    }
    
    showProgress() {
        this.container.querySelector('#upload-progress').style.display = 'block';
    }
    
    hideProgress() {
        this.container.querySelector('#upload-progress').style.display = 'none';
    }
    
    updateProgress(percentage) {
        const progressFill = this.container.querySelector('#progress-fill');
        const progressText = this.container.querySelector('#progress-text');
        
        progressFill.style.width = `${percentage}%`;
        progressText.textContent = `Uploading... ${Math.round(percentage)}%`;
    }
    
    showError(message) {
        console.error('DocumentUploader Error:', message);
        // You can implement a toast notification system here
        alert(message);
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    onUploadComplete() {
        console.log('All files uploaded successfully');
        this.files = [];
        this.updateFileList();
        
        if (this.options.onComplete) {
            this.options.onComplete();
        }
    }
    
    onUploadError(error) {
        console.error('Upload error:', error);
        this.showError(error.message);
        
        if (this.options.onError) {
            this.options.onError(error);
        }
    }
    
    destroy() {
        // Clean up event listeners and DOM
        this.container.innerHTML = '';
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DocumentUploader;
}

// Global initialization
if (typeof window !== 'undefined') {
    window.DocumentUploader = DocumentUploader;
}