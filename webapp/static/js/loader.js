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
     * @param {boolean} options.showProgress - Whether to show a progress bar
     */
    constructor(options = {}) {
        this.type = options.type || 'spinner';
        this.text = options.text || 'Processing...';
        this.subText = options.subText || 'This may take a moment';
        this.showProgress = options.showProgress || false;
        this.progress = 0;
        this.overlayId = 'loader-overlay-' + Math.random().toString(36).substr(2, 9);
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
        const overlay = document.createElement('div');
        overlay.id = this.overlayId;
        overlay.className = 'loader-overlay';

        // Create loader card
        const loaderCard = document.createElement('div');
        loaderCard.className = 'loader-card';

        // Create loader based on type
        const loader = document.createElement('div');
        loader.className = `${this.type}-loader`;

        // Add loader elements based on type
        if (this.type === 'spinner') {
            // Spinner loader doesn't need child elements
        } else if (this.type === 'pulse') {
            loader.appendChild(document.createElement('div'));
            loader.appendChild(document.createElement('div'));
        } else if (this.type === 'dots') {
            for (let i = 0; i < 4; i++) {
                loader.appendChild(document.createElement('div'));
            }
        }

        // Create text elements
        const textElement = document.createElement('h5');
        textElement.className = 'loader-text';
        textElement.textContent = this.text;

        const subTextElement = document.createElement('p');
        subTextElement.className = 'loader-subtext';
        subTextElement.textContent = this.subText;

        // Add elements to card
        loaderCard.appendChild(loader);
        loaderCard.appendChild(textElement);
        loaderCard.appendChild(subTextElement);

        // Add progress bar if needed
        if (this.showProgress) {
            const progressContainer = document.createElement('div');
            progressContainer.className = 'loader-progress';

            const progressBar = document.createElement('div');
            progressBar.className = 'progress';

            const progressBarInner = document.createElement('div');
            progressBarInner.className = 'progress-bar';
            progressBarInner.style.width = '0%';
            progressBarInner.setAttribute('role', 'progressbar');
            progressBarInner.setAttribute('aria-valuenow', '0');
            progressBarInner.setAttribute('aria-valuemin', '0');
            progressBarInner.setAttribute('aria-valuemax', '100');

            const progressText = document.createElement('div');
            progressText.className = 'loader-progress-text';
            progressText.textContent = '0%';

            progressBar.appendChild(progressBarInner);
            progressContainer.appendChild(progressBar);
            progressContainer.appendChild(progressText);
            loaderCard.appendChild(progressContainer);
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
            overlay.classList.add('active');
            this.isActive = true;
        }
    }

    /**
     * Hide the loader
     */
    hide() {
        const overlay = document.getElementById(this.overlayId);
        if (overlay) {
            overlay.classList.remove('active');
            this.isActive = false;
        }
    }

    /**
     * Update the loader text
     * @param {string} text - New text to display
     * @param {string} subText - New subtext to display
     */
    updateText(text, subText = null) {
        const overlay = document.getElementById(this.overlayId);
        if (overlay) {
            const textElement = overlay.querySelector('.loader-text');
            if (textElement && text) {
                textElement.textContent = text;
            }

            if (subText) {
                const subTextElement = overlay.querySelector('.loader-subtext');
                if (subTextElement) {
                    subTextElement.textContent = subText;
                }
            }
        }
    }

    /**
     * Update the progress bar
     * @param {number} progress - Progress value (0-100)
     */
    updateProgress(progress) {
        if (!this.showProgress) return;

        const overlay = document.getElementById(this.overlayId);
        if (overlay) {
            const progressBar = overlay.querySelector('.progress-bar');
            const progressText = overlay.querySelector('.loader-progress-text');

            if (progressBar && progressText) {
                // Ensure progress is between 0 and 100
                this.progress = Math.max(0, Math.min(100, progress));
                
                // Update progress bar
                progressBar.style.width = `${this.progress}%`;
                progressBar.setAttribute('aria-valuenow', this.progress);
                
                // Update progress text
                progressText.textContent = `${Math.round(this.progress)}%`;
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
        button.classList.add('btn-loader', 'loading');
        
        // Add loader element
        const loader = document.createElement('span');
        loader.className = 'inline-loader';
        button.appendChild(loader);
        
        // Disable button
        button.disabled = true;
    } else {
        // Remove loader class
        button.classList.remove('btn-loader', 'loading');
        
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
    type: 'spinner',
    text: 'Processing...',
    subText: 'This may take a moment',
    showProgress: false
});

// Export for global use
window.Loader = Loader;
window.globalLoader = globalLoader;
window.toggleButtonLoader = toggleButtonLoader;
