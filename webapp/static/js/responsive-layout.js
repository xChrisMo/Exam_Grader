/**
 * Responsive Layout System
 * Provides comprehensive responsive layout management with breakpoint handling,
 * component coordination, and adaptive UI behaviors
 */

class ResponsiveLayout {
    constructor(options = {}) {
        this.options = {
            breakpoints: {
                xs: 0,
                sm: 640,
                md: 768,
                lg: 1024,
                xl: 1280,
                '2xl': 1536
            },
            debounceDelay: 150,
            enableTouchGestures: true,
            enableKeyboardNavigation: true,
            enableAccessibility: true,
            ...options
        };
        
        this.currentBreakpoint = null;
        this.components = new Map();
        this.observers = new Map();
        this.touchStartX = 0;
        this.touchStartY = 0;
        
        this.init();
    }
    
    init() {
        this.setupStyles();
        this.detectBreakpoint();
        this.bindEvents();
        this.setupObservers();
        this.initializeComponents();
        
        if (this.options.enableAccessibility) {
            this.setupAccessibility();
        }
        
        if (this.options.enableTouchGestures) {
            this.setupTouchGestures();
        }
    }
    
    setupStyles() {
        const styles = `
            /* Responsive Layout System Styles */
            .responsive-container {
                @apply w-full mx-auto px-4 sm:px-6 lg:px-8;
            }
            
            .responsive-container.max-sm {
                @apply max-w-sm;
            }
            
            .responsive-container.max-md {
                @apply max-w-md;
            }
            
            .responsive-container.max-lg {
                @apply max-w-lg;
            }
            
            .responsive-container.max-xl {
                @apply max-w-xl;
            }
            
            .responsive-container.max-2xl {
                @apply max-w-2xl;
            }
            
            .responsive-container.max-4xl {
                @apply max-w-4xl;
            }
            
            .responsive-container.max-6xl {
                @apply max-w-6xl;
            }
            
            .responsive-container.max-7xl {
                @apply max-w-7xl;
            }
            
            .responsive-grid {
                @apply grid gap-4;
            }
            
            .responsive-grid.cols-1 {
                @apply grid-cols-1;
            }
            
            .responsive-grid.cols-2 {
                @apply grid-cols-1 md:grid-cols-2;
            }
            
            .responsive-grid.cols-3 {
                @apply grid-cols-1 md:grid-cols-2 lg:grid-cols-3;
            }
            
            .responsive-grid.cols-4 {
                @apply grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4;
            }
            
            .responsive-grid.cols-6 {
                @apply grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6;
            }
            
            .responsive-flex {
                @apply flex flex-col sm:flex-row;
            }
            
            .responsive-flex.reverse {
                @apply flex-col-reverse sm:flex-row;
            }
            
            .responsive-flex.center {
                @apply items-center justify-center;
            }
            
            .responsive-flex.between {
                @apply justify-between;
            }
            
            .responsive-flex.around {
                @apply justify-around;
            }
            
            .responsive-flex.evenly {
                @apply justify-evenly;
            }
            
            .responsive-stack {
                @apply space-y-4 sm:space-y-0 sm:space-x-4;
            }
            
            .responsive-sidebar {
                @apply w-full lg:w-64 lg:flex-shrink-0;
            }
            
            .responsive-main {
                @apply flex-1 min-w-0;
            }
            
            .responsive-card {
                @apply bg-white rounded-lg shadow-sm border border-gray-200 p-4 sm:p-6;
            }
            
            .responsive-card.compact {
                @apply p-3 sm:p-4;
            }
            
            .responsive-card.spacious {
                @apply p-6 sm:p-8;
            }
            
            .responsive-text {
                @apply text-sm sm:text-base;
            }
            
            .responsive-text.large {
                @apply text-base sm:text-lg;
            }
            
            .responsive-text.small {
                @apply text-xs sm:text-sm;
            }
            
            .responsive-heading {
                @apply text-lg sm:text-xl lg:text-2xl font-bold;
            }
            
            .responsive-heading.large {
                @apply text-xl sm:text-2xl lg:text-3xl xl:text-4xl;
            }
            
            .responsive-heading.small {
                @apply text-base sm:text-lg lg:text-xl;
            }
            
            .responsive-button {
                @apply px-3 py-2 sm:px-4 sm:py-2 text-sm sm:text-base;
            }
            
            .responsive-button.large {
                @apply px-4 py-3 sm:px-6 sm:py-3 text-base sm:text-lg;
            }
            
            .responsive-button.small {
                @apply px-2 py-1 sm:px-3 sm:py-2 text-xs sm:text-sm;
            }
            
            .responsive-input {
                @apply px-3 py-2 text-base sm:text-sm;
            }
            
            .responsive-spacing {
                @apply space-y-4 sm:space-y-6;
            }
            
            .responsive-spacing.tight {
                @apply space-y-2 sm:space-y-4;
            }
            
            .responsive-spacing.loose {
                @apply space-y-6 sm:space-y-8;
            }
            
            .responsive-padding {
                @apply p-4 sm:p-6 lg:p-8;
            }
            
            .responsive-padding.tight {
                @apply p-2 sm:p-4 lg:p-6;
            }
            
            .responsive-padding.loose {
                @apply p-6 sm:p-8 lg:p-12;
            }
            
            .responsive-margin {
                @apply m-4 sm:m-6 lg:m-8;
            }
            
            .responsive-margin.tight {
                @apply m-2 sm:m-4 lg:m-6;
            }
            
            .responsive-margin.loose {
                @apply m-6 sm:m-8 lg:m-12;
            }
            
            /* Mobile-first utilities */
            .mobile-only {
                @apply block sm:hidden;
            }
            
            .tablet-only {
                @apply hidden sm:block lg:hidden;
            }
            
            .desktop-only {
                @apply hidden lg:block;
            }
            
            .mobile-tablet {
                @apply block lg:hidden;
            }
            
            .tablet-desktop {
                @apply hidden sm:block;
            }
            
            /* Touch-friendly elements */
            .touch-target {
                @apply min-h-[44px] min-w-[44px] flex items-center justify-center;
            }
            
            .touch-friendly {
                @apply p-3 sm:p-2;
            }
            
            /* Responsive tables */
            .responsive-table {
                @apply w-full overflow-x-auto;
            }
            
            .responsive-table table {
                @apply min-w-full;
            }
            
            .responsive-table th,
            .responsive-table td {
                @apply px-2 py-3 sm:px-4 text-sm;
            }
            
            /* Responsive images */
            .responsive-image {
                @apply w-full h-auto max-w-full;
            }
            
            .responsive-avatar {
                @apply w-8 h-8 sm:w-10 sm:h-10 lg:w-12 lg:h-12 rounded-full;
            }
            
            /* Layout transitions */
            .layout-transition {
                @apply transition-all duration-300 ease-in-out;
            }
            
            /* Responsive modals */
            .responsive-modal {
                @apply w-full max-w-sm sm:max-w-md lg:max-w-lg xl:max-w-xl;
                @apply mx-4 sm:mx-auto;
            }
            
            .responsive-modal.large {
                @apply max-w-md sm:max-w-lg lg:max-w-2xl xl:max-w-4xl;
            }
            
            .responsive-modal.small {
                @apply max-w-xs sm:max-w-sm lg:max-w-md;
            }
            
            /* Responsive navigation */
            .responsive-nav {
                @apply flex flex-col sm:flex-row sm:items-center sm:space-x-4;
            }
            
            .responsive-nav-item {
                @apply block py-2 sm:py-0;
            }
            
            /* Print styles */
            @media print {
                .responsive-container {
                    @apply max-w-none px-0;
                }
                
                .responsive-grid {
                    @apply grid-cols-1;
                }
                
                .mobile-only,
                .tablet-only,
                .desktop-only {
                    @apply block;
                }
                
                .responsive-button {
                    @apply border border-gray-400;
                }
            }
            
            /* High contrast mode */
            @media (prefers-contrast: high) {
                .responsive-card {
                    @apply border-2 border-gray-900;
                }
                
                .responsive-button {
                    @apply border-2;
                }
            }
            
            /* Reduced motion */
            @media (prefers-reduced-motion: reduce) {
                .layout-transition {
                    @apply transition-none;
                }
            }
            
            /* Dark mode support */
            @media (prefers-color-scheme: dark) {
                .responsive-card {
                    @apply bg-gray-800 border-gray-700;
                }
            }
        `;
        
        this.injectStyles(styles);
    }
    
