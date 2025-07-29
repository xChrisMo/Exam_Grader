/**
 * Model Testing JavaScript Functions
 * 
 * Handles model testing functionality for the LLM training page.
 */

// Model Testing Functions
async function loadModelTests() {
    try {
        const response = await fetch('/llm-training/api/model-tests');
        const data = await response.json();
        
        if (data.success) {
            // Initialize modelTests if documentManager doesn't exist
            if (typeof window.documentManager !== 'undefined') {
                window.documentManager.modelTests = data.tests || [];
            } else {
                // Create a simple fallback object
                window.modelTests = data.tests || [];
            }
            renderModelTests();
            updateTestingStats();
        } else {
            console.error('Failed to load model tests:', data.error);
            showError(data.error || 'Failed to load model tests');
        }
    } catch (error) {
        console.error('Error loading model tests:', error);
        showError('Failed to load model tests. Please check your connection.');
    }
}

function renderModelTests() {
    const container = document.getElementById('model-tests-container');
    const emptyState = document.getElementById('tests-empty-state');
    
    if (!container) return;
    
    // Get model tests from documentManager or fallback
    const modelTests = (window.documentManager && window.documentManager.modelTests) || window.modelTests || [];
    
    if (modelTests.length === 0) {
        if (emptyState) emptyState.style.display = 'block';
        return;
    }
    
    if (emptyState) emptyState.style.display = 'none';
    
    const testsHtml = modelTests.map(test => renderModelTest(test)).join('');
    container.innerHTML = testsHtml;
}

function renderModelTest(test) {
    const progress = test.progress || 0;
    const statusClass = `status-${test.status}`;
    
    let createdAt = 'Unknown';
    try {
        if (test.created_at) {
            createdAt = new Date(test.created_at).toLocaleDateString();
        }
    } catch (e) {
        console.warn('Invalid date format for test:', test.id);
    }
    
    return `
        <div class="training-job">
            <div class="job-header">
                <div class="job-name">${test.name || 'Unnamed Test'}</div>
                <span class="job-status ${statusClass}">${test.status || 'unknown'}</span>
            </div>
            <div class="job-meta">
                <div>Training Job: ${test.training_job_id || 'Not specified'}</div>
                <div>Created: ${createdAt}</div>
                <div>Progress: ${progress}%</div>
                <div>Submissions: ${test.processed_submissions || 0}/${test.total_submissions || 0}</div>
                ${test.accuracy_score ? `<div>Accuracy: ${(test.accuracy_score * 100).toFixed(1)}%</div>` : ''}
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progress}%"></div>
            </div>
            <div class="job-actions">
                ${test.status === 'pending' ? 
                    `<button class="btn btn-sm btn-primary" onclick="showUploadTestSubmissionsModal('${test.id}')">Upload Submissions</button>` : ''}
                ${test.status === 'ready' ? 
                    `<button class="btn btn-sm btn-primary" onclick="runModelTest('${test.id}')">Run Test</button>` : ''}
                ${test.status === 'running' ? 
                    `<button class="btn btn-sm btn-danger" onclick="cancelModelTest('${test.id}')">Cancel</button>` : ''}
                ${test.status === 'completed' ? 
                    `<button class="btn btn-sm btn-primary" onclick="showTestResults('${test.id}')">View Results</button>` : ''}
                <button class="btn btn-sm btn-secondary" onclick="showTestDetails('${test.id}')">Details</button>
                ${test.status !== 'running' ? 
                    `<button class="btn btn-sm btn-danger" onclick="deleteModelTest('${test.id}', '${(test.name || 'this test').replace(/'/g, '\\\'')}')" title="Delete this test">Delete</button>` : ''}
            </div>
        </div>
    `;
}

