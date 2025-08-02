// Helper function to get CSRF token
function getCSRFToken() {
  const metaTag = document.querySelector('meta[name=csrf-token]');
  if (metaTag && metaTag.getAttribute('content')) {
    return metaTag.getAttribute('content');
  }
  
  const tokenInput = document.querySelector('input[name=csrf_token]');
  if (tokenInput && tokenInput.value) {
    return tokenInput.value;
  }
  
  console.warn('CSRF token not found');
  return '';
}

// Global configuration object
let llmConfig = null;

// Button state management
let buttonStates = {
  hasTrainingGuides: false,
  hasCompletedTrainingJob: false,
  hasTestSubmissions: false,
  isTrainingInProgress: false
};

document.addEventListener('DOMContentLoaded', function() {
  // Set up event listeners first (these should work regardless of configuration)
  setupEventListeners();
  
  // Initialize button states
  updateButtonStates();
  
  // Then load configuration and initialize page
  loadConfiguration().then(() => {
    loadTrainingGuides();
    loadTrainingJobs();
    loadTestSubmissions();
    loadReports();
  }).catch(error => {
    console.error('Failed to load configuration:', error);
    showError('Failed to load system configuration');
    // Still load data even if configuration fails
    loadTrainingGuides();
    loadTrainingJobs();
    loadTestSubmissions();
    loadReports();
  });
});

function setupEventListeners() {
  // Event listeners for main buttons with null checks and validation
  const buttons = [
    { id: 'upload-training-guide-btn', handler: showUploadTrainingGuideModal },
    { id: 'create-training-job-btn', handler: handleCreateTrainingJobClick },
    { id: 'upload-test-submission-btn', handler: handleUploadTestSubmissionClick },
    { id: 'generate-report-btn', handler: handleGenerateReportClick }
  ];

  buttons.forEach(({ id, handler }) => {
    const element = document.getElementById(id);
    if (element) {
      element.addEventListener('click', handler);
    } else {
      console.warn(`Button with ID '${id}' not found`);
    }
  });

  // Modal event listeners with error handling
  const modalListeners = [
    { id: 'confirm-upload-training-guide', handler: uploadTrainingGuide },
    { id: 'cancel-upload-training-guide', handler: hideUploadTrainingGuideModal },
    { id: 'confirm-create-training-job', handler: createTrainingJob },
    { id: 'cancel-create-training-job', handler: hideCreateTrainingJobModal },
    { id: 'confirm-upload-test-submission', handler: uploadTestSubmission },
    { id: 'cancel-upload-test-submission', handler: hideUploadTestSubmissionModal }
  ];

  modalListeners.forEach(({ id, handler }) => {
    const element = document.getElementById(id);
    if (element) {
      element.addEventListener('click', handler);
    } else {
      console.warn(`Modal element with ID '${id}' not found`);
    }
  });

  // File input handlers with validation
  const fileInputs = [
    { fileId: 'training-guide-file', nameId: 'training-guide-file-name' },
    { fileId: 'test-submission-file', nameId: 'test-submission-file-name' }
  ];

  fileInputs.forEach(({ fileId, nameId }) => {
    const fileInput = document.getElementById(fileId);
    const nameDisplay = document.getElementById(nameId);
    
    if (fileInput && nameDisplay) {
      fileInput.addEventListener('change', function(e) {
        const fileName = e.target.files[0] ? e.target.files[0].name : '';
        nameDisplay.textContent = fileName;
        
        // Show file size if file is selected
        if (e.target.files[0]) {
          const fileSize = getFormattedFileSize(e.target.files[0].size);
          nameDisplay.textContent = `${fileName} (${fileSize})`;
        }
      });
    } else {
      console.warn(`File input elements '${fileId}' or '${nameId}' not found`);
    }
  });
}

// Button state management functions
function updateButtonStates() {
  // Update button states based on current data
  updateCreateTrainingJobButton();
  updateUploadTestSubmissionButton();
  updateGenerateReportButton();
  updateStepIndicators();
}

function updateCreateTrainingJobButton() {
  const button = document.getElementById('create-training-job-btn');
  if (!button) return;
  
  if (buttonStates.hasTrainingGuides) {
    enableButton(button, 'Create Training Job');
  } else {
    disableButton(button, 'Upload training guide first');
  }
}

function updateUploadTestSubmissionButton() {
  const button = document.getElementById('upload-test-submission-btn');
  if (!button) return;
  
  if (buttonStates.hasCompletedTrainingJob) {
    enableButton(button, 'Upload Test Submission');
  } else if (buttonStates.isTrainingInProgress) {
    disableButton(button, 'Training in progress...');
  } else if (buttonStates.hasTrainingGuides) {
    disableButton(button, 'Complete training job first');
  } else {
    disableButton(button, 'Upload training guide and complete training first');
  }
}

function updateGenerateReportButton() {
  const button = document.getElementById('generate-report-btn');
  if (!button) return;
  
  if (buttonStates.hasTestSubmissions && buttonStates.hasCompletedTrainingJob) {
    enableButton(button, 'Generate Report');
  } else if (!buttonStates.hasCompletedTrainingJob) {
    disableButton(button, 'Complete training job first');
  } else if (!buttonStates.hasTestSubmissions) {
    disableButton(button, 'Upload test submissions first');
  } else {
    disableButton(button, 'Requirements not met');
  }
}

function enableButton(button, text) {
  button.disabled = false;
  button.textContent = text;
  button.classList.remove('opacity-50', 'cursor-not-allowed');
  button.classList.add('hover:opacity-90', 'cursor-pointer');
  button.title = '';
}

function disableButton(button, reason) {
  button.disabled = true;
  button.textContent = reason;
  button.classList.add('opacity-50', 'cursor-not-allowed');
  button.classList.remove('hover:opacity-90', 'cursor-pointer');
  button.title = reason;
}

// Button click handlers with validation
function handleCreateTrainingJobClick(e) {
  if (!buttonStates.hasTrainingGuides) {
    e.preventDefault();
    showError('Please upload a training guide first');
    return;
  }
  showCreateTrainingJobModal();
}

