/**
 * Modern Responsive UI Components Library
 * Built on Tailwind CSS with accessibility and mobile-first design
 */

class UIComponents {
    constructor() {
        this.components = new Map();
        this.observers = new Map();
        this.init();
    }

    init() {
        this.setupGlobalStyles();
        this.initializeAccessibility();
        this.setupResponsiveObservers();
    }

    setupGlobalStyles() {
        // Inject additional component styles
        const style = document.createElement('style');
        style.textContent = `
            /* Component base styles */
            .ui-component {
                transition: all 0.2s ease-in-out;
            }
            
            .ui-component:focus-visible {
                outline: 2px solid #3b82f6;
                outline-offset: 2px;
            }
            
            /* Loading states */
            .ui-loading {
                position: relative;
                pointer-events: none;
            }
            
            .ui-loading::after {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 20px;
                height: 20px;
                margin: -10px 0 0 -10px;
                border: 2px solid #f3f4f6;
                border-top: 2px solid #3b82f6;
                border-radius: 50%;
                animation: ui-spin 1s linear infinite;
            }
            
            @keyframes ui-spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            /* Responsive utilities */
            @media (max-width: 640px) {
                .ui-mobile-stack {
                    flex-direction: column;
                }
                
                .ui-mobile-full {
                    width: 100%;
                }
                
                .ui-mobile-hidden {
                    display: none;
                }
            }
            
            @media (min-width: 768px) {
                .ui-tablet-show {
                    display: block;
                }
            }
            
            @media (min-width: 1024px) {
                .ui-desktop-grid {
                    display: grid;
                }
            }
        `;
        document.head.appendChild(style);
    }

    initializeAccessibility() {
        // Setup keyboard navigation
        document.addEventListener('keydown', this.handleKeyboardNavigation.bind(this));
        
        // Setup focus management
        this.setupFocusManagement();
        
        // Setup ARIA live regions
        this.setupLiveRegions();
    }

    setupResponsiveObservers() {
        // Intersection Observer for lazy loading
        this.intersectionObserver = new IntersectionObserver(
            this.handleIntersection.bind(this),
            { threshold: 0.1 }
        );
        
        // Resize Observer for responsive adjustments
        this.resizeObserver = new ResizeObserver(
            this.handleResize.bind(this)
        );
    }

    // Button Component
    createButton(options = {}) {
        const {
            text = 'Button',
            variant = 'primary',
            size = 'md',
            disabled = false,
            loading = false,
            icon = null,
            onClick = null,
            className = '',
            ariaLabel = null
        } = options;

        const button = document.createElement('button');
        button.className = this.getButtonClasses(variant, size, disabled, loading, className);
        button.disabled = disabled || loading;
        button.setAttribute('aria-label', ariaLabel || text);
        
        if (loading) {
            button.classList.add('ui-loading');
        }

        // Create button content
        const content = document.createElement('span');
        content.className = 'flex items-center justify-center';
        
        if (icon && !loading) {
            const iconElement = this.createIcon(icon);
            iconElement.className += ' mr-2 h-4 w-4';
            content.appendChild(iconElement);
        }
        
        const textElement = document.createElement('span');
        textElement.textContent = text;
        content.appendChild(textElement);
        
        button.appendChild(content);

        if (onClick) {
            button.addEventListener('click', onClick);
        }

        return button;
    }

    getButtonClasses(variant, size, disabled, loading, className) {
        const baseClasses = 'ui-component inline-flex items-center justify-center font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors';
        
        const variantClasses = {
            primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
            secondary: 'bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500',
            success: 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500',
            danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
            warning: 'bg-yellow-600 text-white hover:bg-yellow-700 focus:ring-yellow-500',
            outline: 'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 focus:ring-blue-500'
        };
        
        const sizeClasses = {
            sm: 'px-3 py-2 text-sm',
            md: 'px-4 py-2 text-sm',
            lg: 'px-6 py-3 text-base',
            xl: 'px-8 py-4 text-lg'
        };
        
        const disabledClasses = disabled || loading ? 'opacity-50 cursor-not-allowed' : '';
        
        return `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${disabledClasses} ${className}`.trim();
    }

