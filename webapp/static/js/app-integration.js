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
            await this.initializeStateManagement();
            await this.initializeWebSocket();
            await this.initializeResponsiveLayout();
            await this.initializeUIComponents();
            await this.initializeWorkflows();
            await this.initializeFormComponents();
            await this.initializeNavigation();

            this.setupApplicationIntegrations();
            this.setupEventHandlers();
            this.setupKeyboardShortcuts();
            this.initializePageSpecificFeatures();

            this.initialized = true;

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
        this.stateManager = window.stateManager;
        this.setupApplicationState();
        this.subscribeToStateChanges();
    }

    async initializeWebSocket() {
        if (!this.options.enableWebSocket) return;

        if (!window.WebSocketIntegration) {
            this.websocketIntegration = this.createSimpleWebSocketIntegration();
        } else {
            this.websocketIntegration = new window.WebSocketIntegration();
        }

        this.websocketClient = this.websocketIntegration.initialize({
            url: this.options.websocketUrl,
            autoConnect: true,
            enableReconnection: true
        });

        this.setupWebSocketHandlers();
    }

    createSimpleWebSocketIntegration() {
        return {
            initialized: false,
            initialize: (options) => {
                this.initialized = true;
                return {
                    on: (event, callback) => {
                        console.log(`WebSocket event registered: ${event}`);
                    }
                };
            },
            subscribeToProgressUpdates: (callback) => {
                console.log('Subscribed to progress updates');
            },
            subscribeToDashboard: (userId, callback) => {
                console.log(`Subscribed to dashboard updates for user: ${userId}`);
            },
            subscribe: (event, callback) => {
                console.log(`Subscribed to WebSocket event: ${event}`);
            }
        };
    }

    async initializeResponsiveLayout() {
        if (!this.options.enableResponsiveLayout || !window.ResponsiveLayout) return;
        this.responsiveLayout = window.responsiveLayout;
        if (this.responsiveLayout) {
            this.responsiveLayout.registerComponent('app', this);
        }
    }

    async initializeUIComponents() {
        if (!window.UIComponents) return;
        this.uiComponents = new window.UIComponents();
        this.setupComponentEventHandlers();
    }
    async initializeWorkflows() {
        if (!this.options.enableWorkflows || !window.UIWorkflows) return;
        this.workflows = window.uiWorkflows;
        this.setupWorkflowComponentRenderers();
    }

    async initializeFormComponents() {
        if (!window.FormComponents) return;
        this.formComponents = new window.FormComponents();
        this.setupFormStateIntegration();
    }

    async initializeNavigation() {
        if (!window.NavigationComponent) return;
        this.navigation = new window.NavigationComponent();
        this.setupNavigationIntegration();
    }

    setupApplicationState() {
        if (!this.stateManager) return;

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
        if (!this.stateManager) return;

        this.stateManager.subscribe('ui.loading.global', (isLoading) => {
            this.handleGlobalLoadingChange(isLoading);
        });

        this.stateManager.subscribe('ui.notifications', (notifications) => {
            this.handleNotificationsChange(notifications);
        });

        this.stateManager.subscribe('app.user', (user) => {
            this.handleUserChange(user);
        });

        this.stateManager.subscribe('app.breakpoint', (breakpoint) => {
            this.handleBreakpointChange(breakpoint);
        });
    }

    setupWebSocketHandlers() {
        if (!this.websocketClient) return;

        this.websocketClient.on('progress_update', (data) => {
            this.handleProgressUpdate(data);
        });

        this.websocketClient.on('dashboard_update', (data) => {
            this.handleDashboardUpdate(data);
        });

        this.websocketClient.on('processing_status', (data) => {
            this.handleProcessingStatusUpdate(data);
        });

        this.websocketClient.on('notification', (data) => {
            this.addNotification(data);
        });

        this.websocketClient.on('connect', () => {
            if (this.stateManager) {
                this.stateManager.setState('websocket.connected', true);
            }
            this.addNotification({
                type: 'success',
                message: 'Connected to real-time updates',
                duration: 3000
            });
        });

        this.websocketClient.on('disconnect', () => {
            if (this.stateManager) {
                this.stateManager.setState('websocket.connected', false);
            }
            this.addNotification({
                type: 'warning',
                message: 'Disconnected from real-time updates',
                duration: 5000
            });
        });
    }

    setupComponentEventHandlers() {
        document.addEventListener('component:created', (e) => {
            this.handleComponentCreated(e.detail);
        });

        document.addEventListener('component:destroyed', (e) => {
            this.handleComponentDestroyed(e.detail);
        });

        document.addEventListener('component:state-change', (e) => {
            this.handleComponentStateChange(e.detail);
        });
    }

    setupWorkflowComponentRenderers() {
        document.addEventListener('workflow:render-component', (e) => {
            this.renderWorkflowComponent(e.detail);
        });

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
        if (!this.stateManager) return;

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
        this.setupDragDropIntegration();
        this.setupProgressTrackingIntegration();
        this.setupAPIClientIntegration();
        this.setupPageSpecificIntegrations();
    }

    setupDragDropIntegration() {
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
        document.addEventListener('app:start-workflow', (e) => {
            this.startWorkflow(e.detail.workflowId, e.detail.options);
        });

        document.addEventListener('app:show-notification', (e) => {
            this.addNotification(e.detail);
        });

        document.addEventListener('app:navigate', (e) => {
            this.navigate(e.detail.url, e.detail.options);
        });

        document.addEventListener('layout:breakpoint-change', (e) => {
            if (this.stateManager) {
                this.stateManager.setState('app.breakpoint', e.detail.current);
            }
        });

        document.addEventListener('layout:mobile-navigation', (e) => {
            this.handleMobileNavigationToggle(e.detail);
        });
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'k') {
                e.preventDefault();
                this.focusSearch();
            }

            if (e.ctrlKey && e.shiftKey && e.key === 'U') {
                e.preventDefault();
                this.startWorkflow('file-upload');
            }

            if (e.ctrlKey && e.shiftKey && e.key === 'P') {
                e.preventDefault();
                this.startWorkflow('ai-processing');
            }

            if (e.key === 'Escape') {
                this.handleEscapeKey();
            }
        });
    }
    initializePageSpecificFeatures() {
        const currentPage = this.getCurrentPage();

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

    initializeUploadFeatures() {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('auto-upload') === 'true') {
            setTimeout(() => {
                this.startWorkflow('file-upload');
            }, 1000);
        }
    }

    initializeProcessingFeatures() {
        if (this.websocketIntegration && this.websocketIntegration.subscribeToProgressUpdates) {
            this.websocketIntegration.subscribeToProgressUpdates((update) => {
                this.handleProcessingProgress(update);
            });
        }

        this.checkActiveProcessingTasks();
    }

    initializeResultsFeatures() {
        this.setupResultsFiltering();
        this.setupResultsSorting();
        this.loadRecentResults();
    }

    setupResultsFiltering() {
        const filterContainer = document.querySelector('.results-filters');
        if (filterContainer) {
            const filterInputs = filterContainer.querySelectorAll('input, select');
            filterInputs.forEach(input => {
                input.addEventListener('change', () => {
                    this.applyResultsFilters();
                });
            });
        }
    }

    setupResultsSorting() {
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
        console.log('Applying results filters...');
    }

    sortResults(sortBy, sortOrder) {
        console.log(`Sorting results by ${sortBy} in ${sortOrder} order`);
    }

    loadRecentResults() {
        console.log('Loading recent results...');
    }

    initializeGuidesFeatures() {
        this.setupGuideManagement();
    }

    setupGuideManagement() {
        console.log('Setting up guide management');

        const createGuideBtn = document.querySelector('[data-action="create-guide"]');
        if (createGuideBtn) {
            createGuideBtn.addEventListener('click', () => {
                this.startWorkflow('create-guide');
            });
        }

        const editGuideBtns = document.querySelectorAll('[data-action="edit-guide"]');
        editGuideBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const guideId = e.target.dataset.guideId;
                this.startWorkflow('edit-guide', { guideId });
            });
        });

        const deleteGuideBtns = document.querySelectorAll('[data-action="delete-guide"]');
        deleteGuideBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const guideId = e.target.dataset.guideId;
                this.confirmDeleteGuide(guideId);
            });
        });
    }

    confirmDeleteGuide(guideId) {
        if (confirm('Are you sure you want to delete this guide?')) {
            this.deleteGuide(guideId);
        }
    }

    async deleteGuide(guideId) {
        try {
            if (this.apiClient) {
                await this.apiClient.delete(`/guides/${guideId}`);
                this.addNotification({
                    type: 'success',
                    message: 'Guide deleted successfully',
                    duration: 3000
                });
                window.location.reload();
            }
        } catch (error) {
            this.addNotification({
                type: 'error',
                message: 'Failed to delete guide',
                duration: 5000
            });
        }
    }

    initializeDashboardFeatures() {
        this.initializeDashboardWidgets();

        if (this.websocketIntegration && this.websocketIntegration.initialized) {
            const userId = this.stateManager?.getState('app.user.id') || 'default';
            this.websocketIntegration.subscribeToDashboard(userId, (update) => {
                this.handleDashboardUpdate(update);
            });
        }
    }

    // Event handlers
    handleProgressUpdate(data) {
        if (this.stateManager) {
            this.stateManager.mergeState('processing.progress', {
                [data.sessionId]: data
            });
        }

        document.dispatchEvent(new CustomEvent('app:progress-update', {
            detail: data
        }));
    }

    handleDashboardUpdate(data) {
        if (this.stateManager) {
            this.stateManager.mergeState('data.dashboard', data);
        }

        document.dispatchEvent(new CustomEvent('app:dashboard-update', {
            detail: data
        }));
    }
    handleProcessingStatusUpdate(data) {
        if (this.stateManager) {
            this.stateManager.mergeState('processing.active', {
                [data.taskId]: data
            });
        }
    }

    handleGlobalLoadingChange(isLoading) {
        document.body.classList.toggle('app-loading', isLoading);

        const loadingIndicator = document.getElementById('global-loading');
        if (loadingIndicator) {
            loadingIndicator.style.display = isLoading ? 'block' : 'none';
        }
    }

    handleNotificationsChange(notifications) {
        this.updateNotificationDisplay(notifications);
    }

    handleUserChange(user) {
        this.updateUserInterface(user);
    }

    handleBreakpointChange(breakpoint) {
        this.updateResponsiveFeatures(breakpoint);
    }

    handleEscapeKey() {
        if (this.workflows && this.workflows.getActiveWorkflow) {
            this.workflows.cancelWorkflow();
            return;
        }

        const activeModal = document.querySelector('.modal.show, .workflow-container:not(.hidden)');
        if (activeModal) {
            const closeButton = activeModal.querySelector('.btn-close, .workflow-close');
            if (closeButton) {
                closeButton.click();
            }
        }
    }

    handleComponentCreated(detail) {
        console.log('Component created:', detail);
        if (detail && detail.id && detail.component) {
            this.components.set(detail.id, detail.component);
        }
    }

    handleComponentDestroyed(detail) {
        console.log('Component destroyed:', detail);
        if (detail && detail.id) {
            this.components.delete(detail.id);
        }
    }
    handleComponentStateChange(detail) {
        console.log('Component state changed:', detail);
    }

    handleWorkflowStarted(detail) {
        console.log('Workflow started:', detail);
        if (this.stateManager && detail && detail.workflowId) {
            this.stateManager.setState('ui.activeWorkflow', detail.workflowId);
        }
    }

    handleWorkflowCompleted(detail) {
        console.log('Workflow completed:', detail);
        if (this.stateManager) {
            this.stateManager.setState('ui.activeWorkflow', null);
        }
    }

    handleWorkflowCancelled(detail) {
        console.log('Workflow cancelled:', detail);
        if (this.stateManager) {
            this.stateManager.setState('ui.activeWorkflow', null);
        }
    }

    handleNavigationClick(detail) {
        console.log('Navigation clicked:', detail);
        if (detail && detail.url) {
            this.navigate(detail.url, detail.options);
        }
    }

    handleNavigationSearch(detail) {
        console.log('Navigation search:', detail);
    }

    handleMobileMenuToggle(detail) {
        console.log('Mobile menu toggled:', detail);
    }

    handleMobileNavigationToggle(detail) {
        console.log('Mobile navigation toggled:', detail);
    }

    handleUploadProgress(progress) {
        console.log('Upload progress:', progress);
        if (this.stateManager) {
            this.stateManager.mergeState('upload.progress', progress);
        }
    }

    handleUploadComplete(result) {
        console.log('Upload complete:', result);
        this.addNotification({
            type: 'success',
            message: 'Upload completed successfully',
            duration: 3000
        });
    }
    handleUploadError(error) {
        console.error('Upload error:', error);
        this.addNotification({
            type: 'error',
            message: 'Upload failed: ' + (error.message || error),
            duration: 5000
        });
    }

    handleProcessingProgress(update) {
        console.log('Processing progress:', update);
        if (this.stateManager) {
            this.stateManager.mergeState('processing.progress', update);
        }
    }

    handleAPIProgress(progress) {
        console.log('API progress:', progress);
    }

    handleAPIError(error) {
        console.error('API error:', error);
        this.addNotification({
            type: 'error',
            message: 'API request failed: ' + (error.message || error),
            duration: 5000
        });
    }

    startProgressTracking(detail) {
        console.log('Starting progress tracking:', detail);
        if (this.stateManager && detail && detail.id) {
            this.stateManager.setState(`ui.loading.components.${detail.id}`, true);
        }
    }

    updateProgress(detail) {
        console.log('Updating progress:', detail);
        if (this.stateManager && detail && detail.id) {
            this.stateManager.mergeState('processing.progress', {
                [detail.id]: detail.progress
            });
        }
    }

    completeProgress(detail) {
        console.log('Completing progress:', detail);
        if (this.stateManager && detail && detail.id) {
            this.stateManager.setState(`ui.loading.components.${detail.id}`, false);
        }
    }

    checkActiveProcessingTasks() {
        console.log('Checking active processing tasks');
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
        if (this.workflows && this.workflows.startWorkflow) {
            this.workflows.startWorkflow(workflowId, options);
        }
    }

    addNotification(notification) {
        if (!notification) return;

        const notifications = this.stateManager?.getState('ui.notifications') || [];
        const newNotification = {
            id: Date.now().toString(),
            timestamp: new Date().toISOString(),
            ...notification
        };

        notifications.push(newNotification);
        if (this.stateManager) {
            this.stateManager.setState('ui.notifications', notifications);
        }

        if (notification.duration) {
            setTimeout(() => {
                this.removeNotification(newNotification.id);
            }, notification.duration);
        }
    }

    removeNotification(id) {
        if (!this.stateManager) return;

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

    handleInitializationError(error) {
        console.error('App initialization failed:', error);

        this.addNotification({
            type: 'error',
            message: 'Application failed to initialize properly. Some features may not work.',
            duration: 10000
        });

        document.dispatchEvent(new CustomEvent('app:initialization-error', {
            detail: { error }
        }));
    }

    // Page-specific integration methods
    setupUploadPageIntegration() {
        this.initializeFileUploadComponents();
        this.setupUploadValidation();
        this.setupUploadProgressTracking();
    }

    setupProcessingPageIntegration() {
        this.initializeProcessingComponents();
        this.setupProcessingStatusTracking();
        this.setupProcessingControls();
    }

    setupResultsPageIntegration() {
        this.initializeResultsComponents();
        this.setupResultsViewer();
        this.setupResultsExport();
    }

    setupGuidesPageIntegration() {
        this.initializeGuidesComponents();
        this.setupGuidesEditor();
        this.setupGuidesManagement();
    }

    setupDashboardPageIntegration() {
        this.initializeDashboardFeatures();
        this.setupDashboardWidgets();
        this.setupDashboardStats();
    }

    initializeFileUploadComponents() {
        console.log('Initializing file upload components');
    }

    setupUploadValidation() {
        console.log('Setting up upload validation');
    }

    setupUploadProgressTracking() {
        console.log('Setting up upload progress tracking');
    }

    initializeProcessingComponents() {
        console.log('Initializing processing components');
    }

    setupProcessingStatusTracking() {
        console.log('Setting up processing status tracking');
        if (this.websocketIntegration && this.websocketIntegration.subscribe) {
            this.websocketIntegration.subscribe('processing:status', (data) => {
                this.updateProcessingStatus(data);
            });
        }
    }

    setupProcessingControls() {
        console.log('Setting up processing controls');
    }

    initializeResultsComponents() {
        console.log('Initializing results components');
    }

    setupResultsViewer() {
        console.log('Setting up results viewer');
    }

    setupResultsExport() {
        console.log('Setting up results export');
    }

    initializeGuidesComponents() {
        console.log('Initializing guides components');
    }

    setupGuidesEditor() {
        console.log('Setting up guides editor');
    }

    setupGuidesManagement() {
        console.log('Setting up guides management');
    }

    initializeDashboardWidgets() {
        console.log('Initializing dashboard widgets');
    }

    setupDashboardWidgets() {
        console.log('Setting up dashboard widgets');
    }

    setupDashboardStats() {
        console.log('Setting up dashboard stats');
        if (this.websocketIntegration && this.websocketIntegration.subscribe) {
            this.websocketIntegration.subscribe('dashboard:stats', (data) => {
                this.updateDashboardStats(data);
            });
        }
    }

    updateProcessingStatus(data) {
        console.log('Updating processing status:', data);
        if (this.stateManager) {
            this.stateManager.mergeState('processing.status', data);
        }
    }

    updateDashboardStats(data) {
        console.log('Updating dashboard stats:', data);
        if (this.stateManager) {
            this.stateManager.mergeState('dashboard.stats', data);
        }
    }

    updateNotificationDisplay(notifications) {
        console.log('Updating notification display:', notifications);
        const container = document.querySelector('#notification-container') ||
            document.querySelector('.notification-container');

        if (!container) {
            const newContainer = document.createElement('div');
            newContainer.id = 'notification-container';
            newContainer.className = 'fixed top-4 right-4 z-50 space-y-2';
            document.body.appendChild(newContainer);
        }
    }

    updateUserInterface(user) {
        console.log('Updating user interface:', user);
    }

    updateResponsiveFeatures(breakpoint) {
        console.log('Updating responsive features:', breakpoint);
    }

    renderWorkflowComponent(detail) {
        if (!detail) return;

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
            default:
                this.renderGenericComponent(step, container, data);
        }
    } rende
    rDragDropUpload(container, data) {
        if (!window.DragDropUpload || !container) return;

        const uploader = new window.DragDropUpload(container, {
            uploadUrl: `${this.options.apiBaseUrl}/files/upload`,
            maxFiles: 10,
            maxFileSize: 50 * 1024 * 1024,
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
        if (!this.formComponents || !container) return;

        const form = this.formComponents.createForm(container, {
            id: 'upload-config',
            fields: [
                {
                    name: 'examName',
                    type: 'text',
                    label: 'Exam Name',
                    required: true,
                    value: data?.examName || ''
                }
            ],
            onSubmit: (formData) => {
                document.dispatchEvent(new CustomEvent('component:data-change', {
                    detail: { data: { config: formData, isValid: true } }
                }));
            }
        });

        this.components.set('workflow-upload-config', form);
    }

    renderProgressTracker(container, data) {
        if (!this.uiComponents || !container) return;

        const progressBar = this.uiComponents.createProgressIndicator({
            value: data?.progress || 0,
            max: 100,
            label: data?.label || 'Processing...',
            showPercentage: true
        });

        container.appendChild(progressBar);
        this.components.set('workflow-progress', progressBar);
    }
    renderGenericComponent(step, container, data) {
        console.log('Rendering generic component:', step);
        if (!container) return;

        const div = document.createElement('div');
        div.className = 'generic-component';
        div.textContent = `Component: ${step?.component || 'Unknown'}`;
        container.appendChild(div);
    }

    // Cleanup method
    destroy() {
        this.components.forEach((component, id) => {
            if (component.destroy) {
                component.destroy();
            }
        });
        this.components.clear();

        if (this.websocketClient && this.websocketClient.disconnect) {
            this.websocketClient.disconnect();
        }

        if (this.responsiveLayout && this.responsiveLayout.unregisterComponent) {
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