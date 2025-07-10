/**
 * Exam Grader Application JavaScript
 * Common functionality and utilities
 */

// Application namespace
var ExamGrader = ExamGrader || {};

// Application namespace
ExamGrader = {

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
    getNotificationLevel: function () {
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
    shouldShowNotification: function (type) {
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
    notify: function (message, type = 'info', duration = 5000) {
      if (!this.shouldShowNotification(type)) {
        console.log(`Notification suppressed (level: ${this.getNotificationLevel()}): ${type} - ${message}`);
        return;
      }

      ExamGrader.utils.showToast(message, type, duration);
    }
  },

  // CSRF token management
  csrf: {
    /**
     * Refresh CSRF token with improved error handling and retry logic
     */
    refreshToken: async function () {
      const maxRetries = 3;
      let lastError = null;

      for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
          console.log(`CSRF token refresh attempt ${attempt}/${maxRetries}`);

          const response = await fetch('/get-csrf-token', {
            method: 'GET',
            credentials: 'same-origin',
            headers: {
              'Cache-Control': 'no-cache',
              'Pragma': 'no-cache'
            }
          });

          if (response.ok) {
            const data = await response.json();
            if (data.csrf_token) {
              // Update meta tag
              const metaTag = document.querySelector('meta[name=csrf-token]');
              if (metaTag) {
                metaTag.setAttribute('content', data.csrf_token);
              } else {
                // Create meta tag if it doesn't exist
                const newMeta = document.createElement('meta');
                newMeta.name = 'csrf-token';
                newMeta.content = data.csrf_token;
                document.head.appendChild(newMeta);
              }

              // Update form inputs
              const tokenInputs = document.querySelectorAll('input[name=csrf_token]');
              tokenInputs.forEach(input => {
                input.value = data.csrf_token;
              });

              console.log('CSRF token refreshed successfully');
              return data.csrf_token;
            }
          }

          // If we get here, the response wasn't successful
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);

        } catch (error) {
          lastError = error;
          console.warn(`CSRF token refresh attempt ${attempt} failed:`, error);

          if (attempt < maxRetries) {
            // Wait before retrying with exponential backoff
            const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
            await new Promise(resolve => setTimeout(resolve, delay));
          }
        }
      }

      console.error('All CSRF token refresh attempts failed:', lastError);
      return null;
    },

    /**
     * Get CSRF token from multiple sources with fallback
     */
    getToken: function () {
      // Try meta tag first
      const metaTag = document.querySelector('meta[name=csrf-token]');
      if (metaTag && metaTag.getAttribute('content')) {
        return metaTag.getAttribute('content');
      }

      // Try form inputs
      const tokenInput = document.querySelector('input[name=csrf_token]');
      if (tokenInput && tokenInput.value) {
        return tokenInput.value;
      }

      // Try alternative input name
      const altTokenInput = document.querySelector('input[name=csrf-token]');
      if (altTokenInput && altTokenInput.value) {
        return altTokenInput.value;
      }

      return null;
    },

    /**
     * Initialize automatic CSRF token refresh with improved logic
     */
    initAutoRefresh: function (intervalMinutes = 30) {
      // Refresh token periodically
      setInterval(async () => {
        try {
          await this.refreshToken();
        } catch (error) {
          console.error('Periodic CSRF token refresh failed:', error);
        }
      }, intervalMinutes * 60 * 1000);

      // Refresh token after user becomes active after inactivity
      let userInactive = false;
      let inactivityTimer;

      const resetInactivityTimer = async () => {
        clearTimeout(inactivityTimer);
        if (userInactive) {
          userInactive = false;
          try {
            await this.refreshToken();
          } catch (error) {
            console.error('Inactivity-based CSRF token refresh failed:', error);
          }
        }
        inactivityTimer = setTimeout(() => {
          userInactive = true;
        }, 10 * 60 * 1000); // 10 minutes of inactivity
      };

      // User activity events
      ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
        document.addEventListener(event, resetInactivityTimer, true);
      });

      // Initial setup
      resetInactivityTimer();
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
      toast.className = `fixed top-4 right-4 z-50 max-w-sm bg-white border-l-4 rounded-lg shadow-lg p-4 animate-slide-up ${type === "error"
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
                        ${type === "error"
          ? '<svg class="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>'
          : type === "success"
            ? '<svg class="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>'
            : type === "warning"
              ? '<svg class="h-5 w-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>'
              : '<svg class="h-5 w-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>'
        }
                    </div>
                    <div class="ml-3">
                        <p class="text-sm font-medium ${type === "error"
          ? "text-red-800"
          : type === "success"
            ? "text-green-800"
            : type === "warning"
              ? "text-yellow-800"
              : "text-blue-800"
        }">${message}</p>
                    </div>
                    <div class="ml-auto pl-3">
                        <button type="button" class="inline-flex rounded-md p-1.5 ${type === "error"
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
      const maxRetries = 3;
      let lastError = null;

      for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
          // Add CSRF token if available - try multiple sources
          let csrfToken = ExamGrader.csrf.getToken();

          // Log CSRF token status for debugging
          if (!csrfToken) {
            console.warn('CSRF token not found in DOM. Attempting to refresh...');
            // Try to fetch a new CSRF token using our refresh mechanism
            try {
              csrfToken = await ExamGrader.csrf.refreshToken();
              if (csrfToken) {
                console.log('Successfully retrieved new CSRF token for API request');
              } else {
                console.error('Failed to retrieve CSRF token for API request');
              }
            } catch (tokenError) {
              console.error('Failed to fetch new CSRF token:', tokenError);
            }
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
                  // Attempt to refresh CSRF token and retry once
                  if (attempt === 1) {
                    console.log('Attempting to refresh CSRF token and retry...');
                    await ExamGrader.csrf.refreshToken();
                    continue; // Retry the request
                  } else {
                    // If retry also failed, reload the page
                    setTimeout(() => {
                      window.location.reload();
                    }, 3000);
                  }
                } else {
                  errorMessage = data.error || 'Bad request. Please check your input.';
                }
                break;
              case 401:
                errorMessage = 'Authentication required. Please refresh the page.';
                // Redirect to login if not authenticated
                setTimeout(() => {
                  window.location.href = '/auth/login';
                }, 2000);
                break;
              case 403:
                errorMessage = 'Access forbidden. You may need to refresh the page.';
                break;
              case 413:
                errorMessage = 'File too large. Please choose a smaller file.';
                break;
              case 429:
                errorMessage = 'Too many requests. Please wait a moment and try again.';
                // Wait before retrying for rate limit errors
                if (attempt < maxRetries) {
                  const delay = Math.min(5000 * attempt, 15000);
                  await new Promise(resolve => setTimeout(resolve, delay));
                  continue;
                }
                break;
              case 500:
                errorMessage = 'Server error. Please try again later.';
                // Retry server errors with exponential backoff
                if (attempt < maxRetries) {
                  const delay = Math.min(2000 * Math.pow(2, attempt - 1), 10000);
                  await new Promise(resolve => setTimeout(resolve, delay));
                  continue;
                }
                break;
            }

            throw new Error(errorMessage);
          }

          return data;
        } catch (error) {
          lastError = error;
          console.warn(`API request attempt ${attempt} failed:`, error);

          // Don't retry for certain types of errors
          if (error.message.includes('CSRF token error') && attempt > 1) {
            break;
          }

          if (attempt < maxRetries) {
            // Wait before retrying with exponential backoff
            const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
            await new Promise(resolve => setTimeout(resolve, delay));
          }
        }
      }

      // If we get here, all retries failed
      console.error('API request failed after all retries:', lastError);
      throw lastError;
    },

    /**
     * Display message with improved styling and auto-dismiss
     */
    displayMessage: function (message, type = "info", duration = 5000) {
      const messageArea = document.getElementById("message-area");
      const messageText = document.getElementById("message-text");

      if (!messageArea || !messageText) {
        console.warn("Message area elements not found, falling back to toast");
        this.showToast(message, type, duration);
        return;
      }

      // Set message content and styling
      messageText.textContent = message;

      // Remove existing classes and add new ones
      messageArea.className = `mb-4 p-3 rounded-md text-sm ${this.getMessageClasses(type)}`;

      // Show the message
      messageArea.classList.remove("hidden");

      // Auto-hide after duration
      setTimeout(() => {
        messageArea.classList.add("hidden");
      }, duration);
    },

    /**
     * Get CSS classes for message types
     */
    getMessageClasses: function (type) {
      switch (type) {
        case "error":
          return "bg-red-50 border border-red-200 text-red-800";
        case "success":
          return "bg-green-50 border border-green-200 text-green-800";
        case "warning":
          return "bg-yellow-50 border border-yellow-200 text-yellow-800";
        default:
          return "bg-blue-50 border border-blue-200 text-blue-800";
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

    /**
     * Enhanced error handling for AJAX and WebSocket
     */
    handleAjaxError: function (error, context = '') {
      let message = (error && error.message) ? error.message : 'An unexpected error occurred.';
      if (context) {
        message = `[${context}] ${message}`;
      }
      ExamGrader.notificationManager.notify(message, 'error', 8000);
      // Optionally, show a modal for critical errors
      if (context === 'background-job' || context === 'websocket') {
        ExamGrader.utils.showModal('Error', message + '<br>Please try again or contact support.', 'error');
      }
    },

    /**
     * Retry logic for failed background jobs
     */
    retryBackgroundJob: function (taskId, retryCallback) {
      ExamGrader.notificationManager.notify('Retrying background job...', 'info');
      if (typeof retryCallback === 'function') {
        retryCallback(taskId);
      }
    },

    /**
     * Show modal
     */
    showModal: function (title, message, type = 'info') {
      const modal = document.createElement('div');
      modal.className = 'fixed inset-0 z-50 overflow-y-auto';
      modal.innerHTML = `
        <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"></div>
          <span class="hidden sm:inline-block sm:align-middle sm:h-screen">&#8203;</span>
          <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
            <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
              <div class="sm:flex sm:items-start">
                <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-${type}-100 sm:mx-0 sm:h-10 sm:w-10">
                  <svg class="h-6 w-6 text-${type}-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                  </svg>
                </div>
                <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                  <h3 class="text-lg leading-6 font-medium text-gray-900">${title}</h3>
                  <div class="mt-2">
                    <p class="text-sm text-gray-500" id="modal-message">${message}</p>
                  </div>
                </div>
              </div>
            </div>
            <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
              <button type="button" class="retry-btn w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-primary-600 text-base font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:ml-3 sm:w-auto sm:text-sm">
                Retry
              </button>
              <button type="button" class="cancel-btn mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
                Cancel
              </button>
            </div>
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      // Add event listeners
      modal.querySelector('.retry-btn').addEventListener('click', () => {
        document.body.removeChild(modal);
        // The retryCallback will be executed by the caller of showModal
      });

      modal.querySelector('.cancel-btn').addEventListener('click', () => {
        document.body.removeChild(modal);
      });

      // Auto-remove after 30 seconds
      setTimeout(() => {
        if (document.body.contains(modal)) {
          document.body.removeChild(modal);
        }
      }, 30000);
    },

    /**
     * WebSocket error handling
     */
    initWebSocket: function (onMessageCallback, progressId, updateCallback, errorCallback) {
      if (window.io) {
        const socket = io();
        let fallbackStarted = false;
        socket.on('connect_error', function (err) {
          ExamGrader.utils.handleAjaxError(err, 'websocket');
          if (!fallbackStarted && typeof ExamGrader.utils.startAjaxPolling === 'function' && progressId && updateCallback && errorCallback) {
            fallbackStarted = true;
            ExamGrader.utils.startAjaxPolling(progressId, updateCallback, errorCallback);
          }
        });
        socket.on('error', function (err) {
          ExamGrader.utils.handleAjaxError(err, 'websocket');
          if (!fallbackStarted && typeof ExamGrader.utils.startAjaxPolling === 'function' && progressId && updateCallback && errorCallback) {
            fallbackStarted = true;
            ExamGrader.utils.startAjaxPolling(progressId, updateCallback, errorCallback);
          }
        });
        socket.on('message', onMessageCallback);
        return socket;
      }
      // If SocketIO is not available, fallback immediately
      if (typeof ExamGrader.utils.startAjaxPolling === 'function' && progressId && updateCallback && errorCallback) {
        ExamGrader.utils.startAjaxPolling(progressId, updateCallback, errorCallback);
      }
      return null;
    },

    /**
     * AJAX error handling for fetch
     */
    initFetch: function () {
      window.fetch = (function (fetch) {
        return function () {
          return fetch.apply(this, arguments).then(function (response) {
            if (!response.ok) {
              return response.text().then(function (text) {
                throw new Error(text || response.statusText);
              });
            }
            return response;
          }).catch(function (error) {
            ExamGrader.utils.handleAjaxError(error, 'ajax');
            throw error;
          });
        };
      })(window.fetch);
    },

    /**
     * Start AJAX polling for a progress ID
     */
    startAjaxPolling: function (progressId, updateCallback, errorCallback) {
      if (ExamGrader.progressPollingInterval) {
        clearInterval(ExamGrader.progressPollingInterval);
      }

      ExamGrader.progressPollingInterval = setInterval(async () => {
        try {
          const progress = await ExamGrader.api.getProgress(progressId);
          updateCallback(progress);

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
          errorCallback(error);
          clearInterval(ExamGrader.progressPollingInterval);
          ExamGrader.progressPollingInterval = null;
          ExamGrader.ui.hideProgressModal();
          ExamGrader.notificationManager.notify('Error during AI processing: ' + error.message, 'error');
        }
      }, 2000); // Poll every 2 seconds
    },

    /**
     * Stop AJAX polling
     */
    stopAjaxPolling: function () {
      if (ExamGrader.progressPollingInterval) {
        clearInterval(ExamGrader.progressPollingInterval);
        ExamGrader.progressPollingInterval = null;
      }
    }
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

  // Error handling system
  errorHandler: {
    /**
     * Handle different types of errors with appropriate user feedback
     */
    handleError: function (error, context = 'general') {
      console.error(`Error in ${context}:`, error);

      let userMessage = 'An unexpected error occurred.';
      let errorType = 'error';
      let shouldRetry = false;
      let retryAction = null;

      // Parse error message and determine appropriate response
      if (typeof error === 'string') {
        userMessage = error;
      } else if (error.message) {
        userMessage = error.message;
      }

      // Handle specific error types
      if (userMessage.toLowerCase().includes('csrf')) {
        userMessage = 'Session expired. Please refresh the page and try again.';
        errorType = 'warning';
        shouldRetry = true;
        retryAction = () => window.location.reload();
      } else if (userMessage.toLowerCase().includes('network') || userMessage.toLowerCase().includes('connection')) {
        userMessage = 'Network connection issue. Please check your internet connection and try again.';
        errorType = 'warning';
        shouldRetry = true;
        retryAction = () => this.retryLastOperation();
      } else if (userMessage.toLowerCase().includes('timeout')) {
        userMessage = 'Request timed out. The server may be busy. Please try again.';
        errorType = 'warning';
        shouldRetry = true;
        retryAction = () => this.retryLastOperation();
      } else if (userMessage.toLowerCase().includes('authentication') || userMessage.toLowerCase().includes('unauthorized')) {
        userMessage = 'Authentication required. Please log in again.';
        errorType = 'warning';
        shouldRetry = true;
        retryAction = () => window.location.href = '/auth/login';
      } else if (userMessage.toLowerCase().includes('file too large')) {
        userMessage = 'File size exceeds the maximum limit. Please choose a smaller file.';
        errorType = 'warning';
      } else if (userMessage.toLowerCase().includes('ocr') && userMessage.toLowerCase().includes('failed')) {
        userMessage = 'OCR processing failed. This may be due to image quality or format. Please try with a different image.';
        errorType = 'warning';
        shouldRetry = true;
        retryAction = () => this.retryLastOperation();
      } else if (userMessage.toLowerCase().includes('ai') && userMessage.toLowerCase().includes('unavailable')) {
        userMessage = 'AI services are temporarily unavailable. Please try again later.';
        errorType = 'warning';
        shouldRetry = true;
        retryAction = () => this.retryLastOperation();
      }

      // Show notification to user
      ExamGrader.notificationManager.notify(userMessage, errorType);

      // Show retry option if applicable
      if (shouldRetry && retryAction) {
        this.showRetryDialog(userMessage, retryAction);
      }

      return {
        message: userMessage,
        type: errorType,
        shouldRetry: shouldRetry,
        retryAction: retryAction
      };
    },

    /**
     * Show retry dialog with user-friendly options
     */
    showRetryDialog: function (message, retryAction) {
      const dialog = document.createElement('div');
      dialog.className = 'fixed inset-0 z-50 overflow-y-auto';
      dialog.innerHTML = `
        <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"></div>
          <span class="hidden sm:inline-block sm:align-middle sm:h-screen">&#8203;</span>
          <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
            <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
              <div class="sm:flex sm:items-start">
                <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100 sm:mx-0 sm:h-10 sm:w-10">
                  <svg class="h-6 w-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                  </svg>
                </div>
                <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                  <h3 class="text-lg leading-6 font-medium text-gray-900">Operation Failed</h3>
                  <div class="mt-2">
                    <p class="text-sm text-gray-500">${message}</p>
                  </div>
                </div>
              </div>
            </div>
            <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
              <button type="button" class="retry-btn w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-primary-600 text-base font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:ml-3 sm:w-auto sm:text-sm">
                Retry
              </button>
              <button type="button" class="cancel-btn mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
                Cancel
              </button>
            </div>
          </div>
        </div>
      `;

      document.body.appendChild(dialog);

      // Add event listeners
      dialog.querySelector('.retry-btn').addEventListener('click', () => {
        document.body.removeChild(dialog);
        retryAction();
      });

      dialog.querySelector('.cancel-btn').addEventListener('click', () => {
        document.body.removeChild(dialog);
      });

      // Auto-remove after 30 seconds
      setTimeout(() => {
        if (document.body.contains(dialog)) {
          document.body.removeChild(dialog);
        }
      }, 30000);
    },

    /**
     * Retry the last operation (placeholder for now)
     */
    retryLastOperation: function () {
      // This would be implemented to retry the specific operation that failed
      console.log('Retrying last operation...');
      // For now, just refresh the page
      window.location.reload();
    },

    /**
     * Handle API errors with specific error codes
     */
    handleApiError: function (response, context = 'API request') {
      const errorCode = response.error_code || response.code;
      let userMessage = response.error || response.message || 'An error occurred';

      switch (errorCode) {
        case 'GUIDE_MISSING':
          userMessage = 'Please upload a marking guide first.';
          break;
        case 'SUBMISSIONS_MISSING':
          userMessage = 'Please upload submissions first.';
          break;
        case 'SERVICE_UNAVAILABLE':
          userMessage = 'AI services are temporarily unavailable. Please try again later.';
          break;
        case 'PROCESSING_ERROR':
          userMessage = 'Processing failed. Please try again or contact support.';
          break;
        case 'CSRF_TOKEN_ERROR':
          userMessage = 'Session expired. Please refresh the page and try again.';
          break;
        default:
          // Use the provided error message
          break;
      }

      return this.handleError(userMessage, context);
    }
  },

  // Initialize application
  init: function () {
    console.log("Exam Grader Application initialized");

    // Initialize common functionality
    this.initFlashMessages();
    this.initServiceWorker();

    // Initialize settings from localStorage
    this.initSettings();

    // Initialize CSRF token auto-refresh
    this.csrf.initAutoRefresh();

    // Try to refresh CSRF token immediately
    this.csrf.refreshToken().then(token => {
      if (token) {
        console.log('Initial CSRF token refresh successful');
      } else {
        console.warn('Initial CSRF token refresh failed, will retry later');
      }
    });

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
  initSettings: function () {
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

  // Refresh CSRF token on page load, especially important after redirects
  if (window.location.pathname === '/dashboard') {
    console.log('Dashboard page detected, ensuring CSRF token is refreshed');
    ExamGrader.csrf.refreshToken().then(token => {
      if (token) {
        console.log('Dashboard CSRF token refresh successful');
      } else {
        console.warn('Dashboard CSRF token refresh failed');
      }
    });
  }
});

