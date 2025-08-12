// Enhanced deleteSubmission function with better error handling and immediate UI updates
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

    // Get CSRF token
    const csrfToken = document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || '';

    // Make API request
    fetch('/api/delete-submission', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
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
            if (window.ExamGrader && window.ExamGrader.notificationManager) {
                window.ExamGrader.notificationManager.notify('Submission deleted successfully!', 'success');
            }
            
            // Remove the row from DOM immediately with animation
            if (submissionRow) {
                submissionRow.style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';
                submissionRow.style.opacity = '0';
                submissionRow.style.transform = 'translateX(-100%)';
                
                setTimeout(() => {
                    submissionRow.remove();
                    updateSubmissionCounts();
                }, 300);
            }
            
            // Force page reload after a short delay to ensure all data is fresh
            setTimeout(() => {
                // Clear any browser cache and reload
                if ('caches' in window) {
                    caches.keys().then(names => {
                        names.forEach(name => {
                            caches.delete(name);
                        });
                    });
                }
                window.location.reload(true);
            }, 1500);
            
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
        if (window.ExamGrader && window.ExamGrader.notificationManager) {
            window.ExamGrader.notificationManager.notify(`Error deleting submission: ${error.message}`, 'error');
        } else {
            alert(`Error deleting submission: ${error.message}`);
        }
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
    
    // Count visible rows to update processed/pending counts
    const visibleRows = document.querySelectorAll('tbody tr:not([style*="display: none"]):not([style*="opacity: 0"])');
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

// Override the existing function when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // The enhanced deleteSubmission function is now available globally
    console.log('Enhanced submission deletion loaded');
});