// Enhanced Upload Functionality for Exam Grader

class EnhancedUploader {
    constructor() {
        this.files = {
            guide: null,
            submission: null
        };
        this.maxFileSize = 50 * 1024 * 1024; // 50MB
        this.allowedTypes = {
            guide: ['.pdf', '.docx', '.txt'],
            submission: ['.pdf', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']
        };
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupFileInputs();
        this.setupFormSubmission();
    }

    setupEventListeners() {
        // File input change events
        document.getElementById('markingGuide').addEventListener('change', (e) => {
            this.handleFileSelect(e, 'guide');
        });

        document.getElementById('studentSubmission').addEventListener('change', (e) => {
            this.handleFileSelect(e, 'submission');
        });

        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.addEventListener(eventName, this.preventDefaults, false);
        });
    }

    setupFileInputs() {
        // Add file size validation
        const inputs = ['markingGuide', 'studentSubmission'];
        inputs.forEach(inputId => {
            const input = document.getElementById(inputId);
            input.addEventListener('change', (e) => {
                this.validateFile(e.target.files[0], inputId.includes('marking') ? 'guide' : 'submission');
            });
        });
    }

    setupFormSubmission() {
        const form = document.getElementById('uploadForm');
        const submitBtn = document.getElementById('submitBtn');

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            if (this.validateForm()) {
                this.submitForm();
            }
        });

        // Update submit button state
        this.updateSubmitButton();
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    handleFileSelect(event, type) {
        const file = event.target.files[0];
        if (file && this.validateFile(file, type)) {
            this.files[type] = file;
            this.showFilePreview(file, type);
            this.updateSubmitButton();
            this.showToast(`${type === 'guide' ? 'Marking guide' : 'Student submission'} uploaded successfully!`, 'success');
        }
    }

    validateFile(file, type) {
        // Check file size
        if (file.size > this.maxFileSize) {
            this.showToast(`File size exceeds 50MB limit. Please choose a smaller file.`, 'error');
            return false;
        }

        // Check file type
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!this.allowedTypes[type].includes(fileExtension)) {
            this.showToast(`Invalid file type. Allowed types: ${this.allowedTypes[type].join(', ')}`, 'error');
            return false;
        }

        return true;
    }

    showFilePreview(file, type) {
        const uploadArea = document.getElementById(`${type}UploadArea`);
        const preview = document.getElementById(`${type}Preview`);
        const fileName = document.getElementById(`${type}FileName`);
        const fileSize = document.getElementById(`${type}FileSize`);

        // Hide upload content and show preview
        uploadArea.querySelector('.upload-content').classList.add('d-none');
        preview.classList.remove('d-none');
        uploadArea.classList.add('has-file');

        // Update preview content
        fileName.textContent = file.name;
        fileSize.textContent = this.formatFileSize(file.size);

        // Add animation
        preview.classList.add('fade-in');
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    updateSubmitButton() {
        const submitBtn = document.getElementById('submitBtn');
        const hasAllFiles = this.files.guide && this.files.submission;
        
        submitBtn.disabled = !hasAllFiles;
        
        if (hasAllFiles) {
            submitBtn.classList.remove('btn-outline-primary');
            submitBtn.classList.add('btn-primary');
            submitBtn.innerHTML = '<i class="bi bi-play-circle-fill me-2"></i>Start Grading';
        } else {
            submitBtn.classList.add('btn-outline-primary');
            submitBtn.classList.remove('btn-primary');
            submitBtn.innerHTML = '<i class="bi bi-upload me-2"></i>Upload Files First';
        }
    }

    validateForm() {
        if (!this.files.guide) {
            this.showToast('Please upload a marking guide', 'error');
            return false;
        }
        if (!this.files.submission) {
            this.showToast('Please upload a student submission', 'error');
            return false;
        }
        return true;
    }

    async submitForm() {
        const formData = new FormData();
        formData.append('marking_guide', this.files.guide);
        formData.append('submission', this.files.submission);

        // Add processing options
        const options = ['detailedFeedback', 'criteriaMapping', 'confidenceScores', 'improvementSuggestions'];
        options.forEach(option => {
            const checkbox = document.getElementById(option);
            if (checkbox && checkbox.checked) {
                formData.append(option, 'true');
            }
        });

        this.showProgressModal();
        
        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                this.handleSuccess(result);
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            this.handleError(error);
        }
    }

    showProgressModal() {
        const modal = new bootstrap.Modal(document.getElementById('progressModal'));
        modal.show();
        this.simulateProgress();
    }

    simulateProgress() {
        const progressBar = document.getElementById('progressBar');
        const progressStage = document.getElementById('progressStage');
        const progressMessage = document.getElementById('progressMessage');
        
        const stages = [
            { progress: 25, stage: 'Uploading files...', message: 'Transferring your files to our servers' },
            { progress: 50, stage: 'Parsing documents...', message: 'Extracting text and analyzing structure' },
            { progress: 75, stage: 'AI Analysis...', message: 'Mapping criteria and generating feedback' },
            { progress: 100, stage: 'Complete!', message: 'Grading finished successfully' }
        ];

        let currentStage = 0;
        const interval = setInterval(() => {
            if (currentStage < stages.length) {
                const stage = stages[currentStage];
                progressBar.style.width = stage.progress + '%';
                progressStage.textContent = stage.stage;
                progressMessage.textContent = stage.message;
                
                // Update progress steps
                this.updateProgressStep(currentStage + 1);
                
                currentStage++;
            } else {
                clearInterval(interval);
                setTimeout(() => {
                    this.hideProgressModal();
                    this.showResultsModal();
                }, 1000);
            }
        }, 2000);
    }

    updateProgressStep(step) {
        for (let i = 1; i <= 4; i++) {
            const stepElement = document.getElementById(`step${i}`);
            if (i <= step) {
                stepElement.classList.add('completed');
                stepElement.classList.remove('active');
            } else if (i === step + 1) {
                stepElement.classList.add('active');
            }
        }
    }

    hideProgressModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('progressModal'));
        if (modal) modal.hide();
    }

    showResultsModal() {
        const modal = new bootstrap.Modal(document.getElementById('resultsModal'));
        modal.show();
    }

    handleSuccess(result) {
        this.showToast('Files uploaded and processed successfully!', 'success');
        // Reset form
        this.resetForm();
    }

    handleError(error) {
        this.hideProgressModal();
        this.showToast('Upload failed. Please try again.', 'error');
        console.error('Upload error:', error);
    }

    resetForm() {
        this.files = { guide: null, submission: null };
        
        // Reset file inputs
        document.getElementById('markingGuide').value = '';
        document.getElementById('studentSubmission').value = '';
        
        // Reset upload areas
        ['guide', 'submission'].forEach(type => {
            const uploadArea = document.getElementById(`${type}UploadArea`);
            const preview = document.getElementById(`${type}Preview`);
            
            uploadArea.querySelector('.upload-content').classList.remove('d-none');
            preview.classList.add('d-none');
            uploadArea.classList.remove('has-file');
        });
        
        this.updateSubmitButton();
    }

    showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-${type === 'error' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        // Add to toast container
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(container);
        }
        
        container.appendChild(toast);
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
}

