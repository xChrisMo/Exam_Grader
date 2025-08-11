/**
 * Enhanced Drag-and-Drop File Upload Component
 * Built with accessibility, progress tracking, and mobile support
 */

class DragDropUpload {
    constructor(options = {}) {
        this.options = {
            container: null,
            input: null,
            multiple: false,
            maxFiles: 10,
            maxFileSize: Infinity, // No file size limit
            acceptedTypes: ['.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'],
            showPreview: true,
            showProgress: true,
            uploadUrl: null,
            onFileSelect: null,
            onUploadProgress: null,
            onUploadComplete: null,
            onError: null,
            ...options
        };

        this.files = [];
        this.uploading = false;
        this.dragCounter = 0;

        this.init();
    }

    init() {
        this.setupContainer();
        this.setupEventListeners();
        this.setupAccessibility();
    }

    setupContainer() {
        if (typeof this.options.container === 'string') {
            this.container = document.querySelector(this.options.container);
        } else {
            this.container = this.options.container;
        }

        if (!this.container) {
            throw new Error('Container element not found');
        }

        // Create or find file input
        if (this.options.input) {
            if (typeof this.options.input === 'string') {
                this.input = document.querySelector(this.options.input);
            } else {
                this.input = this.options.input;
            }
        } else {
            this.input = this.container.querySelector('input[type="file"]');
        }

        if (!this.input) {
            this.input = this.createFileInput();
            this.container.appendChild(this.input);
        }

        // Setup container classes
        this.container.classList.add('drag-drop-upload');
        this.setupContainerHTML();
    }

    createFileInput() {
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = this.options.multiple;
        input.accept = this.options.acceptedTypes.join(',');
        input.className = 'sr-only';
        input.id = `file-input-${Date.now()}`;
        return input;
    }

    setupContainerHTML() {
        // Only setup if container doesn't already have the structure
        if (!this.container.querySelector('.drop-zone')) {
            this.container.innerHTML = `
                <div class="drop-zone border-2 border-dashed border-gray-300 rounded-lg p-8 text-center transition-colors duration-200 hover:border-gray-400 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-opacity-50">
                    <div class="drop-zone-content">
                        <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" stroke="currentColor" fill="none" viewBox="0 0 48 48" aria-hidden="true">
                            <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                        <div class="text-lg font-medium text-gray-900 mb-2">
                            <label for="${this.input.id}" class="cursor-pointer text-blue-600 hover:text-blue-500 focus:outline-none focus:underline">
                                Choose files
                            </label>
                            <span class="text-gray-700"> or drag and drop</span>
                        </div>
                        <p class="text-sm text-gray-500 mb-4">
                            ${this.options.acceptedTypes.join(', ').toUpperCase()} up to ${this.formatFileSize(this.options.maxFileSize)}
                        </p>
                        <div class="file-requirements text-xs text-gray-400">
                            ${this.options.multiple ? `Maximum ${this.options.maxFiles} files` : 'Single file only'}
                        </div>
                    </div>
                    <div class="drop-zone-overlay absolute inset-0 bg-blue-50 border-2 border-blue-300 rounded-lg flex items-center justify-center opacity-0 transition-opacity duration-200 pointer-events-none">
                        <div class="text-blue-600 font-medium">
                            <svg class="mx-auto h-8 w-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 12l3 3m0 0l3-3m-3 3V9"/>
                            </svg>
                            Drop files here
                        </div>
                    </div>
                </div>
                <div class="file-list mt-4 space-y-2"></div>
                <div class="upload-progress mt-4 hidden">
                    <div class="bg-gray-200 rounded-full h-2 mb-2">
                        <div class="progress-bar bg-blue-600 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
                    </div>
                    <div class="flex justify-between text-sm text-gray-600">
                        <span class="progress-text">Uploading...</span>
                        <span class="progress-percentage">0%</span>
                    </div>
                </div>
            `;

            // Make drop zone relative for overlay positioning
            this.container.querySelector('.drop-zone').style.position = 'relative';
        }

        // Get references to elements
        this.dropZone = this.container.querySelector('.drop-zone');
        this.dropZoneOverlay = this.container.querySelector('.drop-zone-overlay');
        this.fileList = this.container.querySelector('.file-list');
        this.progressContainer = this.container.querySelector('.upload-progress');
        this.progressBar = this.container.querySelector('.progress-bar');
        this.progressText = this.container.querySelector('.progress-text');
        this.progressPercentage = this.container.querySelector('.progress-percentage');
    }

