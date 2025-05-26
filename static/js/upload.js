/**
 * Exam Grader - Upload Page JavaScript
 * Handles file uploads, drag & drop, and form submission
 */

class UploadManager {
    constructor() {
        this.files = {
            guide: null,
            submission: null
        };
        this.maxFileSize = 10 * 1024 * 1024; // 10MB
        this.allowedTypes = {
            guide: ['.pdf', '.docx', '.txt'],
            submission: ['.pdf', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']
        };
        this.init();
    }

    init() {
        this.setupFileInputs();
        this.setupDragAndDrop();
        this.setupFormSubmission();
        this.updateSubmitButton();
    }

    setupFileInputs() {
        const guideInput = document.getElementById('markingGuide');
        const submissionInput = document.getElementById('studentSubmission');

        if (guideInput) {
            guideInput.addEventListener('change', (e) => {
                this.handleFileSelect(e, 'guide');
            });
        }

        if (submissionInput) {
            submissionInput.addEventListener('change', (e) => {
                this.handleFileSelect(e, 'submission');
            });
        }
    }

    setupDragAndDrop() {
        const guideArea = document.getElementById('guideUploadArea');
        const submissionArea = document.getElementById('submissionUploadArea');

        if (guideArea) {
            this.setupDropZone(guideArea, 'guide');
        }

        if (submissionArea) {
            this.setupDropZone(submissionArea, 'submission');
        }
    }

    setupDropZone(element, type) {
        element.addEventListener('dragover', (e) => {
            e.preventDefault();
            element.classList.add('dragover');
        });

        element.addEventListener('dragleave', (e) => {
            e.preventDefault();
            if (!element.contains(e.relatedTarget)) {
                element.classList.remove('dragover');
            }
        });

        element.addEventListener('drop', (e) => {
            e.preventDefault();
            element.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileDrop(files[0], type);
            }
        });
    }

    handleFileSelect(event, type) {
        const file = event.target.files[0];
        if (file) {
            this.processFile(file, type);
        }
    }

    handleFileDrop(file, type) {
        this.processFile(file, type);
    }

    processFile(file, type) {
        // Validate file
        const validation = this.validateFile(file, type);
        if (!validation.valid) {
            this.showError(validation.message);
            return;
        }

        // Store file
        this.files[type] = file;

        // Update UI
        this.updateFilePreview(file, type);
        this.updateUploadArea(type, true);
        this.updateSubmitButton();

        // Show success message
        ExamGraderUtils.showNotification(`${type === 'guide' ? 'Marking guide' : 'Submission'} uploaded successfully`, 'success', 3000);
    }

    validateFile(file, type) {
        // Check file size
        if (file.size > this.maxFileSize) {
            return {
                valid: false,
                message: `File size exceeds ${this.maxFileSize / (1024 * 1024)}MB limit`
            };
        }

        // Check file type
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!this.allowedTypes[type].includes(fileExtension)) {
            return {
                valid: false,
                message: `File type ${fileExtension} is not supported for ${type}`
            };
        }

