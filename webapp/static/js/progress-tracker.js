/**
 * Progress Tracker
 *
 * This module handles tracking and displaying progress for long-running operations
 * like LLM calls and OCR processing.
 */

class ProgressTracker {
  /**
   * Initialize the progress tracker
   * @param {Object} options - Configuration options
   * @param {string} options.containerId - ID of the container element for the progress bar
   * @param {number} options.pollInterval - Polling interval in milliseconds (default: 1000)
   * @param {Function} options.onComplete - Callback function when operation completes
   * @param {Function} options.onError - Callback function when operation fails
   */
  constructor(options = {}) {
    this.containerId = options.containerId || "progress-container";
    this.pollInterval = options.pollInterval || 800; // Faster polling for more responsive updates
    this.onComplete = options.onComplete || function () {};
    this.onError = options.onError || function () {};

    this.trackerId = null;
    this.pollTimer = null;
    this.operationType = null;
    this.isActive = false;
    this.lastPollTime = 0;
    this.consecutiveErrors = 0;
    this.lastProgress = null; // Track last progress to prevent oscillation
  }

  /**
   * Start tracking progress for an operation
   * @param {string} trackerId - ID of the progress tracker
   * @param {string} operationType - Type of operation (llm, ocr)
   */
  startTracking(trackerId, operationType) {
    if (!trackerId) {
      console.error("No tracker ID provided");
      return;
    }

    // Check if we're already tracking this operation
    if (this.trackerId === trackerId && this.isActive) {
      console.log(
        `Already tracking progress for ${operationType} operation: ${trackerId}`
      );
      return;
    }

    this.trackerId = trackerId;
    this.operationType = operationType;
    this.isActive = true;
    this.lastProgress = null; // Reset progress tracking for new operation

    // Create or show the progress container
    this._createProgressUI();

    // Start polling for updates
    this._startPolling();

    console.log(
      `Started tracking progress for ${operationType} operation: ${trackerId}`
    );

    // Store in localStorage to persist across page loads
    localStorage.setItem("progressTracker_id", trackerId);
    localStorage.setItem("progressTracker_type", operationType);
    localStorage.setItem("progressTracker_active", "true");
  }