// Drag and Drop Handlers (Global functions for template)
function handleDragEnter(event, type) {
    event.preventDefault();
    const uploadArea = document.getElementById(`${type}UploadArea`);
    uploadArea.classList.add('dragover');
}

function handleDragLeave(event, type) {
    event.preventDefault();
    const uploadArea = document.getElementById(`${type}UploadArea`);
    uploadArea.classList.remove('dragover');
}

function handleDragOver(event) {
    event.preventDefault();
}

function handleDrop(event, type) {
    event.preventDefault();
    const uploadArea = document.getElementById(`${type}UploadArea`);
    uploadArea.classList.remove('dragover');
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        const input = document.getElementById(type === 'guide' ? 'markingGuide' : 'studentSubmission');
        input.files = files;
        input.dispatchEvent(new Event('change'));
    }
}

function removeFile(type) {
    if (window.uploader) {
        window.uploader.files[type] = null;
        
        const uploadArea = document.getElementById(`${type}UploadArea`);
        const preview = document.getElementById(`${type}Preview`);
        
        uploadArea.querySelector('.upload-content').classList.remove('d-none');
        preview.classList.add('d-none');
        uploadArea.classList.remove('has-file');
        
        // Reset file input
        const input = document.getElementById(type === 'guide' ? 'markingGuide' : 'studentSubmission');
        input.value = '';
        
        window.uploader.updateSubmitButton();
        window.uploader.showToast(`${type === 'guide' ? 'Marking guide' : 'Student submission'} removed`, 'info');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.uploader = new EnhancedUploader();
});
