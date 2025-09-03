/**
 * Force refresh utility to ensure UI updates after data changes
 */

// Override the existing deleteSubmission function with enhanced version
window.deleteSubmission = function(submissionId) {
    if (!confirm("Are you sure you want to delete this submission? This action cannot be undone.")) {
        return;
    }

    const deleteButton = document.querySelector(`#delete-button-${submissionId}`);
    
    if (!deleteButton) {
        console.error('Delete button not found for submission:', submissionId);
        return;
    }

    // Show loading state
    const originalText = deleteButton.textContent;
    deleteButton.disabled = true;
    deleteButton.textContent = 'Deleting...';
    deleteButton.style.opacity = '0.5';

    // Get CSRF token
    const csrfToken = document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || '';

    // Make API request with enhanced error handling
    fetch('/api/delete-submission', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        },
        body: JSON.stringify({
            submission_id: submissionId
        })
    })
    .then(response => {
        console.log('Delete response status:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Delete response data:', data);
        
        if (data.success) {
            // Show success notification
            if (window.ExamGrader && window.ExamGrader.notificationManager) {
                window.ExamGrader.notificationManager.notify('Submission deleted successfully!', 'success');
            } else {
                // Fallback notification
                const notification = document.createElement('div');
                notification.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded shadow-lg z-50';
                notification.textContent = 'Submission deleted successfully!';
                document.body.appendChild(notification);
                setTimeout(() => notification.remove(), 3000);
            }
            
            // Immediately remove the row from DOM with animation
            const submissionRow = document.querySelector(`#submission-row-${submissionId}`);
            if (submissionRow) {
                submissionRow.style.transition = 'all 0.3s ease-out';
                submissionRow.style.opacity = '0';
                submissionRow.style.transform = 'translateX(-100%)';
                
                setTimeout(() => {
                    submissionRow.remove();
                    updateSubmissionCounts();
                }, 300);
            }
            
            // Force page reload after a short delay to ensure all data is fresh
            setTimeout(() => {
                // Add cache-busting parameter and reload
                const url = new URL(window.location);
                url.searchParams.set('_t', Date.now());
                window.location.href = url.toString();
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
        deleteButton.style.opacity = '1';
        
        // Show error notification
        const errorMessage = `Error deleting submission: ${error.message}`;
        if (window.ExamGrader && window.ExamGrader.notificationManager) {
            window.ExamGrader.notificationManager.notify(errorMessage, 'error');
        } else {
            alert(errorMessage);
        }
    });
};

// Function to update submission counts after deletion
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

// Add cache-busting to all navigation
document.addEventListener('DOMContentLoaded', function() {
    // Add timestamp to all internal links to prevent caching
    const links = document.querySelectorAll('a[href^="/"]');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href && !href.includes('?')) {
                this.setAttribute('href', href + '?t=' + Date.now());
            }
        });
    });
    
    console.log('Force refresh utility loaded');
});