  /**
   * Stop tracking progress
   */
  stopTracking() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }

    // Delete the tracker on the server if we have a tracker ID
    if (this.trackerId) {
      this.deleteTracker(this.trackerId)
        .then(() =>
          console.log(`Deleted tracker ${this.trackerId} from server`)
        )
        .catch((error) =>
          console.error(`Failed to delete tracker ${this.trackerId}:`, error)
        );
    }

    this.isActive = false;
    this.trackerId = null;
    this.operationType = null;
    this.lastProgress = null; // Reset progress tracking
    this.consecutiveErrors = 0; // Reset error counter

    // Hide the progress container
    const container = document.getElementById(this.containerId);
    if (container) {
      container.style.display = "none";
    }

    // Clear localStorage
    localStorage.removeItem("progressTracker_id");
    localStorage.removeItem("progressTracker_type");
    localStorage.removeItem("progressTracker_active");

    console.log("Stopped progress tracking");
  }

  /**
   * Delete a tracker from the server
   * @param {string} trackerId - ID of the tracker to delete
   * @returns {Promise} - Promise that resolves when the tracker is deleted
   */
  deleteTracker(trackerId) {
    if (!trackerId) return Promise.resolve();

    return fetch(`/api/progress/${trackerId}`, {
      method: "DELETE",
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        console.log(`Tracker deletion response:`, data);
        return data;
      });
  }

  /**
   * Create or update the progress UI
   * @private
   */
  _createProgressUI() {
    let container = document.getElementById(this.containerId);

    // If container doesn't exist, create it
    if (!container) {
      container = document.createElement("div");
      container.id = this.containerId;
      container.className = "progress-container";

      // Create the progress UI structure
      container.innerHTML = `
                <div class="progress-card">
                    <div class="progress-header">
                        <h5 class="progress-title">Processing...</h5>
                        <button type="button" class="btn-close progress-close" aria-label="Close"></button>
                    </div>
                    <div class="progress-body">
                        <div class="progress">
                            <div class="progress-bar progress-bar-striped progress-bar-animated"
                                 role="progressbar" style="width: 0%"
                                 aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
                        </div>
                        <p class="progress-message mt-2">Starting operation...</p>
                        <p class="progress-details text-muted small"></p>
                    </div>
                </div>
            `;

      // Add to document body
      document.body.appendChild(container);

      // Add event listener for close button
      const closeBtn = container.querySelector(".progress-close");
      if (closeBtn) {
        closeBtn.addEventListener("click", () => this.stopTracking());
      }
    }

    // Show the container
    container.style.display = "flex";

    // Set initial title based on operation type
    const titleElement = container.querySelector(".progress-title");
    if (titleElement) {
      titleElement.textContent =
        this.operationType === "llm"
          ? "Processing with AI..."
          : this.operationType === "ocr"
          ? "Extracting Text from Image..."
          : "Processing...";
    }
  }

  /**
   * Start polling for progress updates
   * @private
   */
  _startPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
    }

    // Immediately fetch the first update
    this._fetchProgress();

    // Then start polling at regular intervals
    this.pollTimer = setInterval(() => {
      if (this.isActive) {
        this._fetchProgress();
      } else {
        clearInterval(this.pollTimer);
        this.pollTimer = null;
      }
    }, this.pollInterval);
  }

  /**
   * Fetch progress from the API
   * @private
   */
  _fetchProgress() {
    if (!this.trackerId || !this.isActive) return;

    // Record the current time for adaptive polling
    this.lastPollTime = Date.now();

    fetch(`/api/progress/${this.trackerId}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        // Reset consecutive errors on success
        this.consecutiveErrors = 0;
        return response.json();
      })
      .then((data) => {
        this._updateProgressUI(data);

        // If operation is complete, stop polling
        if (data.completed) {
          if (data.success) {
            console.log("Operation completed successfully");
            setTimeout(() => {
              this.stopTracking();
              this.onComplete(data);
            }, 1500); // Show 100% for a moment before hiding
          } else {
            console.error("Operation failed:", data.error);
            this.onError(data);
            // Keep the error visible, don't auto-hide
          }
        }
        // If operation is taking a long time, update the UI to show it's still working
        else if (data.start_time && Date.now() / 1000 - data.start_time > 30) {
          // For operations taking more than 30 seconds
          const messageElement = document.querySelector(".progress-message");
          if (
            messageElement &&
            messageElement.textContent.indexOf("still working") === -1
          ) {
            messageElement.textContent += " (still working...)";
          }
        }
      })
      .catch((error) => {
        console.error("Error fetching progress:", error);
        this.consecutiveErrors++;

        // If we've had multiple consecutive errors, update the UI
        if (this.consecutiveErrors > 2) {
          const container = document.getElementById(this.containerId);
          if (container) {
            const messageElement = container.querySelector(".progress-message");
            if (messageElement) {
              messageElement.textContent = "Connection issues. Retrying...";
            }

            const detailsElement = container.querySelector(".progress-details");
            if (detailsElement) {
              detailsElement.textContent = `Retry attempt ${this.consecutiveErrors}/10. Will continue in background.`;
            }

            // Update progress bar to show warning
            const progressBar = container.querySelector(".progress-bar");
            if (progressBar) {
              progressBar.classList.remove(
                "bg-success",
                "bg-danger",
                "bg-info",
                "bg-primary"
              );
              progressBar.classList.add("bg-warning");
            }
          }
        }

        // Don't stop tracking on fetch error, might be temporary
        // But if we've had too many errors, stop tracking
        if (this.consecutiveErrors > 10) {
          console.error("Too many consecutive errors, stopping tracker");

          // Update UI to show error before stopping
          const container = document.getElementById(this.containerId);
          if (container) {
            const messageElement = container.querySelector(".progress-message");
            if (messageElement) {
              messageElement.textContent =
                "Operation failed: Connection lost. Please try again.";
              messageElement.classList.add("text-danger");
            }

            // Update progress bar to show error
            const progressBar = container.querySelector(".progress-bar");
            if (progressBar) {
              progressBar.classList.remove(
                "bg-success",
                "bg-warning",
                "bg-info",
                "bg-primary"
              );
              progressBar.classList.add("bg-danger");
            }
          }

          // Wait a moment before stopping so the user can see the error
          setTimeout(() => {
            this.stopTracking();
            this.onError({ error: "Connection lost. Please try again." });
          }, 3000);
        }
      });
  }

  /**
   * Update the progress UI with the latest data
   * @param {Object} data - Progress data from the API
   * @private
   */
  _updateProgressUI(data) {
    const container = document.getElementById(this.containerId);
    if (!container) return;

    // Update progress bar
    const progressBar = container.querySelector(".progress-bar");
    if (progressBar) {
      // Calculate a smoother progress percentage
      let percent = data.percent_complete || 0;

      // For LLM operations, ensure the progress bar shows continuous movement
      if (this.operationType === "llm") {
        const elapsedSeconds = Date.now() / 1000 - (data.start_time || 0);

        // If we're still processing after 2 seconds, show animated progress
        if (!data.completed && elapsedSeconds > 2) {
          // Store the last progress value to prevent oscillation
          if (!this.lastProgress) {
            this.lastProgress = percent;
          }

          // If the actual progress is >= 90%, use the actual progress
          if (percent >= 90) {
            // No need to modify percent, use the actual value
            console.log(`Using actual progress: ${percent}%`);
          } else {
            // Speed up progress until 90%
            let baseProgress;

            if (elapsedSeconds < 5) {
              // Fast initial progress (0-5 seconds): 0-30%
              baseProgress = Math.min(30, Math.max(5, elapsedSeconds * 6));
            } else if (elapsedSeconds < 10) {
              // Accelerate (5-10 seconds): 30-60%
              baseProgress = Math.min(60, 30 + (elapsedSeconds - 5) * 6);
            } else if (elapsedSeconds < 20) {
              // Continue acceleration (10-20 seconds): 60-80%
              baseProgress = Math.min(80, 60 + (elapsedSeconds - 10) * 2);
            } else if (elapsedSeconds < 30) {
              // Slow down as we approach 90% (20-30 seconds): 80-90%
              baseProgress = Math.min(90, 80 + (elapsedSeconds - 20));
            } else {
              // Hold at 90% until actual progress catches up
              baseProgress = 90;
            }

            // Ensure progress never goes backward and doesn't exceed 90% unless actual progress is higher
            percent = Math.max(this.lastProgress, baseProgress, percent);
          }

          // Save the current progress for next time
          this.lastProgress = percent;
        }
      } else {
        // For non-LLM operations, use similar progress estimation but with different timing
        const elapsedSeconds = data.start_time
          ? Date.now() / 1000 - data.start_time
          : 0;

        // If the actual progress is >= 90%, use the actual progress
        if (percent >= 90) {
          // No need to modify percent, use the actual value
        } else if (!data.completed && elapsedSeconds > 2) {
          // Store the last progress value to prevent oscillation
          if (!this.lastProgress) {
            this.lastProgress = percent;
          }

          // Calculate accelerated progress for non-LLM operations
          let baseProgress;

          if (elapsedSeconds < 3) {
            // Fast initial progress (0-3 seconds): 0-25%
            baseProgress = Math.min(25, Math.max(5, elapsedSeconds * 8));
          } else if (elapsedSeconds < 6) {
            // Accelerate (3-6 seconds): 25-50%
            baseProgress = Math.min(50, 25 + (elapsedSeconds - 3) * 8);
          } else if (elapsedSeconds < 10) {
            // Continue acceleration (6-10 seconds): 50-75%
            baseProgress = Math.min(75, 50 + (elapsedSeconds - 6) * 6);
          } else if (elapsedSeconds < 15) {
            // Slow down as we approach 90% (10-15 seconds): 75-90%
            baseProgress = Math.min(90, 75 + (elapsedSeconds - 10) * 3);
          } else {
            // Hold at 90% until actual progress catches up
            baseProgress = 90;
          }

          // Ensure progress never goes backward and doesn't exceed 90% unless actual progress is higher
          percent = Math.max(this.lastProgress, baseProgress, percent);

          // Save the current progress for next time
          this.lastProgress = percent;
        } else if (percent === 0 && data.status !== "initializing") {
          // If we're processing but still at 0%, show at least 5%
          percent = 5;
        }
      }

      // Log progress for debugging
      if (percent >= 90) {
        console.log(`Progress: ${Math.round(percent)}% (actual progress used)`);
      } else {
        console.log(`Progress: ${Math.round(percent)}% (accelerated progress)`);
      }

      progressBar.style.width = `${percent}%`;
      progressBar.setAttribute("aria-valuenow", percent);
      progressBar.textContent = `${Math.round(percent)}%`;

      // Update progress bar color based on status
      progressBar.classList.remove(
        "bg-success",
        "bg-danger",
        "bg-warning",
        "bg-info",
        "bg-primary"
      );

      if (data.completed) {
        if (data.success) {
          progressBar.classList.add("bg-success");
        } else {
          progressBar.classList.add("bg-danger");
        }
      } else if (data.status === "warning") {
        progressBar.classList.add("bg-warning");
      } else if (data.status === "processing" || data.status === "mapping") {
        progressBar.classList.add("bg-info");
      } else {
        progressBar.classList.add("bg-primary");
      }
    }

    // Update message
    const messageElement = container.querySelector(".progress-message");
    if (messageElement) {
      messageElement.textContent = data.message || "Processing...";
    }

    // Update details
    const detailsElement = container.querySelector(".progress-details");
    if (detailsElement) {
      let details = "";

      // Show more detailed status information
      if (
        data.status === "processing" ||
        data.status === "analyzing" ||
        data.status === "mapping" ||
        data.status === "extracting" ||
        data.status === "validating" ||
        data.status === "preparing"
      ) {
        if (data.current_step && data.total_steps) {
          details += `Step ${data.current_step}/${data.total_steps} | `;

          // Add estimated time if available
          if (data.estimated_completion_time) {
            const now = new Date().getTime() / 1000;
            const eta = data.estimated_completion_time - now;
            if (eta > 0) {
              const etaSeconds = Math.round(eta);
              details += `${
                etaSeconds > 60
                  ? Math.round(etaSeconds / 60) + " min"
                  : etaSeconds + " sec"
              } remaining | `;
            }
          }
        }

        // Add operation-specific details
        if (this.operationType === "llm") {
          details += "AI processing may take a minute or two | ";
        } else if (this.operationType === "ocr") {
          details += "Image processing in progress | ";
        }
      } else if (data.status === "warning") {
        details += `Warning: ${
          data.error || "Processing with reduced functionality"
        } | `;
      } else if (data.completed && !data.success && data.error) {
        details += `Error: ${data.error} | `;
      } else if (data.completed && data.success) {
        details += "Completed successfully! | ";
      }

      // Add start time
      if (data.start_time) {
        const startTime = new Date(data.start_time * 1000);
        details += `Started: ${startTime.toLocaleTimeString()} | `;
      }

      // Add status
      if (data.status) {
        details += `Status: ${
          data.status.charAt(0).toUpperCase() + data.status.slice(1)
        }`;
      }

      detailsElement.textContent = details;
    }

    // Update title based on completion status
    const titleElement = container.querySelector(".progress-title");
    if (titleElement && data.completed) {
      if (data.success) {
        titleElement.textContent = "Completed Successfully";
      } else {
        titleElement.textContent = "Operation Failed";
      }
    }
  }
}

// Create a global instance
const progressTracker = new ProgressTracker({
  onComplete: (data) => {
    // Reload the page if needed or show success message
    if (data.result && data.result.reload) {
      window.location.reload();
    }
  },
  onError: (data) => {
    // Show error message
    const errorMessage = data.error || "An unknown error occurred";

    // Don't show alert for connection errors, as they're already handled in the UI
    if (!errorMessage.includes("Connection lost")) {
      console.error(`Operation failed: ${errorMessage}`);

      // Only show alert for non-connection errors
      alert(`Operation failed: ${errorMessage}`);
    }
  },
});

// Export for global use
window.progressTracker = progressTracker;

// Initialize from localStorage if there's an active tracker
document.addEventListener("DOMContentLoaded", () => {
  const trackerId = localStorage.getItem("progressTracker_id");
  const operationType = localStorage.getItem("progressTracker_type");
  const isActive = localStorage.getItem("progressTracker_active") === "true";

  // Check if the tracker ID is stale by making a single request
  if (trackerId && operationType && isActive) {
    // First, check if the tracker is still valid
    fetch(`/api/progress/${trackerId}`)
      .then((response) => response.json())
      .then((data) => {
        // If the tracker is not found or has an error status, clear it
        if (data.status === "not_found" || data.status === "error") {
          console.log(`Clearing stale tracker ID: ${trackerId}`);
          localStorage.removeItem("progressTracker_id");
          localStorage.removeItem("progressTracker_type");
          localStorage.removeItem("progressTracker_active");
          return;
        }

        // If the tracker is completed, clear it
        if (data.completed) {
          console.log(`Clearing completed tracker ID: ${trackerId}`);
          localStorage.removeItem("progressTracker_id");
          localStorage.removeItem("progressTracker_type");
          localStorage.removeItem("progressTracker_active");
          return;
        }

        // Otherwise, resume tracking
        console.log(
          `Resuming progress tracking for ${operationType} operation: ${trackerId}`
        );
        progressTracker.startTracking(trackerId, operationType);
      })
      .catch((error) => {
        // If there's an error checking the tracker, clear it to be safe
        console.error(`Error checking tracker ${trackerId}:`, error);
        localStorage.removeItem("progressTracker_id");
        localStorage.removeItem("progressTracker_type");
        localStorage.removeItem("progressTracker_active");
      });
  }
});
