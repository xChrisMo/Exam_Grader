/**
 * Training Dashboard JavaScript
 * 
 * Handles file uploads, drag-and-drop, training configuration,
 * and progress monitoring for the LLM Training Dashboard.
 */

class TrainingDashboard {
    constructor() {
        this.uploadedFiles = [];
        this.fileCategoryCounts = { qa: 0, q: 0, a: 0 };
        this.isTraining = false;
        this.currentSessionId = null;
        
        // File type configuration
        this.fileTypes = {
            pdf: { category: 'qa', color: 'bg-green-100 text-green-800', label: 'Q+A' },
            docx: { category: 'qa', color: 'bg-green-100 text-green-800', label: 'Q+A' },
            doc: { category: 'qa', color: 'bg-green-100 text-green-800', label: 'Q+A' },
            jpg: { category: 'q', color: 'bg-blue-100 text-blue-800', label: 'Questions' },
            jpeg: { category: 'q', color: 'bg-blue-100 text-blue-800', label: 'Questions' },
            png: { category: 'q', color: 'bg-blue-100 text-blue-800', label: 'Questions' },
            tiff: { category: 'q', color: 'bg-blue-100 text-blue-800', label: 'Questions' },
            bmp: { category: 'q', color: 'bg-blue-100 text-blue-800', label: 'Questions' },
            gif: { category: 'q', color: 'bg-blue-100 text-blue-800', label: 'Questions' }
        };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.bindKeyboardShortcuts();
        this.updateUI();
    }
    
    bindEvents() {
        // Drag and drop events
        const dropZone = document.getElementById('drop-zone');
        if (dropZone) {
            dropZone.addEventListener('click', () => this.triggerFileInput());
            dropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
            dropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
            dropZone.addEventListener('drop', (e) => this.handleDrop(e));
        }
        
        // File input change
        const fileInput = document.getElementById('file-input');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }
        
        // Configuration controls
        const confidenceThreshold = document.getElementById('confidence-threshold');
        if (confidenceThreshold) {
            confidenceThreshold.addEventListener('input', (e) => this.updateThresholdDisplay(e));
        }
        
        const useInMainAppToggle = document.getElementById('use-in-main-app');
        if (useInMainAppToggle) {
            useInMainAppToggle.addEventListener('click', () => this.toggleMainAppUsage());
        }
        
        const sessionNameInput = document.getElementById('session-name');
        if (sessionNameInput) {
            sessionNameInput.addEventListener('input', () => this.updateUI());
        }
        
        // Action buttons
        const startTrainingBtn = document.getElementById('start-training');
        if (startTrainingBtn) {
            startTrainingBtn.addEventListener('click', () => this.startTraining());
        }
        
        const clearFilesBtn = document.getElementById('clear-files');
        if (clearFilesBtn) {
            clearFilesBtn.addEventListener('click', () => this.clearAllFiles());
        }
        