    setupEventListeners() {
        // File input change
        this.input.addEventListener('change', this.handleFileSelect.bind(this));

        // Drag and drop events
        this.dropZone.addEventListener('dragenter', this.handleDragEnter.bind(this));
        this.dropZone.addEventListener('dragover', this.handleDragOver.bind(this));
        this.dropZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.dropZone.addEventListener('drop', this.handleDrop.bind(this));

        // Click to select files
        this.dropZone.addEventListener('click', (e) => {
            if (e.target === this.dropZone || e.target.closest('.drop-zone-content')) {
                this.input.click();
            }
        });

        // Keyboard support
        this.dropZone.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.input.click();
            }
        });

        // Paste support
        document.addEventListener('paste', this.handlePaste.bind(this));
    }

    setupAccessibility() {
        this.dropZone.setAttribute('tabindex', '0');
        this.dropZone.setAttribute('role', 'button');
        this.dropZone.setAttribute('aria-label', 'Click to select files or drag and drop files here');
        this.dropZone.setAttribute('aria-describedby', `${this.input.id}-description`);

        // Create description for screen readers
        const description = document.createElement('div');
        description.id = `${this.input.id}-description`;
        description.className = 'sr-only';
        description.textContent = `Accepted file types: ${this.options.acceptedTypes.join(', ')}. Maximum file size: ${this.formatFileSize(this.options.maxFileSize)}. ${this.options.multiple ? `Maximum ${this.options.maxFiles} files.` : 'Single file only.'}`;
        this.container.appendChild(description);
    }

    handleDragEnter(e) {
        e.preventDefault();
        e.stopPropagation();
        this.dragCounter++;
        
        if (this.dragCounter === 1) {
            this.dropZone.classList.add('drag-over');
            this.dropZoneOverlay.style.opacity = '1';
        }
    }

    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        this.dragCounter--;
        
        if (this.dragCounter === 0) {
            this.dropZone.classList.remove('drag-over');
            this.dropZoneOverlay.style.opacity = '0';
        }
    }

    handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        
        this.dragCounter = 0;
        this.dropZone.classList.remove('drag-over');
        this.dropZoneOverlay.style.opacity = '0';
        
        const files = Array.from(e.dataTransfer.files);
        this.processFiles(files);
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.processFiles(files);
    }

    handlePaste(e) {
        if (!this.container.contains(document.activeElement)) return;
        
        const items = e.clipboardData?.items;
        if (!items) return;
        
        const files = [];
        for (let item of items) {
            if (item.kind === 'file') {
                files.push(item.getAsFile());
            }
        }
        
        if (files.length > 0) {
            e.preventDefault();
            this.processFiles(files);
        }
    }

    processFiles(files) {
        const validFiles = [];
        const errors = [];

        for (let file of files) {
            const validation = this.validateFile(file);
            if (validation.valid) {
                validFiles.push(file);
            } else {
                errors.push({ file, error: validation.error });
            }
        }

        // Check total file count
        if (!this.options.multiple && validFiles.length > 1) {
            errors.push({ error: 'Only one file is allowed' });
            return;
        }

        if (this.options.multiple && (this.files.length + validFiles.length) > this.options.maxFiles) {
            errors.push({ error: `Maximum ${this.options.maxFiles} files allowed` });
            return;
        }

        // Add valid files
        if (!this.options.multiple) {
            this.files = validFiles;
        } else {
            this.files.push(...validFiles);
        }

        // Update UI
        this.updateFileList();
        
        // Show errors
        if (errors.length > 0) {
            this.showErrors(errors);
        }

        // Callback
        if (this.options.onFileSelect) {
            this.options.onFileSelect(this.files);
        }

        // Announce to screen readers
        this.announceFileSelection(validFiles.length, errors.length);
    }

    validateFile(file) {
        // Check file size
        if (file.size > this.options.maxFileSize) {
            return {
                valid: false,
                error: `File "${file.name}" is too large. Maximum size is ${this.formatFileSize(this.options.maxFileSize)}`
            };
        }

        // Check file type
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        if (!this.options.acceptedTypes.includes(extension)) {
            return {
                valid: false,
                error: `File "${file.name}" has an unsupported format. Accepted types: ${this.options.acceptedTypes.join(', ')}`
            };
        }

        return { valid: true };
    }

    updateFileList() {
        this.fileList.innerHTML = '';
        
        this.files.forEach((file, index) => {
            const fileItem = this.createFileItem(file, index);
            this.fileList.appendChild(fileItem);
        });

        // Update drop zone visibility
        if (this.files.length > 0 && !this.options.multiple) {
            this.dropZone.style.display = 'none';
        } else {
            this.dropZone.style.display = 'block';
        }
    }

    createFileItem(file, index) {
        const item = document.createElement('div');
        item.className = 'file-item bg-gray-50 border border-gray-200 rounded-lg p-4 flex items-center justify-between';
        
        item.innerHTML = `
            <div class="flex items-center flex-1 min-w-0">
                <div class="flex-shrink-0">
                    ${this.getFileIcon(file)}
                </div>
                <div class="ml-3 flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-900 truncate" title="${file.name}">
                        ${file.name}
                    </div>
                    <div class="text-sm text-gray-500">
                        ${this.formatFileSize(file.size)} • ${this.getFileType(file)}
                    </div>
                </div>
            </div>
            <div class="flex items-center space-x-2">
                ${this.options.showPreview && this.isImageFile(file) ? `
                    <button type="button" class="preview-btn text-blue-600 hover:text-blue-500 text-sm" data-index="${index}">
                        Preview
                    </button>
                ` : ''}
                <button type="button" class="remove-btn text-red-600 hover:text-red-500" data-index="${index}" aria-label="Remove ${file.name}">
                    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>
        `;

        // Add event listeners
        const removeBtn = item.querySelector('.remove-btn');
        removeBtn.addEventListener('click', () => this.removeFile(index));

        const previewBtn = item.querySelector('.preview-btn');
        if (previewBtn) {
            previewBtn.addEventListener('click', () => this.previewFile(index));
        }

        return item;
    }

    getFileIcon(file) {
        const extension = file.name.split('.').pop().toLowerCase();
        const iconClass = 'h-8 w-8';
        
        if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'].includes(extension)) {
            return `<svg class="${iconClass} text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>`;
        } else if (['pdf'].includes(extension)) {
            return `<svg class="${iconClass} text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>`;
        } else if (['doc', 'docx'].includes(extension)) {
            return `<svg class="${iconClass} text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>`;
        } else {
            return `<svg class="${iconClass} text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>`;
        }
    }

    getFileType(file) {
        const extension = file.name.split('.').pop().toLowerCase();
        const types = {
            pdf: 'PDF Document',
            doc: 'Word Document',
            docx: 'Word Document',
            jpg: 'JPEG Image',
            jpeg: 'JPEG Image',
            png: 'PNG Image',
            gif: 'GIF Image',
            bmp: 'BMP Image',
            tiff: 'TIFF Image'
        };
        return types[extension] || extension.toUpperCase();
    }

    isImageFile(file) {
        const extension = file.name.split('.').pop().toLowerCase();
        return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'].includes(extension);
    }

    removeFile(index) {
        this.files.splice(index, 1);
        this.updateFileList();
        
        if (this.options.onFileSelect) {
            this.options.onFileSelect(this.files);
        }

        // Announce to screen readers
        if (window.UIComponents) {
            window.UIComponents.announce('File removed');
        }
    }

    previewFile(index) {
        const file = this.files[index];
        if (!this.isImageFile(file)) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            this.showImagePreview(file.name, e.target.result);
        };
        reader.readAsDataURL(file);
    }

    showImagePreview(fileName, dataUrl) {
        if (!window.UIComponents) return;

        const previewContent = document.createElement('div');
        previewContent.className = 'text-center';
        previewContent.innerHTML = `
            <img src="${dataUrl}" alt="Preview of ${fileName}" class="max-w-full max-h-96 mx-auto rounded-lg shadow-lg">
            <p class="mt-4 text-sm text-gray-600">${fileName}</p>
        `;

        const modal = window.UIComponents.createModal({
            title: 'File Preview',
            content: previewContent,
            size: 'lg'
        });

        document.body.appendChild(modal);
    }

    showErrors(errors) {
        if (!window.UIComponents) {
            console.error('Errors:', errors);
            return;
        }

        errors.forEach(({ error }) => {
            const alert = window.UIComponents.createAlert({
                message: error,
                variant: 'danger',
                dismissible: true
            });
            
            this.container.insertBefore(alert, this.container.firstChild);
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, 5000);
        });
    }

    announceFileSelection(validCount, errorCount) {
        if (!window.UIComponents) return;

        let message = '';
        if (validCount > 0) {
            message += `${validCount} file${validCount > 1 ? 's' : ''} selected. `;
        }
        if (errorCount > 0) {
            message += `${errorCount} file${errorCount > 1 ? 's' : ''} rejected. `;
        }
        
        if (message) {
            window.UIComponents.announce(message.trim());
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Upload functionality
    async upload() {
        if (!this.options.uploadUrl || this.files.length === 0 || this.uploading) {
            return;
        }

        this.uploading = true;
        this.showProgress();

        try {
            const formData = new FormData();
            
            if (this.options.multiple) {
                this.files.forEach((file, index) => {
                    formData.append(`files[${index}]`, file);
                });
            } else {
                formData.append('file', this.files[0]);
            }

            const xhr = new XMLHttpRequest();
            
            // Progress tracking
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentage = Math.round((e.loaded / e.total) * 100);
                    this.updateProgress(percentage);
                    
                    if (this.options.onUploadProgress) {
                        this.options.onUploadProgress(percentage, e.loaded, e.total);
                    }
                }
            });

            // Handle completion
            xhr.addEventListener('load', () => {
                this.uploading = false;
                this.hideProgress();
                
                if (xhr.status >= 200 && xhr.status < 300) {
                    const response = JSON.parse(xhr.responseText);
                    if (this.options.onUploadComplete) {
                        this.options.onUploadComplete(response);
                    }
                    this.reset();
                } else {
                    // Try to parse error response for detailed message
                    let errorMessage = `Upload failed: ${xhr.statusText}`;
                    try {
                        const errorResponse = JSON.parse(xhr.responseText);
                        if (errorResponse.error) {
                            errorMessage = errorResponse.error;
                            // Add details if available
                            if (errorResponse.details) {
                                errorMessage += `\n\n${errorResponse.details}`;
                            }
                        }
                    } catch (e) {
                        // Keep default error message if JSON parsing fails
                    }
                    this.handleUploadError(errorMessage);
                }
            });

            // Handle errors
            xhr.addEventListener('error', () => {
                this.uploading = false;
                this.hideProgress();
                this.handleUploadError('Upload failed: Network error. Please check your internet connection and try again.');
            });

            // Send request
            xhr.open('POST', this.options.uploadUrl);
            
            // Add CSRF token if available
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            if (csrfToken) {
                xhr.setRequestHeader('X-CSRFToken', csrfToken);
            }
            
            xhr.send(formData);
            
        } catch (error) {
            this.uploading = false;
            this.hideProgress();
            this.handleUploadError(`Upload failed: ${error.message}`);
        }
    }

    showProgress() {
        if (this.progressContainer) {
            this.progressContainer.classList.remove('hidden');
        }
    }

    hideProgress() {
        if (this.progressContainer) {
            this.progressContainer.classList.add('hidden');
        }
    }

    updateProgress(percentage) {
        if (this.progressBar) {
            this.progressBar.style.width = `${percentage}%`;
        }
        if (this.progressPercentage) {
            this.progressPercentage.textContent = `${percentage}%`;
        }
        if (this.progressText) {
            this.progressText.textContent = percentage === 100 ? 'Processing...' : 'Uploading...';
        }
    }

    handleUploadError(error) {
        if (this.options.onError) {
            this.options.onError(error);
        } else {
            this.showErrors([{ error }]);
        }
    }

    // Public methods
    getFiles() {
        return this.files;
    }

    clearFiles() {
        this.files = [];
        this.updateFileList();
    }

    reset() {
        this.clearFiles();
        this.input.value = '';
        this.hideProgress();
        this.updateProgress(0);
    }

    setOptions(newOptions) {
        this.options = { ...this.options, ...newOptions };
    }

    destroy() {
        // Remove event listeners
        this.input.removeEventListener('change', this.handleFileSelect);
        this.dropZone.removeEventListener('dragenter', this.handleDragEnter);
        this.dropZone.removeEventListener('dragover', this.handleDragOver);
        this.dropZone.removeEventListener('dragleave', this.handleDragLeave);
        this.dropZone.removeEventListener('drop', this.handleDrop);
        document.removeEventListener('paste', this.handlePaste);
        
        // Clear files
        this.files = [];
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DragDropUpload;
}

// Global registration
if (typeof window !== 'undefined') {
    window.DragDropUpload = DragDropUpload;
}