function updateTestingStats() {
    // Get model tests from documentManager or fallback
    const modelTests = (window.documentManager && window.documentManager.modelTests) || window.modelTests || [];
    
    const totalTests = modelTests.length;
    const runningTests = modelTests.filter(t => t.status === 'running').length;
    const completedTests = modelTests.filter(t => t.status === 'completed').length;
    
    // Calculate average accuracy
    const completedTestsWithAccuracy = modelTests.filter(t => 
        t.status === 'completed' && t.accuracy_score !== null && t.accuracy_score !== undefined
    );
    const avgAccuracy = completedTestsWithAccuracy.length > 0 
        ? (completedTestsWithAccuracy.reduce((sum, t) => sum + t.accuracy_score, 0) / completedTestsWithAccuracy.length * 100)
        : 0;
    
    safeUpdateElement('total-tests', totalTests);
    safeUpdateElement('running-tests', runningTests);
    safeUpdateElement('completed-tests', completedTests);
    safeUpdateElement('average-accuracy', `${avgAccuracy.toFixed(1)}%`);
}

// Modal Functions
function showCreateTestModal() {
    // Load completed training jobs for selection
    loadCompletedTrainingJobs();
    document.getElementById('create-test-modal').classList.add('show');
}

function hideCreateTestModal() {
    document.getElementById('create-test-modal').classList.remove('show');
    document.getElementById('create-test-form').reset();
}

function showUploadTestSubmissionsModal(testId) {
    if (window.documentManager) {
        window.documentManager.currentTestId = testId;
    } else {
        window.currentTestId = testId;
    }
    setupTestFileUpload();
    document.getElementById('upload-test-submissions-modal').classList.add('show');
}

function hideUploadTestSubmissionsModal() {
    document.getElementById('upload-test-submissions-modal').classList.remove('show');
    resetTestFileUpload();
}

function showTestResults(testId) {
    loadTestResults(testId);
    document.getElementById('test-results-modal').classList.add('show');
}

function hideTestResultsModal() {
    document.getElementById('test-results-modal').classList.remove('show');
}

// Test Management Functions
async function createModelTest() {
    const formData = {
        name: document.getElementById('test-name').value,
        description: document.getElementById('test-description').value,
        training_job_id: document.getElementById('test-training-job').value,
        confidence_threshold: parseFloat(document.getElementById('test-confidence-threshold').value),
        comparison_mode: document.getElementById('test-comparison-mode').value,
        feedback_level: document.getElementById('test-feedback-level').value
    };
    
    try {
        const response = await fetch('/llm-training/api/model-tests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            await loadModelTests(); // Refresh the list
            hideCreateTestModal();
            showSuccess('Model test created successfully');
        } else {
            showError(data.error || 'Failed to create model test');
        }
    } catch (error) {
        console.error('Error creating model test:', error);
        showError('Failed to create model test');
    }
}

async function runModelTest(testId) {
    try {
        const response = await fetch(`/llm-training/api/model-tests/${testId}/run`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Model test started successfully');
            // Start polling for updates
            startTestStatusPolling(testId);
        } else {
            showError(data.error || 'Failed to start model test');
        }
    } catch (error) {
        console.error('Error starting model test:', error);
        showError('Failed to start model test');
    }
}

async function cancelModelTest(testId) {
    if (!confirm('Are you sure you want to cancel this test?')) {
        return;
    }
    
    try {
        const response = await fetch(`/llm-training/api/model-tests/${testId}/cancel`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Model test cancelled successfully');
            await loadModelTests(); // Refresh the list
        } else {
            showError(data.error || 'Failed to cancel model test');
        }
    } catch (error) {
        console.error('Error cancelling model test:', error);
        showError('Failed to cancel model test');
    }
}

