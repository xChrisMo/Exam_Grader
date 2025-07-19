/**
 * Unified WebSocket Client for Real-time Updates
 * 
 * Provides a centralized WebSocket client with:
 * - Automatic reconnection with exponential backoff
 * - Event handling and message routing
 * - Connection state management
 * - Room management
 * - Message queuing for offline scenarios
 * - Health monitoring and statistics
 */

class WebSocketClient {
    constructor(options = {}) {
        this.options = {
            url: options.url || window.location.origin,
            autoConnect: options.autoConnect !== false,
            reconnectAttempts: options.reconnectAttempts || 10,
            reconnectDelay: options.reconnectDelay || 1000,
            maxReconnectDelay: options.maxReconnectDelay || 30000,
            heartbeatInterval: options.heartbeatInterval || 30000,
            messageQueueSize: options.messageQueueSize || 100,
            debug: options.debug || false,
            ...options
        };

        // Connection state
        this.socket = null;
        this.connectionState = 'disconnected'; // disconnected, connecting, connected, reconnecting
        this.reconnectAttempt = 0;
        this.reconnectTimer = null;
        this.heartbeatTimer = null;
        this.lastPingTime = null;
        this.latency = null;

        // Event handling
        this.eventHandlers = new Map();
        this.connectionHandlers = [];
        this.disconnectionHandlers = [];
        this.errorHandlers = [];
        this.reconnectHandlers = [];

        // Room management
        this.joinedRooms = new Set();
        this.pendingRoomJoins = new Set();

        // Message queuing
        this.messageQueue = [];
        this.queueEnabled = true;

        // Statistics
        this.stats = {
            connectTime: null,
            totalConnections: 0,
            totalDisconnections: 0,
            totalReconnections: 0,
            messagesSent: 0,
            messagesReceived: 0,
            errors: 0
        };

        // Auto-connect if enabled
        if (this.options.autoConnect) {
            this.connect();
        }

        this._log('WebSocket client initialized', this.options);
    }

