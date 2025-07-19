/**
 * Navigation Component
 * Provides responsive navigation with mobile menu, breadcrumbs, and accessibility features
 * Integrates with existing layout and authentication system
 */

class NavigationComponent {
    constructor(options = {}) {
        this.options = {
            mobileBreakpoint: 768,
            animationDuration: 300,
            enableBreadcrumbs: true,
            enableSearch: true,
            enableNotifications: true,
            ...options
        };
        
        this.isOpen = false;
        this.currentPath = window.location.pathname;
        this.breadcrumbs = [];
        
        this.init();
    }
    
    init() {
        this.setupStyles();
        this.createNavigation();
        this.bindEvents();
        this.updateActiveState();
        
        if (this.options.enableBreadcrumbs) {
            this.generateBreadcrumbs();
        }
    }
    
    setupStyles() {
        const styles = `
            /* Navigation Component Styles */
            .nav-component {
                @apply relative z-50;
            }
            
            .nav-header {
                @apply bg-white shadow-sm border-b border-gray-200;
            }
            
            .nav-container {
                @apply max-w-7xl mx-auto px-4 sm:px-6 lg:px-8;
            }
            
            .nav-content {
                @apply flex justify-between items-center h-16;
            }
            
            .nav-brand {
                @apply flex items-center space-x-3;
            }
            
            .nav-logo {
                @apply h-8 w-8 text-blue-600;
            }
            
            .nav-title {
                @apply text-xl font-bold text-gray-900 hidden sm:block;
            }
            
            .nav-menu {
                @apply hidden md:flex md:items-center md:space-x-8;
            }
            
            .nav-link {
                @apply text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium;
                @apply transition-colors duration-200;
            }
            
            .nav-link.active {
                @apply text-blue-600 bg-blue-50;
            }
            
            .nav-link:focus {
                @apply outline-none ring-2 ring-blue-500 ring-offset-2;
            }
            
            .nav-actions {
                @apply flex items-center space-x-4;
            }
            
            .nav-search {
                @apply hidden lg:block;
            }
            
            .nav-search-input {
                @apply w-64 px-4 py-2 border border-gray-300 rounded-lg;
                @apply focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500;
                @apply transition-all duration-200;
            }
            
            .nav-notifications {
                @apply relative;
            }
            
            .nav-notification-btn {
                @apply p-2 text-gray-400 hover:text-gray-500 focus:outline-none;
                @apply focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-full;
            }
            
            .nav-notification-badge {
                @apply absolute -top-1 -right-1 h-5 w-5 bg-red-500 text-white;
                @apply text-xs font-bold rounded-full flex items-center justify-center;
            }
            
            .nav-user {
                @apply relative;
            }
            
            .nav-user-btn {
                @apply flex items-center space-x-2 p-2 rounded-lg;
                @apply text-gray-700 hover:bg-gray-100 focus:outline-none;
                @apply focus:ring-2 focus:ring-blue-500 focus:ring-offset-2;
            }
            
            .nav-user-avatar {
                @apply h-8 w-8 bg-gray-300 rounded-full flex items-center justify-center;
            }
            
            .nav-mobile-btn {
                @apply md:hidden p-2 rounded-md text-gray-400 hover:text-gray-500;
                @apply hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500;
            }
            
            .nav-mobile-menu {
                @apply md:hidden absolute top-16 left-0 right-0 bg-white shadow-lg;
                @apply border-t border-gray-200 transform transition-all duration-300;
            }
            
            .nav-mobile-menu.closed {
                @apply -translate-y-full opacity-0 pointer-events-none;
            }
            
            .nav-mobile-menu.open {
                @apply translate-y-0 opacity-100;
            }
            
            .nav-mobile-links {
                @apply px-4 py-2 space-y-1;
            }
            
            .nav-mobile-link {
                @apply block px-3 py-2 rounded-md text-base font-medium;
                @apply text-gray-700 hover:text-gray-900 hover:bg-gray-50;
            }
            
            .nav-mobile-link.active {
                @apply text-blue-600 bg-blue-50;
            }
            
            .nav-mobile-search {
                @apply lg:hidden px-4 py-3 border-t border-gray-200;
            }
            
            .nav-mobile-search-input {
                @apply w-full px-4 py-2 border border-gray-300 rounded-lg;
                @apply focus:outline-none focus:ring-2 focus:ring-blue-500;
            }
            
            .nav-breadcrumbs {
                @apply bg-gray-50 border-b border-gray-200;
            }
            
            .nav-breadcrumb-container {
                @apply max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3;
            }
            
            .nav-breadcrumb-list {
                @apply flex items-center space-x-2 text-sm;
            }
            
            .nav-breadcrumb-item {
                @apply text-gray-500 hover:text-gray-700;
            }
            
            .nav-breadcrumb-item.current {
                @apply text-gray-900 font-medium;
            }
            
            .nav-breadcrumb-separator {
                @apply text-gray-400;
            }
            
            .nav-dropdown {
                @apply absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg;
                @apply ring-1 ring-black ring-opacity-5 focus:outline-none;
                @apply transform transition-all duration-200 origin-top-right;
            }
            
            .nav-dropdown.closed {
                @apply scale-95 opacity-0 pointer-events-none;
            }
            
            .nav-dropdown.open {
                @apply scale-100 opacity-100;
            }
            
            .nav-dropdown-item {
                @apply block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100;
                @apply focus:outline-none focus:bg-gray-100;
            }
            
            /* Mobile optimizations */
            @media (max-width: 768px) {
                .nav-content {
                    @apply h-14;
                }
                
                .nav-title {
                    @apply text-lg;
                }
                
                .nav-mobile-menu {
                    @apply top-14;
                }
            }
            
            /* Animation classes */
            .nav-slide-down {
                animation: navSlideDown 0.3s ease-out;
            }
            
            .nav-slide-up {
                animation: navSlideUp 0.3s ease-in;
            }
            
            @keyframes navSlideDown {
                from {
                    transform: translateY(-100%);
                    opacity: 0;
                }
                to {
                    transform: translateY(0);
                    opacity: 1;
                }
            }
            
            @keyframes navSlideUp {
                from {
                    transform: translateY(0);
                    opacity: 1;
                }
                to {
                    transform: translateY(-100%);
                    opacity: 0;
                }
            }
            
            /* High contrast mode */
            @media (prefers-contrast: high) {
                .nav-header {
                    @apply border-b-2 border-gray-900;
                }
                
                .nav-link:focus {
                    @apply ring-4 ring-blue-600;
                }
            }
            
            /* Reduced motion */
            @media (prefers-reduced-motion: reduce) {
                .nav-mobile-menu,
                .nav-dropdown,
                .nav-link {
                    @apply transition-none;
                }
                
                .nav-slide-down,
                .nav-slide-up {
                    animation: none;
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
    
    createNavigation() {
        const existingNav = document.querySelector('.nav-component');
        if (existingNav) {
            existingNav.remove();
        }
        
        const nav = document.createElement('nav');
        nav.className = 'nav-component';
        nav.setAttribute('role', 'navigation');
        nav.setAttribute('aria-label', 'Main navigation');
        
        nav.innerHTML = `
            <div class="nav-header">
                <div class="nav-container">
                    <div class="nav-content">
                        <!-- Brand -->
                        <div class="nav-brand">
                            <a href="/" class="flex items-center space-x-3">
                                <svg class="nav-logo" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                                </svg>
                                <span class="nav-title">Exam Grader</span>
                            </a>
                        </div>
                        
                        <!-- Desktop Menu -->
                        <div class="nav-menu">
                            <a href="/dashboard" class="nav-link" data-nav="dashboard">Dashboard</a>
                            <a href="/submissions" class="nav-link" data-nav="submissions">Submissions</a>
                            <a href="/marking_guides" class="nav-link" data-nav="guides">Guides</a>
                            <a href="/results" class="nav-link" data-nav="results">Results</a>
                            <a href="/settings" class="nav-link" data-nav="settings">Settings</a>
                        </div>
                        
                        <!-- Actions -->
                        <div class="nav-actions">
                            <!-- Search -->
                            ${this.options.enableSearch ? `
                                <div class="nav-search">
                                    <input 
                                        type="text" 
                                        placeholder="Search..." 
                                        class="nav-search-input"
                                        aria-label="Search"
                                    >
                                </div>
                            ` : ''}
                            
                            <!-- Notifications -->
                            ${this.options.enableNotifications ? `
                                <div class="nav-notifications">
                                    <button class="nav-notification-btn" aria-label="Notifications">
                                        <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-5 5v-5zM10.5 3.74a6 6 0 0 1 8.25 8.98m0 0A6 6 0 0 1 12 21a6 6 0 0 1-6-6 6 6 0 0 1 6-6z"/>
                                        </svg>
                                        <span class="nav-notification-badge hidden">0</span>
                                    </button>
                                </div>
                            ` : ''}
                            
                            <!-- User Menu -->
                            <div class="nav-user">
                                <button class="nav-user-btn" aria-label="User menu" aria-expanded="false">
                                    <div class="nav-user-avatar">
                                        <svg class="h-5 w-5 text-gray-600" fill="currentColor" viewBox="0 0 24 24">
                                            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                                        </svg>
                                    </div>
                                    <span class="hidden sm:block text-sm font-medium">User</span>
                                    <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
                                    </svg>
                                </button>
                                
                                <!-- User Dropdown -->
                                <div class="nav-dropdown closed">
                                    <a href="/profile" class="nav-dropdown-item">Profile</a>
                                    <a href="/settings" class="nav-dropdown-item">Settings</a>
                                    <hr class="my-1">
                                    <a href="/logout" class="nav-dropdown-item">Sign out</a>
                                </div>
                            </div>
                            
                            <!-- Mobile Menu Button -->
                            <button class="nav-mobile-btn" aria-label="Open menu" aria-expanded="false">
                                <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Mobile Menu -->
                <div class="nav-mobile-menu closed">
                    <div class="nav-mobile-links">
                        <a href="/dashboard" class="nav-mobile-link" data-nav="dashboard">Dashboard</a>
                        <a href="/submissions" class="nav-mobile-link" data-nav="submissions">Submissions</a>
                        <a href="/marking_guides" class="nav-mobile-link" data-nav="guides">Guides</a>
                        <a href="/results" class="nav-mobile-link" data-nav="results">Results</a>
                        <a href="/settings" class="nav-mobile-link" data-nav="settings">Settings</a>
                    </div>
                    
                    ${this.options.enableSearch ? `
                        <div class="nav-mobile-search">
                            <input 
                                type="text" 
                                placeholder="Search..." 
                                class="nav-mobile-search-input"
                                aria-label="Search"
                            >
                        </div>
                    ` : ''}
                </div>
            </div>
            
            <!-- Breadcrumbs -->
            ${this.options.enableBreadcrumbs ? `
                <div class="nav-breadcrumbs hidden">
                    <div class="nav-breadcrumb-container">
                        <nav class="nav-breadcrumb-list" aria-label="Breadcrumb"></nav>
                    </div>
                </div>
            ` : ''}
        `;
        
        // Insert navigation at the beginning of body or after header
        const header = document.querySelector('header');
        if (header) {
            header.after(nav);
        } else {
            document.body.insertBefore(nav, document.body.firstChild);
        }
        
        this.nav = nav;
    }
    
    bindEvents() {
        // Mobile menu toggle
        const mobileBtn = this.nav.querySelector('.nav-mobile-btn');
        const mobileMenu = this.nav.querySelector('.nav-mobile-menu');
        
        mobileBtn?.addEventListener('click', () => {
            this.toggleMobileMenu();
        });
        
        // User menu toggle
        const userBtn = this.nav.querySelector('.nav-user-btn');
        const userDropdown = this.nav.querySelector('.nav-dropdown');
        
        userBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleUserMenu();
        });
        
        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.nav-user')) {
                this.closeUserMenu();
            }
            if (!e.target.closest('.nav-mobile-menu') && !e.target.closest('.nav-mobile-btn')) {
                this.closeMobileMenu();
            }
        });
        
        // Handle window resize
        window.addEventListener('resize', () => {
            if (window.innerWidth >= this.options.mobileBreakpoint) {
                this.closeMobileMenu();
            }
        });
        
        // Handle keyboard navigation
        this.nav.addEventListener('keydown', (e) => {
            this.handleKeyboardNavigation(e);
        });
        
        // Handle search
        if (this.options.enableSearch) {
            const searchInputs = this.nav.querySelectorAll('.nav-search-input, .nav-mobile-search-input');
            searchInputs.forEach(input => {
                input.addEventListener('input', (e) => {
                    this.handleSearch(e.target.value);
                });
                
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        this.performSearch(e.target.value);
                    }
                });
            });
        }
        
        // Handle notifications
        if (this.options.enableNotifications) {
            const notificationBtn = this.nav.querySelector('.nav-notification-btn');
            notificationBtn?.addEventListener('click', () => {
                this.handleNotifications();
            });
        }
    }
    
    toggleMobileMenu() {
        const mobileMenu = this.nav.querySelector('.nav-mobile-menu');
        const mobileBtn = this.nav.querySelector('.nav-mobile-btn');
        
        this.isOpen = !this.isOpen;
        
        if (this.isOpen) {
            mobileMenu.classList.remove('closed');
            mobileMenu.classList.add('open');
            mobileBtn.setAttribute('aria-expanded', 'true');
            mobileBtn.setAttribute('aria-label', 'Close menu');
            
            // Update icon
            mobileBtn.innerHTML = `
                <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
            `;
        } else {
            this.closeMobileMenu();
        }
    }
    
    closeMobileMenu() {
        const mobileMenu = this.nav.querySelector('.nav-mobile-menu');
        const mobileBtn = this.nav.querySelector('.nav-mobile-btn');
        
        this.isOpen = false;
        mobileMenu.classList.remove('open');
        mobileMenu.classList.add('closed');
        mobileBtn.setAttribute('aria-expanded', 'false');
        mobileBtn.setAttribute('aria-label', 'Open menu');
        
        // Reset icon
        mobileBtn.innerHTML = `
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
            </svg>
        `;
    }
    
    toggleUserMenu() {
        const userDropdown = this.nav.querySelector('.nav-dropdown');
        const userBtn = this.nav.querySelector('.nav-user-btn');
        
        const isOpen = userDropdown.classList.contains('open');
        
        if (isOpen) {
            this.closeUserMenu();
        } else {
            userDropdown.classList.remove('closed');
            userDropdown.classList.add('open');
            userBtn.setAttribute('aria-expanded', 'true');
        }
    }
    
    closeUserMenu() {
        const userDropdown = this.nav.querySelector('.nav-dropdown');
        const userBtn = this.nav.querySelector('.nav-user-btn');
        
        userDropdown.classList.remove('open');
        userDropdown.classList.add('closed');
        userBtn.setAttribute('aria-expanded', 'false');
    }
    
    updateActiveState() {
        const links = this.nav.querySelectorAll('.nav-link, .nav-mobile-link');
        
        links.forEach(link => {
            link.classList.remove('active');
            
            if (link.href === window.location.href || 
                (link.pathname === window.location.pathname && window.location.pathname !== '/')) {
                link.classList.add('active');
            }
        });
    }
    
    generateBreadcrumbs() {
        const breadcrumbContainer = this.nav.querySelector('.nav-breadcrumb-list');
        if (!breadcrumbContainer) return;
        
        const pathSegments = window.location.pathname.split('/').filter(segment => segment);
        const breadcrumbs = [{ name: 'Home', href: '/' }];
        
        let currentPath = '';
        pathSegments.forEach((segment, index) => {
            currentPath += '/' + segment;
            const name = this.formatBreadcrumbName(segment);
            breadcrumbs.push({
                name,
                href: currentPath,
                current: index === pathSegments.length - 1
            });
        });
        
        if (breadcrumbs.length > 1) {
            this.renderBreadcrumbs(breadcrumbs);
            this.nav.querySelector('.nav-breadcrumbs').classList.remove('hidden');
        }
    }
    
    renderBreadcrumbs(breadcrumbs) {
        const container = this.nav.querySelector('.nav-breadcrumb-list');
        
        container.innerHTML = breadcrumbs.map((crumb, index) => {
            const isLast = index === breadcrumbs.length - 1;
            return `
                <li class="nav-breadcrumb-item ${isLast ? 'current' : ''}">
                    ${isLast ? 
                        `<span aria-current="page">${crumb.name}</span>` :
                        `<a href="${crumb.href}">${crumb.name}</a>`
                    }
                </li>
                ${!isLast ? '<li class="nav-breadcrumb-separator" aria-hidden="true">/</li>' : ''}
            `;
        }).join('');
    }
    
    formatBreadcrumbName(segment) {
        // Convert URL segments to readable names
        const nameMap = {
            'dashboard': 'Dashboard',
            'submissions': 'Submissions',
            'marking_guides': 'Marking Guides',
            'results': 'Results',
            'settings': 'Settings',
            'profile': 'Profile',
            'upload': 'Upload',
            'create': 'Create',
            'edit': 'Edit'
        };
        
        return nameMap[segment] || segment.charAt(0).toUpperCase() + segment.slice(1).replace(/[-_]/g, ' ');
    }
    
    handleKeyboardNavigation(e) {
        const focusableElements = this.nav.querySelectorAll(
            'a, button, input, [tabindex]:not([tabindex="-1"])'
        );
        const currentIndex = Array.from(focusableElements).indexOf(document.activeElement);
        
        switch (e.key) {
            case 'Escape':
                this.closeMobileMenu();
                this.closeUserMenu();
                break;
                
            case 'ArrowDown':
                if (document.activeElement.closest('.nav-user, .nav-mobile-menu')) {
                    e.preventDefault();
                    const nextIndex = (currentIndex + 1) % focusableElements.length;
                    focusableElements[nextIndex]?.focus();
                }
                break;
                
            case 'ArrowUp':
                if (document.activeElement.closest('.nav-user, .nav-mobile-menu')) {
                    e.preventDefault();
                    const prevIndex = currentIndex > 0 ? currentIndex - 1 : focusableElements.length - 1;
                    focusableElements[prevIndex]?.focus();
                }
                break;
        }
    }
    
    handleSearch(query) {
        // Emit search event for other components to handle
        this.nav.dispatchEvent(new CustomEvent('nav:search', {
            detail: { query }
        }));
    }
    
    performSearch(query) {
        if (query.trim()) {
            // Navigate to search results or perform search
            window.location.href = `/search?q=${encodeURIComponent(query)}`;
        }
    }
    
    handleNotifications() {
        // Emit notification event
        this.nav.dispatchEvent(new CustomEvent('nav:notifications', {
            detail: { action: 'toggle' }
        }));
    }
    
    updateNotificationCount(count) {
        const badge = this.nav.querySelector('.nav-notification-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count.toString();
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }
    }
    
    updateUserInfo(userInfo) {
        const userBtn = this.nav.querySelector('.nav-user-btn span');
        if (userBtn && userInfo.name) {
            userBtn.textContent = userInfo.name;
        }
        
        // Update avatar if provided
        if (userInfo.avatar) {
            const avatar = this.nav.querySelector('.nav-user-avatar');
            avatar.innerHTML = `<img src="${userInfo.avatar}" alt="${userInfo.name}" class="h-8 w-8 rounded-full">`;
        }
    }
    
    updateForBreakpoint(breakpoint) {
        // Handle responsive navigation updates based on breakpoint
        const mobileMenu = this.nav.querySelector('.nav-mobile-menu');
        const desktopMenu = this.nav.querySelector('.nav-menu');
        const mobileBtn = this.nav.querySelector('.nav-mobile-btn');
        
        // Close mobile menu when switching to desktop
        if (breakpoint === 'lg' || breakpoint === 'xl') {
            this.closeMobileMenu();
            if (mobileBtn) mobileBtn.style.display = 'none';
            if (desktopMenu) desktopMenu.style.display = 'flex';
        } else {
            if (mobileBtn) mobileBtn.style.display = 'block';
            if (desktopMenu) desktopMenu.style.display = 'none';
        }
        
        // Update search visibility based on breakpoint
        const searchInput = this.nav.querySelector('.nav-search');
        const mobileSearch = this.nav.querySelector('.nav-mobile-search');
        
        if (breakpoint === 'lg' || breakpoint === 'xl') {
            if (searchInput) searchInput.style.display = 'block';
            if (mobileSearch) mobileSearch.style.display = 'none';
        } else {
            if (searchInput) searchInput.style.display = 'none';
            if (mobileSearch) mobileSearch.style.display = 'block';
        }
        
        // Emit breakpoint change event for other components
        this.nav.dispatchEvent(new CustomEvent('nav:breakpoint-change', {
            detail: { breakpoint }
        }));
    }
    
    destroy() {
        if (this.nav) {
            this.nav.remove();
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NavigationComponent;
}

// Global instance
if (typeof window !== 'undefined') {
    window.NavigationComponent = NavigationComponent;
    
    // Auto-initialize if DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.navigationComponent = new NavigationComponent();
        });
    } else {
        window.navigationComponent = new NavigationComponent();
    }
}