function handleUploadTestSubmissionClick(e) {
  if (!buttonStates.hasCompletedTrainingJob) {
    e.preventDefault();
    if (buttonStates.isTrainingInProgress) {
      showError('Please wait for training to complete');
    } else {
      showError('Please complete a training job first');
    }
    return;
  }
  showUploadTestSubmissionModal();
}

function handleGenerateReportClick(e) {
  if (!buttonStates.hasCompletedTrainingJob || !buttonStates.hasTestSubmissions) {
    e.preventDefault();
    if (!buttonStates.hasCompletedTrainingJob) {
      showError('Please complete a training job first');
    } else {
      showError('Please upload test submissions first');
    }
    return;
  }
  generateReport();
}

// Modal functions with error handling
function showUploadTrainingGuideModal() {
  const modal = document.getElementById('upload-training-guide-modal');
  if (modal) {
    modal.classList.remove('hidden');
  } else {
    console.error('Upload training guide modal not found');
  }
}

function hideUploadTrainingGuideModal() {
  const modal = document.getElementById('upload-training-guide-modal');
  if (modal) {
    modal.classList.add('hidden');
    clearUploadTrainingGuideForm();
  }
}

function showCreateTrainingJobModal() {
  const modal = document.getElementById('create-training-job-modal');
  if (modal) {
    loadTrainingGuidesForJob();
    modal.classList.remove('hidden');
  } else {
    console.error('Create training job modal not found');
  }
}

function hideCreateTrainingJobModal() {
  const modal = document.getElementById('create-training-job-modal');
  if (modal) {
    modal.classList.add('hidden');
    clearCreateTrainingJobForm();
  }
}

function showUploadTestSubmissionModal() {
  const modal = document.getElementById('upload-test-submission-modal');
  if (modal) {
    modal.classList.remove('hidden');
  } else {
    console.error('Upload test submission modal not found');
  }
}

function hideUploadTestSubmissionModal() {
  const modal = document.getElementById('upload-test-submission-modal');
  if (modal) {
    modal.classList.add('hidden');
    clearUploadTestSubmissionForm();
  }
}

// Form clearing functions with error handling
function clearUploadTrainingGuideForm() {
  const fields = [
    'training-guide-name',
    'training-guide-description', 
    'training-guide-file'
  ];
  
  fields.forEach(fieldId => {
    const element = document.getElementById(fieldId);
    if (element) {
      element.value = '';
    }
  });
  
  const fileName = document.getElementById('training-guide-file-name');
  if (fileName) {
    fileName.textContent = '';
  }
}

function clearCreateTrainingJobForm() {
  const fields = [
    'training-job-name',
    'training-job-guide',
    'training-job-model'
  ];
  
  fields.forEach(fieldId => {
    const element = document.getElementById(fieldId);
    if (element) {
      element.value = '';
    }
  });
}

function clearUploadTestSubmissionForm() {
  const fields = [
    'test-submission-name',
    'test-submission-expected-score',
    'test-submission-file'
  ];
  
  fields.forEach(fieldId => {
    const element = document.getElementById(fieldId);
    if (element) {
      element.value = '';
    }
  });
  
  const fileName = document.getElementById('test-submission-file-name');
  if (fileName) {
    fileName.textContent = '';
  }
}

// API functions with improved error handling
function uploadTrainingGuide() {
  const nameElement = document.getElementById('training-guide-name');
  const descriptionElement = document.getElementById('training-guide-description');
  const fileElement = document.getElementById('training-guide-file');

  if (!nameElement || !descriptionElement || !fileElement) {
    showError('Form elements not found');
    return;
  }

  const name = nameElement.value.trim();
  const description = descriptionElement.value.trim();
  const file = fileElement.files[0];

  // Validation
  if (!name) {
    showError('Please provide a name for the training guide');
    nameElement.focus();
    return;
  }

  if (!file) {
    showError('Please select a file to upload');
    fileElement.focus();
    return;
  }

  // Validate file format
  if (!validateFileFormat(file, 'training_guide')) {
    const allowedFormats = llmConfig?.file_formats?.training_guides || ['.pdf', '.doc', '.docx', '.txt', '.md'];
    showError(`Invalid file format. Allowed formats: ${allowedFormats.join(', ')}`);
    return;
  }

  // Validate file size
  if (!validateFileSize(file)) {
    const maxSize = llmConfig?.limits?.max_file_size_mb || 50;
    showError(`File size too large. Maximum allowed size: ${maxSize}MB. Your file: ${getFormattedFileSize(file.size)}`);
    return;
  }

  const formData = new FormData();
  formData.append('name', name);
  formData.append('description', description);
  formData.append('file', file);
  formData.append('csrf_token', getCSRFToken());

  showLoading();
  
  fetch('/llm-training/api/training-guides/upload', {
    method: 'POST',
    body: formData
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    hideLoading();
    if (data.success) {
      hideUploadTrainingGuideModal();
      loadTrainingGuides();
      showSuccess('Training guide uploaded successfully');
    } else {
      showError(data.error || 'Failed to upload training guide');
    }
  })
  .catch(error => {
    hideLoading();
    console.error('Upload error:', error);
    showError('Error uploading training guide: ' + error.message);
  });
}

