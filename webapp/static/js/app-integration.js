/**
 * Application Integration
 * Integrates all UI components, state management, and workflows into a cohesive application
 */

class ExamGraderApp {
    constructor(options = {}) {
        this.options = {
            enableWebSocket: true,
            enableStateManagement: true,
            enableResponsiveLayout: true,
            enableWorkflows: true,
            enableProgressTracking: true,
            apiBaseUrl: '/api/v1',
            websocketUrl: window.location.origin,
            ...options
        };
        
        this.components = new Map();
        this.initialized = false;
        
        this.init();
    }
    
    async init() {
        try {
            // Initialize core systems
            await this.initializeStateManagement();
            await this.initializeWebSocket();
            await this.initializeResponsiveLayout();
            await this.initializeUIComponents();
            await this.initializeWorkflows();
            await this.initializeFormComponents();
            await this.initializeNavigation();
            
            // Setup application-specific integrations
            this.setupApplicationIntegrations();
            this.setupEventHandlers();
            this.setupKeyboardShortcuts();
            
            // Initialize page-specific functionality
            this.initializePageSpecificFeatures();
            
            this.initialized = true;
            
            // Emit initialization complete event
            document.dispatchEvent(new CustomEvent('app:initialized', {
                detail: { app: this }
            }));
            
            console.log('Exam Grader App initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize Exam Grader App:', error);
            this.handleInitializationError(error);
        }
    }
    
    async initializeStateManagement() {
        if (!this.options.enableStateManagement || !window.StateManager) return;
        
        // State manager should already be initialized globally
        this.stateManager = window.stateManager;
        
        // Setup application-specific state
        this.setupApplicationState();
        
        // Subscribe to important state changes
        this.subscribeToStateChanges();
    }
    
    async initializeWebSocket() {
        if (!this.options.enableWebSocket || !window.WebSocketIntegration) return;
        
        // Setup WebSocket integration
        this.websocketIntegration = new window.WebSocketIntegration();
        
        // Initialize with options
        this.websocketClient = this.websocketIntegration.initialize({
            url: this.options.websocketUrl,
            autoConnect: true,
            enableReconnection: true
        });
        
        // Setup application-specific WebSocket handlers
        this.setupWebSocketHandlers();
    }
    
    async initializeResponsiveLayout() {
        if (!this.options.enableResponsiveLayout || !window.ResponsiveLayout) return;
        
        // Responsive layout should already be initialized globally
        this.responsiveLayout = window.responsiveLayout;
        
        // Register app as a responsive component
        this.responsiveLayout.registerComponent('app', this);
    }
    
    async initializeUIComponents() {
        if (!window.UIComponents) return;
        
        // Initialize UI components library
        this.uiComponents = new window.UIComponents();
        
        // Setup component event handlers
        this.setupComponentEventHandlers();
    }
    
    async initializeWorkflows() {
        if (!this.options.enableWorkflows || !window.UIWorkflows) return;
        
        // Workflows should already be initialized globally
        this.workflows = window.uiWorkflows;
        
        // Setup workflow component renderers
        this.setupWorkflowComponentRenderers();
    }
    
    async initializeFormComponents() {
        if (!window.FormComponents) return;
        
        // Initialize form components
        this.formComponents = new window.FormComponents();
        
        // Setup form integration with state management
        this.setupFormStateIntegration();
    }
    
    async initializeNavigation() {
        if (!window.NavigationComponent) return;
        
        // Initialize navigation component
        this.navigation = new window.NavigationComponent();
        
        // Setup navigation integration
        this.setupNavigationIntegration();
    }
    
    setupApplicationState() {
        // Initialize application-specific state
        this.stateManager.mergeState('app', {
            currentPage: this.getCurrentPage(),
            user: this.getCurrentUser(),
            features: {
                fileUpload: true,
                aiProcessing: true,
                markingGuides: true,
                resultsReview: true
            }
        });
        
        // Initialize UI state
        this.stateManager.mergeState('ui', {
            currentView: 'dashboard',
            activeWorkflow: null,
            notifications: [],
            loading: {
                global: false,
                components: {}
            }
        });
    }
    