    injectStyles(styles) {
        const styleSheet = document.createElement('style');
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
    }
    
    detectBreakpoint() {
        const width = window.innerWidth;
        let newBreakpoint = 'xs';
        
        for (const [name, minWidth] of Object.entries(this.options.breakpoints)) {
            if (width >= minWidth) {
                newBreakpoint = name;
            }
        }
        
        if (newBreakpoint !== this.currentBreakpoint) {
            const previousBreakpoint = this.currentBreakpoint;
            this.currentBreakpoint = newBreakpoint;
            
            this.onBreakpointChange(newBreakpoint, previousBreakpoint);
        }
        
        return newBreakpoint;
    }
    
    onBreakpointChange(current, previous) {
        // Update body class
        document.body.className = document.body.className
            .replace(/\bbreakpoint-\w+\b/g, '')
            .trim();
        document.body.classList.add(`breakpoint-${current}`);
        
        // Emit breakpoint change event
        document.dispatchEvent(new CustomEvent('layout:breakpoint-change', {
            detail: { current, previous, width: window.innerWidth }
        }));
        
        // Update components
        this.updateComponents(current, previous);
        
        // Handle specific breakpoint behaviors
        this.handleBreakpointBehaviors(current, previous);
    }
    
    bindEvents() {
        // Debounced resize handler
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.detectBreakpoint();
                this.updateLayout();
            }, this.options.debounceDelay);
        });
        
        // Orientation change
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.detectBreakpoint();
                this.updateLayout();
            }, 100);
        });
        
        // Keyboard navigation
        if (this.options.enableKeyboardNavigation) {
            document.addEventListener('keydown', (e) => {
                this.handleKeyboardNavigation(e);
            });
        }
        
        // Focus management
        document.addEventListener('focusin', (e) => {
            this.handleFocusManagement(e);
        });
    }
    
    setupObservers() {
        // Intersection Observer for lazy loading and animations
        if ('IntersectionObserver' in window) {
            this.intersectionObserver = new IntersectionObserver(
                (entries) => this.handleIntersection(entries),
                {
                    rootMargin: '50px',
                    threshold: [0, 0.25, 0.5, 0.75, 1]
                }
            );
        }
        
        // Resize Observer for component-specific resize handling
        if ('ResizeObserver' in window) {
            this.resizeObserver = new ResizeObserver(
                (entries) => this.handleResize(entries)
            );
        }
    }
    
    setupAccessibility() {
        // Add skip links
        this.addSkipLinks();
        
        // Enhance focus indicators
        this.enhanceFocusIndicators();
        
        // Add ARIA landmarks
        this.addAriaLandmarks();
        
        // Handle reduced motion preferences
        this.handleReducedMotion();
    }
    
    setupTouchGestures() {
        document.addEventListener('touchstart', (e) => {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
        }, { passive: true });
        
        document.addEventListener('touchend', (e) => {
            if (!e.changedTouches[0]) return;
            
            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;
            
            const deltaX = touchEndX - this.touchStartX;
            const deltaY = touchEndY - this.touchStartY;
            
            this.handleSwipeGesture(deltaX, deltaY, e);
        }, { passive: true });
    }
    
    initializeComponents() {
        // Auto-detect and initialize responsive components
        this.initializeResponsiveContainers();
        this.initializeResponsiveGrids();
        this.initializeResponsiveTables();
        this.initializeResponsiveImages();
    }
    
    initializeResponsiveContainers() {
        const containers = document.querySelectorAll('.responsive-container');
        containers.forEach(container => {
            this.observeElement(container, 'container');
        });
    }
    
    initializeResponsiveGrids() {
        const grids = document.querySelectorAll('.responsive-grid');
        grids.forEach(grid => {
            this.observeElement(grid, 'grid');
            this.optimizeGridLayout(grid);
        });
    }
    
    initializeResponsiveTables() {
        const tables = document.querySelectorAll('.responsive-table');
        tables.forEach(table => {
            this.enhanceTableResponsiveness(table);
        });
    }
    
    initializeResponsiveImages() {
        const images = document.querySelectorAll('.responsive-image');
        images.forEach(img => {
            this.optimizeImageLoading(img);
        });
    }
    
    observeElement(element, type) {
        if (this.intersectionObserver) {
            this.intersectionObserver.observe(element);
        }
        
        if (this.resizeObserver) {
            this.resizeObserver.observe(element);
        }
        
        element.setAttribute('data-responsive-type', type);
    }
    
    optimizeGridLayout(grid) {
        const items = grid.children;
        const breakpoint = this.currentBreakpoint;
        
        // Adjust grid based on content and breakpoint
        if (breakpoint === 'xs' || breakpoint === 'sm') {
            grid.style.gridTemplateColumns = '1fr';
        } else {
            // Reset to CSS classes
            grid.style.gridTemplateColumns = '';
        }
    }
    
    enhanceTableResponsiveness(table) {
        const tableElement = table.querySelector('table');
        if (!tableElement) return;
        
        // Add horizontal scroll indicators
        const wrapper = document.createElement('div');
        wrapper.className = 'relative';
        
        const scrollIndicator = document.createElement('div');
        scrollIndicator.className = 'absolute top-0 right-0 h-full w-4 bg-gradient-to-l from-white to-transparent pointer-events-none opacity-0 transition-opacity';
        
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
        wrapper.appendChild(scrollIndicator);
        
        // Show/hide scroll indicator
        table.addEventListener('scroll', () => {
            const canScrollRight = table.scrollLeft < (table.scrollWidth - table.clientWidth);
            scrollIndicator.style.opacity = canScrollRight ? '1' : '0';
        });
    }
    
    optimizeImageLoading(img) {
        // Add lazy loading if not already present
        if (!img.hasAttribute('loading')) {
            img.setAttribute('loading', 'lazy');
        }
        
        // Add responsive image handling
        if (!img.hasAttribute('sizes') && img.hasAttribute('srcset')) {
            img.setAttribute('sizes', '(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw');
        }
    }
    
    updateComponents(currentBreakpoint, previousBreakpoint) {
        // Update all registered components
        this.components.forEach((component, id) => {
            if (component.onBreakpointChange) {
                component.onBreakpointChange(currentBreakpoint, previousBreakpoint);
            }
        });
    }
    
    updateLayout() {
        // Trigger layout updates
        document.dispatchEvent(new CustomEvent('layout:update', {
            detail: { breakpoint: this.currentBreakpoint }
        }));
        
        // Update component layouts
        this.updateComponentLayouts();
    }
    
    updateComponentLayouts() {
        // Re-optimize grids
        const grids = document.querySelectorAll('.responsive-grid');
        grids.forEach(grid => this.optimizeGridLayout(grid));
        
        // Update table responsiveness
        const tables = document.querySelectorAll('.responsive-table');
        tables.forEach(table => this.updateTableLayout(table));
    }
    
    updateTableLayout(table) {
        const tableElement = table.querySelector('table');
        if (!tableElement) return;
        
        // Check if table needs horizontal scrolling
        const needsScroll = tableElement.scrollWidth > table.clientWidth;
        table.classList.toggle('overflow-x-auto', needsScroll);
    }
    
    handleBreakpointBehaviors(current, previous) {
        // Mobile-specific behaviors
        if (current === 'xs' || current === 'sm') {
            this.enableMobileBehaviors();
        } else {
            this.disableMobileBehaviors();
        }
        
        // Tablet-specific behaviors
        if (current === 'md') {
            this.enableTabletBehaviors();
        }
        
        // Desktop-specific behaviors
        if (current === 'lg' || current === 'xl' || current === '2xl') {
            this.enableDesktopBehaviors();
        }
    }
    
    enableMobileBehaviors() {
        // Add mobile-specific classes
        document.body.classList.add('mobile-layout');
        
        // Optimize touch targets
        this.optimizeTouchTargets();
        
        // Enable mobile navigation patterns
        this.enableMobileNavigation();
    }
    
    disableMobileBehaviors() {
        document.body.classList.remove('mobile-layout');
    }
    
    enableTabletBehaviors() {
        document.body.classList.add('tablet-layout');
    }
    
    enableDesktopBehaviors() {
        document.body.classList.add('desktop-layout');
        
        // Enable hover effects
        this.enableHoverEffects();
    }
    
    optimizeTouchTargets() {
        const buttons = document.querySelectorAll('button, a, input[type="button"], input[type="submit"]');
        buttons.forEach(button => {
            if (!button.classList.contains('touch-target')) {
                button.classList.add('touch-friendly');
            }
        });
    }
    
    enableMobileNavigation() {
        // Emit event for navigation component
        document.dispatchEvent(new CustomEvent('layout:mobile-navigation', {
            detail: { enabled: true }
        }));
    }
    
    enableHoverEffects() {
        document.body.classList.add('hover-enabled');
    }
    
    handleKeyboardNavigation(e) {
        // Handle global keyboard shortcuts
        if (e.altKey && e.key === 'm') {
            // Alt+M: Toggle mobile menu
            e.preventDefault();
            document.dispatchEvent(new CustomEvent('layout:toggle-mobile-menu'));
        }
        
        if (e.altKey && e.key === 's') {
            // Alt+S: Focus search
            e.preventDefault();
            const searchInput = document.querySelector('input[type="search"], .nav-search-input');
            if (searchInput) {
                searchInput.focus();
            }
        }
    }
    
    handleFocusManagement(e) {
        // Ensure focused elements are visible
        if (e.target.scrollIntoViewIfNeeded) {
            e.target.scrollIntoViewIfNeeded();
        } else {
            e.target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
    
    handleSwipeGesture(deltaX, deltaY, event) {
        const minSwipeDistance = 50;
        const maxVerticalDistance = 100;
        
        // Horizontal swipe
        if (Math.abs(deltaX) > minSwipeDistance && Math.abs(deltaY) < maxVerticalDistance) {
            const direction = deltaX > 0 ? 'right' : 'left';
            
            document.dispatchEvent(new CustomEvent('layout:swipe', {
                detail: { direction, deltaX, deltaY, event }
            }));
        }
        
        // Vertical swipe
        if (Math.abs(deltaY) > minSwipeDistance && Math.abs(deltaX) < maxVerticalDistance) {
            const direction = deltaY > 0 ? 'down' : 'up';
            
            document.dispatchEvent(new CustomEvent('layout:swipe', {
                detail: { direction, deltaX, deltaY, event }
            }));
        }
    }
    
    handleIntersection(entries) {
        entries.forEach(entry => {
            const element = entry.target;
            const type = element.getAttribute('data-responsive-type');
            
            if (entry.isIntersecting) {
                element.classList.add('in-viewport');
                
                // Trigger component-specific actions
                if (type === 'grid') {
                    this.optimizeGridLayout(element);
                }
            } else {
                element.classList.remove('in-viewport');
            }
        });
    }
    
    handleResize(entries) {
        entries.forEach(entry => {
            const element = entry.target;
            const type = element.getAttribute('data-responsive-type');
            
            // Update component based on new size
            if (type === 'container') {
                this.updateContainerLayout(element, entry.contentRect);
            } else if (type === 'grid') {
                this.optimizeGridLayout(element);
            }
        });
    }
    
    updateContainerLayout(container, rect) {
        // Adjust container behavior based on size
        const width = rect.width;
        
        if (width < 400) {
            container.classList.add('compact-layout');
        } else {
            container.classList.remove('compact-layout');
        }
    }
    
    addSkipLinks() {
        const skipLinks = document.createElement('div');
        skipLinks.className = 'sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 z-50';
        skipLinks.innerHTML = `
            <a href="#main-content" class="bg-blue-600 text-white px-4 py-2 rounded-md">
                Skip to main content
            </a>
        `;
        
        document.body.insertBefore(skipLinks, document.body.firstChild);
    }
    
    enhanceFocusIndicators() {
        const style = document.createElement('style');
        style.textContent = `
            *:focus {
                outline: 2px solid #3b82f6;
                outline-offset: 2px;
            }
            
            .focus-visible:focus {
                outline: 2px solid #3b82f6;
                outline-offset: 2px;
            }
        `;
        document.head.appendChild(style);
    }
    
    addAriaLandmarks() {
        // Add main landmark if not present
        if (!document.querySelector('main, [role="main"]')) {
            const mainContent = document.querySelector('#main-content, .main-content, .content');
            if (mainContent && !mainContent.hasAttribute('role')) {
                mainContent.setAttribute('role', 'main');
                mainContent.id = 'main-content';
            }
        }
    }
    
    handleReducedMotion() {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            document.body.classList.add('reduced-motion');
        }
    }
    
    // Public API
    registerComponent(id, component) {
        this.components.set(id, component);
    }
    
    unregisterComponent(id) {
        this.components.delete(id);
    }
    
    getCurrentBreakpoint() {
        return this.currentBreakpoint;
    }
    
    isBreakpoint(breakpoint) {
        return this.currentBreakpoint === breakpoint;
    }
    
    isMobile() {
        return this.currentBreakpoint === 'xs' || this.currentBreakpoint === 'sm';
    }
    
    isTablet() {
        return this.currentBreakpoint === 'md';
    }
    
    isDesktop() {
        return this.currentBreakpoint === 'lg' || this.currentBreakpoint === 'xl' || this.currentBreakpoint === '2xl';
    }
    
    getViewportSize() {
        return {
            width: window.innerWidth,
            height: window.innerHeight,
            breakpoint: this.currentBreakpoint
        };
    }
    
    destroy() {
        // Clean up observers
        if (this.intersectionObserver) {
            this.intersectionObserver.disconnect();
        }
        
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        
        // Remove event listeners
        window.removeEventListener('resize', this.detectBreakpoint);
        window.removeEventListener('orientationchange', this.detectBreakpoint);
        
        // Clear components
        this.components.clear();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ResponsiveLayout;
}

// Global instance
if (typeof window !== 'undefined') {
    window.ResponsiveLayout = ResponsiveLayout;
    
    // Auto-initialize if DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.responsiveLayout = new ResponsiveLayout();
        });
    } else {
        window.responsiveLayout = new ResponsiveLayout();
    }
}