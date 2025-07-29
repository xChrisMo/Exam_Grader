/**
 * Exam Grader Application JavaScript
 * Common functionality and utilities
 */

// Global error handler
window.addEventListener('error', function (event) {
  console.error('Global JavaScript Error:', event.error);
  if (typeof ExamGrader !== 'undefined' && ExamGrader.notificationManager) {
    ExamGrader.notificationManager.notify('An unexpected error occurred', 'error');
  }
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', function (event) {
  console.error('Unhandled Promise Rejection:', event.reason);
  if (typeof ExamGrader !== 'undefined' && ExamGrader.notificationManager) {
    ExamGrader.notificationManager.notify('An unexpected error occurred', 'error');
  }
});

// Application namespace
window.ExamGrader = window.ExamGrader || {};

// Initialize application object - extend existing object instead of replacing
Object.assign(ExamGrader, {

  // Configuration
  config: {
    maxFileSize: 100 * 1024 * 1024, // 100MB (increased from 16MB)
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
      enhancedProcessingStart: "/api/enhanced-processing/start",
      enhancedProcessingProgress: "/api/enhanced-processing/progress",
      processMapping: "/api/enhanced-processing/start", // Legacy compatibility
      processGrading: "/api/enhanced-processing/start", // Legacy compatibility
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
        // Only log in development mode
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
          console.log(`Notification suppressed (level: ${this.getNotificationLevel()}): ${type} - ${message}`);
        }
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
      // Try meta tag first (most reliable for AJAX requests)
      const metaTag = document.querySelector('meta[name=csrf-token]');
      if (metaTag && metaTag.getAttribute('content')) {
        const token = metaTag.getAttribute('content');
        if (token && token.trim() !== '') {
          return token;
        }
      }

      // Try form inputs (for form submissions)
      const tokenInput = document.querySelector('input[name=csrf_token]');
      if (tokenInput && tokenInput.value) {
        const token = tokenInput.value;
        if (token && token.trim() !== '') {
          return token;
        }
      }

      // Try alternative input name
      const altTokenInput = document.querySelector('input[name=csrf-token]');
      if (altTokenInput && altTokenInput.value) {
        const token = altTokenInput.value;
        if (token && token.trim() !== '') {
          return token;
        }
      }

      console.warn('CSRF token not found in any expected location');
      return null;
    },

    /**
     * Initialize automatic CSRF token refresh with improved logic
     */
    initAutoRefresh: function (intervalMinutes = 60) {
      // Refresh token periodically (increased to 60 minutes for development)
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
    },

    /**
     * Ensure all forms have CSRF tokens
     */
    ensureFormsHaveTokens: function () {
      const forms = document.querySelectorAll('form');
      const currentToken = this.getToken();

      if (!currentToken) {
        console.warn('No CSRF token available to add to forms');
        return;
      }

      forms.forEach(form => {
        // Skip forms that already have CSRF tokens
        const existingToken = form.querySelector('input[name="csrf_token"]');
        if (existingToken) {
          // Update existing token if it's different
          if (existingToken.value !== currentToken) {
            existingToken.value = currentToken;
            console.log('Updated CSRF token in form:', form.id || form.action);
          }
        } else {
          // Add CSRF token to forms that don't have one
          const tokenInput = document.createElement('input');
          tokenInput.type = 'hidden';
          tokenInput.name = 'csrf_token';
          tokenInput.value = currentToken;
          form.appendChild(tokenInput);
          console.log('Added CSRF token to form:', form.id || form.action);
        }
      });
    },

    // Type checking utilities for better code quality
    typeCheck: {
      isString: function (value) {
        return typeof value === 'string';
      },

      isNumber: function (value) {
        return typeof value === 'number' && !isNaN(value);
      },

      isObject: function (value) {
        return value !== null && typeof value === 'object' && !Array.isArray(value);
      },

      isArray: function (value) {
        return Array.isArray(value);
      },

      isFunction: function (value) {
        return typeof value === 'function';
      },

      isEmpty: function (value) {
        if (value === null || value === undefined) return true;
        if (this.isString(value) || this.isArray(value)) return value.length === 0;
        if (this.isObject(value)) return Object.keys(value).length === 0;
        return false;
      }
    }
  },

  // Utility functions (moved to top level for proper access)
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
            defaultHeaders['X-CSRF-Token'] = csrfToken; // Alternative header name
          } else {
            console.warn('No CSRF token available for request to:', url);
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
            "Grading completed successfully!",
            "success"
          );
          return true;
        } else {
          throw new Error(data.error || "Grading failed");
        }
      } catch (error) {
        ExamGrader.notificationManager.notify(`Grading failed: ${error.message}`, "error");
        return false;
      }
    },

    /**
     * Get progress status
     */
    getProgress: async function (progressId) {
      try {
        const data = await ExamGrader.utils.apiRequest(
          `/api/progress/${progressId}`,
          {
            method: "GET",
          }
        );
        return data;
      } catch (error) {
        console.error("Error getting progress:", error);
        throw error;
      }
    },

    /**
     * Export results
     */
    exportResults: async function () {
      try {
        const response = await fetch('/api/export-results', {
          method: 'GET',
          headers: {
            'X-CSRFToken': ExamGrader.csrf.getToken(),
          },
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Get filename from response headers
        const contentDisposition = response.headers.get('content-disposition');
        let filename = 'results.pdf';
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="(.+)"/);
          if (filenameMatch) {
            filename = filenameMatch[1];
          }
        }

        // Create blob and download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        ExamGrader.notificationManager.notify('Results exported successfully!', 'success');
        return true;
      } catch (error) {
        ExamGrader.notificationManager.notify(`Export failed: ${error.message}`, 'error');
        return false;
      }
    }
  },

  // UI management
  ui: {
    /**
     * Show progress modal
     */
    showProgressModal: function (title = 'Processing...', message = 'Please wait while we process your request.') {
      const modal = document.createElement('div');
      modal.id = 'progress-modal';
      modal.className = 'fixed inset-0 z-50 overflow-y-auto';
      modal.innerHTML = `
        <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"></div>
          <span class="hidden sm:inline-block sm:align-middle sm:h-screen">&#8203;</span>
          <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
            <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
              <div class="sm:flex sm:items-start">
                <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-primary-100 sm:mx-0 sm:h-10 sm:w-10">
                  <svg class="animate-spin h-6 w-6 text-primary-600" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
                <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                  <h3 class="text-lg leading-6 font-medium text-gray-900" id="progress-title">${title}</h3>
                  <div class="mt-2">
                    <p class="text-sm text-gray-500" id="progress-message">${message}</p>
                    <div class="mt-4">
                      <div class="bg-gray-200 rounded-full h-2">
                        <div id="progress-bar" class="bg-primary-600 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
                      </div>
                      <p class="text-xs text-gray-500 mt-1" id="progress-percentage">0%</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
    },

    /**
     * Update progress modal
     */
    updateProgressModal: function (percentage, message) {
      const progressBar = document.getElementById('progress-bar');
      const progressPercentage = document.getElementById('progress-percentage');
      const progressMessage = document.getElementById('progress-message');

      if (progressBar) {
        progressBar.style.width = `${percentage}%`;
      }
      if (progressPercentage) {
        progressPercentage.textContent = `${percentage}%`;
      }
      if (progressMessage && message) {
        progressMessage.textContent = message;
      }
    },

    /**
     * Hide progress modal
     */
    hideProgressModal: function () {
      const modal = document.getElementById('progress-modal');
      if (modal) {
        modal.remove();
      }
    }
  }
});

// Global functions for backward compatibility
function viewDetails(submissionId) {
  console.log('viewDetails called for submission:', submissionId);

  if (!submissionId) {
    ExamGrader.notificationManager.notify('Invalid submission ID', 'error');
    return;
  }

  // Show loading state
  const modal = document.getElementById('detailsModal');
  const modalContent = document.getElementById('modalContent');

  if (!modal || !modalContent) {
    ExamGrader.notificationManager.notify('Modal elements not found', 'error');
    return;
  }

  modalContent.innerHTML = `
    <div class="flex justify-center items-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
      <span class="ml-3">Loading submission details...</span>
    </div>
  `;

  modal.classList.remove('hidden');

  // Fetch submission details
  fetch(`/api/submission-details/${submissionId}`, {
    method: 'GET',
    headers: {
      'X-CSRFToken': ExamGrader.csrf.getToken(),
      'Content-Type': 'application/json'
    }
  })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.success) {
        modalContent.innerHTML = `
        <div class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 class="text-sm font-medium text-gray-900">Filename</h4>
              <p class="mt-1 text-sm text-gray-600">${data.submission.filename || 'Unknown'}</p>
            </div>
            <div>
              <h4 class="text-sm font-medium text-gray-900">Score</h4>
              <p class="mt-1 text-sm text-gray-600">${data.submission.score || 0}%</p>
            </div>
            <div>
              <h4 class="text-sm font-medium text-gray-900">Status</h4>
              <p class="mt-1 text-sm text-gray-600">${data.submission.status || 'Unknown'}</p>
            </div>
            <div>
              <h4 class="text-sm font-medium text-gray-900">Processed At</h4>
              <p class="mt-1 text-sm text-gray-600">${data.submission.processed_at || 'Not processed'}</p>
            </div>
          </div>
          
          ${data.submission.feedback ? `
            <div>
              <h4 class="text-sm font-medium text-gray-900">Feedback</h4>
              <div class="mt-1 text-sm text-gray-600 bg-gray-50 p-3 rounded-md">
                ${data.submission.feedback}
              </div>
            </div>
          ` : ''}
          
          ${data.submission.questions && data.submission.questions.length > 0 ? `
            <div>
              <h4 class="text-sm font-medium text-gray-900">Question Results</h4>
              <div class="mt-2 space-y-2">
                ${data.submission.questions.map(q => `
                  <div class="border border-gray-200 rounded-md p-3">
                    <div class="flex justify-between items-start">
                      <h5 class="text-sm font-medium text-gray-900">Question ${q.number}</h5>
                      <span class="text-sm font-medium ${q.score >= 80 ? 'text-green-600' : q.score >= 60 ? 'text-yellow-600' : 'text-red-600'}">${q.score}%</span>
                    </div>
                    ${q.feedback ? `<p class="mt-1 text-xs text-gray-600">${q.feedback}</p>` : ''}
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        </div>
      `;
      } else {
        throw new Error(data.error || 'Failed to load submission details');
      }
    })
    .catch(error => {
      console.error('Error loading submission details:', error);
      modalContent.innerHTML = `
      <div class="text-center py-8">
        <div class="text-red-500 mb-2">
          <svg class="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
        </div>
        <h3 class="text-lg font-medium text-gray-900">Error Loading Details</h3>
        <p class="mt-2 text-sm text-gray-600">${error.message}</p>
        <button onclick="closeDetailsModal()" class="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700">
          Close
        </button>
      </div>
    `;
    });
}

function exportResults() {
  console.log('exportResults called');
  ExamGrader.api.exportResults();
}

function closeDetailsModal() {
  const modal = document.getElementById('detailsModal');
  if (modal) {
    modal.classList.add('hidden');
  }
}

// Error handling system
ExamGrader.errorHandler = {
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
};

// Initialize application
ExamGrader.init = function () {
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
      // Ensure all forms have the fresh token
      this.csrf.ensureFormsHaveTokens();
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

  // Performance optimizations
  this.initPerformanceOptimizations();
};

// Performance optimization utilities
ExamGrader.performance = {
  // Debounce function for performance optimization
  debounce: function (func, wait, immediate) {
    let timeout;
    return function executedFunction() {
      const context = this;
      const args = arguments;
      const later = function () {
        timeout = null;
        if (!immediate) func.apply(context, args);
      };
      const callNow = immediate && !timeout;
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
      if (callNow) func.apply(context, args);
    };
  },

  // Throttle function for performance optimization
  throttle: function (func, limit) {
    let inThrottle;
    return function () {
      const args = arguments;
      const context = this;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  },

  // Lazy loading for images
  initLazyLoading: function () {
    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.classList.remove('lazy');
            imageObserver.unobserve(img);
          }
        });
      });

      document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
      });
    }
  }
};

// Initialize performance optimizations
ExamGrader.initPerformanceOptimizations = function () {
  // Debounce scroll events
  const debouncedScroll = this.performance.debounce(() => {
    // Handle scroll events efficiently
  }, 100);

  window.addEventListener('scroll', debouncedScroll, { passive: true });

  // Throttle resize events
  const throttledResize = this.performance.throttle(() => {
    // Handle resize events efficiently
  }, 250);

  window.addEventListener('resize', throttledResize);

  // Initialize lazy loading
  this.performance.initLazyLoading();
};

// Initialize settings from localStorage
ExamGrader.initSettings = function () {
  // Get notification level from localStorage
  const storedNotificationLevel = localStorage.getItem('notification_level');
  if (storedNotificationLevel) {
    // Update notification level select if it exists
    const notificationLevelSelect = document.getElementById('notification_level');
    if (notificationLevelSelect) {
      notificationLevelSelect.value = storedNotificationLevel;
    }
  }
};

/**
 * Initialize flash message handling
 */
ExamGrader.initFlashMessages = function () {
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
};

/**
 * Initialize service worker for offline functionality (if needed)
 */
ExamGrader.initServiceWorker = function () {
  if ("serviceWorker" in navigator) {
    // Service worker registration would go here
    // navigator.serviceWorker.register('/static/js/sw.js');
  }
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
// Note: Duplicate viewDetails function removed - using the one defined above

// Note: Duplicate exportResults and closeDetailsModal functions removed - using the ones defined above

// Dashboard update functions
ExamGrader.dashboard = {
  // Update dashboard statistics
  updateStats: function () {
    ExamGrader.utils.apiRequest('/api/dashboard-stats', {
      method: 'GET'
    })
      .then(data => {
        if (data.success) {
          // Update last score card
          const lastScoreElement = document.querySelector('[data-i18n="last_score"]').parentElement.querySelector('.text-lg.font-medium.text-gray-900');
          if (lastScoreElement && data.stats.last_score !== undefined) {
            lastScoreElement.textContent = data.stats.last_score > 0 ? `${data.stats.last_score}%` : '--';
          }

          // Update submission counts
          const totalSubmissionsElement = document.getElementById('total-submissions-count');
          if (totalSubmissionsElement && data.stats.total_submissions !== undefined) {
            totalSubmissionsElement.textContent = data.stats.total_submissions;
          }

          const processedSubmissionsElement = document.getElementById('processed-submissions-dashboard-count');
          if (processedSubmissionsElement && data.stats.processed_submissions !== undefined) {
            processedSubmissionsElement.innerHTML = `${data.stats.processed_submissions} <span data-i18n="processed">processed</span>`;
          }

          // Update system status
          if (data.stats.service_status) {
            const systemStatusElement = document.querySelector('[data-i18n="system_status"]').parentElement.querySelector('.text-lg.font-medium.text-gray-900');
            if (systemStatusElement) {
              const isOnline = data.stats.service_status.ocr_status && data.stats.service_status.llm_status;
              systemStatusElement.innerHTML = isOnline ?
                '<span class="text-success-600" data-i18n="status_online">Online</span>' :
                '<span class="text-warning-600" data-i18n="status_limited">Limited</span>';
            }
          }
        }
      })
      .catch(error => {
        console.error('Error updating dashboard stats:', error);
      });
  },

  // Initialize auto-refresh for dashboard
  initAutoRefresh: function (intervalSeconds = 30) {
    // Update immediately
    this.updateStats();

    // Set up periodic updates
    setInterval(() => {
      this.updateStats();
    }, intervalSeconds * 1000);
  }
};

// Submission status update functions
ExamGrader.submissions = {
  // Update submission status
  updateStatus: function (submissionId, status) {
    const statusElement = document.querySelector(`#submission-row-${submissionId} .inline-flex.items-center`);
    if (statusElement) {
      const isProcessed = status === 'processed' || status === 'completed';
      statusElement.className = `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${isProcessed ? 'bg-success-100 text-success-800' : 'bg-warning-100 text-warning-800'
        }`;
      statusElement.innerHTML = `
        <svg class="mr-1.5 h-2 w-2 ${isProcessed ? 'text-success-400' : 'text-warning-400'}" fill="currentColor" viewBox="0 0 8 8">
          <circle cx="4" cy="4" r="3" />
        </svg>
        ${isProcessed ? 'Processed' : 'Pending'}
      `;
    }
  },

  // Update upload date
  updateUploadDate: function (submissionId, date) {
    const dateElement = document.querySelector(`#submission-row-${submissionId} .text-sm.text-gray-500`);
    if (dateElement && date && date !== 'Unknown') {
      const formattedDate = new Date(date).toLocaleDateString();
      dateElement.textContent = formattedDate;
    }
  },

  // Refresh all submission statuses
  refreshStatuses: function () {
    ExamGrader.utils.apiRequest('/api/submission-statuses', {
      method: 'GET'
    })
      .then(data => {
        if (data.success && data.submissions) {
          data.submissions.forEach(submission => {
            this.updateStatus(submission.id, submission.status);
            this.updateUploadDate(submission.id, submission.uploaded_at);
          });

          // Update counts
          const processedCount = data.submissions.filter(s => s.status === 'processed' || s.status === 'completed').length;
          const pendingCount = data.submissions.length - processedCount;

          const processedCountElement = document.getElementById('processed-submissions-count');
          const pendingCountElement = document.getElementById('pending-submissions-count');
          const totalCountElement = document.getElementById('total-submissions-count');

          if (processedCountElement) processedCountElement.textContent = processedCount;
          if (pendingCountElement) pendingCountElement.textContent = pendingCount;
          if (totalCountElement) totalCountElement.textContent = data.submissions.length;
        }
      })
      .catch(error => {
        console.error('Error refreshing submission statuses:', error);
      });
  }
};

// Progress bar improvements
ExamGrader.progressBar = {
  // Create enhanced progress bar
  create: function (containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return null;

    const progressBar = document.createElement('div');
    progressBar.className = 'w-full bg-gray-200 rounded-full h-4 mb-4 overflow-hidden';
    progressBar.innerHTML = `
      <div class="bg-gradient-to-r from-primary-500 to-primary-600 h-4 rounded-full transition-all duration-300 ease-out flex items-center justify-center relative overflow-hidden" style="width: 0%">
        <span class="text-xs font-medium text-white z-10">${options.showPercentage ? '0%' : ''}</span>
        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-20 animate-pulse"></div>
      </div>
    `;

    container.appendChild(progressBar);
    return progressBar;
  },

  // Update progress bar
  update: function (progressBar, percentage, message = '') {
    if (!progressBar) return;

    const bar = progressBar.querySelector('div');
    const text = progressBar.querySelector('span');

    if (bar) {
      bar.style.width = `${Math.min(100, Math.max(0, percentage))}%`;

      // Change color based on progress
      if (percentage >= 100) {
        bar.className = bar.className.replace('from-primary-500 to-primary-600', 'from-success-500 to-success-600');
      } else if (percentage >= 75) {
        bar.className = bar.className.replace('from-primary-500 to-primary-600', 'from-info-500 to-info-600');
      }
    }

    if (text) {
      text.textContent = message || `${Math.round(percentage)}%`;
    }
  },

  // Remove progress bar
  remove: function (progressBar) {
    if (progressBar && progressBar.parentNode) {
      progressBar.parentNode.removeChild(progressBar);
    }
  }
};

// Initialize dashboard auto-refresh when on dashboard page
document.addEventListener('DOMContentLoaded', function () {
  // Check if we're on the dashboard page
  if (window.location.pathname === '/dashboard' || window.location.pathname.endsWith('/dashboard')) {
    ExamGrader.dashboard.initAutoRefresh(120); // Refresh every 2 minutes (reduced frequency)
  }

  // Check if we're on the submissions page
  if (window.location.pathname === '/submissions' || window.location.pathname.endsWith('/submissions')) {
    // Refresh submission statuses every 15 seconds
    setInterval(() => {
      ExamGrader.submissions.refreshStatuses();
    }, 15000);
  }
});

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
  if (typeof ExamGrader !== 'undefined' && ExamGrader.init) {
    ExamGrader.init();
  }
});

