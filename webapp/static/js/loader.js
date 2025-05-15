/**
 * Loader Module
 *
 * This module provides functionality for showing and hiding loaders
 * during long-running operations.
 */

class Loader {
  /**
   * Initialize the loader
   * @param {Object} options - Configuration options
   * @param {string} options.type - Type of loader ('spinner', 'pulse', 'dots')
   * @param {string} options.text - Text to display in the loader
   * @param {string} options.subText - Subtext to display in the loader
   * @param {string} options.statusText - Additional status text to display (optional)
   */
  constructor(options = {}) {
    this.type = options.type || "spinner";
    this.text = options.text || "Processing...";
    this.subText = options.subText || "This may take a moment";
    this.statusText = options.statusText || "";
    this.overlayId =
      "loader-overlay-" + Math.random().toString(36).substr(2, 9);
    this.isActive = false;
    this.createOverlay();
  }

  /**
   * Create the loader overlay
   * @private
   */
  createOverlay() {
    // Check if overlay already exists
    if (document.getElementById(this.overlayId)) {
      return;
    }

    // Create overlay element
    const overlay = document.createElement("div");
    overlay.id = this.overlayId;
    overlay.className = "loader-overlay";

    // Create loader card
    const loaderCard = document.createElement("div");
    loaderCard.className = "loader-card";

    // Create loader based on type
    const loader = document.createElement("div");
    loader.className = `${this.type}-loader`;

    // Add loader elements based on type
    if (this.type === "spinner") {
      // Spinner loader doesn't need child elements
    } else if (this.type === "pulse") {
      loader.appendChild(document.createElement("div"));
      loader.appendChild(document.createElement("div"));
    } else if (this.type === "dots") {
      for (let i = 0; i < 4; i++) {
        loader.appendChild(document.createElement("div"));
      }
    }

    // Create text elements
    const textElement = document.createElement("h5");
    textElement.className = "loader-text";
    textElement.textContent = this.text;

    const subTextElement = document.createElement("p");
    subTextElement.className = "loader-subtext";
    subTextElement.textContent = this.subText;

    // Add elements to card
    loaderCard.appendChild(loader);
    loaderCard.appendChild(textElement);
    loaderCard.appendChild(subTextElement);

    // Add status text if provided
    if (this.statusText) {
      const statusContainer = document.createElement("div");
      statusContainer.className = "loader-status mt-3";

      const statusText = document.createElement("div");
      statusText.className = "loader-status-text";
      statusText.textContent = this.statusText;

      statusContainer.appendChild(statusText);
      loaderCard.appendChild(statusContainer);
    }

    // Add card to overlay
    overlay.appendChild(loaderCard);

    // Add overlay to body
    document.body.appendChild(overlay);
  }

  /**
   * Show the loader
   */
  show() {
    const overlay = document.getElementById(this.overlayId);
    if (overlay) {
      overlay.classList.add("active");
      this.isActive = true;
    }
  }

  /**
   * Hide the loader
   */
  hide() {
    const overlay = document.getElementById(this.overlayId);
    if (overlay) {
      overlay.classList.remove("active");
      this.isActive = false;
    }
  }

  /**
   * Update the loader text
   * @param {string} text - New text to display
   * @param {string} subText - New subtext to display
   * @param {string} statusText - New status text to display (optional)
   */
  updateText(text, subText = null, statusText = null) {
    const overlay = document.getElementById(this.overlayId);
    if (overlay) {
      const textElement = overlay.querySelector(".loader-text");
      if (textElement && text) {
        textElement.textContent = text;
      }

      if (subText) {
        const subTextElement = overlay.querySelector(".loader-subtext");
        if (subTextElement) {
          subTextElement.textContent = subText;
        }
      }

      // Update status text if provided
      if (statusText !== null) {
        this.updateStatus(statusText);
      }
    }
  }

  /**
   * Update the status text
   * @param {string} statusText - New status text to display
   */
  updateStatus(statusText) {
    this.statusText = statusText || "";

    const overlay = document.getElementById(this.overlayId);
    if (overlay) {
      let statusElement = overlay.querySelector(".loader-status-text");

      if (statusElement) {
        // Update existing status text
        statusElement.textContent = this.statusText;
      } else if (this.statusText) {
        // Create new status element if it doesn't exist
        const statusContainer = document.createElement("div");
        statusContainer.className = "loader-status mt-3";

        statusElement = document.createElement("div");
        statusElement.className = "loader-status-text";
        statusElement.textContent = this.statusText;

        statusContainer.appendChild(statusElement);

        // Add to loader card
        const loaderCard = overlay.querySelector(".loader-card");
        if (loaderCard) {
          loaderCard.appendChild(statusContainer);
        }
      }
    }
  }

  /**
   * Remove the loader from the DOM
   */
  destroy() {
    const overlay = document.getElementById(this.overlayId);
    if (overlay) {
      document.body.removeChild(overlay);
    }
  }
}

/**
 * Add loader to a button
 * @param {HTMLElement} button - Button element to add loader to
 * @param {boolean} state - Whether to show or hide the loader
 */
function toggleButtonLoader(button, state) {
  if (!button) return;

  if (state) {
    // Save original text
    button.dataset.originalText = button.innerHTML;

    // Add loader class
    button.classList.add("btn-loader", "loading");

    // Add loader element
    const loader = document.createElement("span");
    loader.className = "inline-loader";
    button.appendChild(loader);

    // Disable button
    button.disabled = true;
  } else {
    // Remove loader class
    button.classList.remove("btn-loader", "loading");

    // Restore original text
    if (button.dataset.originalText) {
      button.innerHTML = button.dataset.originalText;
    }

    // Enable button
    button.disabled = false;
  }
}

// Create a global loader instance
const globalLoader = new Loader({
  type: "spinner",
  text: "Processing...",
  subText: "This may take a moment",
  statusText: "Please wait while we process your request",
});

/**
 * Hide all active loaders
 * This is useful when navigating between pages to ensure no loaders are left visible
 */
function hideAllLoaders() {
  // Find all loader overlays in the DOM
  const loaderOverlays = document.querySelectorAll('[id^="loader-overlay-"]');

  // Hide each one
  loaderOverlays.forEach((overlay) => {
    overlay.classList.remove("active");
  });

  // Also hide the global loader
  if (globalLoader && globalLoader.isActive) {
    globalLoader.hide();
  }

  console.log(`Cleaned up ${loaderOverlays.length} active loaders`);
}

// Export for global use
window.Loader = Loader;
window.globalLoader = globalLoader;
window.toggleButtonLoader = toggleButtonLoader;
window.hideAllLoaders = hideAllLoaders;

// Automatically hide all loaders when the page loads
// This prevents loaders from persisting across page navigations
document.addEventListener("DOMContentLoaded", function () {
  // Small delay to ensure the DOM is fully loaded
  setTimeout(hideAllLoaders, 100);
});