    /**
     * Connect to the WebSocket server
     */
    connect() {
        if (this.connectionState === 'connected' || this.connectionState === 'connecting') {
            this._log('Already connected or connecting');
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
            try {
                this._log('Attempting to connect...');
                this.connectionState = 'connecting';

                // Check if Socket.IO is available
                if (typeof io === 'undefined') {
                    throw new Error('Socket.IO library not available');
                }

                // Create socket connection
                this.socket = io(this.options.url, {
                    transports: ['websocket', 'polling'],
                    timeout: 10000,
                    forceNew: true
                });

                // Set up event handlers
                this._setupSocketHandlers(resolve, reject);

            } catch (error) {
                this._log('Connection failed:', error);
                this.connectionState = 'disconnected';
                this.stats.errors++;
                reject(error);
            }
        });
    }

    /**
     * Disconnect from the WebSocket server
     */
    disconnect() {
        this._log('Disconnecting...');
        this.connectionState = 'disconnected';
        this._clearTimers();
        
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }

        this.joinedRooms.clear();
        this.pendingRoomJoins.clear();
    }

    /**
     * Set up socket event handlers
     */
    _setupSocketHandlers(connectResolve, connectReject) {
        this.socket.on('connect', () => {
            this._log('Connected successfully');
            this.connectionState = 'connected';
            this.stats.connectTime = Date.now();
            this.stats.totalConnections++;
            this.reconnectAttempt = 0;
            
            // Clear reconnect timer
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }

            // Start heartbeat
            this._startHeartbeat();

            // Rejoin rooms
            this._rejoinRooms();

            // Process queued messages
            this._processMessageQueue();

            // Notify connection handlers
            this.connectionHandlers.forEach(handler => {
                try {
                    handler({
                        sessionId: this.socket.id,
                        timestamp: new Date().toISOString(),
                        reconnection: this.stats.totalConnections > 1
                    });
                } catch (error) {
                    this._log('Error in connection handler:', error);
                }
            });

            if (connectResolve) connectResolve();
        });

        this.socket.on('disconnect', (reason) => {
            this._log('Disconnected:', reason);
            const wasConnected = this.connectionState === 'connected';
            this.connectionState = 'disconnected';
            this.stats.totalDisconnections++;
            this._clearTimers();

            // Notify disconnection handlers
            this.disconnectionHandlers.forEach(handler => {
                try {
                    handler({
                        reason,
                        timestamp: new Date().toISOString(),
                        wasConnected
                    });
                } catch (error) {
                    this._log('Error in disconnection handler:', error);
                }
            });

            // Attempt reconnection if not manually disconnected
            if (reason !== 'io client disconnect' && this.options.reconnectAttempts > 0) {
                this._scheduleReconnect();
            }
        });

        this.socket.on('connect_error', (error) => {
            this._log('Connection error:', error);
            this.stats.errors++;
            
            // Notify error handlers
            this.errorHandlers.forEach(handler => {
                try {
                    handler({
                        type: 'connection_error',
                        error,
                        timestamp: new Date().toISOString()
                    });
                } catch (handlerError) {
                    this._log('Error in error handler:', handlerError);
                }
            });

            if (connectReject) {
                connectReject(error);
                connectReject = null;
            }
        });

        this.socket.on('pong', (latency) => {
            this.latency = latency;
            this._log(`Heartbeat: ${latency}ms`);
        });

        // Handle custom events
        this.socket.onAny((eventName, ...args) => {
            this.stats.messagesReceived++;
            this._log(`Received event: ${eventName}`, args);

            // Route to specific handlers
            if (this.eventHandlers.has(eventName)) {
                const handlers = this.eventHandlers.get(eventName);
                handlers.forEach(handler => {
                    try {
                        handler(...args);
                    } catch (error) {
                        this._log(`Error in event handler for ${eventName}:`, error);
                    }
                });
            }
        });
    }

    /**
     * Schedule reconnection attempt
     */
    _scheduleReconnect() {
        if (this.reconnectAttempt >= this.options.reconnectAttempts) {
            this._log('Max reconnection attempts reached');
            return;
        }

        this.reconnectAttempt++;
        this.connectionState = 'reconnecting';
        
        // Calculate delay with exponential backoff
        const delay = Math.min(
            this.options.reconnectDelay * Math.pow(2, this.reconnectAttempt - 1),
            this.options.maxReconnectDelay
        );

        this._log(`Scheduling reconnection attempt ${this.reconnectAttempt} in ${delay}ms`);

        this.reconnectTimer = setTimeout(() => {
            this._log(`Reconnection attempt ${this.reconnectAttempt}`);
            this.stats.totalReconnections++;
            
            // Notify reconnect handlers
            this.reconnectHandlers.forEach(handler => {
                try {
                    handler({
                        attempt: this.reconnectAttempt,
                        maxAttempts: this.options.reconnectAttempts,
                        delay,
                        timestamp: new Date().toISOString()
                    });
                } catch (error) {
                    this._log('Error in reconnect handler:', error);
                }
            });

            this.connect().catch(error => {
                this._log('Reconnection failed:', error);
            });
        }, delay);
    }

    /**
     * Start heartbeat monitoring
     */
    _startHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
        }

        this.heartbeatTimer = setInterval(() => {
            if (this.socket && this.connectionState === 'connected') {
                this.lastPingTime = Date.now();
                this.socket.emit('ping');
            }
        }, this.options.heartbeatInterval);
    }

    /**
     * Clear all timers
     */
    _clearTimers() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    /**
     * Rejoin rooms after reconnection
     */
    _rejoinRooms() {
        this.joinedRooms.forEach(room => {
            this._log(`Rejoining room: ${room}`);
            this.socket.emit('join_room', { room });
        });
    }

    /**
     * Process queued messages
     */
    _processMessageQueue() {
        if (!this.queueEnabled || this.messageQueue.length === 0) {
            return;
        }

        this._log(`Processing ${this.messageQueue.length} queued messages`);
        
        const messages = [...this.messageQueue];
        this.messageQueue = [];

        messages.forEach(({ event, data, callback }) => {
            this.emit(event, data, callback);
        });
    }

    /**
     * Emit an event to the server
     */
    emit(event, data = {}, callback = null) {
        if (this.connectionState !== 'connected') {
            if (this.queueEnabled && this.messageQueue.length < this.options.messageQueueSize) {
                this._log(`Queueing message: ${event}`);
                this.messageQueue.push({ event, data, callback });
                return false;
            } else {
                this._log(`Cannot emit ${event}: not connected and queue full/disabled`);
                return false;
            }
        }

        try {
            this.stats.messagesSent++;
            this._log(`Emitting event: ${event}`, data);
            
            if (callback) {
                this.socket.emit(event, data, callback);
            } else {
                this.socket.emit(event, data);
            }
            return true;
        } catch (error) {
            this._log(`Error emitting ${event}:`, error);
            this.stats.errors++;
            return false;
        }
    }

    /**
     * Join a room
     */
    joinRoom(room) {
        if (!room) {
            this._log('Invalid room name');
            return false;
        }

        this.joinedRooms.add(room);
        
        if (this.connectionState === 'connected') {
            this._log(`Joining room: ${room}`);
            return this.emit('join_room', { room });
        } else {
            this._log(`Room join queued: ${room}`);
            this.pendingRoomJoins.add(room);
            return false;
        }
    }

    /**
     * Leave a room
     */
    leaveRoom(room) {
        if (!room) {
            this._log('Invalid room name');
            return false;
        }

        this.joinedRooms.delete(room);
        this.pendingRoomJoins.delete(room);
        
        if (this.connectionState === 'connected') {
            this._log(`Leaving room: ${room}`);
            return this.emit('leave_room', { room });
        }
        return true;
    }

    /**
     * Subscribe to progress updates for a session
     */
    subscribeToProgress(sessionId, callback) {
        if (!sessionId) {
            this._log('Invalid session ID');
            return false;
        }

        const room = `progress_${sessionId}`;
        this.on('progress_update', callback);
        return this.joinRoom(room);
    }

    /**
     * Unsubscribe from progress updates
     */
    unsubscribeFromProgress(sessionId, callback = null) {
        if (!sessionId) {
            this._log('Invalid session ID');
            return false;
        }

        const room = `progress_${sessionId}`;
        if (callback) {
            this.off('progress_update', callback);
        }
        return this.leaveRoom(room);
    }

    /**
     * Subscribe to dashboard updates for a user
     */
    subscribeToDashboard(userId, callback) {
        if (!userId) {
            this._log('Invalid user ID');
            return false;
        }

        const room = `dashboard_${userId}`;
        this.on('dashboard_update', callback);
        return this.joinRoom(room);
    }

    /**
     * Add event listener
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
        this._log(`Added handler for event: ${event}`);
    }

    /**
     * Remove event listener
     */
    off(event, handler = null) {
        if (!this.eventHandlers.has(event)) {
            return;
        }

        if (handler) {
            const handlers = this.eventHandlers.get(event);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
                this._log(`Removed specific handler for event: ${event}`);
            }
        } else {
            this.eventHandlers.delete(event);
            this._log(`Removed all handlers for event: ${event}`);
        }
    }

    /**
     * Add connection event handler
     */
    onConnect(handler) {
        this.connectionHandlers.push(handler);
    }

    /**
     * Add disconnection event handler
     */
    onDisconnect(handler) {
        this.disconnectionHandlers.push(handler);
    }

    /**
     * Add error event handler
     */
    onError(handler) {
        this.errorHandlers.push(handler);
    }

    /**
     * Add reconnection event handler
     */
    onReconnect(handler) {
        this.reconnectHandlers.push(handler);
    }

    /**
     * Get connection state
     */
    getState() {
        return {
            connectionState: this.connectionState,
            sessionId: this.socket?.id || null,
            reconnectAttempt: this.reconnectAttempt,
            joinedRooms: Array.from(this.joinedRooms),
            latency: this.latency,
            queueSize: this.messageQueue.length
        };
    }

    /**
     * Get connection statistics
     */
    getStats() {
        return {
            ...this.stats,
            uptime: this.stats.connectTime ? Date.now() - this.stats.connectTime : 0,
            latency: this.latency,
            queueSize: this.messageQueue.length,
            roomCount: this.joinedRooms.size
        };
    }

    /**
     * Check if connected
     */
    isConnected() {
        return this.connectionState === 'connected';
    }

    /**
     * Check if connecting
     */
    isConnecting() {
        return this.connectionState === 'connecting';
    }

    /**
     * Check if reconnecting
     */
    isReconnecting() {
        return this.connectionState === 'reconnecting';
    }

    /**
     * Enable/disable message queuing
     */
    setQueueEnabled(enabled) {
        this.queueEnabled = enabled;
        if (!enabled) {
            this.messageQueue = [];
        }
    }

    /**
     * Clear message queue
     */
    clearQueue() {
        this.messageQueue = [];
    }

    /**
     * Log debug messages
     */
    _log(message, ...args) {
        if (this.options.debug) {
            console.log(`[WebSocketClient] ${message}`, ...args);
        }
    }

    /**
     * Destroy the client and clean up resources
     */
    destroy() {
        this._log('Destroying WebSocket client');
        this.disconnect();
        this.eventHandlers.clear();
        this.connectionHandlers = [];
        this.disconnectionHandlers = [];
        this.errorHandlers = [];
        this.reconnectHandlers = [];
        this.messageQueue = [];
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketClient;
} else if (typeof window !== 'undefined') {
    window.WebSocketClient = WebSocketClient;
}