    subscribeToStateChanges() {
        // Subscribe to loading state changes
        this.stateManager.subscribe('ui.loading.global', (isLoading) => {
            this.handleGlobalLoadingChange(isLoading);
        });
        
        // Subscribe to notification changes
        this.stateManager.subscribe('ui.notifications', (notifications) => {
            this.handleNotificationsChange(notifications);
        });
        
        // Subscribe to user changes
        this.stateManager.subscribe('app.user', (user) => {
            this.handleUserChange(user);
        });
        
        // Subscribe to breakpoint changes
        this.stateManager.subscribe('app.breakpoint', (breakpoint) => {
            this.handleBreakpointChange(breakpoint);
        });
    }
    
    setupWebSocketHandlers() {
        // Handle progress updates
        this.websocketClient.on('progress_update', (data) => {
            this.handleProgressUpdate(data);
        });
        
        // Handle dashboard updates
        this.websocketClient.on('dashboard_update', (data) => {
            this.handleDashboardUpdate(data);
        });
        
        // Handle processing status updates
        this.websocketClient.on('processing_status', (data) => {
            this.handleProcessingStatusUpdate(data);
        });
        
        // Handle notifications
        this.websocketClient.on('notification', (data) => {
            this.addNotification(data);
        });
        
        // Handle connection status changes
        this.websocketClient.on('connect', () => {
            this.stateManager.setState('websocket.connected', true);
            this.addNotification({
                type: 'success',
                message: 'Connected to real-time updates',
                duration: 3000
            });
        });
        
        this.websocketClient.on('disconnect', () => {
            this.stateManager.setState('websocket.connected', false);
            this.addNotification({
                type: 'warning',
                message: 'Disconnected from real-time updates',
                duration: 5000
            });
        });
    }
    
    setupComponentEventHandlers() {
        // Handle component creation events
        document.addEventListener('component:created', (e) => {
            this.handleComponentCreated(e.detail);
        });
        
        // Handle component destruction events
        document.addEventListener('component:destroyed', (e) => {
            this.handleComponentDestroyed(e.detail);
        });
        
        // Handle component state changes
        document.addEventListener('component:state-change', (e) => {
            this.handleComponentStateChange(e.detail);
        });
    }
    
    setupWorkflowComponentRenderers() {
        // Register component renderers for workflows
        document.addEventListener('workflow:render-component', (e) => {
            this.renderWorkflowComponent(e.detail);
        });
        
        // Handle workflow events
        document.addEventListener('workflow:started', (e) => {
            this.handleWorkflowStarted(e.detail);
        });
        
        document.addEventListener('workflow:completed', (e) => {
            this.handleWorkflowCompleted(e.detail);
        });
        
        document.addEventListener('workflow:cancelled', (e) => {
            this.handleWorkflowCancelled(e.detail);
        });
    }
    
    setupFormStateIntegration() {
        // Integrate forms with state management
        document.addEventListener('form:created', (e) => {
            const { formId, initialData } = e.detail;
            this.stateManager.createForm(formId, initialData);
        });
        
        document.addEventListener('form:field-change', (e) => {
            const { formId, fieldName, value } = e.detail;
            this.stateManager.updateFormField(formId, fieldName, value);
        });
        
        document.addEventListener('form:submit', (e) => {
            const { formId } = e.detail;
            this.stateManager.submitForm(formId);
        });
    }
    
    setupNavigationIntegration() {
        // Handle navigation events
        document.addEventListener('navigation:item-click', (e) => {
            this.handleNavigationClick(e.detail);
        });
        
        document.addEventListener('navigation:search', (e) => {
            this.handleNavigationSearch(e.detail);
        });
        
        document.addEventListener('navigation:mobile-toggle', (e) => {
            this.handleMobileMenuToggle(e.detail);
        });
    }
    
    setupApplicationIntegrations() {
        // Setup drag and drop integration
        this.setupDragDropIntegration();
        
        // Setup progress tracking integration
        this.setupProgressTrackingIntegration();
        
        // Setup API client integration
        this.setupAPIClientIntegration();
        
        // Setup page-specific integrations
        this.setupPageSpecificIntegrations();
    }
    
    setupDragDropIntegration() {
        // Initialize drag-drop upload components
        const uploadAreas = document.querySelectorAll('[data-upload-area]');
        uploadAreas.forEach(area => {
            if (window.DragDropUpload) {
                const uploader = new window.DragDropUpload(area, {
                    uploadUrl: `${this.options.apiBaseUrl}/files/upload`,
                    onProgress: (progress) => {
                        this.handleUploadProgress(progress);
                    },
                    onComplete: (result) => {
                        this.handleUploadComplete(result);
                    },
                    onError: (error) => {
                        this.handleUploadError(error);
                    }
                });
                
                this.components.set(`uploader-${area.id}`, uploader);
            }
        });
    }
    
