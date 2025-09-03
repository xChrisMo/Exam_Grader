/**
 * Mobile Menu Functionality
 * Handles mobile navigation menu toggle and interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenuOverlay = document.getElementById('mobile-menu-overlay');
    const mobileMenuClose = document.getElementById('mobile-menu-close');
    const mobileMenuBackdrop = document.getElementById('mobile-menu-backdrop');
    const menuIcon = document.getElementById('menu-icon');
    const closeIcon = document.getElementById('close-icon');

    // Check if elements exist
    if (!mobileMenuButton || !mobileMenuOverlay) {
        console.warn('Mobile menu elements not found');
        return;
    }

    // Function to open mobile menu
    function openMobileMenu() {
        mobileMenuOverlay.classList.remove('hidden');
        document.body.classList.add('overflow-hidden'); // Prevent body scroll
        
        // Toggle icons
        if (menuIcon && closeIcon) {
            menuIcon.classList.add('hidden');
            closeIcon.classList.remove('hidden');
        }
        
        // Focus trap
        const firstFocusableElement = mobileMenuOverlay.querySelector('a, button');
        if (firstFocusableElement) {
            firstFocusableElement.focus();
        }
    }

    // Function to close mobile menu
    function closeMobileMenu() {
        mobileMenuOverlay.classList.add('hidden');
        document.body.classList.remove('overflow-hidden'); // Restore body scroll
        
        // Toggle icons
        if (menuIcon && closeIcon) {
            menuIcon.classList.remove('hidden');
            closeIcon.classList.add('hidden');
        }
        
        // Return focus to menu button
        mobileMenuButton.focus();
    }

    // Mobile menu button click handler
    mobileMenuButton.addEventListener('click', function(e) {
        e.preventDefault();
        
        if (mobileMenuOverlay.classList.contains('hidden')) {
            openMobileMenu();
        } else {
            closeMobileMenu();
        }
    });

    // Close button click handler
    if (mobileMenuClose) {
        mobileMenuClose.addEventListener('click', function(e) {
            e.preventDefault();
            closeMobileMenu();
        });
    }

    // Backdrop click handler
    if (mobileMenuBackdrop) {
        mobileMenuBackdrop.addEventListener('click', function(e) {
            e.preventDefault();
            closeMobileMenu();
        });
    }

    // Close menu when clicking on navigation links
    const mobileNavLinks = document.querySelectorAll('.mobile-nav-link');
    mobileNavLinks.forEach(function(link) {
        link.addEventListener('click', function() {
            // Small delay to allow navigation to start
            setTimeout(closeMobileMenu, 100);
        });
    });

    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        // Close menu on Escape key
        if (e.key === 'Escape' && !mobileMenuOverlay.classList.contains('hidden')) {
            closeMobileMenu();
        }
    });

    // Handle window resize
    window.addEventListener('resize', function() {
        // Close mobile menu if window becomes large enough for desktop nav
        if (window.innerWidth >= 1024) { // lg breakpoint
            closeMobileMenu();
        }
    });

    // Touch/swipe support for closing menu
    let touchStartX = 0;
    let touchStartY = 0;

    if (mobileMenuOverlay) {
        mobileMenuOverlay.addEventListener('touchstart', function(e) {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        });

        mobileMenuOverlay.addEventListener('touchend', function(e) {
            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;
            
            const deltaX = touchEndX - touchStartX;
            const deltaY = touchEndY - touchStartY;
            
            // Swipe left to close (minimum 50px swipe)
            if (deltaX < -50 && Math.abs(deltaY) < 100) {
                closeMobileMenu();
            }
        });
    }

    console.log('Mobile menu functionality initialized');
});