        // Stop training button
        const stopTrainingBtn = document.getElementById('stop-training');
        if (stopTrainingBtn) {
            stopTrainingBtn.addEventListener('click', () => this.stopTraining());
        }
    }
    
    bindKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+U or Cmd+U to trigger file upload
            if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
                e.preventDefault();
                this.triggerFileInput();
            }
            
            // Ctrl+Enter or Cmd+Enter to start training
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                const startBtn = document.getElementById('start-training');
                if (startBtn && !startBtn.disabled) {
                    this.startTraining();
                }
            }
            
            // Escape to clear files
            if (e.key === 'Escape' && this.uploadedFiles.length > 0) {
                if (confirm('Clear all uploaded files?')) {
                    this.clearAllFiles();
                }
            }
        });
    }
    
    triggerFileInput() {
        const fileInput = document.getElementById('file-input');
        if (fileInput) {
            fileInput.click();
        }
    }
    
    handleDragOver(e) {
        e.preventDefault();
        const dropZone = document.getElementById('drop-zone');
        if (dropZone) {
            dropZone.classList.add('drag-over');
        }
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        const dropZone = document.getElementById('drop-zone');
        if (dropZone) {
            dropZone.classList.remove('drag-over');
        }
    }
    
    handleDrop(e) {
        e.preventDefault();
        const dropZone = document.getElementById('drop-zone');
        if (dropZone) {
            dropZone.classList.remove('drag-over');
        }
        
        const files = Array.from(e.dataTransfer.files);
        this.processFiles(files);
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.processFiles(files);
    }
    
    processFiles(files) {
        files.forEach(file => {
            if (this.validateFile(file)) {
                this.addFileToList(file);
            }
        });
        this.updateUI();
    }
    
    validateFile(file) {
        const maxSize = 50 * 1024 * 1024; // 50MB limit to match backend
        const extension = file.name.split('.').pop().toLowerCase();
        
        if (file.size > maxSize) {
            this.showError(`File "${file.name}" is too large. Maximum size is 50MB.`);
            return false;
        }
        
        if (!this.fileTypes[extension]) {
            this.showError(`File type "${extension}" is not supported.`);
            return false;
        }
        
        return true;
    }
    
    addFileToList(file) {
        const extension = file.name.split('.').pop().toLowerCase();
        const fileType = this.fileTypes[extension];
        const fileId = Date.now() + Math.random();
        
        const fileItem = this.createFileItem(file, fileType, fileId);
        const filesContainer = document.getElementById('files-container');
        if (filesContainer) {
            filesContainer.appendChild(fileItem);
        }
        
        this.uploadedFiles.push({ id: fileId, file, category: fileType.category });
        this.fileCategoryCounts[fileType.category]++;
        
        // Show file list
        const fileList = document.getElementById('file-list');
        if (fileList) {
            fileList.style.display = 'block';
        }
    }
    
    createFileItem(file, fileType, fileId) {
        const template = document.getElementById('file-item-template');
        if (!template) return null;
        
        const fileItem = template.content.cloneNode(true);
        const container = fileItem.querySelector('.file-item');
        container.dataset.fileId = fileId;
        
        fileItem.querySelector('.file-name').textContent = file.name;
        fileItem.querySelector('.file-info').textContent = 
            `${(file.size / 1024 / 1024).toFixed(2)} MB • ${file.name.split('.').pop().toUpperCase()}`;
        
        // Update file icon based on type
        const extension = file.name.split('.').pop().toLowerCase();
        const iconSvg = fileItem.querySelector('svg');
        if (iconSvg) {
            if (['pdf'].includes(extension)) {
                iconSvg.classList.add('text-red-500');
            } else if (['docx', 'doc'].includes(extension)) {
                iconSvg.classList.add('text-blue-500');
            } else if (['jpg', 'jpeg', 'png', 'tiff', 'bmp', 'gif'].includes(extension)) {
                iconSvg.classList.add('text-green-500');
            }
        }
        
        const categorySpan = fileItem.querySelector('.file-category');
        categorySpan.textContent = fileType.label;
        categorySpan.className = `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium file-category ${fileType.color}`;
        
        fileItem.querySelector('.remove-file').addEventListener('click', () => this.removeFile(fileId));
        
        return fileItem;
    }
    
    removeFile(fileId) {
        const fileElement = document.querySelector(`[data-file-id="${fileId}"]`);
        if (fileElement) {
            const fileData = this.uploadedFiles.find(f => f.id === fileId);
            if (fileData) {
                this.fileCategoryCounts[fileData.category]--;
                this.uploadedFiles = this.uploadedFiles.filter(f => f.id !== fileId);
            }
            fileElement.remove();
            this.updateUI();
        }
    }
    
    clearAllFiles() {
        this.uploadedFiles = [];
        this.fileCategoryCounts = { qa: 0, q: 0, a: 0 };
        
        const filesContainer = document.getElementById('files-container');
        if (filesContainer) {
            filesContainer.innerHTML = '';
        }
        
        const fileList = document.getElementById('file-list');
        if (fileList) {
            fileList.style.display = 'none';
        }
        
        this.updateUI();
    }
    
    updateThresholdDisplay(e) {
        const thresholdValue = document.getElementById('threshold-value');
        if (thresholdValue) {
            thresholdValue.textContent = e.target.value;
        }
    }
    
    toggleMainAppUsage() {
        const toggle = document.getElementById('use-in-main-app');
        if (!toggle) return;
        
        const isEnabled = toggle.getAttribute('aria-checked') === 'true';
        toggle.setAttribute('aria-checked', !isEnabled);
        toggle.classList.toggle('bg-blue-600', !isEnabled);
        toggle.classList.toggle('bg-gray-200', isEnabled);
        
        const span = toggle.querySelector('span');
        if (span) {
            span.classList.toggle('translate-x-5', !isEnabled);
            span.classList.toggle('translate-x-0', isEnabled);
        }
    }
    
    updateUI() {
        // Update category counts
        const qaCount = document.getElementById('qa-count');
        const qCount = document.getElementById('q-count');
        const aCount = document.getElementById('a-count');
        
        if (qaCount) qaCount.textContent = this.fileCategoryCounts.qa;
        if (qCount) qCount.textContent = this.fileCategoryCounts.q;
        if (aCount) aCount.textContent = this.fileCategoryCounts.a;
        
        // Update start training button
        const startTrainingBtn = document.getElementById('start-training');
        const sessionNameInput = document.getElementById('session-name');
        
        if (startTrainingBtn && sessionNameInput) {
            const sessionName = sessionNameInput.value.trim();
            startTrainingBtn.disabled = this.uploadedFiles.length === 0 || !sessionName || this.isTraining;
        }
    }
    
    async startTraining() {
        if (this.uploadedFiles.length === 0) {
            this.showError('Please upload at least one marking guide.');
            return;
        }
        
        const sessionNameInput = document.getElementById('session-name');
        if (!sessionNameInput || !sessionNameInput.value.trim()) {
            this.showError('Please enter a session name.');
            sessionNameInput?.focus();
            return;
        }
        
        // Validate session name length
        const sessionName = sessionNameInput.value.trim();
        if (sessionName.length < 3) {
            this.showError('Session name must be at least 3 characters long.');
            sessionNameInput?.focus();
            return;
        }
        
        if (sessionName.length > 100) {
            this.showError('Session name must be less than 100 characters.');
            sessionNameInput?.focus();
            return;
        }
        
        this.isTraining = true;
        this.updateTrainingButtonState(true);
        this.showProgressPanel();
        
        try {
            // Update progress
            this.updateProgressDisplay({
                percentage: 10,
                current_step: 'Uploading files...'
            });
            
            // Collect training configuration
            const config = this.getTrainingConfig();
            
            // Upload files first
            const uploadedFileData = await this.uploadFiles();
            
            // Update progress
            this.updateProgressDisplay({
                percentage: 30,
                current_step: 'Creating training session...'
            });
            
            // Create training session
            const sessionData = await this.createTrainingSession(config, uploadedFileData);
            this.currentSessionId = sessionData.session_id;
            
            // Update progress
            this.updateProgressDisplay({
                percentage: 50,
                current_step: 'Starting training...'
            });
            
            // Start training
            await this.initiateTraining(this.currentSessionId);
            
            // Update progress
            this.updateProgressDisplay({
                percentage: 60,
                current_step: 'Training in progress...'
            });
            
            // Show stop button and monitor progress
            this.showStopTrainingButton();
            this.monitorTrainingProgress();
            
        } catch (error) {
            console.error('Training error:', error);
            this.showError(`Training failed: ${error.message}`);
            this.isTraining = false;
            this.updateTrainingButtonState(false);
            this.hideStopTrainingButton();
            this.hideProgressPanel();
        }
    }
    
    getTrainingConfig() {
        const sessionNameInput = document.getElementById('session-name');
        const maxQuestionsSelect = document.getElementById('max-questions');
        const confidenceThresholdInput = document.getElementById('confidence-threshold');
        const useInMainAppToggle = document.getElementById('use-in-main-app');
        
        return {
            sessionName: sessionNameInput ? sessionNameInput.value.trim() : '',
            maxQuestions: maxQuestionsSelect ? maxQuestionsSelect.value || null : null,
            confidenceThreshold: confidenceThresholdInput ? parseFloat(confidenceThresholdInput.value) : 0.6,
            useInMainApp: useInMainAppToggle ? useInMainAppToggle.getAttribute('aria-checked') === 'true' : false
        };
    }
    
    async uploadFiles() {
        const formData = new FormData();
        this.uploadedFiles.forEach(fileData => {
            formData.append('files', fileData.file);
        });
        
        const response = await fetch('/training/upload', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': this.getCSRFToken()
            }
        });
        
        if (!response.ok) {
            let errorMessage = 'File upload failed';
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
                if (errorData.details && Array.isArray(errorData.details)) {
                    errorMessage += ': ' + errorData.details.join(', ');
                }
            } catch (e) {
                // If response is not JSON, use status text
                errorMessage = `File upload failed: ${response.status} ${response.statusText}`;
            }
            throw new Error(errorMessage);
        }
        
        return await response.json();
    }
    
    async createTrainingSession(config, uploadedFiles) {
        const response = await fetch('/training/create-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                ...config,
                files: uploadedFiles.files
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Session creation failed');
        }
        
        return await response.json();
    }
    
    async initiateTraining(sessionId) {
        const response = await fetch('/training/start-training', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                session_id: sessionId
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Training start failed');
        }
        
        return await response.json();
    }
    
    monitorTrainingProgress() {
        if (!this.currentSessionId) return;
        
        const checkProgress = async () => {
            try {
                const response = await fetch(`/training/session/${this.currentSessionId}/progress`, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                if (response.ok) {
                    let progress;
                    try {
                        const responseText = await response.text();
                        progress = JSON.parse(responseText);
                    } catch (jsonError) {
                        console.error(`JSON parsing error for training progress:`, jsonError);
                        console.error('Response text:', await response.text());
                        setTimeout(checkProgress, 5000); // Retry after longer delay
                        return;
                    }
                    
                    this.updateProgressDisplay(progress);
                    
                    if (progress.status === 'completed') {
                        this.onTrainingComplete();
                    } else if (progress.status === 'failed') {
                        this.onTrainingFailed(progress.error);
                    } else {
                        // Continue monitoring
                        setTimeout(checkProgress, 2000);
                    }
                }
            } catch (error) {
                console.error('Error checking training progress:', error);
                setTimeout(checkProgress, 5000); // Retry after longer delay
            }
        };
        
        checkProgress();
    }
    
    updateProgressDisplay(progress) {
        const progressBar = document.getElementById('progress-bar');
        const progressPercentage = document.getElementById('progress-percentage');
        const progressDetails = document.getElementById('progress-details');
        
        if (progressBar) {
            progressBar.style.width = `${progress.percentage}%`;
        }
        
        if (progressPercentage) {
            progressPercentage.textContent = `${Math.round(progress.percentage)}%`;
        }
        
        if (progressDetails) {
            progressDetails.innerHTML = `<p>${progress.current_step}</p>`;
        }
    }
    
    onTrainingComplete() {
        this.isTraining = false;
        this.updateTrainingButtonState(false);
        this.hideStopTrainingButton();
        
        const progressDetails = document.getElementById('progress-details');
        if (progressDetails) {
            progressDetails.innerHTML = `
                <p class="text-green-600 font-medium">Training completed successfully!</p>
                <p class="mt-2">
                    <a href="/training/session/${this.currentSessionId}/report" 
                       class="text-blue-600 hover:text-blue-800 underline">
                        View Training Report
                    </a>
                </p>
            `;
        }
        
        this.showSuccess('Training completed successfully!');
    }
    
    async stopTraining() {
        if (!this.currentSessionId) {
            this.showError('No active training session to stop.');
            return;
        }
        
        if (!confirm('Are you sure you want to stop the current training session? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`/training/session/${this.currentSessionId}/stop`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || ''
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                this.isTraining = false;
                this.updateTrainingButtonState(false);
                this.hideStopTrainingButton();
                
                const progressDetails = document.getElementById('progress-details');
                if (progressDetails) {
                    progressDetails.innerHTML = `
                        <p class="text-orange-600 font-medium">Training stopped by user</p>
                        <p class="text-sm text-gray-600 mt-1">The training session has been cancelled.</p>
                    `;
                }
                
                this.showSuccess('Training session stopped successfully.');
            } else {
                const errorData = await response.json();
                this.showError(`Failed to stop training: ${errorData.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error stopping training:', error);
            this.showError(`Failed to stop training: ${error.message}`);
        }
    }
    
    onTrainingFailed(error) {
        this.isTraining = false;
        this.updateTrainingButtonState(false);
        this.hideStopTrainingButton();
        this.showError(`Training failed: ${error || 'Unknown error'}`);
    }
    
    showStopTrainingButton() {
        const stopBtn = document.getElementById('stop-training');
        if (stopBtn) {
            stopBtn.style.display = 'inline-flex';
        }
    }
    
    hideStopTrainingButton() {
        const stopBtn = document.getElementById('stop-training');
        if (stopBtn) {
            stopBtn.style.display = 'none';
        }
    }
    
    updateTrainingButtonState(isTraining) {
        const startTrainingBtn = document.getElementById('start-training');
        if (!startTrainingBtn) return;
        
        if (isTraining) {
            startTrainingBtn.disabled = true;
            startTrainingBtn.innerHTML = `
                <svg class="animate-spin -ml-1 mr-2 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Training...
            `;
        } else {
            startTrainingBtn.innerHTML = `
                <svg class="-ml-1 mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                </svg>
                ${this.uploadedFiles.length > 0 ? 'Start New Training' : 'Start Training'}
            `;
            this.updateUI(); // Re-enable based on current state
        }
    }
    
    showProgressPanel() {
        const progressPanel = document.getElementById('training-progress');
        if (progressPanel) {
            progressPanel.style.display = 'block';
        }
    }
    
    hideProgressPanel() {
        const progressPanel = document.getElementById('training-progress');
        if (progressPanel) {
            progressPanel.style.display = 'none';
        }
    }
    
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 max-w-sm p-4 rounded-lg shadow-lg ${
            type === 'error' ? 'bg-red-50 border border-red-200 text-red-800' :
            type === 'success' ? 'bg-green-50 border border-green-200 text-green-800' :
            'bg-blue-50 border border-blue-200 text-blue-800'
        }`;
        
        notification.innerHTML = `
            <div class="flex items-center">
                <div class="flex-shrink-0">
                    ${type === 'error' ? 
                        '<svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>' :
                        type === 'success' ?
                        '<svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>' :
                        '<svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>'
                    }
                </div>
                <div class="ml-3 flex-1">
                    <p class="text-sm font-medium">${message}</p>
                </div>
                <div class="ml-auto pl-3">
                    <button type="button" class="notification-close inline-flex rounded-md p-1.5 hover:bg-gray-100 focus:outline-none">
                        <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
        
        // Add close functionality
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('drop-zone')) {
        new TrainingDashboard();
    }
});