// Enhanced Processing Utilities
ExamGrader.processing = {
    // Active polling intervals
    activePolls: new Map(),
    
    // Start progress monitoring with improved error handling
    startProgressMonitoring: function(taskId, callbacks = {}) {
        if (this.activePolls.has(taskId)) {
            this.stopProgressMonitoring(taskId);
        }
        
        const monitor = new ProcessingMonitor(taskId, callbacks);
        this.activePolls.set(taskId, monitor);
        monitor.start();
        
        return monitor;
    },
    
    // Stop progress monitoring
    stopProgressMonitoring: function(taskId) {
        const monitor = this.activePolls.get(taskId);
        if (monitor) {
            monitor.stop();
            this.activePolls.delete(taskId);
        }
    },
    
    // Stop all active monitoring
    stopAllMonitoring: function() {
        for (const [taskId, monitor] of this.activePolls) {
            monitor.stop();
        }
        this.activePolls.clear();
    }
};

// Processing Monitor Class
class ProcessingMonitor {
    constructor(taskId, callbacks = {}) {
        this.taskId = taskId;
        this.callbacks = callbacks;
        this.isActive = false;
        this.retryCount = 0;
        this.maxRetries = 10;
        this.pollInterval = 2000;
        this.timeoutId = null;
    }
    
