/**
 * Duplicate Detection and Enhanced Upload Handling
 * 
 * This module provides frontend functionality for:
 * - File validation before upload
 * - Duplicate content detection
 * - Enhanced user feedback
 * - Progress tracking for uploads
 */

class DuplicateDetectionHandler {
    constructor() {
        this.apiBaseUrl = '/api/upload';
        this.supportedFormats = [];
        this.maxFileSizeMB = 50;
        this.currentUpload = null;
        
        this.init();
    }
    
    async init() {
        try {
            // Load supported formats
            await this.loadSupportedFormats();
            
            // Initialize event listeners
            this.initializeEventListeners();
            
            console.log('Duplicate detection handler initialized');
        } catch (error) {
            console.error('Failed to initialize duplicate detection handler:', error);
        }
    }
    
    async loadSupportedFormats() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/supported-formats`);
            const data = await response.json();
            
            if (data.success) {
                this.supportedFormats = data.supported_formats;
                this.maxFileSizeMB = data.max_file_size_mb;
                this.formatDescriptions = data.description;
            }
        } catch (error) {
            console.error('Failed to load supported formats:', error);
            // Fallback to default formats
            this.supportedFormats = ['pdf', 'docx', 'doc', 'txt', 'jpg', 'jpeg', 'png', 'tiff', 'bmp'];
        }
    }
    
    initializeEventListeners() {
        // File input change handlers
        document.addEventListener('change', (event) => {
            if (event.target.type === 'file' && event.target.hasAttribute('data-duplicate-check')) {
                this.handleFileSelection(event.target);
            }
        });
        
        // Form submission handlers
        document.addEventListener('submit', (event) => {
            const form = event.target;
            if (form.hasAttribute('data-upload-form')) {
                event.preventDefault();
                this.handleFormSubmission(form);
            }
        });
        
        // Drag and drop handlers
        document.addEventListener('dragover', (event) => {
            const dropZone = event.target.closest('[data-drop-zone]');
            if (dropZone) {
                event.preventDefault();
                dropZone.classList.add('drag-over');
            }
        });
        
        document.addEventListener('dragleave', (event) => {
            const dropZone = event.target.closest('[data-drop-zone]');
            if (dropZone && !dropZone.contains(event.relatedTarget)) {
                dropZone.classList.remove('drag-over');
            }
        });
        
        document.addEventListener('drop', (event) => {
            const dropZone = event.target.closest('[data-drop-zone]');
            if (dropZone) {
                event.preventDefault();
                dropZone.classList.remove('drag-over');
                
                const files = event.dataTransfer.files;
                if (files.length > 0) {
                    const fileInput = dropZone.querySelector('input[type="file"]');
                    if (fileInput) {
                        fileInput.files = files;
                        this.handleFileSelection(fileInput);
                    }
                }
            }
        });
    }
    
    async handleFileSelection(fileInput) {
        const file = fileInput.files[0];
        if (!file) return;
        
        const container = fileInput.closest('[data-upload-container]');
        if (!container) return;
        
        // Clear previous messages
        this.clearMessages(container);
        
        // Validate file
        const validation = this.validateFile(file);
        if (!validation.valid) {
            this.showError(container, validation.error);
            fileInput.value = '';
            return;
        }
        
        // Show file info
        this.showFileInfo(container, file);
        
        // Check for duplicates if enabled
        const checkDuplicates = fileInput.hasAttribute('data-check-duplicates');
        if (checkDuplicates) {
            await this.checkForDuplicates(fileInput, file, container);
        }
    }
    
    validateFile(file) {
        // Check file extension
        const extension = file.name.split('.').pop().toLowerCase();
        if (!this.supportedFormats.includes(extension)) {
            return {
                valid: false,
                error: `File type "${extension}" is not supported. Supported formats: ${this.supportedFormats.join(', ')}`
            };
        }
        
        // Check file size
        const fileSizeMB = file.size / (1024 * 1024);
        if (fileSizeMB > this.maxFileSizeMB) {
            return {
                valid: false,
                error: `File size (${fileSizeMB.toFixed(1)}MB) exceeds maximum allowed size (${this.maxFileSizeMB}MB)`
            };
        }
        
        return { valid: true };
    }
    
    async checkForDuplicates(fileInput, file, container) {
        try {
            this.showProgress(container, 'Checking for duplicate content...');
            
            const formData = new FormData();
            formData.append('file', file);
            
            // Determine check type
            const uploadType = fileInput.getAttribute('data-upload-type') || 'submission';
            formData.append('type', uploadType);
            
            // Add marking guide ID for submissions
            if (uploadType === 'submission') {
                const markingGuideId = this.getMarkingGuideId(container);
                if (markingGuideId) {
                    formData.append('marking_guide_id', markingGuideId);
                }
            }
            
            const response = await fetch(`${this.apiBaseUrl}/check-duplicate`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            this.hideProgress(container);
            
            if (result.success) {
                if (result.is_duplicate) {
                    this.showDuplicateWarning(container, result, fileInput);
                } else {
                    this.showSuccess(container, 'No duplicate content found. Ready to upload.');
                }
            } else {
                this.showWarning(container, result.error || 'Could not check for duplicates');
            }
            
        } catch (error) {
            console.error('Error checking for duplicates:', error);
            this.hideProgress(container);
            this.showWarning(container, 'Could not check for duplicates. Upload will proceed without duplicate detection.');
        }
    }
    
    async handleFormSubmission(form) {
        const container = form.closest('[data-upload-container]') || form;
        
        try {
            // Clear previous messages
            this.clearMessages(container);
            
            // Get file input
            const fileInput = form.querySelector('input[type="file"]');
            if (!fileInput || !fileInput.files[0]) {
                this.showError(container, 'Please select a file to upload');
                return;
            }
            
            const file = fileInput.files[0];
            
            // Validate file again
            const validation = this.validateFile(file);
            if (!validation.valid) {
                this.showError(container, validation.error);
                return;
            }
            
            // Prepare form data
            const formData = new FormData(form);
            
            // Determine upload endpoint
            const uploadType = fileInput.getAttribute('data-upload-type') || 'submission';
            const endpoint = uploadType === 'marking_guide' ? '/marking-guide' : '/submission';
            
            // Show upload progress
            this.showProgress(container, 'Uploading file...');
            
            // Disable form during upload
            this.setFormEnabled(form, false);
            
            // Upload file
            const response = await fetch(`${this.apiBaseUrl}${endpoint}`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            this.hideProgress(container);
            this.setFormEnabled(form, true);
            
            if (result.success) {
                this.showSuccess(container, result.message || 'File uploaded successfully');
                this.handleUploadSuccess(result, uploadType, container);
            } else {
                if (result.code === 'DUPLICATE_CONTENT') {
                    this.showDuplicateError(container, result);
                } else {
                    this.showError(container, result.error || 'Upload failed');
                }
            }
            
        } catch (error) {
            console.error('Error uploading file:', error);
            this.hideProgress(container);
            this.setFormEnabled(form, true);
            this.showError(container, 'Upload failed due to a network error');
        }
    }
    
    showFileInfo(container, file) {
        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(1);
        const extension = file.name.split('.').pop().toLowerCase();
        const description = this.formatDescriptions?.[extension] || 'File';
        
        const info = `
            <div class="file-info alert alert-info">
                <i class="fas fa-file"></i>
                <strong>${file.name}</strong> (${description}, ${fileSizeMB}MB)
            </div>
        `;
        
        this.showMessage(container, info, 'info');
    }
    
    showDuplicateWarning(container, result, fileInput) {
        const duplicateInfo = result.duplicate_submission || result.duplicate_guide;
        
        let warningHtml = `
            <div class="duplicate-warning alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Duplicate Content Detected</strong>
                <p>${result.message}</p>
        `;
        
        if (duplicateInfo) {
            warningHtml += `
                <div class="duplicate-details">
                    <small>
                        <strong>Original file:</strong> ${duplicateInfo.filename}<br>
                        <strong>Uploaded:</strong> ${new Date(duplicateInfo.created_at).toLocaleString()}
            `;
            
            if (duplicateInfo.student_name) {
                warningHtml += `<br><strong>Student:</strong> ${duplicateInfo.student_name} (${duplicateInfo.student_id})`;
            }
            
            warningHtml += `
                    </small>
                </div>
            `;
        }
        
        warningHtml += `
                <div class="duplicate-actions mt-2">
                    <button type="button" class="btn btn-sm btn-outline-primary" onclick="duplicateHandler.proceedWithUpload(this)">
                        <i class="fas fa-upload"></i> Upload Anyway
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" onclick="duplicateHandler.cancelUpload(this)">
                        <i class="fas fa-times"></i> Cancel
                    </button>
                </div>
            </div>
        `;
        
        this.showMessage(container, warningHtml, 'warning');
        
        // Store file input reference for later use
        container.setAttribute('data-pending-upload', 'true');
    }
    
    showDuplicateError(container, result) {
        const duplicateInfo = result.duplicate_info;
        
        let errorHtml = `
            <div class="duplicate-error alert alert-danger">
                <i class="fas fa-times-circle"></i>
                <strong>Upload Blocked - Duplicate Content</strong>
                <p>${result.error}</p>
        `;
        
        if (duplicateInfo) {
            errorHtml += `
                <div class="duplicate-details">
                    <small>
                        <strong>Existing file:</strong> ${duplicateInfo.filename}<br>
                        <strong>Uploaded:</strong> ${new Date(duplicateInfo.created_at).toLocaleString()}
                    </small>
                </div>
            `;
        }
        
        errorHtml += `</div>`;
        
        this.showMessage(container, errorHtml, 'error');
    }
    
    proceedWithUpload(button) {
        const container = button.closest('[data-upload-container]');
        const form = container.querySelector('form[data-upload-form]');
        
        if (form) {
            // Add flag to skip duplicate checking
            const skipDuplicateInput = document.createElement('input');
            skipDuplicateInput.type = 'hidden';
            skipDuplicateInput.name = 'check_duplicates';
            skipDuplicateInput.value = 'false';
            form.appendChild(skipDuplicateInput);
            
            // Clear messages and submit
            this.clearMessages(container);
            container.removeAttribute('data-pending-upload');
            this.handleFormSubmission(form);
        }
    }
    
    cancelUpload(button) {
        const container = button.closest('[data-upload-container]');
        const fileInput = container.querySelector('input[type="file"]');
        
        if (fileInput) {
            fileInput.value = '';
        }
        
        this.clearMessages(container);
        container.removeAttribute('data-pending-upload');
    }
    
    handleUploadSuccess(result, uploadType, container) {
        // Reset form
        const form = container.querySelector('form');
        if (form) {
            form.reset();
        }
        
        // Show additional success info
        if (result.content_hash) {
            const additionalInfo = `
                <div class="upload-success-details mt-2">
                    <small class="text-muted">
                        <i class="fas fa-check-circle"></i>
                        Content processed successfully
                        ${result.text_length ? `(${result.text_length} characters extracted)` : ''}
                    </small>
                </div>
            `;
            
            const successAlert = container.querySelector('.alert-success');
            if (successAlert) {
                successAlert.insertAdjacentHTML('beforeend', additionalInfo);
            }
        }
        
        // Trigger custom event for other components
        const event = new CustomEvent('uploadSuccess', {
            detail: { result, uploadType }
        });
        container.dispatchEvent(event);
        
        // Auto-redirect or refresh after delay
        setTimeout(() => {
            if (uploadType === 'submission') {
                // Redirect to submissions page or refresh
                window.location.href = '/submissions';
            } else if (uploadType === 'marking_guide') {
                // Redirect to marking guides page or refresh
                window.location.href = '/marking-guides';
            }
        }, 2000);
    }
    
    getMarkingGuideId(container) {
        // Try to get from form input
        const input = container.querySelector('input[name="marking_guide_id"], select[name="marking_guide_id"]');
        if (input) {
            return input.value;
        }
        
        // Try to get from data attribute
        return container.getAttribute('data-marking-guide-id');
    }
    
    showProgress(container, message) {
        const progressHtml = `
            <div class="upload-progress alert alert-info">
                <div class="d-flex align-items-center">
                    <div class="spinner-border spinner-border-sm me-2" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <span>${message}</span>
                </div>
            </div>
        `;
        
        this.showMessage(container, progressHtml, 'progress');
    }
    
    hideProgress(container) {
        const progress = container.querySelector('.upload-progress');
        if (progress) {
            progress.remove();
        }
    }
    
    showMessage(container, html, type) {
        const messageContainer = this.getMessageContainer(container);
        messageContainer.innerHTML = html;
    }
    
    showSuccess(container, message) {
        const html = `
            <div class="alert alert-success">
                <i class="fas fa-check-circle"></i>
                ${message}
            </div>
        `;
        this.showMessage(container, html, 'success');
    }
    
    showError(container, message) {
        const html = `
            <div class="alert alert-danger">
                <i class="fas fa-times-circle"></i>
                ${message}
            </div>
        `;
        this.showMessage(container, html, 'error');
    }
    
    showWarning(container, message) {
        const html = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                ${message}
            </div>
        `;
        this.showMessage(container, html, 'warning');
    }
    
    clearMessages(container) {
        const messageContainer = this.getMessageContainer(container);
        messageContainer.innerHTML = '';
    }
    
    getMessageContainer(container) {
        let messageContainer = container.querySelector('.upload-messages');
        if (!messageContainer) {
            messageContainer = document.createElement('div');
            messageContainer.className = 'upload-messages';
            container.insertBefore(messageContainer, container.firstChild);
        }
        return messageContainer;
    }
    
    setFormEnabled(form, enabled) {
        const elements = form.querySelectorAll('input, button, select, textarea');
        elements.forEach(element => {
            element.disabled = !enabled;
        });
    }
}

// Initialize duplicate detection handler when DOM is ready
let duplicateHandler;
document.addEventListener('DOMContentLoaded', () => {
    duplicateHandler = new DuplicateDetectionHandler();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DuplicateDetectionHandler;
}