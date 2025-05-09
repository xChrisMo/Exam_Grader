/**
 * Exam Grader Web Application
 * Main JavaScript file
 */

document.addEventListener('DOMContentLoaded', function() {
    // Handle file upload areas
    const fileUploadAreas = document.querySelectorAll('.file-upload-area');
    fileUploadAreas.forEach(area => {
        const input = area.querySelector('input[type="file"]');
        if (input) {
            area.addEventListener('click', () => {
                input.click();
            });
            
            area.addEventListener('dragover', (e) => {
                e.preventDefault();
                area.classList.add('border-primary');
                area.classList.add('bg-light');
            });
            
            area.addEventListener('dragleave', () => {
                area.classList.remove('border-primary');
                area.classList.remove('bg-light');
            });
            
            area.addEventListener('drop', (e) => {
                e.preventDefault();
                area.classList.remove('border-primary');
                area.classList.remove('bg-light');
                
                if (e.dataTransfer.files.length > 0) {
                    input.files = e.dataTransfer.files;
                    const form = input.closest('form');
                    if (form) {
                        // Show loading overlay if it exists
                        const loadingOverlay = document.getElementById('loadingOverlay');
                        if (loadingOverlay) {
                            loadingOverlay.classList.remove('d-none');
                            loadingOverlay.classList.add('d-flex');
                        }
                        
                        form.submit();
                    }
                }
            });
        }
    });
    
    // Handle confirmation dialogs
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            const message = button.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Show loading overlay on form submissions
    const forms = document.querySelectorAll('form:not(.no-loading)');
    forms.forEach(form => {
        form.addEventListener('submit', () => {
            const loadingOverlay = document.getElementById('loadingOverlay');
            if (loadingOverlay) {
                loadingOverlay.classList.remove('d-none');
                loadingOverlay.classList.add('d-flex');
            }
        });
    });
    
    // Dismiss alerts automatically after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000);
    });
}); 