function createTrainingJob() {
  const nameElement = document.getElementById('training-job-name');
  const guideElement = document.getElementById('training-job-guide');
  const modelElement = document.getElementById('training-job-model');

  if (!nameElement || !guideElement || !modelElement) {
    showError('Form elements not found');
    return;
  }

  const name = nameElement.value.trim();
  const guideId = guideElement.value;
  const model = modelElement.value;

  // Validation
  if (!name) {
    showError('Please provide a name for the training job');
    nameElement.focus();
    return;
  }

  if (!guideId) {
    showError('Please select a training guide');
    guideElement.focus();
    return;
  }

  if (!model) {
    showError('Please select a model');
    modelElement.focus();
    return;
  }

  showLoading();

  // Step 1: Create a dataset from the selected guide
  const datasetData = {
    name: `${name} Dataset`,
    description: `Dataset created for training job: ${name}`,
    csrf_token: getCSRFToken()
  };

  fetch('/llm-training/api/datasets', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify(datasetData)
  })
  .then(response => response.json())
  .then(datasetResult => {
    if (!datasetResult.success) {
      throw new Error(datasetResult.error || 'Failed to create dataset');
    }

    const datasetId = datasetResult.dataset.id;

    // Step 2: Add the selected guide to the dataset
    return fetch(`/llm-training/api/datasets/${datasetId}/documents`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()
      },
      body: JSON.stringify({
        document_ids: [guideId],
        csrf_token: getCSRFToken()
      })
    });
  })
  .then(response => response.json())
  .then(addDocResult => {
    if (!addDocResult.success) {
      throw new Error(addDocResult.error || 'Failed to add guide to dataset');
    }

    // Step 3: Create the training job with the dataset
    const defaults = llmConfig?.training_defaults || {};
    const jobData = {
      name: name,
      dataset_id: addDocResult.dataset_id || addDocResult.dataset.id,
      model: model,
      epochs: defaults.epochs || 10,
      batch_size: defaults.batch_size || 8,
      learning_rate: defaults.learning_rate || 0.0001,
      max_tokens: defaults.max_tokens || 512,
      temperature: defaults.temperature || 0.7,
      csrf_token: getCSRFToken()
    };

    return fetch('/llm-training/api/training-jobs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()
      },
      body: JSON.stringify(jobData)
    });
  })
  .then(response => response.json())
  .then(jobResult => {
    hideLoading();
    if (jobResult.success) {
      hideCreateTrainingJobModal();
      loadTrainingJobs();
      showSuccess('Training job created successfully');
    } else {
      showError(jobResult.error || 'Failed to create training job');
    }
  })
  .catch(error => {
    hideLoading();
    showError('Error creating training job: ' + error.message);
  });
}

function uploadTestSubmission() {
  const nameElement = document.getElementById('test-submission-name');
  const expectedScoreElement = document.getElementById('test-submission-expected-score');
  const fileElement = document.getElementById('test-submission-file');

  if (!nameElement || !expectedScoreElement || !fileElement) {
    showError('Form elements not found');
    return;
  }

  const name = nameElement.value.trim();
  const expectedScore = expectedScoreElement.value.trim();
  const file = fileElement.files[0];

  // Validation
  if (!name) {
    showError('Please provide a name for the test submission');
    nameElement.focus();
    return;
  }

  if (!file) {
    showError('Please select a file to upload');
    fileElement.focus();
    return;
  }

  // Validate file format
  if (!validateFileFormat(file, 'test_submission')) {
    const allowedFormats = llmConfig?.file_formats?.test_submissions || ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png'];
    showError(`Invalid file format. Allowed formats: ${allowedFormats.join(', ')}`);
    return;
  }

  // Validate file size
  if (!validateFileSize(file)) {
    const maxSize = llmConfig?.limits?.max_file_size_mb || 50;
    showError(`File size too large. Maximum allowed size: ${maxSize}MB. Your file: ${getFormattedFileSize(file.size)}`);
    return;
  }

  // Validate expected score if provided
  if (expectedScore && (isNaN(expectedScore) || expectedScore < 0 || expectedScore > 100)) {
    showError('Expected score must be a number between 0 and 100');
    expectedScoreElement.focus();
    return;
  }

  const formData = new FormData();
  formData.append('name', name);
  formData.append('expected_score', expectedScore);
  formData.append('file', file);
  formData.append('csrf_token', getCSRFToken());

  showLoading();
  
  fetch('/llm-training/api/test-submissions/upload', {
    method: 'POST',
    body: formData
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    hideLoading();
    if (data.success) {
      hideUploadTestSubmissionModal();
      loadTestSubmissions();
      showSuccess('Test submission uploaded successfully');
    } else {
      showError(data.error || 'Failed to upload test submission');
    }
  })
  .catch(error => {
    hideLoading();
    console.error('Upload error:', error);
    showError('Error uploading test submission: ' + error.message);
  });
}

function generateReport() {
  showLoading();
  
  // First, get all training jobs to include in the report
  fetch('/llm-training/api/training-jobs')
    .then(response => response.json())
    .then(jobsData => {
      if (!jobsData.success || !jobsData.jobs || jobsData.jobs.length === 0) {
        throw new Error('No training jobs found to generate report');
      }

      // Get all job IDs
      const jobIds = jobsData.jobs.map(job => job.id);

      // Generate report with all available jobs
      return fetch('/llm-training/api/reports', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
          job_ids: jobIds,
          format: 'html',
          include_metrics: true,
          include_logs: false,
          csrf_token: getCSRFToken()
        })
      });
    })
    .then(response => response.json())
    .then(data => {
      hideLoading();
      if (data.success) {
        loadReports();
        showSuccess('Report generated successfully');
      } else {
        showError(data.error || 'Failed to generate report');
      }
    })
    .catch(error => {
      hideLoading();
      showError('Error generating report: ' + error.message);
    });
}

// Load functions
function loadTrainingGuides() {
  fetch('/llm-training/api/training-guides')
    .then(response => response.json())
    .then(data => {
      const container = document.getElementById('training-guides-list');
      container.innerHTML = '';
      
      // Update button state based on training guides
      buttonStates.hasTrainingGuides = data.guides && data.guides.length > 0;
      
      if (data.guides && data.guides.length > 0) {
        data.guides.forEach(guide => {
          const item = document.createElement('div');
          item.className = 'p-3 bg-gray-50 rounded-lg border text-sm mb-2';
          
          // File size info
          let sizeInfo = '';
          if (guide.word_count) {
            sizeInfo = `<div class="text-xs text-gray-500 mt-1">${guide.word_count} words</div>`;
          }
          
          item.innerHTML = `
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <div class="font-medium text-gray-900">${guide.name}</div>
                <div class="text-gray-600 text-xs mt-1">${guide.description || 'No description'}</div>
                ${sizeInfo}
              </div>
              <button onclick="deleteTrainingGuide('${guide.id}')" 
                      class="ml-2 px-2 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700"
                      title="Delete training guide">
                Delete
              </button>
            </div>
          `;
          container.appendChild(item);
        });
      } else {
        container.innerHTML = '<p class="text-gray-500 text-sm">No training guides uploaded yet</p>';
      }
      
      // Update button states after loading
      updateButtonStates();
    })
    .catch(error => {
      console.error('Error loading training guides:', error);
      buttonStates.hasTrainingGuides = false;
      updateButtonStates();
    });
}

