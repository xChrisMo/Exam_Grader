/**
 * UI Workflows System
 * Orchestrates complete user interface workflows by integrating all components,
 * state management, and providing guided user experiences
 */

class UIWorkflows {
    constructor(options = {}) {
        this.options = {
            enableGuidedTours: true,
            enableKeyboardShortcuts: true,
            enableProgressTracking: true,
            enableAutoSave: true,
            autoSaveInterval: 30000, // 30 seconds
            enableNotifications: true,
            ...options
        };
        
        this.workflows = new Map();
        this.activeWorkflow = null;
        this.workflowHistory = [];
        this.shortcuts = new Map();
        this.autoSaveTimers = new Map();
        
        this.init();
    }
    
    init() {
        this.setupWorkflows();
        this.bindEvents();
        this.setupKeyboardShortcuts();
        this.initializeComponents();
    }
    
    setupWorkflows() {
        // File Upload Workflow
        this.registerWorkflow('file-upload', {
            name: 'File Upload',
            description: 'Upload and process exam submissions',
            steps: [
                {
                    id: 'select-files',
                    title: 'Select Files',
                    description: 'Choose files to upload',
                    component: 'drag-drop-upload',
                    validation: (data) => data.files && data.files.length > 0
                },
                {
                    id: 'configure-upload',
                    title: 'Configure Upload',
                    description: 'Set upload options and metadata',
                    component: 'upload-config-form',
                    validation: (data) => data.config && data.config.isValid
                },
                {
                    id: 'upload-progress',
                    title: 'Upload Progress',
                    description: 'Monitor upload progress',
                    component: 'progress-tracker',
                    autoAdvance: true
                },
                {
                    id: 'upload-complete',
                    title: 'Upload Complete',
                    description: 'Review uploaded files',
                    component: 'upload-summary',
                    final: true
                }
            ]
        });
        
        // AI Processing Workflow
        this.registerWorkflow('ai-processing', {
            name: 'AI Processing',
            description: 'Process submissions with AI grading',
            steps: [
                {
                    id: 'select-submissions',
                    title: 'Select Submissions',
                    description: 'Choose submissions to process',
                    component: 'submission-selector',
                    validation: (data) => data.submissions && data.submissions.length > 0
                },
                {
                    id: 'configure-processing',
                    title: 'Configure Processing',
                    description: 'Set AI processing parameters',
                    component: 'processing-config-form',
                    validation: (data) => data.config && data.config.isValid
                },
                {
                    id: 'processing-progress',
                    title: 'Processing Progress',
                    description: 'Monitor AI processing',
                    component: 'processing-tracker',
                    autoAdvance: true
                },
                {
                    id: 'review-results',
                    title: 'Review Results',
                    description: 'Review and approve AI results',
                    component: 'results-reviewer',
                    validation: (data) => data.reviewed === true
                },
                {
                    id: 'processing-complete',
                    title: 'Processing Complete',
                    description: 'View final results',
                    component: 'results-summary',
                    final: true
                }
            ]
        });
        
        // Marking Guide Creation Workflow
        this.registerWorkflow('create-marking-guide', {
            name: 'Create Marking Guide',
            description: 'Create a new marking guide',
            steps: [
                {
                    id: 'guide-details',
                    title: 'Guide Details',
                    description: 'Enter basic guide information',
                    component: 'guide-details-form',
                    validation: (data) => data.title && data.description
                },
                {
                    id: 'add-criteria',
                    title: 'Add Criteria',
                    description: 'Define marking criteria',
                    component: 'criteria-builder',
                    validation: (data) => data.criteria && data.criteria.length > 0
                },
                {
                    id: 'set-weights',
                    title: 'Set Weights',
                    description: 'Assign weights to criteria',
                    component: 'weight-setter',
                    validation: (data) => Math.abs(data.totalWeight - 100) < 0.01
                },
                {
                    id: 'preview-guide',
                    title: 'Preview Guide',
                    description: 'Review the complete guide',
                    component: 'guide-preview',
                    validation: (data) => data.approved === true
                },
                {
                    id: 'save-guide',
                    title: 'Save Guide',
                    description: 'Save the marking guide',
                    component: 'guide-saver',
                    final: true
                }
            ]
        });
        
        // Results Review Workflow
        this.registerWorkflow('review-results', {
            name: 'Review Results',
            description: 'Review and finalize grading results',
            steps: [
                {
                    id: 'select-batch',
                    title: 'Select Batch',
                    description: 'Choose results batch to review',
                    component: 'batch-selector',
                    validation: (data) => data.batchId
                },
                {
                    id: 'review-individual',
                    title: 'Review Individual Results',
                    description: 'Review each submission result',
                    component: 'individual-reviewer',
                    repeatable: true
                },
                {
                    id: 'batch-summary',
                    title: 'Batch Summary',
                    description: 'Review batch statistics',
                    component: 'batch-summary',
                    validation: (data) => data.reviewed === true
                },
                {
                    id: 'finalize-results',
                    title: 'Finalize Results',
                    description: 'Finalize and export results',
                    component: 'results-finalizer',
                    final: true
                }
            ]
        });
        
        // Settings Configuration Workflow
        this.registerWorkflow('configure-settings', {
            name: 'Configure Settings',
            description: 'Configure application settings',
            steps: [
                {
                    id: 'general-settings',
                    title: 'General Settings',
                    description: 'Configure general preferences',
                    component: 'general-settings-form'
                },
                {
                    id: 'ai-settings',
                    title: 'AI Settings',
                    description: 'Configure AI processing settings',
                    component: 'ai-settings-form'
                },
                {
                    id: 'notification-settings',
                    title: 'Notification Settings',
                    description: 'Configure notification preferences',
                    component: 'notification-settings-form'
                },
                {
                    id: 'save-settings',
                    title: 'Save Settings',
                    description: 'Save configuration changes',
                    component: 'settings-saver',
                    final: true
                }
            ]
        });
    }
    
