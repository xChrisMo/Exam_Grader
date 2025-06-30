/**
 * Exam Grader Application JavaScript
 * Common functionality and utilities
 */

// Application namespace
const ExamGrader = {
  // Configuration
  config: {
    maxFileSize: 16 * 1024 * 1024, // 16MB
    allowedFileTypes: [
      ".pdf",
      ".docx",
      ".doc",
      ".jpg",
      ".jpeg",
      ".png",
      ".tiff",
      ".bmp",
      ".gif",
    ],
    apiEndpoints: {
      processMapping: "/api/process-mapping",
      processGrading: "/api/process-grading",
    },
  },

  // Notification Manager
  notificationManager: {
    // Get user's notification level preference
    getNotificationLevel: function() {
      // Try to get from localStorage first
      const storedLevel = localStorage.getItem('notification_level');
      if (storedLevel) {
        return storedLevel;
      }
      
      // Try to get from DOM if available
      const levelSelect = document.getElementById('notification_level');
      if (levelSelect && levelSelect.value) {
        return levelSelect.value;
      }
      
      // Default to 'all' if not found
      return 'all';
    },
    
    // Check if notification should be shown based on type and user preference
    shouldShowNotification: function(type) {
      const level = this.getNotificationLevel();
      
      switch (level) {
        case 'none':
          return false;
        case 'errors':
          return type === 'error';
        case 'important':
          return type === 'error' || type === 'warning';
        case 'all':
        default:
          return true;
      }
    },
    
    // Show notification if it meets the user's preference criteria
    notify: function(message, type = 'info', duration = 5000) {
      if (!this.shouldShowNotification(type)) {
        console.log(`Notification suppressed (level: ${this.getNotificationLevel()}): ${type} - ${message}`);
        return;
      }
      
      ExamGrader.utils.showToast(message, type, duration);
    }
  },

  // Utility functions
  utils: {
    /**
     * Format file size in human readable format
     */
    formatFileSize: function (bytes) {
      if (bytes === 0) return "0 Bytes";
      const k = 1024;
      const sizes = ["Bytes", "KB", "MB", "GB"];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    },

    /**
     * Check if file type is allowed
     */
    isAllowedFileType: function (filename) {
      if (!filename) return false;
      const ext = "." + filename.split(".").pop().toLowerCase();
      return ExamGrader.config.allowedFileTypes.includes(ext);
    },

    /**
     * Show toast notification
     */
    showToast: function (message, type = "info", duration = 5000) {
      const toast = document.createElement("div");
      toast.className = `fixed top-4 right-4 z-50 max-w-sm bg-white border-l-4 rounded-lg shadow-lg p-4 animate-slide-up ${
        type === "error"
          ? "border-red-500 bg-red-50"
          : type === "success"
          ? "border-green-500 bg-green-50"
          : type === "warning"
          ? "border-yellow-500 bg-yellow-50"
          : "border-blue-500 bg-blue-50"
      }`;

      toast.innerHTML = `
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        ${
                          type === "error"
                            ? '<svg class="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>'
                            : type === "success"
                            ? '<svg class="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>'
                            : type === "warning"
                            ? '<svg class="h-5 w-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>'
                            : '<svg class="h-5 w-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>'
                        }
                    </div>
                    <div class="ml-3">
                        <p class="text-sm font-medium ${
                          type === "error"
                            ? "text-red-800"
                            : type === "success"
                            ? "text-green-800"
                            : type === "warning"
                            ? "text-yellow-800"
                            : "text-blue-800"
                        }">${message}</p>
                    </div>
                    <div class="ml-auto pl-3">
                        <button type="button" class="inline-flex rounded-md p-1.5 ${
                          type === "error"
                            ? "text-red-500 hover:bg-red-100"
                            : type === "success"
                            ? "text-green-500 hover:bg-green-100"
                            : type === "warning"
                            ? "text-yellow-500 hover:bg-yellow-100"
                            : "text-blue-500 hover:bg-blue-100"
                        } focus:outline-none" onclick="this.parentElement.parentElement.parentElement.remove()">
                            <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                            </svg>
                        </button>
                    </div>
                </div>
            `;

      document.body.appendChild(toast);

      // Auto remove after duration
      setTimeout(() => {
        if (toast.parentNode) {
          toast.style.transition = "opacity 0.3s ease-out";
          toast.style.opacity = "0";
          setTimeout(() => {
            if (toast.parentNode) {
              toast.remove();
            }
          }, 300);
        }
      }, duration);
    },

    /**
     * Show loading spinner on button
     */
    showButtonLoading: function (button, loadingText = "Processing...") {
      if (!button) return;

      button.dataset.originalText = button.innerHTML;
      button.disabled = true;
      button.innerHTML = `
                <svg class="animate-spin mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                ${loadingText}
            `;
    },

    /**
     * Hide loading spinner on button
     */
    hideButtonLoading: function (button) {
      if (!button) return;

      button.disabled = false;
      button.innerHTML = button.dataset.originalText || button.innerHTML;
    },

    /**
     * Make API request with enhanced error handling and security
     */
    apiRequest: async function (url, options = {}) {
      try {
        // Add CSRF token if available - try multiple sources
        let csrfToken = document.querySelector('meta[name=csrf-token]')?.getAttribute('content') ||
                       document.querySelector('input[name=csrf_token]')?.value ||
                       document.querySelector('input[name=csrf-token]')?.value;
                       
        // Log CSRF token status for debugging
        if (!csrfToken) {
          console.warn('CSRF token not found in DOM. This may cause request failures.');
        }

        const defaultHeaders = {
          "Content-Type": "application/json",
        };

        if (csrfToken) {
          defaultHeaders['X-CSRFToken'] = csrfToken;
        }

        const response = await fetch(url, {
          ...options, // Spread all original options first
          method: options.method || 'POST',
          headers: {
            ...defaultHeaders,
            ...options.headers,
          },
          body: options.body ? JSON.stringify(options.body) : undefined,
          credentials: 'same-origin', // Include cookies for CSRF protection
        });

        // Handle different content types
        let data;
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          data = await response.json();
        } else {
          data = { message: await response.text() };
        }

        if (!response.ok) {
          // Enhanced error handling with specific status codes
          let errorMessage = data.error || data.message || `HTTP error! status: ${response.status}`;

          switch (response.status) {
            case 400:
              if (data.error && data.error.toLowerCase().includes('csrf')) {
                errorMessage = 'CSRF token error. Please refresh the page and try again.';
                console.error('CSRF token error detected:', data);
                // Attempt to reload the page after a short delay to get a fresh CSRF token
                setTimeout(() => {
                  window.location.reload();
                }, 3000);
              } else {
                errorMessage = data.error || 'Bad request. Please check your input.';
              }
              break;
            case 401:
              errorMessage = 'Authentication required. Please refresh the page.';
              break;
            case 403:
              errorMessage = 'Access forbidden. You may need to refresh the page.';
              break;
            case 413:
              errorMessage = 'File too large. Please choose a smaller file.';
              break;
            case 429:
              errorMessage = 'Too many requests. Please wait a moment and try again.';
              break;
            case 500:
              errorMessage = 'Server error. Please try again later.';
              break;
          }

          throw new Error(errorMessage);
        }

        return data;
      } catch (error) {
        console.error("API request failed:", error);

        // Log additional context for debugging
        console.error("Request details:", {
          url,
          method: options.method || 'POST',
          timestamp: new Date().toISOString()
        });

        throw error;
      }
    },

    /**
     * Debounce function
     */
    debounce: function (func, wait) {
      let timeout;
      return function executedFunction(...args) {
        const later = () => {
          clearTimeout(timeout);
          func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
      };
    },

    /**
     * Format date for display
     */
    formatDate: function (dateString) {
      if (!dateString) return "Unknown";
      const date = new Date(dateString);
      return date.toLocaleDateString() + " " + date.toLocaleTimeString();
    },
  },

  // File upload functionality
  fileUpload: {
    /**
     * Initialize drag and drop for file upload
     */
    initDragAndDrop: function (dropZone, fileInput, onFileSelect) {
      if (!dropZone || !fileInput) return;

      // Prevent default drag behaviors
      ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
      });

      // Highlight drop zone when item is dragged over it
      ["dragenter", "dragover"].forEach((eventName) => {
        dropZone.addEventListener(eventName, highlight, false);
      });

      ["dragleave", "drop"].forEach((eventName) => {
        dropZone.addEventListener(eventName, unhighlight, false);
      });

      // Handle dropped files
      dropZone.addEventListener("drop", handleDrop, false);

      function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
      }

      function highlight(e) {
        dropZone.classList.add("border-blue-500", "bg-blue-50");
      }

      function unhighlight(e) {
        dropZone.classList.remove("border-blue-500", "bg-blue-50");
      }

      function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
          fileInput.files = files;
          if (onFileSelect) {
            onFileSelect(files[0]);
          }
        }
      }
    },

    /**
     * Validate file before upload
     */
    validateFile: function (file) {
      const errors = [];

      if (!file) {
        errors.push("No file selected");
        return errors;
      }

      // Check file size
      if (file.size > ExamGrader.config.maxFileSize) {
        errors.push(
          `File size exceeds ${ExamGrader.utils.formatFileSize(
            ExamGrader.config.maxFileSize
          )} limit`
        );
      }

      // Check file type
      if (!ExamGrader.utils.isAllowedFileType(file.name)) {
        errors.push("File type not supported");
      }

      return errors;
    },
  },

  // API interactions
  api: {
    /**
     * Process answer mapping
     */
    processMapping: async function () {
      try {
        const data = await ExamGrader.utils.apiRequest(
          ExamGrader.config.apiEndpoints.processMapping,
          {
            method: "POST",
          }
        );

        if (data.success) {
          ExamGrader.notificationManager.notify(
            "Answer mapping completed successfully!",
            "success"
          );
          return true;
        } else {
          throw new Error(data.error || "Mapping failed");
        }
      } catch (error) {
        ExamGrader.notificationManager.notify(`Mapping failed: ${error.message}`, "error");
        return false;
      }
    },

    /**
     * Process grading
     */
    processGrading: async function () {
      try {
        const data = await ExamGrader.utils.apiRequest(
          ExamGrader.config.apiEndpoints.processGrading,
          {
            method: "POST",
          }
        );

        if (data.success) {
          ExamGrader.notificationManager.notify(
            `Grading completed! Score: ${data.score}%`,
            "success"
          );
          return data;
        } else {
          throw new Error(data.error || "Grading failed");
        }
      } catch (error) {
        ExamGrader.notificationManager.notify(`Grading failed: ${error.message}`, "error");
        return false;
      }
    },

    /**
     * Process unified AI grading with real-time progress tracking
     */
    processUnifiedAI: async function () {
      try {
        // Show progress modal
        ExamGrader.ui.showProgressModal();

        const data = await ExamGrader.utils.apiRequest(
          "/api/process-unified-ai",
          {
            method: "POST",
          }
        );

        if (data.success) {
          const summary = data.summary || {};
          const avgPercentage = summary.average_percentage || 0;
          const processingTime = summary.processing_time || 0;

          ExamGrader.notificationManager.notify(
            `Unified AI processing completed! Average score: ${avgPercentage}% (${processingTime}s)`,
            "success"
          );

          // Stop polling and hide progress modal
          ExamGrader.ui.stopProgressPolling();
          ExamGrader.ui.hideProgressModal();

          // Reload the page to update the UI based on server-side session variables
          window.location.reload();

          return data;
        } else {
          throw new Error(data.error || "Unified AI processing failed");
        }
      } catch (error) {
        ExamGrader.ui.hideProgressModal();
        // Stop any ongoing polling if an error occurs
        ExamGrader.ui.stopProgressPolling();
        ExamGrader.notificationManager.notify(`Unified AI processing failed: ${error.message}`, "error");
        return false;
      }
    },

    /**
     * Get progress updates for a progress ID
     */
    getProgress: async function (progressId) {
      try {
        const data = await ExamGrader.utils.apiRequest(
          `/api/progress/${progressId}`,
          { method: "GET" }
        );

        if (data.success) {
          return data.progress;
        } else {
          throw new Error(data.error || "Failed to get progress");
        }
      } catch (error) {
        console.error("Error getting progress:", error);
        return null;
      }
    },

    /**
     * Get progress history for a progress ID
     */
    getProgressHistory: async function (progressId) {
      try {
        const data = await ExamGrader.utils.apiRequest(
          `/api/progress/${progressId}/history`,
          { method: "GET" }
        );

        if (data.success) {
          return data.history;
        } else {
          throw new Error(data.error || "Failed to get progress history");
        }
      } catch (error) {
        console.error("Error getting progress history:", error);
        return null;
      }
    },
  },

  // UI components for progress tracking
  ui: {
    /**
     * Show progress modal with real-time updates
     */
    showProgressModal: function () {
      // Create progress modal if it doesn't exist
      if (!document.getElementById('progress-modal')) {
        const modalHTML = `
          <div id="progress-modal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
              <div class="mt-3 text-center">
                <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-blue-100">
                  <svg class="animate-spin h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
                <h3 class="text-lg leading-6 font-medium text-gray-900 mt-2" id="progress-title">
                  AI Processing in Progress
                </h3>
                <div class="mt-4">
                  <div class="w-full bg-gray-200 rounded-full h-2.5">
                    <div id="progress-bar" class="bg-blue-600 h-2.5 rounded-full transition-all duration-300" style="width: 0%"></div>
                  </div>
                  <p class="text-sm text-gray-500 mt-2" id="progress-text">Initializing...</p>
                  <p class="text-xs text-gray-400 mt-1" id="progress-details"></p>
                  <p class="text-xs text-gray-400 mt-1" id="progress-eta"></p>
                </div>
              </div>
            </div>
          </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
      }

      document.getElementById('progress-modal').style.display = 'block';
    },

    /**
     * Hide progress modal
     */
      hideProgressModal: function () {
        const modal = document.getElementById("progress-modal");
        if (modal) {
          modal.style.display = "none";
        }
      },

      stopProgressPolling: function () {
        if (ExamGrader.progressPollingInterval) {
          clearInterval(ExamGrader.progressPollingInterval);
          ExamGrader.progressPollingInterval = null;
          console.log("Progress polling stopped.");
        }
      },

    /**
     * Update progress modal with current progress
     */
    updateProgress: function (progress) {
      const progressBar = document.getElementById('progress-bar');
      const progressText = document.getElementById('progress-text');
      const progressDetails = document.getElementById('progress-details');
      const progressEta = document.getElementById('progress-eta');

      if (progressBar) {
        progressBar.style.width = `${progress.percentage}%`;
      }

      if (progressText) {
        progressText.textContent = progress.current_operation || 'Processing...';
      }

      if (progressDetails) {
        const details = progress.details ||
          `Step ${progress.current_step}/${progress.total_steps} - Submission ${progress.submission_index}/${progress.total_submissions}`;
        progressDetails.textContent = details;
      }

      if (progressEta && progress.estimated_time_remaining) {
        const eta = Math.round(progress.estimated_time_remaining);
        progressEta.textContent = `Estimated time remaining: ${eta}s`;
      }

      // Update status color based on progress status
      if (progress.status === 'completed') {
        progressBar.classList.remove('bg-blue-600');
        progressBar.classList.add('bg-green-600');
      } else if (progress.status === 'error') {
        progressBar.classList.remove('bg-blue-600');
        progressBar.classList.add('bg-red-600');
      }
    },

    /**
     * Start progress polling for a progress ID
     */
    startProgressPolling: function (progressId) {
      if (ExamGrader.progressPollingInterval) {
        clearInterval(ExamGrader.progressPollingInterval);
      }

      ExamGrader.progressPollingInterval = setInterval(async () => {
        try {
          const progress = await ExamGrader.api.getProgress(progressId);
          ExamGrader.ui.updateProgress(progress);

          if (progress.status === 'completed' || progress.status === 'failed') {
            clearInterval(ExamGrader.progressPollingInterval);
            ExamGrader.progressPollingInterval = null;
            ExamGrader.ui.hideProgressModal();
            if (progress.status === 'completed') {
              ExamGrader.notificationManager.notify('AI processing completed successfully!', 'success');
            } else {
              ExamGrader.notificationManager.notify('AI processing failed: ' + progress.message, 'error');
            }
          }
        } catch (error) {
          console.error('Error polling for progress:', error);
          clearInterval(ExamGrader.progressPollingInterval);
          ExamGrader.progressPollingInterval = null;
          ExamGrader.ui.hideProgressModal();
          ExamGrader.notificationManager.notify('Error during AI processing: ' + error.message, 'error');
        }
      }, 2000); // Poll every 2 seconds
    },

    /**
     * Stop progress polling
     */
    stopProgressPolling: function () {
      if (ExamGrader.ui.progressInterval) {
        clearInterval(ExamGrader.ui.progressInterval);
        ExamGrader.ui.progressInterval = null;
      }
    },
  },

  // Initialize application
  init: function () {
    console.log("Exam Grader Application initialized");

    // Initialize common functionality
    this.initFlashMessages();
    this.initServiceWorker();
    
    // Initialize settings from localStorage
    this.initSettings();

    // Add global error handler
    window.addEventListener("error", function (e) {
      console.error("Global error:", e.error);
      ExamGrader.notificationManager.notify("An unexpected error occurred", "error");
    });

    // Add unhandled promise rejection handler
    window.addEventListener("unhandledrejection", function (e) {
      console.error("Unhandled promise rejection:", e.reason);
      ExamGrader.notificationManager.notify("An unexpected error occurred", "error");
    });
  },
  
  // Initialize settings from localStorage
  initSettings: function() {
    // Get notification level from localStorage
    const storedNotificationLevel = localStorage.getItem('notification_level');
    if (storedNotificationLevel) {
      // Update notification level select if it exists
      const notificationLevelSelect = document.getElementById('notification_level');
      if (notificationLevelSelect) {
        notificationLevelSelect.value = storedNotificationLevel;
      }
    }
  },

  /**
   * Initialize flash message handling
   */
  initFlashMessages: function () {
    // Auto-hide flash messages after 5 seconds
    setTimeout(() => {
      const flashMessages = document.querySelectorAll(".flash-message");
      flashMessages.forEach((message) => {
        message.style.transition = "opacity 0.5s ease-out";
        message.style.opacity = "0";
        setTimeout(() => {
          if (message.parentNode) {
            message.remove();
          }
        }, 500);
      });
    }, 5000);

    // Close button functionality
    document.querySelectorAll(".flash-close").forEach((button) => {
      button.addEventListener("click", function () {
        const message = this.closest(".flash-message");
        if (message) {
          message.style.transition = "opacity 0.3s ease-out";
          message.style.opacity = "0";
          setTimeout(() => {
            if (message.parentNode) {
              message.remove();
            }
          }, 300);
        }
      });
    });
  },

  /**
   * Initialize service worker for offline functionality (if needed)
   */
  initServiceWorker: function () {
    if ("serviceWorker" in navigator) {
      // Service worker registration would go here
      // navigator.serviceWorker.register('/static/js/sw.js');
    }
  },
};

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  ExamGrader.init();
});

// Export for use in other scripts