function loadTrainingJobs() {
  fetch('/llm-training/api/training-jobs')
    .then(response => response.json())
    .then(data => {
      const container = document.getElementById('training-jobs-list');
      container.innerHTML = '';
      
      // Update button states based on training jobs
      buttonStates.hasCompletedTrainingJob = false;
      buttonStates.isTrainingInProgress = false;
      
      if (data.jobs && data.jobs.length > 0) {
        // Check for completed training jobs and training in progress
        data.jobs.forEach(job => {
          if (job.status === 'completed') {
            buttonStates.hasCompletedTrainingJob = true;
          }
          if (job.status === 'training') {
            buttonStates.isTrainingInProgress = true;
          }
        });
        
        // Render job items
        data.jobs.forEach(job => {
          const item = document.createElement('div');
          item.className = 'p-3 bg-gray-50 rounded-lg border text-sm mb-2';
          
          // Status badge color
          let statusColor = 'bg-gray-500';
          let statusText = job.status;
          
          switch(job.status) {
            case 'pending':
              statusColor = 'bg-yellow-500';
              statusText = 'Pending';
              break;
            case 'training':
              statusColor = 'bg-blue-500';
              statusText = 'Training';
              break;
            case 'completed':
              statusColor = 'bg-green-500';
              statusText = 'Completed';
              break;
            case 'failed':
              statusColor = 'bg-red-500';
              statusText = 'Failed';
              break;
            case 'cancelled':
              statusColor = 'bg-gray-500';
              statusText = 'Cancelled';
              break;
          }
          
          // Progress bar for training jobs
          let progressBar = '';
          if (job.status === 'training' && job.progress) {
            const progress = Math.round(job.progress * 100);
            progressBar = `
              <div class="mt-2">
                <div class="flex justify-between text-xs text-gray-600 mb-1">
                  <span>Progress</span>
                  <span>${progress}%</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                  <div class="bg-blue-600 h-2 rounded-full" style="width: ${progress}%"></div>
                </div>
              </div>
            `;
          }
          
          // Action buttons
          let actionButtons = '';
          if (job.status === 'pending' || job.status === 'failed') {
            actionButtons = `
              <div class="mt-2 flex space-x-2">
                <button onclick="startTrainingJob('${job.id}')" 
                        class="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700">
                  Start Training
                </button>
                <button onclick="deleteTrainingJob('${job.id}')" 
                        class="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700">
                  Delete
                </button>
              </div>
            `;
          } else if (job.status === 'preparing') {
            actionButtons = `
              <div class="mt-2 flex space-x-2">
                <button onclick="cancelTrainingJob('${job.id}')" 
                        class="px-3 py-1 bg-orange-600 text-white text-xs rounded hover:bg-orange-700">
                  Cancel
                </button>
                <button onclick="deleteTrainingJob('${job.id}')" 
                        class="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700">
                  Delete
                </button>
              </div>
            `;
          } else if (job.status === 'training') {
            actionButtons = `
              <button onclick="cancelTrainingJob('${job.id}')" 
                      class="mt-2 px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700">
                Cancel Training
              </button>
            `;
          } else if (job.status === 'completed' || job.status === 'cancelled') {
            actionButtons = `
              <button onclick="deleteTrainingJob('${job.id}')" 
                      class="mt-2 px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700">
                Delete
              </button>
            `;
          }
          
          // Training details
          let details = '';
          if (job.model_id) {
            details += `<div class="text-xs text-gray-500 mt-1">Model: ${job.model_id}</div>`;
          }
          if (job.created_at) {
            const createdDate = new Date(job.created_at).toLocaleDateString();
            details += `<div class="text-xs text-gray-500">Created: ${createdDate}</div>`;
          }
          
          item.innerHTML = `
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <div class="font-medium text-gray-900">${job.name}</div>
                <div class="flex items-center mt-1">
                  <span class="inline-block w-2 h-2 rounded-full ${statusColor} mr-2"></span>
                  <span class="text-gray-600">${statusText}</span>
                </div>
                ${details}
                ${progressBar}
                ${actionButtons}
              </div>
            </div>
          `;
          
          container.appendChild(item);
        });
      } else {
        container.innerHTML = '<p class="text-gray-500 text-sm">No training jobs created yet</p>';
      }
    })
    .catch(error => console.error('Error loading training jobs:', error));
}

function loadTestSubmissions() {
  fetch('/llm-training/api/test-submissions')
    .then(response => response.json())
    .then(data => {
      const container = document.getElementById('test-submissions-list');
      container.innerHTML = '';
      
      // Update button state based on test submissions
      buttonStates.hasTestSubmissions = data.submissions && data.submissions.length > 0;
      
      if (data.submissions && data.submissions.length > 0) {
        data.submissions.forEach(submission => {
          const item = document.createElement('div');
          item.className = 'p-3 bg-gray-50 rounded-lg border text-sm mb-2';
          
          item.innerHTML = `
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <div class="font-medium text-gray-900">${submission.name}</div>
                <div class="text-gray-600 text-xs mt-1">Expected Score: ${submission.expected_score || 'N/A'}</div>
              </div>
              <button onclick="deleteTestSubmission('${submission.id}')" 
                      class="ml-2 px-2 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700"
                      title="Delete test submission">
                Delete
              </button>
            </div>
          `;
          container.appendChild(item);
        });
      } else {
        container.innerHTML = '<p class="text-gray-500 text-sm">No test submissions uploaded yet</p>';
      }
    })
    .catch(error => console.error('Error loading test submissions:', error));
}