    bindEvents() {
        // Listen for workflow events
        document.addEventListener('workflow:start', (e) => {
            this.startWorkflow(e.detail.workflowId, e.detail.options);
        });
        
        document.addEventListener('workflow:next', (e) => {
            this.nextStep(e.detail.data);
        });
        
        document.addEventListener('workflow:previous', () => {
            this.previousStep();
        });
        
        document.addEventListener('workflow:cancel', () => {
            this.cancelWorkflow();
        });
        
        document.addEventListener('workflow:complete', (e) => {
            this.completeWorkflow(e.detail.data);
        });
        
        // Listen for component events
        document.addEventListener('component:data-change', (e) => {
            this.handleComponentDataChange(e.detail);
        });
        
        document.addEventListener('component:validation-change', (e) => {
            this.handleValidationChange(e.detail);
        });
        
        // Listen for state changes
        if (window.stateManager) {
            window.stateManager.subscribe('ui.activeWorkflow', (workflow) => {
                this.handleWorkflowStateChange(workflow);
            });
        }
        
        // Auto-save handling
        if (this.options.enableAutoSave) {
            document.addEventListener('workflow:data-change', (e) => {
                this.scheduleAutoSave(e.detail);
            });
        }
    }
    
    setupKeyboardShortcuts() {
        if (!this.options.enableKeyboardShortcuts) return;
        
        // Register common shortcuts
        this.registerShortcut('ctrl+enter', () => this.nextStep());
        this.registerShortcut('ctrl+shift+enter', () => this.previousStep());
        this.registerShortcut('escape', () => this.cancelWorkflow());
        this.registerShortcut('ctrl+s', (e) => {
            e.preventDefault();
            this.saveWorkflowData();
        });
        
        // Bind keyboard events
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcut(e);
        });
    }
    
    initializeComponents() {
        // Initialize workflow UI components
        this.createWorkflowContainer();
        this.createProgressIndicator();
        this.createNavigationControls();
        this.createNotificationArea();
    }
    
    createWorkflowContainer() {
        if (document.getElementById('workflow-container')) return;
        
        const container = document.createElement('div');
        container.id = 'workflow-container';
        container.className = 'workflow-container hidden';
        container.innerHTML = `
            <div class="workflow-overlay"></div>
            <div class="workflow-modal responsive-modal large">
                <div class="workflow-header">
                    <h2 class="workflow-title responsive-heading"></h2>
                    <button class="workflow-close btn btn-sm" aria-label="Close workflow">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
                <div class="workflow-progress"></div>
                <div class="workflow-content">
                    <div class="workflow-step-content"></div>
                </div>
                <div class="workflow-navigation">
                    <button class="workflow-prev btn btn-secondary" disabled>Previous</button>
                    <div class="workflow-step-info">
                        <span class="workflow-step-number"></span>
                        <span class="workflow-step-title"></span>
                    </div>
                    <button class="workflow-next btn btn-primary" disabled>Next</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(container);
        
        // Bind container events
        container.querySelector('.workflow-close').addEventListener('click', () => {
            this.cancelWorkflow();
        });
        
        container.querySelector('.workflow-prev').addEventListener('click', () => {
            this.previousStep();
        });
        
        container.querySelector('.workflow-next').addEventListener('click', () => {
            this.nextStep();
        });
        
        container.querySelector('.workflow-overlay').addEventListener('click', () => {
            this.cancelWorkflow();
        });
    }
    
    createProgressIndicator() {
        const progressContainer = document.querySelector('.workflow-progress');
        if (!progressContainer) return;
        
        progressContainer.innerHTML = `
            <div class="progress-bar">
                <div class="progress-fill"></div>
            </div>
            <div class="progress-steps"></div>
        `;
    }
    
    createNavigationControls() {
        // Navigation controls are created in the main container
    }
    
    createNotificationArea() {
        if (document.getElementById('workflow-notifications')) return;
        
        const notifications = document.createElement('div');
        notifications.id = 'workflow-notifications';
        notifications.className = 'workflow-notifications';
        document.body.appendChild(notifications);
    }
    
    // Workflow management methods
    registerWorkflow(id, workflow) {
        this.workflows.set(id, {
            id,
            ...workflow,
            currentStep: 0,
            data: {},
            isActive: false
        });
    }
    
    startWorkflow(workflowId, options = {}) {
        const workflow = this.workflows.get(workflowId);
        if (!workflow) {
            console.error(`Workflow '${workflowId}' not found`);
            return false;
        }
        
        // Cancel any active workflow
        if (this.activeWorkflow) {
            this.cancelWorkflow();
        }
        
        // Initialize workflow
        workflow.currentStep = 0;
        workflow.data = options.initialData || {};
        workflow.isActive = true;
        workflow.startTime = Date.now();
        
        this.activeWorkflow = workflow;
        
        // Update state
        if (window.stateManager) {
            window.stateManager.setState('ui.activeWorkflow', {
                id: workflowId,
                step: 0,
                data: workflow.data
            });
        }
        
        // Show workflow UI
        this.showWorkflowUI();
        this.renderCurrentStep();
        
        // Track workflow start
        this.trackWorkflowEvent('start', { workflowId });
        
        // Emit event
        document.dispatchEvent(new CustomEvent('workflow:started', {
            detail: { workflow, options }
        }));
        
        return true;
    }
    
    nextStep(data = {}) {
        if (!this.activeWorkflow) return false;
        
        const currentStep = this.activeWorkflow.steps[this.activeWorkflow.currentStep];
        
        // Merge step data
        this.activeWorkflow.data = { ...this.activeWorkflow.data, ...data };
        
        // Validate current step
        if (currentStep.validation && !currentStep.validation(this.activeWorkflow.data)) {
            this.showValidationError('Please complete all required fields before proceeding.');
            return false;
        }
        
        // Check if this is the final step
        if (currentStep.final) {
            this.completeWorkflow(this.activeWorkflow.data);
            return true;
        }
        
        // Move to next step
        this.activeWorkflow.currentStep++;
        
        // Check if we've reached the end
        if (this.activeWorkflow.currentStep >= this.activeWorkflow.steps.length) {
            this.completeWorkflow(this.activeWorkflow.data);
            return true;
        }
        
        // Update state
        if (window.stateManager) {
            window.stateManager.setState('ui.activeWorkflow.step', this.activeWorkflow.currentStep);
            window.stateManager.setState('ui.activeWorkflow.data', this.activeWorkflow.data);
        }
        
        // Render new step
        this.renderCurrentStep();
        
        // Track step completion
        this.trackWorkflowEvent('step-complete', {
            workflowId: this.activeWorkflow.id,
            step: this.activeWorkflow.currentStep - 1,
            stepId: currentStep.id
        });
        
        return true;
    }
    
    previousStep() {
        if (!this.activeWorkflow || this.activeWorkflow.currentStep <= 0) return false;
        
        this.activeWorkflow.currentStep--;
        
        // Update state
        if (window.stateManager) {
            window.stateManager.setState('ui.activeWorkflow.step', this.activeWorkflow.currentStep);
        }
        
        // Render previous step
        this.renderCurrentStep();
        
        return true;
    }
    
    cancelWorkflow() {
        if (!this.activeWorkflow) return false;
        
        const workflowId = this.activeWorkflow.id;
        
        // Save draft if auto-save is enabled
        if (this.options.enableAutoSave) {
            this.saveDraft();
        }
        
        // Clean up
        this.activeWorkflow.isActive = false;
        this.activeWorkflow = null;
        
        // Update state
        if (window.stateManager) {
            window.stateManager.setState('ui.activeWorkflow', null);
        }
        
        // Hide workflow UI
        this.hideWorkflowUI();
        
        // Track cancellation
        this.trackWorkflowEvent('cancel', { workflowId });
        
        // Emit event
        document.dispatchEvent(new CustomEvent('workflow:cancelled', {
            detail: { workflowId }
        }));
        
        return true;
    }
    
    completeWorkflow(finalData = {}) {
        if (!this.activeWorkflow) return false;
        
        const workflow = this.activeWorkflow;
        workflow.data = { ...workflow.data, ...finalData };
        workflow.endTime = Date.now();
        workflow.duration = workflow.endTime - workflow.startTime;
        
        // Add to history
        this.workflowHistory.push({
            ...workflow,
            completedAt: new Date().toISOString()
        });
        
        // Clean up
        workflow.isActive = false;
        this.activeWorkflow = null;
        
        // Update state
        if (window.stateManager) {
            window.stateManager.setState('ui.activeWorkflow', null);
        }
        
        // Hide workflow UI
        this.hideWorkflowUI();
        
        // Clear auto-save draft
        this.clearDraft(workflow.id);
        
        // Track completion
        this.trackWorkflowEvent('complete', {
            workflowId: workflow.id,
            duration: workflow.duration,
            steps: workflow.steps.length
        });
        
        // Show completion notification
        this.showNotification(`${workflow.name} completed successfully!`, 'success');
        
        // Emit event
        document.dispatchEvent(new CustomEvent('workflow:completed', {
            detail: { workflow, data: workflow.data }
        }));
        
        return true;
    }
    
    // UI rendering methods
    showWorkflowUI() {
        const container = document.getElementById('workflow-container');
        if (container) {
            container.classList.remove('hidden');
            document.body.classList.add('workflow-active');
        }
    }
    
    hideWorkflowUI() {
        const container = document.getElementById('workflow-container');
        if (container) {
            container.classList.add('hidden');
            document.body.classList.remove('workflow-active');
        }
    }
    
    renderCurrentStep() {
        if (!this.activeWorkflow) return;
        
        const workflow = this.activeWorkflow;
        const currentStep = workflow.steps[workflow.currentStep];
        
        // Update workflow title
        const titleElement = document.querySelector('.workflow-title');
        if (titleElement) {
            titleElement.textContent = workflow.name;
        }
        
        // Update progress
        this.updateProgress();
        
        // Update step info
        const stepNumberElement = document.querySelector('.workflow-step-number');
        const stepTitleElement = document.querySelector('.workflow-step-title');
        
        if (stepNumberElement) {
            stepNumberElement.textContent = `Step ${workflow.currentStep + 1} of ${workflow.steps.length}`;
        }
        
        if (stepTitleElement) {
            stepTitleElement.textContent = currentStep.title;
        }
        
        // Update navigation buttons
        this.updateNavigationButtons();
        
        // Render step content
        this.renderStepContent(currentStep);
    }
    
    updateProgress() {
        const workflow = this.activeWorkflow;
        const progressFill = document.querySelector('.progress-fill');
        const progressSteps = document.querySelector('.progress-steps');
        
        if (progressFill) {
            const progress = ((workflow.currentStep + 1) / workflow.steps.length) * 100;
            progressFill.style.width = `${progress}%`;
        }
        
        if (progressSteps) {
            progressSteps.innerHTML = workflow.steps.map((step, index) => {
                const isActive = index === workflow.currentStep;
                const isCompleted = index < workflow.currentStep;
                const classes = ['progress-step'];
                
                if (isActive) classes.push('active');
                if (isCompleted) classes.push('completed');
                
                return `
                    <div class="${classes.join(' ')}" title="${step.title}">
                        <div class="step-indicator">${index + 1}</div>
                        <div class="step-label">${step.title}</div>
                    </div>
                `;
            }).join('');
        }
    }
    
    updateNavigationButtons() {
        const workflow = this.activeWorkflow;
        const prevButton = document.querySelector('.workflow-prev');
        const nextButton = document.querySelector('.workflow-next');
        
        if (prevButton) {
            prevButton.disabled = workflow.currentStep <= 0;
        }
        
        if (nextButton) {
            const currentStep = workflow.steps[workflow.currentStep];
            nextButton.textContent = currentStep.final ? 'Complete' : 'Next';
            nextButton.disabled = false; // Enable by default, validation will handle disabling
        }
    }
    
    renderStepContent(step) {
        const contentContainer = document.querySelector('.workflow-step-content');
        if (!contentContainer) return;
        
        // Clear previous content
        contentContainer.innerHTML = '';
        
        // Add step description
        if (step.description) {
            const description = document.createElement('p');
            description.className = 'workflow-step-description responsive-text';
            description.textContent = step.description;
            contentContainer.appendChild(description);
        }
        
        // Render component based on step configuration
        this.renderStepComponent(step, contentContainer);
    }
    
    renderStepComponent(step, container) {
        // This method would integrate with the specific UI components
        // For now, we'll create a placeholder that can be extended
        
        const componentContainer = document.createElement('div');
        componentContainer.className = `workflow-component workflow-component-${step.component}`;
        componentContainer.id = `workflow-step-${step.id}`;
        
        // Emit event for component rendering
        document.dispatchEvent(new CustomEvent('workflow:render-component', {
            detail: {
                step,
                container: componentContainer,
                data: this.activeWorkflow.data
            }
        }));
        
        container.appendChild(componentContainer);
    }
    
    // Event handlers
    handleComponentDataChange(detail) {
        if (!this.activeWorkflow) return;
        
        // Update workflow data
        this.activeWorkflow.data = { ...this.activeWorkflow.data, ...detail.data };
        
        // Update state
        if (window.stateManager) {
            window.stateManager.setState('ui.activeWorkflow.data', this.activeWorkflow.data);
        }
        
        // Emit workflow data change event
        document.dispatchEvent(new CustomEvent('workflow:data-change', {
            detail: {
                workflowId: this.activeWorkflow.id,
                step: this.activeWorkflow.currentStep,
                data: this.activeWorkflow.data
            }
        }));
    }
    
    handleValidationChange(detail) {
        const nextButton = document.querySelector('.workflow-next');
        if (nextButton) {
            nextButton.disabled = !detail.isValid;
        }
    }
    
    handleWorkflowStateChange(workflow) {
        // Handle external state changes
        if (workflow && !this.activeWorkflow) {
            // Resume workflow from state
            this.resumeWorkflow(workflow);
        }
    }
    
    handleKeyboardShortcut(e) {
        const key = this.getShortcutKey(e);
        const handler = this.shortcuts.get(key);
        
        if (handler && this.activeWorkflow) {
            handler(e);
        }
    }
    
    // Auto-save functionality
    scheduleAutoSave(detail) {
        if (!this.options.enableAutoSave || !this.activeWorkflow) return;
        
        const workflowId = this.activeWorkflow.id;
        
        // Clear existing timer
        if (this.autoSaveTimers.has(workflowId)) {
            clearTimeout(this.autoSaveTimers.get(workflowId));
        }
        
        // Schedule new auto-save
        const timer = setTimeout(() => {
            this.saveDraft();
        }, this.options.autoSaveInterval);
        
        this.autoSaveTimers.set(workflowId, timer);
    }
    
    saveDraft() {
        if (!this.activeWorkflow) return;
        
        const draft = {
            workflowId: this.activeWorkflow.id,
            currentStep: this.activeWorkflow.currentStep,
            data: this.activeWorkflow.data,
            savedAt: Date.now()
        };
        
        try {
            localStorage.setItem(`workflow_draft_${this.activeWorkflow.id}`, JSON.stringify(draft));
        } catch (error) {
            console.warn('Failed to save workflow draft:', error);
        }
    }
    
    loadDraft(workflowId) {
        try {
            const draftData = localStorage.getItem(`workflow_draft_${workflowId}`);
            return draftData ? JSON.parse(draftData) : null;
        } catch (error) {
            console.warn('Failed to load workflow draft:', error);
            return null;
        }
    }
    
    clearDraft(workflowId) {
        try {
            localStorage.removeItem(`workflow_draft_${workflowId}`);
        } catch (error) {
            console.warn('Failed to clear workflow draft:', error);
        }
    }
    
    // Utility methods
    registerShortcut(key, handler) {
        this.shortcuts.set(key, handler);
    }
    
    getShortcutKey(e) {
        const parts = [];
        
        if (e.ctrlKey) parts.push('ctrl');
        if (e.shiftKey) parts.push('shift');
        if (e.altKey) parts.push('alt');
        if (e.metaKey) parts.push('meta');
        
        // Handle cases where e.key might be undefined
        if (e.key && typeof e.key === 'string') {
            parts.push(e.key.toLowerCase());
        } else {
            // Fallback to keyCode if key is not available
            const keyName = this.getKeyNameFromCode(e.keyCode || e.which);
            if (keyName) {
                parts.push(keyName.toLowerCase());
            }
        }
        
        return parts.join('+');
    }
    
    getKeyNameFromCode(keyCode) {
        // Common key codes mapping
        const keyMap = {
            8: 'backspace',
            9: 'tab',
            13: 'enter',
            16: 'shift',
            17: 'ctrl',
            18: 'alt',
            27: 'escape',
            32: 'space',
            37: 'arrowleft',
            38: 'arrowup',
            39: 'arrowright',
            40: 'arrowdown',
            46: 'delete'
        };
        
        if (keyMap[keyCode]) {
            return keyMap[keyCode];
        }
        
        // For letter keys (A-Z)
        if (keyCode >= 65 && keyCode <= 90) {
            return String.fromCharCode(keyCode).toLowerCase();
        }
        
        // For number keys (0-9)
        if (keyCode >= 48 && keyCode <= 57) {
            return String.fromCharCode(keyCode);
        }
        
        return null;
    }
    
    showNotification(message, type = 'info', duration = 5000) {
        if (!this.options.enableNotifications) return;
        
        const container = document.getElementById('workflow-notifications');
        if (!container) return;
        
        const notification = document.createElement('div');
        notification.className = `workflow-notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close" aria-label="Close notification">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;
        
        // Add close handler
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
        
        container.appendChild(notification);
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, duration);
        }
    }
    
    showValidationError(message) {
        this.showNotification(message, 'error', 3000);
    }
    
    trackWorkflowEvent(event, data = {}) {
        // Emit tracking event
        document.dispatchEvent(new CustomEvent('workflow:track', {
            detail: {
                event,
                timestamp: Date.now(),
                ...data
            }
        }));
    }
    
    resumeWorkflow(workflowState) {
        const workflow = this.workflows.get(workflowState.id);
        if (!workflow) return false;
        
        workflow.currentStep = workflowState.step;
        workflow.data = workflowState.data;
        workflow.isActive = true;
        
        this.activeWorkflow = workflow;
        this.showWorkflowUI();
        this.renderCurrentStep();
        
        return true;
    }
    
    saveWorkflowData() {
        if (!this.activeWorkflow) return false;
        
        // Emit save event
        document.dispatchEvent(new CustomEvent('workflow:save', {
            detail: {
                workflowId: this.activeWorkflow.id,
                data: this.activeWorkflow.data
            }
        }));
        
        this.showNotification('Workflow data saved', 'success', 2000);
        return true;
    }
    
    // Public API
    getActiveWorkflow() {
        return this.activeWorkflow;
    }
    
    getWorkflowHistory() {
        return this.workflowHistory;
    }
    
    getAvailableWorkflows() {
        return Array.from(this.workflows.values()).map(w => ({
            id: w.id,
            name: w.name,
            description: w.description,
            steps: w.steps.length
        }));
    }
    
    // Cleanup
    destroy() {
        // Clear auto-save timers
        this.autoSaveTimers.forEach(timer => clearTimeout(timer));
        this.autoSaveTimers.clear();
        
        // Cancel active workflow
        if (this.activeWorkflow) {
            this.cancelWorkflow();
        }
        
        // Remove UI elements
        const container = document.getElementById('workflow-container');
        if (container) {
            container.remove();
        }
        
        const notifications = document.getElementById('workflow-notifications');
        if (notifications) {
            notifications.remove();
        }
        
        // Clear data
        this.workflows.clear();
        this.shortcuts.clear();
        this.workflowHistory = [];
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UIWorkflows;
}

// Global instance
if (typeof window !== 'undefined') {
    window.UIWorkflows = UIWorkflows;
    
    // Auto-initialize if DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.uiWorkflows = new UIWorkflows();
        });
    } else {
        window.uiWorkflows = new UIWorkflows();
    }
}