    setupProgressTrackingIntegration() {
        // Setup progress tracking for various operations
        document.addEventListener('operation:start', (e) => {
            this.startProgressTracking(e.detail);
        });
        
        document.addEventListener('operation:progress', (e) => {
            this.updateProgress(e.detail);
        });
        
        document.addEventListener('operation:complete', (e) => {
            this.completeProgress(e.detail);
        });
    }
    
    setupAPIClientIntegration() {
        // Setup API client if available
        if (window.UnifiedAPIClient) {
            this.apiClient = new window.UnifiedAPIClient({
                baseURL: this.options.apiBaseUrl,
                onProgress: (progress) => {
                    this.handleAPIProgress(progress);
                },
                onError: (error) => {
                    this.handleAPIError(error);
                }
            });
        }
    }
    
    setupPageSpecificIntegrations() {
        const currentPage = this.getCurrentPage();
        
        switch (currentPage) {
            case 'upload':
                this.setupUploadPageIntegration();
                break;
            case 'processing':
                this.setupProcessingPageIntegration();
                break;
            case 'results':
                this.setupResultsPageIntegration();
                break;
            case 'guides':
                this.setupGuidesPageIntegration();
                break;
            case 'dashboard':
                this.setupDashboardPageIntegration();
                break;
        }
    }
    
    setupEventHandlers() {
        // Setup global event handlers
        document.addEventListener('app:start-workflow', (e) => {
            this.startWorkflow(e.detail.workflowId, e.detail.options);
        });
        
        document.addEventListener('app:show-notification', (e) => {
            this.addNotification(e.detail);
        });
        
        document.addEventListener('app:navigate', (e) => {
            this.navigate(e.detail.url, e.detail.options);
        });
        
        // Handle responsive layout events
        document.addEventListener('layout:breakpoint-change', (e) => {
            this.stateManager.setState('app.breakpoint', e.detail.current);
        });
        
        document.addEventListener('layout:mobile-navigation', (e) => {
            this.handleMobileNavigationToggle(e.detail);
        });
    }
    
