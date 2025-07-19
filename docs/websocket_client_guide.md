# WebSocket Client Guide

Comprehensive guide for the unified WebSocket client implementation, covering setup, usage, migration, and best practices.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Core Features](#core-features)
4. [API Reference](#api-reference)
5. [Integration Guide](#integration-guide)
6. [Migration from Legacy Code](#migration-from-legacy-code)
7. [Error Handling](#error-handling)
8. [Performance Optimization](#performance-optimization)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

## Overview

The unified WebSocket client provides a centralized, robust solution for real-time communication in the Exam Grader application. It consolidates multiple scattered WebSocket implementations into a single, feature-rich client with automatic reconnection, event handling, and state management.

### Key Benefits

- **Unified Interface**: Single client for all WebSocket communication
- **Automatic Reconnection**: Exponential backoff with configurable retry logic
- **Event Management**: Centralized event handling and routing
- **Room Management**: Automatic room joining/leaving with persistence
- **Message Queuing**: Offline message queuing and delivery
- **Health Monitoring**: Connection statistics and latency tracking
- **Legacy Support**: Backward compatibility with existing code

## Quick Start

### Basic Usage

```javascript
// Initialize the WebSocket client
const client = new WebSocketClient({
    debug: true,
    reconnectAttempts: 10,
    autoConnect: true
});

// Listen for connection events
client.onConnect((info) => {
    console.log('Connected:', info.sessionId);
});

// Subscribe to events
client.on('progress_update', (data) => {
    console.log('Progress:', data.percentage + '%');
});

// Emit events
client.emit('join_room', { room: 'dashboard_user123' });
```

### Using the Integration Helper

```javascript
// Auto-initialized global integration
const client = webSocketIntegration.getClient();

// Subscribe to progress updates
webSocketIntegration.subscribeToProgress('session123', (data) => {
    updateProgressBar(data.percentage);
});

// Subscribe to dashboard updates
webSocketIntegration.subscribeToDashboard('user456', (data) => {
    updateDashboard(data);
});
```

## Core Features

### Connection Management

```javascript
// Manual connection control
const client = new WebSocketClient({ autoConnect: false });

// Connect
await client.connect();

// Check connection state
if (client.isConnected()) {
    console.log('Ready to communicate');
}

// Disconnect
client.disconnect();
```

### Event Handling

```javascript
// Add event listeners
client.on('progress_update', handleProgress);
client.on('task_completed', handleCompletion);
client.on('task_error', handleError);

// Remove specific listener
client.off('progress_update', handleProgress);

// Remove all listeners for an event
client.off('progress_update');

// Connection event handlers
client.onConnect((info) => {
    console.log('Connected:', info);
});

client.onDisconnect((info) => {
    console.log('Disconnected:', info.reason);
});

client.onReconnect((info) => {
    console.log(`Reconnection attempt ${info.attempt}/${info.maxAttempts}`);
});

client.onError((error) => {
    console.error('WebSocket error:', error);
});
```

### Room Management

```javascript
// Join rooms
client.joinRoom('progress_session123');
client.joinRoom('dashboard_user456');

// Leave rooms
client.leaveRoom('progress_session123');

// Rooms are automatically rejoined after reconnection
```

### Message Queuing

```javascript
// Messages are automatically queued when disconnected
client.emit('update_status', { status: 'processing' });

// Control queuing behavior
client.setQueueEnabled(false); // Disable queuing
client.clearQueue(); // Clear pending messages
```

### Progress Tracking

```javascript
// Subscribe to progress updates
client.subscribeToProgress('session123', (data) => {
    const { percentage, operation, step_number } = data;
    updateProgressUI(percentage, operation);
});

// Unsubscribe
client.unsubscribeFromProgress('session123');
```

### Dashboard Updates

```javascript
// Subscribe to dashboard updates
client.subscribeToDashboard('user456', (data) => {
    if (data.type === 'stats') {
        updateDashboardStats(data.data);
    }
});
```

## API Reference

### WebSocketClient Class

#### Constructor

```javascript
new WebSocketClient(options)
```

**Options:**
- `url` (string): WebSocket server URL (default: current origin)
- `autoConnect` (boolean): Auto-connect on initialization (default: true)
- `reconnectAttempts` (number): Maximum reconnection attempts (default: 10)
- `reconnectDelay` (number): Initial reconnection delay in ms (default: 1000)
- `maxReconnectDelay` (number): Maximum reconnection delay in ms (default: 30000)
- `heartbeatInterval` (number): Heartbeat interval in ms (default: 30000)
- `messageQueueSize` (number): Maximum queued messages (default: 100)
- `debug` (boolean): Enable debug logging (default: false)

#### Methods

##### Connection Methods

```javascript
// Connect to server
await client.connect()

// Disconnect from server
client.disconnect()

// Check connection state
client.isConnected() // boolean
client.isConnecting() // boolean
client.isReconnecting() // boolean
```

##### Event Methods

```javascript
// Add event listener
client.on(event, handler)

// Remove event listener
client.off(event, handler)

// Emit event
client.emit(event, data, callback)

// Connection event handlers
client.onConnect(handler)
client.onDisconnect(handler)
client.onReconnect(handler)
client.onError(handler)
```

##### Room Methods

```javascript
// Join room
client.joinRoom(roomName)

// Leave room
client.leaveRoom(roomName)

// Subscribe to progress
client.subscribeToProgress(sessionId, callback)

// Unsubscribe from progress
client.unsubscribeFromProgress(sessionId, callback)

// Subscribe to dashboard
client.subscribeToDashboard(userId, callback)
```

##### Utility Methods

```javascript
// Get connection state
client.getState()

// Get statistics
client.getStats()

// Queue management
client.setQueueEnabled(enabled)
client.clearQueue()

// Cleanup
client.destroy()
```

### WebSocketIntegration Class

#### Methods

```javascript
// Initialize integration
webSocketIntegration.initialize(options)

// Get client instance
webSocketIntegration.getClient()

// Subscribe to progress
webSocketIntegration.subscribeToProgress(sessionId, callback)

// Subscribe to dashboard
webSocketIntegration.subscribeToDashboard(userId, callback)

// Get stats and state
webSocketIntegration.getStats()
webSocketIntegration.getState()

// Enable legacy compatibility
webSocketIntegration.enableMigrationMode()
```

## Integration Guide

### HTML Integration

Include the WebSocket client files in your HTML:

```html
<!-- Socket.IO library -->
<script src="/static/socket.io/socket.io.js"></script>

<!-- WebSocket client -->
<script src="/static/js/websocket-client.js"></script>
<script src="/static/js/websocket-integration.js"></script>
```

### Progress Tracking Integration

```javascript
// HTML progress bar
<div class="progress-container" data-progress-session="session123">
    <div class="progress-bar">
        <div class="progress-fill" style="width: 0%"></div>
    </div>
    <div class="progress-label">0%</div>
    <div class="operation-label">Initializing...</div>
</div>

// JavaScript
webSocketIntegration.subscribeToProgress('session123', (data) => {
    // Progress bars are automatically updated by the integration
    console.log(`Progress: ${data.percentage}% - ${data.operation}`);
});
```

### Dashboard Integration

```javascript
// HTML dashboard elements
<div class="dashboard-stats">
    <span data-stat="total_submissions">0</span>
    <span data-stat="completed_tasks">0</span>
    <span data-stat="active_sessions">0</span>
</div>

// JavaScript
webSocketIntegration.subscribeToDashboard('user123', (data) => {
    // Dashboard elements are automatically updated
    if (data.type === 'stats') {
        console.log('Dashboard updated:', data.data);
    }
});
```

### Connection Status Integration

```javascript
// HTML status indicator
<div class="websocket-status disconnected">Disconnected</div>

// CSS
.websocket-status.connected { color: green; }
.websocket-status.disconnected { color: red; }

// JavaScript - status is automatically updated
document.addEventListener('websocket-status-change', (event) => {
    const { status, info } = event.detail;
    console.log('WebSocket status changed:', status);
});
```

## Migration from Legacy Code

### Automatic Migration

```javascript
// Enable migration mode for backward compatibility
webSocketIntegration.enableMigrationMode();

// Migrate all known implementations
WebSocketMigration.migrateAll(webSocketIntegration);
```

### Manual Migration Examples

#### From RefactoredAIProcessor

**Before:**
```javascript
class RefactoredAIProcessor {
    initializeSocketIO() {
        this.socket = io();
        this.socket.on('connect', () => {
            console.log('Connected to SocketIO for AI processing');
        });
        this.socket.on('progress_update', (data) => {
            this.handleProgressUpdate(data);
        });
    }
}
```

**After:**
```javascript
class RefactoredAIProcessor {
    initializeSocketIO() {
        this.socket = webSocketIntegration.getClient();
        this.socket.on('progress_update', (data) => {
            this.handleProgressUpdate(data);
        });
    }
}
```

#### From OptimizedProcessingManager

**Before:**
```javascript
class OptimizedProcessingManager {
    initializeWebSocket() {
        this.socket = io();
        this.socket.on('processing_progress', (data) => {
            this.handleProgressUpdate(data);
        });
    }
}
```

**After:**
```javascript
class OptimizedProcessingManager {
    initializeWebSocket() {
        this.socket = webSocketIntegration.getClient();
        this.socket.on('processing_progress', (data) => {
            this.handleProgressUpdate(data);
        });
    }
}
```

#### From Direct Socket.IO Usage

**Before:**
```javascript
const socket = io();
socket.on('connect', () => {
    socket.emit('join_room', { room: 'progress_123' });
});
socket.on('progress_update', handleProgress);
```

**After:**
```javascript
const client = webSocketIntegration.getClient();
client.joinRoom('progress_123');
client.on('progress_update', handleProgress);
```

### Legacy Compatibility Layer

When migration mode is enabled, legacy code can continue to work:

```javascript
// Legacy code continues to work
if (window.legacySocket) {
    legacySocket.emit('test_event', { data: 'test' });
    legacySocket.on('response', handleResponse);
}

// ExamGrader namespace compatibility
if (ExamGrader.websocket) {
    ExamGrader.websocket.emit('update', { status: 'active' });
}
```

## Error Handling

### Connection Errors

```javascript
client.onError((error) => {
    switch (error.type) {
        case 'connection_error':
            console.error('Failed to connect:', error.error);
            showUserMessage('Connection failed. Retrying...');
            break;
        default:
            console.error('WebSocket error:', error);
    }
});
```

### Reconnection Handling

```javascript
client.onReconnect((info) => {
    const { attempt, maxAttempts, delay } = info;
    showUserMessage(`Reconnecting... (${attempt}/${maxAttempts})`);
    
    if (attempt === maxAttempts) {
        showUserMessage('Connection failed. Please refresh the page.');
    }
});
```

### Message Delivery Failures

```javascript
// Check if message was sent successfully
const success = client.emit('important_event', data);
if (!success) {
    console.warn('Message queued or failed to send');
    // Handle offline scenario
}
```

### Graceful Degradation

```javascript
// Fallback for when WebSocket is unavailable
if (!client.isConnected()) {
    // Use polling or other fallback mechanism
    pollForUpdates();
}
```

## Performance Optimization

### Connection Optimization

```javascript
// Optimize for your use case
const client = new WebSocketClient({
    heartbeatInterval: 60000, // Reduce heartbeat frequency
    messageQueueSize: 50,     // Limit queue size
    reconnectDelay: 2000,     // Faster initial reconnection
    maxReconnectDelay: 10000  // Lower maximum delay
});
```

### Event Handler Optimization

```javascript
// Use specific event handlers instead of catch-all
client.on('progress_update', handleProgress);
client.on('task_completed', handleCompletion);

// Remove unused handlers
client.off('old_event', oldHandler);
```

### Memory Management

```javascript
// Clean up when component is destroyed
function cleanup() {
    client.unsubscribeFromProgress(sessionId);
    client.off('progress_update', handleProgress);
    // Don't destroy the global client unless shutting down
}
```

### Monitoring Performance

```javascript
// Monitor connection health
setInterval(() => {
    const stats = client.getStats();
    console.log('WebSocket Stats:', {
        uptime: stats.uptime,
        latency: stats.latency,
        messagesSent: stats.messagesSent,
        messagesReceived: stats.messagesReceived,
        queueSize: stats.queueSize
    });
}, 30000);
```

## Testing

### Unit Testing

```javascript
// Mock WebSocket for testing
const mockClient = {
    emit: jest.fn(),
    on: jest.fn(),
    isConnected: jest.fn(() => true)
};

// Test component with mocked client
const component = new MyComponent(mockClient);
component.sendUpdate({ status: 'test' });

expect(mockClient.emit).toHaveBeenCalledWith('update', { status: 'test' });
```

### Integration Testing

```javascript
// Test with real WebSocket client
describe('WebSocket Integration', () => {
    let client;
    
    beforeEach(async () => {
        client = new WebSocketClient({ autoConnect: false });
        await client.connect();
    });
    
    afterEach(() => {
        client.destroy();
    });
    
    test('should handle progress updates', (done) => {
        client.on('progress_update', (data) => {
            expect(data.percentage).toBeGreaterThan(0);
            done();
        });
        
        // Trigger progress update
        client.emit('start_processing', { sessionId: 'test' });
    });
});
```

## Troubleshooting

### Common Issues

#### Connection Fails

```javascript
// Check if Socket.IO is loaded
if (typeof io === 'undefined') {
    console.error('Socket.IO library not loaded');
}

// Check server availability
client.onError((error) => {
    if (error.type === 'connection_error') {
        console.log('Server may be unavailable');
    }
});
```

#### Events Not Received

```javascript
// Verify room membership
const state = client.getState();
console.log('Joined rooms:', state.joinedRooms);

// Check event handler registration
client.on('test_event', () => {
    console.log('Event handler is registered');
});
```

#### High Memory Usage

```javascript
// Monitor queue size
const stats = client.getStats();
if (stats.queueSize > 50) {
    console.warn('Large message queue detected');
    client.clearQueue(); // Clear if necessary
}

// Remove unused event handlers
client.off('unused_event');
```

### Debug Mode

```javascript
// Enable debug logging
const client = new WebSocketClient({ debug: true });

// Monitor all events
client.socket.onAny((event, ...args) => {
    console.log('WebSocket event:', event, args);
});
```

### Health Monitoring

```javascript
// Create health check dashboard
function createHealthDashboard() {
    const stats = client.getStats();
    const state = client.getState();
    
    return {
        connected: client.isConnected(),
        uptime: stats.uptime,
        latency: stats.latency,
        messagesSent: stats.messagesSent,
        messagesReceived: stats.messagesReceived,
        reconnections: stats.totalReconnections,
        queueSize: stats.queueSize,
        roomCount: state.joinedRooms.length
    };
}

// Display health info
console.table(createHealthDashboard());
```

## Best Practices

1. **Use the Integration Helper**: Prefer `webSocketIntegration` over direct client usage
2. **Handle Disconnections**: Always provide fallback mechanisms
3. **Clean Up Resources**: Remove event handlers when components are destroyed
4. **Monitor Performance**: Track connection health and message throughput
5. **Test Thoroughly**: Test both connected and disconnected scenarios
6. **Use Specific Events**: Avoid catch-all event handlers for better performance
7. **Implement Graceful Degradation**: Provide alternative functionality when WebSocket is unavailable
8. **Log Appropriately**: Use debug mode during development, disable in production

## Conclusion

The unified WebSocket client provides a robust, feature-rich foundation for real-time communication in the Exam Grader application. By following this guide and best practices, you can implement reliable real-time features with minimal complexity and maximum maintainability.