function loadReports() {
  fetch('/llm-training/api/reports')
    .then(response => response.json())
    .then(data => {
      const container = document.getElementById('reports-list');
      container.innerHTML = '';
      
      if (data.reports && data.reports.length > 0) {
        data.reports.forEach(report => {
          const item = document.createElement('div');
          item.className = 'p-3 bg-gray-50 rounded-lg border text-sm mb-2';
          
          // Format the date
          let generatedDate = 'Unknown';
          if (report.created_at) {
            try {
              generatedDate = new Date(report.created_at).toLocaleDateString();
            } catch (e) {
              generatedDate = report.created_at;
            }
          }
          
          // Status indicator
          let statusBadge = '';
          if (report.status) {
            let statusColor = 'bg-gray-500';
            let statusText = report.status;
            
            switch(report.status) {
              case 'generating':
                statusColor = 'bg-yellow-500';
                statusText = 'Generating';
                break;
              case 'completed':
                statusColor = 'bg-green-500';
                statusText = 'Completed';
                break;
              case 'failed':
                statusColor = 'bg-red-500';
                statusText = 'Failed';
                break;
            }
            
            statusBadge = `
              <div class="flex items-center mt-1">
                <span class="inline-block w-2 h-2 rounded-full ${statusColor} mr-2"></span>
                <span class="text-gray-600 text-xs">${statusText}</span>
              </div>
            `;
          }
          
          // Action buttons
          let actionButtons = '';
          if (report.status === 'completed') {
            actionButtons = `
              <div class="mt-2 flex space-x-2">
                <button onclick="downloadReport('${report.id}')" 
                        class="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">
                  Download
                </button>
                <button onclick="deleteReport('${report.id}')" 
                        class="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700">
                  Delete
                </button>
              </div>
            `;
          } else if (report.status === 'generating') {
            actionButtons = `
              <button onclick="deleteReport('${report.id}')" 
                      class="mt-2 px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700"
                      title="Delete generating report">
                Delete
              </button>
            `;
          } else if (report.status === 'failed') {
            actionButtons = `
              <button onclick="deleteReport('${report.id}')" 
                      class="mt-2 px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700">
                Delete
              </button>
            `;
          }
          
          item.innerHTML = `
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <div class="font-medium text-gray-900">${report.name}</div>
                <div class="text-gray-600 text-xs mt-1">Generated: ${generatedDate}</div>
                ${statusBadge}
                ${actionButtons}
              </div>
            </div>
          `;
          container.appendChild(item);
        });
      } else {
        container.innerHTML = '<p class="text-gray-500 text-sm">No reports generated yet</p>';
      }
    })
    .catch(error => console.error('Error loading reports:', error));
}

function loadTrainingGuidesForJob() {
  fetch('/llm-training/api/training-guides')
    .then(response => response.json())
    .then(data => {
      const select = document.getElementById('training-job-guide');
      select.innerHTML = '<option value="">Select training guide...</option>';
      
      if (data.guides && data.guides.length > 0) {
        data.guides.forEach(guide => {
          const option = document.createElement('option');
          option.value = guide.id;
          option.textContent = guide.name;
          select.appendChild(option);
        });
      }
    })
    .catch(error => console.error('Error loading training guides for job:', error));
}

// Configuration loading function
async function loadConfiguration() {
  try {
    const response = await fetch('/llm-training/api/config');
    const data = await response.json();
    
    if (data.success) {
      llmConfig = data.config;
      populateModelOptions();
      updateFileFormatValidation();
      return llmConfig;
    } else {
      throw new Error(data.error || 'Failed to load configuration');
    }
  } catch (error) {
    console.error('Error loading configuration:', error);
    throw error;
  }
}

function populateModelOptions() {
  if (!llmConfig || !llmConfig.models) return;
  
  const modelSelect = document.getElementById('training-job-model');
  if (!modelSelect) return;
  
  // Clear existing options except the first placeholder
  modelSelect.innerHTML = '<option value="">Select model...</option>';
  
  // Add dynamic model options
  llmConfig.models.forEach(model => {
    const option = document.createElement('option');
    option.value = model.id;
    option.textContent = model.name;
    option.setAttribute('data-provider', model.provider);
    modelSelect.appendChild(option);
  });
}

function updateFileFormatValidation() {
  if (!llmConfig || !llmConfig.file_formats) return;
  
  // Update training guide file input
  const trainingGuideInput = document.getElementById('training-guide-file');
  if (trainingGuideInput && llmConfig.file_formats.training_guides) {
    trainingGuideInput.setAttribute('accept', llmConfig.file_formats.training_guides.join(','));
  }
  
  // Update test submission file input
  const testSubmissionInput = document.getElementById('test-submission-file');
  if (testSubmissionInput && llmConfig.file_formats.test_submissions) {
    testSubmissionInput.setAttribute('accept', llmConfig.file_formats.test_submissions.join(','));
  }
}

function validateFileFormat(file, type) {
  if (!llmConfig || !llmConfig.file_formats) return true;
  
  const allowedFormats = type === 'training_guide' 
    ? llmConfig.file_formats.training_guides 
    : llmConfig.file_formats.test_submissions;
  
  if (!allowedFormats) return true;
  
  const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
  return allowedFormats.includes(fileExtension);
}

function validateFileSize(file) {
  if (!llmConfig || !llmConfig.limits) return true;
  
  const maxSizeMB = llmConfig.limits.max_file_size_mb || 50;
  const maxSizeBytes = maxSizeMB * 1024 * 1024;
  
  return file.size <= maxSizeBytes;
}

function getFormattedFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Utility functions
function showLoading() {
  document.getElementById('loading-overlay').classList.remove('hidden');
  document.getElementById('loading-overlay').classList.add('flex');
}

function hideLoading() {
  document.getElementById('loading-overlay').classList.add('hidden');
  document.getElementById('loading-overlay').classList.remove('flex');
}

function showSuccess(message) {
  // Simple alert for now - could be replaced with a toast notification
  alert(message);
}

function showError(message) {
  // Simple alert for now - could be replaced with a toast notification
  alert('Error: ' + message);
}