    setupKeyboardShortcuts() {
        // Global keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl+K: Focus search
            if (e.ctrlKey && e.key === 'k') {
                e.preventDefault();
                this.focusSearch();
            }
            
            // Ctrl+Shift+U: Start upload workflow
            if (e.ctrlKey && e.shiftKey && e.key === 'U') {
                e.preventDefault();
                this.startWorkflow('file-upload');
            }
            
            // Ctrl+Shift+P: Start processing workflow
            if (e.ctrlKey && e.shiftKey && e.key === 'P') {
                e.preventDefault();
                this.startWorkflow('ai-processing');
            }
            
            // Escape: Close modals/workflows
            if (e.key === 'Escape') {
                this.handleEscapeKey();
            }
        });
    }
    
    initializePageSpecificFeatures() {
        const currentPage = this.getCurrentPage();
        
        // Initialize features based on current page
        switch (currentPage) {
            case 'upload':
                this.initializeUploadFeatures();
                break;
            case 'processing':
                this.initializeProcessingFeatures();
                break;
            case 'results':
                this.initializeResultsFeatures();
                break;
            case 'guides':
                this.initializeGuidesFeatures();
                break;
            case 'dashboard':
                this.initializeDashboardFeatures();
                break;
        }
    }
    
    // Page-specific initialization methods
    initializeUploadFeatures() {
        // Auto-start upload workflow if files are detected in URL params
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('auto-upload') === 'true') {
            setTimeout(() => {
                this.startWorkflow('file-upload');
            }, 1000);
        }
    }
    
    initializeProcessingFeatures() {
        // Subscribe to processing updates
        this.websocketIntegration.subscribeToProgressUpdates((update) => {
            this.handleProcessingProgress(update);
        });
        
        // Check for active processing tasks
        this.checkActiveProcessingTasks();
    }
    
    initializeResultsFeatures() {
        // Initialize results filtering and sorting
        this.setupResultsFiltering();
        this.setupResultsSorting();
        
        // Load recent results
        this.loadRecentResults();
    }
    
    setupResultsFiltering() {
        // Initialize results filtering functionality
        const filterContainer = document.querySelector('.results-filters');
        if (filterContainer) {
            // Add filter event listeners
            const filterInputs = filterContainer.querySelectorAll('input, select');
            filterInputs.forEach(input => {
                input.addEventListener('change', () => {
                    this.applyResultsFilters();
                });
            });
        }
    }
    
    setupResultsSorting() {
        // Initialize results sorting functionality
        const sortControls = document.querySelectorAll('.sort-control');
        sortControls.forEach(control => {
            control.addEventListener('click', (e) => {
                const sortBy = e.target.dataset.sortBy;
                const sortOrder = e.target.dataset.sortOrder || 'asc';
                this.sortResults(sortBy, sortOrder);
            });
        });
    }
    
    applyResultsFilters() {
        // Apply filters to results table
        console.log('Applying results filters...');
        // Implementation would go here
    }
    
    sortResults(sortBy, sortOrder) {
        // Sort results table
        console.log(`Sorting results by ${sortBy} in ${sortOrder} order`);
        // Implementation would go here
    }
    
    loadRecentResults() {
        // Load recent grading results
        console.log('Loading recent results...');
        // Implementation would go here - could fetch from API
    }
    
    initializeGuidesFeatures() {
        // Initialize guide management features
        this.setupGuideManagement();
    }
    
    initializeDashboardFeatures() {
        // Initialize dashboard widgets
        this.initializeDashboardWidgets();
        
        // Subscribe to dashboard updates
        if (this.websocketIntegration && this.websocketIntegration.initialized) {
            // Get current user ID from state or session
            const userId = this.stateManager?.getState('app.user.id') || 'default';
            this.websocketIntegration.subscribeToDashboard(userId, (update) => {
                this.handleDashboardUpdate(update);
            });
        }
    }
    
    // Event handlers
    handleProgressUpdate(data) {
        this.stateManager.mergeState('processing.progress', {
            [data.sessionId]: data
        });
        
        // Update UI components
        document.dispatchEvent(new CustomEvent('app:progress-update', {
            detail: data
        }));
    }
    
    handleDashboardUpdate(data) {
        this.stateManager.mergeState('data.dashboard', data);
        
        // Update dashboard widgets
        document.dispatchEvent(new CustomEvent('app:dashboard-update', {
            detail: data
        }));
    }
    
    handleProcessingStatusUpdate(data) {
        this.stateManager.mergeState('processing.active', {
            [data.taskId]: data
        });
    }
    
    handleGlobalLoadingChange(isLoading) {
        document.body.classList.toggle('app-loading', isLoading);
        
        // Show/hide global loading indicator
        const loadingIndicator = document.getElementById('global-loading');
        if (loadingIndicator) {
            loadingIndicator.style.display = isLoading ? 'block' : 'none';
        }
    }
    
    handleNotificationsChange(notifications) {
        // Update notification display
        this.updateNotificationDisplay(notifications);
    }
    
    handleUserChange(user) {
        // Update user-specific UI elements
        this.updateUserInterface(user);
    }
    
    handleBreakpointChange(breakpoint) {
        // Handle responsive changes
        this.updateResponsiveFeatures(breakpoint);
    }
    
    // Workflow component renderers
    renderWorkflowComponent(detail) {
        const { step, container, data } = detail;
        
        switch (step.component) {
            case 'drag-drop-upload':
                this.renderDragDropUpload(container, data);
                break;
            case 'upload-config-form':
                this.renderUploadConfigForm(container, data);
                break;
            case 'progress-tracker':
                this.renderProgressTracker(container, data);
                break;
            case 'submission-selector':
                this.renderSubmissionSelector(container, data);
                break;
            case 'processing-config-form':
                this.renderProcessingConfigForm(container, data);
                break;
            case 'results-reviewer':
                this.renderResultsReviewer(container, data);
                break;
            default:
                this.renderGenericComponent(step, container, data);
        }
    }
    
    renderDragDropUpload(container, data) {
        if (!window.DragDropUpload) return;
        
        const uploader = new window.DragDropUpload(container, {
            uploadUrl: `${this.options.apiBaseUrl}/files/upload`,
            maxFiles: 10,
            maxFileSize: 50 * 1024 * 1024, // 50MB
            acceptedTypes: ['.pdf', '.jpg', '.jpeg', '.png'],
            onFilesSelected: (files) => {
                document.dispatchEvent(new CustomEvent('component:data-change', {
                    detail: { data: { files } }
                }));
            },
            onProgress: (progress) => {
                this.handleUploadProgress(progress);
            },
            onComplete: (result) => {
                this.handleUploadComplete(result);
            }
        });
        
        this.components.set('workflow-uploader', uploader);
    }
    
    renderUploadConfigForm(container, data) {
        if (!this.formComponents) return;
        
        const form = this.formComponents.createForm(container, {
            id: 'upload-config',
            fields: [
                {
                    name: 'examName',
                    type: 'text',
                    label: 'Exam Name',
                    required: true,
                    value: data.examName || ''
                },
                {
                    name: 'subject',
                    type: 'text',
                    label: 'Subject',
                    required: true,
                    value: data.subject || ''
                },
                {
                    name: 'markingGuide',
                    type: 'select',
                    label: 'Marking Guide',
                    required: true,
                    options: data.availableGuides || [],
                    value: data.markingGuide || ''
                }
            ],
            onSubmit: (formData) => {
                document.dispatchEvent(new CustomEvent('component:data-change', {
                    detail: { data: { config: formData, isValid: true } }
                }));
            },
            onChange: (formData, isValid) => {
                document.dispatchEvent(new CustomEvent('component:validation-change', {
                    detail: { isValid }
                }));
            }
        });
        
        this.components.set('workflow-upload-config', form);
    }
    
    renderProgressTracker(container, data) {
        if (!this.uiComponents) return;
        
        const progressBar = this.uiComponents.createProgressIndicator({
            value: data.progress || 0,
            max: 100,
            label: data.label || 'Processing...',
            showPercentage: true
        });
        
        container.appendChild(progressBar);
        
        // Subscribe to progress updates
        this.stateManager.subscribe('processing.progress', (progress) => {
            if (progress && progress.percentage !== undefined) {
                progressBar.setAttribute('value', progress.percentage);
            }
        });
        
        this.components.set('workflow-progress', progressBar);
    }
    
    // Utility methods
    getCurrentPage() {
        const path = window.location.pathname;
        if (path.includes('/upload')) return 'upload';
        if (path.includes('/processing')) return 'processing';
        if (path.includes('/results')) return 'results';
        if (path.includes('/guides')) return 'guides';
        return 'dashboard';
    }
    
    getCurrentUser() {
        // Get user from meta tag or API
        const userMeta = document.querySelector('meta[name="current-user"]');
        if (userMeta) {
            try {
                return JSON.parse(userMeta.content);
            } catch (e) {
                return null;
            }
        }
        return null;
    }
    
    startWorkflow(workflowId, options = {}) {
        if (this.workflows) {
            this.workflows.startWorkflow(workflowId, options);
        }
    }
    
    addNotification(notification) {
        const notifications = this.stateManager.getState('ui.notifications') || [];
        const newNotification = {
            id: Date.now().toString(),
            timestamp: new Date().toISOString(),
            ...notification
        };
        
        notifications.push(newNotification);
        this.stateManager.setState('ui.notifications', notifications);
        
        // Auto-remove after duration
        if (notification.duration) {
            setTimeout(() => {
                this.removeNotification(newNotification.id);
            }, notification.duration);
        }
    }
    
    removeNotification(id) {
        const notifications = this.stateManager.getState('ui.notifications') || [];
        const filtered = notifications.filter(n => n.id !== id);
        this.stateManager.setState('ui.notifications', filtered);
    }
    
    navigate(url, options = {}) {
        if (options.newTab) {
            window.open(url, '_blank');
        } else {
            window.location.href = url;
        }
    }
    
    focusSearch() {
        const searchInput = document.querySelector('.nav-search-input, input[type="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    handleEscapeKey() {
        // Close active workflow
        if (this.workflows && this.workflows.getActiveWorkflow()) {
            this.workflows.cancelWorkflow();
            return;
        }
        
        // Close modals
        const activeModal = document.querySelector('.modal.show, .workflow-container:not(.hidden)');
        if (activeModal) {
            const closeButton = activeModal.querySelector('.btn-close, .workflow-close');
            if (closeButton) {
                closeButton.click();
            }
        }
    }
    
    handleInitializationError(error) {
        console.error('App initialization failed:', error);
        
        // Show error notification
        this.addNotification({
            type: 'error',
            message: 'Application failed to initialize properly. Some features may not work.',
            duration: 10000
        });
        
        // Emit error event
        document.dispatchEvent(new CustomEvent('app:initialization-error', {
            detail: { error }
        }));
    }
    
    // Responsive layout integration
    onBreakpointChange(current, previous) {
        // Update state
        this.stateManager.setState('app.breakpoint', current);
        
        // Update components based on breakpoint
        this.updateComponentsForBreakpoint(current);
    }
    
    updateComponentsForBreakpoint(breakpoint) {
        // Update navigation for mobile/desktop
        if (this.navigation) {
            this.navigation.updateForBreakpoint(breakpoint);
        }
        
        // Update other components
        this.components.forEach((component, id) => {
            if (component.updateForBreakpoint) {
                component.updateForBreakpoint(breakpoint);
            }
        });
    }
    
    // Page-specific integration methods
    setupUploadPageIntegration() {
        // Initialize upload page specific features
        this.initializeFileUploadComponents();
        this.setupUploadValidation();
        this.setupUploadProgressTracking();
    }
    
    setupProcessingPageIntegration() {
        // Initialize processing page specific features
        this.initializeProcessingComponents();
        this.setupProcessingStatusTracking();
        this.setupProcessingControls();
    }
    
    setupResultsPageIntegration() {
        // Initialize results page specific features
        this.initializeResultsComponents();
        this.setupResultsViewer();
        this.setupResultsExport();
    }
    
    setupGuidesPageIntegration() {
        // Initialize guides page specific features
        this.initializeGuidesComponents();
        this.setupGuidesEditor();
        this.setupGuidesManagement();
    }
    
    setupDashboardPageIntegration() {
        // Initialize dashboard page specific features
        this.initializeDashboardFeatures();
        this.setupDashboardWidgets();
        this.setupDashboardStats();
    }
    
    // Notification display method
    updateNotificationDisplay(notifications) {
        const notificationContainer = document.querySelector('#notification-container') || 
                                    document.querySelector('.notification-container') ||
                                    document.querySelector('[data-notifications]');
        
        if (!notificationContainer) {
            // Create notification container if it doesn't exist
            const container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'fixed top-4 right-4 z-50 space-y-2';
            document.body.appendChild(container);
            return this.updateNotificationDisplay(notifications);
        }
        
        // Clear existing notifications
        notificationContainer.innerHTML = '';
        
        // Render each notification
        notifications.forEach(notification => {
            const notificationEl = this.createNotificationElement(notification);
            notificationContainer.appendChild(notificationEl);
        });
    }
    
    createNotificationElement(notification) {
        const el = document.createElement('div');
        el.className = `notification bg-white border-l-4 p-4 shadow-lg rounded-r-lg max-w-sm ${
            notification.type === 'error' ? 'border-red-500' :
            notification.type === 'warning' ? 'border-yellow-500' :
            notification.type === 'success' ? 'border-green-500' :
            'border-blue-500'
        }`;
        
        el.innerHTML = `
            <div class="flex justify-between items-start">
                <div class="flex-1">
                    ${notification.title ? `<h4 class="font-semibold text-gray-900">${notification.title}</h4>` : ''}
                    <p class="text-gray-700">${notification.message}</p>
                </div>
                <button class="ml-2 text-gray-400 hover:text-gray-600" onclick="this.parentElement.parentElement.remove()">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                </button>
            </div>
        `;
        
        return el;
    }
    
    // Helper methods for page-specific integrations
    initializeFileUploadComponents() {
        // Initialize file upload specific components
        const uploadAreas = document.querySelectorAll('[data-upload-area]');
        uploadAreas.forEach(area => {
            if (!area.dataset.initialized) {
                this.setupDragDropForElement(area);
                area.dataset.initialized = 'true';
            }
        });
    }
    
    setupUploadValidation() {
        // Setup file validation for uploads
        document.addEventListener('file:selected', (e) => {
            this.validateUploadFiles(e.detail.files);
        });
    }
    
    setupUploadProgressTracking() {
        // Setup progress tracking for uploads
        document.addEventListener('upload:progress', (e) => {
            this.updateUploadProgress(e.detail);
        });
    }
    
    initializeProcessingComponents() {
        // Initialize processing page components
        const processingControls = document.querySelectorAll('[data-processing-control]');
        processingControls.forEach(control => {
            if (!control.dataset.initialized) {
                this.setupProcessingControl(control);
                control.dataset.initialized = 'true';
            }
        });
    }
    
    setupProcessingStatusTracking() {
        // Setup status tracking for processing
        if (this.websocketIntegration) {
            this.websocketIntegration.subscribe('processing:status', (data) => {
                this.updateProcessingStatus(data);
            });
        }
    }
    
    setupProcessingControls() {
        // Setup processing control buttons
        document.addEventListener('processing:start', (e) => {
            this.startProcessing(e.detail);
        });
        
        document.addEventListener('processing:stop', (e) => {
            this.stopProcessing(e.detail);
        });
    }
    
    initializeResultsComponents() {
        // Initialize results page components
        const resultsViewers = document.querySelectorAll('[data-results-viewer]');
        resultsViewers.forEach(viewer => {
            if (!viewer.dataset.initialized) {
                this.setupResultsViewer(viewer);
                viewer.dataset.initialized = 'true';
            }
        });
    }
    
    setupResultsViewer() {
        // Setup results viewing functionality
        document.addEventListener('results:view', (e) => {
            this.displayResults(e.detail);
        });
    }
    
    setupResultsExport() {
        // Setup results export functionality
        document.addEventListener('results:export', (e) => {
            this.exportResults(e.detail);
        });
    }
    
    initializeGuidesComponents() {
        // Initialize guides page components
        const guidesEditors = document.querySelectorAll('[data-guides-editor]');
        guidesEditors.forEach(editor => {
            if (!editor.dataset.initialized) {
                this.setupGuidesEditor(editor);
                editor.dataset.initialized = 'true';
            }
        });
    }
    
    setupGuidesEditor() {
        // Setup guides editing functionality
        document.addEventListener('guides:edit', (e) => {
            this.editGuide(e.detail);
        });
    }
    
    setupGuidesManagement() {
        // Setup guides management functionality
        document.addEventListener('guides:save', (e) => {
            this.saveGuide(e.detail);
        });
        
        document.addEventListener('guides:delete', (e) => {
            this.deleteGuide(e.detail);
        });
    }
    
    setupDashboardWidgets() {
        // Setup dashboard widgets
        const widgets = document.querySelectorAll('[data-dashboard-widget]');
        widgets.forEach(widget => {
            if (!widget.dataset.initialized) {
                this.initializeDashboardWidget(widget);
                widget.dataset.initialized = 'true';
            }
        });
    }
    
    setupDashboardStats() {
        // Setup dashboard statistics
        if (this.websocketIntegration) {
            this.websocketIntegration.subscribe('dashboard:stats', (data) => {
                this.updateDashboardStats(data);
            });
        }
    }
    
    // User interface update methods
    updateUserInterface(user) {
        // Update user-specific UI elements
        const userElements = document.querySelectorAll('[data-user-info]');
        userElements.forEach(element => {
            if (element.dataset.userField && user[element.dataset.userField]) {
                element.textContent = user[element.dataset.userField];
            }
        });
        
        // Update user avatar if present
        const avatarElements = document.querySelectorAll('[data-user-avatar]');
        avatarElements.forEach(element => {
            if (user.avatar) {
                element.src = user.avatar;
            }
        });
        
        // Update user role-based visibility
        const roleElements = document.querySelectorAll('[data-role-visibility]');
        roleElements.forEach(element => {
            const requiredRoles = element.dataset.roleVisibility.split(',');
            const hasRole = requiredRoles.some(role => user.roles && user.roles.includes(role.trim()));
            element.style.display = hasRole ? '' : 'none';
        });
    }
    
    updateResponsiveFeatures(breakpoint) {
        // Update responsive features based on breakpoint
        document.body.dataset.breakpoint = breakpoint;
        
        // Update navigation for mobile/desktop
        const mobileNav = document.querySelector('[data-mobile-nav]');
        const desktopNav = document.querySelector('[data-desktop-nav]');
        
        if (breakpoint === 'mobile' || breakpoint === 'tablet') {
            if (mobileNav) mobileNav.style.display = 'block';
            if (desktopNav) desktopNav.style.display = 'none';
        } else {
            if (mobileNav) mobileNav.style.display = 'none';
            if (desktopNav) desktopNav.style.display = 'block';
        }
        
        // Update responsive components
        const responsiveElements = document.querySelectorAll('[data-responsive]');
        responsiveElements.forEach(element => {
            const config = JSON.parse(element.dataset.responsive || '{}');
            if (config[breakpoint]) {
                Object.assign(element.style, config[breakpoint]);
            }
        });
        
        // Dispatch responsive change event
        document.dispatchEvent(new CustomEvent('app:responsive-change', {
            detail: { breakpoint }
        }));
    }
    
    setupDragDropForElement(element) {
        // Setup drag and drop functionality for an element
        if (!element) return;
        
        element.addEventListener('dragover', (e) => {
            e.preventDefault();
            element.classList.add('drag-over');
        });
        
        element.addEventListener('dragleave', (e) => {
            e.preventDefault();
            element.classList.remove('drag-over');
        });
        
        element.addEventListener('drop', (e) => {
            e.preventDefault();
            element.classList.remove('drag-over');
            
            const files = Array.from(e.dataTransfer.files);
            if (files.length > 0) {
                document.dispatchEvent(new CustomEvent('file:selected', {
                    detail: { files, element }
                }));
            }
        });
        
        // Also handle click to select files
        element.addEventListener('click', () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.multiple = true;
            input.accept = element.dataset.accept || '*';
            
            input.addEventListener('change', (e) => {
                const files = Array.from(e.target.files);
                if (files.length > 0) {
                    document.dispatchEvent(new CustomEvent('file:selected', {
                        detail: { files, element }
                    }));
                }
            });
            
            input.click();
        });
    }
    
    // Stub methods for functionality that may be implemented elsewhere
    validateUploadFiles(files) { /* Implementation depends on specific requirements */ }
    updateUploadProgress(progress) { /* Implementation depends on specific requirements */ }
    setupProcessingControl(control) { /* Implementation depends on specific requirements */ }
    updateProcessingStatus(data) { /* Implementation depends on specific requirements */ }
    startProcessing(data) { /* Implementation depends on specific requirements */ }
    stopProcessing(data) { /* Implementation depends on specific requirements */ }
    displayResults(data) { /* Implementation depends on specific requirements */ }
    exportResults(data) { /* Implementation depends on specific requirements */ }
    setupGuidesEditor(editor) { /* Implementation depends on specific requirements */ }
    editGuide(data) { /* Implementation depends on specific requirements */ }
    saveGuide(data) { /* Implementation depends on specific requirements */ }
    deleteGuide(data) { /* Implementation depends on specific requirements */ }
    initializeDashboardWidget(widget) { /* Implementation depends on specific requirements */ }
    initializeDashboardWidgets() { 
        // Initialize all dashboard widgets
        const widgets = document.querySelectorAll('.dashboard-widget');
        widgets.forEach(widget => this.initializeDashboardWidget(widget));
    }
    updateDashboardStats(data) { /* Implementation depends on specific requirements */ }
    
    // Public API
    getComponent(id) {
        return this.components.get(id);
    }
    
    registerComponent(id, component) {
        this.components.set(id, component);
    }
    
    unregisterComponent(id) {
        const component = this.components.get(id);
        if (component && component.destroy) {
            component.destroy();
        }
        this.components.delete(id);
    }
    
    isInitialized() {
        return this.initialized;
    }
    
    // Cleanup
    destroy() {
        // Destroy all components
        this.components.forEach((component, id) => {
            if (component.destroy) {
                component.destroy();
            }
        });
        this.components.clear();
        
        // Cleanup state subscriptions
        if (this.stateManager) {
            // State manager handles its own cleanup
        }
        
        // Cleanup WebSocket
        if (this.websocketClient) {
            this.websocketClient.disconnect();
        }
        
        // Cleanup responsive layout
        if (this.responsiveLayout) {
            this.responsiveLayout.unregisterComponent('app');
        }
        
        this.initialized = false;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ExamGraderApp;
}

// Global initialization
if (typeof window !== 'undefined') {
    window.ExamGraderApp = ExamGraderApp;
    
    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.examGraderApp = new ExamGraderApp();
        });
    } else {
        window.examGraderApp = new ExamGraderApp();
    }
}