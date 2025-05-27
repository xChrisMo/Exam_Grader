// Professional Upload System - Enterprise Grade
class ProfessionalUploader {
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
        this.uploadProgress = 0;
        this.processingStage = 0;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupFileInputs();
        this.setupFormSubmission();
        this.setupDragAndDrop();
    }

    setupEventListeners() {
        // File input change events
        document.getElementById('markingGuideProfessional').addEventListener('change', (e) => {
            this.handleFileSelect(e, 'guide');
        });

        document.getElementById('studentSubmissionProfessional').addEventListener('change', (e) => {
            this.handleFileSelect(e, 'submission');
        });

        // Prevent default drag behaviors globally
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.addEventListener(eventName, this.preventDefaults, false);
        });
    }

    setupFileInputs() {
        const inputs = ['markingGuideProfessional', 'studentSubmissionProfessional'];
        inputs.forEach(inputId => {
            const input = document.getElementById(inputId);
            input.addEventListener('change', (e) => {
                const type = inputId.includes('marking') ? 'guide' : 'submission';
                this.validateFile(e.target.files[0], type);
            });
        });
    }

    setupFormSubmission() {
        const form = document.getElementById('uploadFormProfessional');
        const submitBtn = document.getElementById('submitBtnProfessional');

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            if (this.validateForm()) {
                this.submitForm();
            }
        });

        this.updateSubmitButton();
    }

    setupDragAndDrop() {
        // Enhanced drag and drop with visual feedback
        const uploadAreas = ['guideUploadAreaProfessional', 'submissionUploadAreaProfessional'];
        
        uploadAreas.forEach(areaId => {
            const area = document.getElementById(areaId);
            const type = areaId.includes('guide') ? 'guide' : 'submission';
            
            area.addEventListener('dragenter', (e) => this.handleDragEnter(e, type));
            area.addEventListener('dragleave', (e) => this.handleDragLeave(e, type));
            area.addEventListener('dragover', (e) => this.handleDragOver(e));
            area.addEventListener('drop', (e) => this.handleDrop(e, type));
        });
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    handleDragEnter(event, type) {
        event.preventDefault();
        const uploadArea = document.getElementById(`${type}UploadAreaProfessional`);
        uploadArea.classList.add('dragover');
        
        // Add visual feedback
        const icon = uploadArea.querySelector('.upload-icon-professional');
        icon.style.transform = 'scale(1.1) rotate(5deg)';
    }

    handleDragLeave(event, type) {
        event.preventDefault();
        const uploadArea = document.getElementById(`${type}UploadAreaProfessional`);
        
        // Check if we're actually leaving the upload area
        if (!uploadArea.contains(event.relatedTarget)) {
            uploadArea.classList.remove('dragover');
            
            const icon = uploadArea.querySelector('.upload-icon-professional');
            icon.style.transform = 'scale(1) rotate(0deg)';
        }
    }

    handleDragOver(event) {
        event.preventDefault();
    }

    handleDrop(event, type) {
        event.preventDefault();
        const uploadArea = document.getElementById(`${type}UploadAreaProfessional`);
        uploadArea.classList.remove('dragover');
        
        const icon = uploadArea.querySelector('.upload-icon-professional');
        icon.style.transform = 'scale(1) rotate(0deg)';
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            const input = document.getElementById(type === 'guide' ? 'markingGuideProfessional' : 'studentSubmissionProfessional');
            input.files = files;
            input.dispatchEvent(new Event('change'));
        }
    }

    handleFileSelect(event, type) {
        const file = event.target.files[0];
        if (file && this.validateFile(file, type)) {
            this.files[type] = file;
            this.showFilePreview(file, type);
            this.updateSubmitButton();
            this.showProfessionalToast(`${type === 'guide' ? 'Marking guide' : 'Student submission'} uploaded successfully!`, 'success');
            
            // Add success animation
            const uploadArea = document.getElementById(`${type}UploadAreaProfessional`);
            uploadArea.style.transform = 'scale(1.02)';
            setTimeout(() => {
                uploadArea.style.transform = 'scale(1)';
            }, 200);
        }
    }

    validateFile(file, type) {
        // Check file size
        if (file.size > this.maxFileSize) {
            this.showProfessionalToast(`File size exceeds 50MB limit. Please choose a smaller file.`, 'danger');
            return false;
        }

        // Check file type
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!this.allowedTypes[type].includes(fileExtension)) {
            this.showProfessionalToast(`Invalid file type. Allowed types: ${this.allowedTypes[type].join(', ')}`, 'warning');
            return false;
        }

        return true;
    }

    showFilePreview(file, type) {
        const uploadArea = document.getElementById(`${type}UploadAreaProfessional`);
        const preview = document.getElementById(`${type}PreviewProfessional`);
        const fileName = document.getElementById(`${type}FileNameProfessional`);
        const fileSize = document.getElementById(`${type}FileSizeProfessional`);

        // Hide upload content and show preview with animation
        const uploadContent = uploadArea.querySelector('.upload-content-professional');
        uploadContent.style.opacity = '0';
        uploadContent.style.transform = 'translateY(-20px)';
        
        setTimeout(() => {
            uploadContent.classList.add('d-none');
            preview.classList.remove('d-none');
            uploadArea.classList.add('has-file');

            // Update preview content
            fileName.textContent = file.name;
            fileSize.textContent = this.formatFileSize(file.size);

            // Animate preview in
            preview.style.opacity = '0';
            preview.style.transform = 'translateY(20px)';
            setTimeout(() => {
                preview.style.transition = 'all 0.3s ease-out';
                preview.style.opacity = '1';
                preview.style.transform = 'translateY(0)';
            }, 50);
        }, 150);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    updateSubmitButton() {
        const submitBtn = document.getElementById('submitBtnProfessional');
        const hasAllFiles = this.files.guide && this.files.submission;
        
        submitBtn.disabled = !hasAllFiles;
        
        if (hasAllFiles) {
            submitBtn.className = 'btn-primary-professional btn-lg-professional hover-lift-professional';
            submitBtn.innerHTML = '<i class="bi bi-play-circle-fill me-2"></i>Start AI Assessment';
        } else {
            submitBtn.className = 'btn-outline-professional btn-lg-professional';
            submitBtn.innerHTML = '<i class="bi bi-upload me-2"></i>Upload Files First';
        }
    }

    validateForm() {
        if (!this.files.guide) {
            this.showProfessionalToast('Please upload a marking guide', 'warning');
            return false;
        }
        if (!this.files.submission) {
            this.showProfessionalToast('Please upload a student submission', 'warning');
            return false;
        }
        return true;
    }

    async submitForm() {
        const formData = new FormData();
        formData.append('marking_guide', this.files.guide);
        formData.append('submission', this.files.submission);

        // Add processing options
        const options = ['detailedFeedbackProfessional', 'criteriaMappingProfessional', 'confidenceScoresProfessional', 'improvementSuggestionsProfessional'];
        options.forEach(option => {
            const checkbox = document.getElementById(option);
            if (checkbox && checkbox.checked) {
                formData.append(option.replace('Professional', ''), 'true');
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
        const modal = new bootstrap.Modal(document.getElementById('progressModalProfessional'));
        modal.show();
        this.simulateProgress();
    }

    simulateProgress() {
        const progressBar = document.getElementById('progressBarProfessional');
        const progressStage = document.getElementById('progressStageProfessional');
        const progressMessage = document.getElementById('progressMessageProfessional');
        
        const stages = [
            { 
                progress: 25, 
                stage: 'Uploading Files...', 
                message: 'Securely transferring your files to our AI processing servers',
                tip: 'Files are encrypted during transfer for maximum security'
            },
            { 
                progress: 50, 
                stage: 'Parsing Documents...', 
                message: 'Extracting text content and analyzing document structure',
                tip: 'Our OCR technology handles both typed and handwritten content'
            },
            { 
                progress: 75, 
                stage: 'AI Analysis in Progress...', 
                message: 'Mapping criteria, analyzing responses, and generating detailed feedback',
                tip: 'Advanced language models ensure contextual understanding'
            },
            { 
                progress: 100, 
                stage: 'Assessment Complete!', 
                message: 'Comprehensive grading and feedback generation finished successfully',
                tip: 'Results include detailed analytics and improvement suggestions'
            }
        ];

        let currentStage = 0;
        const interval = setInterval(() => {
            if (currentStage < stages.length) {
                const stage = stages[currentStage];
                
                // Update progress bar with smooth animation
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
                }, 1500);
            }
        }, 2500);
    }

    updateProgressStep(step) {
        for (let i = 1; i <= 4; i++) {
            const stepElement = document.getElementById(`step${i}Professional`);
            stepElement.classList.remove('active', 'completed');
            
            if (i < step) {
                stepElement.classList.add('completed');
                stepElement.innerHTML = '<i class="bi bi-check"></i>';
            } else if (i === step) {
                stepElement.classList.add('active');
                stepElement.textContent = i;
            } else {
                stepElement.textContent = i;
            }
        }
    }

    hideProgressModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('progressModalProfessional'));
        if (modal) modal.hide();
    }

    showResultsModal() {
        this.showProfessionalToast('Assessment completed successfully! Redirecting to results...', 'success');
        setTimeout(() => {
            window.location.href = '/results';
        }, 2000);
    }

    handleSuccess(result) {
        this.showProfessionalToast('Files uploaded and processed successfully!', 'success');
        this.resetForm();
    }

    handleError(error) {
        this.hideProgressModal();
        this.showProfessionalToast('Upload failed. Please check your files and try again.', 'danger');
        console.error('Upload error:', error);
    }

    resetForm() {
        this.files = { guide: null, submission: null };
        
        // Reset file inputs
        document.getElementById('markingGuideProfessional').value = '';
        document.getElementById('studentSubmissionProfessional').value = '';
        
        // Reset upload areas with animation
        ['guide', 'submission'].forEach(type => {
            const uploadArea = document.getElementById(`${type}UploadAreaProfessional`);
            const preview = document.getElementById(`${type}PreviewProfessional`);
            const uploadContent = uploadArea.querySelector('.upload-content-professional');
            
            preview.style.opacity = '0';
            preview.style.transform = 'translateY(-20px)';
            
            setTimeout(() => {
                preview.classList.add('d-none');
                uploadContent.classList.remove('d-none');
                uploadArea.classList.remove('has-file');
                
                uploadContent.style.opacity = '1';
                uploadContent.style.transform = 'translateY(0)';
            }, 150);
        });
        
        this.updateSubmitButton();
    }

    showProfessionalToast(message, type = 'primary') {
        if (window.showToast) {
            window.showToast(message, type);
        } else {
            // Fallback for basic alert
            alert(message);
        }
    }
}