// Export for use in other scripts

// Function to download submission content
function downloadSubmission(submissionId) {
  console.log('Downloading submission:', submissionId);

  // Show loading notification
  ExamGrader.notificationManager.notify('Preparing download...', 'info');

  // Fetch submission content
  fetch(`/view-submission/${submissionId}`)
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to fetch submission content');
      }
      return response.text();
    })
    .then(html => {
      // Create a temporary container to parse the HTML
      const tempContainer = document.createElement('div');
      tempContainer.innerHTML = html;

      // Extract the raw text content
      const rawTextScript = tempContainer.querySelector('script');
      let rawText = '';

      if (rawTextScript) {
        const scriptContent = rawTextScript.textContent;
        const match = scriptContent.match(/raw_text: ([^,]+),/);
        if (match && match[1]) {
          try {
            rawText = JSON.parse(match[1]);
          } catch (e) {
            console.error('Error parsing raw text:', e);
          }
        }
      }

      // Create content object
      const content = {
        submission_id: submissionId,
        raw_text: rawText,
        downloaded_at: new Date().toISOString()
      };

      // Create and download the file
      const dataStr = JSON.stringify(content, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });

      const link = document.createElement('a');
      link.href = URL.createObjectURL(dataBlob);
      link.download = `submission_${submissionId.substring(0, 8)}_content.json`;
      link.click();

      // Show success notification
      ExamGrader.notificationManager.notify('Submission downloaded successfully!', 'success');
    })
    .catch(error => {
      console.error('Error downloading submission:', error);
      ExamGrader.notificationManager.notify(`Download failed: ${error.message}`, 'error');
    });
}

// --- Results Page Details Modal Support ---
// Note: viewDetails function is implemented in results.html template
// This ensures the function has access to the results_list data from the template
