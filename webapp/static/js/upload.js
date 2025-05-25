// File Upload Functionality
document.addEventListener('DOMContentLoaded', () => {
    // Guide Upload
    setupUploadArea('guideDropzone', 'guideFile', 'guideForm');
    
    // Submission Upload
    setupUploadArea('submissionDropzone', 'submissionFile', 'submissionForm');

    // Prevent default form submissions and handle clear actions
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
            e.preventDefault(); // Prevent traditional form submission
            
            // Handle clear submission form
            if (form.action.includes('clear_submission')) {
                handleClearSubmissions(form);
            }
            // Handle clear guide form
            else if (form.action.includes('clear_guide')) {
                handleClearGuide(form);
            }
        });
    });
});

function setupUploadArea(dropzoneId, fileInputId, formId) {
    const dropzone = document.getElementById(dropzoneId);
    const fileInput = document.getElementById(fileInputId);
    const form = document.getElementById(formId);
    const progressBar = dropzone.querySelector('.progress-bar');
    const progressText = dropzone.querySelector('.progress-text');
    
    if (!dropzone || !fileInput || !form) {
        console.error(`Missing elements for ${dropzoneId}`);
        return;
    }

    // Click anywhere in dropzone to trigger file input
    dropzone.addEventListener('click', (e) => {
        e.preventDefault();
        fileInput.click();
    });

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight dropzone when dragging over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.remove('dragover');
        });
    });

    // Handle dropped files
    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            fileInput.files = files;
            handleFiles(files, dropzone, progressBar, progressText, form);
        }
    });

    // Handle selected files
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFiles(e.target.files, dropzone, progressBar, progressText, form);
        }
    });
}

function handleFiles(files, dropzone, progressBar, progressText, form) {
    if (files.length === 0) return;

    // Show both the upload progress UI and global loading spinner
    if (progressBar && progressText) {
        progressBar.style.width = '0%';
        progressBar.parentElement.style.display = 'block';
        progressText.textContent = 'Uploading...';
    }
    
    // Show global loading spinner
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
        loadingOverlay.querySelector('.loading-text').textContent = 'Processing upload...';
    }

    // Create FormData and append files
    const formData = new FormData(form);
    for (let file of files) {
        formData.append('file', file);
    }

    // Update UI to show upload starting
    showToast('info', 'Starting upload...');
    updateProgressUI(progressBar, progressText, 10, 'Processing...');

    // Send the upload request
    fetch(form.action, {
        method: 'POST',
        body: formData
    })
    .then(async response => {
        // Update progress to show completion
        updateProgressUI(progressBar, progressText, 100, 'Upload complete!');

        if (response.ok) {
            const responseData = await response.json().catch(() => null);
            
            if (responseData && responseData.success) {
                showToast('success', responseData.message || 'Upload successful!');
                
                // If it's a guide upload, update the guide status
                if (form.id === 'guideForm' && responseData.guide_content) {
                    updateGuideStatus(responseData.guide_content);
                }
                
                // If it's a submission upload, update the submission list
                if (form.id === 'submissionForm' && responseData.submissions) {
                    updateSubmissionsList(responseData.submissions);
                }
            } else {
                showToast('success', 'Upload completed successfully');
            }

            // Hide global loading spinner
            if (loadingOverlay) {
                loadingOverlay.style.display = 'none';
            }

            // Refresh the page after a short delay to show the updated state
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            const errorData = await response.json().catch(() => ({ message: 'Upload failed' }));
            showToast('error', errorData.message || 'Upload failed');
            updateProgressUI(progressBar, progressText, 100, 'Upload failed');
            
            // Hide global loading spinner
            if (loadingOverlay) {
                loadingOverlay.style.display = 'none';
            }
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        showToast('error', 'Upload failed: ' + error.message);
        updateProgressUI(progressBar, progressText, 100, 'Upload failed');
        
        // Hide global loading spinner
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    });
}

function updateProgressUI(progressBar, progressText, percentage, message) {
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
    }
    if (progressText) {
        progressText.textContent = message;
    }
}

function showToast(type, message) {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = document.createElement('i');
    icon.className = `fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}`;
    
    const span = document.createElement('span');
    span.textContent = message;

    toast.appendChild(icon);
    toast.appendChild(span);
    toastContainer.appendChild(toast);

    // Remove toast after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out forwards';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function updateGuideStatus(guideContent) {
    const guideStatus = document.querySelector('.guide-status');
    if (guideStatus) {
        guideStatus.innerHTML = `
            <div class="upload-success">
                <div class="success-info">
                    <i class="bi bi-check-circle-fill text-success"></i>
                    <div>
                        <strong>Guide uploaded successfully</strong>
                        <small>${(guideContent.length / 1000).toFixed(1)}k characters extracted</small>
                    </div>
                </div>
                <div class="upload-actions">
                    <a href="/view_guide" class="btn btn-outline-primary btn-sm">
                        <i class="bi bi-eye"></i> Preview
                    </a>
                    <form action="/clear_guide" method="post" style="display: inline;">
                        <button type="submit" class="btn btn-outline-danger btn-sm" data-confirm="Remove this guide?">
                            <i class="bi bi-trash"></i> Remove
                        </button>
                    </form>
                </div>
            </div>`;
    }
}

function updateSubmissionsList(submissions) {
    const submissionsList = document.querySelector('.submissions-list');
    if (submissionsList && submissions.length > 0) {
        submissionsList.innerHTML = submissions.map(sub => `
            <div class="submission-item">
                <div class="submission-info">
                    <i class="bi bi-file-text"></i>
                    <span>${sub.filename}</span>
                </div>
                <div class="submission-actions">
                    <button class="btn btn-sm btn-outline-danger" onclick="removeSubmission('${sub.filename}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

async function handleClearSubmissions(form) {
    // Show loading spinner
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
        loadingOverlay.querySelector('.loading-text').textContent = 'Clearing submissions...';
    }

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
        });

        if (response.ok) {
            showToast('success', 'All submissions cleared successfully');
            // Redirect to home page after a short delay
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        } else {
            const errorData = await response.json().catch(() => ({ message: 'Failed to clear submissions' }));
            showToast('error', errorData.message || 'Failed to clear submissions');
        }
    } catch (error) {
        console.error('Clear submissions error:', error);
        showToast('error', 'Failed to clear submissions: ' + error.message);
    } finally {
        // Hide loading spinner
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    }
}

async function handleClearGuide(form) {
    // Show loading spinner
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
        loadingOverlay.querySelector('.loading-text').textContent = 'Removing guide...';
    }

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
        });

        if (response.ok) {
            showToast('success', 'Guide removed successfully');
            // Redirect to home page after a short delay
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        } else {
            const errorData = await response.json().catch(() => ({ message: 'Failed to remove guide' }));
            showToast('error', errorData.message || 'Failed to remove guide');
        }
    } catch (error) {
        console.error('Clear guide error:', error);
        showToast('error', 'Failed to remove guide: ' + error.message);
    } finally {
        // Hide loading spinner
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    }
} 