    // Card Component
    createCard(options = {}) {
        const {
            title = null,
            content = '',
            footer = null,
            className = '',
            padding = 'md',
            shadow = 'md',
            hover = false
        } = options;

        const card = document.createElement('div');
        card.className = this.getCardClasses(padding, shadow, hover, className);

        if (title) {
            const header = document.createElement('div');
            header.className = 'px-6 py-4 border-b border-gray-200';
            
            const titleElement = document.createElement('h3');
            titleElement.className = 'text-lg font-medium text-gray-900';
            titleElement.textContent = title;
            
            header.appendChild(titleElement);
            card.appendChild(header);
        }

        const body = document.createElement('div');
        body.className = 'px-6 py-4';
        
        if (typeof content === 'string') {
            body.innerHTML = content;
        } else if (content instanceof HTMLElement) {
            body.appendChild(content);
        }
        
        card.appendChild(body);

        if (footer) {
            const footerElement = document.createElement('div');
            footerElement.className = 'px-6 py-4 border-t border-gray-200 bg-gray-50';
            
            if (typeof footer === 'string') {
                footerElement.innerHTML = footer;
            } else if (footer instanceof HTMLElement) {
                footerElement.appendChild(footer);
            }
            
            card.appendChild(footerElement);
        }

        return card;
    }

    getCardClasses(padding, shadow, hover, className) {
        const baseClasses = 'ui-component bg-white rounded-lg border border-gray-200';
        
        const shadowClasses = {
            none: '',
            sm: 'shadow-sm',
            md: 'shadow-md',
            lg: 'shadow-lg',
            xl: 'shadow-xl'
        };
        
        const hoverClasses = hover ? 'hover:shadow-lg hover:-translate-y-1' : '';
        
        return `${baseClasses} ${shadowClasses[shadow]} ${hoverClasses} ${className}`.trim();
    }

    // Modal Component
    createModal(options = {}) {
        const {
            title = 'Modal',
            content = '',
            size = 'md',
            closable = true,
            backdrop = true,
            onClose = null,
            className = ''
        } = options;

        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 z-50 overflow-y-auto';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-labelledby', 'modal-title');

        // Backdrop
        if (backdrop) {
            const backdropElement = document.createElement('div');
            backdropElement.className = 'fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity';
            
            if (closable) {
                backdropElement.addEventListener('click', () => this.closeModal(modal, onClose));
            }
            
            modal.appendChild(backdropElement);
        }

        // Modal container
        const container = document.createElement('div');
        container.className = 'flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0';

        // Modal panel
        const panel = document.createElement('div');
        panel.className = this.getModalClasses(size, className);

        // Header
        const header = document.createElement('div');
        header.className = 'flex items-center justify-between p-6 border-b border-gray-200';
        
        const titleElement = document.createElement('h3');
        titleElement.id = 'modal-title';
        titleElement.className = 'text-lg font-medium text-gray-900';
        titleElement.textContent = title;
        
        header.appendChild(titleElement);

        if (closable) {
            const closeButton = this.createButton({
                text: '×',
                variant: 'outline',
                size: 'sm',
                className: 'ml-4 text-gray-400 hover:text-gray-600',
                onClick: () => this.closeModal(modal, onClose)
            });
            header.appendChild(closeButton);
        }

        panel.appendChild(header);

        // Content
        const contentElement = document.createElement('div');
        contentElement.className = 'p-6';
        
        if (typeof content === 'string') {
            contentElement.innerHTML = content;
        } else if (content instanceof HTMLElement) {
            contentElement.appendChild(content);
        }
        
