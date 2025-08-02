/**
 * Content Deduplication Handler
 * 
 * Handles duplicate document detection responses and provides
 * user-friendly feedback when duplicates are found.
 */

class DeduplicationHandler {
    constructor() {
        this.setupEventListeners();
    }

    /**
     * Set up event listeners for upload forms
     */
    setupEventListeners() {
        // Handle form submissions that might result in duplicates
        document.addEventListener('submit', (event) => {
            const form = event.target;
            if (form.enctype === 'multipart/form-data') {
                this.handleFormSubmission(form, event);
            }
        });

        // Handle AJAX upload responses
        document.addEventListener('uploadResponse', (event) => {
            this.handleUploadResponse(event.detail);
        });
    }

    /**
     * Handle form submission for file uploads
     */
    handleFormSubmission(form, event) {
        // Add loading state
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking for duplicates...';
        }
    }

    /**
     * Handle upload response, especially duplicate detection
     */
    handleUploadResponse(response) {
        if (response.duplicate && response.existing_document) {
            this.showDuplicateModal(response);
        } else if (response.success === false && response.error) {
            this.showErrorMessage(response.error);
        }
    }

    /**
     * Show duplicate detection modal with options
     */
    showDuplicateModal(response) {
        const modal = this.createDuplicateModal(response);
        document.body.appendChild(modal);
        
        // Show modal
        modal.style.display = 'flex';
        
        // Handle modal actions
        this.setupModalActions(modal, response);
    }

    /**
     * Create duplicate detection modal
     */
    createDuplicateModal(response) {
        const existing = response.existing_document;
        const docType = response.error.includes('training guide') ? 'training guide' : 
                       response.error.includes('test submission') ? 'test submission' :
                       response.error.includes('marking guide') ? 'marking guide' : 'document';

        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50';
        modal.innerHTML = `
            <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-2/3 lg:w-1/2 shadow-lg rounded-md bg-white">
                <div class="mt-3">
                    <!-- Header -->
                    <div class="flex items-center mb-4">
                        <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100">
                            <i class="fas fa-exclamation-triangle text-yellow-600 text-xl"></i>
                        </div>
                    </div>
                    
                    <!-- Title -->
                    <h3 class="text-lg font-medium text-gray-900 text-center mb-4">
                        Duplicate ${docType.charAt(0).toUpperCase() + docType.slice(1)} Detected
                    </h3>
                    
                    <!-- Message -->
                    <div class="mb-6">
                        <p class="text-sm text-gray-600 text-center mb-4">
                            A ${docType} with identical content already exists in your account.
                        </p>
                        
                        <!-- Existing document info -->
                        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                            <h4 class="font-medium text-blue-900 mb-2">Existing ${docType.charAt(0).toUpperCase() + docType.slice(1)}:</h4>
                            <div class="space-y-2 text-sm">
                                <div class="flex justify-between">
                                    <span class="text-blue-700">Name:</span>
                                    <span class="text-blue-900 font-medium">${existing.name}</span>
                                </div>
                                ${existing.created_at ? `
                                <div class="flex justify-between">
                                    <span class="text-blue-700">Created:</span>
                                    <span class="text-blue-900">${new Date(existing.created_at).toLocaleDateString()}</span>
                                </div>
                                ` : ''}
                                ${existing.word_count ? `
                                <div class="flex justify-between">
                                    <span class="text-blue-700">Word Count:</span>
                                    <span class="text-blue-900">${existing.word_count.toLocaleString()}</span>
                                </div>
                                ` : ''}
                                ${existing.file_size ? `
                                <div class="flex justify-between">
                                    <span class="text-blue-700">File Size:</span>
                                    <span class="text-blue-900">${this.formatFileSize(existing.file_size)}</span>
                                </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                    
                    <!-- Actions -->
                    <div class="flex flex-col sm:flex-row gap-3 justify-center">
                        <button type="button" class="duplicate-modal-close px-4 py-2 bg-gray-300 text-gray-700 text-base font-medium rounded-md shadow-sm hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-300">
                            <i class="fas fa-times mr-2"></i>Cancel Upload
                        </button>
                        <button type="button" class="duplicate-modal-view px-4 py-2 bg-blue-600 text-white text-base font-medium rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500">
                            <i class="fas fa-eye mr-2"></i>View Existing
                        </button>
                    </div>
                    
                    <!-- Help text -->
                    <div class="mt-4 text-xs text-gray-500 text-center">
                        <p>💡 Tip: If you want to upload a new version, please modify the content first.</p>
                    </div>
                </div>
            </div>
        `;

        return modal;
    }

    /**
     * Set up modal action handlers
     */
    setupModalActions(modal, response) {
        const closeBtn = modal.querySelector('.duplicate-modal-close');
        const viewBtn = modal.querySelector('.duplicate-modal-view');

        closeBtn.addEventListener('click', () => {
            this.closeDuplicateModal(modal);
        });

        viewBtn.addEventListener('click', () => {
            this.viewExistingDocument(response.existing_document);
            this.closeDuplicateModal(modal);
        });

        // Close on background click
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                this.closeDuplicateModal(modal);
            }
        });

        // Close on escape key
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                this.closeDuplicateModal(modal);
            }
        });
    }

    /**
     * Close duplicate modal
     */
    closeDuplicateModal(modal) {
        modal.style.display = 'none';
        document.body.removeChild(modal);
        
        // Reset form if needed
        this.resetUploadForm();
    }

    /**
     * View existing document (navigate to appropriate page)
     */
    viewExistingDocument(document) {
        // This would navigate to the document view page
        // Implementation depends on your routing structure
        console.log('Viewing existing document:', document);
        
        // Example navigation (adjust based on your routes)
        if (window.location.pathname.includes('llm-training')) {
            // Stay on LLM training page and highlight the existing document
            this.highlightExistingDocument(document.id);
        } else {
            // Navigate to appropriate list page
            window.location.href = this.getDocumentListUrl();
        }
    }

    /**
     * Highlight existing document in the current page
     */
    highlightExistingDocument(documentId) {
        const element = document.querySelector(`[data-document-id="${documentId}"]`);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
            element.classList.add('bg-yellow-100', 'border-yellow-300');
            
            setTimeout(() => {
                element.classList.remove('bg-yellow-100', 'border-yellow-300');
            }, 3000);
        }
    }

    /**
     * Get appropriate document list URL
     */
    getDocumentListUrl() {
        if (window.location.pathname.includes('llm-training')) {
            return '/llm-training/';
        } else if (window.location.pathname.includes('guide')) {
            return '/guides/';
        } else if (window.location.pathname.includes('submission')) {
            return '/submissions/';
        }
        return '/';
    }

    /**
     * Reset upload form
     */
    resetUploadForm() {
        const forms = document.querySelectorAll('form[enctype="multipart/form-data"]');
        forms.forEach(form => {
            const fileInputs = form.querySelectorAll('input[type="file"]');
            fileInputs.forEach(input => {
                input.value = '';
            });
            
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = submitButton.dataset.originalText || 'Upload';
            }
        });
    }

    /**
     * Show error message
     */
    showErrorMessage(message) {
        // Create error toast
        const toast = document.createElement('div');
        toast.className = 'fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-50';
        toast.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-exclamation-circle mr-2"></i>
                <span>${message}</span>
                <button type="button" class="ml-4 text-red-700 hover:text-red-900" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.parentElement.removeChild(toast);
            }
        }, 5000);
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Initialize deduplication handler when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new DeduplicationHandler();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DeduplicationHandler;
}