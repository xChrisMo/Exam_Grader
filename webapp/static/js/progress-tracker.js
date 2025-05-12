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
        if (this.consecutiveErrors > 3) {
          const container = document.getElementById(this.containerId);
          if (container) {
            const detailsElement = container.querySelector(".progress-details");
            if (detailsElement) {
              detailsElement.textContent = "Connection issues. Retrying...";
            }
          }
        }

        // Don't stop tracking on fetch error, might be temporary
        // But if we've had too many errors, stop tracking
        if (this.consecutiveErrors > 10) {
          console.error("Too many consecutive errors, stopping tracker");
          this.stopTracking();
          this.onError({ error: "Connection lost. Please try again." });
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

        // If we're still processing after 3 seconds, show animated progress
        if (!data.completed && elapsedSeconds > 3) {
          // Calculate a progress that increases over time but never reaches 100%
          // This creates an illusion of progress for long-running LLM operations

          // Store the last progress value to prevent oscillation
          if (!this.lastProgress) {
            this.lastProgress = percent;
          }

          // Calculate base progress that increases logarithmically with time
          let baseProgress;

          if (elapsedSeconds < 10) {
            // Start slower (0-10 seconds)
            baseProgress = Math.min(
              50,
              Math.max(5, Math.log(elapsedSeconds * 3) * 15)
            );
          } else if (elapsedSeconds < 30) {
            // Medium speed (10-30 seconds)
            baseProgress = Math.min(75, 50 + ((elapsedSeconds - 10) / 20) * 25);
          } else {
            // Slower approach to 95% (after 30 seconds)
            baseProgress = Math.min(95, 75 + Math.log(elapsedSeconds - 29) * 5);
          }

          // Ensure progress never goes backward
          percent = Math.max(this.lastProgress, baseProgress, percent);

          // Save the current progress for next time
          this.lastProgress = percent;
        }
      } else {
        // For non-LLM operations, use simpler progress estimation
        // For long-running operations, ensure the progress bar shows movement
        if (
          percent < 10 &&
          data.start_time &&
          Date.now() / 1000 - data.start_time > 5
        ) {
          // If more than 5 seconds have passed, show at least 10% progress
          percent = Math.max(percent, 10);
        }

        // If we're processing but still at 0%, show at least 5%
        if (percent === 0 && data.status !== "initializing") {
          percent = 5;
        }
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
    alert(`Operation failed: ${errorMessage}`);
  },
});

// Export for global use
window.progressTracker = progressTracker;

// Initialize from localStorage if there's an active tracker
document.addEventListener("DOMContentLoaded", () => {
  const trackerId = localStorage.getItem("progressTracker_id");
  const operationType = localStorage.getItem("progressTracker_type");
  const isActive = localStorage.getItem("progressTracker_active") === "true";

  if (trackerId && operationType && isActive) {
    console.log(
      `Resuming progress tracking for ${operationType} operation: ${trackerId}`
    );
    progressTracker.startTracking(trackerId, operationType);
  }
});