        panel.appendChild(contentElement);
        container.appendChild(panel);
        modal.appendChild(container);

        // Setup keyboard handling
        modal.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && closable) {
                this.closeModal(modal, onClose);
            }
        });

        return modal;
    }

    getModalClasses(size, className) {
        const baseClasses = 'relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all';
        
        const sizeClasses = {
            sm: 'sm:max-w-sm sm:w-full',
            md: 'sm:max-w-lg sm:w-full',
            lg: 'sm:max-w-2xl sm:w-full',
            xl: 'sm:max-w-4xl sm:w-full',
            full: 'sm:max-w-7xl sm:w-full'
        };
        
        return `${baseClasses} ${sizeClasses[size]} ${className}`.trim();
    }

    closeModal(modal, onClose) {
        modal.classList.add('opacity-0');
        setTimeout(() => {
            modal.remove();
            if (onClose) onClose();
        }, 200);
    }

    // Progress Indicator Component
    createProgressIndicator(options = {}) {
        const {
            value = 0,
            max = 100,
            size = 'md',
            variant = 'primary',
            showLabel = true,
            animated = false,
            className = ''
        } = options;

        const container = document.createElement('div');
        container.className = `ui-component ${className}`;

        if (showLabel) {
            const label = document.createElement('div');
            label.className = 'flex justify-between text-sm font-medium text-gray-700 mb-2';
            
            const labelText = document.createElement('span');
            labelText.textContent = 'Progress';
            
            const percentage = document.createElement('span');
            percentage.textContent = `${Math.round((value / max) * 100)}%`;
            
            label.appendChild(labelText);
            label.appendChild(percentage);
            container.appendChild(label);
        }

        const progressBar = document.createElement('div');
        progressBar.className = this.getProgressClasses(size, variant, animated);
        progressBar.setAttribute('role', 'progressbar');
        progressBar.setAttribute('aria-valuenow', value);
        progressBar.setAttribute('aria-valuemin', '0');
        progressBar.setAttribute('aria-valuemax', max);

        const fill = document.createElement('div');
        fill.className = 'h-full rounded-full transition-all duration-300';
        fill.style.width = `${(value / max) * 100}%`;
        
        const variantColors = {
            primary: 'bg-blue-600',
            success: 'bg-green-600',
            warning: 'bg-yellow-600',
            danger: 'bg-red-600'
        };
        
        fill.className += ` ${variantColors[variant]}`;
        
        progressBar.appendChild(fill);
        container.appendChild(progressBar);

        return container;
    }

    getProgressClasses(size, variant, animated) {
        const baseClasses = 'w-full bg-gray-200 rounded-full overflow-hidden';
        
        const sizeClasses = {
            sm: 'h-2',
            md: 'h-3',
            lg: 'h-4',
            xl: 'h-6'
        };
        
        const animatedClasses = animated ? 'animate-pulse' : '';
        
        return `${baseClasses} ${sizeClasses[size]} ${animatedClasses}`.trim();
    }

    // Alert Component
    createAlert(options = {}) {
        const {
            message = '',
            variant = 'info',
            dismissible = true,
            icon = true,
            className = '',
            onDismiss = null
        } = options;

        const alert = document.createElement('div');
        alert.className = this.getAlertClasses(variant, className);
        alert.setAttribute('role', 'alert');

        const content = document.createElement('div');
        content.className = 'flex';

        if (icon) {
            const iconElement = this.createAlertIcon(variant);
            iconElement.className += ' flex-shrink-0 mr-3';
            content.appendChild(iconElement);
        }

        const messageElement = document.createElement('div');
        messageElement.className = 'flex-1';
        messageElement.innerHTML = message;
        content.appendChild(messageElement);

        if (dismissible) {
            const dismissButton = document.createElement('button');
            dismissButton.className = 'flex-shrink-0 ml-3 text-current opacity-70 hover:opacity-100';
            dismissButton.innerHTML = '×';
            dismissButton.addEventListener('click', () => {
                alert.remove();
                if (onDismiss) onDismiss();
            });
            content.appendChild(dismissButton);
        }

        alert.appendChild(content);
        return alert;
    }

    getAlertClasses(variant, className) {
        const baseClasses = 'ui-component p-4 rounded-md';
        
        const variantClasses = {
            info: 'bg-blue-50 text-blue-800 border border-blue-200',
            success: 'bg-green-50 text-green-800 border border-green-200',
            warning: 'bg-yellow-50 text-yellow-800 border border-yellow-200',
            danger: 'bg-red-50 text-red-800 border border-red-200'
        };
        
        return `${baseClasses} ${variantClasses[variant]} ${className}`.trim();
    }

    createAlertIcon(variant) {
        const icon = document.createElement('div');
        icon.className = 'h-5 w-5';
        
        const iconPaths = {
            info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
            success: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
            warning: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z',
            danger: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z'
        };
        
        icon.innerHTML = `
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${iconPaths[variant]}"/>
            </svg>
        `;
        
        return icon;
    }

    // Icon helper
    createIcon(name) {
        const icon = document.createElement('div');
        icon.className = 'inline-block';
        
        // Basic icon set - can be extended
        const icons = {
            upload: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12',
            download: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4',
            check: 'M5 13l4 4L19 7',
            x: 'M6 18L18 6M6 6l12 12',
            plus: 'M12 6v6m0 0v6m0-6h6m-6 0H6'
        };
        
        if (icons[name]) {
            icon.innerHTML = `
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${icons[name]}"/>
                </svg>
            `;
        }
        
        return icon;
    }

    // Utility methods
    handleKeyboardNavigation(event) {
        // Implement keyboard navigation for components
        if (event.key === 'Tab') {
            this.manageFocus(event);
        }
    }

    setupFocusManagement() {
        // Setup focus trap for modals and other components
        this.focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    }

    setupLiveRegions() {
        // Create ARIA live regions for announcements
        if (!document.getElementById('ui-live-region')) {
            const liveRegion = document.createElement('div');
            liveRegion.id = 'ui-live-region';
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.setAttribute('aria-atomic', 'true');
            liveRegion.className = 'sr-only';
            document.body.appendChild(liveRegion);
        }
    }

    announce(message) {
        const liveRegion = document.getElementById('ui-live-region');
        if (liveRegion) {
            liveRegion.textContent = message;
        }
    }

    handleIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Handle lazy loading or animations
                entry.target.classList.add('ui-visible');
            }
        });
    }

    handleResize(entries) {
        entries.forEach(entry => {
            // Handle responsive adjustments
            const element = entry.target;
            const width = entry.contentRect.width;
            
            // Apply responsive classes based on width
            if (width < 640) {
                element.classList.add('ui-mobile');
                element.classList.remove('ui-tablet', 'ui-desktop');
            } else if (width < 1024) {
                element.classList.add('ui-tablet');
                element.classList.remove('ui-mobile', 'ui-desktop');
            } else {
                element.classList.add('ui-desktop');
                element.classList.remove('ui-mobile', 'ui-tablet');
            }
        });
    }

    // Component registration and management
    registerComponent(name, element) {
        this.components.set(name, element);
        
        // Setup observers
        this.intersectionObserver.observe(element);
        this.resizeObserver.observe(element);
    }

    getComponent(name) {
        return this.components.get(name);
    }

    destroyComponent(name) {
        const component = this.components.get(name);
        if (component) {
            this.intersectionObserver.unobserve(component);
            this.resizeObserver.unobserve(component);
            this.components.delete(name);
        }
    }

    // Cleanup
    destroy() {
        this.intersectionObserver.disconnect();
        this.resizeObserver.disconnect();
        this.components.clear();
    }
}

// Export class globally
window.UIComponents = UIComponents;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UIComponents;
}