// Training job control functions
function startTrainingJob(jobId) {
  if (!confirm('Are you sure you want to start this training job?')) {
    return;
  }

  showLoading();
  
  fetch(`/llm-training/api/training-jobs/${jobId}/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify({
      csrf_token: getCSRFToken()
    })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    hideLoading();
    if (data.success) {
      showSuccess('Training job started successfully');
      loadTrainingJobs(); // Refresh the list
    } else {
      showError(data.error || 'Failed to start training job');
    }
  })
  .catch(error => {
    hideLoading();
    console.error('Start training error:', error);
    showError('Error starting training job: ' + error.message);
  });
}

function cancelTrainingJob(jobId) {
  if (!confirm('Are you sure you want to cancel this training job?')) {
    return;
  }

  showLoading();
  
  fetch(`/llm-training/api/training-jobs/${jobId}/cancel`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify({
      csrf_token: getCSRFToken()
    })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    hideLoading();
    if (data.success) {
      showSuccess('Training job cancelled successfully');
      loadTrainingJobs(); // Refresh the list
    } else {
      showError(data.error || 'Failed to cancel training job');
    }
  })
  .catch(error => {
    hideLoading();
    console.error('Cancel training error:', error);
    showError('Error cancelling training job: ' + error.message);
  });
}

// Auto-refresh functionality for real-time updates
let autoRefreshInterval = null;

function startAutoRefresh() {
  // Refresh every 5 seconds
  autoRefreshInterval = setInterval(() => {
    loadTrainingJobs();
  }, 5000);
}

function stopAutoRefresh() {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
  }
}

// Start auto-refresh when page loads
document.addEventListener('DOMContentLoaded', function() {
  // Start auto-refresh after initial load
  setTimeout(() => {
    startAutoRefresh();
  }, 2000);
});

// Stop auto-refresh when page is hidden (to save resources)
document.addEventListener('visibilitychange', function() {
  if (document.hidden) {
    stopAutoRefresh();
  } else {
    startAutoRefresh();
  }
});

// Delete functions for all items
function deleteTrainingGuide(guideId) {
  if (!confirm('Are you sure you want to delete this training guide? This action cannot be undone.')) {
    return;
  }

  showLoading();
  
  fetch(`/llm-training/api/training-guides/${guideId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    }
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    hideLoading();
    if (data.success) {
      showSuccess('Training guide deleted successfully');
      loadTrainingGuides(); // Refresh the list
    } else {
      showError(data.error || 'Failed to delete training guide');
    }
  })
  .catch(error => {
    hideLoading();
    console.error('Delete training guide error:', error);
    showError('Error deleting training guide: ' + error.message);
  });
}

function deleteTrainingJob(jobId) {
  if (!confirm('Are you sure you want to delete this training job? This action cannot be undone.')) {
    return;
  }

  showLoading();
  
  fetch(`/llm-training/api/training-jobs/${jobId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    }
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    hideLoading();
    if (data.success) {
      showSuccess('Training job deleted successfully');
      loadTrainingJobs(); // Refresh the list
    } else {
      showError(data.error || 'Failed to delete training job');
    }
  })
  .catch(error => {
    hideLoading();
    console.error('Delete training job error:', error);
    showError('Error deleting training job: ' + error.message);
  });
}

function deleteTestSubmission(submissionId) {
  if (!confirm('Are you sure you want to delete this test submission? This action cannot be undone.')) {
    return;
  }

  showLoading();
  
  fetch(`/llm-training/api/test-submissions/${submissionId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    }
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    hideLoading();
    if (data.success) {
      showSuccess('Test submission deleted successfully');
      loadTestSubmissions(); // Refresh the list
    } else {
      showError(data.error || 'Failed to delete test submission');
    }
  })
  .catch(error => {
    hideLoading();
    console.error('Delete test submission error:', error);
    showError('Error deleting test submission: ' + error.message);
  });
}

function deleteReport(reportId) {
  if (!confirm('Are you sure you want to delete this report? This action cannot be undone.')) {
    return;
  }

  showLoading();
  
  fetch(`/llm-training/api/reports/${reportId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    }
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    hideLoading();
    if (data.success) {
      showSuccess('Report deleted successfully');
      loadReports(); // Refresh the list
    } else {
      showError(data.error || 'Failed to delete report');
    }
  })
  .catch(error => {
    hideLoading();
    console.error('Delete report error:', error);
    showError('Error deleting report: ' + error.message);
  });
}

// Download report function
function downloadReport(reportId) {
  showLoading();
  
  fetch(`/llm-training/api/reports/${reportId}/download`, {
    method: 'GET',
    headers: {
      'X-CSRFToken': getCSRFToken()
    }
  })
  .then(response => {
    hideLoading();
    if (response.ok) {
      // Create a blob from the response and trigger download
      return response.blob().then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `training_report_${reportId}.html`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showSuccess('Report downloaded successfully');
      });
    } else {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  })
  .catch(error => {
    hideLoading();
    console.error('Download report error:', error);
    showError('Error downloading report: ' + error.message);
  });
}

// Complete the loadTrainingJobs function by adding button state updates
function completeLoadTrainingJobs() {
  // This function ensures button states are updated after loading training jobs
  updateButtonStates();
}

// Add missing utility functions for button state management
function showError(message) {
  // Create or update error message display
  const errorContainer = document.getElementById('error-messages') || createErrorContainer();
  const errorDiv = document.createElement('div');
  errorDiv.className = 'bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4';
  errorDiv.innerHTML = `
    <div class="flex">
      <div class="flex-shrink-0">
        <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
        </svg>
      </div>
      <div class="ml-3">
        <p class="text-sm font-medium">${message}</p>
      </div>
      <div class="ml-auto pl-3">
        <button type="button" class="inline-flex text-red-400 hover:text-red-600" onclick="this.parentElement.parentElement.parentElement.remove()">
          <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
          </svg>
        </button>
      </div>
    </div>
  `;
  errorContainer.appendChild(errorDiv);
  
  // Auto-remove after 5 seconds
  setTimeout(() => {
    if (errorDiv.parentNode) {
      errorDiv.remove();
    }
  }, 5000);
}

function showSuccess(message) {
  // Create or update success message display
  const successContainer = document.getElementById('success-messages') || createSuccessContainer();
  const successDiv = document.createElement('div');
  successDiv.className = 'bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded mb-4';
  successDiv.innerHTML = `
    <div class="flex">
      <div class="flex-shrink-0">
        <svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
        </svg>
      </div>
      <div class="ml-3">
        <p class="text-sm font-medium">${message}</p>
      </div>
      <div class="ml-auto pl-3">
        <button type="button" class="inline-flex text-green-400 hover:text-green-600" onclick="this.parentElement.parentElement.parentElement.remove()">
          <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
          </svg>
        </button>
      </div>
    </div>
  `;
  successContainer.appendChild(successDiv);
  
  // Auto-remove after 3 seconds
  setTimeout(() => {
    if (successDiv.parentNode) {
      successDiv.remove();
    }
  }, 3000);
}

function createErrorContainer() {
  const container = document.createElement('div');
  container.id = 'error-messages';
  container.className = 'fixed top-4 right-4 z-50 max-w-md';
  document.body.appendChild(container);
  return container;
}

function createSuccessContainer() {
  const container = document.createElement('div');
  container.id = 'success-messages';
  container.className = 'fixed top-4 right-4 z-50 max-w-md';
  document.body.appendChild(container);
  return container;
}

function showLoading() {
  const overlay = document.getElementById('loading-overlay');
  if (overlay) {
    overlay.classList.remove('hidden');
    overlay.classList.add('flex');
  }
}

function hideLoading() {
  const overlay = document.getElementById('loading-overlay');
  if (overlay) {
    overlay.classList.add('hidden');
    overlay.classList.remove('flex');
  }
}

// Training job management functions with button state updates
function startTrainingJob(jobId) {
  if (!jobId) {
    showError('Invalid job ID');
    return;
  }
  
  showLoading();
  
  fetch(`/llm-training/api/training-jobs/${jobId}/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify({
      csrf_token: getCSRFToken()
    })
  })
  .then(response => response.json())
  .then(data => {
    hideLoading();
    if (data.success) {
      showSuccess('Training job started successfully');
      loadTrainingJobs(); // This will update button states
    } else {
      showError(data.error || 'Failed to start training job');
    }
  })
  .catch(error => {
    hideLoading();
    showError('Error starting training job: ' + error.message);
  });
}

