/**
 * WebSocket Client Integration Helper
 * 
 * Provides utilities for integrating the unified WebSocket client
 * with existing code and migration from scattered implementations.
 */

/**
 * Global WebSocket client instance
 */
let globalWebSocketClient = null;

/**
 * WebSocket Integration Manager
 * Provides a centralized way to manage WebSocket connections across the application
 */
class WebSocketIntegration {
    constructor() {
        this.client = null;
        this.initialized = false;
        this.progressCallbacks = new Map();
        this.dashboardCallbacks = new Map();
        this.migrationMode = false;
    }

    /**
     * Initialize the WebSocket client with application-specific configuration
     */
    initialize(options = {}) {
        if (this.initialized) {
            console.warn('WebSocket integration already initialized');
            return this.client;
        }

        const defaultOptions = {
            debug: window.location.hostname === 'localhost',
            reconnectAttempts: 10,
            reconnectDelay: 1000,
            maxReconnectDelay: 30000,
            heartbeatInterval: 30000,
            autoConnect: true
        };

        const config = { ...defaultOptions, ...options };
        
        try {
            this.client = new WebSocketClient(config);
            this._setupApplicationHandlers();
            this.initialized = true;
            
            console.log('WebSocket integration initialized successfully');
            return this.client;
        } catch (error) {
            console.error('Failed to initialize WebSocket integration:', error);
            throw error;
        }
    }

    /**
     * Get the WebSocket client instance
     */
    getClient() {
        if (!this.initialized) {
            throw new Error('WebSocket integration not initialized. Call initialize() first.');
        }
        return this.client;
    }

    /**
     * Setup application-specific event handlers
     */
    _setupApplicationHandlers() {
        // Connection status updates
        this.client.onConnect((info) => {
            this._updateConnectionStatus(true);
            this._notifyConnectionChange('connected', info);
        });

        this.client.onDisconnect((info) => {
            this._updateConnectionStatus(false);
            this._notifyConnectionChange('disconnected', info);
        });

        this.client.onReconnect((info) => {
            this._notifyConnectionChange('reconnecting', info);
        });

        this.client.onError((error) => {
            console.error('WebSocket error:', error);
            this._notifyConnectionChange('error', error);
        });

        // Application-specific events
        this.client.on('progress_update', (data) => {
            this._handleProgressUpdate(data);
        });

        this.client.on('ai_progress', (data) => {
            this._handleProgressUpdate(data);
        });

        this.client.on('dashboard_update', (data) => {
            this._handleDashboardUpdate(data);
        });

        this.client.on('session_status', (data) => {
            this._handleSessionStatus(data);
        });

        this.client.on('task_completed', (data) => {
            this._handleTaskCompletion(data);
        });

        this.client.on('task_error', (data) => {
            this._handleTaskError(data);
        });

        this.client.on('processing_progress', (data) => {
            this._handleProcessingProgress(data);
        });
    }

    /**
     * Update connection status in UI
     */
    _updateConnectionStatus(connected) {
        // Update connection indicators
        const indicators = document.querySelectorAll('.websocket-status');
        indicators.forEach(indicator => {
            indicator.classList.toggle('connected', connected);
            indicator.classList.toggle('disconnected', !connected);
            indicator.textContent = connected ? 'Connected' : 'Disconnected';
        });

        // Update any legacy connection status elements
        const legacyIndicators = document.querySelectorAll('.connection-status');
        legacyIndicators.forEach(indicator => {
            indicator.style.color = connected ? 'green' : 'red';
            indicator.textContent = connected ? '● Connected' : '● Disconnected';
        });
    }

    /**
     * Notify about connection changes
     */
    _notifyConnectionChange(status, info) {
        // Dispatch custom event for other components to listen
        const event = new CustomEvent('websocket-status-change', {
            detail: { status, info, timestamp: new Date().toISOString() }
        });
        document.dispatchEvent(event);

        // Update ExamGrader namespace if it exists (legacy support)
        if (typeof ExamGrader !== 'undefined' && ExamGrader.websocket) {
            ExamGrader.websocket.connectionStatus = status;
            ExamGrader.websocket.lastStatusChange = new Date().toISOString();
        }
    }

