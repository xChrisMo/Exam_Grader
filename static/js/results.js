/**
 * Exam Grader - Results Page JavaScript
 * Handles result filtering, viewing, and management
 */

class ResultsManager {
    constructor() {
        this.currentResults = [];
        this.filteredResults = [];
        this.currentPage = 1;
        this.resultsPerPage = 12;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadResults();
    }

    setupEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                this.filterResults();
            }, 300));
        }

        // Filter functionality
        const filters = ['dateFilter', 'scoreFilter'];
        filters.forEach(filterId => {
            const filter = document.getElementById(filterId);
            if (filter) {
                filter.addEventListener('change', () => {
                    this.filterResults();
                });
            }
        });

        // Load more button
        const loadMoreBtn = document.getElementById('loadMoreBtn');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => {
                this.loadMoreResults();
            });
        }
    }

    loadResults() {
        // Get results from the page data or fetch from API
        const resultItems = document.querySelectorAll('.result-item');
        this.currentResults = Array.from(resultItems).map(item => ({
            element: item,
            score: parseInt(item.dataset.score) || 0,
            date: item.dataset.date || '',
            filename: item.dataset.filename || ''
        }));
        this.filteredResults = [...this.currentResults];
    }

    filterResults() {
        const searchTerm = document.getElementById('searchInput')?.value.toLowerCase() || '';
        const dateFilter = document.getElementById('dateFilter')?.value || 'all';
        const scoreFilter = document.getElementById('scoreFilter')?.value || 'all';

        this.filteredResults = this.currentResults.filter(result => {
            // Search filter
            const matchesSearch = !searchTerm || 
                result.filename.toLowerCase().includes(searchTerm);

            // Date filter (simplified - would need proper date parsing in real implementation)
            const matchesDate = dateFilter === 'all' || this.matchesDateFilter(result.date, dateFilter);

            // Score filter
            const matchesScore = scoreFilter === 'all' || this.matchesScoreFilter(result.score, scoreFilter);

            return matchesSearch && matchesDate && matchesScore;
        });

        this.displayResults();
    }

    matchesDateFilter(date, filter) {
        // Simplified date filtering - would need proper implementation
        return true;
    }

    matchesScoreFilter(score, filter) {
        switch (filter) {
            case '90-100': return score >= 90;
            case '80-89': return score >= 80 && score < 90;
            case '70-79': return score >= 70 && score < 80;
            case '60-69': return score >= 60 && score < 70;
            case '0-59': return score < 60;
            default: return true;
        }
    }

    displayResults() {
        // Hide all results first
        this.currentResults.forEach(result => {
            result.element.style.display = 'none';
        });

        // Show filtered results
        this.filteredResults.forEach(result => {
            result.element.style.display = 'block';
        });

        // Update results count
        this.updateResultsCount();
    }

    updateResultsCount() {
        const totalCount = this.filteredResults.length;
        // Could add a results counter element to show "Showing X of Y results"
    }

    loadMoreResults() {
        // Implementation for pagination if needed
        this.currentPage++;
        // Load more results from server or show more from current set
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Global functions for template usage
function viewResult(resultId) {
    // Show result detail modal
    const modal = new bootstrap.Modal(document.getElementById('resultDetailModal'));
    
    // Load result details (would fetch from API in real implementation)
    const content = document.getElementById('resultDetailContent');
    if (content) {
        content.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading result details...</p>
            </div>
        `;
    }
    
    modal.show();
    
    // Simulate loading
    setTimeout(() => {
        if (content) {
            content.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle me-2"></i>
                    Result details would be loaded here. This is a demo implementation.
                </div>
            `;
        }
    }, 1000);
}

function downloadResult(resultId) {
    // Implement download functionality
    ExamGraderUtils.showNotification('Download functionality would be implemented here', 'info');
}

function shareResult(resultId) {
    // Implement share functionality
    ExamGraderUtils.showNotification('Share functionality would be implemented here', 'info');
}

function deleteResult(resultId) {
    // Show delete confirmation modal
    const modal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
    modal.show();
    
    // Set up confirmation handler
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    if (confirmBtn) {
        confirmBtn.onclick = () => {
            // Implement delete functionality
            ExamGraderUtils.showNotification('Delete functionality would be implemented here', 'warning');
            modal.hide();
        };
    }
}

function clearFilters() {
    // Reset all filters
    const searchInput = document.getElementById('searchInput');
    const dateFilter = document.getElementById('dateFilter');
    const scoreFilter = document.getElementById('scoreFilter');
    
    if (searchInput) searchInput.value = '';
    if (dateFilter) dateFilter.value = 'all';
    if (scoreFilter) scoreFilter.value = 'all';
    
    // Trigger filter update
    if (window.resultsManager) {
        window.resultsManager.filterResults();
    }
    
    ExamGraderUtils.showNotification('Filters cleared', 'success', 2000);
}

function downloadCurrentResult() {
    // Download the currently viewed result
    ExamGraderUtils.showNotification('Download functionality would be implemented here', 'info');
}

// Initialize results manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.resultsManager = new ResultsManager();
});
