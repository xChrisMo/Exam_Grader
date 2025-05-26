/**
 * Exam Grader - Results Page JavaScript
 * Handles result filtering, viewing, and management
 */

class ResultsManager {
    constructor() {
        this.currentResults = [];
        this.filteredResults = [];
        this.currentResultId = null;
        this.init();
    }

    init() {
        this.setupFilters();
        this.setupEventListeners();
        this.loadResults();
    }

    setupFilters() {
        const searchInput = document.getElementById('searchInput');
        const dateFilter = document.getElementById('dateFilter');
        const scoreFilter = document.getElementById('scoreFilter');

        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                this.applyFilters();
            }, 300));
        }

        if (dateFilter) {
            dateFilter.addEventListener('change', () => {
                this.applyFilters();
            });
        }

        if (scoreFilter) {
            scoreFilter.addEventListener('change', () => {
                this.applyFilters();
            });
        }
    }

    setupEventListeners() {
        // Load more button
        const loadMoreBtn = document.getElementById('loadMoreBtn');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => {
                this.loadMoreResults();
            });
        }

        // Delete confirmation
        const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', () => {
                this.confirmDelete();
            });
        }
    }

    loadResults() {
        // In a real implementation, this would fetch from the server
        // For now, we'll work with the results already rendered
        this.currentResults = this.extractResultsFromDOM();
        this.filteredResults = [...this.currentResults];
    }

    extractResultsFromDOM() {
        const resultElements = document.querySelectorAll('.result-item');
        return Array.from(resultElements).map(element => ({
            id: element.dataset.id || Math.random().toString(36).substr(2, 9),
            filename: element.dataset.filename || '',
            score: parseInt(element.dataset.score) || 0,
            date: element.dataset.date || '',
            element: element
        }));
    }

    applyFilters() {
        const searchTerm = document.getElementById('searchInput')?.value.toLowerCase() || '';
        const dateFilter = document.getElementById('dateFilter')?.value || 'all';
        const scoreFilter = document.getElementById('scoreFilter')?.value || 'all';

        this.filteredResults = this.currentResults.filter(result => {
            // Search filter
            const matchesSearch = !searchTerm || 
                result.filename.toLowerCase().includes(searchTerm);

            // Date filter
            const matchesDate = this.matchesDateFilter(result.date, dateFilter);

            // Score filter
            const matchesScore = this.matchesScoreFilter(result.score, scoreFilter);

            return matchesSearch && matchesDate && matchesScore;
        });

        this.updateResultsDisplay();
    }

    matchesDateFilter(dateString, filter) {
        if (filter === 'all') return true;

        const resultDate = new Date(dateString);
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

        switch (filter) {
            case 'today':
                return resultDate >= today;
            case 'week':
                const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
                return resultDate >= weekAgo;
            case 'month':
                const monthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
                return resultDate >= monthAgo;
            default:
                return true;
        }
    }

    matchesScoreFilter(score, filter) {
        if (filter === 'all') return true;

        const [min, max] = filter.split('-').map(Number);
        return score >= min && score <= max;
    }

    updateResultsDisplay() {
        // Hide all result items
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
        const totalCount = this.currentResults.length;
        const filteredCount = this.filteredResults.length;
        
        // You could add a results counter element to show this information
        console.log(`Showing ${filteredCount} of ${totalCount} results`);
    }

    clearFilters() {
        document.getElementById('searchInput').value = '';
        document.getElementById('dateFilter').value = 'all';
        document.getElementById('scoreFilter').value = 'all';
        this.applyFilters();
    }

    loadMoreResults() {
        // In a real implementation, this would load more results from the server
        ExamGraderUtils.showNotification('Loading more results...', 'info', 2000);
        
        // Simulate loading delay
        setTimeout(() => {
            ExamGraderUtils.showNotification('No more results to load', 'info', 2000);
        }, 1000);
    }

    viewResult(resultId) {
        this.currentResultId = resultId;
        
        // In a real implementation, fetch detailed result data
        const mockResultData = this.generateMockResultDetail(resultId);
        
        const modal = new bootstrap.Modal(document.getElementById('resultDetailModal'));
        const content = document.getElementById('resultDetailContent');
        
        if (content) {
            content.innerHTML = this.generateResultDetailHTML(mockResultData);
        }
        
        modal.show();
    }

    generateMockResultDetail(resultId) {
        return {
            id: resultId,
            filename: 'Student_Exam_001.pdf',
            score: 85,
            grade: 'B+',
            submissionDate: '2024-01-15 14:30:00',
            processingTime: '2.3 minutes',
            criteria: [
                { name: 'Problem Solving', score: 90, feedback: 'Excellent approach to problem-solving with clear methodology.' },
                { name: 'Code Quality', score: 80, feedback: 'Good code structure, could improve commenting.' },
                { name: 'Documentation', score: 85, feedback: 'Well-documented solution with clear explanations.' }
            ],
            overallFeedback: 'Strong performance overall. The student demonstrates good understanding of the concepts and applies them effectively. Areas for improvement include more detailed commenting in code sections.',
            suggestions: [
                'Add more inline comments to explain complex logic',
                'Consider edge cases in problem solutions',
                'Improve variable naming conventions'
            ]
        };
    }

    generateResultDetailHTML(data) {
        return `
            <div class="row">
                <div class="col-md-4">
                    <div class="card bg-light border-0 mb-3">
                        <div class="card-body text-center">
                            <div class="score-circle score-${this.getScoreClass(data.score)} mb-3">
                                <span class="score-value">${data.score}%</span>
                            </div>
                            <h5>${data.grade}</h5>
                            <p class="text-muted mb-0">Overall Grade</p>
                        </div>
                    </div>
                    
                    <div class="card border-0 mb-3">
                        <div class="card-body">
                            <h6 class="card-title">Details</h6>
                            <div class="row g-2">
                                <div class="col-6"><strong>File:</strong></div>
                                <div class="col-6">${data.filename}</div>
                                <div class="col-6"><strong>Submitted:</strong></div>
                                <div class="col-6">${ExamGraderUtils.formatDate(data.submissionDate)}</div>
                                <div class="col-6"><strong>Processed:</strong></div>
                                <div class="col-6">${data.processingTime}</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-8">
                    <div class="card border-0 mb-3">
                        <div class="card-header bg-transparent">
                            <h6 class="card-title mb-0">Criteria Breakdown</h6>
                        </div>
                        <div class="card-body">
                            ${data.criteria.map(criterion => `
                                <div class="mb-3">
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <h6 class="mb-0">${criterion.name}</h6>
                                        <span class="badge bg-${this.getScoreClass(criterion.score)}">${criterion.score}%</span>
                                    </div>
                                    <div class="progress mb-2" style="height: 6px;">
                                        <div class="progress-bar bg-${this.getScoreClass(criterion.score)}" 
                                             style="width: ${criterion.score}%"></div>
                                    </div>
                                    <p class="text-muted small mb-0">${criterion.feedback}</p>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div class="card border-0 mb-3">
                        <div class="card-header bg-transparent">
                            <h6 class="card-title mb-0">Overall Feedback</h6>
                        </div>
                        <div class="card-body">
                            <p>${data.overallFeedback}</p>
                        </div>
                    </div>
                    
                    <div class="card border-0">
                        <div class="card-header bg-transparent">
                            <h6 class="card-title mb-0">Improvement Suggestions</h6>
                        </div>
                        <div class="card-body">
                            <ul class="list-unstyled mb-0">
                                ${data.suggestions.map(suggestion => `
                                    <li class="mb-2">
                                        <i class="bi bi-lightbulb text-warning me-2"></i>
                                        ${suggestion}
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    getScoreClass(score) {
        if (score >= 90) return 'success';
        if (score >= 80) return 'primary';
        if (score >= 70) return 'warning';
        return 'danger';
    }

    downloadResult(resultId) {
        ExamGraderUtils.showNotification('Preparing download...', 'info', 2000);
        
        // In a real implementation, this would trigger a download
        setTimeout(() => {
            ExamGraderUtils.showNotification('Download started', 'success', 2000);
        }, 1000);
    }

    downloadCurrentResult() {
        if (this.currentResultId) {
            this.downloadResult(this.currentResultId);
        }
    }

    shareResult(resultId) {
        // In a real implementation, this would generate a shareable link
        const shareUrl = `${window.location.origin}/results/${resultId}`;
        
        if (navigator.share) {
            navigator.share({
                title: 'Exam Grading Result',
                text: 'Check out this grading result from Exam Grader',
                url: shareUrl
            });
        } else {
            // Fallback: copy to clipboard
            navigator.clipboard.writeText(shareUrl).then(() => {
                ExamGraderUtils.showNotification('Share link copied to clipboard', 'success', 3000);
            });
        }
    }

    deleteResult(resultId) {
        this.currentResultId = resultId;
        const modal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
        modal.show();
    }

    confirmDelete() {
        if (!this.currentResultId) return;
        
        // In a real implementation, this would make an API call to delete the result
        ExamGraderUtils.showNotification('Deleting result...', 'info', 2000);
        
        // Remove from DOM
        const resultElement = document.querySelector(`[data-id="${this.currentResultId}"]`);
        if (resultElement) {
            resultElement.remove();
        }
        
        // Update internal arrays
        this.currentResults = this.currentResults.filter(r => r.id !== this.currentResultId);
        this.filteredResults = this.filteredResults.filter(r => r.id !== this.currentResultId);
        
        // Hide modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal'));
        if (modal) {
            modal.hide();
        }
        
        setTimeout(() => {
            ExamGraderUtils.showNotification('Result deleted successfully', 'success', 3000);
        }, 500);
        
        this.currentResultId = null;
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

// Global functions for HTML onclick handlers
function viewResult(resultId) {
    if (window.resultsManager) {
        window.resultsManager.viewResult(resultId);
    }
}

function downloadResult(resultId) {
    if (window.resultsManager) {
        window.resultsManager.downloadResult(resultId);
    }
}

function shareResult(resultId) {
    if (window.resultsManager) {
        window.resultsManager.shareResult(resultId);
    }
}

function deleteResult(resultId) {
    if (window.resultsManager) {
        window.resultsManager.deleteResult(resultId);
    }
}

function clearFilters() {
    if (window.resultsManager) {
        window.resultsManager.clearFilters();
    }
}

function downloadCurrentResult() {
    if (window.resultsManager) {
        window.resultsManager.downloadCurrentResult();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.resultsManager = new ResultsManager();
});