    /**
     * Handle progress updates
     */
    _handleProgressUpdate(data) {
        const sessionId = data.session_id || data.sessionId;
        if (!sessionId) return;

        // Call registered callbacks
        if (this.progressCallbacks.has(sessionId)) {
            this.progressCallbacks.get(sessionId).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error('Error in progress callback:', error);
                }
            });
        }

        // Update progress bars if they exist
        this._updateProgressBars(sessionId, data);

        // Legacy support for global progress handlers
        if (typeof window.handleProgressUpdate === 'function') {
            window.handleProgressUpdate(data);
        }
    }

    /**
     * Handle dashboard updates
     */
    _handleDashboardUpdate(data) {
        const userId = data.user_id || data.userId;
        if (!userId) return;

        // Call registered callbacks
        if (this.dashboardCallbacks.has(userId)) {
            this.dashboardCallbacks.get(userId).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error('Error in dashboard callback:', error);
                }
            });
        }

        // Update dashboard elements
        this._updateDashboardElements(data);
    }

    /**
     * Handle session status updates
     */
    _handleSessionStatus(data) {
        // Update session status displays
        const sessionElements = document.querySelectorAll(`[data-session-id="${data.session_id}"]`);
        sessionElements.forEach(element => {
            element.classList.remove('status-pending', 'status-processing', 'status-completed', 'status-error');
            element.classList.add(`status-${data.status}`);
            
            const statusText = element.querySelector('.status-text');
            if (statusText) {
                statusText.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
            }
        });
    }

    /**
     * Handle task completion
     */
    _handleTaskCompletion(data) {
        // Show completion notification
        this._showNotification('Task completed successfully', 'success');
        
        // Update UI elements
        const taskElements = document.querySelectorAll(`[data-task-id="${data.task_id}"]`);
        taskElements.forEach(element => {
            element.classList.add('task-completed');
        });
    }

    /**
     * Handle task errors
     */
    _handleTaskError(data) {
        // Show error notification
        this._showNotification(`Task failed: ${data.error}`, 'error');
        
        // Update UI elements
        const taskElements = document.querySelectorAll(`[data-task-id="${data.task_id}"]`);
        taskElements.forEach(element => {
            element.classList.add('task-error');
        });
    }

    /**
     * Handle processing progress
     */
    _handleProcessingProgress(data) {
        // Update processing indicators
        const processingElements = document.querySelectorAll('.processing-indicator');
        processingElements.forEach(element => {
            if (data.progress !== undefined) {
                const progressBar = element.querySelector('.progress-bar');
                if (progressBar) {
                    progressBar.style.width = `${data.progress}%`;
                }
                
                const progressText = element.querySelector('.progress-text');
                if (progressText) {
                    progressText.textContent = `${Math.round(data.progress)}%`;
                }
            }
        });
    }

    /**
     * Update progress bars
     */
    _updateProgressBars(sessionId, data) {
        const progressBars = document.querySelectorAll(`[data-progress-session="${sessionId}"]`);
        progressBars.forEach(bar => {
            if (data.percentage !== undefined) {
                const progressFill = bar.querySelector('.progress-fill') || bar;
                progressFill.style.width = `${data.percentage}%`;
                
                const progressLabel = bar.querySelector('.progress-label');
                if (progressLabel) {
                    progressLabel.textContent = `${Math.round(data.percentage)}%`;
                }
            }
            
            if (data.operation) {
                const operationLabel = bar.querySelector('.operation-label');
                if (operationLabel) {
                    operationLabel.textContent = data.operation;
                }
            }
        });
    }

    /**
     * Update dashboard elements
     */
    _updateDashboardElements(data) {
        // Update dashboard cards, stats, etc.
        if (data.type === 'stats') {
            Object.keys(data.data || {}).forEach(key => {
                const element = document.querySelector(`[data-stat="${key}"]`);
                if (element) {
                    element.textContent = data.data[key];
                }
            });
        }
    }

    /**
     * Show notification
     */
    _showNotification(message, type = 'info') {
        // Try to use existing notification system
        if (typeof ExamGrader !== 'undefined' && ExamGrader.utils && ExamGrader.utils.showToast) {
            ExamGrader.utils.showToast(message, type);
            return;
        }

        // Fallback to simple notification
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 4px;
            color: white;
            z-index: 10000;
            background-color: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#007bff'};
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    /**
     * Subscribe to progress updates for a session
     */
    subscribeToProgress(sessionId, callback) {
        if (!this.progressCallbacks.has(sessionId)) {
            this.progressCallbacks.set(sessionId, []);
        }
        this.progressCallbacks.get(sessionId).push(callback);
        
        // Subscribe to WebSocket room
        return this.client.subscribeToProgress(sessionId, callback);
    }

    /**
     * Unsubscribe from progress updates
     */
    unsubscribeFromProgress(sessionId, callback = null) {
        if (callback && this.progressCallbacks.has(sessionId)) {
            const callbacks = this.progressCallbacks.get(sessionId);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
            if (callbacks.length === 0) {
                this.progressCallbacks.delete(sessionId);
            }
        } else {
            this.progressCallbacks.delete(sessionId);
        }
        
        return this.client.unsubscribeFromProgress(sessionId, callback);
    }

    /**
     * Subscribe to dashboard updates for a user
     */
    subscribeToDashboard(userId, callback) {
        if (!this.dashboardCallbacks.has(userId)) {
            this.dashboardCallbacks.set(userId, []);
        }
        this.dashboardCallbacks.get(userId).push(callback);
        
        return this.client.subscribeToDashboard(userId, callback);
    }

    /**
     * Get connection statistics
     */
    getStats() {
        return this.client ? this.client.getStats() : null;
    }

    /**
     * Get connection state
     */
    getState() {
        return this.client ? this.client.getState() : { connectionState: 'not_initialized' };
    }

    /**
     * Enable migration mode for gradual transition from legacy code
     */
    enableMigrationMode() {
        this.migrationMode = true;
        this._setupLegacyCompatibility();
    }

    /**
     * Setup legacy compatibility layer
     */
    _setupLegacyCompatibility() {
        // Create legacy socket object for backward compatibility
        if (!window.legacySocket) {
            window.legacySocket = {
                emit: (event, data, callback) => {
                    return this.client.emit(event, data, callback);
                },
                on: (event, handler) => {
                    return this.client.on(event, handler);
                },
                off: (event, handler) => {
                    return this.client.off(event, handler);
                },
                connected: () => {
                    return this.client.isConnected();
                },
                id: () => {
                    return this.client.socket ? this.client.socket.id : null;
                }
            };
        }

        // Setup ExamGrader namespace compatibility
        if (typeof ExamGrader !== 'undefined') {
            ExamGrader.websocket = ExamGrader.websocket || {};
            ExamGrader.websocket.client = this.client;
            ExamGrader.websocket.isConnected = () => this.client.isConnected();
            ExamGrader.websocket.emit = (event, data) => this.client.emit(event, data);
            ExamGrader.websocket.on = (event, handler) => this.client.on(event, handler);
        }
    }

    /**
     * Destroy the integration and clean up
     */
    destroy() {
        if (this.client) {
            this.client.destroy();
            this.client = null;
        }
        
        this.progressCallbacks.clear();
        this.dashboardCallbacks.clear();
        this.initialized = false;
        
        // Clean up legacy compatibility
        if (window.legacySocket) {
            delete window.legacySocket;
        }
    }
}

