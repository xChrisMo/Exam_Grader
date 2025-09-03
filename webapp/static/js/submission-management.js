/**
 * Enhanced submission management with better error handling and UI updates
 */

function deleteSubmission(submissionId) {
    if (!confirm("Are you sure you want to delete this submission? This action cannot be undone.")) {
        return;
    }

    const deleteButton = document.querySelector(`#delete-button-${submissionId}`);
    const submissionRow = document.querySelector(`#submission-row-${submissionId}`);
    
    if (!deleteButton) {
        console.error('Delete button not found for submission:', submissionId);
        return;
    }

    // Show loading state
    const originalText = deleteButton.textContent;
    deleteButton.disabled = true;
    deleteButton.textContent = 'Deleting...';
    deleteButton.classList.add('opacity-50', 'cursor-not-allowed');

    // Make API request
    fetch('/api/delete-submission', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || ''
        },
        body: JSON.stringify({
            submission_id: submissionId
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Show success notification
            showNotification('Submission deleted successfully!', 'success');
            
            // Remove the row from DOM immediately
            if (submissionRow) {
                submissionRow.style.transition = 'opacity 0.3s ease-out';
                submissionRow.style.opacity = '0';
                setTimeout(() => {
                    submissionRow.remove();
                    updateSubmissionCounts();
                }, 300);
            }
            
            // Force page reload after a short delay to ensure consistency
            setTimeout(() => {
                window.location.reload(true);
            }, 1000);
            
        } else {
            throw new Error(data.error || 'Failed to delete submission');
        }
    })
    .catch(error => {
        console.error('Error deleting submission:', error);
        
        // Restore button state
        deleteButton.disabled = false;
        deleteButton.textContent = originalText;
        deleteButton.classList.remove('opacity-50', 'cursor-not-allowed');
        
        // Show error notification
        showNotification(`Error deleting submission: ${error.message}`, 'error');
    });
}

function updateSubmissionCounts() {
    // Update the statistics cards
    const totalElement = document.getElementById('total-submissions-count');
    const processedElement = document.getElementById('processed-submissions-count');
    const pendingElement = document.getElementById('pending-submissions-count');
    
    if (totalElement) {
        const currentTotal = parseInt(totalElement.textContent) || 0;
        totalElement.textContent = Math.max(0, currentTotal - 1);
    }
    
    // Update other counts based on visible rows
    const visibleRows = document.querySelectorAll('tbody tr:not([style*="display: none"])');
    let processedCount = 0;
    let pendingCount = 0;
    
    visibleRows.forEach(row => {
        const statusElement = row.querySelector('.bg-success-100, .bg-warning-100, .bg-blue-100, .bg-red-100');
        if (statusElement) {
            if (statusElement.classList.contains('bg-success-100')) {
                processedCount++;
            } else {
                pendingCount++;
            }
        }
    });
    
    if (processedElement) processedElement.textContent = processedCount;
    if (pendingElement) pendingElement.textContent = pendingCount;
}

function showNotification(message, type = 'info') {
    // Try to use ExamGrader notification system if available
    if (window.ExamGrader && window.ExamGrader.notificationManager) {
        window.ExamGrader.notificationManager.notify(message, type);
        return;
    }
    
    // Fallback to simple alert
    if (type === 'error') {
        alert('Error: ' + message);
    } else {
        alert(message);
    }
}

// Add CSRF token to all requests
document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token from meta tag or generate it
    let csrfToken = document.querySelector('meta[name=csrf-token]')?.getAttribute('content');
    
    if (!csrfToken) {
        // Try to get it from a form if available
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        if (csrfInput) {
            csrfToken = csrfInput.value;
        }
    }
    
    // Add CSRF token to all fetch requests
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        if (options.method && options.method.toUpperCase() !== 'GET') {
            options.headers = options.headers || {};
            if (csrfToken && !options.headers['X-CSRFToken']) {
                options.headers['X-CSRFToken'] = csrfToken;
            }
        }
        return originalFetch(url, options);
    };
});