        return { valid: true };
    }

    updateFilePreview(file, type) {
        const previewElement = document.getElementById(`${type}Preview`);
        const fileNameElement = document.getElementById(`${type}FileName`);
        const fileSizeElement = document.getElementById(`${type}FileSize`);

        if (previewElement && fileNameElement && fileSizeElement) {
            fileNameElement.textContent = file.name;
            fileSizeElement.textContent = ExamGraderUtils.formatFileSize(file.size);
            previewElement.classList.remove('d-none');
        }
    }

    updateUploadArea(type, hasFile) {
        const uploadArea = document.getElementById(`${type}UploadArea`);
        const uploadContent = uploadArea.querySelector('.upload-content');

        if (hasFile) {
            uploadArea.classList.add('has-file');
            uploadContent.classList.add('d-none');
        } else {
            uploadArea.classList.remove('has-file');
            uploadContent.classList.remove('d-none');
        }
    }

    removeFile(type) {
        this.files[type] = null;
        
        // Reset file input
        const input = document.getElementById(type === 'guide' ? 'markingGuide' : 'studentSubmission');
        if (input) {
            input.value = '';
        }

        // Update UI
        const previewElement = document.getElementById(`${type}Preview`);
        if (previewElement) {
            previewElement.classList.add('d-none');
        }

        this.updateUploadArea(type, false);
        this.updateSubmitButton();

        ExamGraderUtils.showNotification(`${type === 'guide' ? 'Marking guide' : 'Submission'} removed`, 'info', 2000);
    }

    updateSubmitButton() {
        const submitBtn = document.getElementById('submitBtn');
        const hasAllFiles = this.files.guide && this.files.submission;

        if (submitBtn) {
            submitBtn.disabled = !hasAllFiles;
            
            if (hasAllFiles) {
                submitBtn.innerHTML = '<i class="bi bi-play-circle-fill me-2"></i>Start Grading';
                submitBtn.classList.remove('btn-secondary');
                submitBtn.classList.add('btn-primary');
            } else {
                submitBtn.innerHTML = '<i class="bi bi-upload me-2"></i>Upload Both Files First';
                submitBtn.classList.remove('btn-primary');
                submitBtn.classList.add('btn-secondary');
            }
        }
    }

    setupFormSubmission() {
        const form = document.getElementById('uploadForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitForm();
            });
        }
    }

    async submitForm() {
        if (!this.files.guide || !this.files.submission) {
            this.showError('Please upload both marking guide and submission files');
            return;
        }

        try {
            // Show progress modal
            const progressModal = new bootstrap.Modal(document.getElementById('progressModal'));
            progressModal.show();

            // Prepare form data
            const formData = new FormData();
            formData.append('marking_guide', this.files.guide);
            formData.append('submission', this.files.submission);

            // Add processing options
            const options = this.getProcessingOptions();
            Object.keys(options).forEach(key => {
                formData.append(key, options[key]);
            });

            // Upload files
            const uploadResponse = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error(`Upload failed: ${uploadResponse.statusText}`);
            }

            const uploadResult = await uploadResponse.json();
            
            if (!uploadResult.success) {
                throw new Error(uploadResult.error || 'Upload failed');
            }

            // Join session for real-time updates
            if (window.examGraderApp) {
                window.examGraderApp.joinSession(uploadResult.session_id);
            }

            // Start processing
            const processResponse = await fetch('/api/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: uploadResult.session_id,
                    options: options
                })
            });

            if (!processResponse.ok) {
                throw new Error(`Processing failed: ${processResponse.statusText}`);
            }

            const processResult = await processResponse.json();
            
            if (!processResult.success) {
                throw new Error(processResult.error || 'Processing failed');
            }

            ExamGraderUtils.showNotification('Processing started successfully', 'success');

        } catch (error) {
            console.error('Submission error:', error);
            this.showError(error.message);
            
            // Hide progress modal
            const progressModal = bootstrap.Modal.getInstance(document.getElementById('progressModal'));
            if (progressModal) {
                progressModal.hide();
            }
        }
    }

    getProcessingOptions() {
        return {
            detailed_feedback: document.getElementById('detailedFeedback')?.checked || false,
            criteria_mapping: document.getElementById('criteriaMapping')?.checked || false,
            confidence_scores: document.getElementById('confidenceScores')?.checked || false,
            improvement_suggestions: document.getElementById('improvementSuggestions')?.checked || false
        };
    }

    showError(message) {
        ExamGraderUtils.showNotification(message, 'danger', 5000);
    }

    reset() {
        this.files = { guide: null, submission: null };
        
        // Reset file inputs
        const inputs = ['markingGuide', 'studentSubmission'];
        inputs.forEach(id => {
            const input = document.getElementById(id);
            if (input) input.value = '';
        });

        // Reset previews
        ['guide', 'submission'].forEach(type => {
            const preview = document.getElementById(`${type}Preview`);
            if (preview) preview.classList.add('d-none');
            this.updateUploadArea(type, false);
        });

        this.updateSubmitButton();
    }
}

// Global function to remove files (called from HTML)
function removeFile(type) {
    if (window.uploadManager) {
        window.uploadManager.removeFile(type);
    }
}

// Initialize upload manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.uploadManager = new UploadManager();
});

// Handle page unload
window.addEventListener('beforeunload', (e) => {
    if (window.uploadManager && (window.uploadManager.files.guide || window.uploadManager.files.submission)) {
        e.preventDefault();
        e.returnValue = 'You have unsaved files. Are you sure you want to leave?';
    }
});