    start() {
        this.isActive = true;
        this.retryCount = 0;
        this.poll();
    }
    
    stop() {
        this.isActive = false;
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }
    }
    
    async poll() {
        if (!this.isActive) return;
        
        try {
            const response = await fetch(`/api/enhanced-processing/progress/${this.taskId}`, {
                headers: {
                    'X-CSRFToken': ExamGrader.csrf.getToken()
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Unknown error');
            }
            
            this.retryCount = 0; // Reset on success
            
            // Call progress callback
            if (this.callbacks.onProgress) {
                this.callbacks.onProgress(data);
            }
            
            // Check completion
            if (data.status === 'completed') {
                this.stop();
                if (this.callbacks.onComplete) {
                    this.callbacks.onComplete(data);
                }
            } else if (data.status === 'failed') {
                this.stop();
                if (this.callbacks.onError) {
                    this.callbacks.onError(new Error(data.message || 'Processing failed'));
                }
            } else {
                // Schedule next poll
                this.scheduleNextPoll();
            }
            
        } catch (error) {
            console.error('Progress polling error:', error);
            this.retryCount++;
            
            if (this.retryCount >= this.maxRetries) {
                this.stop();
                if (this.callbacks.onError) {
                    this.callbacks.onError(error);
                }
            } else {
                // Retry with exponential backoff
                this.scheduleNextPoll(true);
            }
        }
    }
    
    scheduleNextPoll(isRetry = false) {
        if (!this.isActive) return;
        
        let delay = this.pollInterval;
        if (isRetry) {
            delay = Math.min(1000 * Math.pow(2, this.retryCount), 30000);
        }
        
        this.timeoutId = setTimeout(() => this.poll(), delay);
    }
}

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (ExamGrader.processing) {
        ExamGrader.processing.stopAllMonitoring();
    }
});
