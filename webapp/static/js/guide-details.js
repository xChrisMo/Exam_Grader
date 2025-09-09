/**
 * Guide Details JavaScript
 * Handles functionality for the guide details page
 */

// Toast notification system
function showToast(message, type) {
    type = type || 'success';
    const toast = document.createElement('div');
    toast.className = 'toast transform transition-all duration-300 ease-in-out translate-x-full';

    const bgColor = type === 'success' ? 'bg-green-500' :
        type === 'error' ? 'bg-red-500' :
            type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500';

    const icons = {
        success: '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>',
        error: '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>',
        warning: '<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>',
        info: '<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>'
    };

    const iconPath = icons[type] || icons.info;

    // Escape HTML to prevent XSS
    const escapeHtml = (text) => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };

    const safeMessage = escapeHtml(message);

    toast.innerHTML =
        '<div class="' + bgColor + ' text-white px-6 py-4 rounded-lg shadow-lg flex items-center max-w-sm">' +
        '<svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">' +
        iconPath +
        '</svg>' +
        '<span>' + safeMessage + '</span>' +
        '</div>';

    const container = document.getElementById('toast-container');
    if (container) {
        container.appendChild(toast);
    } else {
        document.body.appendChild(toast);
    }

    // Show toast
    setTimeout(function () {
        toast.classList.remove('translate-x-full');
    }, 100);

    // Hide and remove toast
    setTimeout(function () {
        toast.classList.add('translate-x-full');
        setTimeout(function () {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 300);
    }, 4000);
}

// Get CSRF token
function getCSRFToken() {
    const metaTag = document.querySelector('meta[name=csrf-token]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

// Select guide functionality
function selectGuide(guideId, guideName) {
    // Escape quotes in guideName to prevent syntax errors
    const safeGuideName = String(guideName).replace(/"/g, '\\"');
    const confirmMessage = 'Are you sure you want to set "' + safeGuideName + '" as your active marking guide?';

    if (confirm(confirmMessage)) {
        fetch('/api/select-guide', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                guide_id: guideId,
                guide_name: guideName
            })
        })
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                if (data.success) {
                    const successMessage = '"' + safeGuideName + '" is now your active marking guide';
                    showToast(successMessage, 'success');
                    setTimeout(function () {
                        window.location.href = '/guides';
                    }, 1500);
                } else {
                    showToast(data.message || 'Failed to select guide', 'error');
                }
            })
            .catch(function (error) {
                console.error('Error selecting guide:', error);
                showToast('Failed to select guide', 'error');
            });
    }
}

// Process guide functionality
function processGuide(guideId) {
    const processBtn = document.getElementById('process-guide-btn');
    const processBtnText = document.getElementById('process-btn-text');

    if (processBtn) {
        processBtn.disabled = true;
        processBtnText.textContent = 'Processing...';
    }

    fetch('/api/process-guide', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            guide_id: guideId
        })
    })
        .then(function (response) {
            return response.json();
        })
        .then(function (data) {
            if (data.success) {
                showToast(data.message || 'Guide processed successfully', 'success');
                setTimeout(function () {
                    window.location.reload();
                }, 1500);
            } else {
                showToast(data.message || 'Failed to process guide', 'error');
            }
        })
        .catch(function (error) {
            console.error('Error processing guide:', error);
            showToast('Failed to process guide', 'error');
        })
        .finally(function () {
            if (processBtn) {
                processBtn.disabled = false;
                processBtnText.textContent = 'Process Guide';
            }
        });
}

// Reprocess guide functionality
function reprocessGuide(guideId) {
    const reprocessBtn = document.getElementById('reprocess-guide-btn');
    const reprocessBtnText = document.getElementById('reprocess-btn-text');

    if (reprocessBtn) {
        reprocessBtn.disabled = true;
        reprocessBtnText.textContent = 'Reprocessing...';
    }

    fetch('/api/reprocess-guide', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            guide_id: guideId
        })
    })
        .then(function (response) {
            return response.json();
        })
        .then(function (data) {
            if (data.success) {
                showToast(data.message || 'Guide reprocessed successfully', 'success');
                setTimeout(function () {
                    window.location.reload();
                }, 1500);
            } else {
                showToast(data.message || 'Failed to reprocess guide', 'error');
            }
        })
        .catch(function (error) {
            console.error('Error reprocessing guide:', error);
            showToast('Failed to reprocess guide', 'error');
        })
        .finally(function () {
            if (reprocessBtn) {
                reprocessBtn.disabled = false;
                reprocessBtnText.textContent = 'Reprocess with AI';
            }
        });
}

// Delete guide functionality
function deleteGuide(guideId, guideName) {
    const safeGuideName = String(guideName).replace(/"/g, '\\"');
    
    if (confirm('Are you sure you want to delete "' + safeGuideName + '"? This action cannot be undone.')) {
        fetch('/guides/' + guideId + '/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        })
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                if (data.success) {
                    showToast('Guide deleted successfully', 'success');
                    setTimeout(function () {
                        window.location.href = '/guides';
                    }, 1500);
                } else {
                    showToast(data.message || 'Failed to delete guide', 'error');
                }
            })
            .catch(function (error) {
                console.error('Error deleting guide:', error);
                showToast('Failed to delete guide', 'error');
            });
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function () {
    // Select guide buttons
    const selectGuideButtons = document.querySelectorAll('[data-action="select-guide"]');
    selectGuideButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            const guideId = this.getAttribute('data-guide-id');
            const guideName = this.getAttribute('data-guide-name');
            selectGuide(guideId, guideName);
        });
    });

    // Process guide button
    const processGuideBtn = document.getElementById('process-guide-btn');
    if (processGuideBtn) {
        processGuideBtn.addEventListener('click', function () {
            const guideId = this.getAttribute('data-guide-id');
            processGuide(guideId);
        });
    }

    // Reprocess guide button
    const reprocessGuideBtn = document.getElementById('reprocess-guide-btn');
    if (reprocessGuideBtn) {
        reprocessGuideBtn.addEventListener('click', function () {
            const guideId = this.getAttribute('data-guide-id');
            if (confirm('Are you sure you want to reprocess this guide? This will replace the existing questions with newly extracted ones.')) {
                reprocessGuide(guideId);
            }
        });
    }

    // Download guide button
    const downloadGuideButtons = document.querySelectorAll('[data-action="download-guide"]');
    downloadGuideButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            const guideId = this.getAttribute('data-guide-id');
            window.location.href = '/guides/' + guideId + '/download';
        });
    });

    // Edit guide button
    const editGuideButtons = document.querySelectorAll('[data-action="edit-guide"]');
    editGuideButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            const guideId = this.getAttribute('data-guide-id');
            window.location.href = '/guides/' + guideId + '/edit';
        });
    });

    // Delete guide button
    const deleteGuideButtons = document.querySelectorAll('[data-action="delete-guide"]');
    deleteGuideButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            const guideId = this.getAttribute('data-guide-id');
            const guideName = this.getAttribute('data-guide-name');
            deleteGuide(guideId, guideName);
        });
    });
});