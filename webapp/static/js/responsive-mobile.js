/**
 * Responsive Mobile Enhancements for Exam Grader
 * Handles mobile-specific interactions and responsive behaviors
 */

class ResponsiveMobileHandler {
  constructor() {
    this.isMobile = window.innerWidth < 768;
    this.isTablet = window.innerWidth >= 768 && window.innerWidth < 1024;
    this.isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    
    this.init();
  }

  init() {
    this.setupViewportHandler();
    this.setupTouchEnhancements();
    this.setupMobileNavigation();
    this.setupResponsiveTables();
    this.setupMobileModals();
    this.setupMobileUpload();
    this.setupMobileProgress();
    this.setupAccessibility();
    this.setupOrientationHandler();
  }

  setupViewportHandler() {
    // Handle viewport changes
    window.addEventListener('resize', this.debounce(() => {
      this.isMobile = window.innerWidth < 768;
      this.isTablet = window.innerWidth >= 768 && window.innerWidth < 1024;
      this.updateResponsiveElements();
    }, 250));

    // Initial setup
    this.updateResponsiveElements();
  }

  updateResponsiveElements() {
    // Update grid layouts for mobile
    const grids = document.querySelectorAll('.grid');
    grids.forEach(grid => {
      if (this.isMobile) {
        // Force single column on mobile
        grid.style.gridTemplateColumns = '1fr';
      } else {
        // Reset to original classes
        grid.style.gridTemplateColumns = '';
      }
    });

    // Update navigation
    this.updateNavigation();
    
    // Update tables
    this.updateTables();
    
    // Update forms
    this.updateForms();
  }

  setupTouchEnhancements() {
    if (!this.isTouch) return;

    // Add touch feedback to interactive elements
    const interactiveElements = document.querySelectorAll('button, .btn, a, .clickable');
    
    interactiveElements.forEach(element => {
      element.addEventListener('touchstart', () => {
        element.classList.add('touch-active');
      });

      element.addEventListener('touchend', () => {
        setTimeout(() => {
          element.classList.remove('touch-active');
        }, 150);
      });

      element.addEventListener('touchcancel', () => {
        element.classList.remove('touch-active');
      });
    });

    // Add touch-specific CSS
    const touchStyles = document.createElement('style');
    touchStyles.textContent = `
      .touch-active {
        transform: scale(0.98);
        opacity: 0.8;
        transition: all 0.1s ease;
      }
      
      /* Ensure touch targets are large enough */
      @media (hover: none) and (pointer: coarse) {
        button, .btn, a, input[type="checkbox"], input[type="radio"] {
          min-height: 44px;
          min-width: 44px;
        }
      }
    `;
    document.head.appendChild(touchStyles);
  }