function cancelTrainingJob(jobId) {
  if (!jobId) {
    showError('Invalid job ID');
    return;
  }
  
  if (!confirm('Are you sure you want to cancel this training job?')) {
    return;
  }
  
  showLoading();
  
  fetch(`/llm-training/api/training-jobs/${jobId}/cancel`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify({
      csrf_token: getCSRFToken()
    })
  })
  .then(response => response.json())
  .then(data => {
    hideLoading();
    if (data.success) {
      showSuccess('Training job cancelled successfully');
      loadTrainingJobs(); // This will update button states
    } else {
      showError(data.error || 'Failed to cancel training job');
    }
  })
  .catch(error => {
    hideLoading();
    showError('Error cancelling training job: ' + error.message);
  });
}

function deleteTrainingJob(jobId) {
  if (!jobId) {
    showError('Invalid job ID');
    return;
  }
  
  if (!confirm('Are you sure you want to delete this training job? This action cannot be undone.')) {
    return;
  }
  
  showLoading();
  
  fetch(`/llm-training/api/training-jobs/${jobId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify({
      csrf_token: getCSRFToken()
    })
  })
  .then(response => response.json())
  .then(data => {
    hideLoading();
    if (data.success) {
      showSuccess('Training job deleted successfully');
      loadTrainingJobs(); // This will update button states
    } else {
      showError(data.error || 'Failed to delete training job');
    }
  })
  .catch(error => {
    hideLoading();
    showError('Error deleting training job: ' + error.message);
  });
}

function deleteTrainingGuide(guideId) {
  if (!guideId) {
    showError('Invalid guide ID');
    return;
  }
  
  if (!confirm('Are you sure you want to delete this training guide? This action cannot be undone.')) {
    return;
  }
  
  showLoading();
  
  fetch(`/llm-training/api/training-guides/${guideId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify({
      csrf_token: getCSRFToken()
    })
  })
  .then(response => response.json())
  .then(data => {
    hideLoading();
    if (data.success) {
      showSuccess('Training guide deleted successfully');
      loadTrainingGuides(); // This will update button states
    } else {
      showError(data.error || 'Failed to delete training guide');
    }
  })
  .catch(error => {
    hideLoading();
    showError('Error deleting training guide: ' + error.message);
  });
}