async function deleteModelTest(testId, testName) {
    if (!confirm(`Are you sure you want to delete "${testName}"? This action cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/llm-training/api/model-tests/${testId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(data.message || 'Model test deleted successfully');
            await loadModelTests(); // Refresh the list
        } else {
            showError(data.error || 'Failed to delete model test');
        }
    } catch (error) {
        console.error('Error deleting model test:', error);
        showError('Failed to delete model test');
    }
}

// File Upload Functions
function setupTestFileUpload() {
    const fileInput = document.getElementById('test-file-input');
    const uploadArea = document.getElementById('test-upload-area');
    const uploadBtn = document.getElementById('upload-test-submissions-btn');
    
    if (!fileInput || !uploadArea) return;
    
    // Reset state
    resetTestFileUpload();
    
    // Drag and drop
    uploadArea.addEventListener('dragover', handleTestDragOver);
    uploadArea.addEventListener('dragleave', handleTestDragLeave);
    uploadArea.addEventListener('drop', handleTestDrop);
    
    // File input change
    fileInput.addEventListener('change', handleTestFileSelect);
}

function resetTestFileUpload() {
    const filesList = document.getElementById('test-files-list');
    const uploadBtn = document.getElementById('upload-test-submissions-btn');
    
    if (filesList) filesList.style.display = 'none';
    if (uploadBtn) uploadBtn.disabled = true;
    
    // Clear selected files
    const fileInput = document.getElementById('test-file-input');
    if (fileInput) fileInput.value = '';
}

function handleTestDragOver(e) {
    e.preventDefault();
    e.currentTarget.style.borderColor = '#3b82f6';
    e.currentTarget.style.backgroundColor = '#f0f9ff';
}

function handleTestDragLeave(e) {
    e.preventDefault();
    e.currentTarget.style.borderColor = '#d1d5db';
    e.currentTarget.style.backgroundColor = 'transparent';
}

function handleTestDrop(e) {
    e.preventDefault();
    e.currentTarget.style.borderColor = '#d1d5db';
    e.currentTarget.style.backgroundColor = 'transparent';
    
    const files = Array.from(e.dataTransfer.files);
    displayTestFiles(files);
}

function handleTestFileSelect(e) {
    const files = Array.from(e.target.files);
    displayTestFiles(files);
}

function displayTestFiles(files) {
    const filesList = document.getElementById('test-files-list');
    const filesContainer = document.getElementById('test-files-container');
    const uploadBtn = document.getElementById('upload-test-submissions-btn');
    
    if (!filesList || !filesContainer) return;
    
    if (files.length === 0) {
        filesList.style.display = 'none';
        uploadBtn.disabled = true;
        return;
    }
    
    // Display selected files
    filesContainer.innerHTML = files.map((file, index) => `
        <div class="file-item" style="display: flex; justify-content: space-between; align-items: center; padding: 8px; border: 1px solid #e5e7eb; border-radius: 4px; margin-bottom: 8px;">
            <div>
                <strong>${file.name}</strong>
                <span style="color: #6b7280; font-size: 0.875rem;"> (${formatFileSize(file.size)})</span>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
                <input type="number" placeholder="Expected Grade (0-1)" step="0.01" min="0" max="1" 
                       id="expected-grade-${index}" style="width: 120px; padding: 4px; border: 1px solid #d1d5db; border-radius: 4px;">
                <button type="button" onclick="removeTestFile(${index})" style="color: #ef4444; background: none; border: none; cursor: pointer;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
    `).join('');
    
    filesList.style.display = 'block';
    uploadBtn.disabled = false;
    
    // Store files for upload
    window.selectedTestFiles = files;
}

function removeTestFile(index) {
    if (!window.selectedTestFiles) return;
    
    const files = Array.from(window.selectedTestFiles);
    files.splice(index, 1);
    window.selectedTestFiles = files;
    
    displayTestFiles(files);
}

async function uploadTestSubmissions() {
    if (!window.selectedTestFiles || window.selectedTestFiles.length === 0) {
        documentManager.showError('No files selected');
        return;
    }
    
    const testId = documentManager.currentTestId;
    if (!testId) {
        documentManager.showError('No test selected');
        return;
    }
    
    const uploadProgress = document.getElementById('test-upload-progress');
    const uploadBar = document.getElementById('test-upload-bar');
    const uploadPercentage = document.getElementById('test-upload-percentage');
    
    try {
        if (uploadProgress) uploadProgress.style.display = 'block';
        
        // Create FormData
        const formData = new FormData();
        
        Array.from(window.selectedTestFiles).forEach((file, index) => {
            formData.append('files', file);
            
            // Add expected grade if provided
            const expectedGradeInput = document.getElementById(`expected-grade-${index}`);
            if (expectedGradeInput && expectedGradeInput.value) {
                formData.append(`expected_grade_${file.name}`, expectedGradeInput.value);
            }
        });
        
        // Simulate progress
        let progressInterval = setInterval(() => {
            if (uploadBar && uploadPercentage) {
                const currentWidth = parseFloat(uploadBar.style.width) || 0;
                if (currentWidth < 90) {
                    const newWidth = Math.min(currentWidth + Math.random() * 10, 90);
                    uploadBar.style.width = `${newWidth}%`;
                    uploadPercentage.textContent = `${Math.round(newWidth)}%`;
                }
            }
        }, 200);
        
        const response = await fetch(`/llm-training/api/model-tests/${testId}/submissions`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': documentManager.getCSRFToken()
            },
            body: formData
        });
        
        clearInterval(progressInterval);
        
        const data = await response.json();
        
        if (data.success) {
            if (uploadBar) uploadBar.style.width = '100%';
            if (uploadPercentage) uploadPercentage.textContent = '100%';
            
            setTimeout(() => {
                if (uploadProgress) uploadProgress.style.display = 'none';
                hideUploadTestSubmissionsModal();
                documentManager.showSuccess(data.message || 'Test submissions uploaded successfully');
                loadModelTests(); // Refresh the list
            }, 500);
        } else {
            if (uploadProgress) uploadProgress.style.display = 'none';
            documentManager.showError(data.error || 'Failed to upload test submissions');
        }
        
    } catch (error) {
        console.error('Error uploading test submissions:', error);
        if (uploadProgress) uploadProgress.style.display = 'none';
        documentManager.showError('Failed to upload test submissions');
    }
}

// Helper Functions
async function loadCompletedTrainingJobs() {
    try {
        const response = await fetch('/llm-training/api/training-jobs');
        const data = await response.json();
        
        if (data.success) {
            const completedJobs = data.jobs.filter(job => job.status === 'completed');
            const select = document.getElementById('test-training-job');
            
            if (select) {
                select.innerHTML = '<option value="">Select a completed training job...</option>';
                completedJobs.forEach(job => {
                    const option = document.createElement('option');
                    option.value = job.id;
                    option.textContent = `${job.name} (${job.model_id})`;
                    select.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('Error loading completed training jobs:', error);
    }
}

async function loadTestResults(testId) {
    try {
        const response = await fetch(`/llm-training/api/model-tests/${testId}/results`);
        const data = await response.json();
        
        if (data.success) {
            displayTestResults(data.results);
        } else {
            documentManager.showError(data.error || 'Failed to load test results');
        }
    } catch (error) {
        console.error('Error loading test results:', error);
        documentManager.showError('Failed to load test results');
    }
}

function displayTestResults(results) {
    const content = document.getElementById('test-results-content');
    const title = document.getElementById('test-results-title');
    
    if (!content) return;
    
    const testInfo = results.test_info;
    const submissions = results.submissions;
    const summary = results.summary;
    
    if (title) {
        title.textContent = `Test Results: ${testInfo.name}`;
    }
    
    content.innerHTML = `
        <div style="margin-bottom: 20px;">
            <h4>Test Summary</h4>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">${summary.processed_submissions || 0}</div>
                    <div class="stat-label">Processed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${summary.accurate_grades || 0}</div>
                    <div class="stat-label">Accurate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${((summary.average_accuracy || 0) * 100).toFixed(1)}%</div>
                    <div class="stat-label">Accuracy</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${((summary.average_confidence || 0) * 100).toFixed(1)}%</div>
                    <div class="stat-label">Confidence</div>
                </div>
            </div>
        </div>
        
        <div>
            <h4>Submission Results</h4>
            <div style="max-height: 400px; overflow-y: auto;">
                ${submissions.map(sub => `
                    <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <strong>${sub.original_name}</strong>
                            <span class="tag ${sub.grade_accuracy ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                                ${sub.grade_accuracy ? 'Accurate' : 'Inaccurate'}
                            </span>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; font-size: 0.875rem;">
                            <div>
                                <div><strong>Expected Grade:</strong> ${sub.expected_grade !== null ? sub.expected_grade.toFixed(2) : 'N/A'}</div>
                                <div><strong>Model Grade:</strong> ${sub.model_grade !== null ? sub.model_grade.toFixed(2) : 'N/A'}</div>
                                <div><strong>Difference:</strong> ${sub.grade_difference !== null ? sub.grade_difference.toFixed(3) : 'N/A'}</div>
                            </div>
                            <div>
                                <div><strong>Confidence:</strong> ${sub.confidence_score !== null ? (sub.confidence_score * 100).toFixed(1) + '%' : 'N/A'}</div>
                                <div><strong>Status:</strong> ${sub.processing_status}</div>
                                <div><strong>Words:</strong> ${sub.word_count || 0}</div>
                            </div>
                        </div>
                        ${sub.model_feedback ? `
                            <div style="margin-top: 12px; padding: 8px; background: #f9fafb; border-radius: 4px;">
                                <strong>Model Feedback:</strong><br>
                                <span style="font-size: 0.875rem;">${sub.model_feedback}</span>
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function startTestStatusPolling(testId) {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/llm-training/api/model-tests/${testId}/status`);
            const data = await response.json();
            
            if (data.success) {
                const status = data.status;
                
                // Update the test in our local array
                const testIndex = documentManager.modelTests.findIndex(t => t.id === testId);
                if (testIndex !== -1) {
                    Object.assign(documentManager.modelTests[testIndex], status);
                    renderModelTests();
                    updateTestingStats();
                }
                
                // Stop polling if test is complete
                if (['completed', 'failed', 'cancelled'].includes(status.status)) {
                    clearInterval(pollInterval);
                    
                    if (status.status === 'completed') {
                        documentManager.showSuccess('Model test completed successfully');
                    } else if (status.status === 'failed') {
                        documentManager.showError(`Model test failed: ${status.error_message || 'Unknown error'}`);
                    }
                }
            }
        } catch (error) {
            console.error('Error polling test status:', error);
            clearInterval(pollInterval);
        }
    }, 2000); // Poll every 2 seconds
}

function showTestDetails(testId) {
    const test = documentManager.modelTests.find(t => t.id === testId);
    if (!test) return;
    
    // This would show detailed test information
    // For now, just show an alert with basic info
    alert(`Test Details:\nName: ${test.name}\nStatus: ${test.status}\nProgress: ${test.progress}%`);
}

// Helper functions for when documentManager is not available
function safeUpdateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function showError(message) {
    if (window.documentManager && window.documentManager.showError) {
        window.documentManager.showError(message);
    } else if (window.ExamGrader && window.ExamGrader.notificationManager) {
        window.ExamGrader.notificationManager.notify(message, 'error');
    } else {
        console.error(message);
        alert('Error: ' + message);
    }
}

function showSuccess(message) {
    if (window.documentManager && window.documentManager.showSuccess) {
        window.documentManager.showSuccess(message);
    } else if (window.ExamGrader && window.ExamGrader.notificationManager) {
        window.ExamGrader.notificationManager.notify(message, 'success');
    } else {
        console.log(message);
    }
}

function getCSRFToken() {
    if (window.documentManager && window.documentManager.getCSRFToken) {
        return window.documentManager.getCSRFToken();
    } else if (window.ExamGrader && window.ExamGrader.csrf) {
        return window.ExamGrader.csrf.getToken();
    } else {
        const metaTag = document.querySelector('meta[name=csrf-token]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }
}

function formatFileSize(bytes) {
    if (window.documentManager && window.documentManager.formatFileSize) {
        return window.documentManager.formatFileSize(bytes);
    } else if (window.ExamGrader && window.ExamGrader.utils) {
        return window.ExamGrader.utils.formatFileSize(bytes);
    } else {
        // Simple fallback
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Add event listeners for the create test form
document.addEventListener('DOMContentLoaded', function() {
    const createTestForm = document.getElementById('create-test-form');
    if (createTestForm) {
        createTestForm.addEventListener('submit', (e) => {
            e.preventDefault();
            createModelTest();
        });
    }
    
    // Load model tests on page load
    loadModelTests();
    
    // Auto-refresh model tests every 10 seconds
    setInterval(() => {
        loadModelTests();
    }, 10000);
});