/**
 * Migration utilities for existing code
 */
class WebSocketMigration {
    /**
     * Migrate from RefactoredAIProcessor WebSocket usage
     */
    static migrateRefactoredAIProcessor(integration) {
        // Replace initializeSocketIO calls
        if (typeof RefactoredAIProcessor !== 'undefined') {
            const originalInit = RefactoredAIProcessor.prototype.initializeSocketIO;
            RefactoredAIProcessor.prototype.initializeSocketIO = function() {
                // Use the unified client instead
                this.socket = integration.getClient();
                this.socket.on('progress_update', (data) => this.handleProgressUpdate(data));
                this.socket.on('ai_progress', (data) => this.handleProgressUpdate(data));
                this.socket.on('session_status', (data) => this.handleSessionStatus(data));
            };
        }
    }

    /**
     * Migrate from OptimizedProcessingManager WebSocket usage
     */
    static migrateOptimizedProcessing(integration) {
        if (typeof OptimizedProcessingManager !== 'undefined') {
            const originalInit = OptimizedProcessingManager.prototype.initializeWebSocket;
            OptimizedProcessingManager.prototype.initializeWebSocket = function() {
                this.socket = integration.getClient();
                this.socket.on('processing_progress', (data) => this.handleProgressUpdate(data));
                this.socket.on('task_completed', (data) => this.handleTaskCompletion(data));
                this.socket.on('task_error', (data) => this.handleTaskError(data));
            };
        }
    }

    /**
     * Migrate from UnifiedProgressTracker WebSocket usage
     */
    static migrateUnifiedProgressTracker(integration) {
        if (typeof UnifiedProgressTracker !== 'undefined') {
            const originalInit = UnifiedProgressTracker.prototype.initializeWebSocket;
            UnifiedProgressTracker.prototype.initializeWebSocket = function() {
                this.socket = integration.getClient();
                this.socket.on('progress_update', (data) => this.handleProgressUpdate(data));
                this.options.enableWebSocket = true;
            };
        }
    }

    /**
     * Migrate all known WebSocket implementations
     */
    static migrateAll(integration) {
        this.migrateRefactoredAIProcessor(integration);
        this.migrateOptimizedProcessing(integration);
        this.migrateUnifiedProgressTracker(integration);
        
        console.log('WebSocket migration completed for all known implementations');
    }
}

// Create global integration instance
const webSocketIntegration = new WebSocketIntegration();

// Auto-initialize if DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        try {
            webSocketIntegration.initialize();
            globalWebSocketClient = webSocketIntegration.getClient();
        } catch (error) {
            console.error('Failed to auto-initialize WebSocket integration:', error);
        }
    });
} else {
    // DOM already loaded
    try {
        webSocketIntegration.initialize();
        globalWebSocketClient = webSocketIntegration.getClient();
    } catch (error) {
        console.error('Failed to auto-initialize WebSocket integration:', error);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        WebSocketIntegration,
        WebSocketMigration,
        webSocketIntegration,
        getGlobalClient: () => globalWebSocketClient
    };
} else if (typeof window !== 'undefined') {
    window.WebSocketIntegration = WebSocketIntegration;
    window.WebSocketMigration = WebSocketMigration;
    window.webSocketIntegration = webSocketIntegration;
    window.getGlobalWebSocketClient = () => globalWebSocketClient;
}