function deleteTestSubmission(submissionId) {
  if (!submissionId) {
    showError('Invalid submission ID');
    return;
  }
  
  if (!confirm('Are you sure you want to delete this test submission? This action cannot be undone.')) {
    return;
  }
  
  showLoading();
  
  fetch(`/llm-training/api/test-submissions/${submissionId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify({
      csrf_token: getCSRFToken()
    })
  })
  .then(response => response.json())
  .then(data => {
    hideLoading();
    if (data.success) {
      showSuccess('Test submission deleted successfully');
      loadTestSubmissions(); // This will update button states
    } else {
      showError(data.error || 'Failed to delete test submission');
    }
  })
  .catch(error => {
    hideLoading();
    showError('Error deleting test submission: ' + error.message);
  });
}

// File validation functions
function validateFileFormat(file, type) {
  if (!llmConfig || !llmConfig.file_formats) return true;
  
  const allowedFormats = type === 'training_guide' 
    ? llmConfig.file_formats.training_guides 
    : llmConfig.file_formats.test_submissions;
    
  if (!allowedFormats) return true;
  
  const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
  return allowedFormats.includes(fileExtension);
}

function validateFileSize(file) {
  if (!llmConfig || !llmConfig.limits) return true;
  
  const maxSizeBytes = (llmConfig.limits.max_file_size_mb || 50) * 1024 * 1024;
  return file.size <= maxSizeBytes;
}

function getFormattedFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Auto-refresh training jobs to update progress and button states
function startAutoRefresh() {
  setInterval(() => {
    // Only refresh if there are training jobs in progress
    if (buttonStates.isTrainingInProgress) {
      loadTrainingJobs();
    }
  }, 5000); // Refresh every 5 seconds
}

// Start auto-refresh when page loads
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(startAutoRefresh, 2000); // Start after initial load
});

// Step indicator management functions
function updateStepIndicators() {
  // Step 1: Upload Training Guide
  const step1 = document.getElementById('step-1-indicator');
  if (step1) {
    if (buttonStates.hasTrainingGuides) {
      step1.classList.remove('disabled');
      step1.classList.add('completed');
      step1.style.backgroundColor = '#10b981'; // green
    } else {
      step1.classList.remove('completed', 'in-progress');
      step1.classList.add('disabled');
      step1.style.backgroundColor = '#3b82f6'; // blue (current step)
    }
  }

  // Step 2: Create Training Job
  const step2 = document.getElementById('step-2-indicator');
  if (step2) {
    if (buttonStates.hasCompletedTrainingJob) {
      step2.classList.remove('disabled', 'in-progress');
      step2.classList.add('completed');
      step2.style.backgroundColor = '#10b981'; // green
    } else if (buttonStates.isTrainingInProgress) {
      step2.classList.remove('disabled', 'completed');
      step2.classList.add('in-progress');
      step2.style.backgroundColor = '#f59e0b'; // yellow
    } else if (buttonStates.hasTrainingGuides) {
      step2.classList.remove('completed', 'in-progress');
      step2.classList.add('disabled');
      step2.style.backgroundColor = '#8b5cf6'; // purple (available)
    } else {
      step2.classList.remove('completed', 'in-progress');
      step2.classList.add('disabled');
      step2.style.backgroundColor = '#9ca3af'; // gray (disabled)
    }
  }

  // Step 3: Upload Test Submission
  const step3 = document.getElementById('step-3-indicator');
  if (step3) {
    if (buttonStates.hasTestSubmissions) {
      step3.classList.remove('disabled');
      step3.classList.add('completed');
      step3.style.backgroundColor = '#10b981'; // green
    } else if (buttonStates.hasCompletedTrainingJob) {
      step3.classList.remove('completed');
      step3.classList.add('disabled');
      step3.style.backgroundColor = '#059669'; // green (available)
    } else {
      step3.classList.remove('completed');
      step3.classList.add('disabled');
      step3.style.backgroundColor = '#9ca3af'; // gray (disabled)
    }
  }

  // Step 4: Generate Report
  const step4 = document.getElementById('step-4-indicator');
  if (step4) {
    if (buttonStates.hasTestSubmissions && buttonStates.hasCompletedTrainingJob) {
      step4.classList.remove('disabled');
      step4.classList.add('completed');
      step4.style.backgroundColor = '#ea580c'; // orange (available)
    } else {
      step4.classList.remove('completed');
      step4.classList.add('disabled');
      step4.style.backgroundColor = '#9ca3af'; // gray (disabled)
    }
  }
}

// Enhanced auto-refresh with step indicator updates
function startAutoRefresh() {
  setInterval(() => {
    // Only refresh if there are training jobs in progress
    if (buttonStates.isTrainingInProgress) {
      loadTrainingJobs();
    }
  }, 5000); // Refresh every 5 seconds
}

// Ensure button states are updated after all load functions complete
function completeLoadTrainingJobs() {
  // This function ensures button states are updated after loading training jobs
  updateButtonStates();
}

// Update the loadTrainingJobs function to call updateButtonStates at the end
function enhanceLoadTrainingJobs() {
  // Add updateButtonStates call to the end of loadTrainingJobs
  const originalLoadTrainingJobs = loadTrainingJobs;
  loadTrainingJobs = function() {
    originalLoadTrainingJobs.call(this);
    // Add a small delay to ensure DOM updates are complete
    setTimeout(() => {
      updateButtonStates();
    }, 100);
  };
}

// Update the loadTestSubmissions function to call updateButtonStates at the end
function enhanceLoadTestSubmissions() {
  const originalLoadTestSubmissions = loadTestSubmissions;
  loadTestSubmissions = function() {
    originalLoadTestSubmissions.call(this);
    // Add a small delay to ensure DOM updates are complete
    setTimeout(() => {
      updateButtonStates();
    }, 100);
  };
}

// Initialize enhancements when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  // Enhance load functions to update button states
  enhanceLoadTrainingJobs();
  enhanceLoadTestSubmissions();
  
  // Start auto-refresh after initial load
  setTimeout(startAutoRefresh, 2000);
});

// Add visual feedback for button interactions
function addButtonFeedback() {
  const buttons = document.querySelectorAll('.training-step-button');
  
  buttons.forEach(button => {
    button.addEventListener('mouseenter', function() {
      if (!this.disabled) {
        this.style.transform = 'translateY(-1px)';
        this.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.1)';
      }
    });
    
    button.addEventListener('mouseleave', function() {
      if (!this.disabled) {
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = '';
      }
    });
    
    button.addEventListener('click', function() {
      if (!this.disabled) {
        this.style.transform = 'translateY(1px)';
        setTimeout(() => {
          if (!this.disabled) {
            this.style.transform = 'translateY(0)';
          }
        }, 150);
      }
    });
  });
}

// Initialize button feedback when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(addButtonFeedback, 500);
});

// Add tooltip functionality for disabled buttons
function addTooltips() {
  const buttons = document.querySelectorAll('.training-step-button');
  
  buttons.forEach(button => {
    button.addEventListener('mouseenter', function() {
      if (this.disabled && this.title) {
        showTooltip(this, this.title);
      }
    });
    
    button.addEventListener('mouseleave', function() {
      hideTooltip();
    });
  });
}

function showTooltip(element, text) {
  const tooltip = document.createElement('div');
  tooltip.id = 'button-tooltip';
  tooltip.className = 'absolute z-50 px-2 py-1 text-xs text-white bg-gray-800 rounded shadow-lg';
  tooltip.textContent = text;
  
  const rect = element.getBoundingClientRect();
  tooltip.style.left = rect.left + (rect.width / 2) + 'px';
  tooltip.style.top = (rect.top - 30) + 'px';
  tooltip.style.transform = 'translateX(-50%)';
  
  document.body.appendChild(tooltip);
}

function hideTooltip() {
  const tooltip = document.getElementById('button-tooltip');
  if (tooltip) {
    tooltip.remove();
  }
}

// Initialize tooltips when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(addTooltips, 500);
});