  setupMobileNavigation() {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('mobile-sidebar-backdrop');
    const mobileMenuButton = document.querySelector('button[class*="lg:hidden"]');

    if (!sidebar || !mobileMenuButton) return;

    // Enhanced mobile menu with swipe gestures
    let startX = 0;
    let currentX = 0;
    let isDragging = false;

    // Swipe to open/close sidebar
    document.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
      
      // Only handle swipes from edge on mobile
      if (this.isMobile && (startX < 20 || startX > window.innerWidth - 20)) {
        isDragging = true;
      }
    });

    document.addEventListener('touchmove', (e) => {
      if (!isDragging) return;
      
      currentX = e.touches[0].clientX;
      const diffX = currentX - startX;

      // Swipe from left edge to open
      if (startX < 20 && diffX > 50 && sidebar.classList.contains('hidden')) {
        this.openMobileMenu();
        isDragging = false;
      }
      
      // Swipe to close when sidebar is open
      if (!sidebar.classList.contains('hidden') && diffX < -50) {
        this.closeMobileMenu();
        isDragging = false;
      }
    });

    document.addEventListener('touchend', () => {
      isDragging = false;
    });

    // Close menu when clicking nav links
    const navLinks = sidebar.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
      link.addEventListener('click', () => {
        if (this.isMobile && !sidebar.classList.contains('hidden')) {
          setTimeout(() => this.closeMobileMenu(), 100);
        }
      });
    });
  }

  openMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('mobile-sidebar-backdrop');
    
    if (sidebar) {
      sidebar.classList.remove('hidden');
      sidebar.classList.add('fixed', 'inset-0', 'z-50');
    }
    
    if (backdrop) {
      backdrop.classList.remove('hidden');
    }
    
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
    
    // Add animation
    requestAnimationFrame(() => {
      if (sidebar) {
        sidebar.style.transform = 'translateX(0)';
      }
    });
  }

  closeMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('mobile-sidebar-backdrop');
    
    if (sidebar) {
      sidebar.classList.add('hidden');
      sidebar.classList.remove('fixed', 'inset-0', 'z-50');
      sidebar.style.transform = '';
    }
    
    if (backdrop) {
      backdrop.classList.add('hidden');
    }
    
    // Restore body scroll
    document.body.style.overflow = '';
  }

  setupResponsiveTables() {
    const tables = document.querySelectorAll('table');
    
    tables.forEach(table => {
      // Wrap tables in responsive container
      if (!table.closest('.table-responsive')) {
        const wrapper = document.createElement('div');
        wrapper.className = 'table-responsive overflow-x-auto';
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
      }

      // Add mobile-friendly table behavior
      if (this.isMobile) {
        this.makeTableMobileFriendly(table);
      }
    });
  }

  makeTableMobileFriendly(table) {
    const headers = table.querySelectorAll('th');
    const rows = table.querySelectorAll('tbody tr');

    // Add data labels for mobile stacking
    rows.forEach(row => {
      const cells = row.querySelectorAll('td');
      cells.forEach((cell, index) => {
        if (headers[index]) {
          cell.setAttribute('data-label', headers[index].textContent.trim());
        }
      });
    });

    // Add mobile table class
    table.classList.add('table-stack');
  }

  updateTables() {
    const tables = document.querySelectorAll('table');
    
    tables.forEach(table => {
      if (this.isMobile) {
        table.classList.add('table-stack');
      } else {
        table.classList.remove('table-stack');
      }
    });
  }

  setupMobileModals() {
    const modals = document.querySelectorAll('.modal, [role="dialog"]');
    
    modals.forEach(modal => {
      // Make modals full-screen on mobile
      if (this.isMobile) {
        modal.classList.add('mobile-modal');
      }

      // Handle modal scrolling on mobile
      modal.addEventListener('touchmove', (e) => {
        if (this.isMobile) {
          e.stopPropagation();
        }
      });
    });

    // Add mobile modal styles
    const modalStyles = document.createElement('style');
    modalStyles.textContent = `
      @media (max-width: 640px) {
        .mobile-modal {
          position: fixed !important;
          top: 0 !important;
          left: 0 !important;
          right: 0 !important;
          bottom: 0 !important;
          width: 100% !important;
          height: 100% !important;
          max-width: none !important;
          max-height: none !important;
          margin: 0 !important;
          border-radius: 0 !important;
        }
        
        .mobile-modal .modal-content {
          height: 100%;
          overflow-y: auto;
          -webkit-overflow-scrolling: touch;
        }
      }
    `;
    document.head.appendChild(modalStyles);
  }

  setupMobileUpload() {
    const uploadAreas = document.querySelectorAll('.upload-area, [data-upload]');
    
    uploadAreas.forEach(area => {
      // Enhance touch interactions for upload areas
      area.addEventListener('touchstart', () => {
        area.classList.add('touch-highlight');
      });

      area.addEventListener('touchend', () => {
        setTimeout(() => {
          area.classList.remove('touch-highlight');
        }, 200);
      });

      // Handle file input on mobile
      const fileInput = area.querySelector('input[type="file"]');
      if (fileInput && this.isMobile) {
        // Add accept attribute for better mobile experience
        if (!fileInput.hasAttribute('accept')) {
          fileInput.setAttribute('accept', '.pdf,.docx,.doc,.txt,.jpg,.jpeg,.png,.bmp,.tiff,.gif');
        }
        
        // Add capture attribute for camera access
        if (fileInput.hasAttribute('data-camera')) {
          fileInput.setAttribute('capture', 'environment');
        }
      }
    });

    // Add upload area styles
    const uploadStyles = document.createElement('style');
    uploadStyles.textContent = `
      .touch-highlight {
        background-color: rgba(59, 130, 246, 0.1) !important;
        border-color: #3b82f6 !important;
      }
      
      @media (max-width: 640px) {
        .upload-area {
          padding: 1.5rem 1rem !important;
          min-height: 6rem !important;
        }
        
        .upload-area p {
          font-size: 0.875rem !important;
        }
      }
    `;
    document.head.appendChild(uploadStyles);
  }

  setupMobileProgress() {
    const progressBars = document.querySelectorAll('.progress-bar, [role="progressbar"]');
    
    progressBars.forEach(bar => {
      // Make progress bars more visible on mobile
      if (this.isMobile) {
        bar.style.minHeight = '8px';
      }
    });

    // Handle progress updates with haptic feedback on mobile
    if (this.isTouch && 'vibrate' in navigator) {
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === 'attributes' && mutation.attributeName === 'aria-valuenow') {
            const value = parseInt(mutation.target.getAttribute('aria-valuenow'));
            if (value === 100) {
              // Vibrate on completion
              navigator.vibrate(200);
            }
          }
        });
      });

      progressBars.forEach(bar => {
        observer.observe(bar, { attributes: true });
      });
    }
  }

  updateNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
      if (this.isMobile) {
        // Increase touch target size
        link.style.padding = '0.75rem 0.5rem';
      } else {
        link.style.padding = '';
      }
    });
  }

  updateForms() {
    const inputs = document.querySelectorAll('input, textarea, select');
    
    inputs.forEach(input => {
      if (this.isMobile) {
        // Prevent zoom on iOS
        if (input.type === 'text' || input.type === 'email' || input.type === 'password' || input.tagName === 'TEXTAREA') {
          input.style.fontSize = '16px';
        }
        
        // Add better spacing
        input.style.padding = '0.75rem';
      } else {
        input.style.fontSize = '';
        input.style.padding = '';
      }
    });
  }

  setupAccessibility() {
    // Enhance keyboard navigation on mobile
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        // Close mobile menu on escape
        if (this.isMobile) {
          this.closeMobileMenu();
        }
        
        // Close any open dropdowns
        const openDropdowns = document.querySelectorAll('.dropdown-open, [aria-expanded="true"]');
        openDropdowns.forEach(dropdown => {
          dropdown.classList.remove('dropdown-open');
          dropdown.setAttribute('aria-expanded', 'false');
        });
      }
    });

    // Improve focus management
    const focusableElements = document.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    
    focusableElements.forEach(element => {
      element.addEventListener('focus', () => {
        // Ensure focused element is visible on mobile
        if (this.isMobile) {
          setTimeout(() => {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }, 100);
        }
      });
    });
  }

  setupOrientationHandler() {
    // Handle orientation changes
    window.addEventListener('orientationchange', () => {
      setTimeout(() => {
        this.updateResponsiveElements();
        
        // Close mobile menu on orientation change
        if (this.isMobile) {
          this.closeMobileMenu();
        }
      }, 100);
    });

    // Handle landscape mode adjustments
    const handleOrientationChange = () => {
      const isLandscape = window.innerHeight < window.innerWidth;
      
      if (isLandscape && this.isMobile) {
        document.body.classList.add('landscape-mobile');
      } else {
        document.body.classList.remove('landscape-mobile');
      }
    };

    window.addEventListener('resize', handleOrientationChange);
    handleOrientationChange();

    // Add landscape styles
    const landscapeStyles = document.createElement('style');
    landscapeStyles.textContent = `
      @media (max-width: 896px) and (orientation: landscape) {
        .landscape-mobile #sidebar.fixed .flex.flex-col {
          width: 60vw !important;
          max-width: 16rem !important;
        }
        
        .landscape-mobile .content-container {
          padding: 0.5rem 1rem !important;
        }
        
        .landscape-mobile header {
          padding: 0.5rem 1rem !important;
        }
      }
    `;
    document.head.appendChild(landscapeStyles);
  }

  // Utility function for debouncing
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Public methods for external use
  isMobileDevice() {
    return this.isMobile;
  }

  isTabletDevice() {
    return this.isTablet;
  }

  isTouchDevice() {
    return this.isTouch;
  }
}

// Initialize responsive mobile handler when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.responsiveMobile = new ResponsiveMobileHandler();
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ResponsiveMobileHandler;
}