// Global functions for template compatibility
function handleDropProfessional(event, type) {
    if (window.professionalUploader) {
        window.professionalUploader.handleDrop(event, type);
    }
}

function handleDragOverProfessional(event) {
    if (window.professionalUploader) {
        window.professionalUploader.handleDragOver(event);
    }
}

function handleDragEnterProfessional(event, type) {
    if (window.professionalUploader) {
        window.professionalUploader.handleDragEnter(event, type);
    }
}

function handleDragLeaveProfessional(event, type) {
    if (window.professionalUploader) {
        window.professionalUploader.handleDragLeave(event, type);
    }
}

function removeFileProfessional(type) {
    if (window.professionalUploader) {
        window.professionalUploader.files[type] = null;
        
        const uploadArea = document.getElementById(`${type}UploadAreaProfessional`);
        const preview = document.getElementById(`${type}PreviewProfessional`);
        const uploadContent = uploadArea.querySelector('.upload-content-professional');
        
        preview.style.opacity = '0';
        preview.style.transform = 'translateY(-20px)';
        
        setTimeout(() => {
            preview.classList.add('d-none');
            uploadContent.classList.remove('d-none');
            uploadArea.classList.remove('has-file');
            
            uploadContent.style.opacity = '1';
            uploadContent.style.transform = 'translateY(0)';
        }, 150);
        
        // Reset file input
        const input = document.getElementById(type === 'guide' ? 'markingGuideProfessional' : 'studentSubmissionProfessional');
        input.value = '';
        
        window.professionalUploader.updateSubmitButton();
        window.professionalUploader.showProfessionalToast(`${type === 'guide' ? 'Marking guide' : 'Student submission'} removed`, 'info');
    }
}

function resetFormProfessional() {
    if (window.professionalUploader) {
        window.professionalUploader.resetForm();
        window.professionalUploader.showProfessionalToast('Form reset successfully', 'info');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.professionalUploader = new ProfessionalUploader();
    
    // Add professional animations to form elements
    const cards = document.querySelectorAll('.glass-card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });
});
